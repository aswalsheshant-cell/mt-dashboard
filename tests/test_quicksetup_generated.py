"""PowerBI/QuickSetup's consolidated files are generated from the canonical
PQ/DAX sources and must stay in step (old PR #135, rebuilt as a generator).

Found 2026-09-26 on main a39d55c: the hand-kept copies had drifted -- 7 source
files missing (PQ 42-46, DAX 14-15), DAX 01/02/06/07 older than their sources
(QuickSetup still had the removed `COALESCE(_specific, 0.50)` default), PQ 16/41
older (41 still read the gitignored .xlsx instead of the governed CSV), and the
DAX 13 section carried an appended stale copy of 06. 73 source measures were
missing and none existed only in QuickSetup, so regenerating loses nothing.
"""
import re
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_quicksetup as bq  # noqa: E402


def test_consolidated_files_match_their_sources():
    assert bq.main(["--check"]) == 0, "run: python scripts/build_quicksetup.py"


def _sections(path):
    t = path.read_text(encoding="utf-8")
    parts = re.split(r"\n#{20,}\n# STEP \d+/\d+\s+--\s+SOURCE FILE: (\S+)\n(?:#.*\n)*#{20,}\n", t)
    return dict(zip(parts[1::2], parts[2::2])), t


def test_every_source_is_a_step_or_an_explained_exclusion():
    import json
    cfg = json.loads(bq.CONFIG.read_text(encoding="utf-8"))
    for kind in ("pq", "dax"):
        c = cfg[kind]
        sec, text = _sections(ROOT / c["out"])
        for src in sorted((ROOT / c["source_dir"]).glob(c["glob"])):
            if src.name in c["excluded"]:
                assert src.name not in sec and len(c["excluded"][src.name]) > 40, src.name
                assert f"- {src.name}:" in text, f"{src.name} not listed under NOT INCLUDED"
            else:
                assert sec[src.name].strip() == src.read_text(encoding="utf-8").strip(), src.name


def test_readme_counts_match_the_generated_steps():
    readme = (ROOT / "PowerBI/QuickSetup/README_QuickSetup.md").read_text(encoding="utf-8")
    n_pq = len(_sections(ROOT / "PowerBI/QuickSetup/AllPowerQuery_Consolidated.txt")[0])
    n_dax = len(_sections(ROOT / "PowerBI/QuickSetup/AllDAX_Consolidated.txt")[0])
    assert f"all {n_pq} Power Query steps" in readme and f"STEP 02 through STEP {n_pq} in that file" in readme
    assert f"STEP 02 through STEP {n_dax} in" in readme


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    for d in ("PowerBI/PowerQuery", "PowerBI/DAX", "PowerBI/QuickSetup"):
        shutil.copytree(ROOT / d, tmp_path / d)
    monkeypatch.setattr(bq, "ROOT", tmp_path)
    monkeypatch.setattr(bq, "CONFIG", tmp_path / "PowerBI/QuickSetup/quicksetup_steps.json")
    return tmp_path


def test_check_catches_an_edited_source(sandbox):
    f = sandbox / "PowerBI/DAX/13_CM2_Measures.dax"
    f.write_text(f.read_text(encoding="utf-8") + "\nNew Measure = 1\n", encoding="utf-8")
    assert bq.main(["--check"]) == 1
    assert bq.main([]) == 0 and bq.main(["--check"]) == 0     # regenerating fixes it


def test_new_source_file_needs_an_instruction_or_exclusion(sandbox):
    (sandbox / "PowerBI/PowerQuery/99_New.pq").write_text("let x = 1 in x\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="99_New.pq"):
        bq.main(["--check"])
