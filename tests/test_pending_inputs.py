"""config/pending_inputs.yml covers every blocked page, and everything it says exists really exists."""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
D = yaml.safe_load((ROOT / "config" / "pending_inputs.yml").read_text(encoding="utf-8"))


def test_every_blocked_page_has_a_named_missing_input():
    pages = json.loads((ROOT / "PowerBI" / "full_report_pages.json").read_text(encoding="utf-8"))["pages"]
    need = {p["page_id"] for p in pages if p["status"] in ("NO_SOURCE", "NO_MODEL_SOURCE")}
    have = {u for i in D["items"] for u in i["unblocks"]}
    assert need <= have, need - have


def test_files_listed_as_existing_exist():
    for i in D["items"]:
        for p in i["what_exists"]:
            assert (ROOT / p).exists(), (i["id"], p)


def test_every_item_names_an_owner_and_what_is_missing():
    for i in D["items"]:
        assert i["owner"].strip() and i["what_is_missing"].strip() and i["status"].strip(), i["id"]


def test_tdp_blocks_the_five_pages_in_the_ledger():
    tdp = next(i for i in D["items"] if i["id"] == "TDP_MONTHLY")
    assert sorted(tdp["unblocks"]) == ["1", "10", "11", "7", "9"]
