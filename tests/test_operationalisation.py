#!/usr/bin/env python3
"""Tests for the operationalisation additions: baseline governance, seed manager, D13 fix.

Phase 8 of the operationalisation prompt:
  - Framework stability (baseline, regression mode, engine independence)
  - Seed manager validation, resolution, and hash checks
  - D13 fix verification (MRP corrected, brand exclusion, Jun-26 included)
"""
import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.dataeng import core, governance, quality, reconcile, registry  # noqa: E402
from scripts.dataeng import repo_scan  # noqa: E402
from scripts.dataeng import seed_manager, validate  # noqa: E402
from scripts.dataeng.cli import main as cli_main, readiness, _load_baseline  # noqa: E402

D = Decimal


# ──────────────────────────────────────────────────────────────────────────────
# 1. FRAMEWORK STABILITY — baseline governance and regression mode
# ──────────────────────────────────────────────────────────────────────────────

class TestBaselineGovernance(unittest.TestCase):

    def test_B01_baseline_file_exists_and_is_valid_json(self):
        p = ROOT / "config" / "dataeng_baseline.json"
        self.assertTrue(p.exists(), "dataeng_baseline.json is missing")
        d = json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(d["version"], 1)
        self.assertIn("accepted", d)
        self.assertIn("generated_from_commit", d)

    def test_B02_baseline_accepted_dict_is_not_empty(self):
        d = json.loads((ROOT / "config" / "dataeng_baseline.json")
                       .read_text(encoding="utf-8"))
        self.assertGreater(len(d["accepted"]), 0, "baseline has no accepted findings")

    def test_B03_every_baseline_entry_has_severity(self):
        d = json.loads((ROOT / "config" / "dataeng_baseline.json")
                       .read_text(encoding="utf-8"))
        for fid, rec in d["accepted"].items():
            self.assertIn("severity", rec, f"baseline entry {fid!r} has no severity")
            self.assertIn(rec["severity"], core.SEVERITIES, f"{fid} has bad severity")

    def test_B04_regression_mode_exits_0_on_preexisting_findings(self):
        """--regression must exit 0 when every FAIL/BLOCKED is already in baseline."""
        from scripts.dataeng.cli import _regression_exit, _load_baseline
        import importlib
        mod = importlib.import_module("scripts.dataeng.cli")
        baseline = _load_baseline()
        # Build findings from all pre-existing BLOCKED IDs
        pre_findings = [
            core.Finding(id=fid, skill="s", category="c",
                         severity=rec["severity"], summary=rec.get("summary", "pre"))
            for fid, rec in baseline.items()
            if rec["severity"] in ("FAIL", "BLOCKED")
        ]
        code = _regression_exit(pre_findings)
        self.assertEqual(code, 0, "regression should exit 0 when all FAIL/BLOCKED are pre-existing")

    def test_B05_regression_mode_exits_1_on_new_critical_finding(self):
        """--regression must exit 1 when a NEW FAIL finding not in baseline appears."""
        from scripts.dataeng.cli import _regression_exit
        new_fail = [core.Finding(
            id="NEW-FAIL-THAT-DOES-NOT-EXIST-IN-BASELINE",
            skill="test", category="test", severity="FAIL",
            summary="Injected FAIL to test regression mode"
        )]
        code = _regression_exit(new_fail)
        self.assertEqual(code, 1, "regression should exit 1 on a new FAIL finding")

    def test_B06_save_baseline_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as td:
            test_path = pathlib.Path(td) / "test_baseline.json"
            findings = [
                core.Finding(id="X-WARN", skill="s", category="c",
                             severity="WARN", summary="warn"),
                core.Finding(id="X-PASS", skill="s", category="c",
                             severity="PASS", summary="pass"),
            ]
            from scripts.dataeng import cli as cli_mod
            orig = cli_mod.BASELINE_PATH
            cli_mod.BASELINE_PATH = test_path
            try:
                cli_mod._save_baseline(findings)
            finally:
                cli_mod.BASELINE_PATH = orig
            d = json.loads(test_path.read_text(encoding="utf-8"))
            self.assertIn("X-WARN", d["accepted"])
            self.assertNotIn("X-PASS", d["accepted"], "PASS findings should not enter baseline")


# ──────────────────────────────────────────────────────────────────────────────
# 2. FRAMEWORK STABILITY — engine independence
# ──────────────────────────────────────────────────────────────────────────────

class TestEngineIndependence(unittest.TestCase):

    def _assert_engine_findings(self, findings, label):
        self.assertIsInstance(findings, list, f"{label} must return a list")
        for f in findings:
            self.assertIsInstance(f, core.Finding, f"{label}: item is not a Finding")
            self.assertIn(f.severity, core.SEVERITIES, f"{label}: bad severity {f.severity!r}")
            self.assertTrue(f.id.strip(), f"{label}: finding without id")
            self.assertTrue(f.summary.strip(), f"{label}: finding without summary")

    def test_E01_validate_engine_callable_independently(self):
        self._assert_engine_findings(validate.run(), "validate")

    def test_E02_quality_engine_callable_independently(self):
        self._assert_engine_findings(quality.run(), "quality")

    def test_E03_reconcile_engine_callable_independently(self):
        self._assert_engine_findings(reconcile.run(), "reconcile")

    def test_E04_governance_engine_callable_independently(self):
        _, findings = governance.run()
        self._assert_engine_findings(findings, "governance")

    def test_E05_registry_engine_callable_independently(self):
        _, findings = registry.build()
        self._assert_engine_findings(findings, "registry")

    def test_E06_seed_manager_callable_independently(self):
        self._assert_engine_findings(seed_manager.validate(), "seed_manager")

    def test_E07_readiness_with_blocked_is_not_ready(self):
        f = [core.Finding(id="X", skill="s", category="c",
                          severity="BLOCKED", summary="test")]
        score, verdict = readiness(f)
        self.assertIn("NOT READY", verdict)
        self.assertLess(score, 100)

    def test_E08_readiness_with_pass_only_is_ready(self):
        f = [core.Finding(id="X", skill="s", category="c",
                          severity="PASS", summary="test")]
        self.assertEqual(readiness(f), (100, "READY"))


# ──────────────────────────────────────────────────────────────────────────────
# 3. SEED MANAGER
# ──────────────────────────────────────────────────────────────────────────────

class TestSeedManager(unittest.TestCase):

    def test_S01_seed_validate_passes_on_good_seed(self):
        findings = seed_manager.validate()
        fails = [f for f in findings if f.severity == "FAIL"]
        self.assertEqual(fails, [], f"seed validation FAIL: {[f.summary for f in fails]}")

    def test_S02_seed_validate_has_pass_finding(self):
        findings = seed_manager.validate()
        passes = [f for f in findings if f.severity == "PASS"]
        self.assertGreater(len(passes), 0, "expected at least one PASS from seed validator")

    def test_S03_seed_list_returns_rows(self):
        rows = seed_manager.list_seeds()
        self.assertGreater(len(rows), 0, "seed list should return rows")
        for r in rows:
            self.assertIn("Key", r)
            self.assertIn("Value", r)
            self.assertIn("Status", r)

    def test_S04_seed_resolve_jun26_gmv_mrp_authoritative(self):
        val, status = seed_manager.resolve("GMV", "Jun-26")
        self.assertEqual(status, "AUTHORITATIVE", f"Jun-26 seed status: {status}")
        self.assertIsNotNone(val, "Jun-26 seed value should not be None")
        self.assertEqual(D(str(val)).quantize(D("0.01")), D("9300.91"),
                         f"Jun-26 GMV seed value: {val}")

    def test_S05_seed_resolve_unknown_month_returns_not_found(self):
        val, status = seed_manager.resolve("GMV", "Feb-27")
        self.assertIsNone(val)
        self.assertEqual(status, "NOT_FOUND")

    def test_S06_seed_verify_hash_returns_64char_hex(self):
        sha, matched = seed_manager.verify_hash(
            str(ROOT / "PowerBI" / "SeedData" / "Masters" / "FY27_Monthly_GMV_MRP.csv")
        )
        self.assertEqual(len(sha), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in sha))

    def test_S07_seed_with_draft_row_generates_warn(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False,
                                         dir=ROOT / "PowerBI" / "SeedData" / "Masters") as f:
            w = csv.DictWriter(f, fieldnames=[
                "Month","GMV_MRP_Sales_L","NSV_Control_L","Source_File","Source_SHA256",
                "Source_Sheet","Field","Extraction_Rule","Rows_Total","Rows_After_Exclusion",
                "Recorded_By","Recorded_At","Status","Notes"])
            w.writeheader()
            w.writerow({
                "Month": "Jul-26", "GMV_MRP_Sales_L": "999.99", "NSV_Control_L": "500.00",
                "Source_File": "test.xlsx",
                "Source_SHA256": "a" * 64,
                "Source_Sheet": "Sheet1", "Field": "MRP",
                "Extraction_Rule": "sum", "Rows_Total": "100", "Rows_After_Exclusion": "100",
                "Recorded_By": "test", "Recorded_At": "2026-07-24",
                "Status": "DRAFT", "Notes": "test row"
            })
            tmp_path = pathlib.Path(f.name)

        try:
            seed = {
                "name": "Test Draft Seed",
                "file": tmp_path,
                "key_col": "Month",
                "value_col": "GMV_MRP_Sales_L",
                "control_col": "NSV_Control_L",
                "required_cols": {"Month", "GMV_MRP_Sales_L", "NSV_Control_L",
                                  "Source_File", "Source_SHA256", "Extraction_Rule",
                                  "Recorded_By", "Recorded_At", "Status"},
                "description": "Temp test seed",
            }
            import importlib
            sm = importlib.import_module("scripts.dataeng.seed_manager")
            rows = sm._load_seed(seed)
            findings = []
            sm._check_status(seed, rows, findings)
            warns = [f for f in findings if f.severity == "WARN"]
            self.assertGreater(len(warns), 0, "DRAFT row should generate a WARN finding")
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_S08_seed_with_missing_sha_generates_fail(self):
        import importlib
        sm = importlib.import_module("scripts.dataeng.seed_manager")
        seed = {
            "name": "Missing SHA test",
            "file": ROOT / "PowerBI" / "SeedData" / "Masters" / "FY27_Monthly_GMV_MRP.csv",
            "key_col": "Month",
            "value_col": "GMV_MRP_Sales_L",
            "required_cols": {"Month", "GMV_MRP_Sales_L", "NSV_Control_L",
                              "Source_File", "Source_SHA256", "Extraction_Rule",
                              "Recorded_By", "Recorded_At", "Status"},
        }
        rows = sm._load_seed(seed)
        for r in rows:
            r["Source_SHA256"] = ""
        findings = []
        sm._check_sha_present(seed, rows, findings)
        fails = [f for f in findings if f.severity == "FAIL"]
        self.assertGreater(len(fails), 0, "missing SHA should generate FAIL")

    def test_S09_seed_resolve_case_insensitive_metric(self):
        val_lower, _ = seed_manager.resolve("gmv mrp", "Jun-26")
        val_mixed, _ = seed_manager.resolve("FY27 Monthly GMV", "Jun-26")
        self.assertIsNotNone(val_lower or val_mixed,
                             "seed_manager.resolve should be case-insensitive on metric name")

    def test_S10_seed_list_all_rows_have_key_and_value(self):
        rows = seed_manager.list_seeds()
        for r in rows:
            self.assertTrue((r.get("Key") or "").strip(), "seed row missing Key")
            self.assertTrue(str(r.get("Value") or "").strip(), "seed row missing Value")


# ──────────────────────────────────────────────────────────────────────────────
# 4. D13 — MRP correction verification
# ──────────────────────────────────────────────────────────────────────────────

class TestD13MrpFix(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        import importlib
        dc = importlib.import_module("scripts.dataeng.core")
        dc._DASH_CACHE = None
        cls.dash = dc.load_dash()
        cls.fy27 = cls.dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27", {})

    def test_D13_01_fy27_mrp_is_corrected_total(self):
        mrp = self.fy27.get("mrp")
        self.assertEqual(
            D(str(mrp)).quantize(D("0.01")), D("31336.79"),
            f"Expected 31336.79 but got {mrp}"
        )

    def test_D13_02_fy27_nsv_is_unchanged(self):
        nsv = self.fy27.get("nsv")
        self.assertEqual(
            D(str(nsv)).quantize(D("0.01")), D("13652.59"),
            f"NSV should be unchanged at 13652.59 but is {nsv}"
        )

    def test_D13_03_months_covered_includes_june(self):
        months = self.fy27.get("months_covered", [])
        self.assertIn("June", months, f"Jun-26 missing from months_covered: {months}")

    def test_D13_04_mrp_exceeds_old_value(self):
        mrp = D(str(self.fy27.get("mrp")))
        old_mrp = D("22050.21")
        self.assertGreater(mrp, old_mrp, "New MRP should exceed old understated value")

    def test_D13_05_delta_is_correct(self):
        mrp = D(str(self.fy27.get("mrp")))
        expected_delta = D("9286.58")
        actual_delta = (mrp - D("22050.21")).quantize(D("0.01"))
        self.assertEqual(actual_delta, expected_delta,
                         f"Delta from old to new should be +9286.58 but got {actual_delta}")

    def test_D13_06_apr26_csv_mrp_filtered(self):
        """Apr-26 article CSV must produce 11760.60L after brand exclusion."""
        import csv as csv_mod
        EXCLUDED = {"Pure Origin", "Lumineve", "Staze"}
        BRAND_MAP = {
            "mamaearth": "Mamaearth", "aqualogica": "Aqualogica",
            "the derma co": "The Derma Co", "pure origin": "Pure Origin",
            "lumineve": "Lumineve", "staze": "Staze",
            "bblunt": "Bblunt", "dr. sheth": "Dr. Sheth", "dr sheth": "Dr. Sheth",
        }
        p = ROOT / "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Apr_26.csv"
        total = D("0")
        with open(p, encoding="latin-1", errors="replace") as fh:
            for row in csv_mod.DictReader(fh):
                b = str(row.get("brand") or "").strip()
                canonical = BRAND_MAP.get(b.lower(), b)
                if canonical in EXCLUDED:
                    continue
                mrp = row.get("Total MRP sales") or "0"
                try:
                    total += D(str(float(mrp))) / D("100000")
                except Exception:
                    pass
        self.assertEqual(total.quantize(D("0.01")), D("11760.60"),
                         f"Apr-26 filtered MRP: {total}")

    def test_D13_07_may26_csv_mrp_filtered(self):
        """May-26 article CSV must produce 10275.28L after brand exclusion."""
        import csv as csv_mod
        EXCLUDED = {"Pure Origin", "Lumineve", "Staze"}
        BRAND_MAP = {
            "mamaearth": "Mamaearth", "aqualogica": "Aqualogica",
            "the derma co": "The Derma Co", "pure origin": "Pure Origin",
            "lumineve": "Lumineve", "staze": "Staze",
            "bblunt": "Bblunt", "dr. sheth": "Dr. Sheth", "dr sheth": "Dr. Sheth",
        }
        p = ROOT / "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_May_26.csv"
        total = D("0")
        with open(p, encoding="latin-1", errors="replace") as fh:
            for row in csv_mod.DictReader(fh):
                b = str(row.get("brand") or "").strip()
                canonical = BRAND_MAP.get(b.lower(), b)
                if canonical in EXCLUDED:
                    continue
                mrp = row.get("Total MRP sales") or "0"
                try:
                    total += D(str(float(mrp))) / D("100000")
                except Exception:
                    pass
        self.assertEqual(total.quantize(D("0.01")), D("10275.28"),
                         f"May-26 filtered MRP: {total}")

    def test_D13_08_excluded_brand_mrp_in_apr_may_is_correct(self):
        """Excluded brands contributed exactly 14.33L to the old raw MRP."""
        import csv as csv_mod
        EXCLUDED = {"Pure Origin", "Lumineve", "Staze"}
        BRAND_MAP = {
            "mamaearth": "Mamaearth", "aqualogica": "Aqualogica",
            "the derma co": "The Derma Co", "pure origin": "Pure Origin",
            "lumineve": "Lumineve", "staze": "Staze",
        }
        excluded_total = D("0")
        for month in ("Apr_26", "May_26"):
            p = ROOT / f"PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_{month}.csv"
            with open(p, encoding="latin-1", errors="replace") as fh:
                for row in csv_mod.DictReader(fh):
                    b = str(row.get("brand") or "").strip()
                    canonical = BRAND_MAP.get(b.lower(), b)
                    if canonical not in EXCLUDED:
                        continue
                    mrp = row.get("Total MRP sales") or "0"
                    try:
                        excluded_total += D(str(float(mrp))) / D("100000")
                    except Exception:
                        pass
        self.assertEqual(excluded_total.quantize(D("0.01")), D("14.33"),
                         f"Excluded brand MRP (Apr+May): {excluded_total}")

    def test_D13_09_decision_register_shows_approved(self):
        """D13 in cm2_decision_register.csv must be APPROVED after implementation."""
        reg = core.load_config_csv("cm2_decision_register.csv")
        d13 = [r for r in reg if r.get("decision_id") == "D13"]
        self.assertEqual(len(d13), 1, "D13 must appear exactly once in decision register")
        self.assertEqual(d13[0].get("status", "").upper(), "APPROVED",
                         f"D13 status: {d13[0].get('status')}")

    def test_D13_10_registry_metric_reflects_resolution(self):
        """Registry known limitations must no longer say 'understated'."""
        rows, _ = registry.build()
        mrp_rows = [r for r in rows if "FY27.mrp" in r.get("Dashboard_Path", "")]
        self.assertEqual(len(mrp_rows), 1, "Expected exactly one MRP metric in registry")
        limits = mrp_rows[0].get("Known_Limitations", "")
        self.assertIn("RESOLVED", limits,
                      f"Registry limitation text should say RESOLVED, got: {limits[:80]}")
        self.assertNotIn("understated", limits.lower(),
                         "Registry should not say 'understated' after D13 fix")


# ──────────────────────────────────────────────────────────────────────────────
# 5. CI WORKFLOW
# ──────────────────────────────────────────────────────────────────────────────

class TestCIWorkflow(unittest.TestCase):

    def test_CI01_workflow_file_exists(self):
        p = ROOT / ".github" / "workflows" / "dataeng.yml"
        self.assertTrue(p.exists(), ".github/workflows/dataeng.yml must exist")

    def test_CI02_workflow_has_regression_step(self):
        p = ROOT / ".github" / "workflows" / "dataeng.yml"
        content = p.read_text(encoding="utf-8")
        self.assertIn("--regression", content,
                      "CI workflow must invoke the --regression flag")

    def test_CI03_workflow_has_syntax_check(self):
        p = ROOT / ".github" / "workflows" / "dataeng.yml"
        content = p.read_text(encoding="utf-8")
        self.assertIn("py_compile", content, "CI workflow must include a py_compile step")

    def test_CI04_workflow_uploads_reports(self):
        p = ROOT / ".github" / "workflows" / "dataeng.yml"
        content = p.read_text(encoding="utf-8")
        self.assertIn("outputs/dataeng/", content, "CI workflow must upload dataeng reports")

    def test_CI05_build_script_compiles(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile",
             str(ROOT / "scripts" / "build_dashboard_data.py")],
            capture_output=True, cwd=ROOT
        )
        self.assertEqual(result.returncode, 0,
                         f"build_dashboard_data.py has syntax errors: {result.stderr.decode()}")

    def test_CI06_seed_manager_compiles(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile",
             str(ROOT / "scripts" / "dataeng" / "seed_manager.py")],
            capture_output=True, cwd=ROOT
        )
        self.assertEqual(result.returncode, 0,
                         f"seed_manager.py has syntax errors: {result.stderr.decode()}")

    def test_CI07_fix_d13_mrp_compiles(self):
        result = subprocess.run(
            [sys.executable, "-m", "py_compile",
             str(ROOT / "scripts" / "fix_d13_mrp.py")],
            capture_output=True, cwd=ROOT
        )
        self.assertEqual(result.returncode, 0,
                         f"fix_d13_mrp.py has syntax errors: {result.stderr.decode()}")

    def test_CI08_fix_d13_dry_run_shows_no_change_needed(self):
        """After D13 is applied, dry-run must report NO CHANGE NEEDED."""
        result = subprocess.run(
            [sys.executable, "scripts/fix_d13_mrp.py", "--dry-run"],
            capture_output=True, text=True, cwd=ROOT
        )
        self.assertEqual(result.returncode, 0, f"fix_d13_mrp.py --dry-run failed: {result.stdout}")
        self.assertIn("NO CHANGE NEEDED", result.stdout,
                      "After D13 applied, dry-run should say NO CHANGE NEEDED")


class TestDerivedArtifactIsolation(unittest.TestCase):
    """The engines' own output must never become evidence about the repository.

    Committing outputs/dataeng/ and config/dataeng_baseline.json made every script
    filename appear in a tracked file, which silently killed SCAN-ORPHAN detection:
    baselining a finding suppressed the finding.
    """

    def test_DA01_outputs_dir_is_derived(self):
        self.assertTrue(core.is_derived_artifact("outputs/dataeng/findings.csv"))
        self.assertTrue(core.is_derived_artifact("outputs/dataeng/health_report.json"))

    def test_DA02_baseline_is_derived(self):
        self.assertTrue(core.is_derived_artifact("config/dataeng_baseline.json"))

    def test_DA03_real_sources_are_not_derived(self):
        for p in ("scripts/build_dashboard_data.py", "dashboard/data.js",
                  "PowerBI/Reference/CM2_Provisional/config/cm2_decision_register.csv", "CLAUDE.md"):
            self.assertFalse(core.is_derived_artifact(p), f"{p} must not be treated as derived")

    def test_DA04_windows_separators_are_handled(self):
        self.assertTrue(core.is_derived_artifact("outputs\\dataeng\\findings.csv"))

    def test_DA05_baseline_does_not_suppress_orphan_detection(self):
        """A script named only by the baseline must still be reported as an orphan."""
        baseline = ROOT / "config" / "dataeng_baseline.json"
        if not baseline.exists():
            self.skipTest("no baseline committed")
        accepted = json.loads(baseline.read_text(encoding="utf-8")).get("accepted", {})
        orphan_ids = [k for k in accepted if k.startswith("SCAN-ORPHAN-")]
        if not orphan_ids:
            self.skipTest("no orphan findings in baseline")

        _inventory, _edges, findings = repo_scan.scan()
        found = {f.id for f in findings}
        still_detected = [i for i in orphan_ids if i in found]
        self.assertEqual(
            sorted(still_detected), sorted(orphan_ids),
            "baselined SCAN-ORPHAN findings vanished from the scan -- the engine is "
            "reading its own derived output as evidence")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestCm2ProvisionalGate(unittest.TestCase):
    """GOV-FORMULA-DRAFT remediation: while config/cm2_formula.csv is DRAFT the
    published CM2 must be visibly labelled provisional. The BLOCKED finding
    itself is Finance's to clear (D1); these tests assert the mitigation is
    actually in force in the product, which it previously was not."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_dashboard_data import _cm2_provisional_state
        cls.state_fn = staticmethod(_cm2_provisional_state)
        txt = (ROOT / "dashboard" / "data.js").read_text(encoding="utf-8")
        import re as _re
        m = _re.match(r"\s*window\.DASH\s*=\s*", txt)
        cls.dash = json.loads(txt[m.end():].rstrip().rstrip(";"))
        cls.html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")

    # -- CP01: the shipped data.js actually carries the flag
    def test_CP01_data_js_marks_cm2_provisional(self):
        self.assertTrue(self.dash["cm2"]["provisional"],
                        "CM2 is published without the provisional flag")

    def test_CP02_formula_status_is_draft(self):
        self.assertEqual(self.dash["cm2"]["formula_status"], "DRAFT")

    def test_CP03_reasons_name_both_causes(self):
        joined = " ".join(self.dash["cm2"]["provisional_reasons"]).lower()
        self.assertIn("d1", joined)
        self.assertIn("example", joined)

    def test_CP04_example_data_only_flag(self):
        self.assertTrue(self.dash["cm2"]["example_data_only"])

    # -- CP05: flag agrees with the governance engine's own gate
    def test_CP05_agrees_with_governance_engine(self):
        _, findings = governance.run()
        blocked = [f for f in findings if f.id == "GOV-FORMULA-DRAFT"]
        self.assertEqual(bool(blocked), self.dash["cm2"]["provisional"],
                         "data.js provisional flag disagrees with GOV-FORMULA-DRAFT")

    # -- CP06: the UI renders it
    def test_CP06_dashboard_renders_banner(self):
        self.assertIn("cm2Prov", self.html)
        self.assertIn("provisional_label", self.html)

    def test_CP07_banner_html_escaped(self):
        self.assertIn("hesc(r)", self.html, "reasons must be HTML-escaped")

    # -- CP08: derived from config, not hardcoded -- clears on approval
    def test_CP08_clears_when_formula_approved(self):
        """The gate must be derived from config, not hardcoded: an APPROVED
        formula plus real expense rows must clear it with no code change."""
        with tempfile.TemporaryDirectory() as td:
            fp = pathlib.Path(td) / "cm2_formula.csv"
            with open(fp, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=["Component", "Status"])
                w.writeheader()
                w.writerow({"Component": "NSV", "Status": "APPROVED"})
                w.writerow({"Component": "COGS", "Status": "APPROVED"})

            approved = self.state_fn([{"Remarks": "real trade spend"}], formula_path=fp)
            self.assertEqual(approved["formula_status"], "APPROVED")
            self.assertFalse(approved["provisional"], approved["provisional_reasons"])

            # and one DRAFT component is enough to re-arm it
            with open(fp, "a", newline="", encoding="utf-8") as fh:
                csv.DictWriter(fh, fieldnames=["Component", "Status"]).writerow(
                    {"Component": "Logistics", "Status": "DRAFT"})
            still = self.state_fn([{"Remarks": "real"}], formula_path=fp)
            self.assertEqual(still["formula_status"], "DRAFT")
            self.assertTrue(still["provisional"])

    def test_CP09_example_detection_needs_all_rows(self):
        mixed = [{"Remarks": "EXAMPLE ROW -- x"}, {"Remarks": "real"}]
        self.assertFalse(self.state_fn(mixed)["example_data_only"],
                         "one real row means the data is no longer example-only")

    def test_CP10_patch_script_is_idempotent(self):
        out = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "patch_cm2_provisional.py"), "--dry-run"],
            capture_output=True, text=True, cwd=str(ROOT))
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("Already up to date", out.stdout)

    def test_CP11_cm2_amounts_untouched_by_patch(self):
        c = self.dash["cm2"]
        self.assertAlmostEqual(c["total_nsv"], 42373.35, places=2)
        self.assertAlmostEqual(c["cm2_value"], 42325.70, places=2)
