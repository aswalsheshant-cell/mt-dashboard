"""Test Orchestration Skill.

Runs the real project test suite grouped into logical categories and
reports what a skip actually means -- not just a total pass/fail count.
A skipped test in a group flagged `critical_for_release` blocks
`APPROVED_FOR_SHARING`, matching AI_LEVERAGE_AND_JUDGMENT.md's release
gate: a dependency-related skip is never described as a passed validation.
"""
from __future__ import annotations

import io
import unittest
from dataclasses import dataclass

UNIT = "unit"
DEPENDENCY_SENSITIVE = "dependency_sensitive"
INTEGRATION = "integration"
REGRESSION = "regression"

# module (dotted, relative to agent/tests) -> (group, critical_for_release, business_risk_if_skipped)
TEST_GROUPS = {
    "tests.test_outcome_gate": (UNIT, False, "n/a -- not release-critical"),
    "tests.test_business_validation": (UNIT, True, "an unreconciled or exploded-chain output could pass silently"),
    "tests.test_materiality": (UNIT, False, "n/a -- not release-critical"),
    "tests.test_release_gate": (UNIT, True, "an output could reach APPROVED_FOR_SHARING without real validation"),
    "tests.test_controller": (UNIT, True, "store names could silently become chains; commit/push could run unapproved"),
    "tests.test_final_summary": (UNIT, False, "n/a -- not release-critical"),
    "tests.test_worklog": (UNIT, False, "n/a -- not release-critical, but weakens the audit trail if broken"),
}


@dataclass
class GroupResult:
    group: str
    modules: list
    tests_run: int
    passed: int
    failed: int
    skipped: int
    skip_reasons: list
    critical_for_release: bool
    business_risk_if_skipped: str


def run_group(group: str, modules: list, critical_for_release: bool, business_risk: str) -> GroupResult:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for m in modules:
        suite.addTests(loader.loadTestsFromName(m))
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    skip_reasons = [str(reason) for _test, reason in result.skipped]
    return GroupResult(
        group=group, modules=modules, tests_run=result.testsRun,
        passed=result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        failed=len(result.failures) + len(result.errors), skipped=len(result.skipped),
        skip_reasons=skip_reasons, critical_for_release=critical_for_release,
        business_risk_if_skipped=business_risk,
    )


def run_all_groups() -> list:
    by_group: dict = {}
    for module, (group, critical, risk) in TEST_GROUPS.items():
        by_group.setdefault(group, {"modules": [], "critical": False, "risks": []})
        by_group[group]["modules"].append(module)
        by_group[group]["critical"] = by_group[group]["critical"] or critical
        if critical:
            by_group[group]["risks"].append(f"{module}: {risk}")
    results = []
    for group, info in by_group.items():
        results.append(run_group(group, info["modules"], info["critical"], "; ".join(info["risks"]) or "n/a"))
    return results


def blocks_approved_for_sharing(results: list) -> tuple:
    """A skip in a critical_for_release group blocks APPROVED_FOR_SHARING
    -- never silently treated as a pass."""
    blockers = [r for r in results if r.critical_for_release and r.skipped > 0]
    return (len(blockers) == 0, blockers)


def format_report(results: list) -> str:
    lines = ["Test group results:", ""]
    for r in results:
        lines.append(f"Group: {r.group}  (critical for release: {r.critical_for_release})")
        lines.append(f"  Modules: {', '.join(r.modules)}")
        lines.append(f"  Tests run: {r.tests_run}  Passed: {r.passed}  Failed: {r.failed}  Skipped: {r.skipped}")
        if r.skipped:
            lines.append(f"  Skip reasons: {'; '.join(r.skip_reasons)}")
            lines.append(f"  Business risk of skip: {r.business_risk_if_skipped}")
        lines.append("")
    ok, blockers = blocks_approved_for_sharing(results)
    lines.append(f"Blocks APPROVED_FOR_SHARING: {'No' if ok else 'Yes'}")
    if not ok:
        for b in blockers:
            lines.append(f"  - {b.group}: {b.skipped} skipped in a release-critical group")
    return "\n".join(lines)
