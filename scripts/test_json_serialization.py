import ast
import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

import build_dashboard_data as bd
import json_boundary
import patch_cm2_provisional
import qc_dashboard
import sync_data_js


ROOT = Path(__file__).resolve().parent.parent


def test_normalizer_converts_nested_nonfinite_values_without_mutation():
    original = {
        "finite": 12.5,
        "nested": [float("nan"), {"pos": float("inf"), "neg": float("-inf")}],
        "tuple": (1.0, float("nan")),
    }
    snapshot = copy.deepcopy(original)

    normalized = json_boundary.normalize_json_boundary(original)

    assert normalized == {
        "finite": 12.5,
        "nested": [None, {"pos": None, "neg": None}],
        "tuple": [1.0, None],
    }
    assert original["finite"] == snapshot["finite"]
    assert math.isnan(original["nested"][0])
    assert math.isinf(original["nested"][1]["pos"])
    assert math.isinf(original["nested"][1]["neg"])
    assert math.isnan(original["tuple"][1])


def test_strict_serializer_emits_null_and_preserves_finite_values():
    payload = json_boundary.serialize_window_dash(
        {"finite": 4.25, "nan": float("nan"), "inf": float("inf"), "ninf": float("-inf")},
        indent=1,
    )

    assert payload.startswith("window.DASH = ")
    assert payload.endswith(";\n")
    assert "NaN" not in payload
    assert "Infinity" not in payload
    assert json_boundary.parse_window_dash_strict(payload) == {
        "finite": 4.25,
        "nan": None,
        "inf": None,
        "ninf": None,
    }


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_strict_parser_rejects_nonstandard_constants(constant):
    with pytest.raises(ValueError, match="non-standard JSON constant"):
        json_boundary.parse_window_dash_strict(f'window.DASH = {{"bad": {constant}}};')


def test_all_six_build_paths_use_centralized_serializer():
    source = Path(bd.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    serializer_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "serialize_window_dash"
    ]
    assert len(serializer_calls) == 6
    assert '"window.DASH = " + json.dumps(obj' not in source
    assert '"window.DASH = " + json.dumps(data' not in source


def test_invalid_candidate_cannot_replace_last_known_good(tmp_path, monkeypatch):
    destination = tmp_path / "data.js"
    original = json_boundary.serialize_window_dash({"status": "known-good"})
    destination.write_text(original, encoding="utf-8")
    gate_called = False

    def gate(*args, **kwargs):
        nonlocal gate_called
        gate_called = True
        return True, object()

    monkeypatch.setattr(bd, "_run_release_gate", gate)

    with pytest.raises(ValueError, match="non-standard JSON constant"):
        bd._safe_write_data_js(
            destination,
            'window.DASH = {"bad": NaN};\n',
            skip_gate=False,
        )

    assert destination.read_text(encoding="utf-8") == original
    assert gate_called is False


def test_release_gate_failure_preserves_last_known_good(tmp_path, monkeypatch):
    destination = tmp_path / "data.js"
    original = json_boundary.serialize_window_dash({"status": "known-good"})
    destination.write_text(original, encoding="utf-8")

    class Report:
        def print_report(self):
            pass

    monkeypatch.setattr(bd, "_run_release_gate", lambda *args, **kwargs: (False, Report()))

    with pytest.raises(SystemExit):
        bd._safe_write_data_js(
            destination,
            json_boundary.serialize_window_dash({"status": "candidate"}),
        )

    assert destination.read_text(encoding="utf-8") == original


def test_valid_candidate_replaces_atomically(tmp_path):
    destination = tmp_path / "data.js"
    destination.write_text(json_boundary.serialize_window_dash({"old": True}), encoding="utf-8")
    candidate = json_boundary.serialize_window_dash({"new": True})

    bd._safe_write_data_js(destination, candidate, skip_gate=True)

    assert destination.read_text(encoding="utf-8") == candidate
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_qc_loader_rejects_nonfinite_constants(tmp_path, constant):
    candidate = tmp_path / "data.js"
    candidate.write_text(f'window.DASH = {{"bad": {constant}}};\n', encoding="utf-8")

    with pytest.raises(ValueError, match="non-standard JSON constant"):
        qc_dashboard.load_dash(candidate)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_ci_validator_rejects_nonfinite_constants(tmp_path, constant):
    candidate = tmp_path / "data.js"
    candidate.write_text(f'window.DASH = {{"offtake": {{}}, "bad": {constant}}};\n', encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ci_validate_datajs.py"), "--data", str(candidate)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "non-standard JSON constant" in result.stdout


def test_sync_writer_cannot_emit_nonfinite_constants():
    master = json.loads((ROOT / "data_master.json").read_text(encoding="utf-8"))
    master.setdefault("brand_counter", {})["bad"] = float("nan")

    output = sync_data_js.generate_data_js(master)

    assert "NaN" not in output
    assert "Infinity" not in output
    json_boundary.parse_window_dash_strict(output)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_sync_writer_rejects_nonfinite_existing_artifact(constant):
    master = json.loads((ROOT / "data_master.json").read_text(encoding="utf-8"))
    existing = f'window.DASH = {{"preserved": {{}}, "bad": {constant}}};\n'

    with pytest.raises(ValueError, match="non-standard JSON constant"):
        sync_data_js.generate_data_js(master, existing_js=existing)


def test_patch_writer_uses_strict_boundary_contract():
    source = Path(patch_cm2_provisional.__file__).read_text(encoding="utf-8")
    assert "parse_window_dash_strict" in source
    assert "serialize_window_dash" in source
    assert "json.dumps(dash" not in source

