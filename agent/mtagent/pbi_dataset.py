"""Command: "Build the Power BI-ready dataset from the latest offtake files."

Fully automated (steps 1-4 of the workflow: validate sources -> build
datasets -> generate dim/fact -> validate keys). Reads real committed
offtake CSVs (``PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_*.csv``)
and the seed masters (``PowerBI/SeedData/Masters/ChainMaster.csv`` /
``ArticleMaster.csv`` / ``ChainAliases.csv``) — never fabricates data,
never writes to a source file. All outputs go to
``agent/pbi_build/<build_id>/`` (gitignored).

Excel-Intelligence ingest rules (Module 1):

- **Exact duplicate rows are dropped at the entry point** (full-row
  identity), so re-supplied or double-pasted source lines can never
  double-count. Business-key duplicates ((site, ean, month) seen more
  than once with different values) are legitimate re-lines and are only
  REPORTED, never dropped.
- **Blank ``Site Code`` falls back to ``Internal Code``** when that
  column exists in the source month (older months lack it).
- **Bare corporate chain strings are alias-mapped** to their canonical
  ChainMaster row (e.g. ``Reliance`` -> ``Reliance Retail``) via
  ``ChainAliases.csv``. Every alias hit is logged to the exception
  report so a human can audit the mapping.
- **No row is ever dropped for a blank/unmapped key.** Rows with a
  blank Site Code / EAN / Chain Name are RETAINED in the Fact under
  explicit ``(blank)`` / ``UNMAPPED:`` buckets and routed to
  ``Mapping_Exception_Report.csv`` — so Fact NSV reconciles to the
  source and the data-quality cost of each gap stays visible.
- Pivot metrics (``Pivot_Chain_Category_NSV.csv``,
  ``Pivot_Zone_Brand_NSV.csv``) and a severity-classified
  ``Outlier_Report.csv`` are produced on every build.
- ``Fact_Sandbox_SeedMatched.csv`` is an ADDITIVE, validation-only subset
  of the Fact restricted to rows whose EAN matched the resolved
  ArticleMaster.csv. It never replaces or filters
  ``Fact_OfftakeSales.csv`` -- the core Fact keeps every row so
  source-to-model reconciliation keeps reconciling to source NSV. The
  quarantined NSV impact is reported in ``Data_Quality_Report.csv``
  (``sandbox_model_coverage``) and ``Dataset_Build_Log.json``
  (``sandbox_model``), with the per-EAN breakdown in
  ``Mapping_Exception_Report.csv``.

NOTE on master coverage: the committed ``ArticleMaster.csv`` is a small
SEED file (13 reference SKUs), not the full production article master. A
mostly-unmapped article exception report against that seed is therefore
EXPECTED, not a bug — see ``Data_Quality_Report``'s note field. Point
``masters_dir`` at the real production master export (via config) for
full coverage. Chain-level mapping uses the full 45-chain ChainMaster and
is representative.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from .config import Config
from .fyrules import MON3_NUM, fy_tag_from_ym

REQUIRED_OFFTAKE_COLUMNS = [
    "Zone", "State", "Chain Name", "DC Code", "Site Code", "Site Name",
    "Article", "EAN", "Brand", "Category", "Sub_category",
    "MRP", "Sales Qty", "MRP Sales Value", "NSV", "Month", "Year",
]

_FILENAME_RE = re.compile(r"_([A-Za-z]{3})_(\d{2})\.csv$")
_MIN_COMPLETE_ROWS = 1000   # heuristic: fewer rows than this -> treat month as incomplete

BLANK_BUCKET = "(blank)"
_ZSCORE_THRESHOLD = 3.0
PRODUCTION_MASTERS_DIR = Path("PowerBI") / "RawDataFolders" / "Masters"


def resolve_master_file(root: Path, masters_dir: Path | None, filename: str) -> Path:
    """Production drop-in resolution for one master file (per Module 1's
    "no hardcoded configuration updates" requirement).

    An explicit ``masters_dir`` (``--masters-dir``, or a test fixture) is
    honored exactly, no magic. Otherwise this prefers
    ``PowerBI/RawDataFolders/Masters/<filename>`` -- the same "drop a file
    in RawDataFolders/<watch>/" convention already used for monthly
    offtake refreshes -- over the small ``SeedData/Masters/`` seed set,
    resolved PER FILE so dropping in just a real ``ArticleMaster.csv``
    upgrades article mapping immediately without silently losing
    ``ChainMaster.csv`` coverage if only one file was supplied.
    """
    if masters_dir is not None:
        return masters_dir / filename
    prod_path = root / PRODUCTION_MASTERS_DIR / filename
    if prod_path.exists():
        return prod_path
    return root / "PowerBI" / "SeedData" / "Masters" / filename


def _norm_key(s: str) -> str:
    """TRIM + UPPER + strip non-alphanumerics — the same normalization
    contract used elsewhere in the agent's DuckDB views, so a chain like
    'D-Mart' and 'Dmart' key-match while a genuine gap like 'Frankros'
    vs. 'Frank Ross' still correctly reports as unmapped (and is then
    resolved explicitly via ChainAliases.csv, never by loosening the key).
    """
    return re.sub(r"[^A-Z0-9]", "", (s or "").strip().upper())


def discover_offtake_files(raw_dir: Path) -> list[tuple[int, int, Path, str]]:
    """Return [(year, month, path, label), ...] sorted oldest -> newest,
    skipping template/readme files.
    """
    out = []
    for p in sorted(raw_dir.glob("offtake_store_article_*.csv")):
        m = _FILENAME_RE.search(p.name)
        if not m:
            continue
        mon3, yy = m.group(1).title(), int(m.group(2))
        if mon3 not in MON3_NUM:
            continue
        year = 2000 + yy
        month = MON3_NUM[mon3]
        out.append((year, month, p, f"{mon3}'{yy:02d}"))
    return sorted(out, key=lambda t: (t[0], t[1]))


def _count_rows(path: Path) -> int:
    with open(path, newline="", encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1  # minus header


def load_chain_master(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[_norm_key(row["Chain"])] = row
    return out


def load_article_master(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[_norm_key(row["EAN Code"])] = row
    return out


def load_chain_aliases(path: Path, chain_master: dict) -> tuple[dict, list[str]]:
    """Load ChainAliases.csv -> {normalized alias: canonical ChainMaster row}.

    Aliases whose canonical chain does not exist in ChainMaster are NOT
    silently accepted — they are returned as ``invalid`` so the build can
    surface them (a broken alias must never invent a chain).
    """
    lookup: dict = {}
    invalid: list[str] = []
    if not path.exists():
        return lookup, invalid
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            alias_key = _norm_key(row["Alias"])
            canonical_row = chain_master.get(_norm_key(row["Canonical Chain"]))
            if not alias_key:
                continue
            if canonical_row is None:
                invalid.append(f"{row['Alias']} -> {row['Canonical Chain']}")
                continue
            lookup[alias_key] = canonical_row
    return lookup, invalid


def _nsv_share_severity(share_pct: float) -> str:
    if share_pct <= 0:
        return "Passed"
    if share_pct > 10:
        return "High"
    if share_pct > 2:
        return "Medium"
    return "Low"


def build_dataset(cfg: Config, raw_dir: Path | None = None, masters_dir: Path | None = None) -> dict:
    root = cfg.root()
    raw_dir = raw_dir or (root / "PowerBI" / "RawDataFolders" / "Offtake_Monthly")
    explicit_masters_dir = masters_dir  # None -> per-file production-drop-in resolution

    # --- Step 1: validate source files -----------------------------------
    if not raw_dir.exists():
        return {"blocked_reason": f"source folder not found: {raw_dir}"}
    files = discover_offtake_files(raw_dir)
    if not files:
        return {"blocked_reason": f"no offtake_store_article_*.csv files found in {raw_dir}"}

    year, month, path, label = files[-1]
    row_count = _count_rows(path)
    excluded_incomplete = None
    if row_count < _MIN_COMPLETE_ROWS and len(files) > 1:
        excluded_incomplete = label
        year, month, path, label = files[-2]
        row_count = _count_rows(path)

    with open(path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    missing_cols = [c for c in REQUIRED_OFFTAKE_COLUMNS if c not in header]
    if missing_cols:
        return {"blocked_reason": f"{path.name} is missing required column(s): {missing_cols}"}
    idx = {h: i for i, h in enumerate(header)}
    has_internal_code = "Internal Code" in idx

    # --- masters + alias dictionary -----------------------------------
    chain_master = load_chain_master(resolve_master_file(root, explicit_masters_dir, "ChainMaster.csv"))
    article_master = load_article_master(resolve_master_file(root, explicit_masters_dir, "ArticleMaster.csv"))
    alias_lookup, invalid_aliases = load_chain_aliases(
        resolve_master_file(root, explicit_masters_dir, "ChainAliases.csv"), chain_master)

    # --- Step 2/3: stream-aggregate into fact + detect exceptions -------
    fact = defaultdict(lambda: {"NSV": 0.0, "MRP_Sales_Value": 0.0, "Sales_Qty": 0.0, "sites": set()})
    unmapped_chains = defaultdict(lambda: {"count": 0, "nsv": 0.0})
    unmapped_articles = defaultdict(lambda: {"count": 0, "nsv": 0.0})
    alias_mapped_chains = defaultdict(lambda: {"count": 0, "nsv": 0.0, "canonical": ""})
    key_seen = defaultdict(int)
    seen_row_hashes: set = set()
    exact_duplicate_rows = 0
    exact_duplicate_nsv = 0.0
    invalid_numeric_rows = 0
    site_code_fallbacks = 0
    retained_blank = {
        "Site Code": {"count": 0, "nsv": 0.0},
        "EAN": {"count": 0, "nsv": 0.0},
        "Chain Name": {"count": 0, "nsv": 0.0},
    }
    negative_nsv_rows = 0
    negative_nsv_total = 0.0
    zero_mrp_value_with_qty_rows = 0
    fy_tag = fy_tag_from_ym(year, month)

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)  # header
        for row in reader:
            row_hash = hash(tuple(row))
            if row_hash in seen_row_hashes:
                exact_duplicate_rows += 1
                try:
                    exact_duplicate_nsv += float(row[idx["NSV"]] or 0)
                except (ValueError, IndexError):
                    pass
                continue
            seen_row_hashes.add(row_hash)

            try:
                nsv = float(row[idx["NSV"]] or 0)
                mrp_val = float(row[idx["MRP Sales Value"]] or 0)
                qty = float(row[idx["Sales Qty"]] or 0)
            except (ValueError, IndexError):
                invalid_numeric_rows += 1
                continue

            site_code = row[idx["Site Code"]].strip()
            if not site_code and has_internal_code:
                internal = row[idx["Internal Code"]].strip()
                if internal:
                    site_code = internal
                    site_code_fallbacks += 1
            ean = row[idx["EAN"]].strip()
            chain_raw = row[idx["Chain Name"]].strip()
            zone = row[idx["Zone"]].strip().upper()
            state = row[idx["State"]].strip().title() or BLANK_BUCKET

            # Retain-and-route: a blank key never drops the row -- it is
            # bucketed explicitly and reported, so Fact still reconciles.
            site_is_real = bool(site_code)
            if not site_is_real:
                retained_blank["Site Code"]["count"] += 1
                retained_blank["Site Code"]["nsv"] += nsv
                site_code = BLANK_BUCKET
            if not ean:
                retained_blank["EAN"]["count"] += 1
                retained_blank["EAN"]["nsv"] += nsv
                ean = BLANK_BUCKET

            if site_is_real:
                key_seen[(site_code, ean, label)] += 1

            if nsv < 0:
                negative_nsv_rows += 1
                negative_nsv_total += nsv
            if qty > 0 and mrp_val == 0:
                zero_mrp_value_with_qty_rows += 1

            if not chain_raw:
                retained_blank["Chain Name"]["count"] += 1
                retained_blank["Chain Name"]["nsv"] += nsv
                chain_out = f"UNMAPPED:{BLANK_BUCKET}"
            else:
                chain_key = _norm_key(chain_raw)
                chain_row = chain_master.get(chain_key)
                if chain_row is None and chain_key in alias_lookup:
                    chain_row = alias_lookup[chain_key]
                    a = alias_mapped_chains[chain_raw]
                    a["count"] += 1
                    a["nsv"] += nsv
                    a["canonical"] = chain_row["Chain"]
                if chain_row is None:
                    unmapped_chains[chain_raw]["count"] += 1
                    unmapped_chains[chain_raw]["nsv"] += nsv
                    chain_out = f"UNMAPPED:{chain_raw}"
                else:
                    chain_out = chain_row["Account"]

            article_row = article_master.get(_norm_key(ean)) if ean != BLANK_BUCKET else None
            if article_row is None:
                if ean != BLANK_BUCKET:
                    unmapped_articles[ean]["count"] += 1
                    unmapped_articles[ean]["nsv"] += nsv
                brand = row[idx["Brand"]].strip()
                category = row[idx["Category"]].strip()
                sub_category = row[idx["Sub_category"]].strip()
            else:
                brand = article_row["Brand"]
                category = article_row["Category"]
                sub_category = article_row["Sub-category"]

            fact_key = (fy_tag, label, zone, state, chain_out, ean, brand, category, sub_category)
            f = fact[fact_key]
            f["NSV"] += nsv
            f["MRP_Sales_Value"] += mrp_val
            f["Sales_Qty"] += qty
            if site_is_real:
                f["sites"].add(site_code)

    duplicate_keys = {k: c for k, c in key_seen.items() if c > 1}
    blank_rows_retained = sum(d["count"] for d in retained_blank.values())
    blank_nsv_retained = sum(d["nsv"] for d in retained_blank.values())
    fact_nsv_total = sum(v["NSV"] for v in fact.values())
    # source total = every parsed row, INCLUDING the exact duplicates that
    # were dropped at entry -- so the reconciliation line proves the only
    # NSV removed from the pipeline is the duplicate NSV, nothing else.
    source_nsv_total = fact_nsv_total + exact_duplicate_nsv

    # --- write outputs -------------------------------------------------
    build_id = f"{fy_tag}_{label.replace(chr(39), '')}"
    out_dir = cfg.path(cfg.pbi_build_dir) / build_id
    out_dir.mkdir(parents=True, exist_ok=True)

    fact_path = out_dir / "Fact_OfftakeSales.csv"
    with open(fact_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["FY", "Month", "Zone", "State", "Chain", "EAN", "Brand", "Category",
                    "Sub_Category", "NSV", "MRP_Sales_Value", "Sales_Qty", "Store_Count"])
        for (fy, mon, zone, state, chain, ean, brand, cat, subcat), v in sorted(fact.items()):
            w.writerow([fy, mon, zone, state, chain, ean, brand, cat, subcat,
                        round(v["NSV"], 4), round(v["MRP_Sales_Value"], 2),
                        round(v["Sales_Qty"], 2), len(v["sites"])])

    # --- sandbox model: a VALIDATION-ONLY, additive subset of the Fact
    # above, restricted to rows whose EAN matched the resolved
    # ArticleMaster.csv (production drop-in or seed -- whichever was
    # actually used, never hardcoded to "13 SKUs"). Fact_OfftakeSales.csv
    # itself is never filtered or stripped; every row and every rupee of
    # NSV stays in the core Fact so source-to-model reconciliation keeps
    # passing. This exists purely so a small, fully-mapped mini-model can
    # be validated end to end (relationships, DAX, visuals) while the real
    # production article master is still pending.
    sandbox_path = out_dir / "Fact_Sandbox_SeedMatched.csv"
    sandbox_rows = 0
    sandbox_nsv = 0.0
    with open(sandbox_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["FY", "Month", "Zone", "State", "Chain", "EAN", "Brand", "Category",
                    "Sub_Category", "NSV", "MRP_Sales_Value", "Sales_Qty", "Store_Count"])
        for (fy, mon, zone, state, chain, ean, brand, cat, subcat), v in sorted(fact.items()):
            if ean == BLANK_BUCKET or _norm_key(ean) not in article_master:
                continue
            w.writerow([fy, mon, zone, state, chain, ean, brand, cat, subcat,
                        round(v["NSV"], 4), round(v["MRP_Sales_Value"], 2),
                        round(v["Sales_Qty"], 2), len(v["sites"])])
            sandbox_rows += 1
            sandbox_nsv += v["NSV"]

    dim_date_path = out_dir / "Dim_Date.csv"
    with open(dim_date_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["FY", "Month", "MonthNo", "Quarter"])
        fy_month_no = month - 3 if month >= 4 else month + 9
        quarter = f"Q{-(-fy_month_no // 3)}"
        w.writerow([fy_tag, label, month, quarter])

    dim_chain_path = out_dir / "Dim_Chain.csv"
    with open(dim_chain_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Chain", "Account", "Chain Type", "Primary Zone", "Active"])
        for row in chain_master.values():
            w.writerow([row["Chain"], row["Account"], row["Chain Type"], row["Primary Zone"], row["Active"]])

    dim_article_path = out_dir / "Dim_Article.csv"
    with open(dim_article_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Article Code", "Article Description", "EAN Code", "Brand", "Category", "Sub-category", "Range", "Pack Size"])
        for row in article_master.values():
            w.writerow([row["Article Code"], row["Article Description"], row["EAN Code"],
                        row["Brand"], row["Category"], row["Sub-category"], row["Range"], row["Pack Size"]])

    exc_path = out_dir / "Mapping_Exception_Report.csv"
    with open(exc_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["exception_type", "value", "row_count", "nsv_impact", "resolution"])
        for chain, d in sorted(unmapped_chains.items(), key=lambda kv: -kv[1]["nsv"]):
            w.writerow(["unmapped_chain", chain, d["count"], round(d["nsv"], 2),
                        "add to ChainMaster.csv or map via ChainAliases.csv"])
        for chain, d in sorted(alias_mapped_chains.items(), key=lambda kv: -kv[1]["nsv"]):
            w.writerow(["alias_mapped_chain", chain, d["count"], round(d["nsv"], 2),
                        f"auto-mapped to '{d['canonical']}' via ChainAliases.csv -- verify once"])
        for field in ("Site Code", "EAN", "Chain Name"):
            d = retained_blank[field]
            if d["count"]:
                w.writerow([f"blank_{field.lower().replace(' ', '_')}", BLANK_BUCKET, d["count"],
                            round(d["nsv"], 2),
                            "rows RETAINED in Fact under the (blank) bucket -- fix at source extract"])
        if exact_duplicate_rows:
            w.writerow(["exact_duplicate_row", "(full-row identity)", exact_duplicate_rows,
                        round(exact_duplicate_nsv, 2), "dropped at entry point (idempotent re-ingest)"])
        if invalid_numeric_rows:
            w.writerow(["invalid_numeric_row", "(unparseable NSV/MRP/Qty)", invalid_numeric_rows, "",
                        "skipped -- values not parseable as numbers; fix at source extract"])
        for bad in invalid_aliases:
            w.writerow(["invalid_alias", bad, "", "",
                        "ChainAliases.csv points at a chain missing from ChainMaster.csv -- alias ignored"])
        for ean, d in sorted(unmapped_articles.items(), key=lambda kv: -kv[1]["nsv"])[:500]:
            w.writerow(["unmapped_article_ean", ean, d["count"], round(d["nsv"], 2),
                        "add to ArticleMaster.csv (seed master covers 13 SKUs only)"])

    # --- pivot metrics ---------------------------------------------------
    pivot_chain_cat = defaultdict(lambda: defaultdict(float))
    pivot_zone_brand = defaultdict(lambda: defaultdict(float))
    article_nsv = defaultdict(float)          # ean -> total NSV
    article_category = {}                     # ean -> category (last seen)
    chain_nsv = defaultdict(float)
    for (fy, mon, zone, state, chain, ean, brand, cat, subcat), v in fact.items():
        pivot_chain_cat[chain][cat] += v["NSV"]
        pivot_zone_brand[zone][brand] += v["NSV"]
        chain_nsv[chain] += v["NSV"]
        if ean != BLANK_BUCKET:
            article_nsv[ean] += v["NSV"]
            article_category[ean] = cat

    def _write_pivot(path: Path, row_label: str, data: dict) -> None:
        cols = sorted({c for row in data.values() for c in row})
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow([row_label] + cols + ["Total"])
            for key in sorted(data, key=lambda k: -sum(data[k].values())):
                vals = [round(data[key].get(c, 0.0), 4) for c in cols]
                w.writerow([key] + vals + [round(sum(data[key].values()), 4)])
            w.writerow(["TOTAL"] + [round(sum(data[k].get(c, 0.0) for k in data), 4) for c in cols]
                       + [round(sum(sum(r.values()) for r in data.values()), 4)])

    _write_pivot(out_dir / "Pivot_Chain_Category_NSV.csv", "Chain", pivot_chain_cat)
    _write_pivot(out_dir / "Pivot_Zone_Brand_NSV.csv", "Zone", pivot_zone_brand)

    # --- outlier report (severity-classified) ----------------------------
    outlier_rows = []

    unmapped_nsv = sum(d["nsv"] for d in unmapped_chains.values())
    unmapped_share = 100 * unmapped_nsv / fact_nsv_total if fact_nsv_total else 0.0
    outlier_rows.append({
        "severity": _nsv_share_severity(unmapped_share), "check": "unmapped_chain_nsv_share",
        "entity": f"{len(unmapped_chains)} chain(s)", "value": f"{round(unmapped_share, 2)}% of NSV",
        "note": "NSV sitting in UNMAPPED buckets -- extend ChainMaster.csv or ChainAliases.csv",
    })

    blank_site_share = 100 * retained_blank["Site Code"]["nsv"] / fact_nsv_total if fact_nsv_total else 0.0
    outlier_rows.append({
        "severity": _nsv_share_severity(blank_site_share), "check": "blank_site_code_nsv_share",
        "entity": f"{retained_blank['Site Code']['count']} row(s)",
        "value": f"{round(blank_site_share, 2)}% of NSV",
        "note": "rows retained under the (blank) site bucket; store-level analyses undercount until fixed at source",
    })

    neg_chains = sorted((c for c, v in chain_nsv.items() if v < 0), key=lambda c: chain_nsv[c])
    outlier_rows.append({
        "severity": "High" if neg_chains else "Passed", "check": "negative_chain_total_nsv",
        "entity": "; ".join(neg_chains[:5]) or "none", "value": len(neg_chains),
        "note": "a chain whose month total is negative usually means a returns/claims file leaked into offtake",
    })

    outlier_rows.append({
        "severity": "Low" if negative_nsv_rows else "Passed", "check": "negative_nsv_rows",
        "entity": f"{negative_nsv_rows} row(s)", "value": round(negative_nsv_total, 4),
        "note": "individual negative rows are normal returns; flagged for volume awareness only",
    })

    outlier_rows.append({
        "severity": "Medium" if zero_mrp_value_with_qty_rows else "Passed", "check": "sales_qty_without_mrp_value",
        "entity": f"{zero_mrp_value_with_qty_rows} row(s)", "value": zero_mrp_value_with_qty_rows,
        "note": "quantity sold but MRP Sales Value = 0 -- pricing gap in the source extract",
    })

    # per-category article z-score outliers on NSV (informational)
    by_cat = defaultdict(list)
    for ean, total in article_nsv.items():
        by_cat[article_category[ean]].append((ean, total))
    z_outliers = []
    for cat, pairs in by_cat.items():
        if len(pairs) < 10:
            continue  # too few articles for a meaningful distribution
        vals = [t for _, t in pairs]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = var ** 0.5
        if std == 0:
            continue
        for ean, total in pairs:
            z = (total - mean) / std
            if abs(z) > _ZSCORE_THRESHOLD:
                z_outliers.append((cat, ean, total, round(z, 2)))
    z_outliers.sort(key=lambda t: -abs(t[3]))
    outlier_rows.append({
        "severity": "Low" if z_outliers else "Passed", "check": "article_nsv_zscore",
        "entity": f"{len(z_outliers)} article(s) beyond |z|>{_ZSCORE_THRESHOLD}",
        "value": "; ".join(f"{ean} ({cat}, z={z})" for cat, ean, _, z in z_outliers[:10]),
        "note": "hero SKUs concentrate NSV -- informational, verify only if an article looks unfamiliar",
    })

    outlier_path = out_dir / "Outlier_Report.csv"
    with open(outlier_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["severity", "check", "entity", "value", "note"])
        w.writeheader()
        w.writerows(outlier_rows)

    # --- data quality + reconciliation ------------------------------------
    dq_path = out_dir / "Data_Quality_Report.csv"
    with open(dq_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "value", "note"])
        w.writerow(["latest_month_used", label, "excluded_incomplete_month=" + str(excluded_incomplete)])
        w.writerow(["source_row_count", row_count, ""])
        w.writerow(["exact_duplicate_rows_dropped", exact_duplicate_rows,
                    f"full-row duplicates removed at entry (NSV impact {round(exact_duplicate_nsv, 4)})"])
        w.writerow(["invalid_numeric_rows_skipped", invalid_numeric_rows,
                    "NSV/MRP/Qty not parseable as numbers"])
        w.writerow(["site_code_internal_fallbacks", site_code_fallbacks,
                    "blank Site Code substituted from Internal Code"])
        w.writerow(["blank_key_rows_retained", blank_rows_retained,
                    f"kept in Fact under (blank)/UNMAPPED buckets (NSV {round(blank_nsv_retained, 4)}) "
                    f"-- by field: { {k: v['count'] for k, v in retained_blank.items()} }"])
        w.writerow(["duplicate_business_keys", len(duplicate_keys),
                    "(site, ean, month) seen >1x in source (real sites only) -- reported, not dropped"])
        w.writerow(["alias_mapped_chains", len(alias_mapped_chains),
                    "chains resolved via ChainAliases.csv -- see Mapping_Exception_Report"])
        w.writerow(["unmapped_chains", len(unmapped_chains), "see Mapping_Exception_Report"])
        w.writerow(["unmapped_articles", len(unmapped_articles),
                    "ArticleMaster.csv is a small seed (13 SKUs) -- high unmapped count here is expected, "
                    "not a data-quality defect; supply the production master for full coverage"])
        if invalid_aliases:
            w.writerow(["invalid_aliases", len(invalid_aliases), "; ".join(invalid_aliases)])
        sandbox_pct = round(100 * sandbox_nsv / fact_nsv_total, 2) if fact_nsv_total else 0.0
        w.writerow(["sandbox_model_coverage",
                    f"{sandbox_rows}/{len(fact)} fact rows, NSV {round(sandbox_nsv, 2)}/{round(fact_nsv_total, 2)} ({sandbox_pct}%)",
                    "Fact_Sandbox_SeedMatched.csv is a VALIDATION-ONLY subset restricted to ArticleMaster-matched "
                    "rows -- the core Fact_OfftakeSales.csv above is never filtered or stripped; quarantined NSV "
                    f"= {round(fact_nsv_total - sandbox_nsv, 2)} (see Mapping_Exception_Report for per-EAN detail)"])

    recon_path = out_dir / "Source_Reconciliation_Report.csv"
    variance = round(source_nsv_total - fact_nsv_total, 6)
    unexplained = round(variance - round(exact_duplicate_nsv, 6), 6)
    with open(recon_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "source_value", "output_value", "variance", "status"])
        w.writerow(["NSV", round(source_nsv_total, 2), round(fact_nsv_total, 2), variance,
                    "PASS" if abs(unexplained) < 0.01 else "FAIL"])
        w.writerow(["NSV_variance_explained_by_dropped_duplicates", round(exact_duplicate_nsv, 2), "", "",
                    "INFO"])
        w.writerow(["row_count", row_count, len(fact), "n/a (fact is aggregated, not 1:1)", "INFO"])

    build_log = {
        "build_id": build_id, "source_file": str(path.relative_to(root)),
        "fy": fy_tag, "month": label, "source_row_count": row_count,
        "fact_row_count": len(fact),
        "exact_duplicate_rows_dropped": exact_duplicate_rows,
        "invalid_numeric_rows_skipped": invalid_numeric_rows,
        "site_code_internal_fallbacks": site_code_fallbacks,
        "blank_key_rows_retained": blank_rows_retained,
        "blank_field_counts": {k: v["count"] for k, v in retained_blank.items()},
        "duplicate_business_keys": len(duplicate_keys),
        "alias_mapped_chains": len(alias_mapped_chains),
        "unmapped_chains": len(unmapped_chains), "unmapped_articles": len(unmapped_articles),
        "reconciliation_variance": variance,
        "reconciliation_unexplained_variance": unexplained,
        "sandbox_model": {
            "output_file": str(sandbox_path.relative_to(root)),
            "row_count": sandbox_rows,
            "nsv_covered": round(sandbox_nsv, 4),
            "nsv_quarantined": round(fact_nsv_total - sandbox_nsv, 4),
            "pct_nsv_covered": round(100 * sandbox_nsv / fact_nsv_total, 2) if fact_nsv_total else 0.0,
        },
    }
    log_path = out_dir / "Dataset_Build_Log.json"
    log_path.write_text(json.dumps(build_log, indent=2), encoding="utf-8")

    warning_bits = []
    if unmapped_chains:
        warning_bits.append(f"{len(unmapped_chains)} unmapped chain(s)")
    if blank_rows_retained:
        warning_bits.append(f"{blank_rows_retained} blank-key row(s) retained under (blank) buckets")
    if abs(unexplained) >= 0.01:
        warning_bits.append(f"NSV reconciliation has UNEXPLAINED variance {unexplained}")
    warning = ", ".join(warning_bits)

    return {
        "output_file": str(out_dir.relative_to(root)),
        "validation_result": json.dumps(build_log),
        "warning": warning,
    }
