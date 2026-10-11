"""Guards on the data source map (scripts/audit_data_source_map.py).

They make the layout of the data folders a tested contract: a query, the HTML dashboard or the
registry cannot name a file that is not there, a watch folder cannot start mixing in a new column
layout unnoticed, and estimated data cannot feed a KPI.
"""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
_spec = importlib.util.spec_from_file_location("audit_data_source_map", ROOT / "scripts" / "audit_data_source_map.py")
audit = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(audit)

# Files that hold estimated or derived numbers. No query, dashboard load or registry entry may read them.
SYNTHETIC_FILES = ["PowerBI/RawDataFolders/Primary_Derived_FY25/"]


def _doc():
    return audit.build()[0]


def test_every_referenced_path_exists():
    doc = _doc()
    assert not doc["missing_references"], [(r["used_by"], r["ref"]) for r in doc["missing_references"]]


def test_every_column_layout_in_the_data_folders_is_pinned():
    doc = _doc()
    assert not doc["unpinned_header_layouts"], (
        "New column layout in a data folder: %s. Review it, then run "
        "python scripts/audit_data_source_map.py --update-pins" % doc["unpinned_header_layouts"][:3])


def test_committed_map_matches_the_repo():
    live = _doc()
    committed = json.loads((ROOT / "PowerBI" / "data_source_map.json").read_text(encoding="utf-8"))
    for key in ("counts", "missing_references", "unpinned_header_layouts", "orphan_files"):
        assert live[key] == committed[key], "%s is out of date: run python scripts/audit_data_source_map.py" % key


def test_estimated_data_is_not_read_by_any_query_or_dashboard():
    doc = _doc()
    for r in doc["references"]:
        for f in r.get("files", []) + [r["ref"]]:
            for bad in SYNTHETIC_FILES:
                assert bad.rstrip("/") not in f.replace("\\", "/"), "%s reads estimated data %s" % (r["used_by"], bad)


def test_only_expected_watch_folders_are_empty():
    doc = _doc()
    empty = {r["ref"] for r in doc["references"] if r["used_by"].startswith("Power Query") and r["kind"] == "folder" and not r["files"]}
    assert empty <= audit.EXPECTED_EMPTY | set(), empty


def test_no_query_uses_a_hard_coded_path():
    doc = _doc()
    assert not [r for r in doc["references"] if r.get("hard_coded_path")]


def test_new_raw_drops_are_ignored_but_templates_and_seeds_are_not():
    import subprocess

    def ignored(p):
        return subprocess.run(["git", "check-ignore", "-q", p], cwd=ROOT).returncode == 0

    assert ignored("PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Sep_26.csv")
    assert ignored("PowerBI/RawDataFolders/TDP_Monthly/TDP_Sep_26.csv")
    assert not ignored("PowerBI/RawDataFolders/TDP_Monthly/_TEMPLATE_TDP_Monthly.csv")
    assert not ignored("PowerBI/SeedData/Masters/ChainMaster.csv")
    assert not ignored("PowerBI/SeedData/Nielsen/Nielsen_Monthly/nielsen_urban_mt_aug26.csv")
