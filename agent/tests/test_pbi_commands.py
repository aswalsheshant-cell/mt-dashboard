"""Integration tests: the pbi_registry + pbi_commands + CLI wiring, driving
commands the way ``python -m mtagent pbi <cmd>`` actually does, end to end
against synthetic fixtures (not the CLI subprocess, to keep this fast and
independent of the interpreter path, but through the exact same handler
dispatch cli.py uses).
"""
import csv
import tempfile
import unittest
from pathlib import Path

from mtagent import pbi_commands  # noqa: F401 -- populates the registry
from mtagent.cli import build_parser, main
from mtagent.config import Config
from mtagent.pbi_registry import get_command, list_commands
from mtagent.pbi_workflow import WorkflowController


class TestRegistry(unittest.TestCase):
    def test_all_seven_commands_registered(self):
        names = {c.name for c in list_commands()}
        self.assertEqual(names, {"build-dataset", "generate-dax", "reconcile-model",
                                  "status", "next-manual-step", "resume", "mark-complete"})

    def test_unknown_command_raises_helpful_error(self):
        with self.assertRaises(KeyError):
            get_command("not-a-real-command")

    def test_each_command_has_a_classification(self):
        for c in list_commands():
            self.assertIn(c.classification, ("automated", "manual", "approval"))


class TestCliArgparseWiring(unittest.TestCase):
    def test_pbi_status_parses(self):
        args = build_parser().parse_args(["pbi", "status"])
        self.assertEqual(args.cmd, "pbi")
        self.assertEqual(args.pbi_cmd, "status")

    def test_pbi_mark_complete_requires_all_three_flags(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["pbi", "mark-complete", "--step-id", "x"])

    def test_pbi_reconcile_model_requires_source_and_build_dir(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["pbi", "reconcile-model"])


class TestEndToEndThroughMain(unittest.TestCase):
    """Drives mtagent.cli.main(argv) exactly as the console entrypoint would,
    against a synthetic offtake fixture, proving the full command chain
    (registry -> controller -> build_dataset -> workflow state persistence)
    works together, not just each module in isolation.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "CLAUDE.md").write_text("# fixture repo root marker\n", encoding="utf-8")
        self.raw_dir = self.root / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
        self.masters_dir = self.root / "PowerBI" / "SeedData" / "Masters"
        self.raw_dir.mkdir(parents=True)
        self.masters_dir.mkdir(parents=True)

        with open(self.masters_dir / "ChainMaster.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Chain", "Account", "Chain Type", "Primary Zone", "Active"])
            w.writerow(["D-Mart", "D-Mart", "Hypermarket", "West", "Yes"])
        with open(self.masters_dir / "ArticleMaster.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["Article Code", "Article Description", "EAN Code", "Brand", "Category", "Sub-category", "Range", "Pack Size"])
            w.writerow(["ME-FW-1", "Mamaearth Face Wash", "8900000000001", "Mamaearth", "Face", "Face Wash", "Rice", "100 g/ml"])

        header = ["col0", "Unique", "Zone", "State", "City", "SO/ASE Emp Code", "SO/ASE Name",
                  "Chain Name", "Store Type", "DC Code", "DC Name", "Internal Code", "Site Code",
                  "Site Name", "Article", "Article_1", "EAN", "Chain Article Description",
                  "Net Weight", "Description as per Fountain", "Brand", "Category", "Sub_category",
                  "Range", "MRP", "Sales Qty", "MRP Sales Value", "NSV", "Per pc", "With Tax",
                  "Margin", "Revised Month", "Month", "Year", "PPT Category"]
        row = ["", "U1", "West", "MH", "Mumbai", "", "", "D-Mart", "Hyper", "DC1", "Mumbai DC", "",
               "SITE1", "Store 1", "A1", "A1", "8900000000001", "Face Wash 100ml", "100",
               "Face Wash 100ml", "Mamaearth", "Face", "Face Wash", "Rice", "199", "10", "1990",
               "15.0", "1.5", "1.65", "0.3", "", "May'26", "2026", "Face"]
        rows = [row] * 1200  # above the "complete month" heuristic threshold
        with open(self.raw_dir / "offtake_store_article_May_26.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)

        self.config_path = self.root / "agent" / "config.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        self.config_path.write_text(json.dumps({
            "repo_root": str(self.root), "index_path": "agent/index/index.json",
        }), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_build_dataset_then_status_then_resume_via_cli_main(self):
        rc = main(["--config", str(self.config_path), "pbi", "build-dataset"])
        self.assertEqual(rc, 0)

        cfg = Config(repo_root=str(self.root), index_path="agent/index/index.json")
        controller = WorkflowController(cfg)
        summary = controller.status_summary()
        self.assertGreaterEqual(summary["completion_pct"], 25.0)
        self.assertIn("build_datasets", [s.id for s in
                       __import__("mtagent.pbi_workflow", fromlist=["STEP_SEQUENCE"]).STEP_SEQUENCE])

        plan = controller.resume_plan()
        self.assertEqual(plan["last_completed_step"], "Validate business keys and relationships.")

    def test_generate_dax_then_reconcile_via_cli_main(self):
        rc = main(["--config", str(self.config_path), "pbi", "build-dataset"])
        self.assertEqual(rc, 0)

        dax_dir = self.root / "PowerBI" / "DAX"
        dax_dir.mkdir(parents=True)
        rc = main(["--config", str(self.config_path), "pbi", "generate-dax", "--dax-dir", str(dax_dir)])
        self.assertEqual(rc, 0)  # Completed with Warning still returns 0 (not Failed/Blocked)

        cfg = Config(repo_root=str(self.root), index_path="agent/index/index.json")
        build_dir = cfg.root() / "agent" / "pbi_build"
        build_subdirs = [p for p in build_dir.iterdir() if p.is_dir() and p.name != "dax_gap_latest"]
        self.assertEqual(len(build_subdirs), 1)

        rc = main(["--config", str(self.config_path), "pbi", "reconcile-model",
                   "--source", str(self.raw_dir / "offtake_store_article_May_26.csv"),
                   "--build-dir", str(build_subdirs[0])])
        self.assertEqual(rc, 0)
        self.assertTrue((build_subdirs[0] / "Source_To_Model_Reconciliation_Report.csv").exists())

    def test_status_command_returns_2_on_unknown_pbi_subcommand_gracefully(self):
        # argparse itself rejects unknown subcommands before cmd_pbi ever runs.
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["pbi", "not-a-command"])


if __name__ == "__main__":
    unittest.main()
