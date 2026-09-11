#!/usr/bin/env python3
"""Incentive identity foundation: WoA person -> Employee ID candidates + input templates.

RESTRICTED OUTPUT. Everything this writes carries employee identity, so it all
goes to incentive_working/ (gitignored). Nothing reaches dashboard/.

What this does NOT do
---------------------
It never assigns an employee identity. Name matching proposes; a named owner
approves. Every register row leaves Approved_Employee_ID blank and
Approval_Status = PENDING, and a blank stays blank -- silence is not evidence.
Fuzzy similarity is never used to auto-approve an identity: paying the wrong
person is worse than leaving a row open.

Classification follows the six approval-register types:
  OWNER_RULE_APPROVAL     one consistent candidate, zone agrees -> one-line ask
  OWNER_ROW_EXCEPTION     several people match, or the zone disagrees
  INSUFFICIENT_EVIDENCE   no candidate exists in the employee master
  SOURCE_DATA_FIX_REQUIRED the source value is a placeholder, not a person
  NON_MATERIAL_MONITOR    real but tiny; tracked, not blocking
  AUTO_GOVERNABLE         only from a prior approved policy, never first-time

Usage:
  python scripts/build_incentive_identity.py --woa <woa.csv> --employees <master.csv>
                                             [--out incentive_working] [--dry-run]
"""
from __future__ import annotations
import argparse, csv, importlib.util, json, re, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# Values that look like a person but are not one.
PLACEHOLDERS = re.compile(r"^\s*(vacant|tbd|na|n/?a|open|blank|-+)\b", re.I)
# Grades the slab master defines. Nothing outside this list may be entered.
GRADE_OPTIONS = {
    "RKAM": ["Asst RKAM", "RKAM", "Sr RKAM"],
    "NKAM": ["Asst NKAM", "NKAM", "Sr NKAM"],
    "BA_Leads": ["BA Lead - Sr Exec", "BA Lead - Asst Mgr"],
    "BDO_BDE": ["BDO", "BDE", "Sr BDE"],
    "BA_Ops": ["Sr National BA Ops"],
    "Analyst": ["Analyst"],
}
# Role groups whose designation in the employee master already equals a slab
# grade. The rest need the grade supplied.
GRADE_SELF_EVIDENT = {"BDO_BDE", "Analyst", "BA_Ops"}


def load_builder():
    spec = importlib.util.spec_from_file_location("bdd", REPO / "scripts" / "build_dashboard_data.py")
    m = importlib.util.module_from_spec(spec); sys.modules["bdd"] = m
    spec.loader.exec_module(m); return m


def norm_name(s):
    return re.sub(r"\s+", " ", str(s or "").strip()).lower()


def read_employees(path: Path):
    raw = list(csv.reader(open(path, encoding="utf-8-sig")))
    hi = next((i for i, r in enumerate(raw[:12]) if "Employee ID" in [c.strip() for c in r]), None)
    if hi is None:
        raise SystemExit(f"{path}: no 'Employee ID' header row found")
    hdr = [c.strip() for c in raw[hi]]
    out = []
    for r in raw[hi + 1:]:
        if not r or not r[0].strip():
            continue
        d = dict(zip(hdr, [c.strip() for c in r]))
        d["_title"] = r[13].strip() if len(r) > 13 else ""
        out.append(d)
    return out


def read_woa(path: Path):
    raw = list(csv.reader(open(path, encoding="utf-8-sig")))
    hi = next((i for i, r in enumerate(raw[:12]) if "Client Id" in [c.strip() for c in r]), None)
    if hi is None:
        raise SystemExit(f"{path}: no 'Client Id' header row found")
    idx = {c.strip(): i for i, c in enumerate(raw[hi]) if c.strip()}
    rows = []
    for r in raw[hi + 1:]:
        sn = idx.get("S.No")
        if sn is None or len(r) <= sn or not r[sn].strip().isdigit():
            continue
        rows.append({k: (r[i].strip() if i < len(r) else "") for k, i in idx.items()})
    return rows, idx


def match(raw_name, zone_c, emp_by_norm, emp_by_first, cfg, b):
    """Candidates for one WoA person value. Proposes only."""
    n = norm_name(raw_name)
    if not n:
        return [], "NO_MATCH"
    if PLACEHOLDERS.match(raw_name):
        return [], "PLACEHOLDER"
    exact = emp_by_norm.get(n, [])
    if exact:
        zoned = [e for e in exact if b.canon_zone_name(e.get("Region/Zone"), cfg)[0] == zone_c]
        if len(zoned) == 1:
            return zoned, "EXACT_NAME_AND_ZONE"
        if len(exact) == 1:
            return exact, "EXACT_NAME"
        return exact, "AMBIGUOUS"
    # First token only (WoA carries first names). A candidate, never an answer.
    first = emp_by_first.get(n.split(" ")[0], [])
    if not first:
        return [], "NO_MATCH"
    zoned = [e for e in first if b.canon_zone_name(e.get("Region/Zone"), cfg)[0] == zone_c]
    if len(zoned) == 1:
        return zoned, "NORMALIZED_NAME_AND_ZONE"
    if len(first) == 1:
        return first, "UNIQUE_CANDIDATE"
    return first, "AMBIGUOUS"


def classify(method, cands, stores, floor):
    if method == "PLACEHOLDER":
        return "SOURCE_DATA_FIX_REQUIRED", "Source value is a placeholder, not a person. A corrected WoA extract is needed."
    if method == "NO_MATCH":
        return "INSUFFICIENT_EVIDENCE", "No employee in the master matches this name. Supply the Employee ID, or the person is not in the master."
    if method == "AMBIGUOUS":
        names = ", ".join(sorted({c["Employee Name"] for c in cands}))
        return "OWNER_ROW_EXCEPTION", f"{len(cands)} employees match this name ({names}). Only the business can say which."
    if stores < floor:
        return "NON_MATERIAL_MONITOR", f"Single candidate, but only {stores} store(s) — below the {floor}-store materiality floor. Tracked, not blocking."
    return "OWNER_RULE_APPROVAL", f"One consistent candidate via {method}, covering {stores} store(s). Confirm or correct the Employee ID."


def w(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=header)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in header})
    return len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--woa", required=True)
    ap.add_argument("--employees", required=True)
    ap.add_argument("--out", default="incentive_working")
    ap.add_argument("--materiality-floor", type=int, default=3,
                    help="Stores below which a single-candidate row is monitored, not asked.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    b = load_builder()
    cfg = b.load_analytics_config(REPO)
    outd = REPO / a.out if not Path(a.out).is_absolute() else Path(a.out)
    rel = outd.resolve().relative_to(REPO.resolve()).parts if str(outd.resolve()).startswith(str(REPO.resolve())) else ()
    if rel and rel[0] == "dashboard":
        print("REFUSING: identity output must not enter the published dashboard."); return 2

    emps = read_employees(Path(a.employees))
    woa, idx = read_woa(Path(a.woa))
    emp_by_norm, emp_by_first = defaultdict(list), defaultdict(list)
    for e in emps:
        n = norm_name(e.get("Employee Name"))
        if n:
            emp_by_norm[n].append(e)
            emp_by_first[n.split(" ")[0]].append(e)

    # ---- 1. WoA person -> Employee ID candidate register --------------------
    # read_woa() strips header keys, so look them up stripped. "SO Name " carries
    # a trailing space in the source; matching it unstripped silently dropped the
    # whole SO column -- the largest population in the register.
    person_cols = [c for c in ("RKAM", "SO Name", "BA Lead", "BA Supervisor") if c in idx]
    if "SO Name" not in idx:
        print("WARNING: no 'SO Name' column found in the WoA sheet — "
              f"available person-like columns: {[k for k in idx if 'name' in k.lower()]}")
    agg = {}
    for r in woa:
        zc, _ = b.canon_zone_name(r.get("Zone"), cfg)
        for col in person_cols:
            v = (r.get(col) or "").strip()
            if not v:
                continue
            k = (col.strip(), v, zc)
            a_ = agg.setdefault(k, {"stores": 0})
            a_["stores"] += 1

    reg, counts = [], defaultdict(int)
    for (col, raw, zone_c), meta in sorted(agg.items(), key=lambda kv: -kv[1]["stores"]):
        cands, method = match(raw, zone_c, emp_by_norm, emp_by_first, cfg, b)
        cls, why = classify(method, cands, meta["stores"], a.materiality_floor)
        counts[cls] += 1
        c0 = cands[0] if len(cands) == 1 else None
        reg.append({
            "WoA_Role_Column": col, "WoA_Raw_Name": raw, "Zone": zone_c or "",
            "Stores_Assigned": meta["stores"],
            "Candidate_Employee_Name": c0["Employee Name"] if c0 else
                ("; ".join(sorted({c['Employee Name'] for c in cands})) if cands else ""),
            "Candidate_Employee_ID": c0["Employee ID"] if c0 else "",
            "Candidate_Designation": c0["Designation"] if c0 else "",
            "Candidate_Zone": (b.canon_zone_name(c0.get("Region/Zone"), cfg)[0] if c0 else ""),
            "Candidate_Count": len(cands),
            "Match_Method": method,
            "Ambiguity_Flag": "YES" if method == "AMBIGUOUS" else "NO",
            "Classification": cls,
            "Why": why,
            # Owner fields — never populated here.
            "Approved_Employee_ID": "", "Approval_Status": "PENDING",
            "Approved_By": "", "Approval_Date": "", "Notes": "",
        })
    n1 = 0 if a.dry_run else w(outd / "woa_employee_mapping_register.csv", list(reg[0].keys()), reg) if reg else 0

    # ---- 2. Incentive grade request ----------------------------------------
    grade_rows = []
    for e in emps:
        rg = (e.get("Role Group") or "").strip()
        if rg in GRADE_SELF_EVIDENT:
            continue                      # designation already equals a slab grade
        opts = GRADE_OPTIONS.get(rg or (e.get("Designation") or "").strip(), [])
        if not opts:
            continue
        grade_rows.append({
            "Employee_ID": e["Employee ID"], "Employee_Name": e["Employee Name"],
            "Role_Group": rg, "Current_Designation": e.get("Designation", ""),
            "Current_Title": e.get("_title", ""),
            "Zone_or_Scope": b.canon_zone_name(e.get("Region/Zone"), cfg)[0] or e.get("Region/Zone", ""),
            "Required_Incentive_Grade": "", "Allowed_Values": " | ".join(opts),
            "Confirmed_By": "", "Confirmation_Date": "", "Notes": "",
        })
    n2 = 0 if a.dry_run else w(outd / "incentive_grade_request.csv", list(grade_rows[0].keys()), grade_rows) if grade_rows else 0

    # ---- 3. Role measurement scope -----------------------------------------
    BC = "BUSINESS_CONFIRMATION_REQUIRED"
    scope = [
        dict(Role_Group="BDO_BDE", Designation_or_Grade="BDO / BDE / Sr BDE", Measurement_Level=BC,
             Actual_Metric="Primary Sales", Target_Level=BC, Frequency="Monthly",
             Brand_Scope="All", Additional_Parameter="Any 1 Focus Pack WoA L3M avg (Quarterly)",
             Rule_Status=BC, Confirmed_By=""),
        dict(Role_Group="RKAM", Designation_or_Grade="Asst / RKAM / Sr RKAM", Measurement_Level="Zone",
             Actual_Metric="Primary Sales", Target_Level=BC, Frequency="Quarterly",
             Brand_Scope="Overall + Emerging (all brands except Mamaearth)",
             Additional_Parameter="Annual kicker at 120%+", Rule_Status=BC, Confirmed_By=""),
        dict(Role_Group="NKAM", Designation_or_Grade="Asst / NKAM / Sr NKAM", Measurement_Level="Account",
             Actual_Metric="Primary Sales", Target_Level=BC, Frequency="Quarterly",
             Brand_Scope="Overall + Emerging (all brands except Mamaearth)",
             Additional_Parameter="Annual kicker at 120%+", Rule_Status=BC, Confirmed_By=""),
        dict(Role_Group="BA_Ops", Designation_or_Grade="Sr National BA Ops", Measurement_Level=BC,
             Actual_Metric="MT manned stores offtake L3M avg", Target_Level=BC, Frequency="Quarterly",
             Brand_Scope="All", Additional_Parameter="Focus Pack WoA; BA & Promoter attrition",
             Rule_Status=BC, Confirmed_By=""),
        dict(Role_Group="BA_Leads", Designation_or_Grade="Sr Exec / Asst Mgr", Measurement_Level=BC,
             Actual_Metric="GT Secondary; MT outlets above 2 lakhs MRP L3M avg", Target_Level=BC,
             Frequency="Monthly", Brand_Scope="All", Additional_Parameter="BA attrition LM",
             Rule_Status=BC, Confirmed_By=""),
        dict(Role_Group="Analyst", Designation_or_Grade="Analyst", Measurement_Level=BC,
             Actual_Metric="Primary Sales", Target_Level=BC, Frequency="Quarterly",
             Brand_Scope="Overall + Emerging (all brands except Mamaearth)",
             Additional_Parameter="Floor is 100%, not 90%", Rule_Status=BC, Confirmed_By=""),
    ]
    n3 = 0 if a.dry_run else w(outd / "role_measurement_scope.csv", list(scope[0].keys()), scope)

    # ---- 4. Target request template (empty by design) -----------------------
    thdr = ["FY", "Month_or_Quarter", "Target_Basis", "Measurement_Level", "Zone", "Account",
            "Chain", "Territory", "Employee_ID_if_applicable", "Brand", "Target_Value",
            "Target_Unit", "Approved_By", "Approval_Date", "Source_File", "Version"]
    n4 = 0 if a.dry_run else w(outd / "target_request_template.csv", thdr, [])

    # ---- 5. Decision register: target basis + C1-C6 + caps ------------------
    dec = [
        dict(Decision_ID="D1", Question="Is the incentive target set on Primary billing or Offtake?",
             Current_Status="ASSUMED", Current_Assumption="Offtake (matches the existing forecast convention)",
             Business_Impact="Apr-Jul achievement 89.0% on offtake vs 109.8% on primary",
             Affected_Roles="All", Decision_Owner="MT Leadership / Finance"),
        dict(Decision_ID="C1", Question="RKAM Overall vs Emerging weighting is the mirror of NKAM's. Intended?",
             Current_Status="CONFLICT", Current_Assumption="None — both sources agree, but the RKAM narrative contradicts its own table",
             Business_Impact="Changes RKAM payout whenever the two parameters land in different slabs",
             Affected_Roles="RKAM (6)", Decision_Owner="MT Leadership"),
        dict(Decision_ID="C2", Question="BDE/BDO quarterly top-up: Q1 only, or all four quarters?",
             Current_Status="CONFLICT", Current_Assumption="None — the table annualises 4 quarters, the text says Q1 only",
             Business_Impact="Rs 7,200-15,300 per person per year",
             Affected_Roles="BDO_BDE (35)", Decision_Owner="MT Leadership / Finance"),
        dict(Decision_ID="C3", Question="BA Ops attrition Below 5%: is the payout Rs 15,250 or 120% of Rs 10,000 (Rs 12,000)?",
             Current_Status="CONFLICT", Current_Assumption="None — Max total agrees with 15,250, so the % label looks wrong",
             Business_Impact="Rs 3,250 per qualifying quarter", Affected_Roles="BA_Ops (1)",
             Decision_Owner="Finance"),
        dict(Decision_ID="C4", Question="BA Lead attrition Below 5%: amounts imply 150%/133%, not the stated 120%.",
             Current_Status="CONFLICT", Current_Assumption="None — Max totals agree with the amounts",
             Business_Impact="Rs 300-500 per qualifying month", Affected_Roles="BA_Leads (3)",
             Decision_Owner="Finance"),
        dict(Decision_ID="C5", Question="BDE Focus Pack jumps Rs 2,400 -> Rs 10,000 between slabs (4.2x). Intended cliff?",
             Current_Status="CONFLICT", Current_Assumption="None — every other step is 1.2x",
             Business_Impact="Rs 7,600 per person per qualifying quarter", Affected_Roles="BDO_BDE (35)",
             Decision_Owner="MT Leadership"),
        dict(Decision_ID="C6", Question="Analyst floor is 100%, not the 90% used by every other role. Intended?",
             Current_Status="CONFLICT", Current_Assumption="None", Business_Impact="No payout between 90-100%",
             Affected_Roles="Analyst (1)", Decision_Owner="MT Leadership"),
        dict(Decision_ID="D2", Question="Are the Max Quarter / Max Annual caps in the letter binding? They are not in the slab sheet.",
             Current_Status="MISSING", Current_Assumption="None", Business_Impact="Uncapped payout above the stated maximum",
             Affected_Roles="All", Decision_Owner="Finance"),
        dict(Decision_ID="D3", Question="For nested lower-is-better slabs (attrition below 10% and below 5% both qualify), take the highest qualifying slab?",
             Current_Status="MISSING", Current_Assumption="None — a first-match implementation would underpay",
             Business_Impact="Underpayment risk on every attrition parameter",
             Affected_Roles="BA_Ops, BA_Leads", Decision_Owner="Finance"),
        dict(Decision_ID="D4", Question="Proration rule for joiners and leavers mid-period?",
             Current_Status="MISSING", Current_Assumption="None",
             Business_Impact="11 employees joined during FY27; 1 exits 31-Aug-26",
             Affected_Roles="All", Decision_Owner="HR / Finance"),
        dict(Decision_ID="D5", Question="Which FY does the revised structure apply from?",
             Current_Status="MISSING", Current_Assumption="FY27 assumed from project context; the letter does not say",
             Business_Impact="Determines the whole calculation window", Affected_Roles="All",
             Decision_Owner="MT Leadership / HR"),
    ]
    for d in dec:
        d.update(Decision="", Effective_From="", Confirmed_By="", Confirmation_Date="", Version="")
    n5 = 0 if a.dry_run else w(outd / "incentive_decision_register.csv", list(dec[0].keys()), dec)

    # ---- 6. Readiness ------------------------------------------------------
    basis_ok = bool((cfg.get("target") or {}).get("basis_confirmed_by"))
    by_role = {}
    for rg in sorted({(e.get("Role Group") or "").strip() or "(blank)" for e in emps}):
        members = [e for e in emps if (e.get("Role Group") or "").strip() == rg]
        by_role[rg] = {
            "employees": len(members),
            "employee_id": "READY",
            "incentive_grade": "READY" if rg in GRADE_SELF_EVIDENT else "MISSING",
            "woa_store_mapping": "PARTIAL",
            "actual_data": "PARTIAL",
            "target_data": "MISSING",
            "target_basis": "READY" if basis_ok else "BUSINESS_CONFIRMATION_REQUIRED",
            "slab": "READY",
            "emerging_brand_rule": "READY",
            "rules_C1_C6": "BUSINESS_CONFIRMATION_REQUIRED",
            "proration": "BUSINESS_CONFIRMATION_REQUIRED",
            "cap": "BUSINESS_CONFIRMATION_REQUIRED",
            "calculation_ready": "BLOCKED",
        }
    basis = {}
    bp = outd / "massit_sales_basis.json"
    if bp.exists():
        basis = json.loads(bp.read_text(encoding="utf-8"))
    by_month = {}
    for m in ["Apr-26", "May-26", "Jun-26", "Jul-26"]:
        mm = (basis.get("by_month") or {}).get(m)
        by_month[m] = {
            "massit_available": bool(mm),
            "store_hierarchy_coverage_pct": (mm or {}).get("hierarchy_coverage_pct") if mm else None,
            "employee_id_coverage": "PENDING_APPROVAL",
            "employee_grade_coverage": "MISSING",
            "target_available": "MISSING",
            "rule_ready": False,
            "calculation_ready": "BLOCKED" if mm else "NO_DATA",
        }
    readiness = {
        "scope": "INCENTIVE_ONLY",
        "generated_from": {"woa_rows": len(woa), "employees": len(emps)},
        "register_classification_counts": dict(counts),
        "by_role": by_role, "by_month": by_month,
        "note": ("Nothing here is a payout. A role or month shows BLOCKED until every "
                 "mandatory input is present; BLOCKED and zero are different statements."),
    }
    n6 = 0
    if not a.dry_run:
        (outd / "incentive_readiness.json").write_text(
            json.dumps(readiness, ensure_ascii=False, indent=1), encoding="utf-8")
        n6 = 1

    print(f"WoA rows {len(woa)} | employees {len(emps)} | unique WoA person-values {len(agg)}")
    print("\nregister classification:")
    for k, v in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {k:26s} {v}")
    print(f"\nwritten to {outd}/ (restricted, gitignored):")
    for f, n in [("woa_employee_mapping_register.csv", n1), ("incentive_grade_request.csv", n2),
                 ("role_measurement_scope.csv", n3), ("target_request_template.csv", n4),
                 ("incentive_decision_register.csv", n5), ("incentive_readiness.json", n6)]:
        print(f"  {f:38s} {n} row(s)")
    if a.dry_run:
        print("\n(--dry-run: nothing written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
