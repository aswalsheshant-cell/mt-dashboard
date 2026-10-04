"""Aug-26 store-wise offtake refresh (file re-supplied 2026-10-04): checked on the published data.js and the derived chain view.

The refreshed store x article CSV itself is not committed: the restricted-source firewall pins the tracked Aug-26 file by SHA-256
(config/restricted_source_policy.yml, owner decision I-2), so the refresh lives in data.js and the derived aggregates.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def offtake():
    txt = (ROOT / "dashboard" / "data.js").read_text()
    return json.loads(txt[txt.index("{"): txt.rstrip().rstrip(";").rindex("}") + 1])["offtake"]


def test_aug26_total_and_fy_baselines(offtake):
    assert offtake["months_fy27"][-1] == "Aug-26"
    assert offtake["monthly_fy27"][-1] == pytest.approx(3901.83, abs=0.02)            # Aug-26 ex Reliance Brand Counter, Rs lakh
    assert offtake["total_fy27"] == pytest.approx(sum(offtake["monthly_fy27"]), abs=0.05) and offtake["total_fy27"] == pytest.approx(18971.69, abs=0.02)
    assert offtake["total_fy26"] == pytest.approx(31119.87, abs=0.02)                  # FY26 baseline unchanged


def test_restated_and_missing_chains(offtake):
    fy27 = {c["name"]: c.get("fy27") for c in offtake["by_chain"]}
    assert fy27["DMart"] == pytest.approx(7017.13, abs=0.02) and fy27["Reliance Retail"] == pytest.approx(4708.35, abs=0.02)   # restated down
    assert fy27["Apollo"] == pytest.approx(3616.22, abs=0.02)
    assert fy27["VMM"] == pytest.approx(166.95, abs=0.02) and fy27["V-Mart"] == pytest.approx(64.40, abs=0.02)             # Aug-26 added


def test_derived_chain_view_has_the_missing_chains():
    cc = pd.read_csv(ROOT / "data" / "nielsen" / "Chain_Contribution_Aug26.csv")
    names = {str(c).strip().upper() for c in cc["Chain"]}
    assert {"VMM", "V-MART"} <= names or {"VISHAL MEGA MART", "V-MART"} <= names or any("VMM" in n or "VISHAL" in n for n in names)
