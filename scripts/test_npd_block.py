"""Regression tests for npd_block() -- NPI launch governance, Chain x Article
grain, FY-based cohort with March carry-forward (replaces the March-only
rule confirmed 2026-09-14; see git history / this function's docstring).

Covers: cohort assignment (normal + March carry-forward), left-censoring
guard, per-chain independence, invalid-transaction exclusion (Qty<=0 or
NSV<=0 rows must never establish or move a launch), and the per-FY
metrics (launches, NSV, units, contribution %, active count,
productivity, YoY growth).
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
bd = importlib.import_module("build_dashboard_data")


def _row(chain, article, fy, month, nsv=100.0, qty=10.0):
    return {"Chain": chain, "Article": article, "FY": fy, "Month": month,
            "NSV": nsv, "Qty": qty}


def test_normal_launch_cohort_is_its_own_fy():
    # Earliest month is April (FY26) so it's censored; use May onward as the
    # "confirmed" launch to isolate the cohort-assignment behavior itself.
    rows = [
        _row("DMart", "A1", "FY26", "April"),   # establishes earliest (censored)
        _row("DMart", "A2", "FY26", "May"),     # genuine launch, not March
    ]
    npd = bd.npd_block(rows)
    assert npd["by_fy"]["FY26"][0]["chain"] == "DMart"
    assert npd["by_fy"]["FY26"][0]["article"] == "A2"
    assert npd["by_fy"]["FY26"][0]["actual_first_sale_month"] == "May"
    assert npd["by_fy"]["FY26"][0]["npi_cohort_fy"] == "FY26"


def test_march_launch_carries_forward_to_next_fy():
    rows = [
        _row("DMart", "A1", "FY26", "April"),      # censored anchor
        _row("Reliance Retail", "A2", "FY26", "March"),  # March launch
    ]
    npd = bd.npd_block(rows)
    row = npd["by_fy"]["FY27"][0]
    assert row["chain"] == "Reliance Retail"
    assert row["actual_first_sale_fy"] == "FY26"
    assert row["actual_first_sale_month"] == "March"
    assert row["npi_cohort_fy"] == "FY27"
    assert "FY26" not in npd["by_fy"] or all(
        r["article"] != "A2" for r in npd["by_fy"].get("FY26", [])
    )


def test_left_censored_pairs_excluded_from_launches():
    rows = [
        _row("DMart", "A1", "FY26", "April"),
        _row("Apollo", "A2", "FY26", "April"),
    ]
    npd = bd.npd_block(rows)
    assert npd["by_fy"] == {}
    assert npd["qc"]["pairs_excluded_left_censored"] == 2


def test_same_article_different_chains_are_independent_launches():
    rows = [
        _row("DMart", "A1", "FY26", "April"),           # censored anchor
        _row("Reliance Retail", "A9", "FY26", "March"),  # March @ Reliance
        _row("More Retail", "A9", "FY26", "May"),        # not March @ More Retail
    ]
    npd = bd.npd_block(rows)
    fy27_articles = {(r["chain"], r["article"]) for r in npd["by_fy"].get("FY27", [])}
    fy26_articles = {(r["chain"], r["article"]) for r in npd["by_fy"].get("FY26", [])}
    assert ("Reliance Retail", "A9") in fy27_articles
    assert ("More Retail", "A9") in fy26_articles


def test_zero_or_negative_qty_row_does_not_establish_launch():
    rows = [
        _row("DMart", "A1", "FY26", "April"),
        # A return / zero-value row in May must not count as the launch --
        # the real launch is June.
        _row("Apollo", "A2", "FY26", "May", nsv=-50.0, qty=-5.0),
        _row("Apollo", "A2", "FY26", "June", nsv=100.0, qty=10.0),
    ]
    npd = bd.npd_block(rows)
    row = [r for fy in npd["by_fy"].values() for r in fy if r["article"] == "A2"][0]
    assert row["actual_first_sale_month"] == "June"


def test_missing_identifier_rows_are_counted_and_skipped():
    rows = [
        _row("DMart", "A1", "FY26", "April"),
        {"Chain": None, "Article": None, "FY": "FY26", "Month": "May", "NSV": 50.0, "Qty": 5.0},
    ]
    npd = bd.npd_block(rows)
    assert npd["qc"]["rows_skipped_missing_chain_or_article"] == 1


def test_metrics_reconcile_to_raw_sums():
    rows = [
        _row("DMart", "A1", "FY26", "April"),             # censored anchor
        _row("Apollo", "A2", "FY26", "May", nsv=100.0, qty=10.0),
        _row("Apollo", "A2", "FY26", "June", nsv=50.0, qty=5.0),
        _row("Apollo", "A3", "FY26", "May", nsv=200.0, qty=20.0),
    ]
    npd = bd.npd_block(rows)
    m = npd["metrics_by_fy"]["FY26"]
    assert m["npi_launches"] == 2          # A2 and A3
    assert m["npi_nsv"] == 350.0           # 100+50+200
    assert m["npi_units"] == 35.0
    assert m["active_npi_count"] == 2
    assert m["avg_nsv_per_launch"] == 175.0
    assert m["npi_productivity"] == 175.0


def test_contribution_pct_uses_whole_fy_universe_not_just_npi():
    rows = [
        _row("DMart", "A0", "FY26", "April", nsv=900.0, qty=90.0),   # censored, but counts in FY total
        _row("Apollo", "A2", "FY26", "May", nsv=100.0, qty=10.0),
    ]
    npd = bd.npd_block(rows)
    # FY26 total NSV = 900 (censored A0) + 100 (NPI A2) = 1000; NPI share = 10%
    assert npd["metrics_by_fy"]["FY26"]["npi_contribution_pct"] == 10.0


def test_yoy_growth_present_from_second_cohort_fy_onward():
    rows = [
        _row("DMart", "A0", "FY26", "April"),
        _row("Apollo", "A2", "FY26", "May", nsv=100.0, qty=10.0),
        _row("Apollo", "A3", "FY27", "May", nsv=300.0, qty=30.0),
    ]
    npd = bd.npd_block(rows)
    assert npd["metrics_by_fy"]["FY26"]["yoy_npi_nsv_growth_pct"] is None
    assert npd["metrics_by_fy"]["FY27"]["yoy_npi_nsv_growth_pct"] == 200.0  # (300-100)/100*100


def test_empty_input_returns_none():
    assert bd.npd_block([]) is None
    assert bd.npd_block(None) is None


def test_real_data_shape_still_reconciles():
    """Sanity check against the real, checked-in dashboard/data.js: censored
    + all cohort counts must equal the total distinct Chain x Article pairs
    with a valid transaction."""
    import json
    import re
    data_js = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"
    if not data_js.exists():
        return
    txt = data_js.read_text(encoding="utf-8")
    m = re.search(r"window\.DASH\s*=\s*(\{.*\})\s*;?\s*$", txt, re.DOTALL)
    dash = json.loads(m.group(1))
    dr = dash.get("detail_records")
    if not dr:
        return
    npd = bd.npd_block(dr)
    total_launches = sum(npd["counts_by_fy"].values())
    total_pairs = {(r.get("Chain"), r.get("Article")) for r in dr
                   if (r.get("NSV") or 0) > 0 and (r.get("Qty") or 0) > 0
                   and r.get("Chain") and r.get("Article")}
    assert total_launches + npd["qc"]["pairs_excluded_left_censored"] == len(total_pairs)
