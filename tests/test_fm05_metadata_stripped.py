"""Regression test for FM-05's closure: _safe_write_data_js() strips a stray
top-level "metadata" key before writing, so a leftover from a stray
scripts/sync_data_js.py run (the deprecated Tier-3 pipeline) can never
silently persist forward through every subsequent partial-refresh build.

Before this fix, ci_validate_datajs.py WARNed forever ("data.js has
'metadata' and 'meta' with different content") because build_dashboard_data.py
never writes "metadata" itself but also never removes one it finds already
present in the file it loads and mutates -- json.loads()-then-patch-specific-
keys carries every other top-level key forward unchanged.
"""
import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
bdd = importlib.import_module("build_dashboard_data")


def test_stray_metadata_key_is_stripped_before_write(tmp_path):
    out = tmp_path / "data.js"
    payload = "window.DASH = " + json.dumps({
        "meta": {"real": True},
        "metadata": {"stale": True, "generated_by": "sync_data_js.py"},
        "primary": {"nsv_fy26": 1.0},
    }) + ";\n"
    bdd._safe_write_data_js(str(out), payload, skip_gate=True)

    written = out.read_text(encoding="utf-8")
    obj = json.loads(written[len("window.DASH = "):].rstrip().rstrip(";"))
    assert "metadata" not in obj
    assert obj["meta"] == {"real": True}
    assert obj["primary"] == {"nsv_fy26": 1.0}


def test_payload_without_metadata_key_is_unaffected(tmp_path):
    out = tmp_path / "data.js"
    payload = "window.DASH = " + json.dumps({
        "meta": {"real": True},
        "primary": {"nsv_fy26": 1.0},
    }) + ";\n"
    bdd._safe_write_data_js(str(out), payload, skip_gate=True)

    written = out.read_text(encoding="utf-8")
    obj = json.loads(written[len("window.DASH = "):].rstrip().rstrip(";"))
    assert obj == {"meta": {"real": True}, "primary": {"nsv_fy26": 1.0}}


def test_malformed_payload_falls_back_to_writing_unchanged(tmp_path):
    """A payload that isn't the expected 'window.DASH = {...};' shape (or
    doesn't parse) must still be written as-is, not dropped or corrupted --
    this guard fails closed, never closed-off."""
    out = tmp_path / "data.js"
    payload = "not a valid data.js payload at all"
    bdd._safe_write_data_js(str(out), payload, skip_gate=True)
    assert out.read_text(encoding="utf-8") == payload


def test_production_data_js_has_no_stray_metadata_key():
    """The currently-committed dashboard/data.js itself -- confirms FM-05
    is actually resolved in the live file, not just guarded for future
    writes."""
    path = REPO_ROOT / "dashboard" / "data.js"
    txt = path.read_text(encoding="utf-8")
    obj = json.loads(txt[len("window.DASH = "):].rstrip().rstrip(";"))
    assert "metadata" not in obj
