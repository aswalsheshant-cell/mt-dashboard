"""Land selected data files that exist only in a PR or an unmerged branch into the canonical folders of this repo.

Why: the HTML dashboard and the Power BI model must read one home for their data (docs/DATA_HOME.md). Files that were
committed on PR branches that never merged are otherwise invisible. This copies a fixed allow-list with `git show` (no
checkout), keeps the same relative path, and writes PowerBI/Reference/PR_INPUTS_MANIFEST.csv with SHA-256, rows, the PR
or branch it came from and its status class. It never overwrites a file that already exists with different content.

What it does NOT land: restricted raw extracts (store-level offtake, SIS files, primary article extracts, store masters),
synthetic or estimated data, release packages. Those are classified in docs/evidence/INPUT_AVAILABILITY_REGISTER.md and
stay reachable through scripts/restore_branch_files.py.

Landing a file does not wire it into any query, measure or HTML block, and does not approve it: a PENDING or PROVISIONAL
status inside a file stays exactly as written.

Usage:  git fetch origin '+refs/pull/*/head:refs/remotes/pr/*' && python scripts/land_pr_inputs.py [--check]
"""
import argparse
import csv
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "PowerBI" / "Reference" / "PR_INPUTS_MANIFEST.csv"
OFFLINE = "origin/claude/offline-agent-pbi-workflow-08cz7j"
JUNE = "origin/claude/june-26-sales-data-xzbhub"

# (ref, path, destination (None = same path), source label, status class, what it is)
ALLOW = [
    # fill rate (PR 279): real aggregate, no store level
    ("pr/279", "PowerBI/SeedData/Forecast/PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv", None, "PR 279", "NEEDS_OWNER", "PO fill rate by month x chain x brand, Apr-25 to Aug-26"),
    ("pr/279", "PowerBI/SeedData/Forecast/PO_Unfilled_Reasons_Monthly_Apr25_to_Aug26.csv", None, "PR 279", "NEEDS_OWNER", "reasons for unfilled PO lines"),
    ("pr/279", "PowerBI/SeedData/Forecast/PO_vs_Target_Monthly_FY27.csv", None, "PR 279", "NEEDS_OWNER", "PO value against target, FY27"),
    ("pr/279", "PowerBI/SeedData/Forecast/PO_Fill_Rate_QC.json", None, "PR 279", "NEEDS_OWNER", "QC summary written with the fill-rate files"),
    # B3: distributor claim inputs (PR 267, rebuild of 252)
    ("pr/267", "PowerBI/SeedData/Masters/PL_Distributor_Claim_Monthly_Allocated_Q1_FY27.csv", None, "PR 267", "NEEDS_OWNER", "Q1 FY27 distributor claim allocated to months, PROVISIONAL"),
    ("pr/252", "PowerBI/SeedData/Masters/PL_Distributor_Claim_Input_Q1_FY27.csv", None, "PR 252/267", "NEEDS_OWNER", "Q1 FY27 distributor claim input (32 rows)"),
    ("pr/267", "PowerBI/SeedData/Mapping/ClaimDriver_Alias_Decisions_Q1_FY27.csv", None, "PR 267", "NEEDS_OWNER", "7 alias decisions, owner decision column still blank"),
    # CM2 decision context (B3/B4)
    ("pr/16", "PowerBI/Reference/CM2_Provisional/config/cm2_decision_register.csv", None, "PR 16", "REFERENCE_PENDING", "CM2 decision register D1-D13, mostly PENDING_APPROVAL"),
    ("pr/16", "PowerBI/Reference/CM2_Provisional/SeedData/CM2_Governance_Status.csv", None, "PR 16", "REFERENCE_PENDING", "CM2 governance status per decision"),
    ("pr/16", "PowerBI/Reference/CM2_Provisional/SeedData/CM2_Provisional_Assumptions.csv", None, "PR 16", "REFERENCE_PENDING", "Q1 FY27 COGS and logistics provisional assumptions"),
    ("pr/16", "PowerBI/Reference/CM2_Provisional/config/cm2_allocation_rules.csv", None, "PR 16", "REFERENCE_PENDING", "allocation rules ALLOC-001..003 (not yet activated)"),
    ("pr/16", "PowerBI/Reference/CM2_Provisional/config/cm2_expense_taxonomy.csv", None, "PR 16", "REFERENCE_PENDING", "CM2 expense taxonomy"),
    ("pr/16", "PowerBI/SeedData/Masters/FY27_Monthly_GMV_MRP.csv", None, "PR 16", "NEEDS_OWNER", "Jun-26 GMV/MRP control with source file hash"),
    # masters
    ("pr/16", "PowerBI/SeedData/Masters/EAN_Product_Master.csv", None, "PR 16", "SAFE_SEED", "EAN lifecycle master, 3,494 EANs"),
    (OFFLINE, "PowerBI/SeedData/Masters/NPI_List.csv", None, "offline-agent branch", "NEEDS_OWNER", "NPI list FY27 (first primary month Apr-26), 32 EANs"),
    # business input templates and trackers (placeholders, nothing approved)
    ("pr/18", "BUSINESS_INPUT_APPROVAL_TRACKER.xlsx", "PowerBI/Reference/Business_Inputs/BUSINESS_INPUT_APPROVAL_TRACKER.xlsx", "PR 18", "REFERENCE_PENDING", "approval tracker: events PENDING, targets MISSING, NPI schema only"),
    ("pr/18", "margin_repository/Pending_Business_Decisions.xlsx", "PowerBI/Reference/Business_Inputs/Pending_Business_Decisions.xlsx", "PR 18", "REFERENCE_PENDING", "12 pending business decisions (11 pending, 1 confirmed)"),
    ("pr/18", "Phase_A_Input/events_calendar.csv", "PowerBI/Reference/Business_Inputs/Phase_A_Input/events_calendar.csv", "PR 18", "TEMPLATE", "festival uplift calendar, every row PLACEHOLDER_TBC"),
    ("pr/18", "Phase_A_Input/launch_plan.csv", "PowerBI/Reference/Business_Inputs/Phase_A_Input/launch_plan.csv", "PR 18", "TEMPLATE", "NPI launch plan, header only"),
    ("pr/18", "Phase_A_Input/targets.csv", "PowerBI/Reference/Business_Inputs/Phase_A_Input/targets.csv", "PR 18", "TEMPLATE", "targets input, header only"),
    # store audit: only the template exists
    (OFFLINE, "PowerBI/templates/Template_Visibility_Tracker.csv", None, "offline-agent branch", "TEMPLATE", "visibility / store audit input template (1 example row)"),
]


def show(ref, path):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def rows_of(path, data):
    if not path.lower().endswith(".csv"):
        return ""
    lines = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
    return str(max(lines - 1, 0))


def run(check=False):
    out, problems = [], []
    for ref, path, dest, label, cls, what in ALLOW:
        data = show(ref, path)
        if data is None:
            problems.append(f"missing in {ref}: {path}")
            continue
        sha = hashlib.sha256(data).hexdigest()
        target = ROOT / (dest or path)
        rel = (dest or path)
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest() != sha:
                problems.append(f"already exists with different content, left alone: {rel}")
        elif not check:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        elif check:
            problems.append(f"not landed yet: {rel}")
        out.append([rel, label, ref, cls, sha, rows_of(path, data), what])
    if not check and not problems:
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        with open(MANIFEST, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["path", "from", "ref", "status_class", "sha256", "data_rows", "what_it_is"])
            w.writerows(sorted(out))
    return out, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only verify that every allow-listed file is landed unchanged")
    a = ap.parse_args()
    out, problems = run(a.check)
    for p in problems:
        print("PROBLEM:", p)
    print("%d files %s" % (len(out), "checked" if a.check else "landed or already present"))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
