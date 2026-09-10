"""
Regression tests for scripts/mapping_approval_compression.py, following the
mapping-approval-governor skill contract: never fabricate a decision, never
broaden across a real conflict, always reconcile exactly.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mapping_approval_compression as mac  # noqa: E402


def _detail(rows):
    return pd.DataFrame(rows, columns=["Month", "Distributor", "Brand", "Chain", "Value_L"])


def test_single_stable_chain_collapses_to_one_rule():
    d = _detail([
        ["Apr'25", "D1", "B1", "Lulu", 10.0],
        ["May'25", "D1", "B1", "Lulu", 12.0],
        ["Jun'25", "D1", "B1", "Lulu", 8.0],
    ])
    rules, exc = mac.compress(d)
    assert len(rules) == 1
    assert len(exc) == 0
    assert rules.iloc[0]["Proposed_Chain"] == "Lulu"
    assert abs(rules.iloc[0]["Value_L"] - 30.0) < 0.01


def test_stable_multi_chain_split_collapses_to_one_rule_with_breakdown():
    d = _detail([
        ["Apr'25", "D1", "B1", "Apollo", 60.0], ["Apr'25", "D1", "B1", "Lulu", 40.0],
        ["May'25", "D1", "B1", "Apollo", 55.0], ["May'25", "D1", "B1", "Lulu", 45.0],
        ["Jun'25", "D1", "B1", "Apollo", 65.0], ["Jun'25", "D1", "B1", "Lulu", 35.0],
    ])
    rules, exc = mac.compress(d)
    assert len(rules) == 1
    assert len(exc) == 0
    assert "Apollo" in rules.iloc[0]["Proposed_Chain"] and "Lulu" in rules.iloc[0]["Proposed_Chain"]
    assert abs(rules.iloc[0]["Value_L"] - 300.0) < 0.01


def test_genuine_chain_swap_becomes_exception_not_a_broadened_rule():
    """Chain composition genuinely changes (Apollo drops out, DMart takes
    over) -- must never be folded into one rule by majority."""
    d = _detail([
        ["Apr'25", "D1", "B1", "Apollo", 100.0],
        ["May'25", "D1", "B1", "Apollo", 100.0],
        ["Jun'25", "D1", "B1", "DMart", 100.0],
        ["Jul'25", "D1", "B1", "DMart", 100.0],
    ])
    rules, exc = mac.compress(d)
    assert len(rules) == 0
    assert len(exc) == 1
    assert exc.iloc[0]["Decision_Type"] == "OWNER_ROW_EXCEPTION"
    assert abs(exc.iloc[0]["Value_L"] - 400.0) < 0.01


def test_small_one_off_chain_folded_as_residual_not_a_separate_exception():
    """A tiny one-month appearance of a different chain (well under the
    residual materiality floor) should not blow up an otherwise-stable rule
    into an exception -- but it must still be disclosed and still counted in
    the rule's total value."""
    d = _detail([
        ["Apr'25", "D1", "B1", "Lulu", 100.0],
        ["May'25", "D1", "B1", "Lulu", 100.0],
        ["Jun'25", "D1", "B1", "Lulu", 100.0],
        ["Jun'25", "D1", "B1", "Spencer", 1.0],  # one-off, immaterial
    ])
    rules, exc = mac.compress(d)
    assert len(rules) == 1
    assert len(exc) == 0
    assert rules.iloc[0]["Residual_Non_Core_Value_L"] > 0
    assert abs(rules.iloc[0]["Value_L"] - 301.0) < 0.01  # residual still counted in the total


def test_large_residual_is_not_silently_folded_in():
    """If the non-core portion is too large relative to the total, do not
    quietly absorb it -- treat the whole (distributor, brand) as unstable."""
    d = _detail([
        ["Apr'25", "D1", "B1", "Lulu", 60.0], ["Apr'25", "D1", "B1", "Apollo", 40.0],
        ["May'25", "D1", "B1", "Lulu", 55.0], ["May'25", "D1", "B1", "DMart", 45.0],
        ["Jun'25", "D1", "B1", "Lulu", 58.0], ["Jun'25", "D1", "B1", "Spencer", 42.0],
    ])
    rules, exc = mac.compress(d)
    # Lulu clears the coverage bar (present every month), but the non-core
    # residual (Apollo/DMart/Spencer, a different chain each month) is >20%
    # of the total and material -- must not be silently absorbed.
    assert len(exc) == 1
    assert exc.iloc[0]["Distributor"] == "D1"


def test_brands_sharing_identical_split_merge_into_one_rule():
    d = _detail([
        ["Apr'25", "D1", "B1", "Lulu", 50.0], ["Apr'25", "D1", "B2", "Lulu", 30.0],
        ["May'25", "D1", "B1", "Lulu", 40.0], ["May'25", "D1", "B2", "Lulu", 20.0],
    ])
    rules, exc = mac.compress(d)
    assert len(rules) == 1
    # both brands share the distributor's only chain signature, so scope
    # collapses to "ALL" rather than listing brands individually
    assert rules.iloc[0]["Brand_Scope"] == "ALL"
    assert abs(rules.iloc[0]["Value_L"] - 140.0) < 0.01


def test_different_distributors_never_merge():
    d = _detail([
        ["Apr'25", "D1", "B1", "Lulu", 50.0],
        ["Apr'25", "D2", "B1", "Lulu", 50.0],
    ])
    rules, exc = mac.compress(d)
    assert len(rules) == 2
    assert set(rules["Distributor"]) == {"D1", "D2"}


def test_never_sets_an_owner_decision_column():
    """The compressor must never emit a column that looks like a decision
    already made -- Owner_Decision is the human's field, not this script's."""
    d = _detail([["Apr'25", "D1", "B1", "Lulu", 10.0]])
    rules, exc = mac.compress(d)
    assert "Owner_Decision" not in rules.columns
    assert "Owner_Decision" not in exc.columns


def test_near_zero_brand_never_silently_dropped():
    """Regression: a (distributor, brand) where every value is at/below the
    noise floor used to hit an early `continue` and vanish from BOTH rules
    and exceptions -- a real, if tiny, silent-loss bug caught during the
    governance audit (9 real distributor-brand pairs, Rs0.0001L, in the
    actual PR #119 register). It must now surface as an exception."""
    d = _detail([["Apr'25", "D1", "B1", "Lulu", 0.001]])  # below NOISE_FLOOR_L
    rules, exc = mac.compress(d)
    assert len(rules) == 0
    assert len(exc) == 1
    assert abs(exc.iloc[0]["Value_L"] - 0.001) < 1e-9


def test_small_total_high_percentage_conflict_is_not_hidden_by_absolute_floor():
    """Regression: a flat absolute residual floor let a 65% disagreement
    through as a clean rule whenever the total was small enough that even a
    large SHARE of it stayed under the floor (Rs1.93L / Rs2.97L total, 65%,
    real case from the PR #119 register). The test must be percentage-based,
    not gated by an absolute rupee floor, or small-total hidden conflicts
    slip through."""
    d = _detail([
        ["Apr'25", "D1", "B1", "Apollo", 1.0],
        ["May'25", "D1", "B1", "DMart", 1.0],
        ["Jun'25", "D1", "B1", "Apollo", 1.0],
    ])
    rules, exc = mac.compress(d)
    # Apollo appears 2/3 months (67%, clears the 80% bar? No -- 2/3=66.7% < 80%,
    # so no chain clears CORE_CHAIN_MONTH_COVERAGE) -> straight to exception.
    assert len(rules) == 0
    assert len(exc) == 1


def test_large_rule_with_small_percentage_residual_is_not_wrongly_exploded():
    """Regression: after fixing the above, an early attempt used a flat
    absolute floor (Rs5L) for the OR-branch, which wrongly exploded a large,
    genuinely stable rule (Rs2,334L total, 0.24% residual) just because the
    residual's raw rupee value happened to exceed the flat floor. The
    percentage test must scale with rule size in both directions."""
    rows = []
    for i, month in enumerate(["Apr'25", "May'25", "Jun'25", "Jul'25"]):
        rows.append([month, "D1", "B1", "DMart", 500.0])
        rows.append([month, "D1", "B1", "Apollo", 80.0])
    rows.append(["Apr'25", "D1", "B1", "Spencer", 5.55])  # one-off, ~0.24% of total
    d = _detail(rows)
    rules, exc = mac.compress(d)
    assert len(exc) == 0
    assert len(rules) == 1
    assert rules.iloc[0]["Chain_Approval_Type"] == "ALLOCATION_SPLIT_APPROVAL"


def test_chain_set_approval_vs_allocation_split_approval():
    single = _detail([["Apr'25", "D1", "B1", "Lulu", 10.0], ["May'25", "D1", "B1", "Lulu", 10.0]])
    rules_single, _ = mac.compress(single)
    assert rules_single.iloc[0]["Chain_Approval_Type"] == "CHAIN_SET_APPROVAL"

    multi = _detail([
        ["Apr'25", "D1", "B1", "Lulu", 60.0], ["Apr'25", "D1", "B1", "Apollo", 40.0],
        ["May'25", "D1", "B1", "Lulu", 55.0], ["May'25", "D1", "B1", "Apollo", 45.0],
    ])
    rules_multi, _ = mac.compress(multi)
    assert rules_multi.iloc[0]["Chain_Approval_Type"] == "ALLOCATION_SPLIT_APPROVAL"


def test_draft_policy_never_defaults_to_future_scope():
    d = _detail([["Apr'25", "D1", "B1", "Lulu", 10.0], ["May'25", "D1", "B1", "Lulu", 10.0]])
    rules, exc = mac.compress(d)
    policy = mac.build_draft_policy(rules, exc, "deadbeef")
    assert (policy["STATUS"] == "PENDING").all()
    assert not policy["DECISION_SCOPE"].str.contains("FUTURE_PERIODS_ALSO").any()
    assert (policy["VALID_FROM"] != "").all()
    assert (policy["VALID_TO"] != "").all()


def test_order_by_materiality_high_first():
    df = pd.DataFrame([
        {"Materiality": "LOW", "Value_L": 1.0},
        {"Materiality": "HIGH", "Value_L": 300.0},
        {"Materiality": "MEDIUM", "Value_L": 50.0},
        {"Materiality": "HIGH", "Value_L": 500.0},
    ])
    ordered = mac.order_by_materiality(df)
    assert list(ordered["Materiality"]) == ["HIGH", "HIGH", "MEDIUM", "LOW"]
    assert ordered.iloc[0]["Value_L"] == 500.0  # higher HIGH value first


def test_reconciliation_exact_on_mixed_batch():
    d = _detail([
        ["Apr'25", "D1", "B1", "Lulu", 10.0],
        ["May'25", "D1", "B1", "Lulu", 12.0],
        ["Apr'25", "D2", "B1", "Apollo", 100.0],
        ["May'25", "D2", "B1", "DMart", 100.0],
    ])
    rules, exc = mac.compress(d)
    total_in = d["Value_L"].sum()
    total_out = rules["Value_L"].sum() + exc["Value_L"].sum() if len(exc) else rules["Value_L"].sum()
    assert abs(total_in - total_out) < 0.01


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
