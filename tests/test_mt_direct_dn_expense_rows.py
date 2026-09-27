"""MT Direct DN claims loaded into PL_Expense_Input.csv (registry: mt_direct_dn_claims).

Guards the committed rows (no source workbook needed) and the loader's rules on a
small synthetic frame (tmp only, never written to the repo):
  * 64 rows, Rs1,274.71 L excl. GST, all FY27 Apr-Aug 2026, no duplicate CM2 keys
  * no Nykaa / EB2B customer (1103979) rows -- held out, channel "GT_ e B2B"
  * every chain resolves to a Primary chain; Tnsi Retail (1100027) = WH-Smith by
    owner decision 2026-09-27 (loader OWNER_CHAIN_DECISIONS), never guessed
  * Jul/Aug 2026 rows carry the PARTIAL MONTH marker (owner decision 2026-09-27)
  * FM-14: no provision row shares a Month x Chain x Expense Head with a DN row
  * the 3 template rows are untouched and the file is otherwise a pure append
  * loader: drops exact duplicates, holds out non-MT-Direct, FY from the claim month
"""
import csv
import importlib
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
bd = importlib.import_module("build_dashboard_data")
dn = importlib.import_module("ingest_mt_direct_dn")
SEED = ROOT / "PowerBI" / "SeedData" / "Masters" / "PL_Expense_Input.csv"


def _dn_rows():
    with open(SEED, newline="", encoding="utf-8") as fh:
        return [r for r in csv.DictReader(fh) if (r.get("Source") or "").startswith(dn.SOURCE_TAG)]


def test_loaded_rows_total_and_period():
    rows = _dn_rows()
    assert len(rows) == 64
    assert round(sum(float(r["Expense Amount (INR Lakh)"]) for r in rows), 2) == 1274.71
    assert {bd._fylabel(r["FY"]) for r in rows} == {"FY27"}
    assert {bd._mlabel(r["Month"]) for r in rows} == set(bd._ORDER[:5])   # Apr-Aug in the pipeline's own labels
    keys = [tuple((r.get(k) or "").strip().lower() for k in bd._EXPENSE_DEDUP_FIELDS) for r in rows]
    assert len(keys) == len(set(keys)), "a DN row would be dropped as a CM2 duplicate"


def test_no_eb2b_nykaa_rows_loaded():
    rows = _dn_rows()
    assert not [r for r in rows if r["Customer Code"] == "1103979" or "NYKAA" in r["Customer Name"].upper()]


def test_all_chains_resolve_tnsi_is_wh_smith():
    known = dn.primary_chains()
    unresolved = {r["Chain"] for r in _dn_rows() if bd.canon_chain(r["Chain"]) not in known}
    assert unresolved == set()
    tnsi = [r for r in _dn_rows() if r["Customer Code"] == "1100027"]
    assert {r["Chain"] for r in tnsi} == {"WH-Smith"}
    assert round(sum(float(r["Expense Amount (INR Lakh)"]) for r in tnsi), 2) == 5.20
    assert all("owner decision 2026-09-27" in r["Remarks"] for r in tnsi)
    assert dn.OWNER_CHAIN_DECISIONS["1100027"][0] == "WH-Smith"


def test_partial_months_marked_only_on_jul_aug():
    for r in _dn_rows():
        marked = dn.PARTIAL_MARK in r["Remarks"]
        assert marked == (r["Month"] in ("July", "August")), (r["Month"], r["Remarks"])


def test_no_provision_row_overlaps_a_dn_row():
    # FM-14: a provision and its later DN describe one commercial event.
    with open(SEED, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    key = lambda r: (r["Month"].strip().lower(), bd.canon_chain(r["Chain"]), r["Expense Head"].strip().lower())
    dn_keys = {key(r) for r in rows if (r.get("Source") or "").startswith(dn.SOURCE_TAG)}
    prov = [r for r in rows if "provision" in ((r.get("Source") or "") + (r.get("Remarks") or "")).lower()]
    assert not [r for r in prov if key(r) in dn_keys]


def test_file_is_template_plus_append():
    head = subprocess.run(["git", "show", "7204491:PowerBI/SeedData/Masters/PL_Expense_Input.csv"],
                          cwd=ROOT, capture_output=True)
    if head.returncode != 0:   # shallow clone without that commit: fall back to the template marker
        with open(SEED, newline="", encoding="utf-8") as fh:
            assert sum("EXAMPLE ROW" in (r.get("Remarks") or "").upper() for r in csv.DictReader(fh)) == 3
        return
    assert SEED.read_bytes().startswith(head.stdout), "an existing line of the seed file was changed"


def _frame(rows):
    return pd.DataFrame(rows, columns=dn.COLS).assign(
        ExpMonth=lambda d: pd.to_datetime(d["ExpMonth"]), Base=lambda d: d["Base"].astype(float),
        DN_No=lambda d: d["DN_No"].astype(str), Code=lambda d: d["Code"].astype(str))


def test_loader_rules_on_synthetic_frame():
    r = ["2025-26", "1100022", "2026-05-01", None, None, "MT Direct", "Reliance", "SYN-1", 100000.0, 18000.0, 118000.0, "syn", "Promotion"]
    dup = list(r)
    eb2b = ["2026-27", "1103979", "2026-05-01", None, None, "GT_ e B2B", "NYKAA SS (FSN)", "SYN-2", 500000.0, 0.0, 500000.0, "syn", "Promotion"]
    vis = ["2026-27", "1100049", "2026-06-01", None, None, "MT Direct", "Wellness", "SYN-3", 50000.0, 0.0, 50000.0, "syn", "Visiblity"]
    rows, rep = dn.build_rows(_frame([r, dup, eb2b, vis]), "2026-09-26")
    assert rep["duplicate_rows_dropped"] == 1
    assert rep["held_out_non_mt_direct"] == {"NYKAA SS (FSN) / GT_ e B2B": 5.0}
    assert rep["fy_label_overridden_rows"] == 1          # '2025-26' on a May-2026 claim
    by_chain = {x["Chain"]: x for x in rows}
    assert by_chain["Reliance Retail"]["FY"] == "FY26-27" and by_chain["Reliance Retail"]["Month"] == "May"
    assert by_chain["Reliance Retail"]["Expense Amount (INR Lakh)"] == "1.0000"   # base excl. GST
    assert by_chain["Wellness Forever"]["Expense Head"] == "Visibility"
    assert rep["written_lakh"] == 1.5
    assert dn.PARTIAL_MARK not in by_chain["Reliance Retail"]["Remarks"]          # May: complete


def test_loader_owner_decisions_on_synthetic_frame():
    tnsi = ["2026-27", "1100027", "2026-07-01", None, None, "MT Direct", "Tnsi Retail Pvt Ltd", "SYN-4", 150000.0, 27000.0, 177000.0, "syn", "Visibility"]
    rows, rep = dn.build_rows(_frame([tnsi]), "2026-09-27")
    assert rows[0]["Chain"] == "WH-Smith" and rep["unresolved_chain_lakh"] == {}
    assert dn.PARTIAL_MARK in rows[0]["Remarks"]                                   # July: partial
