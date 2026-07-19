"""Spec Tests 1, 5, 6, 8 -- the controller-level behavioral tests from
AI_LEVERAGE_AND_JUDGMENT.md that don't fit cleanly under a single
validators module (outcome_gate / business_validation / materiality),
because they're about controller.py's end-to-end behavior.
"""
import unittest

from mtagent import controller as ctl
from mtagent.validators import release_gate
from tests.test_controller import _fixture_repo


class TestVagueRequestNeverExecutes(unittest.TestCase):
    """Spec Test 1: 'Build the dashboard.' must not execute."""

    def test_vague_instruction_returns_clarification_required(self):
        tmp, cfg = _fixture_repo()
        try:
            plan = ctl.interpret("Build the dashboard.")
            self.assertFalse(plan.recognized)
            result = ctl.execute(cfg, plan)
            self.assertEqual(result.run_status, "CLARIFICATION_REQUIRED")
            # nothing ran -- exactly one stage (interpret), no pipeline call
            self.assertEqual(len(result.stages), 1)
            self.assertEqual(result.stages[0].name, "interpret")
        finally:
            tmp.cleanup()


class TestToolFollowsOutcome(unittest.TestCase):
    """Spec Test 5: outcome must be defined before a tool is selected --
    the controller must not pick a tool (or a presentation format) before
    the analysis output itself is defined."""

    def test_business_outcome_is_set_alongside_tool_selection_reason(self):
        plan = ctl.interpret("run reconciliation")
        self.assertTrue(plan.business_outcome)
        self.assertTrue(plan.tool_selection_reason)
        # the reasoning must reference the actual method used (Python/CSV/
        # pipeline), never a presentation tool like PowerPoint chosen
        # ahead of the analysis itself
        self.assertNotIn("powerpoint", plan.tool_selection_reason.lower())
        self.assertNotIn("pptx", plan.tool_selection_reason.lower())

    def test_every_recognized_action_names_a_tool_selection_reason(self):
        for action, spec in ctl.KNOWN_ACTIONS.items():
            outcome = ctl.ACTION_OUTCOME_SPEC.get(action, {})
            self.assertTrue(outcome.get("business_outcome"), f"{action}: no business_outcome")
            self.assertTrue(outcome.get("tool_selection_reason"), f"{action}: no tool_selection_reason")


class TestMappingExplainability(unittest.TestCase):
    """Spec Test 6: 'Map Apollo Healthco to Apollo for the secondary file
    only' must return raw label, canonical, scope, and a reason/risk --
    never a bare 'Mapping successful.'"""

    def test_apply_alias_result_follows_what_changed_scope_impact_reason_risk(self):
        tmp, cfg = _fixture_repo()
        try:
            plan = ctl.interpret('apply "Apollo Healthco" to "Apollo" for the secondary file only')
            result = ctl.execute(cfg, plan)
            detail = result.stages[0].detail
            for required in ("What changed:", "Scope:", "Impact:", "Reason:", "Risk:"):
                self.assertIn(required, detail)
            self.assertIn("Apollo Healthco", detail)
            self.assertIn("Apollo", detail)
            self.assertIn("secondary", detail)
        finally:
            tmp.cleanup()


class TestFinalResponseSeparatesWorkFromOutcome(unittest.TestCase):
    """Spec Test 8: every final response must separate work completed from
    business outcome achieved, plus validation status and uncertainty."""

    def test_pass_result_has_all_required_fields(self):
        tmp, cfg = _fixture_repo()
        try:
            result = ctl.execute(cfg, ctl.interpret("rebuild the dataset"))
            self.assertIsNotNone(result.business_outcome_achieved)
            self.assertIsInstance(result.checks_passed, list)
            self.assertIsInstance(result.checks_failed, list)
            self.assertIsInstance(result.remaining_uncertainty, list)
            text = ctl.format_run_result(result)
            for required in ("Business outcome achieved:", "Checks passed:", "Checks failed:",
                              "Remaining uncertainty:"):
                self.assertIn(required, text)
        finally:
            tmp.cleanup()

    def test_clarification_required_result_has_no_outcome_yet(self):
        tmp, cfg = _fixture_repo()
        try:
            result = ctl.execute(cfg, ctl.interpret("do something vague"))
            self.assertIsNone(result.business_outcome_achieved)
            text = ctl.format_run_result(result)
            self.assertIn("n/a (did not execute)", text)
        finally:
            tmp.cleanup()

    def test_release_gate_final_response_structure_present(self):
        text = release_gate.format_final_response(
            run_status="PASS", business_outcome="Produce a trusted June dataset.",
            outcome_achieved="Yes", key_results=["Row variance: 0"],
            validation_evidence={"nsv_variance": 0, "qty_variance": 0},
            assumptions=["Apollo Healthco == Apollo"], exceptions_and_risks=["June is partial"],
            confidence=["High: NSV/Qty reconcile exactly"], files=["Fact_OfftakeSales.csv"],
            sharing_status="VALIDATED", decision_required="Approve commit",
        )
        for required in ("Run Status:", "Business Outcome:", "Outcome Achieved:", "Key Results:",
                          "Validation Evidence:", "Assumptions:", "Exceptions and Risks:",
                          "Confidence:", "Files Created or Changed:", "Sharing Status:",
                          "Decision Required:"):
            self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main()
