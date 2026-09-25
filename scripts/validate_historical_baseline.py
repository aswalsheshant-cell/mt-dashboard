#!/usr/bin/env python3
"""CI step: verify the FY25/FY26 historical baseline from LIVE canonical fields.

Replaces the check that used to read the deprecated top-level `metadata` key
(`metadata.coverage.fiscal_years` / `fy25_months` / `fy26_months`). That block
was never written by the production generator (`scripts/build_dashboard_data.py`)
-- it is a frozen leftover from the retired `scripts/sync_data_js.py` / Tier-3
`data_master.json` pipeline (see FM-05, docs/FAILURE_MODE_REGISTER.md), and its
own FY-month split is wrong by THE ONE FY RULE (see the "Known data.js hygiene
issue" note in docs/DATA_AVAILABILITY_MATRIX.md). PR #180 correctly strips it;
this check must not depend on it, or on anything with the same drift risk.

Per THE ONE FY RULE / three-measures documentation (CLAUDE.md,
docs/DATA_AVAILABILITY_MATRIX.md), Primary and Offtake genuinely have no FY25
extract anywhere in this repo -- that is a real, confirmed source-data
boundary, not a defect. The ONLY real FY25 series across all three MT measures
is Distributor Secondary (`offtake.secondary_total_fy25` /
`offtake.secondary_months_fy25`). So the canonical baseline this check proves is:

  FY26  -- 'fy26' present in BOTH primary.fy_tags and offtake.fy_tags
           (Primary billing and Offtake POS both genuinely cover FY26)
  FY25  -- offtake.secondary_total_fy25 is a real number AND
           offtake.secondary_months_fy25 is a non-empty month list
           (Distributor Secondary is the one real FY25 series; a scalar total
           alone does not prove coverage, so both are required)

Fails closed: any missing/null/wrong-type field is a FAIL with a specific
message naming exactly what's missing -- never silently treated as
empty/zero/valid, and the deprecated `metadata` key is never read, so its
presence or absence never changes the result.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_datajs(path=None):
    """Parse window.DASH out of data.js."""
    text = Path(path or REPO / "dashboard" / "data.js").read_text()
    m = re.search(r"window\.DASH\s*=\s*", text)
    body = text[m.end():] if m else text
    return json.loads(body.strip().rstrip(";"))


def check_historical_baseline(data):
    """Validate the canonical live FY25/FY26 historical baseline.

    Returns (ok: bool, messages: list[str]). `messages` holds a "✓ ..." line
    per invariant that held and an "ERROR: ..." line per invariant that
    didn't; `ok` is True only when zero ERROR lines were produced.
    """
    if not isinstance(data, dict):
        return False, ["ERROR: Top-level data.js payload is not a JSON object"]

    messages = []
    errors = []

    primary = data.get("primary")
    if not isinstance(primary, dict):
        errors.append("ERROR: Canonical 'primary' block missing or malformed")
        primary = {}

    offtake = data.get("offtake")
    if not isinstance(offtake, dict):
        errors.append("ERROR: Canonical 'offtake' block missing or malformed")
        offtake = {}

    # ---- FY26: Primary (billing) + Offtake (POS) ----
    primary_tags = primary.get("fy_tags")
    if not isinstance(primary_tags, list):
        errors.append(
            "ERROR: Canonical Primary fiscal-year coverage field "
            "(primary.fy_tags) missing, null, or not a list"
        )
        primary_tags = []

    offtake_tags = offtake.get("fy_tags")
    if not isinstance(offtake_tags, list):
        errors.append(
            "ERROR: Canonical Offtake fiscal-year coverage field "
            "(offtake.fy_tags) missing, null, or not a list"
        )
        offtake_tags = []

    primary_tags_lo = [str(t).lower() for t in primary_tags]
    offtake_tags_lo = [str(t).lower() for t in offtake_tags]

    if "fy26" not in primary_tags_lo:
        errors.append(
            "ERROR: Missing required fiscal years: ['fy26'] not found in "
            f"primary.fy_tags (found: {primary_tags})"
        )
    else:
        messages.append(f"✓ Primary FY26 coverage verified: {primary_tags}")

    if "fy26" not in offtake_tags_lo:
        errors.append(
            "ERROR: Missing required fiscal years: ['fy26'] not found in "
            f"offtake.fy_tags (found: {offtake_tags})"
        )
    else:
        messages.append(f"✓ Offtake FY26 coverage verified: {offtake_tags}")

    # ---- FY25: Distributor Secondary (the one real FY25 series) ----
    sec_total = offtake.get("secondary_total_fy25")
    if sec_total is None or isinstance(sec_total, bool) or not isinstance(sec_total, (int, float)):
        errors.append(
            "ERROR: Missing required fiscal years: FY25 Distributor Secondary "
            "total (offtake.secondary_total_fy25) missing, null, or not numeric"
        )
    else:
        messages.append(f"✓ FY25 Distributor Secondary total verified: {sec_total}")

    sec_months = offtake.get("secondary_months_fy25")
    if not isinstance(sec_months, list) or len(sec_months) == 0:
        errors.append(
            "ERROR: Missing required fiscal years: FY25 Distributor Secondary "
            "month coverage (offtake.secondary_months_fy25) missing, empty, "
            "or not a list"
        )
    else:
        messages.append(f"✓ FY25 Distributor Secondary month coverage: {len(sec_months)} months")

    ok = len(errors) == 0
    if ok:
        messages.append("✓ Historical baseline integrity verified (canonical live fields)")
    return ok, messages + errors


def main():
    try:
        data = load_datajs()
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in data.js: {e}")
        return 1

    ok, messages = check_historical_baseline(data)
    for line in messages:
        print(line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
