#!/usr/bin/env python3
"""Write PowerBI/SeedData/Masters/RAG_Thresholds.csv from config/analytics_config.json ("rag" block).

The config is the one place the Green / Amber / Red bands live (the HTML dashboard already reads it from DASH.config).
This file hands the same numbers to Power BI as the 'Dim RAG Threshold' table, so a status or colour measure never
carries its own copy. tests/test_rag_threshold_alignment.py fails if the CSV and the config drift apart.

    python scripts/build_rag_threshold_seed.py            # rewrite the CSV
    python scripts/build_rag_threshold_seed.py --check    # exit 1 if the CSV is out of date
"""
import argparse
import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "analytics_config.json"
SEED = ROOT / "PowerBI" / "SeedData" / "Masters" / "RAG_Thresholds.csv"
COLUMNS = ["Metric", "Green", "Amber", "Red", "Lower_Is_Better", "Unit"]


def _unit(metric):
    """pct = value is in percent (100 means 100%); ratio = plain ratio."""
    return "pct" if metric.endswith("_pct") else "ratio"


def render():
    rag = json.loads(CONFIG.read_text(encoding="utf-8"))["rag"]
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    for metric, b in rag.items():
        if metric.startswith("_"):
            continue
        w.writerow([metric, b["green"], b["amber"], b.get("red", ""),
                    "TRUE" if b.get("lower_is_better") else "FALSE", _unit(metric)])
    return buf.getvalue()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    text = render()
    if a.check:
        ok = SEED.exists() and SEED.read_text(encoding="utf-8") == text
        print("RAG_Thresholds.csv is up to date" if ok else "RAG_Thresholds.csv is out of date: run scripts/build_rag_threshold_seed.py")
        return 0 if ok else 1
    SEED.write_text(text, encoding="utf-8")
    print("wrote", SEED.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
