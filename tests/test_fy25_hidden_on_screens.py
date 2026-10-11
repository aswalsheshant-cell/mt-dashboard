"""FY25 is hidden on screens (owner request 2026-10-11). The FY25 distributor-secondary data stays in
data.js (offtake.secondary_*_fy25); only what the dashboard draws changes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")


def test_fy25_secondary_section_is_not_rendered():
    assert "${fy25SecondarySection()}" not in HTML


def test_unified_trend_has_no_fy25_series_or_title():
    assert "Secondary (FY25 only)" not in HTML
    assert "Primary / Offtake / FY25 Secondary" not in HTML
    assert "Apr'24" not in HTML.split("function unifiedSalesTrendSection")[1].split("function renderPogGapCharts")[0]


def test_footer_does_not_list_fy25():
    assert "const _fyList=" in HTML and "f!=='FY25'" in HTML


def test_fy25_data_is_still_in_data_js():
    s = (ROOT / "dashboard" / "data.js").read_text(encoding="utf-8")
    d = json.loads(s[s.index("{"): s.rindex("}") + 1])
    assert d["offtake"]["secondary_total_fy25"] > 0       # nothing deleted, easy to bring back
