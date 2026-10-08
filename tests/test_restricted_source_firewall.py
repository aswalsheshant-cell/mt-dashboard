"""Restricted-source firewall (scripts/restricted_source_firewall.py).

Found 2026-10-01 on main 6aa2e3c: the public repository tracked 56 raw extract
files (Primary article, store x article Offtake, Ship-To, Secondary, Master_Data,
Aug'26 detail, archive dumps) and PowerBI/SeedData/Mapping/Store_SO_Mapping.csv
with employee IDs and names, against docs/DATA_SECURITY_CLASSIFICATION.md.
Nothing stopped a new one being added. These tests make a NEW restricted file,
or growth of an existing one, fail the suite (which runs inside the required
Production Acceptance Gate). Removing the existing ones is owner decision I-2.

Fixtures below use made-up paths and header names only; no real data.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import restricted_source_firewall as fw  # noqa: E402


@pytest.fixture(scope="module")
def policy():
    return fw.load_policy()


def test_no_confidential_raw_source_is_tracked(policy):
    failures, known = fw.check(fw.tracked_files(), policy)
    assert failures == [], "\n".join(failures)
    assert known, "premise: today's known debt is recorded, not hidden"


def _run(policy, paths, headers=None, hashes=None):
    headers = headers or {}
    hashes = hashes or {}
    return fw.check(paths, policy, header_of=lambda p: headers.get(p, ""),
                    hash_of=lambda p: hashes.get(p, "x"))


def test_new_raw_extract_fails(policy):
    p = "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Sep_26.csv"
    failures, _ = _run({**policy, "known_debt": []}, [p], headers={p: "Month,Chain,Article,NSV\n"})
    assert failures and failures[0].startswith("NEW CUSTOMER_STORE_ARTICLE_RAW")


def test_employee_columns_fail_anywhere(policy):
    p = "PowerBI/SeedData/Mapping/some_new_mapping.csv"
    failures, _ = _run({**policy, "known_debt": []}, [p], headers={p: "Store Code,Employee ID 1,Cont%\n"})
    assert failures and "EMPLOYEE_RAW" in failures[0]


def test_known_debt_cannot_change(policy):
    p = "PowerBI/RawDataFolders/Offtake_Monthly/x.csv"
    pol = {**policy, "known_debt": [{"path": p, "class": "CUSTOMER_STORE_ARTICLE_RAW", "sha256": "aaa"}]}
    assert _run(pol, [p], hashes={p: "aaa"})[0] == []
    failures, _ = _run(pol, [p], hashes={p: "bbb"})
    assert failures and failures[0].startswith("CHANGED")


def test_stale_debt_entry_fails(policy):
    pol = {**policy, "known_debt": [{"path": "gone.csv", "class": "X", "sha256": "a"}]}
    failures, _ = _run(pol, [])
    assert failures and failures[0].startswith("STALE")


def test_templates_and_aggregates_are_allowed(policy):
    paths = ["PowerBI/RawDataFolders/Offtake_Monthly/_TEMPLATE_Offtake_Monthly.csv",
             "PowerBI/RawDataFolders/Offtake_Monthly/_README.txt",
             "PowerBI/SeedData/Targets/FY2627_Targets.csv"]
    headers = {paths[2]: "MonthStart,Month,FY Year,Quarter,Target NSV Cr\n"}
    assert _run({**policy, "known_debt": []}, paths, headers=headers)[0] == []
