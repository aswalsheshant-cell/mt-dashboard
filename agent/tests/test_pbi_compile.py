"""Tests for pbi_compile: programmatic .pbip semantic-model compilation.

Uses a fixture repo whose DAX library is the REAL committed files (copied in,
so tests stay hermetic while pinning behaviour against the true library) and
a synthetic 4-CSV dataset build.
"""
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.pbi_compile import compile_model

REPO = Path(__file__).resolve().parents[2]


def _write_build_dir(build_dir: Path) -> None:
    build_dir.mkdir(parents=True)
    with open(build_dir / "Fact_OfftakeSales.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["FY", "Month", "Zone", "State", "Chain", "Counter_Type", "EAN", "Brand",
                    "Category", "Sub_Category", "NSV", "MRP_Sales_Value", "Sales_Qty", "Store_Count"])
        w.writerow(["FY27", "May'26", "WEST", "Maharashtra", "Reliance", "Brand Counter",
                    "8900000000001", "Mamaearth", "Face", "Face Wash", "5.0", "995", "5", "3"])
        w.writerow(["FY27", "May'26", "WEST", "Maharashtra", "Reliance", "Non Brand Counter",
                    "8900000000001", "Mamaearth", "Face", "Face Wash", "9.0", "1791", "9", "0"])
    with open(build_dir / "Dim_Date.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["FY", "Month", "MonthNo", "Quarter"])
        w.writerow(["FY27", "May'26", "5", "Q1"])
    with open(build_dir / "Dim_Chain.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Chain", "Account", "Chain Type", "Primary Zone", "Active"])
        w.writerow(["Reliance Retail", "Reliance", "Hypermarket", "Pan India", "Yes"])
        w.writerow(["Azorte", "Reliance", "Beauty Retail", "Pan India", "Yes"])  # non-unique Account on purpose
    with open(build_dir / "Dim_Article.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Article Code", "Article Description", "EAN Code", "Brand", "Category",
                    "Sub-category", "Range", "Pack Size"])
        w.writerow(["ME-FW-1", "Face Wash", "8900000000001", "Mamaearth", "Face", "Face Wash", "Rice", "100 g/ml"])


class TestCompileModel(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "CLAUDE.md").write_text("# fixture repo root marker\n", encoding="utf-8")
        dax_dir = self.root / "PowerBI" / "DAX"
        dax_dir.mkdir(parents=True)
        for name in ("00_DateTable.dax", "01_CoreMeasures.dax", "14_GrowthEngine_Measures.dax"):
            shutil.copy(REPO / "PowerBI" / "DAX" / name, dax_dir / name)
        targets_dir = self.root / "PowerBI" / "SeedData" / "Targets"
        targets_dir.mkdir(parents=True)
        shutil.copy(REPO / "PowerBI" / "SeedData" / "Targets" / "FY2627_Targets.csv",
                    targets_dir / "FY2627_Targets.csv")
        self.build_dir = self.root / "agent" / "pbi_build" / "FY27_May26"
        _write_build_dir(self.build_dir)
        self.cfg = Config(repo_root=str(self.root), index_path="agent/index/index.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_blocked_without_a_dataset_build(self):
        shutil.rmtree(self.build_dir)
        result = compile_model(self.cfg)
        self.assertIn("blocked_reason", result)
        self.assertIn("build-dataset", result["blocked_reason"])

    def test_compiles_pbip_structure_with_relationships_and_gated_measures(self):
        result = compile_model(self.cfg)
        self.assertNotIn("blocked_reason", result)

        pbip = self.root / "PowerBI" / "ModelDefinition.pbip"
        bim_path = self.root / "PowerBI" / "ModelDefinition.SemanticModel" / "model.bim"
        pbir = self.root / "PowerBI" / "ModelDefinition.Report" / "definition.pbir"
        for p in (pbip, bim_path, pbir):
            self.assertTrue(p.exists(), p)

        bim = json.loads(bim_path.read_text(encoding="utf-8"))
        rels = {(r["fromTable"], r["fromColumn"], r["toTable"], r["toColumn"])
                for r in bim["model"]["relationships"]}
        # the three spec relationships (Chain via the distinct-Account dimension;
        # FY+Month composite collapsed to the unique Month label)
        self.assertIn(("Fact Offtake Sales", "Chain", "Chain Master", "Account"), rels)
        self.assertIn(("Fact Offtake Sales", "EAN", "Dim_Article", "EAN Code"), rels)
        self.assertIn(("Fact Offtake Sales", "Month", "Dim_Date", "Month"), rels)

        fact = next(t for t in bim["model"]["tables"] if t["name"] == "Fact Offtake Sales")
        names = [m["name"] for m in fact["measures"]]
        self.assertEqual(len(names), len(set(names)))  # engine rejects duplicates
        for critical in ("NSV", "Offtake NSV (Adjusted)", "Reliance BC NSV", "BC Isolation Check"):
            self.assertIn(critical, names)
        # string literals survive extraction (bodies come from original text,
        # not the comment/string-blanked scan text)
        bc = next(m for m in fact["measures"] if m["name"] == "Reliance BC NSV")
        self.assertIn('"Brand Counter"', bc["expression"])

        # measures the aggregated fact genuinely cannot compute are excluded WITH reasons
        report = json.loads((self.build_dir / "Model_Compile_Report.json").read_text(encoding="utf-8"))
        excluded = {e["name"]: e["reason"] for e in report["excluded_detail"]}
        self.assertIn("Active Stores", excluded)
        self.assertIn("Site Code", excluded["Active Stores"])
        self.assertIn("SOA %", excluded)  # gated Visibility Tracker table absent
        self.assertNotIn("BC Isolation Check", excluded)

        # BuildDir M parameter binds the fixture build, with a trailing separator
        params = {e["name"]: e["expression"] for e in bim["model"]["expressions"]}
        self.assertIn(str(self.build_dir.resolve()).replace("\\", "/") + "/", params["BuildDir"])

    def test_recompile_is_idempotent(self):
        compile_model(self.cfg)
        bim_path = self.root / "PowerBI" / "ModelDefinition.SemanticModel" / "model.bim"
        first = bim_path.read_text(encoding="utf-8")
        compile_model(self.cfg)
        self.assertEqual(first, bim_path.read_text(encoding="utf-8"))

    def test_non_unique_dimension_one_side_is_blocked(self):
        # corrupt Dim_Article so EAN Code repeats -> must block, not emit a
        # .pbip the Tabular engine will reject on load
        with open(self.build_dir / "Dim_Article.csv", "a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow(["ME-FW-2", "Dup EAN", "8900000000001", "Mamaearth",
                                      "Face", "Face Wash", "Rice", "50 g/ml"])
        result = compile_model(self.cfg)
        self.assertIn("blocked_reason", result)
        self.assertIn("EAN Code", result["blocked_reason"])


class TestCompileCommandWorkflow(unittest.TestCase):
    """compile-model must complete step 11 programmatically with evidence --
    no Manual Action Required stop."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "CLAUDE.md").write_text("# fixture repo root marker\n", encoding="utf-8")
        dax_dir = self.root / "PowerBI" / "DAX"
        dax_dir.mkdir(parents=True)
        for name in ("00_DateTable.dax", "01_CoreMeasures.dax", "14_GrowthEngine_Measures.dax"):
            shutil.copy(REPO / "PowerBI" / "DAX" / name, dax_dir / name)
        (self.root / "PowerBI" / "SeedData" / "Targets").mkdir(parents=True)
        shutil.copy(REPO / "PowerBI" / "SeedData" / "Targets" / "FY2627_Targets.csv",
                    self.root / "PowerBI" / "SeedData" / "Targets" / "FY2627_Targets.csv")
        _write_build_dir(self.root / "agent" / "pbi_build" / "FY27_May26")
        (self.root / "agent").mkdir(exist_ok=True)
        config_path = self.root / "agent" / "config.json"
        config_path.write_text(json.dumps({"repo_root": str(self.root),
                                            "index_path": "agent/index/index.json"}), encoding="utf-8")
        self.config_path = config_path

    def tearDown(self):
        self.tmp.cleanup()

    def test_compile_model_completes_step_11_with_metadata_evidence(self):
        from mtagent.cli import main
        from mtagent.pbi_workflow import WorkflowController

        rc = main(["--config", str(self.config_path), "pbi", "compile-model"])
        self.assertEqual(rc, 0)

        cfg = Config(repo_root=str(self.root), index_path="agent/index/index.json")
        controller = WorkflowController(cfg)
        step = controller.state.steps["manual_desktop_actions"]
        self.assertIn(step["status"], ("Completed", "Completed with Warning"))
        # evidence is the machine-generated compile metadata, not a bare flip
        self.assertIn("critical_measures_verified", step["validation_result"])
        self.assertIn("ModelDefinition.pbip", step["output_file"])
        # never stops at Manual Action Required
        self.assertIsNone(controller.next_manual_step())


if __name__ == "__main__":
    unittest.main()
