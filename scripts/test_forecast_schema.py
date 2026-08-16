"""
CI-runnable schema tests for the forecast.detail block in dashboard/data.js.

These tests run on every push/PR via the dataeng CI workflow.  They validate
the *output* produced by load_forecast_detail.py so that a silently malformed
data.js is caught before it reaches production.

Run locally:
  pytest scripts/test_forecast_schema.py -v
"""
from __future__ import annotations
import json, math, re
from pathlib import Path

import pytest

DATA_JS = Path(__file__).resolve().parent.parent / "dashboard" / "data.js"
_MON_KEY_RE = re.compile(r"^[a-z]{3}_\d{2}$")   # e.g. sep_26, oct_26
_MON_LABEL_RE = re.compile(r"^[A-Z][a-z]{2}-\d{2}$")  # e.g. Sep-26


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def data():
    assert DATA_JS.exists(), f"data.js not found at {DATA_JS}"
    content = DATA_JS.read_text(encoding="utf-8")
    body = content[len("window.DASH = "):]
    body = body.rstrip()
    if body.endswith(";"):
        body = body[:-1]
    return json.loads(body)


@pytest.fixture(scope="module")
def forecast(data):
    assert "forecast" in data, "top-level 'forecast' key missing from data.js"
    return data["forecast"]


@pytest.fixture(scope="module")
def detail(forecast):
    assert "detail" in forecast, (
        "forecast.detail missing — run: "
        "python scripts/load_forecast_detail.py --xlsx <file> --out dashboard/data.js"
    )
    return forecast["detail"]


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_finite(v) -> bool:
    if not isinstance(v, (int, float)):
        return False
    return not math.isnan(v) and not math.isinf(v)


def _month_key(label: str) -> str:
    """'Sep-26' → 'sep_26'"""
    parts = label.split("-")
    return f"{parts[0].lower()}_{parts[1]}"


# ── top-level structure ───────────────────────────────────────────────────────

class TestDetailTopLevel:

    def test_detail_is_dict(self, detail):
        assert isinstance(detail, dict), "forecast.detail must be a dict"

    def test_required_keys_present(self, detail):
        required = {
            "months", "monthly_forecast", "monthly_target",
            "q2_q3_total", "by_brand", "by_chain", "status", "source",
        }
        missing = required - detail.keys()
        assert not missing, f"forecast.detail missing keys: {missing}"

    def test_source_is_string(self, detail):
        assert isinstance(detail["source"], str) and detail["source"], (
            "forecast.detail.source must be a non-empty string"
        )

    def test_source_date_present(self, detail):
        assert detail.get("source_date"), (
            "forecast.detail.source_date must be present and non-empty"
        )


# ── months array ──────────────────────────────────────────────────────────────

class TestDetailMonths:

    def test_months_is_nonempty_list(self, detail):
        mos = detail.get("months", [])
        assert isinstance(mos, list) and len(mos) > 0, (
            "forecast.detail.months must be a non-empty list"
        )

    def test_months_format(self, detail):
        bad = [m for m in detail.get("months", []) if not _MON_LABEL_RE.match(str(m))]
        assert not bad, (
            f"forecast.detail.months has invalid labels (expected Mon-YY): {bad}"
        )

    def test_months_no_duplicates(self, detail):
        mos = detail.get("months", [])
        assert len(mos) == len(set(mos)), (
            f"forecast.detail.months has duplicates: "
            f"{[m for m in set(mos) if mos.count(m) > 1]}"
        )


# ── monthly arrays ────────────────────────────────────────────────────────────

class TestDetailMonthlyArrays:

    def test_monthly_forecast_length_matches_months(self, detail):
        assert len(detail.get("monthly_forecast", [])) == len(detail.get("months", [])), (
            "monthly_forecast length must equal months length"
        )

    def test_monthly_target_length_matches_months(self, detail):
        assert len(detail.get("monthly_target", [])) == len(detail.get("months", [])), (
            "monthly_target length must equal months length"
        )

    def test_monthly_forecast_all_positive_finite(self, detail):
        bad = [(i, v) for i, v in enumerate(detail.get("monthly_forecast", []))
               if not _is_finite(v) or v <= 0]
        assert not bad, (
            f"monthly_forecast has non-positive or non-finite values at indices: {bad}"
        )

    def test_monthly_target_all_positive_finite(self, detail):
        bad = [(i, v) for i, v in enumerate(detail.get("monthly_target", []))
               if not _is_finite(v) or v <= 0]
        assert not bad, (
            f"monthly_target has non-positive or non-finite values at indices: {bad}"
        )

    def test_q2_q3_total_is_finite_positive(self, detail):
        t = detail.get("q2_q3_total")
        assert _is_finite(t) and t > 0, (
            f"q2_q3_total must be a finite positive number, got {t!r}"
        )

    def test_q2_q3_total_matches_monthly_sum(self, detail):
        mf = detail.get("monthly_forecast", [])
        expected = sum(mf)
        actual = detail.get("q2_q3_total", 0)
        assert abs(actual - expected) < 1.0, (
            f"q2_q3_total ({actual}) does not match sum(monthly_forecast) "
            f"({expected:.2f}); difference {abs(actual - expected):.2f} L"
        )


# ── by_brand ─────────────────────────────────────────────────────────────────

class TestDetailByBrand:

    def test_by_brand_is_nonempty_list(self, detail):
        bb = detail.get("by_brand", [])
        assert isinstance(bb, list) and len(bb) > 0, (
            "forecast.detail.by_brand must be a non-empty list"
        )

    def test_by_brand_entries_have_name(self, detail):
        bad = [i for i, b in enumerate(detail.get("by_brand", []))
               if not isinstance(b.get("name"), str) or not b["name"]]
        assert not bad, f"by_brand entries missing 'name' at indices: {bad}"

    def test_by_brand_entries_have_total(self, detail):
        bad = [(b.get("name"), b.get("total"))
               for b in detail.get("by_brand", [])
               if not _is_finite(b.get("total", float("nan"))) or b.get("total", -1) < 0]
        assert not bad, f"by_brand entries with invalid 'total': {bad}"

    def test_by_brand_entries_have_month_keys(self, detail):
        mos = detail.get("months", [])
        missing_keys: list[str] = []
        for b in detail.get("by_brand", []):
            for mo in mos:
                k = _month_key(mo)
                if k not in b:
                    missing_keys.append(f"{b.get('name')}.{k}")
        assert not missing_keys, (
            f"by_brand entries missing month keys: {missing_keys[:10]}"
        )

    def test_by_brand_month_values_are_finite(self, detail):
        mos = detail.get("months", [])
        bad: list[str] = []
        for b in detail.get("by_brand", []):
            for mo in mos:
                v = b.get(_month_key(mo))
                if not _is_finite(v if v is not None else 0.0):
                    bad.append(f"{b.get('name')}.{_month_key(mo)}={v!r}")
        assert not bad, f"by_brand has non-finite month values: {bad}"

    def test_by_brand_totals_sum_to_q2_q3_total(self, detail):
        brand_sum = sum(b.get("total", 0) for b in detail.get("by_brand", []))
        q2q3 = detail.get("q2_q3_total", 0)
        assert abs(brand_sum - q2q3) < 2.0, (
            f"sum(by_brand totals)={brand_sum:.2f} L does not match "
            f"q2_q3_total={q2q3:.2f} L (diff={abs(brand_sum-q2q3):.2f} L)"
        )

    def test_by_brand_no_duplicate_names(self, detail):
        names = [b.get("name") for b in detail.get("by_brand", [])]
        dupes = [n for n in set(names) if names.count(n) > 1]
        assert not dupes, f"by_brand has duplicate brand names: {dupes}"


# ── by_chain ──────────────────────────────────────────────────────────────────

class TestDetailByChain:

    def test_by_chain_is_nonempty_list(self, detail):
        bc = detail.get("by_chain", [])
        assert isinstance(bc, list) and len(bc) > 0, (
            "forecast.detail.by_chain must be a non-empty list"
        )

    def test_by_chain_entries_have_name(self, detail):
        bad = [i for i, c in enumerate(detail.get("by_chain", []))
               if not isinstance(c.get("name"), str) or not c["name"]]
        assert not bad, f"by_chain entries missing 'name' at indices: {bad}"

    def test_by_chain_entries_have_total(self, detail):
        bad = [(c.get("name"), c.get("total"))
               for c in detail.get("by_chain", [])
               if not _is_finite(c.get("total", float("nan"))) or c.get("total", -1) < 0]
        assert not bad, f"by_chain entries with invalid 'total': {bad}"

    def test_by_chain_entries_have_month_keys(self, detail):
        mos = detail.get("months", [])
        missing_keys: list[str] = []
        for c in detail.get("by_chain", []):
            for mo in mos:
                k = _month_key(mo)
                if k not in c:
                    missing_keys.append(f"{c.get('name')}.{k}")
        assert not missing_keys, (
            f"by_chain entries missing month keys: {missing_keys[:10]}"
        )

    def test_by_chain_totals_leq_q2_q3_total(self, detail):
        chain_sum = sum(c.get("total", 0) for c in detail.get("by_chain", []))
        q2q3 = detail.get("q2_q3_total", 0)
        assert chain_sum <= q2q3 + 2.0, (
            f"sum(by_chain totals)={chain_sum:.2f} L > q2_q3_total={q2q3:.2f} L"
        )

    def test_by_chain_no_duplicate_names(self, detail):
        names = [c.get("name") for c in detail.get("by_chain", [])]
        dupes = [n for n in set(names) if names.count(n) > 1]
        assert not dupes, f"by_chain has duplicate chain names: {dupes}"


# ── status block ──────────────────────────────────────────────────────────────

class TestDetailStatus:

    def test_status_is_dict(self, detail):
        assert isinstance(detail.get("status"), dict), (
            "forecast.detail.status must be a dict"
        )

    def test_status_has_reconciliation(self, detail):
        st = detail.get("status", {})
        assert "reconciliation" in st, (
            "forecast.detail.status must have a 'reconciliation' key"
        )

    def test_status_reconciliation_is_pass_or_blocked(self, detail):
        val = detail.get("status", {}).get("reconciliation")
        assert val in ("PASS", "WARN", "BLOCKED", "FAIL"), (
            f"status.reconciliation must be PASS/WARN/BLOCKED/FAIL, got {val!r}"
        )


# ── existing forecast block regression ───────────────────────────────────────

class TestForecastBlockRegression:
    """Ensure that adding forecast.detail did not alter the pre-existing keys."""

    def test_fy26_actual_unchanged(self, forecast):
        assert forecast.get("fy26_actual") == 31082.0, (
            f"forecast.fy26_actual changed; expected 31082.0, got {forecast.get('fy26_actual')}"
        )

    def test_fy27_forecast_unchanged(self, forecast):
        expected = 44132.86
        actual = forecast.get("fy27_forecast", 0)
        assert abs(actual - expected) < 1.0, (
            f"forecast.fy27_forecast changed; expected ~{expected}, got {actual}"
        )

    def test_fc_labels_length_unchanged(self, forecast):
        assert len(forecast.get("fc_labels", [])) == 12, (
            "forecast.fc_labels should have 12 months (Apr-26 to Mar-27)"
        )

    def test_hist_labels_length_unchanged(self, forecast):
        assert len(forecast.get("hist_labels", [])) == 24, (
            "forecast.hist_labels should have 24 months (FY24 + FY25 actuals)"
        )

    def test_detail_monthly_totals_match_fc_array(self, forecast):
        """Sep-26, Oct-26, Nov-26 detail totals must equal the corresponding fc[] slots."""
        fc = forecast.get("fc", [])
        det = forecast.get("detail", {})
        mos = det.get("months", [])
        fc_labels = forecast.get("fc_labels", [])
        mf = det.get("monthly_forecast", [])
        for i, mo in enumerate(mos):
            # find position in fc_labels
            if mo in fc_labels:
                fc_idx = fc_labels.index(mo)
                fc_val = fc[fc_idx]
                det_val = mf[i]
                assert abs(det_val - fc_val) < 0.5, (
                    f"{mo}: detail monthly_forecast={det_val} differs from "
                    f"fc[{fc_idx}]={fc_val}"
                )
