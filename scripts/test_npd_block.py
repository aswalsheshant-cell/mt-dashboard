"""Regression tests for npd_block() -- NPI launch governance, Chain x Article
grain, FY-based cohort with March carry-forward (replaces the March-only
rule confirmed 2026-09-14; see git history / this function's docstring).

Covers: cohort assignment (normal + March carry-forward), the
history-incomplete guard (formerly "left-censored" -- renamed for clarity;
see the function's own docstring for why), per-chain independence,
invalid-transaction exclusion (Qty<=0 or NSV<=0 rows must never establish
or move a launch), the per-FY metrics (launches, NSV, units,
contribution %, active count, productivity, YoY growth), history-coverage
classification, and the golden Chain x Article boundary-case table that is
this function's permanent specification -- change this table only with a
deliberate, reviewed business-rule change, never to make a refactor pass.
"""
import importlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
bd = importlib.import_module("build_dashboard_data")


def _row(chain, article, fy, month, nsv=100.0, qty=10.0):
    return {"Chain": chain, "Article": article, "FY": fy, "Month": month,
            "NSV": nsv, "Qty": qty}


# ── Golden boundary-case table -- the permanent specification ──────────────
# Every row's "historical transactions" all post-date a fixed anchor
# (DMart/ANCHOR, Apr-25/FY26 -- the dataset's earliest month) so none of
# them are themselves history-incomplete; that guard is tested separately.
_ANCHOR = _row("DMart", "ANCHOR", "FY26", "April")

_GOLDEN_CASES = [
    # (chain, article, transactions[(fy, month, nsv, qty)], expected_launch_fy,
    #  expected_launch_month, expected_cohort_fy)
    ("Reliance", "A", [("FY26", "March", 100, 10)], "FY26", "March", "FY27"),
    ("Reliance", "B", [("FY27", "April", 100, 10)], "FY27", "April", "FY27"),
    ("Reliance", "C", [("FY27", "Feb", 100, 10)], "FY27", "Feb", "FY27"),
    ("Reliance", "D", [("FY27", "March", 100, 10)], "FY27", "March", "FY28"),
    ("DMart", "A", [("FY27", "July", 100, 10)], "FY27", "July", "FY27"),
    # "Jan-26 sale, Jun-26 sale" as calendar dates: Jan-26 falls in FY26
    # (Apr'25-Mar'26), Jun-26 falls in FY27 (Apr'26-Mar'27) -- different FY
    # tags for the same calendar-chronological order the source table implies.
    ("Reliance", "E", [("FY26", "Jan", 100, 10), ("FY27", "June", 50, 5)], "FY26", "Jan", "FY26"),
    ("Reliance", "F", [("FY26", "March", -50, -5), ("FY27", "April", 100, 10)], "FY27", "April", "FY27"),
    ("Reliance", "G", [("FY26", "March", 0, 0), ("FY27", "May", 100, 10)], "FY27", "May", "FY27"),
]


@pytest.mark.parametrize(
    "chain,article,txns,exp_fy,exp_month,exp_cohort",
    _GOLDEN_CASES,
    ids=[f"{c[0]}-{c[1]}" for c in _GOLDEN_CASES],
)
def test_golden_boundary_table(chain, article, txns, exp_fy, exp_month, exp_cohort):
    rows = [_ANCHOR] + [_row(chain, article, fy, month, nsv, qty) for fy, month, nsv, qty in txns]
    npd = bd.npd_block(rows)
    matches = [r for fy_rows in npd["by_fy"].values() for r in fy_rows
               if r["chain"] == chain and r["article"] == article]
    assert len(matches) == 1, f"expected exactly one launch row for {chain}/{article}"
    row = matches[0]
    assert row["actual_first_sale_fy"] == exp_fy
    assert row["actual_first_sale_month"] == exp_month
    assert row["npi_cohort_fy"] == exp_cohort


def test_normal_launch_cohort_is_its_own_fy():
    # Earliest month is April (FY26) so it's history-incomplete; use May
    # onward as the confirmed launch to isolate cohort assignment itself.
    rows = [
        _row("DMart", "A1", "FY26", "April"),   # establishes earliest (history-incomplete)
        _row("DMart", "A2", "FY26", "May"),     # genuine launch, not March
    ]
    npd = bd.npd_block(rows)
    assert npd["by_fy"]["FY26"][0]["chain"] == "DMart"
    assert npd["by_fy"]["FY26"][0]["article"] == "A2"
    assert npd["by_fy"]["FY26"][0]["actual_first_sale_month"] == "May"
    assert npd["by_fy"]["FY26"][0]["npi_cohort_fy"] == "FY26"


def test_march_launch_carries_forward_to_next_fy():
    rows = [
        _row("DMart", "A1", "FY26", "April"),      # history-incomplete anchor
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


def test_history_incomplete_pairs_excluded_from_launches_but_not_lost():
    rows = [
        _row("DMart", "A1", "FY26", "April"),
        _row("Apollo", "A2", "FY26", "April"),
    ]
    npd = bd.npd_block(rows)
    assert npd["by_fy"] == {}
    assert npd["qc"]["pairs_excluded_history_incomplete"] == 2
    # NPI = Unknown, not NPI = No -- the pairs are reported, not discarded.
    assert len(npd["history_incomplete_pairs"]) == 2
    assert all(p["launch_status"] == "boundary_unknown" for p in npd["history_incomplete_pairs"])


def test_same_article_different_chains_are_independent_launches():
    rows = [
        _row("DMart", "A1", "FY26", "April"),           # history-incomplete anchor
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
        _row("DMart", "A1", "FY26", "April"),             # history-incomplete anchor
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
        _row("DMart", "A0", "FY26", "April", nsv=900.0, qty=90.0),   # history-incomplete, but counts in FY total
        _row("Apollo", "A2", "FY26", "May", nsv=100.0, qty=10.0),
    ]
    npd = bd.npd_block(rows)
    # FY26 total NSV = 900 (history-incomplete A0) + 100 (NPI A2) = 1000; NPI share = 10%
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


def test_launch_confirmation_status_is_per_pair_not_per_fy():
    # A launch's confidence depends on ITS OWN first-sale month's lookback,
    # not on which cohort FY it lands in. April-26 (12 months' lookback
    # behind Apr-25) is "confirmed"; May-25 (1 month's lookback) in the
    # SAME FY26 cohort is "observed_only".
    rows = [
        _row("DMart", "ANCHOR", "FY26", "April"),          # earliest, excluded
        _row("Apollo", "EARLY", "FY26", "May", nsv=100.0, qty=10.0),   # 1 month lookback
        _row("Apollo", "LATER", "FY27", "April", nsv=100.0, qty=10.0),  # 12 months lookback
    ]
    npd = bd.npd_block(rows)
    early = [r for fy in npd["by_fy"].values() for r in fy if r["article"] == "EARLY"][0]
    later = [r for fy in npd["by_fy"].values() for r in fy if r["article"] == "LATER"][0]
    assert early["history_months_before_first_sale"] == 1
    assert early["launch_confirmation_status"] == "observed_only"
    assert later["history_months_before_first_sale"] == 12
    assert later["launch_confirmation_status"] == "confirmed"


def test_march_carryforward_launch_keeps_its_own_lookback_not_cohort_fys():
    # A March-26 launch carries into the FY27 cohort, but its lookback is
    # measured from ITS OWN first-sale month (March-26), not from FY27's
    # own April start -- so it lands at 11 months, one short of "confirmed",
    # even though it's reported inside the FY27 cohort.
    rows = [
        _row("DMart", "ANCHOR", "FY26", "April"),
        _row("Reliance", "MARCH26", "FY26", "March", nsv=100.0, qty=10.0),
    ]
    npd = bd.npd_block(rows)
    row = npd["by_fy"]["FY27"][0]
    assert row["npi_cohort_fy"] == "FY27"
    assert row["history_months_before_first_sale"] == 11
    assert row["launch_confirmation_status"] == "observed_only"


def test_fy_coverage_is_partial_when_cohort_mixes_confirmed_and_observed_only():
    # FY27 contains BOTH an April-26 launch (12 months, confirmed) and a
    # March-26 carry-forward launch (11 months, observed_only) -- the
    # cohort as a whole must not be reported as CONFIRMED just because one
    # of its members clears the bar.
    rows = [
        _row("DMart", "ANCHOR", "FY26", "April"),
        _row("Reliance", "MARCH26", "FY26", "March", nsv=100.0, qty=10.0),   # -> FY27, observed_only
        _row("Apollo", "APR26", "FY27", "April", nsv=200.0, qty=20.0),        # -> FY27, confirmed
    ]
    npd = bd.npd_block(rows)
    m = npd["metrics_by_fy"]["FY27"]
    assert m["history_coverage"] == "PARTIAL"
    assert m["confirmed_launch_count"] == 1
    assert m["observed_only_launch_count"] == 1


def test_fy_coverage_confirmed_only_when_every_launch_clears_12_months():
    rows = [
        _row("DMart", "ANCHOR", "FY26", "April"),
        _row("Apollo", "APR26", "FY27", "April", nsv=200.0, qty=20.0),   # exactly 12 months, confirmed
    ]
    npd = bd.npd_block(rows)
    assert npd["metrics_by_fy"]["FY27"]["history_coverage"] == "CONFIRMED"
    assert npd["metrics_by_fy"]["FY27"]["observed_only_launch_count"] == 0


def test_yoy_comparison_flagged_invalid_when_either_side_not_confirmed():
    # FY26's only launch is observed_only (1 month lookback) -> FY27's YoY
    # vs FY26 must be flagged, not presented as a confirmed comparison.
    rows = [
        _row("DMart", "A0", "FY26", "April"),
        _row("Apollo", "A2", "FY26", "May", nsv=100.0, qty=10.0),
        _row("Apollo", "A3", "FY27", "April", nsv=300.0, qty=30.0),
    ]
    npd = bd.npd_block(rows)
    assert npd["metrics_by_fy"]["FY27"]["yoy_comparison_valid"] is False
    assert npd["metrics_by_fy"]["FY27"]["yoy_caveat"] is not None
    assert "FY26" in npd["metrics_by_fy"]["FY27"]["yoy_caveat"]


def test_active_count_never_exceeds_launch_count():
    rows = [
        _row("DMart", "A0", "FY26", "April"),
        _row("Apollo", "A2", "FY26", "May", nsv=100.0, qty=10.0),
        # A3 launches in FY26 but has no NSV in its own cohort FY (e.g.
        # discontinued immediately) -- must count as a launch but not active.
        _row("Apollo", "A3", "FY26", "June", nsv=0.0, qty=0.0),
    ]
    npd = bd.npd_block(rows)
    m = npd["metrics_by_fy"]["FY26"]
    assert m["active_npi_count"] <= m["npi_launches"]


def test_no_pair_appears_in_two_cohorts():
    rows = [
        _row("DMart", "A0", "FY26", "April"),
        _row("Reliance", "X", "FY26", "March"),   # -> FY27 cohort
        _row("Reliance", "X", "FY27", "August"),  # same pair, later sale -- must not create a 2nd launch
    ]
    npd = bd.npd_block(rows)
    hits = [r for fy_rows in npd["by_fy"].values() for r in fy_rows
            if r["chain"] == "Reliance" and r["article"] == "X"]
    assert len(hits) == 1


def test_empty_input_returns_none():
    assert bd.npd_block([]) is None
    assert bd.npd_block(None) is None


def test_real_data_shape_still_reconciles():
    """Sanity check against the real, checked-in dashboard/data.js:
    history-incomplete + all cohort counts must equal the total distinct
    Chain x Article pairs with a valid transaction."""
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
    assert total_launches + npd["qc"]["pairs_excluded_history_incomplete"] == len(total_pairs)
    # Every displayed metric must reconcile to its own formula, on the real data.
    for fy, m in npd["metrics_by_fy"].items():
        if m["npi_launches"]:
            assert m["avg_nsv_per_launch"] == round(m["npi_nsv"] / m["npi_launches"], 2)
        if m["active_npi_count"]:
            assert m["npi_productivity"] == round(m["npi_nsv"] / m["active_npi_count"], 2)
        assert m["active_npi_count"] <= m["npi_launches"]
