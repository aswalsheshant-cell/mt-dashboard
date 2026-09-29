"""45_Fact_ClaimMaster.pq defect fix (2026-09-27) -- sibling of the #261 fix to 44.

Static checks (no Power BI Desktop in the repo):
  * no column list passed as fnCombineFolder's HeaderRow number argument;
  * the folder sits directly under pRootFolder (00_Parameters.pq), not pRootFolder\\PowerBI;
  * only claim_master_chain_*.csv is read -- the same folder holds the brand and
    distributor claim files, whose totals would otherwise be added to the chain fact;
  * only the six expense components are unpivoted: Total_Claim_Lakh (their sum) and the
    extra Entity / Amount_Lakh columns in the chain CSV must never become categories,
    or SUM('Fact Claim Master'[Amount_Lakh]) counts every claim twice.
The last test replays the query's column logic on the real CSV and checks the fact
total equals the chain file's Total_Claim_Lakh.
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PQ = ROOT / "PowerBI/PowerQuery/45_Fact_ClaimMaster.pq"
FOLDER = ROOT / "PowerBI/RawDataFolders/ClaimMaster_Quarterly"
PREFIX = "claim_master_chain_"
COMPONENTS = ["Chain_Promo_Lakh", "Rate_Diff_Lakh", "Freight_Lakh",
              "Incentive_Lakh", "Off_Invoice_Lakh", "Visibility_Lakh"]


def _code():
    """Query text without // comments (the commented companion block is not executed)."""
    return "\n".join(l.split("//", 1)[0] for l in PQ.read_text(encoding="utf-8").splitlines())


def test_no_list_passed_to_fncombinefolder():
    for call in re.finditer(r"fnCombineFolder\s*\(([^()]*)\)", _code()):
        assert "{" not in call.group(1), f"list passed to fnCombineFolder: {call.group(0)}"


def test_reads_only_chain_claim_files_directly_under_prootfolder():
    code = _code()
    assert re.search(r'Folder\.Files\(\s*pRootFolder\s*&\s*"\\RawDataFolders\\ClaimMaster_Quarterly"\s*\)', code)
    assert "\\PowerBI\\RawDataFolders" not in code
    assert re.search(r'Text\.StartsWith\(\s*Text\.Lower\(\[Name\]\)\s*,\s*"' + PREFIX + r'"\s*\)', code)
    assert code.index(PREFIX) < code.index("Csv.Document"), "filter files before parsing them"
    assert "MissingField.Error" in code


def test_unpivots_the_six_components_only():
    code = _code()
    m = re.search(r"Table\.Unpivot\(\s*\w+\s*,\s*(\w+|\{[^}]*\})", code)
    assert m, "use Table.Unpivot with an explicit component list, not UnpivotOtherColumns"
    assert "UnpivotOtherColumns" not in code
    listed = m.group(1)
    if not listed.startswith("{"):
        listed = re.search(listed + r"\s*=\s*(\{[^}]*\})", code).group(1)
    names = re.findall(r'"([^"]+)"', listed)
    assert sorted(names) == sorted(COMPONENTS), names


def test_fact_total_equals_chain_file_total():
    """Replay the query's column logic on the committed chain CSV(s)."""
    files = sorted(p for p in FOLDER.glob("*.csv") if p.name.lower().startswith(PREFIX))
    assert files, "no chain claim file"
    others = [p.name for p in FOLDER.glob("*.csv") if p not in files]
    assert any("brand" in n for n in others) and any("distributor" in n for n in others)
    keep = ["Period", "FY_Year", "Quarter", "Chain", "Source_Chain"] + COMPONENTS + ["Total_Claim_Lakh"]
    c = pd.concat([pd.read_csv(p) for p in files])[keep]   # the query's SelectColumns step
    fact = c.melt(id_vars=["Period", "FY_Year", "Quarter", "Chain", "Source_Chain"],
                  value_vars=COMPONENTS, value_name="Amount_Lakh")
    fact = fact[fact["Amount_Lakh"] != 0]
    assert abs(fact["Amount_Lakh"].sum() - c["Total_Claim_Lakh"].sum()) < 0.01


def test_quicksetup_copy_matches():
    qs = (ROOT / "PowerBI/QuickSetup/AllPowerQuery_Consolidated.txt").read_text(encoding="utf-8")
    assert PQ.read_text(encoding="utf-8").strip() in qs, "run python scripts/build_quicksetup.py"
