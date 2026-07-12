import json
import tempfile
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.pbi_workflow import (BLOCKED, COMPLETED, COMPLETED_WITH_WARNING,
                                  MANUAL_ACTION_REQUIRED, NOT_STARTED, READY,
                                  STEP_SEQUENCE, WorkflowController,
                                  run_automated_step)


def _cfg(tmp_root: Path) -> Config:
    return Config(repo_root=str(tmp_root), index_path="agent/index/index.json")


class TestFreshState(unittest.TestCase):
    def test_first_step_ready_rest_not_started(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            steps = sorted(c.state.steps.values(), key=lambda r: r["seq"])
            self.assertEqual(steps[0]["status"], READY)
            self.assertTrue(all(s["status"] == NOT_STARTED for s in steps[1:]))

    def test_all_16_steps_present_in_spec_order(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            self.assertEqual(len(c.state.steps), 16)
            self.assertEqual([s.id for s in STEP_SEQUENCE], list(c.state.steps.keys()))


class TestTransitions(unittest.TestCase):
    def test_complete_step_advances_next_to_ready(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            c.start_step("validate_sources")
            c.complete_step("validate_sources", output_file="out.csv")
            self.assertEqual(c.state.steps["validate_sources"]["status"], COMPLETED)
            self.assertEqual(c.state.steps["build_datasets"]["status"], READY)

    def test_complete_with_warning_sets_warning_status(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            c.start_step("validate_sources")
            c.complete_step("validate_sources", warning="6 unmapped chains")
            self.assertEqual(c.state.steps["validate_sources"]["status"], COMPLETED_WITH_WARNING)

    def test_block_step_records_reason(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            c.block_step("validate_sources", "no source files found")
            self.assertEqual(c.state.steps["validate_sources"]["status"], BLOCKED)
            self.assertEqual(c.state.steps["validate_sources"]["blocker"], "no source files found")
            # a blocked step must NOT advance the next step to Ready
            self.assertEqual(c.state.steps["build_datasets"]["status"], NOT_STARTED)

    def test_unknown_step_id_raises(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            with self.assertRaises(KeyError):
                c.start_step("not_a_real_step")

    def test_every_transition_is_logged_to_events(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            c.start_step("validate_sources")
            c.complete_step("validate_sources")
            self.assertGreaterEqual(len(c.state.events), 2)
            self.assertEqual(c.state.events[0]["step"], "validate_sources")


class TestMarkStepComplete(unittest.TestCase):
    def test_accepts_clean_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            c.require_manual_action("manual_desktop_actions", "import files")
            result = c.mark_step_complete("manual_desktop_actions", "screenshot", "/tmp/proof.png")
            self.assertTrue(result["ok"])
            self.assertIn(c.state.steps["manual_desktop_actions"]["status"], (COMPLETED, COMPLETED_WITH_WARNING))

    def test_rejects_evidence_showing_unresolved_error(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            result = c.mark_step_complete("manual_desktop_actions", "screenshot", "screenshot shows #Error on visual")
            self.assertFalse(result["ok"])
            self.assertEqual(c.state.steps["manual_desktop_actions"]["status"], BLOCKED)

    def test_rejects_empty_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            with self.assertRaises(ValueError):
                c.mark_step_complete("manual_desktop_actions", "screenshot", "   ")

    def test_rejects_unknown_evidence_kind(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            with self.assertRaises(ValueError):
                c.mark_step_complete("manual_desktop_actions", "vibes", "looked fine")


class TestPersistence(unittest.TestCase):
    def test_state_round_trips_through_disk(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            c1 = WorkflowController(cfg)
            c1.start_step("validate_sources")
            c1.complete_step("validate_sources", output_file="x.csv", warning="w")

            c2 = WorkflowController(cfg)  # fresh instance, same cfg -> loads from disk
            self.assertEqual(c2.state.steps["validate_sources"]["status"], COMPLETED_WITH_WARNING)
            self.assertEqual(c2.state.steps["validate_sources"]["output_file"], "x.csv")
            self.assertEqual(c2.state.build_id, c1.state.build_id)

    def test_corrupt_state_file_falls_back_to_fresh_rather_than_crashing(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = _cfg(Path(td))
            state_path = cfg.path(cfg.index_path).parent / "pbi_workflow_state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text("{not valid json", encoding="utf-8")
            c = WorkflowController(cfg)  # must not raise
            self.assertEqual(c.state.steps["validate_sources"]["status"], READY)


class TestQueries(unittest.TestCase):
    def test_status_summary_completion_pct_and_pending_lists(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            c.start_step("validate_sources")
            c.complete_step("validate_sources")
            summary = c.status_summary()
            self.assertAlmostEqual(summary["completion_pct"], 100 / 16, places=1)
            self.assertIn("Guide the user through manual Power BI Desktop actions.", summary["manual_steps_pending"])
            # "current_phase" is the freshly-Ready step; "next_step" is the first
            # step that hasn't started at all yet (one further down the sequence).
            self.assertEqual(summary["current_phase"], "Build Power BI-ready datasets.")
            self.assertEqual(summary["next_step"], "Generate dimension and fact tables.")

    def test_next_manual_step_none_when_no_manual_action_pending(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            self.assertIsNone(c.next_manual_step())

    def test_next_manual_step_returns_the_flagged_step(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            c.require_manual_action("manual_desktop_actions", "do the thing")
            step = c.next_manual_step()
            self.assertEqual(step["id"], "manual_desktop_actions")
            self.assertEqual(step["required_input"], "do the thing")

    def test_resume_plan_identifies_last_completed_and_next(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            c.start_step("validate_sources")
            c.complete_step("validate_sources")
            plan = c.resume_plan()
            self.assertEqual(plan["last_completed_step"], "Validate source files.")
            self.assertEqual(plan["next_step_id"], "build_datasets")


class TestRunAutomatedStep(unittest.TestCase):
    def test_success_completes_the_step(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            result = run_automated_step(c, "validate_sources",
                                         lambda: {"output_file": "a.csv", "validation_result": "ok"})
            self.assertEqual(result["status"], COMPLETED)

    def test_blocked_result_blocks_the_step_without_crashing(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))
            result = run_automated_step(c, "validate_sources", lambda: {"blocked_reason": "no files"})
            self.assertEqual(result["status"], BLOCKED)

    def test_exception_fails_the_step_without_crashing_the_caller(self):
        with tempfile.TemporaryDirectory() as td:
            c = WorkflowController(_cfg(Path(td)))

            def _boom():
                raise RuntimeError("disk on fire")

            result = run_automated_step(c, "validate_sources", _boom)
            self.assertEqual(result["status"], "Failed")
            self.assertIn("disk on fire", c.state.steps["validate_sources"]["blocker"])


if __name__ == "__main__":
    unittest.main()
