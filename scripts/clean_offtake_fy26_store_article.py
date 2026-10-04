#!/usr/bin/env python3
"""Clean and QC the last-year (FY26, Apr-25 to Mar-26) store x article offtake files, one folder per month and one CSV per chain.

The files stay outside Git (data/raw_drops is ignored). What is written:

  --out   <folder>/offtake_store_article_<Mon>_25.csv   (Apr..Dec) and _26.csv (Jan..Mar): one clean file per month, the same 34 columns as this year's
          store x article files, ONE ROW per chain x store x month x article. Local only.
  data/offtake_fy26/Store_Month_NSV_FY26.csv            store x month NSV and units (no names, no articles): the last-year store sales the city
          workbook and dashboards read. Tracked.
  data/qc/offtake_fy26_QC.csv, offtake_fy26_by_chain_month.csv, offtake_fy26_duplicate_lines.csv   what was checked and what was found. Tracked.

What the cleaning does (every step is counted in the QC files; nothing is estimated and no sales are dropped):
  1. Headers differ between chains (blank leading columns, 'Unique' / 'Unique Code', 'Yr' / 'Year'): read by name. The Reliance file holds two stacked tables
     (non-counter and Brand Counter, one extra leading column difference): both are read, Brand Counter rows go to chain 'Reliance Brand Counter' like this year.
  2. The month comes from the folder. The Month_Std column is only compared (typos such as Aug'26 or Dec-25 are reported, not used).
  3. One spelling each: chain (CHAIN_STANDARD), zone, state (STATE_STANDARD), city (one capitalisation per city), store name (truncated copies take the full name),
     brand, category, sub category, range and article name (per EAN: this year's article master first, then the most frequent value).
  4. Lines that repeat the same chain x store x month x article are added into one row (quantity, MRP value and NSV are summed; MRP is value / quantity).
     Totals do not change. Identical lines WITH a store identity are listed as suspected double loads (offtake_fy26_duplicate_lines.csv) but NOT removed:
     they are in the published FY26 baseline, which has to keep tying (31,119.87 L). Owner decision 2026-10-04: keep them, baseline unchanged.
  5. Tie-out: every chain x month NSV (Brand Counter apart) against data/raw_drops/_agg/offtake_fy26.json, and input NSV = output NSV.

    python scripts/clean_offtake_fy26_store_article.py --src <unzipped folder(s)> --out data/raw_drops/offtake_fy26_clean
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import visit_cities as vc  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MON = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MONTHS = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25", "Sep'25", "Oct'25", "Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26"]
OUT_COLS = ["Unique Code", "Zone", "State", "City", "SO/ASE Emp Code", "SO/ASE Name", "Chain Name", "Store Type", "DC Code", "DC Name", "Internal Code", "Site Code", "Site Name",
            "Article", "Article_1", "EAN", "Chain Article Description", "Net Weight", "Description as per Fountain", "Brand", "Category", "Sub_category", "Range", "MRP", "Sales Qty",
            "MRP Sales Value", "NSV", "Per pc", "With Tax", "Margin", "Revised Month", "Month", "Year", "PPT Category"]
CANON = {"Unique": "Unique Code", "Yr": "Year", "MRP-2": "MRP 2"}
READ = ["Zone", "State", "City", "Chain Name", "Store Type", "Site Code", "Site Name", "Article", "EAN", "Chain Article Description", "Net Weight", "Description as per Fountain",
        "Brand", "Category", "Sub_category", "Range", "MRP", "Sales Qty", "MRP Sales Value", "NSV", "Month", "Year", "Source_Tab", "Month_Std", "PPT Category"]
TEXT = ["Zone", "State", "City", "Chain Name", "Store Type", "Site Code", "Site Name", "Article", "EAN", "Chain Article Description", "Net Weight", "Description as per Fountain",
        "Brand", "Category", "Sub_category", "Range", "PPT Category"]
NUM = ["MRP", "Sales Qty", "MRP Sales Value", "NSV"]


def month_of(folder: str):
    m = re.match(r"^([A-Za-z]{3})['\- ]*(\d{2})$", folder.strip())
    return (m.group(1).title(), 2000 + int(m.group(2))) if m else None


def read_file(path: Path, folder: str, qc: list):
    """One chain file -> DataFrame of the READ columns. Reads by header name; the Reliance Brand Counter block is re-aligned."""
    csv.field_size_limit(10**9)
    with path.open(encoding="utf-8-sig", errors="replace", newline="") as h:
        rd = csv.reader(h)
        head = [CANON.get(c.strip(), c.strip()) for c in next(rd)]
        n = len(head)
        rows, realigned, rejected = [], 0, 0
        for r in rd:
            if len(r) == n:
                rows.append(r)
            elif len(r) == n + 1 and head[0].startswith("Unnamed") and len(r) > 3 and str(r[-2]).startswith("Reliance_Brand"):
                x = dict(zip(head[1:26], r[:25]))
                x["Source_Tab"], x["Month_Std"] = r[-2], r[-1]
                rows.append([x.get(c, "") for c in head])
                realigned += 1
            else:
                rejected += 1
    d = pd.DataFrame(rows, columns=head)
    d = d.loc[:, ~d.columns.duplicated()]
    for c in READ:
        if c not in d:
            d[c] = None
    d = d[READ].replace("", None)
    d["folder"], d["file"] = folder, path.name
    if realigned:
        qc.append(("INFO", f"{path.name} {folder}: Brand Counter block re-aligned (leading column and two extra fields)", realigned, ""))
    if rejected:
        qc.append(("ERROR", f"{path.name} {folder}: rows with an unreadable field count (not loaded)", rejected, ""))
    return d


def tidy(s):
    return None if s is None or (isinstance(s, float) and pd.isna(s)) else re.sub(r"\s+", " ", str(s)).strip() or None


def mode_prefer(series):
    """Most frequent value; ties go to the one that is not ALL CAPS, then the longer one."""
    c = series.dropna().value_counts()
    if c.empty:
        return None
    top = c[c == c.iloc[0]].index.tolist()
    return sorted(top, key=lambda v: (v.isupper(), -len(v), v))[0]


def one_spelling(series):
    """Map every spelling that differs only by capitals to the most frequent one (ties: not ALL CAPS)."""
    s = series.dropna()
    best = s.groupby(s.str.lower()).agg(mode_prefer)
    return series.map(lambda v: best[v.lower()] if isinstance(v, str) else v)


def build(src_dirs, article_master, qc):
    frames = []
    for src in src_dirs:
        for f in sorted(Path(src).rglob("*.csv")):
            folder = f.parent.name
            if month_of(folder) is None:
                continue
            frames.append(read_file(f, folder, qc))
    a = pd.concat(frames, ignore_index=True)
    qc.append(("INFO", "rows read", len(a), f"{len(frames)} files"))
    for c in TEXT:
        a[c] = a[c].map(tidy)
    for c in NUM:
        a[c] = pd.to_numeric(a[c], errors="coerce")
    bad = a[NUM].isna().any(axis=1) & a["NSV"].isna()
    qc.append(("ERROR" if bad.any() else "PASS", "every row has a numeric NSV", int(bad.sum()), ""))
    for c in ("Sales Qty", "MRP Sales Value", "MRP"):
        a[c] = a[c].fillna(0.0)
    a = a[~bad].copy()
    a["ym"] = a["folder"].map(month_of)
    a["Month"] = a["ym"].map(lambda t: t[0])
    a["Year"] = a["ym"].map(lambda t: t[1])
    # month tags that disagree with the folder (reported, folder wins)
    tag = a["Month_Std"].map(lambda v: month_of(str(v)) if v else None)
    off = a[tag.notna() & (tag != a["ym"])]
    qc.append(("WARN" if len(off) else "PASS", "Month_Std tag disagrees with the folder (folder used)", len(off),
               "; ".join(f"{k[0]} {k[1]} tag {k[2]}" for k in off.groupby(["file", "folder", "Month_Std"]).size().index[:5])))
    # chain
    a["chain"] = a["Chain Name"].map(vc.std_chain)
    unknown = sorted(a.loc[a["chain"].isna(), "Chain Name"].dropna().unique())
    if unknown:
        raise SystemExit(f"chain spelling(s) not in CHAIN_STANDARD: {unknown} (add them on purpose in scripts/visit_cities.py)")
    a["bc"] = a["Store Type"].fillna("").str.lower().eq("brand counter")
    a.loc[a["bc"] & (a["chain"] == "Reliance Retail"), "chain"] = "Reliance Brand Counter"       # same chain name as this year's Brand Counter file
    # geography: one spelling
    a["Zone"] = a["Zone"].map(vc.norm_zone)
    stt = a["State"].map(lambda x: vc.std_state(x)[0] if x else None)
    unk = sorted(set(a.loc[stt.isna() & a["State"].notna(), "State"]))
    qc.append(("WARN" if unk else "PASS", "state names not in the standard list (kept as written)", len(unk), "; ".join(unk[:8])))
    a["State"] = one_spelling(stt.where(stt.notna(), a["State"]))
    a["City"] = one_spelling(a["City"].map(lambda c: c.title() if isinstance(c, str) and (c.isupper() or c.islower()) else c))
    # store identity (same rule as the current-year files)
    a["code"] = a["Site Code"].map(vc.norm_code)
    nocode = a["code"].isna()
    a["sid"] = a["chain"] + "|" + a["code"].fillna("")
    a.loc[nocode & a["Site Name"].notna(), "sid"] = a["chain"] + "|" + a["Site Name"]
    a.loc[nocode & a["Site Name"].isna() & a["City"].notna(), "sid"] = a["chain"] + "|" + a["City"]
    a.loc[nocode & a["Site Name"].isna() & a["City"].isna(), "sid"] = a["chain"] + "|NO-CITY|" + a["State"].fillna("")
    alias = vc.load_aliases()
    n_alias = int(a["sid"].isin(alias).sum())
    a["sid"] = a["sid"].map(lambda k: alias.get(k, k))
    qc.append(("INFO", "rows whose store key was merged into the store master's one store (aliases)", n_alias, ""))
    # one set of attributes per store: most frequent zone, state, city; the full (not truncated) name
    for col in ("Zone", "State", "City"):
        a[col] = a["sid"].map(a.dropna(subset=[col]).groupby("sid")[col].agg(mode_prefer))
    a["Zone"] = [vc.apply_zone_rules(s, c, z) for s, c, z in zip(a["State"], a["City"], a["Zone"])]      # owner's zone rules
    names = a.dropna(subset=["Site Name"]).groupby("sid")["Site Name"].agg(lambda s: list(s.value_counts().index))

    def full_name(lst):
        top = lst[0]
        longer = [n for n in lst if n.lower().startswith(top.lower()) and len(n) > len(top)]
        return mode_prefer(pd.Series(longer + [top])) if not longer else sorted(longer, key=len)[-1]
    a["Site Name"] = a["sid"].map(names.map(full_name))
    # the code of a coded store is the code in its key (after aliases); a store keyed by name or city has none
    coded = a[a["code"].notna() & (a["sid"] == a["chain"] + "|" + a["code"].fillna(""))].drop_duplicates("sid").set_index("sid")["code"]
    alias_code = {k: v.split("|", 1)[1] for k, v in alias.items() if v.split("|", 1)[1] and vc.norm_code(v.split("|", 1)[1]) == v.split("|", 1)[1] and "|NO-CITY" not in v}
    a["Site Code"] = a["sid"].map(coded)
    a.loc[a["Site Code"].isna(), "Site Code"] = a.loc[a["Site Code"].isna(), "sid"].map(lambda k: None)
    # articles: one set of attributes per EAN (this year's article master first), one EAN per chain article code
    a["EAN"] = a["EAN"].map(lambda e: re.sub(r"\.0+$", "", e) if isinstance(e, str) else e)
    a["Article"] = a["Article"].map(lambda e: re.sub(r"\.0+$", "", e) if isinstance(e, str) else e)
    sci = a["Article"].fillna("").str.contains(r"^\d+(?:\.\d+)?E\+\d+$", regex=True)
    qc.append(("INFO", "chain article codes written in Excel scientific notation (digits lost): blanked, then taken from another row of the same chain and EAN", int(sci.sum()), ""))
    a.loc[sci, "Article"] = None
    # an EAN that Excel turned into 8.90609E+12 has lost its digits: take the real EAN of the same chain article code, else of the same article name
    valid = a["EAN"].fillna("").str.fullmatch(r"\d{8,14}")
    broken = a["EAN"].notna() & ~valid
    by_art = a[valid & a["Article"].notna()].groupby(["chain", "Article"])["EAN"].agg(mode_prefer)
    by_name = a[valid & a["Description as per Fountain"].notna()].groupby("Description as per Fountain")["EAN"].agg(mode_prefer)
    fixed = [by_art.get((c, x)) or by_name.get(d) for c, x, d in zip(a.loc[broken, "chain"], a.loc[broken, "Article"], a.loc[broken, "Description as per Fountain"])]
    a.loc[broken, "EAN_fixed"] = fixed
    a["EAN_fixed"] = a.get("EAN_fixed")
    n_fixed = int(pd.Series(fixed, dtype=object).notna().sum()) if len(fixed) else 0
    qc.append(("INFO", "EANs written in Excel scientific notation (digits lost) repaired from the same article code or article name", n_fixed, f"of {int(broken.sum())}"))
    a.loc[broken, "EAN"] = a.loc[broken, "EAN_fixed"]
    left = a["EAN"].notna() & ~a["EAN"].fillna("").str.fullmatch(r"\d{8,14}")
    qc.append(("WARN" if left.any() else "PASS", "EANs still not a real EAN after the repair (kept by article code)", int(left.sum()), "; ".join(a.loc[left, "EAN"].unique()[:4])))
    a.loc[left, "EAN"] = None
    art_ean = a.dropna(subset=["EAN", "Article"]).groupby(["chain", "Article"])["EAN"].agg(mode_prefer)
    fix = a["EAN"].isna() & a["Article"].notna()
    a.loc[fix, "EAN"] = [art_ean.get((c, x)) for c, x in zip(a.loc[fix, "chain"], a.loc[fix, "Article"])]
    qc.append(("INFO", "rows with no EAN at all (kept, keyed by chain article code)", int(a["EAN"].isna().sum()), ""))
    attrs = ["Brand", "Category", "Sub_category", "Range", "Description as per Fountain", "Net Weight"]
    cur = pd.DataFrame()
    if article_master is not None:
        m = pd.read_csv(article_master, dtype=str, usecols=lambda c: c in ["EAN"] + attrs, low_memory=False)
        m["EAN"] = m["EAN"].map(lambda e: re.sub(r"\.0+$", "", e) if isinstance(e, str) else e)
        for c in attrs:
            m[c] = m[c].map(tidy)
        cur = m.dropna(subset=["EAN"]).groupby("EAN")[attrs].agg(mode_prefer)
    ly = a.dropna(subset=["EAN"]).groupby("EAN")[attrs].agg(mode_prefer)
    conflicts = {c: int((a.dropna(subset=["EAN", c]).groupby("EAN")[c].nunique() > 1).sum()) for c in attrs}
    for c in attrs:
        best = ly[c].copy()
        if len(cur):
            best.update(cur[c].dropna())
        a[c] = a["EAN"].map(best).where(a["EAN"].notna(), a[c])
    for c, n in conflicts.items():
        qc.append(("INFO", f"EANs that had more than one {c} (one now: this year's article master, else most frequent)", n, ""))
    top_art = a.dropna(subset=["Article", "EAN"]).groupby(["chain", "EAN"])["Article"].agg(mode_prefer)
    miss = a["Article"].isna() & a["EAN"].notna()
    a.loc[miss, "Article"] = [top_art.get((c, e)) for c, e in zip(a.loc[miss, "chain"], a.loc[miss, "EAN"])]
    qc.append(("INFO", "rows still without a chain article code (the EAN identifies the product)", int(a["Article"].isna().sum()), ""))
    a["Store Type"] = a["sid"].map(a.dropna(subset=["Store Type"]).groupby("sid")["Store Type"].agg(mode_prefer))
    a["PPT Category"] = a["EAN"].map(a.dropna(subset=["PPT Category", "EAN"]).groupby("EAN")["PPT Category"].agg(mode_prefer))
    a["Chain Article Description"] = a.groupby(["chain", "Article"])["Chain Article Description"].transform(lambda s: mode_prefer(s) if s.notna().any() else None)
    a["PPT Category"] = a["PPT Category"].where(a["PPT Category"].notna(), None)
    return a


def duplicate_lines(a):
    """Identical lines that carry a store identity: the signature of a double load. Reported, not removed."""
    cols = ["folder", "sid", "Article", "EAN", "Sales Qty", "MRP Sales Value", "NSV", "MRP"]
    ident = a["Site Code"].notna() | a["Site Name"].notna()
    d = a[ident & a.duplicated(cols, keep="first")]
    rep = d.groupby(["chain", "folder"]).agg(extra_lines=("NSV", "size"), nsv_in_extra_lines=("NSV", "sum")).reset_index()
    return rep


def consolidate(a):
    """One row per month x chain x store x product (EAN; the chain article code where there is no EAN). Lines are added; attributes are already one per store / per EAN."""
    a = a.copy()
    a["pkey"] = a["EAN"].fillna("ART:" + a["Article"].fillna("?"))
    top = a.groupby(["chain", "pkey"])["Article"].agg(mode_prefer)          # one chain article code per product (a chain can re-code a product)
    a["Article"] = [top.get((c, k)) for c, k in zip(a["chain"], a["pkey"])]
    first = ["Store Type", "Zone", "State", "City", "Site Code", "Site Name", "Article", "EAN", "Chain Article Description", "Net Weight", "Description as per Fountain",
             "Brand", "Category", "Sub_category", "Range", "PPT Category", "Month", "Year"]
    g = a.groupby(["folder", "chain", "sid", "pkey"], sort=True).agg(**{c: (c, "first") for c in first}, **{"Sales Qty": ("Sales Qty", "sum"),
        "MRP Sales Value": ("MRP Sales Value", "sum"), "NSV": ("NSV", "sum"), "lines": ("NSV", "size")}).reset_index()
    g["MRP"] = (g["MRP Sales Value"] / g["Sales Qty"].where(g["Sales Qty"] != 0)).round(2)
    return g


QC_DIR_HOLDER = []


def checks(a, c, qc):
    """Uniqueness and consistency of the CLEAN table."""
    def add(name, bad, example=""):
        qc.append(("PASS" if not bad else "ERROR", name, int(bad), example))
    k = ["folder", "sid", "EAN"]
    d = c[c["EAN"].notna() & c.duplicated(k, keep=False)]
    add("one row per month x chain x store x EAN", len(d), "; ".join(map(str, d[k].head(3).values.tolist())))
    k2 = ["folder", "sid", "Article"]
    e = c[c["EAN"].isna()]
    d = e[e.duplicated(k2, keep=False)]
    add("one row per month x chain x store x article code where there is no EAN", len(d))
    for col in ("Zone", "State", "City", "Site Name"):
        n = c.dropna(subset=[col]).groupby("sid")[col].nunique()
        add(f"one {col} per store", int((n > 1).sum()), "; ".join(n[n > 1].index[:3]))
    n = c.dropna(subset=["Site Code"]).groupby(["chain", "Site Code"])["sid"].nunique()
    add("one store key per chain x site code", int((n > 1).sum()))
    for col in ("Brand", "Category", "Sub_category", "Range", "Description as per Fountain"):
        n = c.dropna(subset=["EAN", col]).groupby("EAN")[col].nunique()
        add(f"one {col} per EAN", int((n > 1).sum()), "; ".join(n[n > 1].index[:3]))
    n = a.dropna(subset=["EAN", "Article"]).groupby(["chain", "folder", "Article"])["EAN"].nunique()
    conf = n[n > 1].reset_index()[["chain", "folder", "Article"]]
    qc.append(("WARN" if len(conf) else "PASS", "one chain article code points to two EANs in the same month (source conflict: each EAN keeps its own row, nothing is merged)", len(conf),
               "; ".join(f"{r.chain} {r.folder} {r.Article}" for r in conf.head(3).itertuples())))
    if QC_DIR_HOLDER:
        conf.to_csv(QC_DIR_HOLDER[0] / "offtake_fy26_article_code_conflicts.csv", index=False)
    n2 = a.dropna(subset=["EAN", "Article"]).groupby(["chain", "Article"])["EAN"].nunique()
    qc.append(("INFO", "chain article codes that point to more than one EAN across the year (the chain re-coded a product; each EAN keeps its own row)", int((n2 > 1).sum()), ""))
    for col in ("Zone", "State", "City"):
        low = c[col].dropna().drop_duplicates()
        add(f"{col} spelt one way (no capitals-only variants)", int(low.str.lower().duplicated().sum()), "; ".join(low[low.str.lower().duplicated(keep=False)].head(4)))
    add("input NSV = output NSV", int(abs(a["NSV"].sum() - c["NSV"].sum()) > 1e-6), f"{a['NSV'].sum():.6f} vs {c['NSV'].sum():.6f}")
    add("input quantity = output quantity", int(abs(a["Sales Qty"].sum() - c["Sales Qty"].sum()) > 1e-6))


def tie_out(c, ly_json, qc):
    mm = {m: f"{m.split(chr(39))[0]}-{m.split(chr(39))[1]}" for m in MONTHS}
    t = c[c["chain"] != "Reliance Brand Counter"].groupby(["chain", "folder"])["NSV"].sum().unstack().reindex(columns=MONTHS).rename(columns=mm)
    bc = c[c["chain"] == "Reliance Brand Counter"].groupby("folder")["NSV"].sum().reindex(MONTHS).rename(index=mm)
    ref = {}
    for k, v in json.loads(Path(ly_json).read_text(encoding="utf-8"))["by_chain"].items():
        ch = vc.std_chain(k) or k
        for m, x in v.items():
            ref.setdefault(ch, {})
            ref[ch][m] = ref[ch].get(m, 0) + (x or 0)
    r = pd.DataFrame(ref).T.reindex(columns=list(mm.values()))
    diff = (t.fillna(0) - r.reindex(t.index).fillna(0))
    worst = float(diff.abs().max().max())
    tot, rtot = float(t.sum().sum()), float(r.sum().sum())
    qc.append(("PASS" if worst <= 0.011 else "ERROR", "every chain x month NSV ties to data/raw_drops/_agg/offtake_fy26.json (within 0.01 L)", round(worst, 4), f"files {tot:.2f} L vs baseline {rtot:.2f} L"))
    ly = json.loads(Path(ly_json).read_text(encoding="utf-8"))
    bdiff = float(abs(bc.fillna(0).values - pd.Series(ly["bc_monthly"]).values).max())
    qc.append(("PASS" if bdiff <= 0.011 else "ERROR", "Brand Counter NSV by month ties to the baseline", round(bdiff, 4), ""))
    miss = [(ch, m) for ch in r.index for m in r.columns if (r.at[ch, m] or 0) > 0 and (ch not in t.index or pd.isna(t.at[ch, m]))]
    qc.append(("PASS" if not miss else "ERROR", "no chain x month with baseline sales is missing from the files", len(miss), str(miss[:3])))
    return t, r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, nargs="+", required=True, help="folder(s) holding <Mon'YY>/<chain>.csv (the unzipped files)")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "raw_drops" / "offtake_fy26_clean")
    ap.add_argument("--article-master", type=Path, default=vc.RAW / "offtake_store_article_Aug_26.csv", help="this year's file used for one article attribute set per EAN")
    ap.add_argument("--ly-json", type=Path, default=ROOT / "data" / "raw_drops" / "_agg" / "offtake_fy26.json")
    ap.add_argument("--qc-dir", type=Path, default=ROOT / "data" / "qc")
    ap.add_argument("--agg-dir", type=Path, default=ROOT / "data" / "offtake_fy26")
    a = ap.parse_args()
    qc = []
    a.qc_dir.mkdir(parents=True, exist_ok=True)
    QC_DIR_HOLDER[:] = [a.qc_dir]
    raw = build(a.src, a.article_master if a.article_master.exists() else None, qc)
    dup = duplicate_lines(raw)
    qc.append(("WARN" if len(dup) else "PASS", "identical lines with a store identity (suspected double loads): added into one row, NOT removed (they are in the FY26 baseline)",
               int(dup["extra_lines"].sum()), f"{dup['nsv_in_extra_lines'].sum():.2f} L"))
    c = consolidate(raw)
    qc.append(("INFO", "rows in -> rows out (one per month x chain x store x article)", len(raw), f"-> {len(c)} ({len(raw) - len(c)} repeated lines added into their row)"))
    checks(raw, c, qc)
    t, r = tie_out(c, a.ly_json, qc)
    # same store name + city under different codes (not merged: only the current store master's aliases are applied)
    nm = c[c["Site Name"].notna() & c["City"].notna()].drop_duplicates("sid")
    nm = nm.assign(k=nm["chain"] + "|" + nm["Site Name"].str.lower().str.replace(r"[^a-z0-9]", "", regex=True) + "|" + nm["City"].str.lower())
    qc.append(("WARN", "same chain + store name + city under different store keys in last year only (listed, not merged)", int(nm.duplicated("k").sum()), ""))
    errors = [x for x in qc if x[0] == "ERROR"]
    a.qc_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(qc, columns=["Severity", "Check", "Count", "Detail"]).to_csv(a.qc_dir / "offtake_fy26_QC.csv", index=False)
    for sev, name, n, ex in qc:
        print(f"[{sev}] {name}: {n}  {ex[:140]}")
    rep = raw.groupby(["chain", "folder"]).agg(rows_in=("NSV", "size"), nsv_in=("NSV", "sum"), negative_rows=("NSV", lambda s: int((s < 0).sum()))).join(
        c.groupby(["chain", "folder"]).agg(rows_out=("NSV", "size"), nsv_out=("NSV", "sum"))).reset_index()
    rep["lines_added_into_a_row"] = rep["rows_in"] - rep["rows_out"]
    rep.round(4).to_csv(a.qc_dir / "offtake_fy26_by_chain_month.csv", index=False)
    dup.round(4).to_csv(a.qc_dir / "offtake_fy26_duplicate_lines.csv", index=False)
    if errors:
        raise SystemExit(f"Not written: {len(errors)} QC error(s) above.")
    # store x month aggregate (tracked) and the clean monthly files (local)
    a.agg_dir.mkdir(parents=True, exist_ok=True)
    sm = c.groupby(["chain", "sid", "folder"]).agg(NSV=("NSV", "sum"), Units=("Sales Qty", "sum")).reset_index()
    sm["Month"] = sm["folder"]
    sm = sm.rename(columns={"chain": "Chain Name", "sid": "Store Key"})[["Store Key", "Chain Name", "Month", "NSV", "Units"]]
    sm.sort_values(["Chain Name", "Store Key", "Month"]).round(6).to_csv(a.agg_dir / "Store_Month_NSV_FY26.csv", index=False)
    a.out.mkdir(parents=True, exist_ok=True)
    for folder, g in c.groupby("folder"):
        mon, yr = month_of(folder)
        o = pd.DataFrame({
            "Unique Code": g["chain"] + (g["Site Code"].fillna("")), "Zone": g["Zone"], "State": g["State"], "City": g["City"], "SO/ASE Emp Code": None, "SO/ASE Name": None,
            "Chain Name": g["chain"], "Store Type": g["Store Type"], "DC Code": None, "DC Name": None, "Internal Code": None, "Site Code": g["Site Code"], "Site Name": g["Site Name"],
            "Article": g["Article"], "Article_1": g["Article"], "EAN": g["EAN"], "Chain Article Description": g["Chain Article Description"], "Net Weight": g["Net Weight"],
            "Description as per Fountain": g["Description as per Fountain"], "Brand": g["Brand"], "Category": g["Category"], "Sub_category": g["Sub_category"], "Range": g["Range"],
            "MRP": g["MRP"], "Sales Qty": g["Sales Qty"], "MRP Sales Value": g["MRP Sales Value"], "NSV": g["NSV"], "Per pc": None, "With Tax": None, "Margin": None,
            "Revised Month": None, "Month": mon, "Year": yr, "PPT Category": g["PPT Category"]})[OUT_COLS]
        o.to_csv(a.out / f"offtake_store_article_{mon}_{str(yr)[2:]}.csv", index=False)
    print(f"wrote {len(c):,} clean rows to {a.out}, the store x month aggregate to {a.agg_dir}, QC to {a.qc_dir}")


if __name__ == "__main__":
    main()
