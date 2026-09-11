#!/usr/bin/env python3
"""Build MT_Incentive_Working_FY27.xlsx -- the governed incentive working model.

RESTRICTED OUTPUT. Carries employee identity and incentive rates, so it is written
to incentive_working/ (gitignored) and never under dashboard/.

Design follows docs/knowledge/KA-09 (Excel engineering), KA-02 (auditability),
KA-03 (target scope) and KA-10 (privacy boundary):

  * every sheet is a real Excel Table with structured references
  * every calculated cell is a formula -- no typed-over results
  * a row missing a mandatory input stays BLOCKED and shows no amount.
    BLOCKED and zero are different business statements (KA-02).
  * no final payout is produced while any mandatory decision is open

Usage:
  python scripts/build_incentive_workbook.py --employees <grades.xlsx> --slabs <slab.xlsx>
      --targets <targets.xlsx> [--woa-register incentive_working/woa_employee_mapping_register.csv]
      [--out incentive_working/MT_Incentive_Working_FY27.xlsx]
"""
from __future__ import annotations
import argparse, csv, json, re, sys
from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

REPO = Path(__file__).resolve().parent.parent
FY = "FY27"
MONTHS = ["Apr-26", "May-26", "Jun-26", "Jul-26"]
_MON3 = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(color="FFFFFF", bold=True)


def sheet(wb, name, headers, rows, table_name, widths=None, note=None):
    """One sheet, one Excel Table. Structured references need a real table."""
    ws = wb.create_sheet(name)
    r0 = 1
    if note:
        ws.cell(1, 1, note).font = Font(italic=True, color="555555")
        ws.cell(1, 1).alignment = Alignment(wrap_text=False)
        r0 = 3
    for c, h in enumerate(headers, 1):
        cell = ws.cell(r0, c, h)
        cell.fill, cell.font = HDR_FILL, HDR_FONT
    for i, row in enumerate(rows, 1):
        for c, v in enumerate(row, 1):
            ws.cell(r0 + i, c, v)
    n = max(len(rows), 1)
    ref = f"A{r0}:{get_column_letter(len(headers))}{r0 + n}"
    t = Table(displayName=table_name, ref=ref)
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(t)
    for c, h in enumerate(headers, 1):
        ws.column_dimensions[get_column_letter(c)].width = (widths or {}).get(h, max(12, min(34, len(h) + 4)))
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    return ws


def _num(v):
    """CSV reads everything as text. A blank must stay blank, not become 0 (KA-02)."""
    if v is None or str(v).strip() == "":
        return ""
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return v


def read_employees(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows[:12]) if r and any(str(c).strip() == "Employee ID" for c in r if c))
    hdr = [("" if c is None else str(c).strip()) for c in rows[hi]]
    gi = ws.max_column - 1
    out = []
    for r in rows[hi + 1:]:
        if not r or not r[0]:
            continue
        d = {hdr[i]: ("" if c is None else str(c).strip()) for i, c in enumerate(r) if i < len(hdr) and hdr[i]}
        d["_grade"] = "" if gi >= len(r) or r[gi] is None else str(r[gi]).strip()
        out.append(d)
    return out


def read_slabs(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows[:10]) if r and any(str(c).strip() == "Designation" for c in r if c))
    hdr = [("" if c is None else str(c).strip()) for c in rows[hi]]
    out = []
    for r in rows[hi + 1:]:
        if not r or not r[0]:
            continue
        out.append({hdr[i]: ("" if c is None else str(c).strip()) for i, c in enumerate(r) if i < len(hdr) and hdr[i]})
    return out


def read_targets(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = next((wb[n] for n in wb.sheetnames if "TARGET MASTER" in n.upper()), wb[wb.sheetnames[0]])
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows[:15]) if r and any(str(c).strip().upper() == "TARGET" for c in r if c))
    hdr = [("" if c is None else str(c).strip()) for c in rows[hi]]
    ix = {h: i for i, h in enumerate(hdr) if h}
    out = []
    for r in rows[hi + 1:]:
        if not r or not r[0]:
            continue
        g = lambda k: ("" if ix.get(k) is None or ix[k] >= len(r) or r[ix[k]] is None else str(r[ix[k]]).strip())
        try:
            val = float(r[ix["Target"]] or 0)
        except (TypeError, ValueError):
            val = 0.0
        m = r[ix["Month"]] if ix.get("Month") is not None and ix["Month"] < len(r) else None
        mlab = f"{_MON3[m.month - 1]}-{m.year % 100:02d}" if hasattr(m, "month") else str(m or "").strip()[:10]
        out.append({"FY": g("FY"), "Month": mlab, "Region": g("Region"), "State": g("State"),
                    "Chain": g("Chain"), "Brand": g("Brand"), "BDO_BDE": g("BDO/BDE"),
                    "RKAM": g("RKAM"), "Target": val})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--employees", required=True)
    ap.add_argument("--slabs", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--woa-register", default="incentive_working/woa_employee_mapping_register.csv")
    ap.add_argument("--attribution", default="incentive_working/employee_actual_attribution.csv")
    ap.add_argument("--scope-diagnostic", default="incentive_working/target_scope_diagnostic.json")
    ap.add_argument("--at-stake", default="incentive_working/woa_approval_value_at_stake.csv")
    ap.add_argument("--out", default="incentive_working/MT_Incentive_Working_FY27.xlsx")
    a = ap.parse_args()

    outp = REPO / a.out if not Path(a.out).is_absolute() else Path(a.out)
    rel = outp.resolve().relative_to(REPO.resolve()).parts if str(outp.resolve()).startswith(str(REPO.resolve())) else ()
    if rel and rel[0] == "dashboard":
        print("REFUSING: the incentive workbook must not be written into the published dashboard.")
        return 2

    emps = read_employees(Path(a.employees))
    slabs = read_slabs(Path(a.slabs))
    tgts = read_targets(Path(a.targets))
    slab_desig = {s["Designation"] for s in slabs}
    def load_csv(rel):
        f = REPO / rel
        return list(csv.DictReader(open(f, encoding="utf-8"))) if f.exists() else []

    woa = load_csv(a.woa_register)
    attrib = load_csv(a.attribution)
    at_stake = {(r["Role_Column"], r["WoA_Person"], r["Zone"]): r for r in load_csv(a.at_stake)}
    sp = REPO / a.scope_diagnostic
    scope = json.loads(sp.read_text()) if sp.exists() else {}

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # ---- 00_Control ----------------------------------------------------------
    tgt_total = sum(t["Target"] for t in tgts)
    biz_target = 44132.86
    gapd = (scope.get("gap_decomposition") or {})
    _mo = {m: i for i, m in enumerate(
        ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"])}
    attr_months = sorted({r["Month"] for r in attrib if r.get("Month")},
                         key=lambda m: (int(m.split("-")[1]) if "-" in m else 0,
                                        _mo.get(m.split("-")[0], 99)))
    approved_ids = {r["Approved_Employee_ID"] for r in attrib if r.get("Approved_Employee_ID")}
    ctrl = [
        ["Reporting FY", FY, "From the target file"],
        ["Reporting months", ", ".join(attr_months or MONTHS), "Months with actuals available"],
        ["Refresh timestamp", date.today().isoformat(), "Date this workbook was generated"],
        ["Target basis", "ASSUMED: Offtake", "BLOCKED — Primary vs Offtake not confirmed (D1)"],
        ["Target file total (Rs L)", round(tgt_total, 2), "Sum of the target master"],
        ["Business target (Rs L)", biz_target, "FY27 total-business target"],
        ["Target coverage %", round(tgt_total / biz_target * 100, 2), "Target file as a share of business target"],
        ["Target scope gap (Rs L)", round(biz_target - tgt_total, 2), "Business target less target file"],
        ["Gap explained (Rs L)", gapd.get("explained_indicative_L", "–"),
         "Traced to named causes — see 13_Target_Scope"],
        ["Gap unexplained (Rs L)", gapd.get("unexplained_L", "–"),
         "No region, account, brand or period accounts for it"],
        ["Target_Scope_Status", "UNKNOWN_SCOPE", "KA-11 — must be confirmed before payout use"],
        ["Approved WoA identities", len(approved_ids), "Employees who may receive credited actual"],
        ["Actual rows loaded", len(attrib), "From the attribution layer (KA-12)"],
        ["Rule version", "PENDING", "Set once C1-C6, caps and proration are closed"],
        ["Calculation status", "BLOCKED", "Mandatory decisions still open"],
        ["Privacy class", "RESTRICTED_HR_FINANCE", "Never publish to dashboard/ (KA-10)"],
    ]
    sheet(wb, "00_Control", ["Item", "Value", "Note"], ctrl, "tblControl",
          {"Item": 28, "Value": 34, "Note": 62},
          note="Control sheet. Every downstream sheet reads its period and status from here.")

    # ---- 01_Employee_Master --------------------------------------------------
    erows = []
    for e in emps:
        g = e["_grade"]
        st = ("VALID" if g in slab_desig else
              "SOURCE_DATA_FIX_REQUIRED" if g.upper().startswith("#") else
              "MISSING" if not g else "INVALID")
        erows.append([e.get("Employee ID", ""), e.get("Employee Name", ""), e.get("Role Group", ""),
                      e.get("Designation", ""), g, st, e.get("Region/Zone", ""),
                      e.get("Active?", ""), e.get("Joining Date", ""), e.get("Last Working Date", ""),
                      e.get("Quarter Eligibility", ""), e.get("Annual Eligibility", "")])
    sheet(wb, "01_Employee_Master",
          ["Employee_ID", "Employee_Name", "Role_Group", "Designation", "Incentive_Grade",
           "Grade_Status", "Zone", "Active", "Date_Of_Joining", "Last_Working_Date",
           "Quarter_Eligible", "Annual_Eligible"], erows, "tblEmployee",
          note="Grade_Status is derived from the slab master. Only VALID rows can be paid.")

    # ---- 02_Incentive_Criteria ----------------------------------------------
    srows = [[s.get("Role Group", ""), s.get("Designation", ""), s.get("Frequency", ""),
              s.get("Metric", ""), s.get("Slab Name", ""), s.get("Min Ach %", ""),
              s.get("Max Ach %", ""), s.get("Amount %", ""), s.get("Payout Amount", ""),
              s.get("Condition Type", "")] for s in slabs]
    sheet(wb, "02_Incentive_Criteria",
          ["Role_Group", "Designation", "Frequency", "Metric", "Slab_Name", "Min_Ach_Pct",
           "Max_Ach_Pct", "Amount_Pct", "Payout_Amount", "Condition_Type"], srows, "tblSlab",
          note="Slab master, reconciled 85/85 against the incentive communication. Rates only — no formulas here.")

    # ---- 03_Targets ----------------------------------------------------------
    trows = [[t["FY"], t["Month"], t["Region"], t["State"], t["Chain"], t["Brand"],
              t["BDO_BDE"], t["RKAM"], t["Target"], "UNKNOWN_SCOPE"] for t in tgts]
    sheet(wb, "03_Targets",
          ["FY", "Month", "Region", "State", "Chain", "Brand", "BDO_BDE", "RKAM",
           "Target_Value", "Target_Scope_Status"], trows, "tblTarget",
          note="Official target file. Scope unconfirmed (74.5% of business target) — not payout-usable yet (KA-03).")

    # ---- 04_Actuals ----------------------------------------------------------
    arows = [[r.get("FY", ""), r.get("Month", ""), r.get("Approved_Employee_ID", ""),
              r.get("Candidate_Employee_ID", ""), r.get("Role_Column", ""), r.get("WoA_Person", ""),
              r.get("Zone", ""), _num(r.get("Store_Count")), _num(r.get("Gross_Store_Actual_INR")),
              _num(r.get("Credited_Actual_INR")), r.get("Contribution_Pct", ""),
              r.get("Mapping_Status", ""), r.get("Source", ""), r.get("Period_Status", "")]
             for r in attrib]
    sheet(wb, "04_Actuals",
          ["FY", "Month", "Employee_ID", "Candidate_Employee_ID", "Role_Column", "WoA_Person",
           "Zone", "Store_Count", "Gross_Store_Actual", "Credited_Actual", "Contribution_Pct",
           "Mapping_Status", "Source", "Period_Status"], arows, "tblActual",
          {"Mapping_Status": 32, "WoA_Person": 24},
          note="Employee_ID is filled ONLY for an owner-approved mapping. Unapproved value is kept here "
               "under its Mapping_Status so the total still reconciles — it is never discarded and never "
               "credited. Each role is a separate credit line over the same stores: reconcile within a "
               "role, never add across roles (KA-12).")

    # ---- 05_WoA_Mapping ------------------------------------------------------
    wrows = []
    for w in woa:
        k = (w.get("WoA_Role_Column", ""), w.get("WoA_Raw_Name", ""), w.get("Zone", ""))
        st = at_stake.get(k, {})
        wrows.append([w.get("WoA_Role_Column", ""), w.get("WoA_Raw_Name", ""), w.get("Zone", ""),
                      _num(w.get("Stores_Assigned")), w.get("Candidate_Employee_ID", ""),
                      w.get("Candidate_Employee_Name", ""), w.get("Match_Method", ""),
                      w.get("Classification", ""), _num(st.get("Actual_At_Stake_L")),
                      w.get("Approved_Employee_ID", ""), w.get("Approval_Status", "PENDING"),
                      "MT Ops"])
    wrows.sort(key=lambda r: -(r[8] or 0))
    sheet(wb, "05_WoA_Mapping",
          ["WoA_Role_Column", "WoA_Raw_Name", "Zone", "Stores_Assigned", "Candidate_Employee_ID",
           "Candidate_Employee_Name", "Match_Method", "Classification", "Actual_At_Stake_L",
           "Approved_Employee_ID", "Approval_Status", "Owner"], wrows, "tblWoA",
          note="Candidates only — Approved_Employee_ID stays blank until MT Ops fills it (KA-04). "
               "Actual_At_Stake_L is the Apr-Jul role credit each signature releases; rows are sorted "
               "by it so the most valuable approvals are at the top.")

    # ---- 06_Achievement (formula-driven, gates named per KA-15) -------------
    ws = wb.create_sheet("06_Achievement")
    ws.cell(1, 1, "Readiness reports the FIRST failing gate by name, in KA-15 order: grade, "
                  "identity, target scope, target basis, rule. Blocked is never rendered as 0."
                  ).font = Font(italic=True, color="555555")
    heads = ["Employee_ID", "Employee_Name", "Incentive_Grade", "Grade_Status", "Period",
             "Measurement_Scope", "Target_Value", "Actual_Value", "Actual_Pending_Approval",
             "Achievement_Pct", "Readiness"]
    for c, h in enumerate(heads, 1):
        ws.cell(3, c, h).fill = HDR_FILL
        ws.cell(3, c).font = HDR_FONT
    EMP = "tblEmployee[Employee_ID]"
    for i, e in enumerate(emps, 1):
        r = 3 + i
        ws.cell(r, 1, e.get("Employee ID", ""))
        for col, src in ((2, "Employee_Name"), (3, "Incentive_Grade"), (4, "Grade_Status")):
            ws.cell(r, col, f'=IFERROR(INDEX(tblEmployee[{src}],MATCH([@[Employee_ID]],{EMP},0)),"")')
        ws.cell(r, 5, FY)
        ws.cell(r, 6, "BUSINESS_CONFIRMATION_REQUIRED")
        # BDO/BDE is the only person-level column in the target file; RKAM there is a zone
        # role label, not a name. Gated so an all-India total can never post to one person.
        ws.cell(r, 7, '=IF([@[Readiness]]<>"READY_TO_CALCULATE","",SUMIFS(tblTarget[Target_Value],'
                      'tblTarget[BDO_BDE],[@[Employee_Name]],tblTarget[FY],[@[Period]]))')
        # Only owner-approved rows carry a credited actual.
        ws.cell(r, 8, '=IF(COUNTIFS(tblActual[Employee_ID],[@[Employee_ID]])=0,"",'
                      'SUMIFS(tblActual[Credited_Actual],tblActual[Employee_ID],[@[Employee_ID]]))')
        # What a signature on this person's WoA mapping would release.
        ws.cell(r, 9, '=SUMIFS(tblActual[Gross_Store_Actual],tblActual[Candidate_Employee_ID],'
                      '[@[Employee_ID]])')
        ws.cell(r, 10, '=IF(OR([@[Target_Value]]="",[@[Actual_Value]]=""),"",'
                       '[@[Actual_Value]]/[@[Target_Value]]*100)')
        ws.cell(r, 11,
                '=IF([@[Grade_Status]]<>"VALID","GRADE_BLOCKED",'
                'IF(COUNTIFS(tblActual[Employee_ID],[@[Employee_ID]])=0,"IDENTITY_BLOCKED: WoA mapping not approved",'
                'IF(INDEX(tblControl[Value],MATCH("Target_Scope_Status",tblControl[Item],0))<>"CONFIRMED",'
                '"TARGET_BLOCKED: scope unconfirmed",'
                'IF(LEFT(INDEX(tblControl[Value],MATCH("Target basis",tblControl[Item],0)),7)="ASSUMED",'
                '"TARGET_BLOCKED: basis unconfirmed",'
                'IF(INDEX(tblControl[Value],MATCH("Rule version",tblControl[Item],0))="PENDING",'
                '"RULE_BLOCKED","READY_TO_CALCULATE")))))')
    n = max(len(emps), 1)
    t = Table(displayName="tblAchievement", ref=f"A3:{get_column_letter(len(heads))}{3 + n}")
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(t)
    for c, h in enumerate(heads, 1):
        ws.column_dimensions[get_column_letter(c)].width = max(14, min(38, len(h) + 8))
    ws.freeze_panes = ws.cell(4, 1)

    # ---- 07_Incentive_Calc ---------------------------------------------------
    ws = wb.create_sheet("07_Incentive_Calc")
    ws.cell(1, 1, "No payout is calculated while any mandatory decision is open. "
                  "Final_Calculated_Amount stays blank by design (KA-02).").font = Font(italic=True, color="555555")
    heads = ["Employee_ID", "Incentive_Grade", "Achievement_Pct", "Slab_Applied", "Parameter_Payout",
             "Kicker", "Gross", "Cap_Applied", "Proration", "Adjustment",
             "Final_Calculated_Amount", "Rule_Version", "Target_Version", "Actual_Source_Version",
             "Calculation_Timestamp", "Calculation_Status"]
    for c, h in enumerate(heads, 1):
        ws.cell(3, c, h).fill = HDR_FILL
        ws.cell(3, c).font = HDR_FONT
    for i, e in enumerate(emps, 1):
        r = 3 + i
        ws.cell(r, 1, e.get("Employee ID", ""))
        ws.cell(r, 2, '=IFERROR(INDEX(tblEmployee[Incentive_Grade],MATCH([@[Employee_ID]],tblEmployee[Employee_ID],0)),"")')
        ws.cell(r, 3, '=IFERROR(INDEX(tblAchievement[Achievement_Pct],MATCH([@[Employee_ID]],tblAchievement[Employee_ID],0)),"")')
        for c in (4, 5, 6, 7, 8, 9, 10, 11):
            ws.cell(r, c, "")
        ws.cell(r, 12, "PENDING")
        ws.cell(r, 13, "UNKNOWN_SCOPE")
        ws.cell(r, 14, "NOT_AVAILABLE")
        ws.cell(r, 15, date.today().isoformat())
        ws.cell(r, 16, '=IFERROR(INDEX(tblAchievement[Readiness],MATCH([@[Employee_ID]],'
                       'tblAchievement[Employee_ID],0)),"BLOCKED")')
    t = Table(displayName="tblCalc", ref=f"A3:{get_column_letter(len(heads))}{3 + max(len(emps),1)}")
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(t)
    for c, h in enumerate(heads, 1):
        ws.column_dimensions[get_column_letter(c)].width = max(14, min(30, len(h) + 4))
    ws.freeze_panes = ws.cell(4, 1)

    # ---- 08_Exceptions -------------------------------------------------------
    exc = []
    for e in emps:
        g, eid = e["_grade"], e.get("Employee ID", "")
        if g in slab_desig:
            continue
        kind = ("SOURCE_DATA_FIX_REQUIRED" if g.upper().startswith("#") else "MISSING" if not g else "INVALID")
        exc.append(["Grade", eid, kind, g or "(blank)",
                    "Employee cannot be paid until a valid slab grade is supplied", 1, "HR", "OPEN"])
    for w in woa:
        if w.get("Classification") in ("OWNER_ROW_EXCEPTION", "SOURCE_DATA_FIX_REQUIRED"):
            exc.append(["WoA mapping", w.get("WoA_Raw_Name", ""), w.get("Classification", ""),
                        w.get("Match_Method", ""), w.get("Why", "")[:120],
                        w.get("Stores_Assigned", ""), "MT Ops", "OPEN"])
    exc.append(["Target scope", "RKAM target file", "UNKNOWN_SCOPE",
                f"{round(tgt_total / biz_target * 100, 1)}% of business target",
                "Scope and exclusions unconfirmed — blocks every payout row", len(tgts),
                "MT Leadership / Finance", "OPEN"])
    pc = (scope.get("period_coverage") or {}).get("part_year_regions") or {}
    for reg, v in sorted(pc.items()):
        exc.append(["Target coverage", f"{reg} region", "INCOMPLETE_TARGET_COVERAGE",
                    f"{v['months_planned']}/12 months planned",
                    f"{v['months_missing'][0]}-{v['months_missing'][-1]} carries no target; "
                    f"H2 cannot be measured", v["planned_L"], "MT Leadership", "OPEN"])
    gd = scope.get("grain_defects") or {}
    if gd.get("blank_chain_L"):
        exc.append(["Target grain", "Rows with no chain name", "GRAIN_MISMATCH",
                    f"{gd['blank_chain_rows']} rows, Rs {gd['blank_chain_L']:,.0f} L",
                    f"{', '.join(gd.get('blank_chain_regions', []))} planned at state x brand x "
                    f"person, not chain-wise — not a duplicate, but not chain-measurable",
                    gd["blank_chain_L"], "MT Leadership / MT Ops", "OPEN"])
    for c, v in list((scope.get("dimensions", {}).get("chain", {})
                      .get("in_business_not_in_target") or {}).items())[:6]:
        exc.append(["Target coverage", c, "ACCOUNT_WITHOUT_TARGET", f"Rs {v:,.0f} L FY26 offtake",
                    "Live account with no target row — intentional exclusion or coverage gap?",
                    v, "MT Leadership", "OPEN"])
    # Actual-side coverage: the population with sales but no ownership record at all.
    ocsv = REPO / "incentive_working" / "actuals_outside_woa_coverage.csv"
    if ocsv.exists():
        for r in csv.DictReader(open(ocsv, encoding="utf-8")):
            exc.append(["Actual coverage", f"{r['Client_Type']} stores", "STORE_NOT_IN_WOA_SHEET",
                        f"{r['Stores']} stores, Rs {float(r['Actual_L']):,.0f} L",
                        "Sales with no ownership row — is this population inside the incentive "
                        "measurement scope?", r["Stores"], "MT Leadership / MT Ops", "OPEN"])
    sheet(wb, "08_Exceptions",
          ["Area", "Item", "Exception_Type", "Current_Value", "Why_It_Blocks",
           "Rows_Or_Stores_Affected", "Owner", "Status"], exc, "tblExceptions",
          {"Why_It_Blocks": 58, "Item": 30},
          note="The working control centre. Every open row here blocks something downstream.")

    # ---- 09_Finance_Approval / 10_Summary / 11_Data_Quality / 12_Rule_Decisions
    sheet(wb, "09_Finance_Approval",
          ["Batch_ID", "Period", "Employee_Count", "Total_Calculated", "Prepared_By",
           "Reviewed_By", "Approved_By", "Approval_Date", "Payout_Status", "Remarks"], [],
          "tblApproval",
          note="EMPTY BY DESIGN. Nothing reaches approval while calculation status is BLOCKED.")

    gv = sum(1 for e in emps if e["_grade"] in slab_desig)
    # The source total for store actuals. It cannot be summed off the attribution rows:
    # each role repeats the same store-month by design, so any sum over them multiplies.
    asum = REPO / "incentive_working" / "actual_attribution_summary.json"
    gross_actual_L = json.loads(asum.read_text()).get("total_store_actual_L", 0.0) \
        if asum.exists() else 0.0
    by_role = {}
    for k, r in at_stake.items():
        by_role[k[0]] = by_role.get(k[0], 0.0) + float(r.get("Actual_At_Stake_L") or 0)
    at_stake_top = max(by_role.values()) if by_role else 0.0
    summ = [
        ["Employees in master", len(emps), ""],
        ["Grade VALID", gv, "Payable against the slab"],
        ["Grade not usable", len(emps) - gv, "#N/A or blank — see 08_Exceptions"],
        ["WoA person-values", len(woa), "From the candidate register"],
        ["WoA approved", len(approved_ids), "Owner-approved identities"],
        ["Target rows", len(tgts), f"{round(tgt_total, 2)} Rs L over "
                                   f"{len({t['Month'] for t in tgts})} month(s)"],
        ["Target gap explained", f"{gapd.get('explained_indicative_L', '–')} Rs L",
         f"{100 - gapd.get('unexplained_pct_of_gap', 0):.0f}% of the gap traced — see 13_Target_Scope"],
        ["Actual rows", len(attrib),
         f"{gross_actual_L:,.2f} Rs L of store actuals across {len(attr_months)} month(s), "
         f"credited once per role line"],
        ["Actual credited", 0, "No identity approved yet, so nothing is credited"],
        ["Actual at stake on signatures", f"{at_stake_top:,.2f} Rs L",
         "Largest single role line; role lines are never added together (KA-12)"],
        ["Calculation-ready employees", 0, "Every row blocked — see 06_Achievement for the gate"],
        ["Final payout", "NOT CALCULATED", "Mandatory decisions open"],
    ]
    sheet(wb, "10_Summary", ["Metric", "Value", "Note"], summ, "tblSummary",
          {"Metric": 30, "Note": 48},
          note="Counts only. No payout figure appears anywhere in this workbook yet.")

    _variants = len((scope.get("dimensions", {}).get("chain", {})
                     .get("spelling_variants_folded") or []))
    _pc = scope.get("period_coverage") or {}
    _full_reg = len(_pc.get("fully_planned_regions") or {})
    _all_reg = _full_reg + len(_pc.get("part_year_regions") or {})
    rc = REPO / "incentive_working" / "actual_attribution_reconciliation.csv"
    rrows = list(csv.DictReader(open(rc, encoding="utf-8"))) if rc.exists() else []
    recon_status = "YES" if rrows and all(r["Reconciles"] == "YES" for r in rrows) else "NO"
    oc = REPO / "incentive_working" / "actuals_outside_woa_coverage.csv"
    stores_outside = str(sum(int(r["Stores"]) for r in csv.DictReader(open(oc, encoding="utf-8")))) \
        if oc.exists() else "–"
    dq = [
        ["Employee master", "Grade populated", f"{gv}/{len(emps)}", "AMBER" if gv < len(emps) else "GREEN"],
        ["Employee master", "Grade matches slab", f"{gv}/{len(emps)}", "AMBER" if gv < len(emps) else "GREEN"],
        ["Target file", "Rows loaded", str(len(tgts)), "GREEN"],
        ["Target file", "Coverage vs business target", f"{round(tgt_total/biz_target*100,1)}%", "RED"],
        ["Target file", "Chain spelling variants folded", str(_variants), "AMBER" if _variants else "GREEN"],
        ["WoA register", "Identities approved", f"{sum(1 for w in woa if (w.get('Approved_Employee_ID') or '').strip())}/{len(woa)}", "RED"],
        ["Target file", "Regions planned for all 12 months",
         f"{_full_reg}/{_all_reg} regions" if _all_reg else "–",
         "RED" if _full_reg < _all_reg else "GREEN"],
        ["Actuals", "Store actual rows loaded", str(len(attrib)), "GREEN" if attrib else "RED"],
        ["Actuals", "Credited to an approved employee", f"0/{len(attrib)}", "RED"],
        ["Actuals", "Reconciles to source (all role lines)", recon_status, 
         "GREEN" if recon_status == "YES" else "RED"],
        ["Actuals", "Stores with sales but no WoA row", stores_outside, "RED"],
    ]
    sheet(wb, "11_Data_Quality", ["Source", "Check", "Result", "RAG"], dq, "tblDQ",
          {"Check": 38, "Source": 22})

    dp = REPO / "incentive_working" / "incentive_decision_register.csv"
    dec = list(csv.DictReader(open(dp, encoding="utf-8"))) if dp.exists() else []
    # Value at stake per decision, so an owner sees what their signature unlocks (KA-13).
    impact = {
        "target scope": (round(biz_target - tgt_total, 2), len(emps)),
        "target basis": (round(tgt_total, 2), len(emps)),
        "identity": (round(sum(by_role.values()), 2), len(woa)),
        "grade": ("–", len(emps) - gv),
    }

    def _impact(q):
        ql = (q or "").lower()
        for k, v in impact.items():
            if k.split()[0] in ql:
                return v
        return ("–", "–")

    drows = []
    for d in dec:
        val, cnt = _impact(d.get("Question", ""))
        drows.append([d.get("Decision_ID", ""), d.get("Question", ""), d.get("Current_Status", ""),
                      d.get("Affected_Roles", ""), d.get("Decision_Owner", ""), val, cnt,
                      d.get("Decision", ""), d.get("Effective_From", ""), d.get("Confirmed_By", ""),
                      "", ""])
    # Decisions surfaced by this phase that the register does not yet carry.
    pcs = (scope.get("period_coverage") or {}).get("part_year_regions") or {}
    if pcs:
        drows.append(["D-SCOPE-01",
                      f"Are {', '.join(sorted(pcs))} H1-only for incentive, or is the H2 target "
                      "still to be loaded?", "OPEN", "RKAM, BDO/BDE", "MT Leadership",
                      round((scope.get("period_coverage") or {}).get("indicative_missing_L", 0), 2),
                      "–", "", "", "", "", ""])
    if ocsv.exists():
        drows.append(["D-SCOPE-02",
                      "Are stores with no WoA deployment (D-Mart estate) inside the incentive "
                      "measurement scope?", "OPEN", "All field roles", "MT Leadership / MT Ops",
                      "–", stores_outside, "", "", "", "", ""])
    sheet(wb, "12_Rule_Decisions",
          ["Decision_ID", "Question", "Status", "Affected_Roles", "Owner", "Value_At_Stake_L",
           "Affected_Count", "Decision", "Effective_From", "Confirmed_By", "Rule_Version",
           "Supersedes"], drows, "tblDecisions",
          {"Question": 76, "Affected_Roles": 20},
          note="Open business decisions with their owner and what they are worth (KA-13). "
               "Decision / Effective_From / Confirmed_By / Rule_Version are for the owner to fill (KA-14).")

    # ---- 13_Target_Scope -----------------------------------------------------
    srows = []
    rc2 = REPO / "incentive_working" / "target_scope_reconciliation.csv"
    if rc2.exists():
        rd = list(csv.DictReader(open(rc2, encoding="utf-8")))
        srows = [[r["Dimension"], r["Universe_Count"], r["Target_Count"], r["Missing_Count"],
                  _num(r["Target_Value_L"]), _num(r["Reference_Value_L"]), r["Coverage_Pct"],
                  r["Status"], r["Business_Interpretation_Required"]] for r in rd]
    for e in (gapd.get("explained") or []):
        srows.append(["GAP CAUSE: " + e["cause"], "", "", "", _num(e["indicative_L"]), "", "",
                      e.get("likely_class", ""), "Yes"])
    if gapd:
        srows.append(["GAP: unexplained residual", "", "", "", _num(gapd.get("unexplained_L")), "",
                      f"{gapd.get('unexplained_pct_of_gap', 0)}% of gap", "UNKNOWN_SCOPE", "Yes"])
    sheet(wb, "13_Target_Scope",
          ["Dimension", "Universe_Count", "Target_Count", "Missing_Count", "Target_Value_L",
           "Reference_Value_L", "Coverage_Pct", "Status", "Business_Interpretation_Required"],
          srows, "tblScope", {"Dimension": 52, "Status": 32},
          note="KA-11 reconciliation. Indicative sizings only — nothing here allocates or adjusts a "
               "target. Full narrative: incentive_working/target_scope_decision_pack.md")

    outp.parent.mkdir(parents=True, exist_ok=True)
    wb.save(outp)
    print(f"Wrote {outp}  ({outp.stat().st_size/1024:.0f} KB, {len(wb.sheetnames)} sheets) — RESTRICTED, gitignored")
    print(f"  employees {len(emps)} | grade VALID {gv} | slab rows {len(slabs)} | "
          f"target rows {len(tgts)} | WoA {len(woa)} | exceptions {len(exc)}")
    print(f"  target coverage {round(tgt_total/biz_target*100,1)}% -> Target_Scope_Status UNKNOWN_SCOPE")
    print("  calculation status: BLOCKED — no payout produced")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
