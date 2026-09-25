"""Edge-case regression tests for the Account/Chain YoY fields added to
same_period_block() and threaded through scorecard_block() (PR #167).

Governance principle under test: a missing prior-year base, a missing
current-period value, or a zero denominator must NEVER be silently read as
a genuine 0% or -100% growth number. Each case below is a synthetic frame
built to isolate exactly one edge condition.
"""
import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
bd = importlib.import_module("build_dashboard_data")


def _frame(rows):
    """rows: list of (fy, month, chain, brand, nsv, qty)."""
    return pd.DataFrame(rows, columns=["_FY", "_M", "_Chain", "_Brand", "_NSV", "_Qty"])


def _row(block, dim, name):
    rows = {r["name"]: r for r in block[dim]}
    assert name in rows, f"{name!r} missing from {dim}: {list(rows)}"
    return rows[name]


class TestNewAccountNoPriorBase:
    """A chain with sales this period but none last period must be flagged
    NEW_ACCOUNT, never given a fabricated growth number."""

    def test_new_account_flagged_not_computed_as_growth(self):
        df = _frame([
            ("FY26", "April", "DMart", "Mamaearth", 100.0, 10),
            ("FY26", "April", "Reliance Retail", "Mamaearth", 50.0, 5),
            ("FY27", "April", "DMart", "Mamaearth", 120.0, 12),
            ("FY27", "April", "Reliance Retail", "Mamaearth", 60.0, 6),
            ("FY27", "April", "NewChain", "Mamaearth", 30.0, 3),
        ])
        sp = bd.same_period_block(df)
        row = _row(sp, "by_chain", "NewChain")
        assert row["prev"] == 0
        assert row["curr"] == 30.0
        assert row["comparability"] == "NEW_ACCOUNT"
        # A real prior-year base of 0 must not produce a growth percentage --
        # there is nothing to grow FROM.
        assert row["yoy_pct"] is None
        assert row["qty_yoy_pct"] is None


class TestExitedAccount:
    """A chain present last period but absent this period must be flagged
    EXITED. Unlike NEW_ACCOUNT (no valid prior base to divide by), going
    from a real prior value to zero IS a well-defined -100% -- that number
    is accurate, not fabricated, so it is shown. The EXITED flag is what
    disambiguates it from an ongoing, still-trading decline; hiding the
    number would lose real information (a full account loss reads very
    differently from a -100% single-month dip)."""

    def test_exited_account_flagged_and_shows_true_minus_100(self):
        df = _frame([
            ("FY26", "April", "DMart", "Mamaearth", 100.0, 10),
            ("FY26", "April", "OldChain", "Mamaearth", 40.0, 4),
            ("FY27", "April", "DMart", "Mamaearth", 120.0, 12),
        ])
        sp = bd.same_period_block(df)
        row = _row(sp, "by_chain", "OldChain")
        assert row["curr"] == 0
        assert row["prev"] == 40.0
        assert row["comparability"] == "EXITED"
        assert row["yoy_pct"] == -100.0
        assert row["qty_yoy_pct"] == -100.0


class TestComparableAccount:
    """The normal case: both periods have real sales -- growth IS computed,
    and units/value are independent of each other."""

    def test_comparable_account_computes_growth(self):
        df = _frame([
            ("FY26", "April", "DMart", "Mamaearth", 100.0, 10),
            ("FY27", "April", "DMart", "Mamaearth", 150.0, 10),  # value up, units flat
        ])
        sp = bd.same_period_block(df)
        row = _row(sp, "by_chain", "DMart")
        assert row["comparability"] == "COMPARABLE"
        assert row["yoy_pct"] == 50.0
        assert row["qty_yoy_pct"] == 0.0   # units unchanged despite value +50%
        assert row["nsv_contribution_pct"] == 100.0  # only chain this period


class TestZeroTotalDenominator:
    """If the whole current-period total is zero (should not happen in real
    data, but the function must not divide by zero), contribution_pct must
    come back None, not a crash or a fabricated number."""

    def test_zero_current_total_gives_none_contribution(self):
        df = _frame([
            ("FY26", "April", "DMart", "Mamaearth", 100.0, 10),
            ("FY27", "April", "DMart", "Mamaearth", 0.0, 0),
        ])
        sp = bd.same_period_block(df)
        row = _row(sp, "by_chain", "DMart")
        assert row["nsv_contribution_pct"] is None
        assert row["comparability"] == "EXITED"


class TestNegativeValues:
    """A chain with net negative NSV this period (heavy returns/credit notes)
    must still classify and compute without raising, and must not be
    silently treated as 'no data' (comparability logic must key off
    presence relative to zero, not truthiness). The resulting yoy_pct is
    a real (if unusual) number -- below -100%, since it fell past zero
    into net returns -- not suppressed, same reasoning as TestExitedAccount."""

    def test_negative_current_value_still_classified(self):
        df = _frame([
            ("FY26", "April", "DMart", "Mamaearth", 100.0, 10),
            ("FY27", "April", "DMart", "Mamaearth", -5.0, -1),
        ])
        sp = bd.same_period_block(df)
        row = _row(sp, "by_chain", "DMart")
        # curr <= 0 and prev > 0 -> EXITED under the current (a>0,b>0)/(a>0,b<=0)/
        # (a<=0,b>0)/else rule; a net-negative period is treated the same as
        # "nothing sold" for comparability purposes, not silently as COMPARABLE.
        assert row["comparability"] == "EXITED"
        assert row["yoy_pct"] == -105.0
        assert row["qty_yoy_pct"] == -110.0


class TestBrandOnlyInOnePeriod:
    """by_brand (new in this PR) must apply the identical governance rules
    as by_chain/by_zone -- it is not a second, looser implementation."""

    def test_brand_only_in_current_period(self):
        df = _frame([
            ("FY26", "April", "DMart", "Mamaearth", 100.0, 10),
            ("FY27", "April", "DMart", "Mamaearth", 100.0, 10),
            ("FY27", "April", "DMart", "NewBrand", 20.0, 2),
        ])
        sp = bd.same_period_block(df)
        assert "by_brand" in sp
        row = _row(sp, "by_brand", "NewBrand")
        assert row["comparability"] == "NEW_ACCOUNT"
        assert row["yoy_pct"] is None


class TestContributionReconciliation:
    """Contribution percentages across every chain in the current period
    must sum to exactly 100% -- it is a share of the same total by
    construction, not an independently-estimated figure."""

    def test_contributions_sum_to_100(self):
        df = _frame([
            ("FY26", "April", "DMart", "Mamaearth", 100.0, 10),
            ("FY26", "April", "Reliance Retail", "Mamaearth", 50.0, 5),
            ("FY27", "April", "DMart", "Mamaearth", 120.0, 12),
            ("FY27", "April", "Reliance Retail", "Mamaearth", 60.0, 6),
            ("FY27", "April", "Apollo", "Mamaearth", 20.0, 2),
        ])
        sp = bd.same_period_block(df)
        total_contrib = sum(r["nsv_contribution_pct"] for r in sp["by_chain"])
        assert abs(total_contrib - 100.0) < 1e-6, (
            f"contributions summed to {total_contrib}, expected exactly 100"
        )


class TestScorecardThreadsFieldsThrough:
    """scorecard_block() must carry the new fields on its own rows without
    disturbing its existing target/RAG/action fields."""

    def test_scorecard_rows_carry_new_fields_and_keep_old_ones(self):
        df = _frame([
            ("FY26", "April", "DMart", "Mamaearth", 100.0, 10),
            ("FY27", "April", "DMart", "Mamaearth", 150.0, 12),
            ("FY27", "April", "NewChain", "Mamaearth", 30.0, 3),
        ])
        sp = bd.same_period_block(df)
        sc = bd.scorecard_block(sp, targets=None, cfg={}, dim="by_chain")
        rows = {r["name"]: r for r in sc["rows"]}
        assert rows["DMart"]["qty_yoy_pct"] == 20.0
        assert rows["DMart"]["nsv_contribution_pct"] is not None
        assert rows["DMart"]["comparability"] == "COMPARABLE"
        # Existing fields (present before this PR) must still be there.
        assert "growth_pct" in rows["DMart"]
        assert "action" in rows["DMart"]
        assert rows["NewChain"]["comparability"] == "NEW_ACCOUNT"
        assert rows["NewChain"]["growth_pct"] is None
