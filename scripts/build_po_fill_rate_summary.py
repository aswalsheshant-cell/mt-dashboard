#!/usr/bin/env python3
"""PO received vs PO billed -> monthly Fill Rate summary (and PO demand vs FY27 target).

Source: SAP "PO vs Billing" sales-order extract, one row per sales-order (SO) line
(SO Qty = quantity the customer ordered, Invoice Qty = quantity billed against it).
The raw extract is customer-level and stays OUTSIDE Git (the repository is public;
docs/DATA_SECURITY_CLASSIFICATION.md). Only the aggregated outputs below are
committed, with the SHA-256 of every raw part recorded so the summary can be rebuilt.

    python scripts/build_po_fill_rate_summary.py \
        --src "/path/outside/repo/PO_VS_Billing_FR_*_part_*.csv"

Rules (each one checked against the Apr'25-Sep'26 extract, 2026-10-01):
  1. Business date = SO Date (order date). The file's own "Month" column is the
     extract month; 3,389 rows are open orders repeated in the next month's extract.
  2. Carry-over: the same SO line (SO No + Article + Item cat + SO Qty + SO Net Value
     + SO Time) in two extracts is ONE line. The latest extract's row is kept: it
     carries the billing (the earlier row always shows 0 billed, never more), so no
     billed quantity is lost and no PO quantity is counted twice. The same holds for
     a line repeated inside one extract with a status update: the billed row is kept.
  3. Exact duplicate rows inside one extract are counted once (logged in the QC file).
  4. Months after --max-month are dropped (default Aug-26): September data is not
     stored in this repository. Nothing is read from a dropped extract.
  5. Fill rate uses billable lines only (Item cat ZDM1). Free goods (ZFOC) are kept
     out of the rate and reported in the QC file.
  6. Chain = governed canon_chain() from build_dashboard_data.py. A distributor that
     the resolver does not map stays under its own name with Chain_Resolved = N --
     never guessed onto a chain.
  7. Unbilled lines: the Apr-Dec'25 extracts write Invoice Qty = 0, the Jan'26+
     extracts leave the same cells blank (49,297 lines); no extract mixes the two and
     the blank lines carry rejection reasons. So a blank is read as "not billed" ONLY
     inside an extract that has no explicit 0 -- an extract that mixes both stops the
     build (the meaning would no longer be provable). Counts are logged in the QC file.
  8. Column swap: the whole Dec'25 extract (25,460 rows) has Article and Customer No
     swapped (7-digit customer code under Article, 8-digit article under Customer No).
     Those rows are swapped back only when every one of them passes both checks: its
     EAN maps (on clean rows) to the article now under Customer No, and the code under
     Article is that customer's own code on clean rows. Any failure stops the build.
  9. Missing is never zero elsewhere: a slice with no PO qty has a blank fill rate.

This file measures FILL RATE only. It cannot measure OTIF: the extract has no
requested delivery date and no delivered date (docs/METRIC_REGISTRY.md PO_FILL_RATE).
"""
import argparse
import glob
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from build_dashboard_data import _ALIAS_LOOKUP, canon_chain, fy_tag_from_ym  # noqa: E402  governed helpers

GOVERNED_CHAINS = set(_ALIAS_LOOKUP.values())          # chain names the governed resolver can return

OUT_DIR = ROOT / "PowerBI" / "SeedData" / "Forecast"
TARGETS = ROOT / "PowerBI" / "SeedData" / "Targets" / "FY2627_Targets.csv"
LINE_KEY = ["SO No.", "Article", "Item cat", "SO Qty", "SO Net Value", "SO Time"]
NUM_COLS = ["SO Qty", "SO Net Value", "Invoice Qty", "NET Value"]
MON = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
       "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
MON_LBL = {v: k.title() for k, v in MON.items()}


def extract_month(label: str) -> pd.Timestamp:
    """The file's Month column, e.g. "April'25" / "Sept'25" / "Apr'26" -> first day of month."""
    name, yy = str(label).split("'")
    return pd.Timestamp(2000 + int(yy), MON[name[:3].lower()], 1)


def month_label(ts: pd.Timestamp) -> str:
    return f"{MON_LBL[ts.month]}-{ts.year % 100:02d}"            # Apr-25, same style as data.js


def load(paths):
    parts, fingerprints = [], []
    for p in paths:
        fingerprints.append({"file": Path(p).name, "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest()})
        parts.append(pd.read_csv(p, dtype=str, encoding="utf-8-sig"))
    cols = list(parts[0].columns)
    if any(list(d.columns) != cols for d in parts):
        raise SystemExit("parts do not share one column layout -- stop, do not merge them")
    df = pd.concat(parts, ignore_index=True)
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c].str.replace(",", ""), errors="coerce")
    return df, fingerprints


def fix_swapped_columns(df, qc):
    """Rule 8: swap Article / Customer No back on rows where the extract swapped them."""
    sw = (df["Article"].str.len() == 7) & (df["Customer No"].str.len() == 8)
    if sw.any():
        clean = df[~sw]
        ean_to_article = clean.groupby("EAN No.")["Article"].agg(lambda s: s.mode().iat[0])
        codes_by_customer = clean.groupby("Customer Name")["Customer No"].agg(set)
        rows = df[sw]
        ean_ok = rows["EAN No."].map(ean_to_article).eq(rows["Customer No"])
        cust_ok = [a in codes_by_customer.get(n, set()) for a, n in zip(rows["Article"], rows["Customer Name"])]
        if not (ean_ok.all() and all(cust_ok)):
            raise SystemExit("Article/Customer No look swapped but the EAN/customer cross-check fails -- stop")
        df.loc[sw, ["Article", "Customer No"]] = df.loc[sw, ["Customer No", "Article"]].values
    qc["article_customer_swap_fixed_rows"] = int(sw.sum())
    qc["article_customer_swap_extracts"] = sorted(set(df.loc[sw, "Month"]))
    return df


def build(df: pd.DataFrame, max_month: pd.Timestamp):
    qc = {"rows_read": int(len(df))}
    df = fix_swapped_columns(df, qc)
    df["Extract_Month"] = df["Month"].map(extract_month)
    df["SO_Month"] = pd.to_datetime(df["SO Date"], format="%d-%m-%Y", errors="coerce").dt.to_period("M").dt.to_timestamp()
    if df["SO_Month"].isna().any() or df[["SO Qty", "SO Net Value"]].isna().any().any():
        raise SystemExit("unparseable SO Date, SO Qty or SO Net Value -- stop and fix the source")
    # Rule 7: blank Invoice Qty means "not billed" only in extracts that never write an explicit 0.
    blank, zero = df["Invoice Qty"].isna(), df["Invoice Qty"].eq(0)
    mixed = sorted(set(df.loc[blank, "Month"]) & set(df.loc[zero, "Month"]))
    if mixed:
        raise SystemExit(f"extract(s) {mixed} have both blank and 0 Invoice Qty -- meaning of blank unproven, stop")
    if (blank & df["NET Value"].notna()).any() or (df["NET Value"].isna() & ~blank).any():
        raise SystemExit("Invoice Qty and NET Value are not blank together -- stop and check the source")
    qc["blank_invoice_lines_read_as_not_billed"] = int(blank.sum())
    qc["blank_invoice_extracts"] = sorted(set(df.loc[blank, "Month"]), key=extract_month)
    df[["Invoice Qty", "NET Value"]] = df[["Invoice Qty", "NET Value"]].fillna(0.0)

    late = df["Extract_Month"] > max_month
    qc["rows_dropped_after_max_month"] = int(late.sum())            # e.g. every Sep-26 extract row
    df = df[~late]

    n = len(df)
    df = df.drop_duplicates()
    qc["exact_duplicate_rows_removed"] = n - len(df)

    n = len(df)
    # Rule 2: latest extract wins; inside one extract the billed row wins over the
    # unbilled repeat of the same line (255 such pairs, never both billed).
    df = df.sort_values(["Extract_Month", "Invoice Qty"], kind="stable").drop_duplicates(LINE_KEY, keep="last")
    qc["carry_over_rows_merged"] = n - len(df)
    df = df[df["SO_Month"] <= max_month]

    foc = df["Item cat"] == "ZFOC"
    qc["free_goods_lines_excluded"] = int(foc.sum())
    qc["free_goods_qty_excluded"] = float(df.loc[foc, "SO Qty"].sum())
    df = df[~foc].copy()

    df["Chain_Raw"] = df["Chain"].str.strip()
    df["Chain"] = df["Chain_Raw"].map(canon_chain)
    df["Chain_Resolved"] = df["Chain"].isin(GOVERNED_CHAINS).map({True: "Y", False: "N"})
    df["Month"] = df["SO_Month"].map(month_label)
    df["FY"] = df["SO_Month"].map(lambda t: fy_tag_from_ym(t.year, t.month))
    df["Channel"] = df["Chanel"].str.strip()
    df["Line_Full"] = df["Invoice Qty"] >= df["SO Qty"]
    df["Line_Zero"] = df["Invoice Qty"] <= 0
    df["Unfilled_Qty"] = (df["SO Qty"] - df["Invoice Qty"]).clip(lower=0)
    df["Unfilled_Value"] = (df["SO Net Value"] - df["NET Value"]).clip(lower=0)
    df["Reason"] = df["Reason for Rejection Desc"].fillna("").str.strip().replace("", "No reason recorded")
    qc["lines_kept"] = int(len(df))
    return df, qc


def summarise(df):
    dims = ["Month", "FY", "Channel", "Customer Group Desc", "Zone", "Chain", "Chain_Raw", "Chain_Resolved", "Brand", "Category"]
    g = df.groupby(dims, dropna=False, sort=True).agg(
        SO_Lines=("SO Qty", "size"), Lines_Fully_Billed=("Line_Full", "sum"), Lines_Not_Billed=("Line_Zero", "sum"),
        PO_Qty=("SO Qty", "sum"), Billed_Qty=("Invoice Qty", "sum"),
        PO_Value_L=("SO Net Value", lambda s: s.sum() / 1e5), Billed_Value_L=("NET Value", lambda s: s.sum() / 1e5),
    ).reset_index().rename(columns={"Customer Group Desc": "Customer_Group"})
    g["FR_Qty_Pct"] = (g["Billed_Qty"] / g["PO_Qty"] * 100).where(g["PO_Qty"] > 0)          # blank, never 0, when no PO
    g["FR_Value_Pct"] = (g["Billed_Value_L"] / g["PO_Value_L"] * 100).where(g["PO_Value_L"] > 0)
    for c in ("PO_Value_L", "Billed_Value_L"):
        g[c] = g[c].round(4)
    for c in ("FR_Qty_Pct", "FR_Value_Pct"):
        g[c] = g[c].round(2)
    unf = df[df["Unfilled_Qty"] > 0]
    r = unf.groupby(["Month", "FY", "Channel", "Chain", "Chain_Resolved", "Reason"], sort=True).agg(
        SO_Lines=("SO Qty", "size"), Unfilled_Qty=("Unfilled_Qty", "sum"),
        Unfilled_Value_L=("Unfilled_Value", lambda s: round(s.sum() / 1e5, 4))).reset_index()
    return g, r


def po_vs_target(df):
    """PO demand vs the FY27 monthly business target, total level only (the target has no split)."""
    t = pd.read_csv(TARGETS)
    t["Month"] = pd.to_datetime(t["MonthStart"]).map(month_label)
    m = df.groupby("Month").agg(PO_Value_All_L=("SO Net Value", "sum"), Billed_Value_All_L=("NET Value", "sum"))
    mt = df[df["Channel"] == "MT"].groupby("Month").agg(PO_Value_MT_L=("SO Net Value", "sum"), Billed_Value_MT_L=("NET Value", "sum"))
    out = t[["Month", "FY Year", "Target NSV Cr"]].merge((m.join(mt) / 1e5).reset_index(), on="Month", how="inner")
    out["Target_L"] = out.pop("Target NSV Cr") * 100
    for basis in ("All", "MT"):
        po = out[f"PO_Value_{basis}_L"]
        out[f"PO_vs_Target_{basis}_Pct"] = (po / out["Target_L"] * 100).round(2)
        out[f"Abs_Error_{basis}_Pct"] = ((po - out["Target_L"]).abs() / po * 100).round(2)   # error vs actual demand
    return out.round(4)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="glob of the raw parts (keep them outside the repo)")
    ap.add_argument("--max-month", default="2026-08", help="last SO/extract month to keep (YYYY-MM)")
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    a = ap.parse_args(argv)
    paths = sorted(glob.glob(a.src))
    if not paths:
        raise SystemExit(f"no files match {a.src}")
    if any(Path(p).resolve().is_relative_to(ROOT) for p in paths):
        raise SystemExit("raw PO extract must stay outside the repository (customer-level data, public repo)")
    raw, prints = load(paths)
    raw_tot = {c: float(raw[c].sum()) for c in NUM_COLS}
    df, qc = build(raw, pd.Timestamp(a.max_month + "-01"))
    fr, reasons = summarise(df)
    tgt = po_vs_target(df)
    a.out_dir.mkdir(parents=True, exist_ok=True)
    first, last = df["SO_Month"].min(), df["SO_Month"].max()
    tag = f"{MON_LBL[first.month]}{first.year % 100}_to_{MON_LBL[last.month]}{last.year % 100}"
    fr.to_csv(a.out_dir / f"PO_Fill_Rate_Monthly_{tag}.csv", index=False)
    reasons.to_csv(a.out_dir / f"PO_Unfilled_Reasons_Monthly_{tag}.csv", index=False)
    tgt.to_csv(a.out_dir / "PO_vs_Target_Monthly_FY27.csv", index=False)
    month_tot = fr.groupby("Month", sort=False)[["PO_Qty", "Billed_Qty", "PO_Value_L", "Billed_Value_L"]].sum()
    qc.update({
        "source_parts": prints, "raw_totals_all_rows": raw_tot,
        "months_kept": [month_label(m) for m in sorted(df["SO_Month"].unique())],
        "summary_totals": {k: round(float(v), 4) for k, v in fr[["PO_Qty", "Billed_Qty", "PO_Value_L", "Billed_Value_L"]].sum().items()},
        "lines_check": {"summary_lines": int(fr["SO_Lines"].sum()), "lines_kept": qc["lines_kept"]},
        "fr_qty_pct_overall": round(float(fr["Billed_Qty"].sum() / fr["PO_Qty"].sum() * 100), 2),
        "fr_value_pct_overall": round(float(fr["Billed_Value_L"].sum() / fr["PO_Value_L"].sum() * 100), 2),
        "unresolved_chain_po_value_L": round(float(fr.loc[fr["Chain_Resolved"] == "N", "PO_Value_L"].sum()), 4),
        "month_totals": {m: {k: round(float(v), 4) for k, v in r.items()} for m, r in month_tot.iterrows()},
        "not_measurable": "OTIF / on-time: the extract has no requested-delivery or delivered date.",
    })
    (a.out_dir / "PO_Fill_Rate_QC.json").write_text(json.dumps(qc, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in qc.items() if k not in ("source_parts", "month_totals")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
