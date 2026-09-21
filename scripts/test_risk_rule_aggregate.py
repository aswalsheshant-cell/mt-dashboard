"""Tests for the Phase A Risk Rule Registry + Aggregator.

Every test here checks one thing this module promises: it OBSERVES existing
governed state and never invents or recomputes a business number. See
docs/RISK_MANAGEMENT_PHASE_A.md for the design this protects.
"""
import json
import sys
import unittest
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import risk_rule_aggregate as rra  # noqa: E402

REGISTRY_PATH = REPO / "config" / "risk_rule_registry.yml"
DATA_JS_PATH = REPO / "dashboard" / "data.js"


class TestRegistrySchema(unittest.TestCase):
    def setUp(self):
        self.registry = rra.load_registry()

    def test_registry_parses(self):
        self.assertIn("rules", self.registry)
        self.assertIn("risk_families", self.registry)

    def test_rule_ids_are_unique(self):
        ids = [r["rule_id"] for r in self.registry["rules"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate rule_id in registry")

    def test_every_rule_declares_a_real_source(self):
        """A rule with no source_module/source_function is exactly the
        'invented risk' failure mode this registry exists to prevent."""
        for r in self.registry["rules"]:
            self.assertTrue(r.get("source_module"), f"{r['rule_id']} missing source_module")
            self.assertIn("evaluation", r, f"{r['rule_id']} missing evaluation status")

    def test_every_rule_family_is_declared(self):
        families = set(self.registry["risk_families"])
        for r in self.registry["rules"]:
            self.assertIn(r["risk_family"], families, f"{r['rule_id']} has an undeclared risk_family")

    def test_every_rule_is_provisional_or_explicitly_not_approved(self):
        """No rule may claim approval without a named approver -- this
        registry never self-certifies."""
        for r in self.registry["rules"]:
            self.assertIn(r["approval_status"], ("PROVISIONAL", "NOT_APPROVED"),
                          f"{r['rule_id']} claims an approval status this Phase A pass cannot back")

    def test_unimplemented_rule_is_never_silently_evaluated(self):
        unimpl = [r for r in self.registry["rules"] if r["evaluation"] != "IMPLEMENTED"]
        self.assertTrue(unimpl, "expected at least one explicitly-unimplemented rule (RR-FORECAST-RELIABILITY)")
        for r in unimpl:
            self.assertNotIn(r["rule_id"], rra.EVALUATORS,
                             f"{r['rule_id']} is marked unimplemented but has an evaluator wired in")


class TestAggregateAgainstRealRepoState(unittest.TestCase):
    """Runs against this repo's own real, current state -- not a fixture.
    Each assertion mirrors a fact already independently confirmed elsewhere
    this session (data_source_registry.yml, DASH.readiness, phase2c_gate_status())."""

    @classmethod
    def setUpClass(cls):
        cls.report = rra.aggregate()

    def test_report_shape(self):
        self.assertIn("rules", self.report)
        self.assertIn("open_risk_instance_count", self.report)
        self.assertEqual(self.report["open_risk_instance_count"],
                          sum(len(r["instances"]) for r in self.report["rules"]))

    def test_baseline_drift_rule_ran_clean(self):
        """This repo's full test suite already asserts baselines hold --
        this rule must agree, not invent a different answer."""
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-BASELINE-DRIFT")
        self.assertTrue(rule["evaluated"])
        self.assertEqual(rule["instances"], [])

    def test_source_degraded_flags_the_known_missing_fy26_source(self):
        """offtake_fy26_store_article was registered MISSING earlier this
        session (Phase 2D governance closeout) -- this rule must surface it,
        not silently drop it."""
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-SOURCE-DEGRADED")
        keys = {i["risk_key"] for i in rule["instances"]}
        self.assertIn("RR-SOURCE-DEGRADED::offtake_fy26_store_article", keys)

    def test_source_degraded_never_flags_a_validated_source(self):
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-SOURCE-DEGRADED")
        reg = yaml.safe_load((REPO / "config" / "data_source_registry.yml").read_text())
        validated = {name for name, e in reg["datasets"].items()
                     if e.get("validation_status") in ("VALIDATED", "AVAILABLE")}
        flagged = {i["entity"] for i in rule["instances"]}
        self.assertEqual(flagged & validated, set())

    def test_readiness_gate_matches_datajs_blocked_list(self):
        """DASH.readiness.blocked already names the non-PASS gates -- this
        rule's instance set must agree with it exactly, not approximate it."""
        data = rra.cvd.load_datajs(DATA_JS_PATH)
        gates = rra.cvd.dig(data, "readiness.gates") or {}
        expected = {name for name, g in gates.items() if g.get("status") not in ("PASS", "N/A")}
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-READINESS-GATE")
        got = {i["entity"] for i in rule["instances"]}
        self.assertEqual(got, expected)

    def test_ssg_source_blocked_rule_matches_phase2c_gate_status(self):
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-SSG-SOURCE-BLOCKED")
        live = rra.shr.phase2c_gate_status()
        if live["publication_blocked"]:
            self.assertEqual(len(rule["instances"]), 1)
        else:
            self.assertEqual(rule["instances"], [])

    def test_forecast_reliability_rule_is_skipped_not_faked(self):
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-FORECAST-RELIABILITY")
        self.assertFalse(rule["evaluated"])
        self.assertEqual(rule["instances"], [])
        self.assertEqual(rule["reason"], "NOT_IMPLEMENTED_PHASE_A")


class TestDeterminism(unittest.TestCase):
    def test_same_state_produces_identical_risk_keys_across_runs(self):
        r1 = rra.aggregate()
        r2 = rra.aggregate()
        keys1 = sorted(i["risk_key"] for r in r1["rules"] for i in r["instances"])
        keys2 = sorted(i["risk_key"] for r in r2["rules"] for i in r["instances"])
        self.assertEqual(keys1, keys2)

    def test_output_differs_only_in_timestamp(self):
        r1 = rra.aggregate()
        r2 = rra.aggregate()
        r1.pop("generated_at_utc"); r2.pop("generated_at_utc")
        self.assertEqual(r1, r2)


class TestFixtureIsolation(unittest.TestCase):
    """Synthetic fixtures only -- proves the evaluators generalize beyond
    this repo's own current state, and never crash on an edge case."""

    def test_source_degraded_against_a_synthetic_registry(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "reg.yml"
            p.write_text(yaml.dump({"datasets": {
                "good": {"validation_status": "VALIDATED", "business_owner": "X"},
                "bad": {"validation_status": "MISSING", "business_owner": "Y",
                        "business_name": "Bad Source"},
            }}))
            rule = {"rule_id": "RR-SOURCE-DEGRADED"}
            instances, note = rra.eval_source_degraded(rule, p)
            self.assertEqual(len(instances), 1)
            self.assertEqual(instances[0]["risk_key"], "RR-SOURCE-DEGRADED::bad")
            self.assertEqual(instances[0]["owner"], "Y")

    def test_source_degraded_empty_registry_is_zero_instances_not_an_error(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "reg.yml"
            p.write_text(yaml.dump({"datasets": {}}))
            instances, note = rra.eval_source_degraded({"rule_id": "RR-SOURCE-DEGRADED"}, p)
            self.assertEqual(instances, [])

    def test_baseline_drift_missing_datajs_reports_not_evaluated_not_a_crash(self):
        instances, note = rra.eval_baseline_drift({"rule_id": "RR-BASELINE-DRIFT", "owner": "X"},
                                                    Path("/nonexistent/data.js"))
        self.assertEqual(instances, [])
        self.assertIn("not found", note)


if __name__ == "__main__":
    unittest.main()
