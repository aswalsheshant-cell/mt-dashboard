"""restore_branch_files.py copies a file out of Git without switching branches, and never overwrites."""
import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import restore_branch_files as rb  # noqa: E402


def _tracked_seed_file():
    out = rb.git("ls-tree", "-r", "--name-only", "HEAD", "--", "PowerBI/SeedData/Masters").stdout.decode().split("\n")
    out = [p for p in out if p.endswith(".csv")]
    return out[0] if out else None


def test_restore_writes_only_to_dest_and_never_overwrites(tmp_path):
    rel = _tracked_seed_file()
    if rel is None or rb.ref_for("HEAD") is None:
        pytest.skip("no tracked seed file to restore")
    first = rb.restore("HEAD", [rel], tmp_path)
    assert first[0][1].startswith("restored")
    assert (tmp_path / rel).exists()
    second = rb.restore("HEAD", [rel], tmp_path)
    assert second[0][1].startswith("SKIPPED")
    rows = list(csv.reader(open(tmp_path / "restored_files.csv", encoding="utf-8")))
    assert rows[0] == ["path", "result", "sha256", "branch"] and len(rows) == 3


def test_unknown_branch_stops_with_a_message(tmp_path):
    with pytest.raises(SystemExit):
        rb.restore("no/such/branch-xyz", ["PowerBI/*"], tmp_path)
