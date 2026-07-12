"""Proactive diff engine: month-over-month exception analytics on the
offtake watch folder. Pure stdlib; powers two surfaces:

  * `place` — after the placement advice, an automated comparison of the
    newest month vs the prior month prints a three-point Proactive
    Exception Report (volume/NSV drops, NPI zero-sales, operational gaps).
  * `meeting --drilldown` — the same computation plus sub-category /
    pack-size mix deltas, top underperforming outlets, and the GST/TOT
    confidence status, injected as computed context for the local model
    (and printed verbatim when Ollama is down).

Data-contract rules applied here: lookup dimensions (Chain Name, Site
Name, DC Code, descriptions) are TRIM+UPPER-normalized for matching (the
first-seen trimmed original is kept for display), and month labels accept
text styles or raw Excel serials via fyrules.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .fyrules import ym_from_label

MIN_BASE_LAKH = 1.0     # ignore MoM% on bases smaller than this (noise guard)
_FILE_MONTH_RE = re.compile(r"_([A-Z][a-z]{2})[_-](\d{2})", re.ASCII)


def _norm(s: str) -> str:
    return " ".join(str(s).split()).upper()


def file_month(path: Path) -> tuple[int, int] | None:
    m = _FILE_MONTH_RE.search(path.stem)
    return ym_from_label(f"{m.group(1)}-{m.group(2)}") if m else None


@dataclass
class MonthAgg:
    label: str
    zone_nsv: dict = field(default_factory=dict)
    chaindc_nsv: dict = field(default_factory=dict)    # (chain, dc) -> nsv
    store_nsv: dict = field(default_factory=dict)      # site_code -> nsv
    store_meta: dict = field(default_factory=dict)     # site_code -> (name, chain, type)
    article_nsv: dict = field(default_factory=dict)
    article_stores: dict = field(default_factory=dict) # article -> set(site)
    article_desc: dict = field(default_factory=dict)
    subcat_nsv: dict = field(default_factory=dict)
    pack_nsv: dict = field(default_factory=dict)
    rows: int = 0


def load_offtake_month(path: Path) -> MonthAgg | None:
    """Aggregate one offtake CSV. Column access is positional by first-seen
    header name (duplicate headers exist in these extracts)."""
    ym = file_month(path)
    mon3 = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    agg = MonthAgg(label=f"{mon3[ym[1]]}-{ym[0] % 100:02d}" if ym else "?")
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        def col(name):
            try:
                return header.index(name)
            except ValueError:
                return None
        c = {k: col(k) for k in ("Zone", "Chain Name", "DC Code", "Site Code",
                                 "Site Name", "Store Type", "Article",
                                 "Chain Article Description", "Sub_category",
                                 "Net Weight", "NSV")}
        if c["NSV"] is None or c["Site Code"] is None:
            return None
        for row in reader:
            if len(row) <= c["NSV"]:
                continue
            try:
                nsv = float(row[c["NSV"]]) if row[c["NSV"]].strip() else 0.0
            except ValueError:
                continue
            agg.rows += 1
            def get(key):
                i = c[key]
                return row[i].strip() if i is not None and i < len(row) else ""
            zone = _norm(get("Zone")) or "(BLANK)"
            chain = _norm(get("Chain Name")) or "(BLANK)"
            dc = _norm(get("DC Code")) or "(NO DC)"
            site = _norm(get("Site Code")) or "(BLANK)"
            art = _norm(get("Article")) or "(BLANK)"
            agg.zone_nsv[zone] = agg.zone_nsv.get(zone, 0.0) + nsv
            agg.chaindc_nsv[(chain, dc)] = agg.chaindc_nsv.get((chain, dc), 0.0) + nsv
            agg.store_nsv[site] = agg.store_nsv.get(site, 0.0) + nsv
            agg.store_meta.setdefault(
                site, (get("Site Name"), get("Chain Name"), get("Store Type")))
            agg.article_nsv[art] = agg.article_nsv.get(art, 0.0) + nsv
            agg.article_stores.setdefault(art, set()).add(site)
            agg.article_desc.setdefault(art, get("Chain Article Description"))
            sub = _norm(get("Sub_category")) or "(BLANK)"
            agg.subcat_nsv[sub] = agg.subcat_nsv.get(sub, 0.0) + nsv
            pack = _norm(get("Net Weight")) or "(BLANK)"
            agg.pack_nsv[pack] = agg.pack_nsv.get(pack, 0.0) + nsv
    return agg


def _drops(prior: dict, cur: dict, threshold_pct: float) -> list[tuple]:
    out = []
    for key, p in prior.items():
        if p < MIN_BASE_LAKH:
            continue
        cv = cur.get(key, 0.0)
        pct = (cv - p) / p * 100
        if pct < -threshold_pct:
            out.append((key, p, cv, pct))
    out.sort(key=lambda t: t[1] * t[3] / 100)   # biggest absolute damage first
    return out


def _npi_list(cfg: Config) -> set | None:
    p = cfg.path(cfg.npi_list)
    if not p.exists():
        return None
    arts = set()
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        reader = csv.reader(fh)
        header = next(reader, [])
        idx = 0
        for cand in ("Article", "Article Code", "SKU", "EAN"):
            if cand in header:
                idx = header.index(cand)
                break
        for row in reader:
            if row and row[idx].strip():
                arts.add(_norm(row[idx]))
    return arts or None


def analyze_offtake(cfg: Config, folder: Path | None = None,
                    extra_file: Path | None = None) -> dict | None:
    """Compare the two most recent months in the offtake watch folder
    (extra_file, if given and existing, joins the candidate set). Returns
    None when fewer than two months are available."""
    folder = folder or (cfg.root() /
                        "PowerBI/RawDataFolders/Offtake_Monthly")
    files = [f for f in sorted(folder.glob("*.csv"))
             if not f.name.startswith("_") and file_month(f)]
    if extra_file and extra_file.exists() and file_month(extra_file) and \
            extra_file.resolve() not in [f.resolve() for f in files]:
        files.append(extra_file)
    files.sort(key=lambda f: file_month(f))
    if len(files) < 2:
        return None
    prior_f, cur_f = files[-2], files[-1]
    prior, cur = load_offtake_month(prior_f), load_offtake_month(cur_f)
    if not prior or not cur:
        return None
    th = cfg.mom_drop_threshold_pct

    npi = _npi_list(cfg)
    if npi is not None:
        npi_universe, npi_source = npi, "NPI_List.csv"
    else:
        # proxy: articles that first appeared in the PRIOR month's file
        npi_universe = set(prior.article_nsv) - set(
            a for f in files[:-2] for a in (load_offtake_month(f) or
                                            MonthAgg("")).article_nsv) \
            if len(files) > 2 else set(prior.article_nsv)
        npi_source = ("proxy: articles present in the prior month "
                      f"({prior.label}) — supply {cfg.npi_list} for the real list")
    npi_zero = sorted(
        a for a in npi_universe
        if cur.article_nsv.get(a, 0.0) <= 0.0 or not cur.article_stores.get(a))

    missing = [(s, *prior.store_meta.get(s, ("", "", "")), prior.store_nsv[s])
               for s in prior.store_nsv
               if prior.store_nsv[s] > 0 and s not in cur.store_nsv]
    missing.sort(key=lambda t: -t[-1])

    store_drops = _drops(prior.store_nsv, cur.store_nsv, 0.0)  # all declines
    return {
        "prior": prior, "cur": cur, "threshold_pct": th,
        "zone_drops": _drops(prior.zone_nsv, cur.zone_nsv, th),
        "dc_drops": _drops(prior.chaindc_nsv, cur.chaindc_nsv, th),
        "npi_source": npi_source, "npi_zero": npi_zero,
        "missing_stores": missing,
        "store_drops": store_drops,
        "subcat_delta": sorted(((k, prior.subcat_nsv.get(k, 0.0),
                                 cur.subcat_nsv.get(k, 0.0),
                                 cur.subcat_nsv.get(k, 0.0) - prior.subcat_nsv.get(k, 0.0))
                                for k in set(prior.subcat_nsv) | set(cur.subcat_nsv)),
                               key=lambda t: t[3]),
        "pack_delta": sorted(((k, prior.pack_nsv.get(k, 0.0),
                               cur.pack_nsv.get(k, 0.0),
                               cur.pack_nsv.get(k, 0.0) - prior.pack_nsv.get(k, 0.0))
                              for k in set(prior.pack_nsv) | set(cur.pack_nsv)),
                             key=lambda t: t[3]),
    }


def gst_confidence_summary(cfg: Config) -> list[dict]:
    p = cfg.root() / "PowerBI/SeedData/Masters/GST_Rate_QC_Table.csv"
    if not p.exists():
        return []
    out = []
    with open(p, newline="", encoding="utf-8-sig", errors="replace") as fh:
        for row in csv.DictReader(fh):
            out.append({"category": row.get("Category", ""),
                        "confidence": row.get("Confidence", ""),
                        "finance_approved": row.get("Finance_Approved", ""),
                        "impact_on_tot_pct": row.get("Impact_on_TOT_pct", "")})
    return out


# --------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------

def format_exception_report(r: dict) -> str:
    prior, cur, th = r["prior"], r["cur"], r["threshold_pct"]
    out = [f"\nProactive Exception Report — {cur.label} vs {prior.label} "
           f"(threshold {th:.0f}% MoM, bases < {MIN_BASE_LAKH} Lakh ignored)"]

    out.append(f"1) Volume/NSV drops > {th:.0f}% MoM:")
    hits = [f"   - Zone {z}: {p:,.1f} -> {c:,.1f} Lakh ({pct:+.1f}%)"
            for z, p, c, pct in r["zone_drops"]]
    hits += [f"   - {chain} / DC {dc}: {p:,.1f} -> {c:,.1f} Lakh ({pct:+.1f}%)"
             for (chain, dc), p, c, pct in r["dc_drops"][:10]]
    out += hits or ["   - none: no zone or chain/DC breached the threshold"]
    if len(r["dc_drops"]) > 10:
        out.append(f"   … {len(r['dc_drops']) - 10} more chain/DC drops")

    out.append(f"2) NPI tracking (source: {r['npi_source']}):")
    if r["npi_zero"]:
        for a in r["npi_zero"][:10]:
            desc = (r["prior"].article_desc.get(a) or
                    r["cur"].article_desc.get(a) or "")[:45]
            out.append(f"   - article {a} {desc!s}: ZERO sales / zero-store "
                       f"availability in {cur.label}")
        if len(r["npi_zero"]) > 10:
            out.append(f"   … {len(r['npi_zero']) - 10} more zero-sales articles")
    else:
        out.append("   - none: every tracked NPI billed in the new month")

    out.append("3) Operational gaps (reported last cycle, ZERO records now):")
    if r["missing_stores"]:
        for s, name, chain, stype, pnsv in r["missing_stores"][:10]:
            out.append(f"   - {s} {name[:30]} ({chain}, {stype or 'type n/a'}): "
                       f"{pnsv:,.2f} Lakh in {prior.label}, absent in {cur.label}")
        if len(r["missing_stores"]) > 10:
            out.append(f"   … {len(r['missing_stores']) - 10} more missing stores")
        gone = sum(t[-1] for t in r["missing_stores"])
        out.append(f"   missing-store NSV at risk: {gone:,.1f} Lakh")
    else:
        out.append("   - none: every store that billed last month billed again")
    return "\n".join(out)


def format_drilldown_context(cfg: Config, r: dict) -> str:
    """Computed context block for meeting --drilldown (also printed raw
    when no local LLM is available)."""
    prior, cur = r["prior"], r["cur"]
    n = cfg.drilldown_top_n
    out = [f"[computed] offtake drill-down {cur.label} vs {prior.label} (INR Lakh)"]
    out.append(f"top {n} underperforming outlets (by absolute MoM NSV drop):")
    for s, p, c, pct in r["store_drops"][:n]:
        name, chain, stype = (prior.store_meta.get(s) or
                              cur.store_meta.get(s) or ("", "", ""))
        out.append(f"  {s} {name[:32]} | {chain} | {stype or 'type n/a'} | "
                   f"{p:,.2f} -> {c:,.2f} ({pct:+.1f}%)")
    out.append("sub-category NSV delta (worst first):")
    for k, p, c, d in r["subcat_delta"][:6]:
        out.append(f"  {k}: {p:,.1f} -> {c:,.1f} ({d:+,.1f})")
    out.append("pack-size (net weight) NSV delta (worst first):")
    for k, p, c, d in r["pack_delta"][:6]:
        out.append(f"  {k}: {p:,.1f} -> {c:,.1f} ({d:+,.1f})")
    gst = gst_confidence_summary(cfg)
    if gst:
        pending = [g for g in gst if g["finance_approved"].strip().lower() != "approved"]
        out.append(f"GST/TOT confidence ({len(gst)} rows, "
                   f"{len(pending)} NOT finance-approved):")
        for g in gst:
            out.append(f"  {g['category']}: confidence={g['confidence'] or '?'}, "
                       f"finance={g['finance_approved'] or '?'}, "
                       f"TOT impact={g['impact_on_tot_pct'] or '?'}")
    return "\n".join(out)
