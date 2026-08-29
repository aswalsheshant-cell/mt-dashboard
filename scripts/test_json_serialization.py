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


class _SerializationReached(Exception):
    pass


@pytest.mark.parametrize(
    ("mode", "extra_args"),
    [
        ("full", []),
        ("detail-only", ["--detail-only"]),
        ("primary-only", ["--primary-only"]),
        ("forecast-only", ["--forecast-only"]),
        ("offtake-patch", ["--offtake-patch"]),
        ("distgap", ["--distgap"]),
    ],
)
def test_all_six_build_modes_reach_centralized_serializer(tmp_path, monkeypatch, mode, extra_args):
    output = tmp_path / "data.js"
    output.write_text(
        json_boundary.serialize_window_dash({"primary": {}, "offtake": {}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["build_dashboard_data.py", "--src", str(tmp_path),
                                      "--out", str(output), *extra_args])

    calls = []

    def serializer(value, *, indent=None):
        calls.append((value, indent))
        raise _SerializationReached(mode)

    monkeypatch.setattr(bd, "serialize_window_dash", serializer)

    if mode == "detail-only":
        monkeypatch.setattr(
            bd, "_build_detail_meta",
            lambda *args: ([], {}, {"representative": False}, None, None, None),
        )
    elif mode == "primary-only":
        monkeypatch.setattr(bd, "load_primary_v2", lambda *args: object())
        monkeypatch.setattr(bd, "load_chain_allocation_weights", lambda *args: None)
        monkeypatch.setattr(bd, "load_offtake", lambda *args: (_ for _ in ()).throw(OSError()))
        allocated = bd.pd.DataFrame(columns=["chain", "brand", "zone", "channel"])
        monkeypatch.setattr(bd, "apply_chain_allocation_enhanced",
                            lambda *args: (allocated, None))
        monkeypatch.setattr(bd, "primary_block",
                            lambda *args: (bd.pd.DataFrame(), {"fy_tags": []}))
        monkeypatch.setattr(bd, "pnl_block", lambda *args: {})
        monkeypatch.setattr(bd, "insights_block", lambda *args: [])
    elif mode == "forecast-only":
        monkeypatch.setattr(bd, "load_ty_target", lambda *args: [{}])
        monkeypatch.setattr(
            bd, "forecast_block_ty",
            lambda *args: {"fy26_actual": 1, "fy27_forecast": 2},
        )
    elif mode == "offtake-patch":
        monkeypatch.setattr(
            bd, "load_offtake_article_files",
            lambda *args: ({"Chain": {"Apr-26": 1}}, {}),
        )
        monkeypatch.setattr(bd, "patch_offtake_new_months", lambda *args: {"fy_tags": []})
        monkeypatch.setattr(bd, "load_reliance_bc_data", lambda *args: None)
    elif mode == "distgap":
        monkeypatch.setattr(
            bd, "dist_gap_block",
            lambda *args: {
                "row_count": 1,
                "window_label": "test",
                "total_addon_window": 1,
                "total_addon_ann": 1,
                "addon_by_group": [],
            },
        )
    else:
        monkeypatch.setattr(bd, "load_primary", lambda *args: object())
        monkeypatch.setattr(bd, "primary_block",
                            lambda *args: (bd.pd.DataFrame(), {"by_channel": []}))
        monkeypatch.setattr(bd, "load_offtake", lambda *args: ({}, {}))
        monkeypatch.setattr(bd, "offtake_block", lambda *args: {})
        monkeypatch.setattr(bd, "universe_block", lambda *args: (bd.pd.DataFrame(), {}))
        monkeypatch.setattr(bd, "promo_block", lambda *args: (bd.pd.DataFrame(), {}))
        monkeypatch.setattr(bd, "pnl_block", lambda *args: {})
        monkeypatch.setattr(bd, "forecast_block", lambda *args: {})
        monkeypatch.setattr(bd, "insights_block", lambda *args: [])
        monkeypatch.setattr(
            bd, "_build_detail_meta",
            lambda *args: ([], {}, {"representative": False}, None, None, None),
        )
        monkeypatch.setattr(bd, "dist_gap_block", lambda *args: None)

    with pytest.raises(_SerializationReached, match=mode):
        bd.main()

    assert len(calls) == 1
    assert calls[0][1] == 1


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
    assert not list(tmp_path.glob("*.tmp"))


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


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_patch_writer_rejects_nonfinite_input(tmp_path, monkeypatch, constant):
    candidate = tmp_path / "data.js"
    candidate.write_text(
        f'window.DASH = {{"cm2": {{"total_nsv": {constant}}}}};\n',
        encoding="utf-8",
    )
    original = candidate.read_bytes()
    monkeypatch.setattr(sys, "argv", ["patch_cm2_provisional.py", "--data-js", str(candidate)])

    assert patch_cm2_provisional.main() == 2
    assert candidate.read_bytes() == original
    assert not candidate.with_suffix(".js.cm2prov.bak").exists()


def test_patch_writer_produces_strict_finite_output(tmp_path, monkeypatch):
    candidate = tmp_path / "data.js"
    candidate.write_text(
        json_boundary.serialize_window_dash({
            "cm2": {
                "total_nsv": 10.5,
                "total_expense": 2.25,
                "cm2_value": 8.25,
                "cm2_pct": 78.57,
            },
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["patch_cm2_provisional.py", "--data-js", str(candidate)])
    monkeypatch.setattr(patch_cm2_provisional, "load_pl_expense_input", lambda: object())
    monkeypatch.setattr(
        patch_cm2_provisional,
        "_cm2_provisional_state",
        lambda *args: {
            "formula_status": "PROVISIONAL",
            "provisional": True,
            "provisional_label": "Pending",
            "provisional_reasons": ["Review"],
            "example_data_only": False,
        },
    )

    assert patch_cm2_provisional.main() == 0

    output = candidate.read_text(encoding="utf-8")
    parsed = json_boundary.parse_window_dash_strict(output)
    assert parsed["cm2"]["total_nsv"] == 10.5
    assert parsed["cm2"]["total_expense"] == 2.25
    assert parsed["cm2"]["cm2_value"] == 8.25
    assert parsed["cm2"]["cm2_pct"] == 78.57
    assert "NaN" not in output
    assert "Infinity" not in output

