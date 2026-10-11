"""One data home: no second copy of a dataset under PowerBI/, every landed file in the manifest, every dashboard JS file has a generator."""
import csv
import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _tracked():
    out = subprocess.run(["git", "ls-files", "-z", "PowerBI"], cwd=ROOT, capture_output=True, check=True).stdout.decode()
    return [p for p in out.split("\0") if p]


def test_no_two_tracked_files_share_a_name_with_different_content_in_seed_or_reference():
    seen = {}
    for p in _tracked():
        if not (p.startswith("PowerBI/SeedData/") or p.startswith("PowerBI/Reference/")) or not p.endswith((".csv", ".json", ".xlsx")):
            continue
        h = hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
        name = Path(p).name
        if name in seen and seen[name][1] != h:
            raise AssertionError(f"{name} exists twice with different content: {seen[name][0]} and {p}")
        seen[name] = (p, h)


def test_landed_files_are_all_in_the_manifest():
    manifest = {r["path"] for r in csv.DictReader(open(ROOT / "PowerBI" / "Reference" / "PR_INPUTS_MANIFEST.csv", encoding="utf-8"))}
    for p in _tracked():
        if p.startswith("PowerBI/Reference/Business_Inputs/"):
            assert p in manifest, p


def test_every_generated_dashboard_file_is_named_in_data_home():
    doc = (ROOT / "docs" / "DATA_HOME.md").read_text(encoding="utf-8")
    for f in ("data.js", "tdp.js", "tdp_inhouse.js", "tdp_focus.js", "store_cuts.js", "store_universe.js", "nielsen.js"):
        assert f in doc, f
