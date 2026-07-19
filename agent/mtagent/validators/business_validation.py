"""Business-validation gate (AI_LEVERAGE_AND_JUDGMENT.md, enforcement §C).

Technical success (a script exiting 0, a file being written) is not the
same claim as business success (the numbers are right). Every function
here returns a `CheckResult` naming exactly what was checked and why it
passed or failed -- never a bare boolean with no explanation, per the
explainability gate (§F).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def reconcile_counts(label: str, source_n: int, output_n: int) -> CheckResult:
    """Row-count reconciliation: every row from source must be accounted
    for in the output, no silent drops, no silent duplication."""
    passed = source_n == output_n
    return CheckResult(f"{label}_row_count", passed,
                        f"source={source_n} output={output_n}" + ("" if passed else " -- MISMATCH"))


def reconcile_metric(label: str, source_total: float, output_total: float, tolerance: float = 0.0) -> CheckResult:
    """NSV/Qty-style metric reconciliation within a tolerance band."""
    diff = abs(source_total - output_total)
    passed = diff <= tolerance
    return CheckResult(f"{label}_reconciliation", passed,
                        f"source={source_total} output={output_total} diff={diff} tolerance={tolerance}")


def distinct_value_check(label: str, before_count: int, after_count: int, max_growth_ratio: float = 1.5) -> CheckResult:
    """Generalizes the real Reliance store-explosion bug this project hit:
    a canonical dimension's distinct value count must not balloon after a
    mapping/build step. `before_count` is the last known-good distinct
    count (e.g. ChainMaster.csv row count); `after_count` is what the
    current run actually produced.
    """
    if before_count <= 0:
        return CheckResult(f"{label}_distinct_value_check", True,
                            f"before={before_count} after={after_count} (no prior baseline to compare)")
    ratio = after_count / before_count
    passed = ratio <= max_growth_ratio
    detail = f"before={before_count} after={after_count} ratio={ratio:.2f} max_allowed={max_growth_ratio}"
    if not passed:
        detail += " -- distinct-value explosion, likely store/ship-to codes leaking in as canonical rows"
    return CheckResult(f"{label}_distinct_value_check", passed, detail)


def period_completeness_check(label: str, is_partial_period: bool, treated_as_closed: bool) -> CheckResult:
    """A partial/provisional period must never be silently reported as a
    closed one -- that's a business-rule failure even if every technical
    step succeeded."""
    passed = not (is_partial_period and treated_as_closed)
    if not passed:
        detail = "partial period incorrectly treated as closed -- period-completeness business rule failed"
    elif is_partial_period:
        detail = "partial period correctly flagged as provisional"
    else:
        detail = "period complete"
    return CheckResult(f"{label}_period_completeness", passed, detail)


def mapping_validation_check(label: str, canonical: str, known_canonicals: set) -> CheckResult:
    """A mapping target must resolve to an approved canonical value, or be
    explicitly flagged -- never silently accepted either way."""
    passed = canonical in known_canonicals
    detail = (f"'{canonical}' matches an approved canonical value" if passed
              else f"'{canonical}' is NOT an approved canonical value -- flagged for human confirmation")
    return CheckResult(f"{label}_mapping_validation", passed, detail)


def evaluate(checks: list) -> tuple:
    """Roll up a list of CheckResult into (all_passed, checks_passed_names, checks_failed_names)."""
    passed_names = [c.name for c in checks if c.passed]
    failed_names = [c.name for c in checks if not c.passed]
    return (len(failed_names) == 0, passed_names, failed_names)
