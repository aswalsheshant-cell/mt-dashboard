"""Aug-26 store-wise offtake refresh (file re-supplied 2026-10-04): checked on the published data.js and the derived chain view.

The refreshed store x article CSV is committed (owner's instruction 2026-10-04) and re-pinned in config/restricted_source_policy.yml.
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
    assert offtake["months_fy27"][:5] == ["Apr-26", "May-26", "Jun-26", "Jul-26", "Aug-26"] and offtake["months_fy27"][5] == "Sep-26"
    assert offtake["monthly_fy27"][4] == pytest.approx(3901.83, abs=0.02)             # Aug-26 ex Reliance Brand Counter, Rs lakh
    assert offtake["monthly_fy27"][5] == pytest.approx(3318.40, abs=0.02)             # Sep-26 as received 2026-10-16: PARTIAL, 10+ chains pending
    assert sum(offtake["monthly_fy27"][:5]) == pytest.approx(18971.69, abs=0.05)      # Apr-Aug unchanged by the Sep load
    assert offtake["total_fy27"] == pytest.approx(sum(offtake["monthly_fy27"]), abs=0.05) and offtake["total_fy27"] == pytest.approx(22290.09, abs=0.02)
    assert offtake["total_fy26"] == pytest.approx(31119.87, abs=0.02)                  # FY26 baseline unchanged


def test_restated_and_missing_chains(offtake):
    fy27 = {c["name"]: c.get("fy27") for c in offtake["by_chain"]}
    assert fy27["DMart"] == pytest.approx(8279.32, abs=0.02) and fy27["Reliance Retail"] == pytest.approx(5446.39, abs=0.02)   # Apr-Sep (7017.13 / 4708.35 to Aug)
    assert fy27["Apollo"] == pytest.approx(4313.81, abs=0.02)
    assert fy27["VMM"] == pytest.approx(199.06, abs=0.02) and fy27["V-Mart"] == pytest.approx(64.40, abs=0.02)             # V-Mart: Sep-26 not received, so unchanged


def test_derived_chain_view_has_the_missing_chains():
    cc = pd.read_csv(ROOT / "data" / "nielsen" / "Chain_Contribution_Aug26.csv")
    names = {str(c).strip().upper() for c in cc["Chain"]}
    assert {"VMM", "V-MART"} <= names or {"VISHAL MEGA MART", "V-MART"} <= names or any("VMM" in n or "VISHAL" in n for n in names)


def test_committed_aug_csv_is_the_refreshed_file():
    aug = pd.read_csv(ROOT / "PowerBI" / "RawDataFolders" / "Offtake_Monthly" / "offtake_store_article_Aug_26.csv", usecols=["Chain Name", "NSV", "SO/ASE Emp Code", "SO/ASE Name"], low_memory=False)
    by = aug.assign(c=aug["Chain Name"].str.strip()).groupby("c")["NSV"].sum()
    assert by["Vmm"] == pytest.approx(41.52, abs=0.01) and by["V-Mart"] == pytest.approx(14.97, abs=0.01) and by["Dmart"] == pytest.approx(1388.74, abs=0.01)
    assert aug["SO/ASE Emp Code"].isna().all() and aug["SO/ASE Name"].isna().all()           # no employee values in the committed file
