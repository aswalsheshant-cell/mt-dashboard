#!/usr/bin/env python3
"""Monthly refresh of the market-share report (the Nielsen Cuts / Chain Share & Plan HTML, the MT dashboard card and the Power BI seeds) in one command.

It runs the existing builders in the right order and stops at the first failure. Steps whose input files are not given are skipped and listed,
so a partial month still builds. Nothing is estimated: a missing input leaves that block as it was.

    python scripts/refresh_market_share_report.py --label Sep26 --month "Sep 26" --months Apr May Jun Jul Aug Sep \\
        --tracker-from data/nielsen_aug26.json --standalone \\
        [--facewash Nielson_FW_Report_Sep26.xlsb --shampoo Nielson_Shampoo_Report_Sep26.xlsb] \\
        [--lulu ... --more ... --wellness ... --reliance ...] [--store-master Final_..._storelist.xlsb]

Order: Nielsen CSVs -> store master -> chain view and price/volume (internal offtake) -> city plan -> account share -> payload (twice: the account view
needs it for the Facewash plan, the payload carries the account view) -> data.js card file -> standalone HTML -> Power BI seeds -> checks.
Then: python -m pytest -q   and   node tests/nielsen_ms_browser.js <html> <shots> aug
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


def plan(a):
    """[(step name, argv or None, why skipped)] in run order."""
    s = lambda f: str(ROOT / "scripts" / f)   # noqa: E731
    payload = f"data/nielsen_{a.label.lower()}.json"
    steps = []
    steps.append(("Nielsen workbooks -> CSVs", [PY, s("extract_nielsen_report.py"), "--facewash", str(a.facewash), "--shampoo", str(a.shampoo), "--label", a.label]
                  if a.facewash and a.shampoo else None, "no --facewash / --shampoo: the CSVs for this label must already be in data/nielsen"))
    steps.append(("Store master (unique stores, state and zone from the offtake)", [PY, s("build_store_city_master.py"), "--master", str(a.store_master), "--months", *a.months]
                  if a.store_master else None, "no --store-master: the committed store master is used"))
    steps.append(("Chain contribution and pack presence", [PY, s("build_nielsen_chain_view.py"), "--months", *a.months, "--label", a.label], None))
    steps.append(("Price and volume", [PY, s("build_nielsen_price_volume.py"), "--label", a.label, "--month", a.month, "--months", *a.months], None))
    steps.append(("Payload (first pass)", [PY, s("build_nielsen_payload.py"), "--label", a.label, "--month", a.month, "--tracker-from", str(a.tracker_from), "--out", payload], None))
    steps.append(("City plan and visit cities", [PY, s("build_visit_city_plan.py"), "--out", str(a.city_xlsx), "--label", a.label, "--months", *a.months, "--payload", payload], None))
    acct = [a.lulu, a.more, a.wellness]
    steps.append(("Account share (Lulu, More, Wellness, Reliance)", [PY, s("build_account_share.py"), "--lulu", str(a.lulu), "--more", str(a.more), "--wellness", str(a.wellness),
                  *(["--reliance", str(a.reliance)] if a.reliance else [])] if all(acct) else None, "no --lulu / --more / --wellness: the committed account share files are used"))
    steps.append(("Account view and Facewash plan", [PY, s("build_account_view.py"), "--payload", payload], None))
    steps.append(("Payload (with the account view)", [PY, s("build_nielsen_payload.py"), "--label", a.label, "--month", a.month, "--tracker-from", str(a.tracker_from), "--out", payload], None))
    steps.append(("Governance check", [PY, s("build_nielsen_dashboard.py"), "--data", payload, "--check-only"], None))
    steps.append(("MT dashboard card file (dashboard/nielsen.js)", [PY, s("build_nielsen_dashboard.py"), "--data", payload, "--emit-js", "dashboard/nielsen.js"], None))
    steps.append(("Market-share HTML", [PY, s("build_nielsen_dashboard.py"), "--data", payload, "--out", str(a.html), *(["--standalone"] if a.standalone else [])], None))
    steps.append(("Power BI seeds", [PY, s("build_nielsen_powerbi_seed.py"), "--label", a.label, "--month", a.month], None))
    steps.append(("Power BI QuickSetup text", [PY, s("build_quicksetup.py")], None))
    steps.append(("Store universe card", [PY, s("build_store_universe.py")], None))
    return steps


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True, help="e.g. Sep26")
    ap.add_argument("--month", required=True, help='latest month, e.g. "Sep 26"')
    ap.add_argument("--months", nargs="+", default=["Apr", "May", "Jun", "Jul", "Aug"], help="internal offtake months of this FY loaded so far")
    ap.add_argument("--tracker-from", type=Path, default=Path("data/nielsen_aug26.json"), help="previous month's payload (carries the tracker text)")
    ap.add_argument("--facewash", type=Path)
    ap.add_argument("--shampoo", type=Path)
    ap.add_argument("--store-master", type=Path)
    ap.add_argument("--lulu", type=Path)
    ap.add_argument("--more", type=Path)
    ap.add_argument("--wellness", type=Path)
    ap.add_argument("--reliance", type=Path)
    ap.add_argument("--city-xlsx", type=Path, default=ROOT / "dist" / "City_Plan.xlsx")
    ap.add_argument("--html", type=Path)
    ap.add_argument("--standalone", action="store_true", help="inline Chart.js so the HTML works when emailed")
    ap.add_argument("--dry-run", action="store_true", help="list the steps without running them")
    a = ap.parse_args()
    a.html = a.html or ROOT / "dist" / f"Nielsen_MS_{a.label}_Dashboard.html"
    a.city_xlsx.parent.mkdir(parents=True, exist_ok=True)
    a.html.parent.mkdir(parents=True, exist_ok=True)
    steps = plan(a)
    for i, (name, argv, why) in enumerate(steps, 1):
        if argv is None:
            print(f"[{i:02d}] SKIP  {name}: {why}")
            continue
        print(f"[{i:02d}] RUN   {name}")
        if a.dry_run:
            continue
        r = subprocess.run(argv, cwd=ROOT)
        if r.returncode:
            raise SystemExit(f"STOPPED at step {i} ({name}): exit {r.returncode}. Fix it and run again; earlier steps are safe to repeat.")
    print("\nDone." if not a.dry_run else "\nDry run only.")
    print(f"HTML: {a.html}\nNext: python -m pytest -q ; node tests/nielsen_ms_browser.js {a.html} <shots-dir> aug")


if __name__ == "__main__":
    main()
