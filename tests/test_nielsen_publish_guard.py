"""The Nielsen market-share page must never be built or published from an ungoverned payload.

Found 2026-10-01 on main 6aa2e3c: data/nielsen_aug26.json says
"SAMPLE -- replace with actual Nielsen Aug 26 extract before building" (its share
series is the July file moved one month later plus an invented Aug value), yet
.github/workflows/build-nielsen-dashboard.yml built it, copied it to
market-share.html on GitHub Pages and created release `nielsen-dashboard-aug26`.

Two guards, both required:
  * builder: scripts/build_nielsen_dashboard.py refuses an ungoverned payload
    (SAMPLE marker, data_status != GOVERNED, missing source/validation reference)
    and writes nothing;
  * workflow: a separate guard step runs that check before build and publish,
    and the workflow creates no GitHub Release (CLAUDE.md: zero releases).
"""
import copy
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_nielsen_dashboard as bn  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "build-nielsen-dashboard.yml"
SAMPLE = ROOT / "data" / "nielsen_aug26.json"
JUL = ROOT / "data" / "nielsen_jul26.json"


def _governed(base):
    d = copy.deepcopy(base)
    d.pop("_comment", None)
    d.update({"data_status": "GOVERNED",
              "source_reference": "Nielsen RMS <report name, period, delivery date>",
              "validation_reference": "registry entry + reconciliation evidence"})
    return d


def test_sample_payload_is_rejected():
    # The old SAMPLE file was replaced by the governed Aug-26 payload (2026-10-04);
    # the guard is still proven on a payload carrying the same marker.
    d = json.loads(SAMPLE.read_text(encoding="utf-8"))
    d["_comment"] = "SAMPLE -- replace with actual Nielsen Aug 26 extract before building"
    errs = bn.governance_errors(d)
    assert any("SAMPLE" in e for e in errs)


def test_payload_without_governed_status_is_rejected():
    # nielsen_jul26.json carries no data_status / references (provenance unconfirmed).
    errs = bn.governance_errors(json.loads(JUL.read_text(encoding="utf-8")))
    assert any("data_status" in e for e in errs)
    assert any("source_reference" in e for e in errs)


def test_governed_payload_passes():
    assert bn.governance_errors(_governed(json.loads(JUL.read_text(encoding="utf-8")))) == []


def test_build_writes_nothing_for_sample(tmp_path):
    out = tmp_path / "out.html"
    src = tmp_path / "sample.json"
    d = json.loads(SAMPLE.read_text(encoding="utf-8"))
    d["_comment"] = "SAMPLE -- replace with actual Nielsen Aug 26 extract before building"
    src.write_text(json.dumps(d), encoding="utf-8")
    with pytest.raises(SystemExit):
        bn.build(bn.DEFAULT_TEMPLATE, src, out)
    assert not out.exists()


def test_build_still_works_for_governed_payload(tmp_path):
    src = tmp_path / "nielsen_test.json"
    src.write_text(json.dumps(_governed(json.loads(JUL.read_text(encoding="utf-8")))), encoding="utf-8")
    out = tmp_path / "out.html"
    bn.build(bn.DEFAULT_TEMPLATE, src, out)
    assert out.exists() and out.stat().st_size > 0


def _steps():
    text = WORKFLOW.read_text(encoding="utf-8")
    return re.findall(r"^\s*- name:\s*(.+)$", text, re.M), text


def test_workflow_guard_runs_before_build_and_publish():
    names, text = _steps()
    guard = next(i for i, n in enumerate(names) if "governance guard" in n.lower())
    build = next(i for i, n in enumerate(names) if n.strip().lower() == "build dashboard")
    publish = next(i for i, n in enumerate(names) if "publish" in n.lower())
    assert guard < build < publish
    assert "--check-only" in text


def test_workflow_creates_no_release():
    _, text = _steps()
    assert "createRelease" not in text and "Create GitHub Release" not in text
