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

    def test_forecast_method_fallback_never_flags_a_string_it_does_not_recognize(self):
        """Regression: the live data.js's forecast.method does not match
        either function's current exact template (data.js can trail the
        generator by a build or two). A rule that positive-matches the
        authoritative phrase instead of the fallback's own signature would
        false-positive on this exact file -- this pins that down."""
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-FORECAST-METHOD-FALLBACK")
        data = rra.cvd.load_datajs(DATA_JS_PATH)
        method = rra.cvd.dig(data, "forecast.method") or ""
        if "Seasonally-indexed run-rate" in method:
            self.assertEqual(len(rule["instances"]), 1)
        else:
            self.assertEqual(rule["instances"], [])

    def test_forecast_growth_clamped_never_flags_the_unclamped_ty_target_path(self):
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-FORECAST-GROWTH-CLAMPED")
        data = rra.cvd.load_datajs(DATA_JS_PATH)
        method = rra.cvd.dig(data, "forecast.method") or ""
        if "Seasonally-indexed run-rate" not in method:
            self.assertEqual(rule["instances"], [],
                             "must never flag a clamp hit outside the seasonal-projection path")

    def test_allocation_fallback_reports_not_available_when_qc_absent(self):
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-ALLOCATION-FALLBACK")
        data = rra.cvd.load_datajs(DATA_JS_PATH)
        qc = rra.cvd.dig(data, "chain_allocation_qc")
        if not qc:
            self.assertEqual(rule["instances"], [])
            self.assertIn("NOT_AVAILABLE", rule["note"])

    def test_mapping_completeness_degraded_matches_mapping_health_rag(self):
        rule = next(r for r in self.report["rules"] if r["rule_id"] == "RR-MAPPING-COMPLETENESS-DEGRADED")
        data = rra.cvd.load_datajs(DATA_JS_PATH)
        mh = rra.cvd.dig(data, "mapping_health") or {}
        expected = {fy for fy, e in (mh.get("by_fy") or {}).items() if e.get("rag") != "green"}
        got = {i["entity"] for i in rule["instances"]}
        self.assertEqual(got, expected)


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


class TestPatchIntoDatajs(unittest.TestCase):
    """The one place this module writes anything -- proves it's additive-only."""

    def test_patch_adds_only_risk_snapshot_and_changes_nothing_else(self):
        """DATA_JS_PATH is the real dashboard/data.js, which this same Phase C
        pass patches in place -- so it may already carry risk_snapshot by the
        time this test runs (from a prior --patch-into-datajs call, or from a
        previous test run against this real file). The invariant that
        actually matters, and holds regardless of starting state: re-patching
        touches risk_snapshot and NOTHING else -- never a second key, never a
        change to any other key's value."""
        import shutil, tempfile
        with tempfile.TemporaryDirectory() as td:
            copy_path = Path(td) / "data.js"
            shutil.copy(DATA_JS_PATH, copy_path)
            before = rra.cvd.load_datajs(copy_path)

            rra.patch_into_datajs(copy_path)

            after = rra.cvd.load_datajs(copy_path)
            self.assertIn("risk_snapshot", after)
            before_other = {k: v for k, v in before.items() if k != "risk_snapshot"}
            after_other = {k: v for k, v in after.items() if k != "risk_snapshot"}
            self.assertEqual(set(after_other.keys()), set(before_other.keys()))
            for k in before_other:
                self.assertEqual(json.dumps(before_other[k], sort_keys=True),
                                 json.dumps(after_other[k], sort_keys=True),
                                 f"existing key {k!r} was altered by the patch")

    def test_patched_snapshot_matches_a_direct_aggregate_call(self):
        import shutil, tempfile
        with tempfile.TemporaryDirectory() as td:
            copy_path = Path(td) / "data.js"
            shutil.copy(DATA_JS_PATH, copy_path)
            direct = rra.aggregate(data_js_path=copy_path)
            patched_report = rra.patch_into_datajs(copy_path)
            for a, b in zip(direct["rules"], patched_report["rules"]):
                self.assertEqual(a["rule_id"], b["rule_id"])
                self.assertEqual(len(a["instances"]), len(b["instances"]))

    def test_patch_rejects_a_file_that_is_not_a_datajs(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "not_data.js"
            p.write_text("console.log('nope');")
            with self.assertRaises(SystemExit):
                rra.patch_into_datajs(p)

    def test_report_carries_rule_name_and_family_for_dashboard_rendering(self):
        report = rra.aggregate()
        for r in report["rules"]:
            self.assertIn("rule_name", r)
            self.assertIn("risk_family", r)
            self.assertTrue(r["rule_name"])
            self.assertTrue(r["risk_family"])


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

    @staticmethod
    def _fixture_datajs(tmp_path, obj):
        import json
        p = Path(tmp_path) / "data.js"
        p.write_text("window.DASH = " + json.dumps(obj) + ";\n")
        return p

    def test_forecast_method_fallback_flags_the_seasonal_signature(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = self._fixture_datajs(td, {"forecast": {
                "method": "Seasonally-indexed run-rate: FY26 monthly seasonality applied "
                          "to a forward base grown at the realised offtake YoY rate (clamped 0-60%)."}})
            instances, note = rra.eval_forecast_method_fallback({"rule_id": "RR-FORECAST-METHOD-FALLBACK", "owner": "X"}, p)
            self.assertEqual(len(instances), 1)
            self.assertEqual(instances[0]["severity"], "SEASONAL_ESTIMATE")

    def test_forecast_method_fallback_does_not_flag_an_unrelated_method_string(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = self._fixture_datajs(td, {"forecast": {"method": "Some other method entirely."}})
            instances, note = rra.eval_forecast_method_fallback({"rule_id": "RR-FORECAST-METHOD-FALLBACK", "owner": "X"}, p)
            self.assertEqual(instances, [])

    def test_forecast_growth_clamped_fires_only_on_seasonal_path_at_ceiling(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = self._fixture_datajs(td, {"forecast": {
                "method": "Seasonally-indexed run-rate: clamped 0-60%.", "growth_assumption_pct": 60.0}})
            instances, note = rra.eval_forecast_growth_clamped({"rule_id": "RR-FORECAST-GROWTH-CLAMPED", "owner": "X"}, p)
            self.assertEqual(len(instances), 1)

    def test_forecast_growth_clamped_ignores_high_growth_on_ty_target_path(self):
        """A real >=60% TY target growth is a legitimate business ambition on
        this path (unclamped) -- must never be misread as a clamp artifact."""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = self._fixture_datajs(td, {"forecast": {
                "method": "FY27 = the business's own TY target.", "growth_assumption_pct": 75.0}})
            instances, note = rra.eval_forecast_growth_clamped({"rule_id": "RR-FORECAST-GROWTH-CLAMPED", "owner": "X"}, p)
            self.assertEqual(instances, [])

    def test_allocation_fallback_flags_reconciliation_failure(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = self._fixture_datajs(td, {"chain_allocation_qc": {
                "reconciliation_passed": False, "variance_lakh": 12.5, "variance_pct": 0.3,
                "tier1_rows": 100, "tier2_rows": 20, "tier3_rows": 5, "total_dist_rows_processed": 125}})
            instances, note = rra.eval_allocation_fallback({"rule_id": "RR-ALLOCATION-FALLBACK", "owner": "X"}, p)
            self.assertEqual(len(instances), 1)
            self.assertEqual(instances[0]["severity"], "RECONCILIATION_FAILED")

    def test_allocation_fallback_reconciled_true_is_zero_instances(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = self._fixture_datajs(td, {"chain_allocation_qc": {
                "reconciliation_passed": True, "tier1_rows": 100, "tier2_rows": 20,
                "tier3_rows": 5, "total_dist_rows_processed": 125}})
            instances, note = rra.eval_allocation_fallback({"rule_id": "RR-ALLOCATION-FALLBACK", "owner": "X"}, p)
            self.assertEqual(instances, [])
            self.assertIn("tier3", note)

    def test_mapping_completeness_degraded_flags_non_green_fy_only(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            p = self._fixture_datajs(td, {"mapping_health": {
                "exception_count": 3, "exception_nsv": 45.0,
                "by_fy": {
                    "FY26": {"rag": "green", "completeness_pct": 99.0, "unmapped_nsv": 1.0},
                    "FY27": {"rag": "amber", "completeness_pct": 88.0, "unmapped_nsv": 45.0},
                }}})
            instances, note = rra.eval_mapping_completeness_degraded(
                {"rule_id": "RR-MAPPING-COMPLETENESS-DEGRADED", "owner": "X"}, p)
            self.assertEqual(len(instances), 1)
            self.assertEqual(instances[0]["entity"], "FY27")
            self.assertEqual(instances[0]["severity"], "amber")


if __name__ == "__main__":
    unittest.main()
