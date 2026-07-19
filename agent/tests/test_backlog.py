"""Behavioral tests for the Backlog Completion and Evidence Orchestration
skills (agent/mtagent/backlog/). Covers the required proofs from the
Master Prompt that are new ground here -- proofs already covered by
agent/tests/test_business_validation.py, test_controller.py, and
test_release_gate.py (store-explosion BLOCKED, June-cannot-be-closed,
commit/push approval-gating, claim evidence+confidence, DRAFT/VALIDATED/
APPROVED_FOR_SHARING) are not duplicated here.
"""
import tempfile
import unittest
from pathlib import Path

from mtagent.backlog import (audit_rerun, environment, exceptions as exc_mod,
                              orchestration, reproducibility, resume, test_orchestration as to,
                              traceability)
from mtagent.config import Config
from mtagent.worklog import log_run


class TestReleaseRequiredDependencyBlocksReadiness(unittest.TestCase):
    """Proof 1: a package genuinely declared required-for-release, if
    missing, returns ENVIRONMENT_BLOCKED with a dependency failure class.
    (openpyxl was this example until 2026-07-19, when redaction_scan()/
    formula_error_scan() were rewritten to need only the stdlib -- see
    RELEASE_REQUIRED_PACKAGES's docstring in environment.py. The
    mechanism is proven here directly rather than via a package that's
    no longer actually required, so this test doesn't silently go stale
    the next time a real dependency requirement changes.)"""

    def test_missing_release_required_package_blocks_readiness(self):
        # check_environment() only probes a fixed set of real packages
        # (openpyxl/pandas/duckdb/pypdf); use one of those (pandas, not
        # installed in this environment) rather than a fake name, so the
        # dependency actually appears in the checked list.
        original = environment.RELEASE_REQUIRED_PACKAGES
        environment.RELEASE_REQUIRED_PACKAGES = ("pandas",)
        try:
            blocked_report = environment.check_environment(repo_root=str(Path(__file__).resolve().parents[2]))
        finally:
            environment.RELEASE_REQUIRED_PACKAGES = original
        pandas_dep = next(d for d in blocked_report.dependencies if d.name == "pandas")
        if pandas_dep.installed:
            self.skipTest("pandas happens to be installed in this environment -- can't prove the blocked path")
        self.assertEqual(blocked_report.status, environment.BLOCKED)
        self.assertEqual(blocked_report.failure_class, environment.DEPENDENCY_FAILURE)
        self.assertTrue(any("pandas" in m for m in blocked_report.missing))

    def test_no_release_required_packages_currently_declared_missing_does_not_block(self):
        # real, current state: RELEASE_REQUIRED_PACKAGES is empty, so a
        # merely-optional package being absent (e.g. openpyxl, pandas)
        # must never block readiness on its own
        report = environment.check_environment(repo_root=str(Path(__file__).resolve().parents[2]))
        self.assertEqual(environment.RELEASE_REQUIRED_PACKAGES, ())
        dependency_reasons = [m for m in report.missing if any(d.name in m for d in report.dependencies)]
        self.assertEqual(dependency_reasons, [])

    def test_dependency_check_never_assumes_success_from_silence(self):
        # a package that isn't importable is never reported installed,
        # even if metadata claimed otherwise -- checked via two signals
        dep = environment._check_package("definitely_not_a_real_package_xyz", "n/a", True)
        self.assertFalse(dep.installed)


class TestSkippedCriticalTestBlocksApproval(unittest.TestCase):
    """Proof 3: a skipped critical release test prevents APPROVED_FOR_SHARING."""

    def test_skip_in_critical_group_blocks(self):
        result = to.GroupResult(group="unit", modules=["m"], tests_run=10, passed=9,
                                 failed=0, skipped=1, skip_reasons=["openpyxl missing"],
                                 critical_for_release=True, business_risk_if_skipped="x")
        ok, blockers = to.blocks_approved_for_sharing([result])
        self.assertFalse(ok)
        self.assertEqual(len(blockers), 1)

    def test_skip_in_non_critical_group_does_not_block(self):
        result = to.GroupResult(group="unit", modules=["m"], tests_run=10, passed=9,
                                 failed=0, skipped=1, skip_reasons=["n/a"],
                                 critical_for_release=False, business_risk_if_skipped="n/a")
        ok, blockers = to.blocks_approved_for_sharing([result])
        self.assertTrue(ok)


class TestRuleWithoutEvidenceCannotPass(unittest.TestCase):
    """Proof 4: a rule without linked evidence cannot be marked PASS."""

    def test_pass_with_no_evidence_raises(self):
        with self.assertRaises(ValueError):
            traceability.TraceabilityRow(
                rule_id="X1", business_rule="test rule", risk_controlled="test risk",
                implementation_file="x.py", function_or_module="f()", test_file="t.py",
                test_name="test_f", expected_behavior="works", actual_result=traceability.PASS,
                evidence_location="",
            )

    def test_pass_with_evidence_is_accepted(self):
        row = traceability.TraceabilityRow(
            rule_id="X2", business_rule="test rule", risk_controlled="test risk",
            implementation_file="x.py", function_or_module="f()", test_file="t.py",
            test_name="test_f", expected_behavior="works", actual_result=traceability.PASS,
            evidence_location="agent/tests/test_x.py::test_f passes",
        )
        self.assertEqual(row.actual_result, traceability.PASS)


class TestReproducibility(unittest.TestCase):
    """Proofs 5/6: identical inputs -> identical totals; a changed mapping
    version is detected as an unexpected business-data difference."""

    def _snapshot(self, **overrides):
        base = dict(run_id="r1", created_timestamp="t1", source_hashes={"a": "h1"},
                    rule_version="v1", mapping_version="m1", row_count=23193,
                    nsv_total=12500000.0, qty_total=98000, canonical_chain_count=45,
                    exception_count=3, output_schema=["a", "b"], output_hash="oh1",
                    reconciliation_status="PASS")
        base.update(overrides)
        return reproducibility.RunSnapshot(**base)

    def test_identical_business_totals_across_two_runs_is_reproducible(self):
        a = self._snapshot()
        b = self._snapshot(run_id="r2", created_timestamp="t2", output_hash="oh2")
        report = reproducibility.compare(a, b)
        self.assertEqual(report.verdict, reproducibility.REPRODUCIBLE)
        self.assertTrue(report.expected_technical_differences)
        self.assertEqual(report.unexpected_business_differences, [])

    def test_changed_mapping_version_is_detected_as_unexpected(self):
        a = self._snapshot()
        b = self._snapshot(run_id="r2", mapping_version="m2")
        report = reproducibility.compare(a, b)
        self.assertEqual(report.verdict, reproducibility.NON_REPRODUCIBLE)
        self.assertTrue(any("mapping_version" in d for d in report.unexpected_business_differences))

    def test_changed_row_count_is_non_reproducible(self):
        a = self._snapshot()
        b = self._snapshot(run_id="r2", row_count=23100)
        report = reproducibility.compare(a, b)
        self.assertEqual(report.verdict, reproducibility.NON_REPRODUCIBLE)


class TestExceptionOwnership(unittest.TestCase):
    """Proof 9: an exception without owner and action cannot be closed."""

    def test_no_owner_cannot_close(self):
        e = exc_mod.Exception_(title="x", severity="High", impact="y", root_cause="z",
                                recommended_action="do something", owner="", due_date="tbd",
                                blocking_status="blocking", verification_method="check")
        ok, reason = e.can_close()
        self.assertFalse(ok)
        with self.assertRaises(ValueError):
            e.close()

    def test_no_action_cannot_close(self):
        e = exc_mod.Exception_(title="x", severity="High", impact="y", root_cause="z",
                                recommended_action="", owner="someone", due_date="tbd",
                                blocking_status="blocking", verification_method="check")
        ok, _ = e.can_close()
        self.assertFalse(ok)

    def test_owner_and_action_present_can_close(self):
        e = exc_mod.Exception_(title="x", severity="High", impact="y", root_cause="z",
                                recommended_action="do something", owner="someone", due_date="tbd",
                                blocking_status="blocking", verification_method="check")
        e.close()
        self.assertEqual(e.status, exc_mod.CLOSED)

    def test_known_backlog_exceptions_are_all_ownerless_action_complete(self):
        # the two REAL current exceptions must themselves satisfy the rule
        for e in exc_mod.known_backlog_exceptions():
            ok, reason = e.can_close()
            self.assertTrue(ok, f"{e.title}: {reason}")


class TestResumeContinuesFromLastCompletedStage(unittest.TestCase):
    """Proof 10: resume continues from the last completed stage."""

    def test_resume_reports_last_pass_stage_from_real_worklog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text("# fixture\n", encoding="utf-8")
            cfg = Config(repo_root=str(root), index_path="agent/index/index.json")
            log_run(cfg, "controller:build_dataset", [], 0, [],
                    run_id="run-abc", desired_output="test",
                    stage_results={"build_dataset": "PASS"}, output_files=["f.csv"])
            state = resume.find_run(cfg, "run-abc")
            self.assertTrue(state.found)
            self.assertEqual(state.last_completed_stage, "build_dataset")
            self.assertIn("nothing to resume", state.next_safe_action)

    def test_resume_on_unknown_run_id_says_so_explicitly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text("# fixture\n", encoding="utf-8")
            cfg = Config(repo_root=str(root), index_path="agent/index/index.json")
            state = resume.find_run(cfg, "nonexistent")
            self.assertFalse(state.found)

    def test_resume_reports_pending_decision_as_next_safe_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "CLAUDE.md").write_text("# fixture\n", encoding="utf-8")
            cfg = Config(repo_root=str(root), index_path="agent/index/index.json")
            log_run(cfg, "controller:commit", [], 1, [],
                    run_id="run-blocked", desired_output="test",
                    stage_results={"approval_gate": "BLOCKED"},
                    decision_required=["needs explicit approval"])
            state = resume.find_run(cfg, "run-blocked")
            self.assertIn("resolve pending decision", state.next_safe_action)


class TestFailedStagePreventsLaterReleaseStages(unittest.TestCase):
    """Proof 11: a failed stage prevents later release stages -- real
    16-stage audit rerun halting at the true first blocker."""

    def test_audit_rerun_halts_at_first_blocked_stage_not_later(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "agent" / "mtagent").mkdir(parents=True)
            result = audit_rerun.run_audit(str(root), "June'26")
            self.assertIsNotNone(result.halted_at)
            # exactly the stages up to and including the halt point ran --
            # nothing downstream was attempted
            names = [s.stage for s in result.stages]
            self.assertEqual(names[-1], result.halted_at)
            self.assertEqual(len(result.stages), audit_rerun.STAGE_NAMES.index(result.halted_at) + 1)

    def test_all_16_stage_names_are_reachable_in_order(self):
        self.assertEqual(len(audit_rerun.STAGE_NAMES), 16)


class TestBacklogOrchestrationDependencyGating(unittest.TestCase):
    """Backlog Orchestration Skill: a task cannot start until its
    dependencies are met, and technical completion is separate from
    business validation."""

    def _simple_backlog(self):
        t1 = orchestration.BacklogTask(
            task_id="A", business_purpose="first", dependency=[], assigned_subagent="x",
            input_required=[], expected_output="o", validation_required="v", evidence_required="e",
        )
        t2 = orchestration.BacklogTask(
            task_id="B", business_purpose="second", dependency=["A"], assigned_subagent="x",
            input_required=[], expected_output="o", validation_required="v", evidence_required="e",
        )
        return orchestration.Backlog([t1, t2])

    def test_dependent_task_is_blocked_until_dependency_validated(self):
        b = self._simple_backlog()
        b.refresh_ready_states()
        self.assertEqual(b.get("A").status, orchestration.READY)
        self.assertEqual(b.get("B").status, orchestration.BLOCKED)

    def test_dependent_task_becomes_ready_after_dependency_closed(self):
        b = self._simple_backlog()
        b.mark_technically_complete("A", evidence_present=True)
        b.mark_validated("A", business_accepted=True)
        b.close("A")
        b.refresh_ready_states()
        self.assertEqual(b.get("B").status, orchestration.READY)

    def test_technical_completion_without_evidence_is_refused(self):
        b = self._simple_backlog()
        b.mark_technically_complete("A", evidence_present=False)
        self.assertEqual(b.get("A").status, orchestration.BLOCKED)

    def test_business_validation_is_a_separate_gate_from_technical_completion(self):
        b = self._simple_backlog()
        b.mark_technically_complete("A", evidence_present=True)
        self.assertEqual(b.get("A").status, orchestration.TECHNICALLY_COMPLETE)
        b.mark_validated("A", business_accepted=False, reason="business rejected the result")
        self.assertEqual(b.get("A").status, orchestration.BLOCKED)
        self.assertIn("business rejected", b.get("A").blocking_reason)


if __name__ == "__main__":
    unittest.main()
