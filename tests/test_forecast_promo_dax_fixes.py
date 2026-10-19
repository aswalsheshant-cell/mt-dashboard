"""Forecast accuracy and promo ROI fixes (Power BI DAX). DAX is not executed here: the maths is mirrored in Python
and the DAX text is checked for the properties that matter."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FORECAST = (ROOT / "PowerBI/DAX/03_Forecast_Measures.dax").read_text(encoding="utf-8")
PROMO = (ROOT / "PowerBI/DAX/15_Promo_Measures.dax").read_text(encoding="utf-8")


def _measure(text, name):
    """The measure's text: from its header line to the next blank line (comment lines dropped)."""
    lines = text.splitlines()
    for i, l in enumerate(lines):
        if l.strip() in (name + " =", "[" + name + "] ="):
            out = []
            for l2 in lines[i + 1:]:
                if not l2.strip():
                    break
                if not l2.lstrip().startswith("//"):
                    out.append(l2)
            return "\n".join(out)
    raise AssertionError(name)


def wape_and_bias(rows):
    """rows = (forecast, actual) per scoring unit; same maths as Forecast WAPE % / Forecast Bias %."""
    act = sum(a for _, a in rows)
    return sum(abs(a - f) for f, a in rows) / act, (sum(f for f, _ in rows) - act) / act


def test_four_sku_example_total_looks_perfect_units_do_not():
    rows = [(1200, 1000), (800, 1000), (500, 400), (500, 600)]
    wape, bias = wape_and_bias(rows)
    assert round(1 - wape, 2) == 0.80          # real accuracy
    assert bias == 0                           # errors cancel in the bias, as they should
    total_level = 1 - abs(sum(a for _, a in rows) - sum(f for f, _ in rows)) / sum(a for _, a in rows)
    assert total_level == 1.0                  # what the old measure showed


def test_dax_scores_per_chain_month_before_summing():
    body = _measure(FORECAST, "Forecast Abs Error")
    assert "CROSSJOIN" in body and "'Chain Master'[Chain]" in body and "'Date Table'[MonthStart]" in body
    assert re.search(r"SUMX\s*\(\s*_grid\s*,\s*ABS", body)
    assert "[Actual NSV] > 0" in body                      # only chain-months with actuals are scored


def test_accuracy_uses_wape_and_old_total_level_kept_by_name():
    assert "[Forecast WAPE %]" in _measure(FORECAST, "Forecast Accuracy %")
    assert "Forecast Accuracy % (Total Level) =" in FORECAST
    assert "Forecast Bias % =" in FORECAST


def test_promo_baseline_is_like_for_like():
    body = _measure(PROMO, "Historical Baseline Velocity Lakh")
    assert "[Actual Promoted NSV Lakh]" in body
    assert "REMOVEFILTERS" not in body


def test_promo_net_margin_roi_has_no_hardcoded_margin():
    body = _measure(PROMO, "Promo Net Margin ROI")
    assert "0.40" not in body and "[_Assumption Gross Margin %]" in body
    assert "ISBLANK(BaseGrossMarginPct)" in body
