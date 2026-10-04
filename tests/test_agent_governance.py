"""Tests for scripts/agent_governance.py (decision policy + hash-chained log)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import agent_governance as g


REPO = Path(__file__).resolve().parent.parent
EVIDENCE_FILE = "config/agent_decision_policy.yml"


def good_evidence():
    import hashlib
    return [{"type": "file", "path": EVIDENCE_FILE,
             "sha256": hashlib.sha256((REPO / EVIDENCE_FILE).read_bytes()).hexdigest()}]


def pol(**kw):
    p = g.load_policy()
    p["approvers"] = ["Finance Head", "Owner"]
    p.update(kw)
    return p


def dec(**kw):
    base = dict(id="D1", ts="2026-10-04T10:00:00Z", actor="qc-agent",
                action_class="run_validation", label="GO", rule="AUTO_LOG",
                owner="MT Analyst Lead", validation_check="ci_validate_datajs.py PASS",
                evidence=good_evidence(), paths=[])
    base.update(kw)
    return base


class EvaluateTests(unittest.TestCase):
    def test_auto_log_with_evidence_is_allowed(self):
        self.assertEqual(g.evaluate(dec())["verdict"], g.ALLOWED)

    def test_no_evidence_is_blocked(self):
        self.assertEqual(g.evaluate(dec(evidence=[]))["verdict"], g.BLOCKED)

    def test_hold_needs_no_evidence_but_needs_fields(self):
        self.assertEqual(g.evaluate(dec(label="HOLD", evidence=[], action_class="read_only"))["verdict"], g.ALLOWED)
        # AUTO_LOG actions always need evidence, whatever the label
        self.assertEqual(g.evaluate(dec(label="HOLD", evidence=[]))["verdict"], g.BLOCKED)
        self.assertEqual(g.evaluate(dec(label="HOLD", owner=""))["verdict"], g.BLOCKED)

    def test_protected_path_forces_approval(self):
        r = g.evaluate(dec(paths=["config/baselines.json"]))
        self.assertEqual(r["verdict"], g.NEEDS_APPROVAL)
        ok = g.evaluate(dec(paths=["config/baselines.json"], approver="Finance Head"), pol())
        self.assertEqual(ok["verdict"], g.ALLOWED)

    def test_seed_data_glob_is_protected(self):
        r = g.evaluate(dec(paths=["PowerBI/SeedData/Masters/x.csv"]))
        self.assertEqual(r["verdict"], g.NEEDS_APPROVAL)

    def test_unknown_action_is_blocked_for_a_registered_agent(self):
        self.assertEqual(g.evaluate(dec(action_class="surprise"))["verdict"], g.BLOCKED)

    def test_forbidden_actions_blocked_even_with_approver(self):
        for cls in ("create_release_or_tag", "override_failed_control"):
            self.assertEqual(g.evaluate(dec(action_class=cls, approver="Owner"), pol())["verdict"], g.BLOCKED)

    def test_merge_blocked_while_branch_protection_unconfirmed(self):
        rm = dict(actor="release-manager-agent", action_class="merge_pr", approver="Owner")
        self.assertEqual(g.evaluate(dec(**rm), pol())["verdict"], g.BLOCKED)
        self.assertEqual(g.evaluate(dec(**rm), pol(main_branch_protection_confirmed=True))["verdict"], g.ALLOWED)

    def test_unregistered_actor_blocked(self):
        self.assertEqual(g.evaluate(dec(actor="rogue-bot"))["verdict"], g.BLOCKED)

    def test_agent_cannot_use_action_outside_its_list(self):
        r = g.evaluate(dec(actor="insight-agent", action_class="branch_commit"))
        self.assertEqual(r["verdict"], g.BLOCKED)

    def test_agent_cannot_approve_itself(self):
        r = g.evaluate(dec(paths=["config/baselines.json"], approver="qc-agent"), pol(approvers=["qc-agent"]))
        self.assertEqual(r["verdict"], g.BLOCKED)

    def test_approver_must_be_on_list_and_list_is_empty_by_default(self):
        d = dec(paths=["config/baselines.json"], approver="Anyone")
        self.assertEqual(g.evaluate(d)["verdict"], g.NEEDS_APPROVAL)          # real policy: empty list
        self.assertEqual(g.evaluate(d, pol())["verdict"], g.NEEDS_APPROVAL)   # not on list

    def test_free_text_evidence_rejected(self):
        self.assertEqual(g.evaluate(dec(evidence=["tests passed"]))["verdict"], g.BLOCKED)

    def test_evidence_file_hash_must_match(self):
        bad = [{"type": "file", "path": EVIDENCE_FILE, "sha256": "0" * 64}]
        self.assertTrue(g.verify_evidence(dec(evidence=bad)))
        self.assertEqual(g.verify_evidence(dec()), [])

    def test_evidence_commit_must_exist(self):
        self.assertTrue(g.verify_evidence(dec(evidence=[{"type": "commit", "sha": "deadbeef" * 5}])))

    def test_bad_label_blocked(self):
        self.assertEqual(g.evaluate(dec(label="MAYBE"))["verdict"], g.BLOCKED)


class LogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "log.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_log_is_clean(self):
        self.assertEqual(g.check_log(self.log), [])

    def test_record_refuses_blocked(self):
        with self.assertRaises(PermissionError):
            g.record(dec(evidence=[]), self.log)
        with self.assertRaises(PermissionError):   # evidence points at a file that is not there
            g.record(dec(evidence=[{"type": "file", "path": "nope.txt", "sha256": "0" * 64}]), self.log)
        self.assertFalse(self.log.exists())

    def test_chain_and_clean_check(self):
        g.record(dec(id="D1"), self.log)
        g.record(dec(id="D2"), self.log)
        self.assertEqual(g.check_log(self.log), [])

    def test_edit_after_write_is_caught(self):
        g.record(dec(id="D1"), self.log)
        rec = json.loads(self.log.read_text())
        rec["owner"] = "someone else"
        self.log.write_text(json.dumps(rec) + "\n")
        self.assertTrue(any("edited" in p for p in g.check_log(self.log)))

    def test_deleted_record_breaks_chain(self):
        for i in (1, 2, 3):
            g.record(dec(id=f"D{i}"), self.log)
        lines = self.log.read_text().splitlines()
        self.log.write_text("\n".join([lines[0], lines[2]]) + "\n")
        self.assertTrue(any("chain broken" in p for p in g.check_log(self.log)))


if __name__ == "__main__":
    unittest.main()
