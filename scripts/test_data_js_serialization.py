"""Regression tests for strict JSON serialization of dashboard/data.js."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qc_dashboard  # noqa: E402


REPO = Path(__file__).resolve().parent.parent
DATA_JS = REPO / "dashboard" / "data.js"


def _reject_non_finite(value: str):
    raise ValueError(f"non-finite JSON number: {value}")


def test_committed_data_js_is_strict_json():
    text = DATA_JS.read_text(encoding="utf-8")
    payload = text.split("=", 1)[1].rstrip().rstrip(";")

    json.loads(payload, parse_constant=_reject_non_finite)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_qc_loader_rejects_non_finite_json_constants(tmp_path, constant):
    data_js = tmp_path / "data.js"
    data_js.write_text(f'window.DASH = {{"value": {constant}}};\n', encoding="utf-8")

    with pytest.raises(ValueError, match=f"non-finite JSON number: {constant}"):
        qc_dashboard.load_dash(data_js)
