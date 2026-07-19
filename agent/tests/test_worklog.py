"""worklog schema v2: additive fields, backward compatibility with v1
entries, and hash_file/hash_files correctness (see
agent/AGENT_OPERATING_PRINCIPLES.md "Worklog schema" and principles
#7/#10 -- feedback loop evidence and repeatability evidence)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent.worklog import hash_file, hash_files, log_run, read_log


class TestWorklogBackwardCompat(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Config(repo_root=self.tmp.name, index_path="agent/index/index.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_v1_style_call_writes_a_plain_v1_shaped_line(self):
        log_run(self.cfg, "status", [], 0, ["ok"])
        entries = read_log(self.cfg, tail=10)
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e["command"], "status")
        self.assertNotIn("schema_version", e)
        self.assertNotIn("desired_output", e)

    def test_v2_call_carries_full_feedback_loop_evidence(self):
        log_run(
            self.cfg, "audit-june-data", [], 0, [],
            run_id="2026-07-19-001",
            desired_output="Validated June primary-secondary matrix",
            success_criteria=["All rows accounted for", "NSV unchanged", "Qty unchanged",
                               "No store-level chain explosion"],
            input_files=["Primary_June26.xlsx"],
            input_hashes={"Primary_June26.xlsx": "abc123"},
            stage_results={"ingest": "PASS", "resolve": "PASS", "reconcile": "PASS"},
            reconciliation={"nsv_delta": 0.000002, "qty_delta": 0.0},
            exceptions=["Sancus routed to RMT Sancus"],
            decision_required=["Reliance Azorte pipeline-wide scope"],
            output_files=["matrix.csv"],
            output_hashes={"matrix.csv": "def456"},
            approved_by=None,
        )
        entries = read_log(self.cfg, tail=10)
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e["schema_version"], 2)
        self.assertEqual(e["desired_output"], "Validated June primary-secondary matrix")
        self.assertEqual(e["stage_results"]["reconcile"], "PASS")
        self.assertIsNone(e["approved_by"])  # explicit None is preserved, not dropped

    def test_mixed_v1_and_v2_lines_both_read_correctly(self):
        log_run(self.cfg, "build-dataset", [], 0)
        log_run(self.cfg, "audit-june-data", [], 0, run_id="run-2", desired_output="x")
        entries = read_log(self.cfg, tail=10)
        self.assertEqual(len(entries), 2)
        self.assertNotIn("schema_version", entries[0])
        self.assertEqual(entries[1]["schema_version"], 2)

    def test_logging_never_raises_on_unwritable_path(self):
        bad_cfg = Config(repo_root="/nonexistent/\x00bad", index_path="agent/index/index.json")
        log_run(bad_cfg, "x", [], 0)  # must not raise


class TestHashHelpers(unittest.TestCase):
    def test_hash_file_matches_known_sha256(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sample.txt"
            p.write_bytes(b"hello world")
            expected = hashlib.sha256(b"hello world").hexdigest()
            self.assertEqual(hash_file(p), expected)

    def test_hash_file_changes_when_content_changes(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "sample.txt"
            p.write_bytes(b"version 1")
            h1 = hash_file(p)
            p.write_bytes(b"version 2")
            h2 = hash_file(p)
            self.assertNotEqual(h1, h2)

    def test_hash_files_maps_each_path_to_its_hash(self):
        with tempfile.TemporaryDirectory() as td:
            p1 = Path(td) / "a.txt"
            p2 = Path(td) / "b.txt"
            p1.write_bytes(b"AAA")
            p2.write_bytes(b"BBB")
            hashes = hash_files([p1, p2])
            self.assertEqual(hashes[str(p1)], hashlib.sha256(b"AAA").hexdigest())
            self.assertEqual(hashes[str(p2)], hashlib.sha256(b"BBB").hexdigest())


if __name__ == "__main__":
    unittest.main()
