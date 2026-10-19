"""Power BI status measures read the same Green / Amber / Red bands as the HTML dashboard (config/analytics_config.json).
DAX is not executed here; the test checks the seed, the query, the model and the measure text."""
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_rag_threshold_seed as seed  # noqa: E402

CORE = (ROOT / "PowerBI/DAX/01_CoreMeasures.dax").read_text(encoding="utf-8")
RAG = json.loads((ROOT / "config/analytics_config.json").read_text(encoding="utf-8"))["rag"]


def _block(name):
    lines = CORE.splitlines()
    for i, l in enumerate(lines):
        if l.strip() == name + " =":
            out = []
            for l2 in lines[i + 1:]:
                if not l2.strip():
                    break
                if not l2.lstrip().startswith("//"):
                    out.append(l2)
            return "\n".join(out)
    raise AssertionError(name)


def test_seed_csv_matches_config():
    assert seed.SEED.read_text(encoding="utf-8") == seed.render(), "run scripts/build_rag_threshold_seed.py"
    assert subprocess.run([sys.executable, str(ROOT / "scripts/build_rag_threshold_seed.py"), "--check"]).returncode == 0


def test_every_config_band_is_in_the_csv():
    with open(seed.SEED, newline="", encoding="utf-8") as fh:
        rows = {r["Metric"]: r for r in csv.DictReader(fh)}
    for metric, b in RAG.items():
        if metric.startswith("_"):
            continue
        assert float(rows[metric]["Green"]) == b["green"] and float(rows[metric]["Amber"]) == b["amber"], metric
        assert (rows[metric]["Lower_Is_Better"] == "TRUE") == bool(b.get("lower_is_better")), metric


def test_query_and_model_carry_the_table():
    pq = (ROOT / "PowerBI/PowerQuery/64_Dim_RAG_Threshold.pq").read_text(encoding="utf-8")
    assert "RAG_Thresholds.csv" in pq and "Columns=6" in pq
    model = json.loads((ROOT / "PowerBI/model.bim").read_text(encoding="utf-8"))["model"]
    t = next(x for x in model["tables"] if x["name"] == "Dim RAG Threshold")
    assert [c["name"] for c in t["columns"]] == seed.COLUMNS


def test_status_measures_have_no_private_numbers():
    ach = _block("Achievement Status")
    assert "[RAG Achievement Green]" in ach and "[RAG Achievement Amber]" in ach
    assert not re.search(r"\b1\.00\b|\b0\.90\b", ach)
    col = _block("Growth Colour")
    assert "[RAG Growth Green]" in col and "[RAG Growth Amber]" in col
    assert not re.search(r"\]\s*[<>]=?\s*0\s*,", col)               # the old "> 0" / "< 0" tests are gone
    rr = _block("Run Rate Status")
    assert "[RAG Run Rate Green]" in rr and not re.search(r"<=\s*1\.\d+", rr)


def test_missing_threshold_never_falls_back_to_a_number():
    assert '"No threshold"' in _block("Achievement Status")
    assert '"No threshold"' in _block("Run Rate Status")
    assert '"#7F8C8D"' in _block("Growth Colour")
