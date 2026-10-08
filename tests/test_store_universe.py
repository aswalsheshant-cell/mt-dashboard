"""One store universe for the Executive Cockpit and Inventory & Supply Health: overrides + browser check."""
import csv
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

def _node_with_playwright():
    """True when node and its 'playwright' package are both available (the Python-only CI job has node but not the npm packages; the Browser Regression job covers the UI there)."""
    import shutil
    import subprocess
    if shutil.which("node") is None:
        return False
    return subprocess.run(["node", "-e", "require.resolve('playwright')"], cwd=ROOT, capture_output=True).returncode == 0

sys.path.insert(0, str(ROOT / "scripts"))
import build_store_universe as bsu  # noqa: E402

CSV = ROOT / "PowerBI" / "SeedData" / "Masters" / "Store_Universe_Overrides.csv"


def test_overrides_are_reliance_more_retail_tentative_and_fsn_na():
    o = bsu.build()["overrides"]
    assert o["Reliance Retail"]["count"] == 1000 and o["Reliance Retail"]["status"] == "TENTATIVE"
    assert o["More Retail"]["count"] == 400 and o["More Retail"]["status"] == "TENTATIVE"
    assert o["Nykaa (FSN)"]["count"] is None and o["Nykaa (FSN)"]["status"] == "NA"


def test_generated_js_is_current():
    text = (ROOT / "dashboard" / "store_universe.js").read_text(encoding="utf-8")
    assert text.startswith("window.STORE_UNIVERSE=")
    assert json.loads(text[len("window.STORE_UNIVERSE="):].rstrip().rstrip(";")) == bsu.build()


def test_bad_status_and_missing_tentative_count_are_refused(tmp_path):
    bad = tmp_path / "o.csv"
    bad.write_text("Chain,Offtake Chain,Store Count,Status,Note,Source,As Of\nX,X,5,MAYBE,n,s,d\n", encoding="utf-8")
    with pytest.raises(ValueError):
        bsu.build(bad)
    bad.write_text("Chain,Offtake Chain,Store Count,Status,Note,Source,As Of\nX,X,,TENTATIVE,n,s,d\n", encoding="utf-8")
    with pytest.raises(ValueError):
        bsu.build(bad)


def test_both_tabs_use_the_shared_function():
    html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
    assert html.count("storeUniverse()") >= 3 and '<script src="store_universe.js"></script>' in html


def test_power_bi_measures_use_the_same_overrides():
    dax = (ROOT / "PowerBI" / "DAX" / "16_PriceVolume_Measures.dax").read_text(encoding="utf-8")
    for m in ("Universe POS Stores", "Universe Tentative Stores", "Universe Stores"):
        assert re.search(rf"^{re.escape(m)}\s*=", dax, re.M), m
    assert "Store Universe Overrides" in (ROOT / "PowerBI" / "PowerQuery" / "52_Store_Universe_Overrides.pq").read_text(encoding="utf-8")


@pytest.mark.skipif(not _node_with_playwright(), reason="node or its playwright package not installed")
def test_both_tabs_show_the_same_universe_in_a_browser():
    import subprocess
    r = subprocess.run(["node", str(ROOT / "tests" / "store_universe_browser.js")], capture_output=True, text=True, cwd=ROOT, timeout=240)
    assert r.returncode == 0, r.stdout + r.stderr
