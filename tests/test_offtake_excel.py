"""Excel QoQ / H1 dashboard: structure and that the builder ties to the dashboard total (skips where the raw monthly CSVs are absent)."""
import json
import subprocess
import sys
from pathlib import Path

import openpyxl
import pytest

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "PowerBI" / "RawDataFolders" / "Offtake_Monthly" / "offtake_store_article_Sep_26.csv"


@pytest.mark.skipif(not RAW.exists(), reason="raw monthly offtake CSVs are gitignored and not on this machine")
def test_workbook_builds_and_ties_to_dashboard(tmp_path):
    out = tmp_path / "x.xlsx"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_offtake_excel.py"), "--out", str(out)], check=True, capture_output=True)
    wb = openpyxl.load_workbook(out)
    for s in ("Dashboard", "Insights", "Control", "By_Chain", "By_Brand", "By_SubCategory", "By_PackSize", "Chain_x_Brand", "Monthly", "Pending_Chains", "Primary_vs_Offtake", "Offtake_Data"):
        assert s in wb.sheetnames
    for nm in ("d_Month", "d_NSV", "LatestMonth", "CY_H1_S", "LY_H1_E", "N_Q2", "d_Type", "Incl_Est", "Est_Crit"):
        assert nm in wb.defined_names
    ws = wb["By_Chain"]
    assert str(ws["B6"].value).startswith("=SUMIFS")   # numbers are formulas on the data sheet, not pasted values
    s = (ROOT / "dashboard" / "data.js").read_text()
    D = json.loads(s[s.index("{"): s.rindex("}") + 1])
    total = sum(r[6] for r in wb["Offtake_Data"].iter_rows(min_row=2, values_only=True) if r[0] and r[0].year == 2026 and r[0].month >= 4 and r[9] == "Actual")
    assert abs(total - D["offtake"]["total_fy27"]) < 0.05
