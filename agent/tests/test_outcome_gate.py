"""Tests for the pre-execution outcome gate (§A in AI_LEVERAGE_AND_JUDGMENT.md)."""
import unittest

from mtagent import controller as ctl
from mtagent.validators import outcome_gate


class TestCheckPlanFields(unittest.TestCase):
    def test_complete_dict_passes(self):
        result = outcome_gate.check_plan_fields({
            "business_outcome": "x", "deliverable": "y",
            "success_criteria": ["a"], "source_data": ["b"],
            "approval_boundary": [],
        })
        self.assertTrue(result.ok)
        self.assertEqual(result.missing, [])

    def test_missing_business_outcome_is_named(self):
        result = outcome_gate.check_plan_fields({
            "business_outcome": "", "deliverable": "y",
            "success_criteria": ["a"], "source_data": ["b"],
            "approval_boundary": [],
        })
        self.assertFalse(result.ok)
        self.assertIn("business_outcome", result.missing)

    def test_missing_source_data_is_named(self):
        result = outcome_gate.check_plan_fields({
            "business_outcome": "x", "deliverable": "y",
            "success_criteria": ["a"], "source_data": [],
            "approval_boundary": [],
        })
        self.assertFalse(result.ok)
        self.assertIn("source_data", result.missing)

    def test_approval_boundary_empty_list_is_valid_not_missing(self):
        # An empty approval_boundary is a deliberate "no approval needed"
        # statement, not an unset field -- only None counts as unset.
        result = outcome_gate.check_plan_fields({
            "business_outcome": "x", "deliverable": "y",
            "success_criteria": ["a"], "source_data": ["b"],
            "approval_boundary": [],
        })
        self.assertNotIn("approval_boundary", result.missing)

    def test_approval_boundary_none_is_missing(self):
        result = outcome_gate.check_plan_fields({
            "business_outcome": "x", "deliverable": "y",
            "success_criteria": ["a"], "source_data": ["b"],
            "approval_boundary": None,
        })
        self.assertFalse(result.ok)
        self.assertIn("approval_boundary", result.missing)


class TestCheckPlanAgainstRealControllerPlans(unittest.TestCase):
    """Every recognized action's static template must satisfy the gate --
    proves the templates in controller.ACTION_OUTCOME_SPEC are actually
    complete, not just present for a couple of actions."""

    def test_every_known_action_produces_a_gate_passing_plan(self):
        for action, spec in ctl.KNOWN_ACTIONS.items():
            instruction = {
                "status": "show current status",
                "build_dataset": "rebuild the dataset",
                "reconcile": "run reconciliation",
                "compile_model": "compile the model",
                "derive_article_master": "derive the article master",
                "derive_npi_list": "derive the npi list",
                "run_automated": "run the full pipeline everything",
                "apply_alias": 'apply "X" to "D-Mart" for the secondary file only',
                "commit": "commit these changes",
                "push": "push to remote",
            }[action]
            plan = ctl.interpret(instruction)
            self.assertTrue(plan.recognized, f"{action}: instruction not recognized")
            result = outcome_gate.check_plan(plan)
            self.assertTrue(result.ok, f"{action}: gate failed, missing {result.missing}")


if __name__ == "__main__":
    unittest.main()
