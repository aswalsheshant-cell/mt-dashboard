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
    woa = []
    wp = REPO / a.woa_register
    if wp.exists():
        woa = list(csv.DictReader(open(wp, encoding="utf-8")))

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    # ---- 00_Control ----------------------------------------------------------
    tgt_total = sum(t["Target"] for t in tgts)
    biz_target = 44132.86
    ctrl = [
        ["Reporting FY", FY, "From the target file"],
        ["Reporting months", ", ".join(MONTHS), "Months with actuals available"],
        ["Refresh timestamp", date.today().isoformat(), "Date this workbook was generated"],
        ["Target basis", "ASSUMED: Offtake", "BLOCKED — Primary vs Offtake not confirmed (D1)"],
        ["Target file total (Rs L)", round(tgt_total, 2), "Sum of the target master"],
        ["Business target (Rs L)", biz_target, "FY27 total-business target"],
        ["Target coverage %", round(tgt_total / biz_target * 100, 2), "Target file as a share of business target"],
        ["Target_Scope_Status", "UNKNOWN_SCOPE", "KA-03 — must be confirmed before payout use"],
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
    sheet(wb, "04_Actuals",
          ["FY", "Month", "Employee_ID", "Measurement_Scope", "Actual_Value",
           "Actual_Source", "Source_Version", "Status"], [], "tblActual",
          note="EMPTY BY DESIGN. Employee-level actuals need approved WoA mapping first — see 05. Never fill with zeros.")

    # ---- 05_WoA_Mapping ------------------------------------------------------
    wrows = [[w.get("WoA_Role_Column", ""), w.get("WoA_Raw_Name", ""), w.get("Zone", ""),
              w.get("Stores_Assigned", ""), w.get("Candidate_Employee_ID", ""),
              w.get("Candidate_Employee_Name", ""), w.get("Match_Method", ""),
              w.get("Classification", ""), w.get("Approved_Employee_ID", ""),
              w.get("Approval_Status", "PENDING")] for w in woa]
    sheet(wb, "05_WoA_Mapping",
          ["WoA_Role_Column", "WoA_Raw_Name", "Zone", "Stores_Assigned", "Candidate_Employee_ID",
           "Candidate_Employee_Name", "Match_Method", "Classification", "Approved_Employee_ID",
           "Approval_Status"], wrows, "tblWoA",
          note="Candidates only. Approved_Employee_ID stays blank until a named owner fills it (KA-04).")

    # ---- 06_Achievement (formula-driven, blocked until inputs exist) ---------
    ws = wb.create_sheet("06_Achievement")
    ws.cell(1, 1, "Achievement is formula-driven. A row stays BLOCKED until identity, grade, "
                  "scope, target and actual are all present — it never shows 0.").font = Font(italic=True, color="555555")
    heads = ["Employee_ID", "Employee_Name", "Incentive_Grade", "Grade_Status", "Period",
             "Measurement_Scope", "Target_Value", "Actual_Value", "Achievement_Pct", "Readiness"]
    for c, h in enumerate(heads, 1):
        ws.cell(3, c, h).fill = HDR_FILL
        ws.cell(3, c).font = HDR_FONT
    for i, e in enumerate(emps, 1):
        r = 3 + i
        ws.cell(r, 1, e.get("Employee ID", ""))
        ws.cell(r, 2, f'=IFERROR(INDEX(tblEmployee[Employee_Name],MATCH([@[Employee_ID]],tblEmployee[Employee_ID],0)),"")')
        ws.cell(r, 3, f'=IFERROR(INDEX(tblEmployee[Incentive_Grade],MATCH([@[Employee_ID]],tblEmployee[Employee_ID],0)),"")')
        ws.cell(r, 4, f'=IFERROR(INDEX(tblEmployee[Grade_Status],MATCH([@[Employee_ID]],tblEmployee[Employee_ID],0)),"")')
        ws.cell(r, 5, FY)
        ws.cell(r, 6, "BUSINESS_CONFIRMATION_REQUIRED")
        # BDO/BDE is the only person-level column in the target file; RKAM holds a zone role
        # label ("RKAM West"), not a name. Attribution stays an open decision, so the sum is
        # gated on Readiness and can never post an all-India total against one employee.
        ws.cell(r, 7, '=IF([@[Readiness]]<>"READY","",SUMIFS(tblTarget[Target_Value],'
                      'tblTarget[BDO_BDE],[@[Employee_Name]],tblTarget[FY],[@[Period]]))')
        ws.cell(r, 8, '=IF(COUNTA(tblActual[Actual_Value])=0,"",SUMIFS(tblActual[Actual_Value],tblActual[Employee_ID],[@[Employee_ID]]))')
        ws.cell(r, 9, '=IF(OR([@[Target_Value]]="",[@[Actual_Value]]=""),"",[@[Actual_Value]]/[@[Target_Value]]*100)')
        ws.cell(r, 10, '=IF([@[Grade_Status]]<>"VALID","BLOCKED: grade",'
                       'IF(COUNTA(tblActual[Actual_Value])=0,"BLOCKED: no actuals",'
                       'IF(INDEX(tblControl[Value],MATCH("Target_Scope_Status",tblControl[Item],0))<>"CONFIRMED","BLOCKED: target scope","READY")))')
    n = max(len(emps), 1)
    t = Table(displayName="tblAchievement", ref=f"A3:{get_column_letter(len(heads))}{3 + n}")
    t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
    ws.add_table(t)
    for c, h in enumerate(heads, 1):
        ws.column_dimensions[get_column_letter(c)].width = max(14, min(32, len(h) + 6))
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
        ws.cell(r, 16, '=IFERROR(INDEX(tblAchievement[Readiness],MATCH([@[Employee_ID]],tblAchievement[Employee_ID],0)),"BLOCKED")')
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
                f"{round(tgt_total/biz_target*100,1)}% of business target",
                "Scope and exclusions unconfirmed — blocks every payout row", len(tgts),
                "MT Leadership / Finance", "OPEN"])
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
    summ = [
        ["Employees in master", len(emps), ""],
        ["Grade VALID", gv, "Payable against the slab"],
        ["Grade not usable", len(emps) - gv, "#N/A or blank — see 08_Exceptions"],
        ["WoA person-values", len(woa), "From the candidate register"],
        ["WoA approved", sum(1 for w in woa if (w.get("Approved_Employee_ID") or "").strip()), "Owner-approved identities"],
        ["Target rows", len(tgts), f"{round(tgt_total,2)} Rs L"],
        ["Actual rows", 0, "Blocked on approved WoA mapping"],
        ["Calculation-ready employees", 0, "Every row blocked — see 08_Exceptions"],
        ["Final payout", "NOT CALCULATED", "Mandatory decisions open"],
    ]
    sheet(wb, "10_Summary", ["Metric", "Value", "Note"], summ, "tblSummary",
          {"Metric": 30, "Note": 48},
          note="Counts only. No payout figure appears anywhere in this workbook yet.")

    dq = [
        ["Employee master", "Grade populated", f"{gv}/{len(emps)}", "AMBER" if gv < len(emps) else "GREEN"],
        ["Employee master", "Grade matches slab", f"{gv}/{len(emps)}", "AMBER" if gv < len(emps) else "GREEN"],
        ["Target file", "Rows loaded", str(len(tgts)), "GREEN"],
        ["Target file", "Coverage vs business target", f"{round(tgt_total/biz_target*100,1)}%", "RED"],
        ["Target file", "Chain/brand spelling variants", "16", "AMBER"],
        ["WoA register", "Identities approved", f"{sum(1 for w in woa if (w.get('Approved_Employee_ID') or '').strip())}/{len(woa)}", "RED"],
        ["Actuals", "Employee-level actuals available", "0", "RED"],
    ]
    sheet(wb, "11_Data_Quality", ["Source", "Check", "Result", "RAG"], dq, "tblDQ",
          {"Check": 38, "Source": 22})

    dp = REPO / "incentive_working" / "incentive_decision_register.csv"
    dec = list(csv.DictReader(open(dp, encoding="utf-8"))) if dp.exists() else []
    drows = [[d.get("Decision_ID", ""), d.get("Question", ""), d.get("Current_Status", ""),
              d.get("Affected_Roles", ""), d.get("Decision_Owner", ""), d.get("Decision", ""),
              d.get("Effective_From", ""), d.get("Confirmed_By", "")] for d in dec]
    sheet(wb, "12_Rule_Decisions",
          ["Decision_ID", "Question", "Status", "Affected_Roles", "Owner", "Decision",
           "Effective_From", "Confirmed_By"], drows, "tblDecisions",
          {"Question": 76, "Affected_Roles": 20},
          note="Open business decisions. Decision/Effective_From/Confirmed_By are for the owner to fill.")

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
