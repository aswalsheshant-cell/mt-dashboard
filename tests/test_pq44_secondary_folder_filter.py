"""44_Fact_SecondarySales.pq defect fix (2026-09-27).

Static checks (no Power BI Desktop in the repo):
  * the query must not pass a column list as fnCombineFolder's second argument,
    which 01_fnCombineFolder.pq types as `optional HeaderRow as nullable number`;
  * it must read only secondary_sales_distributor_*.csv from SecondarySales_Monthly,
    because the same folder holds chain/brand registers and two tot_hierarchy
    files that repeat Apr-Aug'26 (reading them would double or triple count);
  * the folder path must sit directly under pRootFolder (which already points at
    the PowerBI folder - 00_Parameters.pq), not under pRootFolder\\PowerBI.
"""
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PQ = ROOT / "PowerBI/PowerQuery/44_Fact_SecondarySales.pq"
FN = ROOT / "PowerBI/PowerQuery/01_fnCombineFolder.pq"
FOLDER = ROOT / "PowerBI/RawDataFolders/SecondarySales_Monthly"
PREFIX = "secondary_sales_distributor_"


def _code(path):
    """Query text without // comments."""
    return "\n".join(line.split("//", 1)[0] for line in path.read_text(encoding="utf-8").splitlines())


def test_fncombinefolder_second_argument_is_a_number():
    sig = re.search(r"fnCombineFolder\s*=\s*\(([^)]*)\)", _code(FN)).group(1)
    assert "optional HeaderRow as nullable number" in sig


def test_query_does_not_pass_a_list_to_fncombinefolder():
    code = _code(PQ)
    # any remaining fnCombineFolder call must not carry a { ... } list argument
    for call in re.finditer(r"fnCombineFolder\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)", code):
        assert "{" not in call.group(1), f"list passed to fnCombineFolder: {call.group(0)}"


def test_query_filters_to_distributor_register_files_before_parsing():
    code = _code(PQ)
    assert re.search(r'Folder\.Files\(\s*pRootFolder\s*&\s*"\\RawDataFolders\\SecondarySales_Monthly"\s*\)', code), \
        "must list the SecondarySales_Monthly folder directly under pRootFolder"
    assert "\\PowerBI\\RawDataFolders" not in code, "pRootFolder already points at the PowerBI folder"
    assert re.search(r'Text\.StartsWith\(\s*Text\.Lower\(\[Name\]\)\s*,\s*"' + PREFIX + r'"\s*\)', code), \
        "name filter on secondary_sales_distributor_ missing"
    assert re.search(r'Text\.Lower\(\[Extension\]\)\s*=\s*"\.csv"', code)
    # filter must come before the files are parsed
    assert code.index(PREFIX) < code.index("Csv.Document")
    assert "MissingField.Error" in code, "schema drift must fail the refresh, not load nulls"


def test_filter_selects_only_the_q1_and_jul_aug_distributor_files():
    picked = sorted(p.name for p in FOLDER.iterdir()
                    if p.name.lower().startswith(PREFIX) and p.suffix.lower() == ".csv")
    assert picked == ["secondary_sales_distributor_Jul_Aug_FY27.csv", "secondary_sales_distributor_Q1_FY27.csv"] \
        or picked == ["secondary_sales_distributor_Q1_FY27.csv"], picked
    others = [p.name for p in FOLDER.glob("*.csv") if p.name not in picked]
    assert any("tot_hierarchy" in n for n in others), "hierarchy files must stay excluded"
    # the files the filter keeps never repeat a month x distributor
    d = pd.concat([pd.read_csv(FOLDER / n) for n in picked])
    assert not d.duplicated(["Source_Month", "Distributor"]).any()


def test_quicksetup_copy_matches():
    qs = (ROOT / "PowerBI/QuickSetup/AllPowerQuery_Consolidated.txt").read_text(encoding="utf-8")
    body = PQ.read_text(encoding="utf-8").strip()
    assert body in qs, "run python scripts/build_quicksetup.py"
