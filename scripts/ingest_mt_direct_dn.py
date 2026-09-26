#!/usr/bin/env python3
"""Load the MT Direct debit-note (DN) claim register into PL_Expense_Input.csv.

Input: the Finance DN register workbook (e.g. MT-DN_1.xlsx), Sheet1 -- one row per
DN: Pertain to FY, Code, Expense Related to Month, DN Receipt Date, Doc Date,
Channel, Customer Name, DN No, Base Amount, GST, Gross Amount, Narration,
Expense Types. Source workbooks stay outside Git; only the aggregated rows land
in the seed file.

Rules (registered as `mt_direct_dn_claims` in config/data_source_registry.yml):
  * Business date = "Expense Related to Month" (the claim period), never the DN
    receipt/doc date. FY comes from that month by THE ONE FY RULE -- the
    workbook's own "Pertain to FY" column is not trusted (14 rows in the
    2026-09-26 file say 2025-26 for May-Aug 2026 claims).
  * Amount = Base Amount (excl. GST), in INR Lakh (CM2 formula decision D2).
  * Exact duplicate rows (every column identical) are dropped and reported.
  * Only Channel == "MT Direct" is loaded. Other channels (the file's Nykaa
    rows are "GT_ e B2B", customer 1103979 = EB2B in the customer master) are
    reported and held out, not loaded.
  * Chain comes from the confirmed customer master
    (SeedData/Mapping/CustomerCode_Zone_State_Mapping.csv) where the code is
    there, else the workbook's customer name as given -- never a guess; a name
    the pipeline cannot resolve shows as unmapped in the CM2 QC.
  * Grain written: Month x FY x Customer Code x Expense Head.
  * Idempotent: rows whose Source starts with SOURCE_TAG are replaced, every
    other row (including the template EXAMPLE rows) is kept byte-for-byte.

Usage:
    python scripts/ingest_mt_direct_dn.py --src "D:/sALES & eXPENSES/MT-DN_1.xlsx" --dry-run
    python scripts/ingest_mt_direct_dn.py --src "D:/sALES & eXPENSES/MT-DN_1.xlsx"
Then refresh CM2: python scripts/build_dashboard_data.py --detail-only --src <dir> --out dashboard/data.js
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
EXPENSE_CSV = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"
CUST_MASTER = ROOT / "PowerBI" / "SeedData" / "Mapping" / "CustomerCode_Zone_State_Mapping.csv"
SOURCE_TAG = "MT Direct DN register"
COLS = ["FY_src", "Code", "ExpMonth", "DN_Receipt", "DocDate", "Channel", "Customer",
        "DN_No", "Base", "GST", "Gross", "Narration", "ExpType"]
# Expense Head / Expense Type per DN expense type. Fixed vs Variable follows the
# template's own examples (Visibility Spend = Fixed, Scheme / Trade Spend = Variable).
HEADS = {
    "promotion": ("Promotion", "Variable"),
    "visiblity": ("Visibility", "Fixed"),
    "visibility": ("Visibility", "Fixed"),
    "off-invoice": ("Off-Invoice", "Variable"),
    "listing fees": ("Listing Fees", "Fixed"),
    "extra-margin": ("Extra Margin", "Variable"),
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def fy_span(d: dt.date) -> str:
    """THE ONE FY RULE, written in the template's 'FYyy-yy' form (Apr-26 -> FY26-27)."""
    end = d.year + 1 if d.month >= 4 else d.year
    return f"FY{(end - 1) % 100:02d}-{end % 100:02d}"


def read_register(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name="Sheet1", header=None)
    hits = raw.index[raw[0].astype(str).str.strip().str.startswith("Pertain")]
    if len(hits) == 0:
        raise SystemExit(f"ERROR: no 'Pertain to FY' header row in Sheet1 of {path}")
    df = raw.iloc[hits[0] + 1:].reset_index(drop=True)
    if df.shape[1] != len(COLS):
        raise SystemExit(f"ERROR: expected {len(COLS)} columns, found {df.shape[1]}")
    df.columns = COLS
    df = df[df["Base"].notna()].copy()
    df["ExpMonth"] = pd.to_datetime(df["ExpMonth"], errors="raise")
    df["Base"] = df["Base"].astype(float)
    df["DN_No"] = df["DN_No"].astype(str)
    df["Code"] = df["Code"].astype("int64").astype(str)
    return df


def customer_master() -> dict:
    """Code -> {account, channel} for Confirmed rows only."""
    out = {}
    with open(CUST_MASTER, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            code = (r.get("Customer Code") or "").strip()
            if code.isdigit() and (r.get("Validation Status") or "").strip() == "Confirmed":
                out.setdefault(code, {"account": (r.get("Account") or "").strip(),
                                      "channel": (r.get("Channel") or "").strip()})
    return out


def primary_chains() -> set:
    """Chains present in the article-level Primary detail of the committed data.js."""
    from json_boundary import parse_window_dash_strict
    dash = parse_window_dash_strict((ROOT / "dashboard" / "data.js").read_text(encoding="utf-8"))
    return {r["Chain"] for r in dash.get("detail_records", []) if r.get("Chain")}


def resolve_chain(name: str, m: dict | None, canon, known: set) -> tuple[str, bool]:
    """The chain name the CM2 loader will resolve, and whether it resolves. Tries the
    DN's own customer name, then the Confirmed master account (MT channel only)."""
    cands = [name]
    if m and m["channel"] == "MT" and m["account"]:
        cands.append(m["account"].replace("(Ho)", "").replace("(HO)", "").strip())
    for c in cands:
        if canon(c) in known:
            return canon(c), True
    return name, False


def build_rows(df: pd.DataFrame, today: str):
    report = {"rows_in": len(df), "base_in_lakh": round(df["Base"].sum() / 1e5, 2)}
    dups = df[df.duplicated(keep="first")]
    df = df.drop_duplicates()
    report.update(duplicate_rows_dropped=len(dups), duplicate_value_lakh=round(dups["Base"].sum() / 1e5, 2))
    held = df[df["Channel"].str.strip() != "MT Direct"]
    report["held_out_non_mt_direct"] = {
        f"{c} / {ch}": round(v / 1e5, 2)
        for (c, ch), v in held.groupby(["Customer", "Channel"])["Base"].sum().items()}
    df = df[df["Channel"].str.strip() == "MT Direct"].copy()
    unknown = sorted(set(df["ExpType"].str.strip().str.lower()) - set(HEADS))
    if unknown:
        raise SystemExit(f"ERROR: unknown Expense Types {unknown} -- add them to HEADS first")
    fy_label_mismatch = df[df["ExpMonth"].apply(lambda d: fy_span(d.date())[2:].replace("-", "")[2:])
                           != df["FY_src"].astype(str).str[-2:]]
    report["fy_label_overridden_rows"] = len(fy_label_mismatch)
    master = customer_master()
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_dashboard_data import canon_chain
    known = primary_chains()
    unresolved = {}
    df["Head"], df["Type"] = zip(*df["ExpType"].str.strip().str.lower().map(HEADS))
    rows = []
    for (month, code, head, etype), g in df.groupby(["ExpMonth", "Code", "Head", "Type"]):
        name = g["Customer"].iloc[0].strip()
        m = master.get(code)
        chain, ok = resolve_chain(name, m, canon_chain, known)
        if not ok:
            unresolved[f"{name} ({code})"] = unresolved.get(f"{name} ({code})", 0) + float(g["Base"].sum()) / 1e5
        rows.append({
            "Month": MONTHS[month.month - 1], "FY": fy_span(month.date()), "Chain": chain,
            "Customer Code": code, "Customer Name": name, "Zone": "", "State": "",
            "Brand": "", "Category": "", "Sub Category": "",
            "Expense Head": head, "Expense Type": etype,
            "Expense Amount (INR Lakh)": f"{g['Base'].sum() / 1e5:.4f}",
            "Remarks": f"{len(g)} DN(s), base excl. GST (GST {g['GST'].astype(float).sum() / 1e5:.4f} L held separately)"
                       + ("" if ok else "; chain not resolved to a Primary chain -- shows as unmapped in CM2 QC"),
            "Source": f"{SOURCE_TAG} ({month:%b-%y})",
            "Updated By": "MT Analytics", "Updated Date": today,
        })
    report["unresolved_chain_lakh"] = {k: round(v, 2) for k, v in unresolved.items()}
    report.update(rows_out=len(rows), mt_direct_base_lakh=round(df["Base"].sum() / 1e5, 2),
                  written_lakh=round(sum(float(r["Expense Amount (INR Lakh)"]) for r in rows), 2))
    return rows, report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    a = ap.parse_args()
    new_rows, report = build_rows(read_register(Path(a.src)), a.today)
    # Existing lines are copied byte-for-byte (the file is CRLF and its template
    # rows use their own quoting); only lines this script wrote are replaced.
    text = EXPENSE_CSV.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)
    if lines and lines[-1] == "":
        lines.pop()
    header = next(csv.reader([lines[0]]))
    src_idx = header.index("Source")

    def is_ours(line: str) -> bool:
        fields = next(csv.reader([line]), [])
        return len(fields) > src_idx and fields[src_idx].startswith(SOURCE_TAG)

    kept = [lines[0]] + [ln for ln in lines[1:] if not is_ours(ln)]
    report.update(existing_rows_kept=len(kept) - 1, existing_dn_rows_replaced=len(lines) - len(kept))
    for k, v in report.items():
        print(f"  {k}: {v}")
    if a.dry_run:
        print("DRY RUN -- nothing written")
        return 0
    buf = io.StringIO()
    csv.DictWriter(buf, fieldnames=header, lineterminator=eol).writerows(new_rows)
    EXPENSE_CSV.write_bytes((eol.join(kept) + eol + buf.getvalue()).encode("utf-8"))
    print(f"wrote {len(kept) - 1 + len(new_rows)} rows to {EXPENSE_CSV.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
