"""Behavioral acceptance tests for the Main Controller (agent/mtagent/controller.py).

Proves the 5 required behaviors from agent/AGENT_OPERATING_PRINCIPLES.md,
each against real controller output, not asserted claims:

1. A natural-language instruction converts into a structured Plan.
2. A canonical target shaped like a raw store/ship-to code is refused,
   never silently promoted to a chain.
3. A failed/blocked stage halts downstream work.
4. No commit/push executes without approved=True passed explicitly.
5. Every execute() call writes a worklog entry.

Also proves NON-REGRESSION: the existing `ask` (RAG Q&A) command's
argparse wiring is untouched -- `run` is a separate command.
"""
import csv
import tempfile
import unittest
from pathlib import Path

from mtagent import controller as ctl
from mtagent.config import Config
from mtagent.worklog import read_log


def _fixture_repo() -> Path:
    """A minimal repo skeleton the controller's real pbi commands can run
    against: masters + one committed offtake month, matching the shape
    pbi_dataset.py expects (same fixture pattern as test_pbi_dataset.py)."""
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    (root / "CLAUDE.md").write_text("# fixture\n", encoding="utf-8")
    masters = root / "PowerBI" / "SeedData" / "Masters"
    masters.mkdir(parents=True)
    with open(masters / "ChainMaster.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Chain", "Account", "Chain Type", "Primary Zone", "Active"])
        w.writerow(["D-Mart", "D-Mart", "Hypermarket", "West", "Yes"])
        w.writerow(["Apollo", "Apollo", "Pharmacy", "South-1", "Yes"])
    with open(masters / "ArticleMaster.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Article Code", "Article Description", "EAN Code", "Brand", "Category", "Sub-category", "Range", "Pack Size"])
        w.writerow(["ME-FW-1", "Face Wash", "8900000000001", "Mamaearth", "Face", "Face Wash", "Rice", "100 g/ml"])

    raw_dir = root / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
    raw_dir.mkdir(parents=True)
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
    with open(raw_dir / "offtake_store_article_May_26.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows([row] * 1200)   # above the "complete month" heuristic

    cfg = Config(repo_root=str(root), index_path="agent/index/index.json")
    return tmp, cfg


class TestPlanStructure(unittest.TestCase):
    """#1 -- NL instruction converts into a structured plan."""

    def test_recognized_instruction_yields_full_plan_structure(self):
        plan = ctl.interpret("rebuild the dataset")
        self.assertTrue(plan.recognized)
        self.assertEqual(plan.action, "build_dataset")
        self.assertTrue(plan.desired_output)
        self.assertIn("pbi-workflow", plan.required_systems)
        self.assertTrue(plan.success_criteria)
        self.assertIn("entry", plan.entry_exit_conditions)
        self.assertIn("exit", plan.entry_exit_conditions)
        self.assertTrue(plan.expected_output_files)
        self.assertFalse(plan.approval_required)

    def test_unrecognized_instruction_is_never_silently_guessed(self):
        plan = ctl.interpret("do something completely unrelated xyz123")
        self.assertFalse(plan.recognized)
        self.assertIsNone(plan.action)
        self.assertTrue(plan.suggestions)  # names the known actions instead of guessing

    def test_format_plan_shows_every_required_field_before_execution(self):
        plan = ctl.interpret("commit these changes")
        text = ctl.format_plan(plan)
        for required in ("Desired output:", "Entry condition:", "Exit condition:",
                         "Approval boundary:"):
            self.assertIn(required, text)


class TestStoreNamesCannotBecomeChains(unittest.TestCase):
    """#2 -- the exact bug this project hit for real (Reliance store codes
    exploding into fake per-store 'chains') must be refused at the plan
    level, not just caught after the fact."""

    def test_store_code_shaped_canonical_is_refused_at_interpret_time(self):
        plan = ctl.interpret('apply "Some Label" to "Reliance Retail Limited_FRDI" for the primary file only')
        self.assertFalse(plan.recognized)
        self.assertIn("store", " ".join(plan.suggestions).lower())

    def test_sap_style_store_suffix_is_refused(self):
        plan = ctl.interpret('apply "X" to "V-Mart Retail Limited-148-BIRSA" for the primary file only')
        self.assertFalse(plan.recognized)

    def test_apply_alias_execution_flags_a_canonical_not_in_chain_master(self):
        tmp, cfg = _fixture_repo()
        try:
            plan = ctl.interpret('apply "Az Ent" to "Totally New Chain" for the secondary file only')
            self.assertTrue(plan.recognized)
            result = ctl.execute(cfg, plan)
            self.assertEqual(result.run_status, "PASS")  # recorded, but flagged, not rejected outright
            self.assertIn("NOT an existing ChainMaster", result.stages[0].detail)
        finally:
            tmp.cleanup()

    def test_apply_alias_to_a_real_chain_is_recorded_cleanly(self):
        tmp, cfg = _fixture_repo()
        try:
            plan = ctl.interpret('apply "Apollo Healthco" to "Apollo" for the secondary file only')
            result = ctl.execute(cfg, plan)
            self.assertEqual(result.run_status, "PASS")
            out = cfg.root() / "PowerBI" / "SeedData" / "Mapping" / "ControllerAlias_secondary.csv"
            self.assertTrue(out.exists())
            with open(out, newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(rows[0]["Canonical Chain"], "Apollo")
            self.assertEqual(rows[0]["Canonical Exists In ChainMaster"], "True")
        finally:
            tmp.cleanup()


class TestReconciliationFailureHaltsDownstream(unittest.TestCase):
    """#3 -- a BLOCKED/FAIL stage stops the run; later stages never
    execute (see AGENT_OPERATING_PRINCIPLES.md #2/#6)."""

    def test_reconcile_blocked_when_no_build_exists(self):
        tmp, cfg = _fixture_repo()
        try:
            plan = ctl.interpret("check reconciliation")
            result = ctl.execute(cfg, plan)
            self.assertEqual(result.run_status, "BLOCKED")
            self.assertEqual(len(result.stages), 1)  # halted at the first stage, nothing after ran
            self.assertIn("no completed dataset build", result.stages[0].detail)
        finally:
            tmp.cleanup()

    def test_build_then_reconcile_real_chain_passes(self):
        tmp, cfg = _fixture_repo()
        try:
            build_result = ctl.execute(cfg, ctl.interpret("rebuild the dataset"))
            self.assertEqual(build_result.run_status, "PASS")
            recon_result = ctl.execute(cfg, ctl.interpret("run reconciliation"))
            self.assertEqual(recon_result.run_status, "PASS")
        finally:
            tmp.cleanup()


class TestNoCommitOrPushWithoutApproval(unittest.TestCase):
    """#4 -- destructive actions are BLOCKED without explicit approved=True,
    and even when approved, this module never invokes git itself."""

    def test_commit_blocked_without_approval(self):
        tmp, cfg = _fixture_repo()
        try:
            plan = ctl.interpret("commit these changes")
            self.assertTrue(plan.approval_required)
            result = ctl.execute(cfg, plan, approved=False)
            self.assertEqual(result.run_status, "BLOCKED")
            self.assertIsNotNone(result.approval_required)
        finally:
            tmp.cleanup()

    def test_push_blocked_without_approval(self):
        tmp, cfg = _fixture_repo()
        try:
            result = ctl.execute(cfg, ctl.interpret("push to remote"), approved=False)
            self.assertEqual(result.run_status, "BLOCKED")
        finally:
            tmp.cleanup()

    def test_commit_even_when_approved_never_calls_git(self):
        tmp, cfg = _fixture_repo()
        try:
            result = ctl.execute(cfg, ctl.interpret("commit these changes"), approved=True)
            # still BLOCKED -- this module documents it never runs git itself,
            # the orchestrating session does, only after this approval
            self.assertEqual(result.run_status, "BLOCKED")
            self.assertIn("never auto-run", result.stages[0].detail)
            self.assertFalse((cfg.root() / ".git").exists())  # no git operation was attempted
        finally:
            tmp.cleanup()


class TestEveryRunWritesAWorklogEntry(unittest.TestCase):
    """#5 -- feedback-loop evidence: execute() always appends a schema-v2
    worklog entry, whether the run passed, failed, or was blocked."""

    def test_pass_writes_worklog_with_stage_results(self):
        tmp, cfg = _fixture_repo()
        try:
            ctl.execute(cfg, ctl.interpret("rebuild the dataset"))
            entries = read_log(cfg, tail=5)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["schema_version"], 2)
            self.assertIn("build_dataset", entries[0]["stage_results"])
            self.assertEqual(entries[0]["stage_results"]["build_dataset"], "PASS")
        finally:
            tmp.cleanup()

    def test_blocked_run_also_writes_worklog(self):
        tmp, cfg = _fixture_repo()
        try:
            ctl.execute(cfg, ctl.interpret("commit these changes"), approved=False)
            entries = read_log(cfg, tail=5)
            self.assertEqual(len(entries), 1)
            self.assertTrue(entries[0]["decision_required"])
            self.assertIsNone(entries[0]["approved_by"])
        finally:
            tmp.cleanup()

    def test_unrecognized_instruction_never_reaches_execute_or_worklog(self):
        # execute() is only ever called after interpret() -- an unrecognized
        # plan is handled by the CLI layer before execute(); confirm execute()
        # itself still degrades safely (CLARIFICATION_REQUIRED, one stage) if
        # called directly. Per AI_LEVERAGE_AND_JUDGMENT.md rule 13: a
        # materially unclear instruction is CLARIFICATION_REQUIRED, distinct
        # from BLOCKED (a recognized plan that failed a gate).
        tmp, cfg = _fixture_repo()
        try:
            result = ctl.execute(cfg, ctl.interpret("gibberish not a real instruction"))
            self.assertEqual(result.run_status, "CLARIFICATION_REQUIRED")
            self.assertEqual(len(result.stages), 1)
        finally:
            tmp.cleanup()


class TestExistingAskCommandUnaffected(unittest.TestCase):
    """Non-regression: `ask`'s argparse wiring is a separate command from
    `run` -- confirm the parser still defines `ask` as pure Q&A with no
    controller-related flags leaking onto it."""

    def test_ask_and_run_are_separate_subcommands(self):
        from mtagent.cli import build_parser
        parser = build_parser()
        ask_args = parser.parse_args(["ask", "How is FY derived?"])
        self.assertEqual(ask_args.cmd, "ask")
        self.assertEqual(ask_args.question, "How is FY derived?")
        self.assertFalse(hasattr(ask_args, "instruction"))
        self.assertFalse(hasattr(ask_args, "approve"))

        run_args = parser.parse_args(["run", "rebuild the dataset"])
        self.assertEqual(run_args.cmd, "run")
        self.assertEqual(run_args.instruction, "rebuild the dataset")
        self.assertFalse(hasattr(run_args, "question"))


if __name__ == "__main__":
    unittest.main()
