#!/usr/bin/env python3
"""Employee-level actual attribution for the incentive cycle (KA-12).

RESTRICTED. Reads DMS store sales and the WoA store->person sheet, and credits
store actuals to employees -- but only where an owner has APPROVED the identity.
A candidate is never treated as approved. Value that cannot be credited is not
discarded; it is classified and kept in the reconciliation so the total still ties.

Scope fence: this uses DMS/Massit data, which is incentive-only. It never feeds
the commercial dashboard.

Crediting model
  Each role column in the WoA sheet (RKAM / SO Name / BA Lead / BA Supervisor) is
  a separate credit line over the same stores -- a field hierarchy, not a split of
  one pot. So actuals reconcile WITHIN a role and are never summed ACROSS roles.
  Whether a role earns full or shared credit is a business rule (crediting policy),
  not something this script decides.

Usage:
  python scripts/build_actual_attribution.py --woa <woa_sheet.csv> --massit <m1.csv> [<m2.csv> ...]
"""
from __future__ import annotations
import argparse, csv, json, re, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import build_dashboard_data as B  # noqa: E402
from build_incentive_identity import read_woa  # noqa: E402

OUT = REPO / "incentive_working"
MEASURE = "TotalTertiaryValue"          # established basis, see massit_sales_basis.json
ROLE_COLS = ("RKAM", "SO Name", "BA Lead", "BA Supervisor")
MON3 = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

csv.field_size_limit(10 ** 7)


def month_label(raw):
    """Massit month strings vary ("Apr'26", "JuL'26", "2026-04"). Derive, never index."""
    s = str(raw or "").strip()
    m = re.match(r"([A-Za-z]{3})[a-zA-Z]*['\-\s]*(\d{2,4})", s)
    if m and m.group(1).title() in MON3:
        y = int(m.group(2))
        return f"{m.group(1).title()}-{y % 100:02d}"
    m = re.match(r"(\d{4})-(\d{1,2})", s)
    if m:
        yy, mm = int(m.group(1)), int(m.group(2))
        return f"{[k for k, v in MON3.items() if v == mm][0]}-{yy % 100:02d}"
    return s or None


def read_massit(paths):
    """Store x month actual on the established measure. Returns rows and a load report."""
    rows, report = [], []
    for p in paths:
        n, bad, val = 0, 0, 0.0
        with open(p, encoding="utf-8-sig", newline="") as fh:
            rd = csv.DictReader(fh)
            keys = {k.strip(): k for k in (rd.fieldnames or [])}
            need = [MEASURE, "Client_Id", "Month", "Zone"]
            miss = [k for k in need if k not in keys]
            if miss:
                raise SystemExit(f"{Path(p).name}: missing column(s) {miss}")
            for r in rd:
                cid = (r.get(keys["Client_Id"]) or "").strip()
                try:
                    v = float(r.get(keys[MEASURE]) or 0)
                except ValueError:
                    bad += 1
                    continue
                if not cid:
                    bad += 1
                    continue
                rows.append({
                    "Client_Id": cid,
                    "Month": month_label(r.get(keys["Month"])),
                    "Zone_Raw": (r.get(keys["Zone"]) or "").strip(),
                    "Chain_Raw": (r.get(keys.get("Chain (from Client_Id)", "")) or "").strip()
                                 if "Chain (from Client_Id)" in keys else "",
                    "Client_Type": (r.get(keys["Client Type"]) or "").strip()
                                   if "Client Type" in keys else "",
                    "Value": v,
                })
                n += 1
                val += v
        report.append({"file": Path(p).name, "rows": n, "skipped": bad, "value_inr": round(val, 2)})
    return rows, report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--woa", required=True)
    ap.add_argument("--massit", nargs="+", required=True)
    ap.add_argument("--register", default="incentive_working/woa_employee_mapping_register.csv")
    ap.add_argument("--out-dir", default=str(OUT))
    a = ap.parse_args()
    outd = Path(a.out_dir)
    outd.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((REPO / "config" / "analytics_config.json").read_text())

    # ---- store -> person, from the WoA sheet -------------------------------
    woa, idx = read_woa(Path(a.woa))
    cid_key = next((k for k in idx if k.lower().replace(" ", "") == "clientid"), None)
    store_people = {}                      # client_id -> {role: (raw_name, canonical zone)}
    for r in woa:
        cid = (r.get(cid_key) or "").strip()
        if not cid:
            continue
        zc, _ = B.canon_zone_name(r.get("Zone"), cfg)
        store_people[cid] = {c: ((r.get(c) or "").strip(), zc)
                             for c in ROLE_COLS if (r.get(c) or "").strip()}

    # ---- approved identities only ------------------------------------------
    reg = list(csv.DictReader(open(REPO / a.register, encoding="utf-8")))
    approved, candidate = {}, {}
    for x in reg:
        k = (x["WoA_Role_Column"].strip(), x["WoA_Raw_Name"].strip(), x["Zone"].strip())
        if (x.get("Approved_Employee_ID") or "").strip():
            approved[k] = x["Approved_Employee_ID"].strip()
        candidate[k] = {"emp_id": (x.get("Candidate_Employee_ID") or "").strip(),
                        "name": (x.get("Candidate_Employee_Name") or "").strip(),
                        "cls": x.get("Classification", ""),
                        "status": x.get("Approval_Status", "PENDING")}

    # ---- store actuals ------------------------------------------------------
    mass, load_report = read_massit(a.massit)
    gross = defaultdict(float)             # (client_id, month) -> value
    ctype = {}
    for m in mass:
        gross[(m["Client_Id"], m["Month"])] += m["Value"]
        if m.get("Client_Type"):
            ctype[m["Client_Id"]] = m["Client_Type"]
    total_actual = sum(gross.values())

    # ---- credit, per role ---------------------------------------------------
    STATUS = {
        "OWNER_RULE_APPROVAL": "UNATTRIBUTED_PENDING_APPROVAL",
        "OWNER_ROW_EXCEPTION": "AMBIGUOUS_IDENTITY",
        "SOURCE_DATA_FIX_REQUIRED": "INVALID_SOURCE_PERSON",
        "INSUFFICIENT_EVIDENCE": "SOURCE_POPULATION_MISSING",
        "NON_MATERIAL_MONITOR": "UNATTRIBUTED_PENDING_APPROVAL",
    }
    per_role_total = defaultdict(float)
    lines = defaultdict(lambda: {"value": 0.0, "stores": set(), "months": set()})
    unmapped_store = defaultdict(float)    # stores with actuals but not in the WoA sheet
    no_person = defaultdict(float)         # in WoA but that role column is blank

    for (cid, month), val in gross.items():
        people = store_people.get(cid)
        if people is None:
            unmapped_store[month] += val
            continue
        for role in ROLE_COLS:
            per_role_total[role] += val
            if role not in people:
                no_person[(role, month)] += val
                continue
            raw, zc = people[role]
            k = (role, raw, zc or "")
            emp = approved.get(k)
            c = candidate.get(k, {})
            st = "ATTRIBUTED" if emp else STATUS.get(c.get("cls", ""), "SOURCE_POPULATION_MISSING")
            key = (role, raw, zc or "", month, emp or "", st)
            lines[key]["value"] += val
            lines[key]["stores"].add(cid)
            lines[key]["months"].add(month)

    # ---- write the attribution table ---------------------------------------
    rows = []
    for (role, raw, zc, month, emp, st), v in sorted(lines.items(), key=lambda kv: -kv[1]["value"]):
        c = candidate.get((role, raw, zc), {})
        rows.append({
            "FY": B.fy_tag_from_label(month) if month else "",
            "Month": month, "Role_Column": role, "WoA_Person": raw, "Zone": zc,
            "Approved_Employee_ID": emp,
            "Candidate_Employee_ID": "" if emp else c.get("emp_id", ""),
            "Candidate_Employee_Name": "" if emp else c.get("name", ""),
            "Store_Count": len(v["stores"]),
            "Gross_Store_Actual_INR": round(v["value"], 2),
            "Contribution_Pct": "" if not emp else "CREDITING_POLICY_REQUIRED",
            "Credited_Actual_INR": round(v["value"], 2) if emp else "",
            "Mapping_Status": st,
            "Source": f"DMS {MEASURE}",
            "Period_Status": "PARTIAL_FY",
        })
    hdr = list(rows[0]) if rows else []
    with open(outd / "employee_actual_attribution.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=hdr)
        w.writeheader()
        w.writerows(rows)

    # ---- reconciliation, per role ------------------------------------------
    recon = []
    for role in ROLE_COLS:
        b = defaultdict(float)
        for r in rows:
            if r["Role_Column"] == role:
                b[r["Mapping_Status"]] += r["Gross_Store_Actual_INR"]
        nm = sum(unmapped_store.values())
        npv = sum(v for (rl, _), v in no_person.items() if rl == role)
        acc = sum(b.values()) + npv + nm
        recon.append({
            "Role": role,
            "Total_Store_Actual_INR": round(total_actual, 2),
            "Attributed_INR": round(b.get("ATTRIBUTED", 0.0), 2),
            "Pending_Approval_INR": round(b.get("UNATTRIBUTED_PENDING_APPROVAL", 0.0), 2),
            "Ambiguous_INR": round(b.get("AMBIGUOUS_IDENTITY", 0.0), 2),
            "Invalid_Source_Person_INR": round(b.get("INVALID_SOURCE_PERSON", 0.0), 2),
            "Missing_Population_INR": round(b.get("SOURCE_POPULATION_MISSING", 0.0), 2),
            "Role_Not_Staffed_INR": round(npv, 2),
            "Store_Not_In_WoA_INR": round(nm, 2),
            "Reconciliation_Difference_INR": round(total_actual - acc, 2),
            "Reconciles": "YES" if abs(total_actual - acc) < 1.0 else "NO",
        })
    with open(outd / "actual_attribution_reconciliation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(recon[0]))
        w.writeheader()
        w.writerows(recon)

    # ---- what each pending signature is worth ------------------------------
    worth = defaultdict(lambda: {"value": 0.0, "stores": 0, "cand": "", "name": "", "cls": ""})
    for r in rows:
        if r["Mapping_Status"] == "UNATTRIBUTED_PENDING_APPROVAL":
            k = (r["Role_Column"], r["WoA_Person"], r["Zone"])
            worth[k]["value"] += r["Gross_Store_Actual_INR"]
            worth[k]["stores"] = max(worth[k]["stores"], r["Store_Count"])
            worth[k]["cand"] = r["Candidate_Employee_ID"]
            worth[k]["name"] = r["Candidate_Employee_Name"]
            worth[k]["cls"] = candidate.get(k, {}).get("cls", "")
    with open(outd / "woa_approval_value_at_stake.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Role_Column", "WoA_Person", "Zone", "Stores", "Candidate_Employee_ID",
                    "Candidate_Employee_Name", "Classification", "Actual_At_Stake_INR",
                    "Actual_At_Stake_L", "Owner", "Approval_Status"])
        for (role, raw, zc), v in sorted(worth.items(), key=lambda kv: -kv[1]["value"]):
            w.writerow([role, raw, zc, v["stores"], v["cand"], v["name"], v["cls"],
                        round(v["value"], 2), round(v["value"] / 100000, 2), "MT Ops", "PENDING"])

    # Stores carrying actuals that the WoA sheet does not cover at all. Naming the
    # population matters: a chain with no beauty-advisor deployment has no WoA row by
    # design, which is a scope question, not a mapping failure.
    outside = defaultdict(lambda: {"value": 0.0, "stores": set()})
    for (cid, _m), v in gross.items():
        if cid not in store_people:
            k = ctype.get(cid) or "(no client type)"
            outside[k]["value"] += v
            outside[k]["stores"].add(cid)
    with open(outd / "actuals_outside_woa_coverage.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Client_Type", "Stores", "Actual_INR", "Actual_L", "Share_Of_Total_Pct",
                    "Interpretation_Required"])
        for k, v in sorted(outside.items(), key=lambda kv: -kv[1]["value"]):
            w.writerow([k, len(v["stores"]), round(v["value"], 2), round(v["value"] / 1e5, 2),
                        round(v["value"] / total_actual * 100, 2) if total_actual else 0,
                        "Is this population inside the incentive measurement scope?"])

    summary = {
        "generated": date.today().isoformat(),
        "measure": MEASURE,
        "files": load_report,
        "months": sorted({m for _, m in gross}),
        "total_store_actual_inr": round(total_actual, 2),
        "total_store_actual_L": round(total_actual / 100000, 2),
        "stores_with_actuals": len({c for c, _ in gross}),
        "stores_in_woa": len(store_people),
        "stores_with_actuals_not_in_woa": len({c for c, _ in gross} - set(store_people)),
        "approved_identities": len(approved),
        "pending_signatures": len(worth),
        "value_awaiting_signature_by_role_inr": {
            role: round(sum(v["value"] for k, v in worth.items() if k[0] == role), 2)
            for role in ROLE_COLS},
        "_cross_role_sum_is_not_a_total": "Each role credits the same store actual once, so "
                                          "role figures must never be added together.",
        "actuals_outside_woa_coverage": {
            k: {"stores": len(v["stores"]), "actual_L": round(v["value"] / 1e5, 2)}
            for k, v in sorted(outside.items(), key=lambda kv: -kv[1]["value"])},
        "per_role_reconciliation": recon,
        "scope": "INCENTIVE_ONLY — never merged into commercial reporting",
    }
    (outd / "actual_attribution_summary.json").write_text(json.dumps(summary, indent=2))

    print(f"store actuals {total_actual / 1e5:,.2f} L over {len(summary['months'])} month(s) "
          f"{summary['months']}")
    print(f"  stores with actuals {summary['stores_with_actuals']} | in WoA {summary['stores_in_woa']} "
          f"| not in WoA {summary['stores_with_actuals_not_in_woa']}")
    print(f"  approved identities {len(approved)} -> attributed "
          f"{sum(r['Attributed_INR'] for r in recon) / 1e5:,.2f} L")
    print(f"  {len(worth)} signatures pending; value at stake per role (never added across roles):")
    for role in ROLE_COLS:
        rv = sum(v["value"] for k, v in worth.items() if k[0] == role)
        print(f"      {role:14s} {rv / 1e5:>10,.2f} L")
    print("  actuals in stores outside WoA coverage:")
    for k, v in sorted(outside.items(), key=lambda kv: -kv[1]["value"]):
        print(f"      {k:22s} {v['value'] / 1e5:>10,.2f} L over {len(v['stores'])} store(s)")
    for r in recon:
        print(f"  {r['Role']:14s} reconciles={r['Reconciles']} diff={r['Reconciliation_Difference_INR']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
