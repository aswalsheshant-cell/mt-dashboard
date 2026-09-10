"""
Historical Primary chain-attribution backfill, Apr'25 -> Jul'26.

Scope: CHAIN attribution of Primary billing only (which chain a rupee of
Primary NSV belongs to). Does NOT touch article/EAN-level Primary-vs-Offtake
reconciliation -- that is a separate, still-BLOCKED problem (Primary's EAN
column has no stable common key with Offtake/Secondary) and is explicitly
out of scope for this module.

Evidence hierarchy (one rupee enters exactly one level, per month):

  Level 1   ACTUAL_CHAIN_PRIMARY
            Direct-billed rows. Chain comes from the row's own "Chain name"
            column (legacy + still-present schema, Apr'25-May'26). The
            locked schema (Jun'26-Jul'26) drops "Chain name" entirely, so
            those two months fall back to the pooled field (see Level 1.5)
            for Direct rows too -- there is no other field to use.

  Level 1.5 DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY
            Dist.-billed (distributor-pooled) rows where the pooled field
            ("Dist chain ten" in the legacy schema, renamed
            "Chain name for Dashboard" in the locked schema, confirmed the
            SAME field by row-level match -- see docs/HistoricalPrimaryBackfill.md
            Section 1) names exactly ONE chain (no "/" list): unambiguous by
            construction, no split decision needed.
            Excludes self-referential-fallback rows (pooled value merely
            echoes the row's own distributor name in specific months --
            Sep'25/Oct'25/some Jun'26 cases -- a data-population gap, not a
            genuine single-chain resolution) UNLESS that value is already a
            governed CHAIN_ALIASES entry (e.g. Sancus, whose own name is a
            real, stable chain identity).

  Level 2   PROVISIONAL_BUSINESS_MAPPED_PRIMARY
            Remaining multi-chain ("A/B/C") Dist. rows, split by the
            business-maintained Chain_Wise_Primary_Sale_2.xlsx Dump-sheet
            ratio (Distributor x Brand x Chain, same month). PENDING OWNER
            APPROVAL -- never reported as governed/actual.

  Level 3   SECONDARY_DERIVED_PRIMARY
            Secondary-ratio fallback, only where a Secondary source exists
            for that month (in this repo: none of Apr'25-Mar'26; only
            Apr'26-Aug'26 has the EAN-level hierarchy file).

  Level 4   UNALLOCATED_PRIMARY
            No evidence anywhere. Never guessed. Includes the explicit
            SOURCE_SCHEMA_ANOMALY bucket (May'26: 86 rows where PO Type
            itself is corrupted to an MTD-Sale-type value).

No source files are modified. No fuzzy matching. No new distributor aliases
beyond the reviewed DISTRIBUTOR_NAME_ALIAS already used for Aug'26
(aug26_data_readiness_gate.py) -- any unmatched distributor/chain is
reported, not silently guessed.

Usage:
    python scripts/historical_primary_chain_backfill.py --out-dir <dir>

Outputs (written under --out-dir, none of them committed to the repo --
see docs/HistoricalPrimaryBackfill.md "Regenerating the outputs"):
    Monthly_Reconciliation_Summary.csv   -- Section 7 table
    ChainArticle_FullDetail.csv          -- full row-level detail, all months
    Unallocated_Register.csv             -- Section 5 register
    Provenance.json                      -- SHA-256 fingerprints of every
                                             source file consumed + run metadata
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import aug26_data_readiness_gate as gate  # noqa: E402
import build_dashboard_data as bdd  # noqa: E402

REPO_ROOT = SCRIPT_DIR.parent

MONTH_TAGS = ["Apr_25", "May_25", "Jun_25", "Jul_25", "Aug_25", "Sep_25", "Oct_25",
              "Nov_25", "Dec_25", "Jan_26", "Feb_26", "Mar_26", "Apr_26", "May_26",
              "Jun_26", "Jul_26"]
MONTH_LABELS = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25", "Sep'25", "Oct'25",
                "Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26", "Apr'26", "May'26",
                "Jun'26", "Jul'26"]

MONTH_FULL_TO_ABBR = {"January": "Jan", "February": "Feb", "March": "Mar", "April": "Apr",
                       "May": "May", "June": "Jun", "July": "Jul", "August": "Aug",
                       "September": "Sep", "Sept": "Sep", "October": "Oct",
                       "November": "Nov", "December": "Dec"}

REQUIRED_PRIMARY_COLS = {"Month", "Ship To Name", "EAN No.", "brand", "Description",
                          "MTD-Sale type", "PO Type", "Inv. Net value(LOC)", "Inv Qty"}


def norm_month_label(x):
    """Workbook 'Month' strings (April'25, Sept'25, Jul'26, ...) -> canonical
    "Mon'YY" matching the primary_article file's own Month column format."""
    m = re.match(r"([A-Za-z]+)'(\d{2})", str(x).strip())
    if not m:
        return None
    name, yy = m.groups()
    abbr = MONTH_FULL_TO_ABBR.get(name, name[:3].title())
    return f"{abbr}'{yy}"


def sec_month_to_label(ym):
    y, m = str(ym).split("-")
    abbr = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(m)]
    return f"{abbr}'{y[2:]}"


def load_workbook_dump(path: Path) -> pd.DataFrame:
    """Load the frozen Dump-sheet snapshot (CSV, columns identical to the
    Chain_Wise_Primary_Sale_2.xlsx 'Dump' sheet). See docs/HistoricalPrimaryBackfill.md
    for how to regenerate this snapshot from a newer workbook."""
    dump = pd.read_csv(path)
    dump.columns = [str(c).strip() for c in dump.columns]
    dump = dump.dropna(how="all")
    dump["_month"] = dump["Month"].map(norm_month_label)
    dump["_brand"] = dump["Brand"].map(bdd.canon_brand)
    dump["_chain"] = dump["Chain Name"].map(bdd.canon_chain)
    dump["_distributor"] = dump["Bill to customer"].astype(str).str.strip()
    return dump


def load_secondary_hierarchy(path: Path):
    if not path.exists():
        return None
    sec = pd.read_csv(path, low_memory=False)
    sec["NSV_Value"] = pd.to_numeric(sec["NSV_Value"], errors="coerce").fillna(0.0)
    sec["_month"] = sec["Source_Month"].map(sec_month_to_label)
    sec["_brand"] = sec["Brand"].map(bdd.canon_brand)
    sec["_chain"] = sec["Chain"].map(bdd.canon_chain)
    sec["_distributor"] = sec["Distributor"].astype(str).str.strip()
    return sec


def process_month(primary_dir: Path, month_tag: str, month_label: str, dump: pd.DataFrame,
                   sec_hier):
    path = primary_dir / f"primary_article_{month_tag}.csv"
    if not path.exists():
        return None, [f"MISSING SOURCE FILE: {path.name}"], None

    fp = gate.fingerprint_file(str(path))
    df = pd.read_csv(path, low_memory=False)
    df.columns = [str(c).strip().strip("'") for c in df.columns]
    problems = []

    if "Dist chain ten" in df.columns:
        df["_pooled_chain"] = df["Dist chain ten"]
        schema = "legacy (Dist chain ten)"
    elif "Chain name for Dashboard" in df.columns:
        df["_pooled_chain"] = df["Chain name for Dashboard"]
        schema = "locked (Chain name for Dashboard)"
    else:
        return None, ["Neither 'Dist chain ten' nor 'Chain name for Dashboard' present"], fp

    missing = REQUIRED_PRIMARY_COLS - set(df.columns)
    if missing:
        return None, [f"Missing required columns: {sorted(missing)}"], fp

    df["Inv. Net value(LOC)"] = pd.to_numeric(df["Inv. Net value(LOC)"], errors="coerce")
    if df["Inv. Net value(LOC)"].isna().any():
        problems.append(f"{df['Inv. Net value(LOC)'].isna().sum()} rows failed numeric parse")
    df["Inv. Net value(LOC)"] = df["Inv. Net value(LOC)"].fillna(0.0)
    df = df[df["MTD-Sale type"] != "Cancel Invoice"].copy()

    actual_month_labels = df["Month"].dropna().unique().tolist()
    if month_label not in actual_month_labels:
        problems.append(f"Expected Month '{month_label}' not found in file (found {actual_month_labels})")

    df["_brand"] = df["brand"].map(bdd.canon_brand)
    df["_desc"] = df["Description"].map(gate.norm_desc)
    df["_distributor_raw"] = df["Ship To Name"].astype(str).str.strip()
    df["_distributor"] = df["_distributor_raw"].replace(gate.DISTRIBUTOR_NAME_ALIAS)

    wb_month = dump[dump["_month"] == month_label]
    wb_grp = wb_month.groupby(["_distributor", "_brand", "_chain"])["NSV"].sum().reset_index()
    wb_tot = wb_grp.groupby(["_distributor", "_brand"])["NSV"].sum().rename("tot").reset_index()
    wb_grp = wb_grp.merge(wb_tot, on=["_distributor", "_brand"])
    wb_grp["frac"] = wb_grp["NSV"] / wb_grp["tot"].replace(0, np.nan)
    wb_ratio = {k: list(zip(g["_chain"], g["frac"]))
                for k, g in wb_grp.groupby(["_distributor", "_brand"]) if g["tot"].iloc[0] != 0}

    art_ratio, db_ratio = {}, {}
    if sec_hier is not None:
        sec_m = sec_hier[sec_hier["_month"] == month_label]
        if len(sec_m):
            sec_m = sec_m.copy()
            sec_m["_desc"] = sec_m["Article"].map(gate.norm_desc)
            ag = sec_m.groupby(["_distributor", "_brand", "_desc", "_chain"])["NSV_Value"].sum().reset_index()
            at = ag.groupby(["_distributor", "_brand", "_desc"])["NSV_Value"].sum().rename("tot").reset_index()
            ag = ag.merge(at, on=["_distributor", "_brand", "_desc"])
            ag["frac"] = ag["NSV_Value"] / ag["tot"].replace(0, np.nan)
            art_ratio = {k: list(zip(g["_chain"], g["frac"]))
                         for k, g in ag.groupby(["_distributor", "_brand", "_desc"]) if g["tot"].iloc[0] > 0}
            dg = sec_m.groupby(["_distributor", "_brand", "_chain"])["NSV_Value"].sum().reset_index()
            dt = dg.groupby(["_distributor", "_brand"])["NSV_Value"].sum().rename("tot").reset_index()
            dg = dg.merge(dt, on=["_distributor", "_brand"])
            dg["frac"] = dg["NSV_Value"] / dg["tot"].replace(0, np.nan)
            db_ratio = {k: list(zip(g["_chain"], g["frac"]))
                        for k, g in dg.groupby(["_distributor", "_brand"]) if g["tot"].iloc[0] > 0}

    # Level 1 -- Direct rows use the row's own "Chain name" when present.
    # The locked schema (Jun'26-Jul'26) drops that column entirely, so those
    # two months have no choice but the pooled field. Using the pooled field
    # for Direct rows where "Chain name" IS available is wrong: verified
    # (Sep'25/Oct'25 D-Mart) that the pooled field can carry an unrelated
    # operational routing tag ("D-Mart-Offline"/"DC-D-Mart-Offline") on rows
    # whose "Chain name" is uniformly the real, governed "D-Mart" -- using
    # the pooled field there would fork one governed chain into a spurious
    # ungoverned bucket. See docs/HistoricalPrimaryBackfill.md Section 6.
    direct = df[df["PO Type"] == "Direct"].copy()
    if "Chain name" in df.columns:
        direct["Allocated_Chain"] = direct["Chain name"].map(bdd.canon_chain)
        direct["Mapping_Source"] = "Governed (Direct billing, unambiguous Ship-To=Chain via 'Chain name')"
    else:
        direct["Allocated_Chain"] = direct["_pooled_chain"].map(bdd.canon_chain)
        direct["Mapping_Source"] = f"Governed (Direct billing, {schema} -- no separate 'Chain name' column in this schema)"
    direct["Primary_Type"] = "ACTUAL_CHAIN_PRIMARY"

    # Data-quality exception -- PO Type holds an MTD-Sale-type value instead
    # of Direct/Dist. (found: May'26, 86 rows, all Reliance/Azorte). Never
    # inferred into Direct or Dist.; routed to UNALLOCATED_PRIMARY so the
    # total still ties exactly and the anomaly stays visible.
    other = df[~df["PO Type"].isin(["Direct", "Dist."])].copy()
    if len(other):
        other["Allocated_Chain"] = "UNALLOCATED_PRIMARY"
        other["Primary_Type"] = "UNALLOCATED_PRIMARY"
        other["Mapping_Source"] = other["PO Type"].map(
            lambda p: f"SOURCE_SCHEMA_ANOMALY: PO Type='{p}' (not Direct/Dist.) -- not auto-classified")
        problems.append(f"{len(other)} rows have PO Type outside {{Direct, Dist.}} "
                         f"(Rs{other['Inv. Net value(LOC)'].sum()/1e5:.4f}L) -- routed to UNALLOCATED_PRIMARY, not guessed")

    dist = df[df["PO Type"] == "Dist."].copy()
    out_rows = []
    for _, r in dist.iterrows():
        pooled = str(r["_pooled_chain"]).strip()
        is_single_value = bool(pooled) and pooled.lower() != "nan" and "/" not in pooled
        wb_key = (r["_distributor_raw"], r["_brand"])
        sec_key = (r["_distributor"], r["_brand"])
        art_key = (r["_distributor"], r["_brand"], r["_desc"])

        is_governed_alias = is_single_value and pooled.lower() in bdd._ALIAS_LOOKUP
        is_self_referential = is_single_value and not is_governed_alias and (
            pooled.lower() in r["_distributor_raw"].lower() or r["_distributor_raw"].lower() in pooled.lower())
        is_single_chain = is_single_value and not is_self_referential

        if is_single_chain:
            row = r.copy()
            row["Allocated_Chain"] = bdd.canon_chain(pooled)
            row["Primary_Type"] = "DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY"
            row["Mapping_Source"] = f"{schema}: single-chain value, unambiguous by construction"
            out_rows.append(row)
        elif wb_key in wb_ratio:
            for chain, frac in wb_ratio[wb_key]:
                row = r.copy()
                row["Allocated_Chain"] = chain
                row["Primary_Type"] = "PROVISIONAL_BUSINESS_MAPPED_PRIMARY"
                row["Mapping_Source"] = "Chain_Wise_Primary_Sale_2.xlsx (Dump) -- PENDING OWNER APPROVAL"
                row["Inv. Net value(LOC)"] = r["Inv. Net value(LOC)"] * frac
                out_rows.append(row)
        elif art_key in art_ratio:
            for chain, frac in art_ratio[art_key]:
                row = r.copy()
                row["Allocated_Chain"] = chain
                row["Primary_Type"] = "SECONDARY_DERIVED_PRIMARY"
                row["Mapping_Source"] = "Secondary, article-level ratio"
                row["Inv. Net value(LOC)"] = r["Inv. Net value(LOC)"] * frac
                out_rows.append(row)
        elif sec_key in db_ratio:
            for chain, frac in db_ratio[sec_key]:
                row = r.copy()
                row["Allocated_Chain"] = chain
                row["Primary_Type"] = "SECONDARY_DERIVED_PRIMARY"
                row["Mapping_Source"] = "Secondary, distributor-brand ratio"
                row["Inv. Net value(LOC)"] = r["Inv. Net value(LOC)"] * frac
                out_rows.append(row)
        else:
            row = r.copy()
            row["Allocated_Chain"] = "UNALLOCATED_PRIMARY"
            row["Primary_Type"] = "UNALLOCATED_PRIMARY"
            row["Mapping_Source"] = "MAPPING_NOT_FOUND: no workbook or Secondary evidence for this month"
            out_rows.append(row)

    dist_alloc = pd.DataFrame(out_rows) if out_rows else dist.iloc[0:0].copy()
    final = pd.concat([direct, other, dist_alloc], ignore_index=True, sort=False)

    diff = final["Inv. Net value(LOC)"].sum() - df["Inv. Net value(LOC)"].sum()
    if abs(diff) > 0.01:
        problems.append(f"RECONCILIATION FAILURE: diff={diff:.4f}")

    final["Month"] = month_label
    return final, problems, fp


def categorize_unallocated(mapping_source: str) -> str:
    if str(mapping_source).startswith("SOURCE_SCHEMA_ANOMALY"):
        return "SOURCE_SCHEMA_ANOMALY"
    if str(mapping_source).startswith("MAPPING_NOT_FOUND"):
        return "MAPPING_NOT_FOUND"
    return "OTHER"


def build_unallocated_register(combined: pd.DataFrame) -> pd.DataFrame:
    un = combined[combined["Primary_Type"] == "UNALLOCATED_PRIMARY"].copy()
    un["Category"] = un["Mapping_Source"].map(categorize_unallocated)
    reg = (un.groupby(["Month", "Ship To Name", "brand", "Category"])["Inv. Net value(LOC)"]
             .sum().div(1e5).round(4).reset_index()
             .rename(columns={"Ship To Name": "Distributor", "Inv. Net value(LOC)": "Value_L"}))
    reg["Levels_Attempted"] = reg["Category"].map({
        "SOURCE_SCHEMA_ANOMALY": "1 (Direct/Dist. undetermined -- no level applicable)",
        "MAPPING_NOT_FOUND": "1.5, 2, 3 (no single-chain value, no workbook row, no Secondary row)",
    }).fillna("1.5, 2, 3")
    reg["Source"] = reg["Category"].map({
        "SOURCE_SCHEMA_ANOMALY": "primary_article_<month>.csv, corrupted PO Type field",
        "MAPPING_NOT_FOUND": "primary_article_<month>.csv (no matching workbook/Secondary row)",
    }).fillna("primary_article_<month>.csv")
    reg["Recommended_Action"] = reg["Category"].map({
        "SOURCE_SCHEMA_ANOMALY": "Ask source owner to confirm true PO Type (Direct vs Dist.) for these invoices",
        "MAPPING_NOT_FOUND": "Add this Distributor x Brand x Chain split to the next workbook refresh",
    }).fillna("Review")
    return reg.sort_values(["Category", "Value_L"], ascending=[True, False])


def build_reconciliation_summary(all_frames, missing_month_rows) -> pd.DataFrame:
    rows = list(missing_month_rows)
    for final in all_frames:
        month_label = final["Month"].iloc[0]
        by_type = final.groupby("Primary_Type")["Inv. Net value(LOC)"].sum() / 1e5
        total = final["Inv. Net value(LOC)"].sum() / 1e5
        levels_sum = by_type.sum()
        rows.append(dict(
            Month=month_label,
            Raw_Primary_L=round(total, 4),
            Actual_L=round(by_type.get("ACTUAL_CHAIN_PRIMARY", 0.0), 4),
            DistChainTen_Single_L=round(by_type.get("DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY", 0.0), 4),
            Provisional_L=round(by_type.get("PROVISIONAL_BUSINESS_MAPPED_PRIMARY", 0.0), 4),
            Secondary_Derived_L=round(by_type.get("SECONDARY_DERIVED_PRIMARY", 0.0), 4),
            Unallocated_L=round(by_type.get("UNALLOCATED_PRIMARY", 0.0), 4),
            Reconciliation_Diff_L=round(levels_sum - total, 6),
            Status="PASS" if abs(levels_sum - total) < 0.0001 else "FAIL",
        ))
    df = pd.DataFrame(rows)
    order = {m: i for i, m in enumerate(MONTH_LABELS)}
    return df.sort_values("Month", key=lambda s: s.map(order)).reset_index(drop=True)


def run(primary_dir: Path, workbook_dump_csv: Path, secondary_hierarchy: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    dump = load_workbook_dump(workbook_dump_csv)
    sec_hier = load_secondary_hierarchy(secondary_hierarchy)

    fingerprints = {
        "workbook_dump_csv": gate.fingerprint_file(str(workbook_dump_csv)),
    }
    if secondary_hierarchy.exists():
        fingerprints["secondary_hierarchy"] = gate.fingerprint_file(str(secondary_hierarchy))

    all_frames = []
    missing_month_rows = []
    month_fingerprints = {}
    for tag, label in zip(MONTH_TAGS, MONTH_LABELS):
        final, problems, fp = process_month(primary_dir, tag, label, dump, sec_hier)
        if fp:
            month_fingerprints[label] = fp
        status = "OK" if (final is not None and not problems) else ("OK_WITH_WARNINGS" if final is not None else "FAILED")
        print(f"{label}: {status}" + (f"  ISSUES: {problems}" if problems else ""))
        if final is None:
            missing_month_rows.append(dict(Month=label, Raw_Primary_L=None, Actual_L=None,
                                            DistChainTen_Single_L=None, Provisional_L=None,
                                            Secondary_Derived_L=None, Unallocated_L=None,
                                            Reconciliation_Diff_L=None, Status=f"FAILED: {problems}"))
            continue
        all_frames.append(final)

    summary = build_reconciliation_summary(all_frames, missing_month_rows)
    summary.to_csv(out_dir / "Monthly_Reconciliation_Summary.csv", index=False)

    combined = pd.concat(all_frames, ignore_index=True, sort=False) if all_frames else pd.DataFrame()
    keep_cols = ["Month", "PO Type", "Ship To Name", "brand", "EAN No.", "Article Code",
                 "Description", "category", "sub_category", "range", "Inv Qty",
                 "Inv. Net value(LOC)", "Total MRP sales", "Zone", "State",
                 "Allocated_Chain", "Primary_Type", "Mapping_Source"]
    keep_cols = [c for c in dict.fromkeys(keep_cols) if c in combined.columns]
    combined[keep_cols].to_csv(out_dir / "ChainArticle_FullDetail.csv", index=False)

    register = build_unallocated_register(combined) if len(combined) else pd.DataFrame()
    register.to_csv(out_dir / "Unallocated_Register.csv", index=False)

    provenance = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "months_covered": MONTH_LABELS,
        "source_fingerprints": {"primary_article_files": month_fingerprints, **fingerprints},
        "total_rows_in_detail": int(len(combined)),
        "reconciliation": summary.to_dict(orient="records"),
    }
    with open(out_dir / "Provenance.json", "w") as f:
        json.dump(provenance, f, indent=2, default=str)

    print("\n=== RECONCILIATION SUMMARY ===")
    print(summary.to_string(index=False))
    n_fail = (summary["Status"] != "PASS").sum() if "Status" in summary.columns else 0
    print(f"\nWrote outputs to {out_dir}")
    if n_fail:
        print(f"\n{n_fail} month(s) NOT reconciled -- see Status column above.")
        return 1
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--primary-dir", type=Path,
                     default=REPO_ROOT / "PowerBI/RawDataFolders/Primary_Article_Monthly")
    ap.add_argument("--workbook-dump-csv", type=Path,
                     default=REPO_ROOT / "PowerBI/SeedData/Mapping/ChainWisePrimarySale_Dump_Snapshot.csv",
                     help="Frozen snapshot of the Chain_Wise_Primary_Sale_2.xlsx 'Dump' sheet")
    ap.add_argument("--secondary-hierarchy", type=Path,
                     default=REPO_ROOT / "PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_tot_hierarchy_Apr_Aug_2026.csv")
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT / "historical_primary_chain_backfill_output",
                     help="Output directory (gitignored -- not committed)")
    args = ap.parse_args()
    return run(args.primary_dir, args.workbook_dump_csv, args.secondary_hierarchy, args.out_dir)


if __name__ == "__main__":
    sys.exit(main())
