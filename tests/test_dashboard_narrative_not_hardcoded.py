"""Dashboard narrative figures must come from data, not typed-in literals.

Each pattern below was a real defect on the leadership screen:
  * "FY25–27 (140 zone-months)" header -- fixed count written by the deprecated
    sync_data_js.py; never refreshed (found 2026-09-30).
  * "FY25 to FY27 trajectory" over an FY26-only line (found 2026-09-30).
  * "~83% of MT primary" / "12,000+ active stores" (fixed in #264).
Browser-level checks of the same labels: TC11 in tests/e2e_v1.1.0_consolidation.spec.js.

An approved, immutable baseline may be written as a literal only if it is added
to ALLOWED with its provenance.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "dashboard/index.html").read_text(encoding="utf-8")

FORBIDDEN = {
    "fixed zone-month count": r"\d+\s*zone-months",
    "fixed FY range in a chart subtitle": r"FY\d\d to FY\d\d trajectory",
    "fixed store count": r"\d{1,3},\d{3}\+\s*(active )?stores",
    "fixed brand share": r"~\d+% of MT primary",
}
ALLOWED = set()   # e.g. {"<exact literal>  # approved baseline, source <file>, <date>"}


def test_index_html_has_no_hardcoded_narrative_figures():
    for what, rx in FORBIDDEN.items():
        hits = [m.group(0) for m in re.finditer(rx, HTML) if m.group(0) not in ALLOWED]
        assert not hits, f"{what} typed into dashboard/index.html: {hits}"


def test_header_period_is_derived_not_meta_period():
    assert "textContent=dataPeriodLabel()" in HTML
    assert "D.meta.period" not in HTML, "header/lead text must use dataPeriodLabel(), not the stored meta.period"


def test_generators_do_not_write_a_fixed_zone_month_count():
    for f in ("scripts/sync_data_js.py", "scripts/build_dashboard_data.py"):
        src = (ROOT / f).read_text(encoding="utf-8")
        assert not re.search(r"\d+\s*zone-months", src), f"{f} writes a fixed zone-month count"
    assert 'data["meta"]["period"] = data["meta"]["fy_range"]' in (
        ROOT / "scripts/build_dashboard_data.py").read_text(encoding="utf-8")


def test_primary_trend_subtitle_is_built_from_plotted_series():
    assert "card('Primary Sales Trend',_trendSub" in HTML
    assert "_trend.map(t=>`${t.tag} (${t.first} to ${t.last})`)" in HTML
