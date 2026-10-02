"""B1 / CB-01: FY27 zone sales are MT accounts only.

MT Leadership decision 2026-10-01 (DA): Decision 1 = MT-only views, Decision 2 =
A (Nykaa (FSN) under eB2B). Before the fix the FY27 zone rollup in
detail_meta.fyx_primary equalled the all-channel total, so Rs 11.64 Cr of eB2B
and SIS sat inside geographic MT zones and scripts/mt_channel_reconciliation.py
exited 2 (BLOCKED).

Decision 3 = B (restate FY26 on the MT basis) is NOT applied here: it changes a
protected baseline and waits for its signed approval reference. These tests
also pin that FY26 is untouched.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "dashboard" / "data.js"


@pytest.fixture(scope="module")
def d():
    s = DATA.read_text(encoding="utf-8")
    return json.loads(s[s.index("{"): s.rindex("}") + 1])


@pytest.fixture(scope="module")
def fx(d):
    return d["detail_meta"]["fyx_primary"]["FY27"]


def test_fy27_zone_rollup_equals_mt_channel(fx):
    zones = sum(z["nsv"] for z in fx["by_zone"])
    mt = next(c["nsv"] for c in fx["by_channel"] if c["name"] == "MT")
    assert abs(zones - mt) < 1.0, f"zones {zones} vs MT {mt}"
    assert abs(zones - fx["nsv"]) > 100, "zone rollup still equals the all-channel total"


def test_non_mt_kept_under_its_own_channel_not_dropped(fx):
    # every rupee is still accounted for: MT zones + non-MT per zone = all-channel total
    non_mt = sum(v for z in fx["non_mt_by_zone"] for k, v in z.items() if k != "name")
    assert abs(sum(z["nsv"] for z in fx["by_zone"]) + non_mt - fx["nsv"]) < 1.0
    chans = {c["name"] for c in fx["by_channel"]}
    assert {"EB2B", "SIS"} <= chans


def test_nykaa_is_reported_under_eb2b(fx):
    acct = {a["name"]: a for a in fx["non_mt_accounts"]}
    assert acct["Nykaa (FSN)"]["channel"] == "EB2B"
    assert "MT channel only" in fx["by_zone_basis"]


def test_fy26_baseline_untouched(d):
    # Decision 3B (restate FY26) is not applied without its signed approval
    assert d["primary"]["by_zone"] and all("fy27" not in z for z in d["primary"]["by_zone"])
    fy26 = sum(c.get("fy26") or 0 for c in d["primary"]["by_channel"])
    assert abs(fy26 - 32900.36) < 0.05


def test_channel_control_passes():
    r = subprocess.run([sys.executable, str(ROOT / "scripts/mt_channel_reconciliation.py"), str(DATA)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-1500:]
