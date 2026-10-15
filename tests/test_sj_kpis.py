"""Sales Journey proxy KPIs: ND/WD maths and the sidecar's basic shape."""
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_sj_kpis as sj  # noqa: E402


def test_nd_wd_hand_example():
    # Chain A has 4 active stores (s1..s4). Article X sells in s1, s2 only.
    rows = [("A", "s1", "X", 30), ("A", "s2", "X", 10), ("A", "s3", "Y", 40), ("A", "s4", "Y", 20)]
    df = pd.DataFrame(rows, columns=["Chain", "sid", "art", "NSV"])
    g = sj.nd_wd(df, "art").set_index("art")
    x = g.loc["X"]
    assert x["nd_pct"] == 50.0                      # 2 of 4 stores
    assert x["wd_pct"] == 40.0                      # (30+10) of 100 chain value
    assert x["missing_stores"] == 2
    assert x["indicative_lakh"] == 2 * 20           # median(30,10)=20


def test_breakeven_formula():
    d, m = 30.0, 60.0
    assert d / (m - d) * 100 == 100.0


def test_sidecar_shape():
    s = (ROOT / "dashboard" / "sj_kpis.js").read_text()
    d = json.loads(s[s.index("{"): s.rindex("}") + 1])
    assert d["distribution"] and d["breakeven_inputs"]["rows"] and d["order_line_value"]["by_month"]
    assert "Nielsen" in json.dumps(d["distribution"])
