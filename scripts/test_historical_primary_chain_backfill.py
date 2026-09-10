"""
Regression / adversarial tests for the historical Primary chain backfill
(scripts/historical_primary_chain_backfill.py).

These are synthetic-data unit tests -- they build small in-memory DataFrames
shaped exactly like the real primary_article_<month>.csv schemas (both
vintages) and the workbook Dump-sheet snapshot, then call the module's own
functions. They do not read the real (multi-GB) source files, so they run
in seconds and can catch a regression before it reaches a real backfill.

Run: pytest scripts/test_historical_primary_chain_backfill.py -v
     (or: python -m pytest ... from the repo root)
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import historical_primary_chain_backfill as hpcb  # noqa: E402
import build_dashboard_data as bdd  # noqa: E402
import aug26_data_readiness_gate as gate  # noqa: E402


def _primary_row(**kw):
    base = dict(
        Month="Apr'25", **{"Ship To Name": "Az Enterprises(Apollo/More)Mt"},
        **{"EAN No.": "8901234567890"}, brand="MAMAEARTH",
        Description="MAMAEARTH SHAMPOO 200ML",
        **{"MTD-Sale type": "Sales"}, **{"PO Type": "Dist."},
        **{"Inv. Net value(LOC)": 1000.0}, **{"Inv Qty": 10},
        **{"Chain name": "Az Enterprises(Apollo/More)Mt"},
        **{"Dist chain ten": "Apollo/More Retails"},
    )
    base.update(kw)
    return base


def _make_primary_df(rows, locked_schema=False):
    df = pd.DataFrame(rows)
    if locked_schema:
        df = df.rename(columns={"Dist chain ten": "Chain name for Dashboard"})
        df = df.drop(columns=["Chain name"], errors="ignore")
    return df


def _empty_dump():
    cols = ["Month", "Bill to customer", "Brand", "Chain Name", "NSV",
            "_month", "_brand", "_chain", "_distributor"]
    return pd.DataFrame(columns=cols)


def _dump_with(rows):
    df = pd.DataFrame(rows)
    df["_month"] = df["Month"].map(hpcb.norm_month_label)
    df["_brand"] = df["Brand"].map(bdd.canon_brand)
    df["_chain"] = df["Chain Name"].map(bdd.canon_chain)
    df["_distributor"] = df["Bill to customer"].astype(str).str.strip()
    return df


def _process(df, dump=None, sec_hier=None, month_label="Apr'25", tmp_path=None):
    """Write df to a temp primary_article_<tag>.csv and run process_month."""
    tag = "Apr_25"
    p = tmp_path / f"primary_article_{tag}.csv"
    df.to_csv(p, index=False)
    final, problems, fp = hpcb.process_month(tmp_path, tag, month_label,
                                              dump if dump is not None else _empty_dump(),
                                              sec_hier)
    return final, problems


# ---------------------------------------------------------------------
# 1. Old schema (Dist chain ten)
# ---------------------------------------------------------------------
def test_legacy_schema_single_chain(tmp_path):
    df = _make_primary_df([_primary_row(**{"Dist chain ten": "Lulu"})])
    final, problems = _process(df, tmp_path=tmp_path)
    assert not problems
    assert final.iloc[0]["Primary_Type"] == "DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY"
    assert final.iloc[0]["Allocated_Chain"] == bdd.canon_chain("Lulu")


# ---------------------------------------------------------------------
# 2. New/locked schema (Chain name for Dashboard), no Chain name column
# ---------------------------------------------------------------------
def test_locked_schema_single_chain(tmp_path):
    df = _make_primary_df([_primary_row(**{"Dist chain ten": "Lulu"})], locked_schema=True)
    final, problems = _process(df, month_label="Apr'25", tmp_path=tmp_path)
    assert not problems
    assert final.iloc[0]["Primary_Type"] == "DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY"


def test_locked_schema_direct_row_uses_pooled_field(tmp_path):
    """Locked schema has no 'Chain name' -- Direct rows must fall back to the
    pooled field (there is no other data), and this must be visible in
    Mapping_Source, not silently blended with the governed-'Chain name' path."""
    df = _make_primary_df([_primary_row(**{"PO Type": "Direct", "Dist chain ten": "Lulu"})],
                           locked_schema=True)
    final, problems = _process(df, tmp_path=tmp_path)
    row = final.iloc[0]
    assert row["Primary_Type"] == "ACTUAL_CHAIN_PRIMARY"
    assert "no separate 'Chain name' column" in row["Mapping_Source"]
    assert row["Allocated_Chain"] == bdd.canon_chain("Lulu")


# ---------------------------------------------------------------------
# 3. Blank mapping value
# ---------------------------------------------------------------------
def test_blank_pooled_chain_falls_through_to_unallocated(tmp_path):
    df = _make_primary_df([_primary_row(**{"Dist chain ten": ""})])
    final, problems = _process(df, tmp_path=tmp_path)
    assert final.iloc[0]["Primary_Type"] == "UNALLOCATED_PRIMARY"
    assert final.iloc[0]["Allocated_Chain"] == "UNALLOCATED_PRIMARY"


# ---------------------------------------------------------------------
# 4. One-chain mapping (Level 1.5) vs 5. Multi-chain mapping (needs workbook)
# ---------------------------------------------------------------------
def test_multi_chain_value_requires_workbook(tmp_path):
    df = _make_primary_df([_primary_row(**{"Dist chain ten": "Apollo/Lulu/More Retails"})])
    # No workbook row for this distributor+brand+month -> UNALLOCATED, not guessed
    final, problems = _process(df, tmp_path=tmp_path)
    assert final.iloc[0]["Primary_Type"] == "UNALLOCATED_PRIMARY"
    assert "MAPPING_NOT_FOUND" in final.iloc[0]["Mapping_Source"]


def test_multi_chain_value_resolved_by_workbook(tmp_path):
    row = _primary_row(**{"Dist chain ten": "Apollo/Lulu/More Retails"})
    df = _make_primary_df([row])
    dump = _dump_with([
        dict(Month="Apr'25", **{"Bill to customer": row["Ship To Name"]}, Brand="MAMAEARTH",
             **{"Chain Name": "Apollo"}, NSV=600.0),
        dict(Month="Apr'25", **{"Bill to customer": row["Ship To Name"]}, Brand="MAMAEARTH",
             **{"Chain Name": "Lulu"}, NSV=400.0),
    ])
    final, problems = _process(df, dump=dump, tmp_path=tmp_path)
    assert not problems
    assert set(final["Primary_Type"]) == {"PROVISIONAL_BUSINESS_MAPPED_PRIMARY"}
    assert abs(final["Inv. Net value(LOC)"].sum() - row["Inv. Net value(LOC)"]) < 0.01
    assert len(final) == 2  # split into two chain rows


# ---------------------------------------------------------------------
# 6. Malformed PO Type / 7. Unknown PO Type -> SOURCE_SCHEMA_ANOMALY
# ---------------------------------------------------------------------
def test_malformed_po_type_is_source_schema_anomaly(tmp_path):
    df = _make_primary_df([_primary_row(**{"PO Type": "Sales"})])
    final, problems = _process(df, tmp_path=tmp_path)
    assert final.iloc[0]["Primary_Type"] == "UNALLOCATED_PRIMARY"
    assert "SOURCE_SCHEMA_ANOMALY" in final.iloc[0]["Mapping_Source"]
    assert any("PO Type outside" in p for p in problems)
    # total must still reconcile exactly
    assert abs(final["Inv. Net value(LOC)"].sum() - df["Inv. Net value(LOC)"].sum()) < 0.01


def test_unknown_po_type_never_inferred_as_direct_or_dist(tmp_path):
    df = _make_primary_df([_primary_row(**{"PO Type": "MRN"})])
    final, problems = _process(df, tmp_path=tmp_path)
    assert final.iloc[0]["Primary_Type"] == "UNALLOCATED_PRIMARY"


# ---------------------------------------------------------------------
# 8. Missing required column
# ---------------------------------------------------------------------
def test_missing_required_column_fails_cleanly(tmp_path):
    rows = [_primary_row()]
    df = pd.DataFrame(rows).drop(columns=["PO Type"])
    tag = "Apr_25"
    p = tmp_path / f"primary_article_{tag}.csv"
    df.to_csv(p, index=False)
    final, problems, fp = hpcb.process_month(tmp_path, tag, "Apr'25", _empty_dump(), None)
    assert final is None
    assert any("Missing required columns" in p for p in problems)


# ---------------------------------------------------------------------
# 9. Unknown distributor (no workbook/secondary evidence at all)
# ---------------------------------------------------------------------
def test_unknown_distributor_stays_unallocated(tmp_path):
    df = _make_primary_df([_primary_row(**{"Ship To Name": "Totally New Distributor Pvt Ltd",
                                            "Dist chain ten": "Apollo/Lulu"})])
    final, problems = _process(df, tmp_path=tmp_path)
    assert final.iloc[0]["Primary_Type"] == "UNALLOCATED_PRIMARY"


# ---------------------------------------------------------------------
# 10. Same distributor across different months (no cross-month leakage)
# ---------------------------------------------------------------------
def test_workbook_month_filter_is_exact(tmp_path):
    row = _primary_row(**{"Dist chain ten": "Apollo/Lulu"})
    df = _make_primary_df([row])
    # Workbook row exists but for a DIFFERENT month -- must not be used.
    dump = _dump_with([
        dict(Month="May'25", **{"Bill to customer": row["Ship To Name"]}, Brand="MAMAEARTH",
             **{"Chain Name": "Apollo"}, NSV=1000.0),
    ])
    final, problems = _process(df, dump=dump, month_label="Apr'25", tmp_path=tmp_path)
    assert final.iloc[0]["Primary_Type"] == "UNALLOCATED_PRIMARY"


# ---------------------------------------------------------------------
# 11. Same distributor mapped differently by month (each month independent)
# ---------------------------------------------------------------------
def test_same_distributor_different_workbook_split_by_month(tmp_path):
    row_apr = _primary_row(**{"Dist chain ten": "Apollo/Lulu"})
    row_may = dict(row_apr, Month="May'25")
    dump = _dump_with([
        dict(Month="Apr'25", **{"Bill to customer": row_apr["Ship To Name"]}, Brand="MAMAEARTH",
             **{"Chain Name": "Apollo"}, NSV=1000.0),
        dict(Month="May'25", **{"Bill to customer": row_apr["Ship To Name"]}, Brand="MAMAEARTH",
             **{"Chain Name": "Lulu"}, NSV=1000.0),
    ])
    final_apr, _ = _process(_make_primary_df([row_apr]), dump=dump, month_label="Apr'25", tmp_path=tmp_path)
    final_may, _ = _process(_make_primary_df([row_may]), dump=dump, month_label="May'25", tmp_path=tmp_path)
    assert final_apr.iloc[0]["Allocated_Chain"] == bdd.canon_chain("Apollo")
    assert final_may.iloc[0]["Allocated_Chain"] == bdd.canon_chain("Lulu")


# ---------------------------------------------------------------------
# 12. The Kottaram regression: alias applied for Secondary lookup must NOT
#     be applied before the workbook lookup (workbook uses the raw spelling)
# ---------------------------------------------------------------------
def test_kottaram_alias_ordering_regression(tmp_path):
    raw_name = "M/S KOTTARAM BUSINESS CORPORATION-MT"
    aliased_name = gate.DISTRIBUTOR_NAME_ALIAS[raw_name]
    assert aliased_name != raw_name  # sanity: alias table actually changes the spelling
    row = _primary_row(**{"Ship To Name": raw_name, "Dist chain ten": "Apollo/Lulu"})
    df = _make_primary_df([row])
    # Workbook carries the RAW (unaliased) spelling, as the real file does.
    dump = _dump_with([
        dict(Month="Apr'25", **{"Bill to customer": raw_name}, Brand="MAMAEARTH",
             **{"Chain Name": "Lulu"}, NSV=1000.0),
    ])
    final, problems = _process(df, dump=dump, tmp_path=tmp_path)
    assert not problems
    assert final.iloc[0]["Primary_Type"] == "PROVISIONAL_BUSINESS_MAPPED_PRIMARY"
    assert final.iloc[0]["Allocated_Chain"] == bdd.canon_chain("Lulu")


# ---------------------------------------------------------------------
# 13. Self-referential-fallback regression (Sep'25/Oct'25 data-quality gap)
# ---------------------------------------------------------------------
def test_self_referential_fallback_not_trusted_as_single_chain(tmp_path):
    dist_name = "G.V Enterprises"
    row = _primary_row(**{"Ship To Name": dist_name, "Dist chain ten": dist_name})
    df = _make_primary_df([row])
    final, problems = _process(df, tmp_path=tmp_path)
    # Must NOT be trusted as Level 1.5 -- falls through (no workbook row here -> unallocated)
    assert final.iloc[0]["Primary_Type"] != "DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY"


def test_governed_alias_self_name_is_trusted(tmp_path):
    """A governed CHAIN_ALIASES entry whose own name IS the chain (e.g. a
    self-named chain like Sancus) must still resolve at Level 1.5 even
    though it equals the distributor's own name."""
    governed_names = list(bdd._ALIAS_LOOKUP.keys())
    self_named = next((n for n in governed_names if bdd.canon_chain(n) and "/" not in n), None)
    assert self_named is not None, "expected at least one single-token governed alias in this repo's CHAIN_ALIASES"
    row = _primary_row(**{"Ship To Name": self_named, "Dist chain ten": self_named})
    df = _make_primary_df([row])
    final, problems = _process(df, tmp_path=tmp_path)
    assert final.iloc[0]["Primary_Type"] == "DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY"


# ---------------------------------------------------------------------
# 14. D-Mart-Offline handling: Direct rows must key off "Chain name", not
#     the pooled field, when "Chain name" is available.
# ---------------------------------------------------------------------
def test_direct_row_uses_chain_name_not_pooled_field(tmp_path):
    row = _primary_row(**{"PO Type": "Direct", "Chain name": "D-Mart",
                           "Dist chain ten": "D-Mart-Offline"})
    df = _make_primary_df([row])
    final, problems = _process(df, tmp_path=tmp_path)
    assert final.iloc[0]["Allocated_Chain"] == bdd.canon_chain("D-Mart")
    assert final.iloc[0]["Allocated_Chain"] != "D-Mart-Offline"


# ---------------------------------------------------------------------
# 15. No NaN/Infinity in output; 16. no silent row loss; 17. exact monthly
#     reconciliation across a small mixed batch
# ---------------------------------------------------------------------
def test_no_nan_infinity_and_exact_reconciliation(tmp_path):
    rows = [
        _primary_row(**{"PO Type": "Direct", "Chain name": "D-Mart", "Dist chain ten": "D-Mart"}),
        _primary_row(**{"PO Type": "Dist.", "Dist chain ten": "Lulu"}),
        _primary_row(**{"PO Type": "Dist.", "Dist chain ten": "Apollo/Lulu"}),
        _primary_row(**{"PO Type": "Sales"}),
    ]
    df = _make_primary_df(rows)
    final, problems = _process(df, tmp_path=tmp_path)
    assert not final["Inv. Net value(LOC)"].isna().any()
    assert not final["Inv. Net value(LOC)"].isin([float("inf"), float("-inf")]).any()
    assert len(final) >= len(rows)  # multi-chain rows can only grow the row count, never shrink it
    assert abs(final["Inv. Net value(LOC)"].sum() - df["Inv. Net value(LOC)"].sum()) < 0.01


def test_cancel_invoice_rows_excluded(tmp_path):
    rows = [
        _primary_row(**{"PO Type": "Direct", "Chain name": "D-Mart"}),
        _primary_row(**{"MTD-Sale type": "Cancel Invoice", "Inv. Net value(LOC)": 500.0}),
    ]
    df = _make_primary_df(rows)
    final, problems = _process(df, tmp_path=tmp_path)
    assert abs(final["Inv. Net value(LOC)"].sum() - rows[0]["Inv. Net value(LOC)"]) < 0.01


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
