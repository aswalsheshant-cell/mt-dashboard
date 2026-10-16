"""Build the Offtake QoQ / H1 Excel dashboard (formulas live; add a month of rows, recalculate, it flows through).

Data sheet (Offtake_Data) = one row per Month x Chain x Brand x Category x Sub-category x Pack Size, NSV in Rs lakh.
  * This year (FY27): from the monthly store x article offtake CSVs (Brand Counter left out, as on the dashboard).
  * Last year (FY26): chain x month only (data/offtake_fy26/Store_Month_NSV_FY26.csv). Brand / sub-category / pack split for
    last year is NOT in the repo, so those rows carry the label LY_NO_SPLIT and the brand-level LY cells show "-" until the
    last-year article extract is pasted in (same columns).
Every analysis cell is SUMIFS over named ranges on Offtake_Data, so appended rows are picked up on recalculation.

  python scripts/build_offtake_excel.py [--out exports/MT_Offtake_QoQ_H1_Dashboard.xlsx] [--months Apr May Jun Jul Aug]
"""
import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import visit_cities as vc  # noqa: E402

LY_FILE = ROOT / "data" / "offtake_fy26" / "Store_Month_NSV_FY26.csv"
NO_SPLIT = "LY_NO_SPLIT"
MON = {"Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12, "Jan": 1, "Feb": 2, "Mar": 3}
NAVY, GOLD, LIGHT, GREEN, RED = "10254A", "DAA520", "F5F7FA", "1E8449", "C0392B"
TYPE = 'd_Type,"<>"&Est_Crit'      # leaves the exploratory estimate rows out when Control switch Incl_Est = 0
LAST_ROW = 200000       # named ranges run to this row so appended months are included
HFONT = Font(bold=True, color="FFFFFF", size=10)
HFILL = PatternFill("solid", fgColor=NAVY)
thin = Side(style="thin", color="D0D5DD")


def available_months(year="26"):
    order = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return [m for m in order if (vc.RAW / f"offtake_store_article_{m}_{year}.csv").exists()]


def exploratory_rows(cy, months, year="26"):
    """Exploratory rows for chains that have not reported the latest month: the chain's own average of the 3 months before
    it, at the same chain x brand x category x sub-category x pack grain (so every By_ sheet stays consistent)."""
    cols = ["Month", "Chain", "Brand", "Category", "Sub-category", "Pack Size", "NSV", "Qty", "Source", "Type"]
    if len(months) < 2:
        return cy.iloc[0:0][cols], []
    yr = 2000 + int(year)
    mk = lambda m: date(yr + (1 if MON[m] < 4 else 0), MON[m], 1)
    latest, win = mk(months[-1]), [mk(m) for m in months[-4:-1]]
    have = set(cy[cy["Month"] == latest]["Chain"])
    w = cy[cy["Month"].isin(win)]
    pend = sorted(c for c in w["Chain"].unique() if c not in have)
    g = w[w["Chain"].isin(pend)].groupby(["Chain", "Brand", "Category", "Sub-category", "Pack Size"], as_index=False).agg(NSV=("NSV", "sum"), Qty=("Qty", "sum"))
    g["NSV"] /= len(win)
    g["Qty"] /= len(win)
    g["Month"] = latest
    g["Source"] = "Exploratory: chain's own average of " + ", ".join(m.strftime("%b") for m in win) + " (not actual)"
    g["Type"] = "Estimate"
    return g[cols], pend


def load_cy(months, year="26"):
    d = vc.load_offtake(months, year=year)
    d = d[~d["bc"]].copy()
    d["Net Weight"] = pd.to_numeric(d["Net Weight"], errors="coerce")
    d["Pack Size"] = d["Net Weight"].map(lambda x: f"{int(x)} g/ml" if pd.notna(x) else "Not stated")
    g = d.groupby(["file", "Chain", "Brand", "Category", "Sub_category", "Pack Size"], dropna=False).agg(
        NSV=("NSV", "sum"), Qty=("Sales Qty", "sum")).reset_index()
    g["Month"] = g["file"].map(lambda m: date(2000 + int(year) + (1 if MON[m] < 4 else 0), MON[m], 1))
    g["Source"] = "Chain POS (store x article file)"
    g["Type"] = "Actual"
    return g.rename(columns={"Sub_category": "Sub-category"})[["Month", "Chain", "Brand", "Category", "Sub-category", "Pack Size", "NSV", "Qty", "Source", "Type"]]


def load_ly():
    d = pd.read_csv(LY_FILE)
    d = d[d["Chain Name"] != "Reliance Brand Counter"].copy()
    d["Chain"] = d["Chain Name"].map(lambda s: vc.std_chain(s) or s)
    d["Month"] = d["Month"].map(lambda m: date(2000 + int(m.split("'")[1]), MON[m.split("'")[0]], 1))
    g = d.groupby(["Month", "Chain"]).agg(NSV=("NSV", "sum"), Qty=("Units", "sum")).reset_index()
    for c in ("Brand", "Category", "Sub-category", "Pack Size"):
        g[c] = NO_SPLIT
    g["Source"] = "Chain POS (chain x month only)"
    g["Type"] = "Actual"
    return g[["Month", "Chain", "Brand", "Category", "Sub-category", "Pack Size", "NSV", "Qty", "Source", "Type"]]


def hdr(ws, row, c1, c2, h=32):
    for c in range(c1, c2 + 1):
        x = ws.cell(row=row, column=c)
        x.font, x.fill = HFONT, HFILL
        x.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[row].height = h


def add_names(wb, ws_name, cols):
    for nm, col in cols.items():
        wb.defined_names[nm] = DefinedName(nm, attr_text=f"{ws_name}!${col}$2:${col}${LAST_ROW}")


def sumifs(period, crit):
    """crit: list of (name, cell-ref). period: (startName, endName)"""
    s = ",".join(f"{n},{c}" for n, c in crit)
    s = (s + ",") if s else ""
    return f"SUMIFS(d_NSV,{s}{TYPE},d_Month,\">=\"&{period[0]},d_Month,\"<=\"&{period[1]})"


def countifs(period, crit):
    s = ",".join(f"{n},{c}" for n, c in crit)
    s = (s + ",") if s else ""
    return f"COUNTIFS({s}{TYPE},d_Month,\">=\"&{period[0]},d_Month,\"<=\"&{period[1]})"


def ly_cell(period, crit):
    return f"=IF({countifs(period, crit)}=0,\"–\",{sumifs(period, crit)})" if crit else f"={sumifs(period, crit)}"


def pct(a, b):
    return f"IF(AND(ISNUMBER({a}),ISNUMBER({b})),IF({b}=0,\"–\",{a}/{b}-1),\"–\")"


def analysis_sheet(wb, name, title, keys, items, key_names, n_total_note=""):
    """keys: header names; items: list of tuples (values for each key); key_names: defined names of the data columns."""
    ws = wb.create_sheet(name)
    k = len(keys)
    heads = keys + ["CY Q1\nApr–Jun", "CY Q2\nJul–Sep (to date)", "QoQ %\n(per-month basis)", "LY Q1", "LY Q2\n(same months)", "LY QoQ %",
                    "Q1 YoY %", "Q2 YoY %\n(same months)", "CY H1\n(to date)", "LY H1\n(same months)", "H1 YoY %", "H1 change\n₹ L",
                    "Share of CY H1 %", "Share of total\nH1 growth %", "Suggested action", "rank CY", "rank gain", "rank drop"]
    ws["A1"] = title
    ws["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws["A2"] = ("NSV in ₹ lakh. CY = this year, LY = same months last year. Q2 and H1 count only the months loaded so far, and LY uses the same months. "
                "'–' means last year's split is not loaded for that item. " + n_total_note)
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=k + 12)
    ws.row_dimensions[2].height = 44
    hr = 5
    for i, h in enumerate(heads, 1):
        ws.cell(row=hr, column=i, value=h)
    hdr(ws, hr, 1, len(heads), 44)
    first, last = hr + 1, hr + len(items)
    tot = last + 1
    c0 = k + 1
    col = {n: L(c0 + i) for i, n in enumerate(["cq1", "cq2", "qoq", "lq1", "lq2", "lqoq", "yq1", "yq2", "ch1", "lh1", "yh1", "dh1", "sh", "ct", "act", "r1", "r2", "r3"])}
    for r, it in enumerate(items, first):
        for j, v in enumerate(it, 1):
            ws.cell(row=r, column=j, value=v)
        crit = [(key_names[j], f"${L(j + 1)}{r}") for j in range(k)]
        ws[f"{col['cq1']}{r}"] = "=" + sumifs(("CY_Q1_S", "CY_Q1_E"), crit)
        ws[f"{col['cq2']}{r}"] = "=" + sumifs(("CY_Q2_S", "CY_Q2_E"), crit)
        ws[f"{col['lq1']}{r}"] = ly_cell(("LY_Q1_S", "LY_Q1_E"), crit)
        ws[f"{col['lq2']}{r}"] = ly_cell(("LY_Q2_S", "LY_Q2_E"), crit)
        ws[f"{col['ch1']}{r}"] = "=" + sumifs(("CY_H1_S", "CY_H1_E"), crit)
        ws[f"{col['lh1']}{r}"] = ly_cell(("LY_H1_S", "LY_H1_E"), crit)
        cq1, cq2, lq1, lq2 = (f"{col[x]}{r}" for x in ("cq1", "cq2", "lq1", "lq2"))
        ws[f"{col['qoq']}{r}"] = f"=IF(OR(N_Q2=0,N_Q1=0),\"–\",IF({cq1}=0,\"–\",({cq2}/N_Q2)/({cq1}/N_Q1)-1))"
        ws[f"{col['lqoq']}{r}"] = f"=IF(OR(N_Q2=0,N_Q1=0),\"–\",IF(NOT(AND(ISNUMBER({lq1}),ISNUMBER({lq2}))),\"–\",IF({lq1}=0,\"–\",({lq2}/N_Q2)/({lq1}/N_Q1)-1)))"
        ws[f"{col['yq1']}{r}"] = "=" + pct(cq1, lq1)
        ws[f"{col['yq2']}{r}"] = f"=IF(N_Q2=0,\"–\"," + pct(cq2, lq2) + ")"
        ch1, lh1 = f"{col['ch1']}{r}", f"{col['lh1']}{r}"
        ws[f"{col['yh1']}{r}"] = "=" + pct(ch1, lh1)
        ws[f"{col['dh1']}{r}"] = f"=IF(ISNUMBER({lh1}),{ch1}-{lh1},\"–\")"
        ws[f"{col['sh']}{r}"] = f"=IF(${col['ch1']}${tot}=0,\"–\",{ch1}/${col['ch1']}${tot})"
        ws[f"{col['ct']}{r}"] = f"=IF(AND(ISNUMBER({col['dh1']}{r}),ISNUMBER(${col['lh1']}${tot})),IF(${col['lh1']}${tot}=0,\"–\",{col['dh1']}{r}/${col['lh1']}${tot}),\"–\")"
        y, q = f"{col['yh1']}{r}", f"{col['qoq']}{r}"
        ws[f"{col['act']}{r}"] = (f"=IF(NOT(ISNUMBER({y})),\"Last year split not loaded: cannot judge\","
                                  f"IF(AND({y}<-Thr_Fall,ISNUMBER({q}),{q}<0),\"Falling on both views: check listing, stock cover, promo and visibility\","
                                  f"IF({y}<-Thr_Fall,\"Below last year: find the gap (stores, SKUs, price)\","
                                  f"IF(AND(ISNUMBER({q}),{q}<-Thr_Fall),\"Slowing vs Q1: check Q2 stock and promo\","
                                  f"IF({y}>Thr_Grow,\"Growing: protect fill rate and visibility\",\"Hold: monitor\")))))")
        rng = lambda c: f"${col[c]}${first}:${col[c]}${last}"
        ws[f"{col['r1']}{r}"] = f"=RANK({ch1},{rng('ch1')},0)+COUNTIF(${col['ch1']}${first}:{ch1},{ch1})-1"
        d = f"{col['dh1']}{r}"
        ws[f"{col['r2']}{r}"] = f"=IF(ISNUMBER({d}),RANK({d},{rng('dh1')},0)+COUNTIF(${col['dh1']}${first}:{d},{d})-1,\"\")"
        ws[f"{col['r3']}{r}"] = f"=IF(ISNUMBER({d}),RANK({d},{rng('dh1')},1)+COUNTIF(${col['dh1']}${first}:{d},{d})-1,\"\")"
    # total row = every row in the data (not just listed items)
    ws.cell(row=tot, column=1, value="Total (all rows in data)")
    for key in ("cq1", "cq2", "lq1", "lq2", "ch1", "lh1"):
        per = {"cq1": ("CY_Q1_S", "CY_Q1_E"), "cq2": ("CY_Q2_S", "CY_Q2_E"), "lq1": ("LY_Q1_S", "LY_Q1_E"), "lq2": ("LY_Q2_S", "LY_Q2_E"),
               "ch1": ("CY_H1_S", "CY_H1_E"), "lh1": ("LY_H1_S", "LY_H1_E")}[key]
        ws[f"{col[key]}{tot}"] = "=" + sumifs(per, [])
    t = lambda c: f"{col[c]}{tot}"
    ws[t("qoq")] = f"=IF(OR(N_Q2=0,N_Q1=0),\"–\",({t('cq2')}/N_Q2)/({t('cq1')}/N_Q1)-1)"
    ws[t("lqoq")] = f"=IF(OR(N_Q2=0,N_Q1=0),\"–\",({t('lq2')}/N_Q2)/({t('lq1')}/N_Q1)-1)"
    ws[t("yq1")] = "=" + pct(t("cq1"), t("lq1"))
    ws[t("yq2")] = f"=IF(N_Q2=0,\"–\"," + pct(t("cq2"), t("lq2")) + ")"
    ws[t("yh1")] = "=" + pct(t("ch1"), t("lh1"))
    ws[t("dh1")] = f"={t('ch1')}-{t('lh1')}"
    for c in range(1, len(heads) - 2):
        ws.cell(row=tot, column=c).font = Font(bold=True)
        ws.cell(row=tot, column=c).fill = PatternFill("solid", fgColor="E8EDF5")
    # check cell: are all rows in the data listed on this sheet?
    ws["A3"] = (f"=IF(ABS({t('ch1')}-SUM({col['ch1']}{first}:{col['ch1']}{last}))<0.01,\"Check: OK, every row in the data is listed here\","
                f"\"Check: NEW items in the data are not listed (₹ \"&TEXT({t('ch1')}-SUM({col['ch1']}{first}:{col['ch1']}{last}),\"#,##0.0\")&\" L). Copy the last item row down and type the new name.\")")
    ws["A3"].font = Font(bold=True, color=NAVY)
    # formats
    for r in range(first, tot + 1):
        for key in ("cq1", "cq2", "lq1", "lq2", "ch1", "lh1", "dh1"):
            ws[f"{col[key]}{r}"].number_format = '#,##0.0;[Red]-#,##0.0'
        for key in ("qoq", "lqoq", "yq1", "yq2", "yh1", "sh", "ct"):
            ws[f"{col[key]}{r}"].number_format = '0.0%;[Red]-0.0%'
        for c in range(1, len(heads) + 1):
            ws.cell(row=r, column=c).border = Border(bottom=thin)
            if c > k and c <= len(heads) - 3 and key != "act":
                ws.cell(row=r, column=c).alignment = Alignment(horizontal="right")
    for key in ("yq1", "yq2", "yh1", "qoq"):
        rg = f"{col[key]}{first}:{col[key]}{tot}"
        ws.conditional_formatting.add(rg, CellIsRule(operator="greaterThan", formula=["0"], font=Font(color=GREEN, bold=True)))
    ws.freeze_panes = ws.cell(row=hr + 1, column=k + 1)
    ws.column_dimensions["A"].width = 26
    for i in range(2, k + 1):
        ws.column_dimensions[L(i)].width = 22
    for i in range(c0, c0 + 14):
        ws.column_dimensions[L(i)].width = 13
    ws.column_dimensions[col["act"]].width = 58
    for key in ("r1", "r2", "r3"):
        ws.column_dimensions[col[key]].hidden = True
    ws.auto_filter.ref = f"A{hr}:{col['act']}{last}"
    return ws, col, first, last, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "exports" / "MT_Offtake_QoQ_H1_Dashboard.xlsx"))
    ap.add_argument("--months", nargs="+", default=None, help="default: every offtake_store_article_<Mon>_26.csv in the watch folder")
    ap.add_argument("--no-estimate", action="store_true", help="leave out the exploratory estimate rows")
    a = ap.parse_args()
    months = a.months or available_months()
    cy, ly = load_cy(months), load_ly()
    est, pending = (cy.iloc[0:0], []) if a.no_estimate else exploratory_rows(cy, months)
    data = pd.concat([ly, cy, est], ignore_index=True)
    wb = Workbook()
    wb.remove(wb.active)

    # ---------- README
    rd = wb.create_sheet("README")
    lines = [
        ("MT Offtake: QoQ and H1 dashboard (Excel)", "t"),
        ("Offtake = chain POS sell-out. Primary and Distributor Secondary are different measures and are not in this file.", ""),
        ("Brand Counter stores (Reliance staffed counters) are left out, same as the web dashboard. NSV is in ₹ lakh.", ""),
        ("", ""),
        ("HOW TO ADD SEPTEMBER (or any new month)", "h"),
        ("1. Option A (small file): run  python scripts/offtake_month_to_rows.py Oct_26  . It writes a CSV in the same columns as Offtake_Data (Type = Actual). Paste its rows under the last row of Offtake_Data. When a chain is still pending, rebuild with scripts/build_offtake_excel.py to refresh the estimate rows, or delete the old Estimate rows for that month first.", ""),
        ("2. Option B (Power Query): Data > Get Data > From File > From Folder on the offtake_store_article folder, then use the query text on the sheet PowerQuery_Option. Load to Offtake_Data.", ""),
        ("3. Month must be a real date on the 1st of the month (type 1-Sep-2026, or Sep-26 and format as mmm-yy).", ""),
        ("4. Recalculate (F9, or Data > Refresh All). Control shows the new Latest month; every sheet and the Dashboard move to it.", ""),
        ("5. On Control, check 'Rows with a bad month' = 0. On each By_ sheet, the Check line at the top says OK or lists new chains/items to add as a row.", ""),
        ("", ""),
        ("HOW THE PERIODS WORK", "h"),
        ("CY = the FY (Apr–Mar) of the latest month in the data. LY = the same months one year earlier. Q1 = Apr–Jun, Q2 = Jul–Sep, H1 = Apr–Sep.", ""),
        ("Q2 and H1 count only months loaded so far, and LY uses the same months, so a part-built quarter is never compared with a full one.", ""),
        ("QoQ is on a per-month basis (Q2 average month ÷ Q1 average month), so it stays fair while Q2 is still filling.", ""),
        ("", ""),
        ("WHAT IS NOT IN THE DATA (named, not estimated)", "h"),
        ("Last year (FY26) is loaded at chain x month only. Last year's brand, category, sub-category and pack split is not in the repo, so those LY cells show '–'.", ""),
        ("To fill them: supply the FY26 store x article extracts (the 12 monthly files behind the 'FY-24-26 Chain offtake Store Wise File' source). Paste the aggregated rows in the same columns and delete the LY_NO_SPLIT rows for those months.", ""),
        ("Sep-26 offtake: loaded from Compiled_Sep26_File.xlsb (partial: some chains not received). Primary Sep-26 is NOT loaded (primary_article_Sep_26.csv not supplied).", ""),
        ("Chains with no Sep-26 rows carry an EXPLORATORY estimate (Type = Estimate): the chain's own average of the 3 months before, at brand / sub-category / pack level. Control switch Incl_Est turns it on or off. Never treat it as actual.", ""),
        ("", ""),
        ("SHEETS", "h"),
        ("Dashboard: headline numbers, charts, top movers.  Insights: descriptive / diagnostic / predictive / prescriptive read-out.  Control: periods and thresholds.", ""),
        ("By_Chain, By_Brand, By_Category, By_SubCategory, By_PackSize, Chain_x_Brand, Chain_x_SubCat, Brand_x_SubCat, Brand_x_Pack: Q1, Q2, QoQ, H1 and YoY at each level.", ""),
        ("Monthly: month-by-month trend by chain, this year and last year.  Offtake_Data: the data. All numbers on other sheets are formulas on this sheet.", ""),
    ]
    for i, (t, k) in enumerate(lines, 1):
        c = rd.cell(row=i, column=1, value=t)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if k == "t":
            c.font = Font(bold=True, size=16, color=NAVY)
        elif k == "h":
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = HFILL
    rd.column_dimensions["A"].width = 150

    # ---------- Offtake_Data
    wd = wb.create_sheet("Offtake_Data")
    cols = ["Month", "Chain", "Brand", "Category", "Sub-category", "Pack Size", "NSV (₹ L)", "Qty", "Source", "Type"]
    wd.append(cols)
    for r in data.itertuples(index=False):
        wd.append([r.Month, r.Chain, r.Brand, r.Category, r._4, r._5, round(float(r.NSV), 6), float(r.Qty), r.Source, r.Type])
    n = len(data) + 1
    for row in wd.iter_rows(min_row=2, max_row=n, min_col=1, max_col=1):
        row[0].number_format = "mmm-yy"
    tab = Table(displayName="tblOfftake", ref=f"A1:J{n}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    wd.add_table(tab)
    for c, w in zip("ABCDEFGHIJ", (10, 22, 16, 16, 22, 14, 12, 12, 40, 10)):
        wd.column_dimensions[c].width = w
    wd.freeze_panes = "A2"
    add_names(wb, "Offtake_Data", {"d_Month": "A", "d_Chain": "B", "d_Brand": "C", "d_Cat": "D", "d_Sub": "E", "d_Pack": "F", "d_NSV": "G", "d_Type": "J"})

    # ---------- Control
    ct = wb.create_sheet("Control")
    ct["A1"] = "Control: periods and thresholds (formulas; change only the yellow cells)"
    ct["A1"].font = Font(bold=True, size=14, color=NAVY)
    rows = [
        ("Latest month in data", "=MAX(d_Month)", "LatestMonth", "mmm-yy"),
        ("Financial year start (Apr)", "=DATE(YEAR(LatestMonth)-IF(MONTH(LatestMonth)<4,1,0),4,1)", "FYStart", "mmm-yy"),
        ("CY label", '="FY"&TEXT(MOD(YEAR(FYStart)+1,100),"00")', "CY_Label", "@"),
        ("LY label", '="FY"&TEXT(MOD(YEAR(FYStart),100),"00")', "LY_Label", "@"),
        ("CY Q1 start", "=FYStart", "CY_Q1_S", "mmm-yy"),
        ("CY Q1 end (to date)", "=MIN(EDATE(FYStart,2),LatestMonth)", "CY_Q1_E", "mmm-yy"),
        ("CY Q2 start", "=EDATE(FYStart,3)", "CY_Q2_S", "mmm-yy"),
        ("CY Q2 end (to date)", "=MIN(EDATE(FYStart,5),LatestMonth)", "CY_Q2_E", "mmm-yy"),
        ("CY H1 start", "=FYStart", "CY_H1_S", "mmm-yy"),
        ("CY H1 end (to date)", "=MIN(EDATE(FYStart,5),LatestMonth)", "CY_H1_E", "mmm-yy"),
        ("Months loaded in Q1", "=MAX(0,(YEAR(CY_Q1_E)-YEAR(CY_Q1_S))*12+MONTH(CY_Q1_E)-MONTH(CY_Q1_S)+1)", "N_Q1", "0"),
        ("Months loaded in Q2", "=MAX(0,(YEAR(CY_Q2_E)-YEAR(CY_Q2_S))*12+MONTH(CY_Q2_E)-MONTH(CY_Q2_S)+1)", "N_Q2", "0"),
        ("Months loaded in H1", "=MAX(0,(YEAR(CY_H1_E)-YEAR(CY_H1_S))*12+MONTH(CY_H1_E)-MONTH(CY_H1_S)+1)", "N_H1", "0"),
        ("LY Q1 start", "=EDATE(CY_Q1_S,-12)", "LY_Q1_S", "mmm-yy"),
        ("LY Q1 end", "=EDATE(CY_Q1_E,-12)", "LY_Q1_E", "mmm-yy"),
        ("LY Q2 start", "=EDATE(CY_Q2_S,-12)", "LY_Q2_S", "mmm-yy"),
        ("LY Q2 end (same months)", "=EDATE(CY_Q2_E,-12)", "LY_Q2_E", "mmm-yy"),
        ("LY H1 start", "=EDATE(CY_H1_S,-12)", "LY_H1_S", "mmm-yy"),
        ("LY H1 end (same months)", "=EDATE(CY_H1_E,-12)", "LY_H1_E", "mmm-yy"),
        ("LY full H1 end (Sep)", "=EDATE(FYStart,5-12)", "LY_H1_FULL_E", "mmm-yy"),
        ("Include exploratory estimate for pending chains (1 = yes, 0 = actuals only)", 1, "Incl_Est", "0"),
        ("(helper) criterion that leaves estimate rows out", '=IF(Incl_Est=1,"__none__","Estimate")', "Est_Crit", "@"),
        ("Exploratory estimate in the latest month (₹ L)", '=SUMIFS(d_NSV,d_Type,"Estimate",d_Month,LatestMonth)', "Est_Latest", "#,##0.0"),
        ("Actual in the latest month (₹ L)", '=SUMIFS(d_NSV,d_Type,"<>Estimate",d_Month,LatestMonth)', "Act_Latest", "#,##0.0"),
        ("Fall threshold (action flag)", 0.10, "Thr_Fall", "0%"),
        ("Growth threshold (action flag)", 0.20, "Thr_Grow", "0%"),
        ("Rows in data", '=COUNT(d_Month)', "N_Rows", "#,##0"),
        ("Rows with a bad month (not the 1st of a month)", "=SUMPRODUCT((d_Month<>\"\")*(DAY(d_Month)<>1))", "N_BadMonth", "0"),
        ("Total NSV in data, CY to date (₹ L)", "=SUMIFS(d_NSV,d_Type,\"<>\"&Est_Crit,d_Month,\">=\"&FYStart,d_Month,\"<=\"&LatestMonth)", "CY_Total", "#,##0.0"),
    ]
    for i, (lab, f, nm, fmt) in enumerate(rows, 3):
        ct.cell(row=i, column=1, value=lab)
        c = ct.cell(row=i, column=2, value=f)
        c.number_format = fmt
        wb.defined_names[nm] = DefinedName(nm, attr_text=f"Control!$B${i}")
        if nm in ("Thr_Fall", "Thr_Grow", "Incl_Est"):
            c.fill = PatternFill("solid", fgColor="FFF2CC")
    ct.column_dimensions["A"].width = 46
    ct.column_dimensions["B"].width = 16

    # ---------- analysis sheets
    d = data
    cyd = cy
    chains = sorted(set(d["Chain"]), key=lambda c: -cyd[cyd["Chain"] == c]["NSV"].sum())
    sheets = {}

    def uniq(colname, extra_ly=False):
        return sorted(set(cyd[colname]), key=lambda v: -cyd[cyd[colname] == v]["NSV"].sum())

    def combos(c1, c2):
        g = cyd.groupby([c1, c2])["NSV"].sum().sort_values(ascending=False)
        return list(g.index)

    note_split = "Last year is loaded at chain level only, so LY and YoY show '–' here until the LY article split is added."
    specs = [
        ("By_Chain", "Offtake by chain: Q1, Q2, QoQ and H1 vs last year", ["Chain"], [(c,) for c in chains], ["d_Chain"], ""),
        ("By_Brand", "Offtake by brand", ["Brand"], [(c,) for c in uniq("Brand")], ["d_Brand"], note_split),
        ("By_Category", "Offtake by category", ["Category"], [(c,) for c in uniq("Category")], ["d_Cat"], note_split),
        ("By_SubCategory", "Offtake by sub-category", ["Sub-category"], [(c,) for c in uniq("Sub-category")], ["d_Sub"], note_split),
        ("By_PackSize", "Offtake by pack size", ["Pack Size"], [(c,) for c in uniq("Pack Size")], ["d_Pack"], note_split),
        ("Chain_x_Brand", "Offtake by chain and brand", ["Chain", "Brand"], combos("Chain", "Brand"), ["d_Chain", "d_Brand"], note_split),
        ("Chain_x_SubCat", "Offtake by chain and sub-category", ["Chain", "Sub-category"], combos("Chain", "Sub-category"), ["d_Chain", "d_Sub"], note_split),
        ("Brand_x_SubCat", "Offtake by brand and sub-category", ["Brand", "Sub-category"], combos("Brand", "Sub-category"), ["d_Brand", "d_Sub"], note_split),
        ("Brand_x_Pack", "Offtake by brand and pack size", ["Brand", "Pack Size"], combos("Brand", "Pack Size"), ["d_Brand", "d_Pack"], note_split),
    ]
    for nm, title, keys, items, kn, note in specs:
        sheets[nm] = analysis_sheet(wb, nm, title, keys, items, kn, note)

    # ---------- Monthly trend
    mo = wb.create_sheet("Monthly")
    mo["A1"] = "Monthly offtake by chain (₹ lakh): this year and last year"
    mo["A1"].font = Font(bold=True, size=14, color=NAVY)
    for blk, (lab, off) in enumerate((("CY", 0), ("LY", -12))):
        r0 = 3 + blk * (len(chains) + 6)
        mo.cell(row=r0, column=1, value=f'="{lab} "&{"CY_Label" if lab == "CY" else "LY_Label"}&" by chain"').font = Font(bold=True, color=NAVY)
        mo.cell(row=r0 + 1, column=1, value="Chain")
        for m in range(12):
            mo.cell(row=r0 + 1, column=2 + m, value=f"=EDATE(FYStart,{m + off})").number_format = "mmm-yy"
        mo.cell(row=r0 + 1, column=14, value="Total")
        hdr(mo, r0 + 1, 1, 14, 22)
        for i, c in enumerate(chains):
            r = r0 + 2 + i
            mo.cell(row=r, column=1, value=c)
            for m in range(12):
                cl = L(2 + m)
                mo.cell(row=r, column=2 + m, value=f"=SUMIFS(d_NSV,d_Chain,$A{r},{TYPE},d_Month,{cl}${r0 + 1})").number_format = "#,##0.0"
            mo.cell(row=r, column=14, value=f"=SUM(B{r}:M{r})").number_format = "#,##0.0"
        rt = r0 + 2 + len(chains)
        mo.cell(row=rt, column=1, value="Total (all rows)").font = Font(bold=True)
        for m in range(12):
            cl = L(2 + m)
            x = mo.cell(row=rt, column=2 + m, value=f"=SUMIFS(d_NSV,{TYPE},d_Month,{cl}${r0 + 1})")
            x.number_format, x.font = "#,##0.0", Font(bold=True)
        mo.cell(row=rt, column=14, value=f"=SUM(B{rt}:M{rt})").number_format = "#,##0.0"
        if blk == 0:
            cy_tot_row, cy_hdr = rt, r0 + 1
        else:
            ly_tot_row, ly_hdr = rt, r0 + 1
    rf = ly_tot_row + 3
    mo.cell(row=rf, column=1, value="Chart feed (month, this year, last year; blank months show #N/A so the line stops)").font = Font(bold=True)
    mo.cell(row=rf + 1, column=1, value="Month")
    mo.cell(row=rf + 2, column=1, value='="CY "&CY_Label')
    mo.cell(row=rf + 3, column=1, value='="LY "&LY_Label')
    for m in range(12):
        cl = L(2 + m)
        mo.cell(row=rf + 1, column=2 + m, value=f'=TEXT({cl}{cy_hdr},"mmm")')
        mo.cell(row=rf + 2, column=2 + m, value=f"=IF({cl}{cy_hdr}>LatestMonth,NA(),{cl}{cy_tot_row})").number_format = "#,##0"
        mo.cell(row=rf + 3, column=2 + m, value=f"=IF(COUNTIFS({TYPE},d_Month,{cl}{ly_hdr})=0,NA(),{cl}{ly_tot_row})").number_format = "#,##0"
    mo.conditional_formatting.add(f"B{rf + 2}:M{rf + 3}", FormulaRule(formula=[f"ISNA(B{rf + 2})"], font=Font(color="FFFFFF")))
    mo.column_dimensions["A"].width = 26
    for c in range(2, 15):
        mo.column_dimensions[L(c)].width = 10
    mo.freeze_panes = "B3"

    # ---------- Dashboard
    db = wb.create_sheet("Dashboard", 1)
    bc, bcol, bfirst, blast, btot = sheets["By_Chain"]
    db["A1"] = '="MT Offtake dashboard: "&CY_Label&" vs "&LY_Label&" (data to "&TEXT(LatestMonth,"mmm-yy")&")"'
    db["A1"].font = Font(bold=True, size=16, color=NAVY)
    db["A2"] = ('="Offtake (chain POS), Brand Counter excluded, ₹ Cr unless stated. Q2 and H1 count loaded months only; LY uses the same months. "&'
                'IF(Incl_Est=1,"INCLUDES an exploratory estimate of ₹"&TEXT(Est_Latest,"#,##0.0")&" L for chains not yet received in "&TEXT(LatestMonth,"mmm-yy")&" (actual ₹"&TEXT(Act_Latest,"#,##0.0")&" L). Switch off on Control.","Actuals only (estimate switched off on Control).")')
    db["A2"].font = Font(italic=True, color="B9770E")
    kp = [
        ("H1 to date, this year (₹ Cr)", f"=By_Chain!{bcol['ch1']}{btot}/100", "#,##0.00"),
        ("H1, same months last year (₹ Cr)", f"=By_Chain!{bcol['lh1']}{btot}/100", "#,##0.00"),
        ("H1 YoY %", f"=By_Chain!{bcol['yh1']}{btot}", "0.0%;[Red]-0.0%"),
        ("Q1 YoY %", f"=By_Chain!{bcol['yq1']}{btot}", "0.0%;[Red]-0.0%"),
        ("Q2 YoY % (same months)", f"=By_Chain!{bcol['yq2']}{btot}", "0.0%;[Red]-0.0%"),
        ("QoQ % (Q2 vs Q1, per month)", f"=By_Chain!{bcol['qoq']}{btot}", "0.0%;[Red]-0.0%"),
        ("LY QoQ % (same quarters)", f"=By_Chain!{bcol['lqoq']}{btot}", "0.0%;[Red]-0.0%"),
        ("Months loaded in H1", "=N_H1", "0"),
    ]
    for i, (lab, f, fmt) in enumerate(kp):
        r, c = 4 + (i // 4) * 3, 1 + (i % 4) * 3
        db.cell(row=r, column=c, value=lab).font = Font(size=9, color="667085")
        x = db.cell(row=r + 1, column=c, value=f)
        x.number_format, x.font = fmt, Font(bold=True, size=18, color=NAVY)
        db.merge_cells(start_row=r + 1, start_column=c, end_row=r + 1, end_column=c + 1)
        db.merge_cells(start_row=r, start_column=c, end_row=r, end_column=c + 1)
    # top 10 chains + movers (from By_Chain rank helpers)
    t0 = 12
    db.cell(row=t0, column=1, value="Top 10 chains by H1 (₹ L)").font = Font(bold=True, color=NAVY)
    for j, h in enumerate(["#", "Chain", "CY H1", "LY H1", "H1 YoY %"], 1):
        db.cell(row=t0 + 1, column=j, value=h)
    hdr(db, t0 + 1, 1, 5, 20)
    rk = lambda key: f"By_Chain!${bcol[key]}${bfirst}:${bcol[key]}${blast}"
    for i in range(1, 11):
        r = t0 + 1 + i
        db.cell(row=r, column=1, value=i)
        db.cell(row=r, column=2, value=f"=INDEX(By_Chain!$A${bfirst}:$A${blast},MATCH($A{r},{rk('r1')},0))")
        for j, key in ((3, "ch1"), (4, "lh1"), (5, "yh1")):
            db.cell(row=r, column=j, value=f"=INDEX({rk(key)},MATCH($A{r},{rk('r1')},0))").number_format = "0.0%;[Red]-0.0%" if key == "yh1" else "#,##0.0"
    m0 = t0 + 14
    for blk, (lab, key) in enumerate((("Top 5 gainers vs LY (H1 change ₹ L)", "r2"), ("Top 5 decliners vs LY (H1 change ₹ L)", "r3"))):
        r0 = m0 + blk * 9
        db.cell(row=r0, column=1, value=lab).font = Font(bold=True, color=NAVY)
        for j, h in enumerate(["#", "Chain", "Change ₹ L", "YoY %", "Suggested action"], 1):
            db.cell(row=r0 + 1, column=j, value=h)
        hdr(db, r0 + 1, 1, 5, 20)
        for i in range(1, 6):
            r = r0 + 1 + i
            db.cell(row=r, column=1, value=i)
            mt = f"MATCH($A{r},{rk(key)},0)"
            db.cell(row=r, column=2, value=f'=IFERROR(INDEX(By_Chain!$A${bfirst}:$A${blast},{mt}),"–")')
            db.cell(row=r, column=3, value=f'=IFERROR(INDEX({rk("dh1")},{mt}),"–")').number_format = "#,##0.0;[Red]-#,##0.0"
            db.cell(row=r, column=4, value=f'=IFERROR(INDEX({rk("yh1")},{mt}),"–")').number_format = "0.0%;[Red]-0.0%"
            db.cell(row=r, column=5, value=f'=IFERROR(INDEX({rk("act")},{mt}),"–")')
    db.column_dimensions["A"].width = 8
    db.column_dimensions["B"].width = 24
    for c in "CD":
        db.column_dimensions[c].width = 14
    db.column_dimensions["E"].width = 54
    for c in "FGHIJKLM":
        db.column_dimensions[c].width = 12
    # charts
    lc = LineChart()
    lc.title, lc.height, lc.width = "Monthly offtake, this year vs last year (₹ L)", 8, 16
    lc.add_data(Reference(mo, min_col=1, max_col=13, min_row=rf + 2, max_row=rf + 3), from_rows=True, titles_from_data=True)
    lc.set_categories(Reference(mo, min_col=2, max_col=13, min_row=rf + 1))
    db.add_chart(lc, "G12")
    bch = BarChart()
    bch.type, bch.title, bch.height, bch.width = "col", "Top 10 chains: H1 this year vs last year (₹ L)", 8, 16
    bch.add_data(Reference(db, min_col=3, max_col=4, min_row=t0 + 1, max_row=t0 + 11), titles_from_data=True)
    bch.set_categories(Reference(db, min_col=2, min_row=t0 + 2, max_row=t0 + 11))
    db.add_chart(bch, "G29")

    # ---------- Insights (four types)
    ins = wb.create_sheet("Insights", 2)
    ins["A1"] = "Insights: what happened, why, what next, what to do (all formulas)"
    ins["A1"].font = Font(bold=True, size=14, color=NAVY)
    T = lambda key: f"By_Chain!{bcol[key]}{btot}"
    top = lambda i, key: f"INDEX(By_Chain!${bcol[key]}${bfirst}:${bcol[key]}${blast},MATCH({i},{rk('r2')},0))"
    nm = lambda rkey, i: f"INDEX(By_Chain!$A${bfirst}:$A${blast},MATCH({i},{rk(rkey)},0))"
    blocks = [
        ("1. DESCRIPTIVE: what happened", [
            f'="H1 to date ("&N_H1&" months): ₹"&TEXT({T("ch1")}/100,"#,##0.0")&" Cr vs ₹"&TEXT({T("lh1")}/100,"#,##0.0")&" Cr last year, "&IF(ISNUMBER({T("yh1")}),TEXT({T("yh1")},"+0.0%;-0.0%"),"–")&"."',
            f'="Q1 YoY "&IF(ISNUMBER({T("yq1")}),TEXT({T("yq1")},"+0.0%;-0.0%"),"–")&"; Q2 YoY (same months) "&IF(ISNUMBER({T("yq2")}),TEXT({T("yq2")},"+0.0%;-0.0%"),"–")&"."',
            f'="QoQ (Q2 vs Q1, per month): "&IF(ISNUMBER({T("qoq")}),TEXT({T("qoq")},"+0.0%;-0.0%"),"–")&"; same quarters last year: "&IF(ISNUMBER({T("lqoq")}),TEXT({T("lqoq")},"+0.0%;-0.0%"),"–")&"."',
        ]),
        ("2. DIAGNOSTIC: why it moved", [
            f'="Biggest gain: "&{nm("r2", 1)}&" (+₹"&TEXT({top(1, "dh1")},"#,##0.0")&" L), then "&{nm("r2", 2)}&" and "&{nm("r2", 3)}&"."',
            f'="Biggest drag: "&{nm("r3", 1)}&" (₹"&TEXT(INDEX({rk("dh1")},MATCH(1,{rk("r3")},0)),"#,##0.0")&" L), then "&{nm("r3", 2)}&" and "&{nm("r3", 3)}&"."',
            f'="Top 2 chains hold "&TEXT((INDEX({rk("ch1")},MATCH(1,{rk("r1")},0))+INDEX({rk("ch1")},MATCH(2,{rk("r1")},0)))/{T("ch1")},"0%")&" of H1 offtake (concentration)."',
            '="Brand, sub-category and pack drivers: see By_Brand, By_SubCategory, By_PackSize. Last year split shows – until the LY article extract is loaded."',
        ]),
        ("3. PREDICTIVE: what could happen next (run-rate view, not a forecast)", [
            f'=IF(N_H1=0,"–","Run-rate H1 if the loaded months continue: ₹"&TEXT({T("ch1")}/N_H1*6/100,"#,##0.0")&" Cr for 6 months (no seasonality applied).")',
            f'=IF(N_H1>=6,"H1 is complete.",IF({T("ch1")}>=SUMIFS(d_NSV,d_Type,"<>"&Est_Crit,d_Month,">="&LY_H1_S,d_Month,"<="&LY_H1_FULL_E),"Already above last year full H1 (Apr–Sep, ₹"&TEXT(SUMIFS(d_NSV,d_Type,"<>"&Est_Crit,d_Month,">="&LY_H1_S,d_Month,"<="&LY_H1_FULL_E)/100,"#,##0.0")&" Cr) with "&(6-N_H1)&" month(s) still to come.","Last year H1 (Apr–Sep) was ₹"&TEXT(SUMIFS(d_NSV,d_Type,"<>"&Est_Crit,d_Month,">="&LY_H1_S,d_Month,"<="&LY_H1_FULL_E)/100,"#,##0.0")&" Cr; to match it the remaining "&(6-N_H1)&" month(s) need ₹"&TEXT((SUMIFS(d_NSV,d_Type,"<>"&Est_Crit,d_Month,">="&LY_H1_S,d_Month,"<="&LY_H1_FULL_E)-{T("ch1")})/(6-N_H1),"#,##0.0")&" L a month."))',
            '="A proper forecast needs an agreed method and monthly history by chain; the FY27 forecast lives on the web dashboard (Demand & S&OP)."',
        ]),
        ("4. PRESCRIPTIVE: what should we do", [
            f'="Fall threshold "&TEXT(Thr_Fall,"0%")&", growth threshold "&TEXT(Thr_Grow,"0%")&" (change on Control). Suggested action per chain is in By_Chain, last column."',
            f'="Decliners to review first: "&{nm("r3", 1)}&", "&{nm("r3", 2)}&", "&{nm("r3", 3)}&". Owner: chain KAM with category and supply planning. Timeline: before next PO cycle."',
            f'="Gainers to protect (fill rate, visibility): "&{nm("r2", 1)}&", "&{nm("r2", 2)}&", "&{nm("r2", 3)}&"."',
        ]),
    ]
    r = 3
    for head, fs in blocks:
        ins.cell(row=r, column=1, value=head).font = HFONT
        ins.cell(row=r, column=1).fill = HFILL
        r += 1
        for f in fs:
            c = ins.cell(row=r, column=1, value=f)
            c.alignment = Alignment(wrap_text=True, vertical="top")
            ins.row_dimensions[r].height = 32
            r += 1
        r += 1
    ins.column_dimensions["A"].width = 150

    # ---------- Pending chains (static snapshot at build time)
    import json
    import re
    pc = wb.create_sheet("Pending_Chains")
    pc["A1"] = "Chains with no rows in the latest month: exploratory estimate (static snapshot at build; the rows themselves are in Offtake_Data with Type = Estimate)"
    pc["A1"].font = Font(bold=True, size=13, color=NAVY)
    try:
        tj = json.loads((ROOT / "config" / "offtake_chain_tracker.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        tj = {"status": {}}
    nz = lambda s: re.sub(r"[^a-z0-9]", "", str(s).lower())
    stat = {nz(k): v for k, v in tj.get("status", {}).items()}
    stat.update({"trends": stat.get("reliancetrends", "")})
    latest_m = date(2026, MON[months[-1]], 1)
    win = [date(2026, MON[m], 1) for m in months[-4:-1]]
    heads = ["Pending chain"] + [w.strftime("%b-%y") + " actual (₹ L)" for w in win] + ["Estimate = L3M average (₹ L)", "Tracker status"]
    for j, h in enumerate(heads, 1):
        pc.cell(row=3, column=j, value=h)
    hdr(pc, 3, 1, len(heads), 34)
    rr = 4
    for c in pending:
        vals = [float(cy[(cy["Chain"] == c) & (cy["Month"] == w)]["NSV"].sum()) for w in win]
        pc.cell(row=rr, column=1, value=c)
        for j, v in enumerate(vals, 2):
            pc.cell(row=rr, column=j, value=round(v, 2)).number_format = "#,##0.00"
        pc.cell(row=rr, column=len(win) + 2, value=round(sum(vals) / len(win), 2)).number_format = "#,##0.00"
        pc.cell(row=rr, column=len(win) + 3, value=stat.get(nz(c), "Not on tracker"))
        rr += 1
    pc.cell(row=rr, column=1, value="Total").font = Font(bold=True)
    for j in range(2, len(win) + 3):
        x = pc.cell(row=rr, column=j, value=f"=SUM({L(j)}4:{L(j)}{rr - 1})")
        x.number_format, x.font = "#,##0.00", Font(bold=True)
    pc.cell(row=rr + 2, column=1, value="Chains that did not sell in a window month count as 0 in that month. Tracker source: Compiled_Sep26_File.xlsb sheet Sheet3. Centro is Azorte (owner, 2026-10-11).")
    pc.column_dimensions["A"].width = 24
    for j in range(2, len(heads) + 1):
        pc.column_dimensions[L(j)].width = 22
    pc.column_dimensions[L(len(heads))].width = 46

    # ---------- Primary vs Offtake (static from dashboard/data.js; Primary is not in Offtake_Data)
    pv = wb.create_sheet("Primary_vs_Offtake")
    pv["A1"] = "Primary vs Offtake (₹ L): Primary is SAP billing, Offtake is chain POS. Different measures: never one growth rate."
    pv["A1"].font = Font(bold=True, size=13, color=NAVY)
    try:
        s_ = (ROOT / "dashboard" / "data.js").read_text(encoding="utf-8")
        DJ = json.loads(s_[s_.index("{"): s_.rindex("}") + 1])
        gap = DJ["primary_offtake_gap"]
    except (OSError, ValueError, KeyError):
        gap = None
    if gap:
        r = 3
        for fy in ("fy26", "fy27"):
            blk = gap.get(fy)
            if not blk:
                continue
            pv.cell(row=r, column=1, value=fy.upper() + " by month (Primary months only)").font = Font(bold=True)
            for j, h in enumerate(["Month", "Primary", "Offtake", "Gap (P − O)", "Primary ÷ Offtake"], 1):
                pv.cell(row=r + 1, column=j, value=h)
            hdr(pv, r + 1, 1, 5, 20)
            for i, row in enumerate(blk["by_month"]["rows"]):
                rw = r + 2 + i
                pv.cell(row=rw, column=1, value=row["month"])
                for j, k in ((2, "primary"), (3, "offtake"), (4, "gap")):
                    pv.cell(row=rw, column=j, value=row[k]).number_format = "#,##0.0;[Red]-#,##0.0"
                pv.cell(row=rw, column=5, value=row["ratio"]).number_format = "0.00"
            r += len(blk["by_month"]["rows"]) + 4
        xo = DJ["offtake"].get("exploratory_fy27")
        pv.cell(row=r, column=1, value="Sep-26 Primary: NOT LOADED. Needs PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Sep_26.csv (SAP billing). Offtake Sep-26 actual ₹ %s L is shown on the other sheets; no Primary comparison for it until the file arrives." % (f"{xo['actual_month_total']:,.1f}" if xo else "–")).font = Font(bold=True, color=RED)
        r += 2
        pv.cell(row=r, column=1, value="FY27 by chain, same months as Primary (Apr–Aug-26). FY27 Primary still includes EB2B/SIS (~5%), Offtake is MT only.").font = Font(bold=True)
        for j, h in enumerate(["Chain", "Primary", "Offtake", "Gap (P − O)", "Primary ÷ Offtake"], 1):
            pv.cell(row=r + 1, column=j, value=h)
        hdr(pv, r + 1, 1, 5, 20)
        for i, row in enumerate(gap["fy27"]["by_chain"]["matched"]):
            rw = r + 2 + i
            pv.cell(row=rw, column=1, value=row["name"])
            for j, k in ((2, "primary"), (3, "offtake"), (4, "gap")):
                pv.cell(row=rw, column=j, value=row[k]).number_format = "#,##0.0;[Red]-#,##0.0"
            pv.cell(row=rw, column=5, value=row["ratio"]).number_format = "0.00"
    pv.column_dimensions["A"].width = 30
    for c in "BCDE":
        pv.column_dimensions[c].width = 16

    # ---------- Power Query option
    pq = wb.create_sheet("PowerQuery_Option")
    pq["A1"] = "Option B: load the monthly store x article CSVs straight into Offtake_Data (paste into Data > Get Data > Blank Query > Advanced Editor). Not tested in Excel."
    pq["A1"].font = Font(bold=True)
    m = ('let\n  Source = Folder.Files("C:\\\\path\\\\to\\\\Offtake_Monthly"),\n'
         '  Csv = Table.SelectRows(Source, each Text.StartsWith([Name], "offtake_store_article_")),\n'
         '  Load = Table.AddColumn(Csv, "T", each Table.PromoteHeaders(Csv.Document([Content], [Delimiter=",", Encoding=65001]))),\n'
         '  Rows = Table.ExpandTableColumn(Load, "T", {"Chain Name","Store Type","Brand","Category","Sub_category","Net Weight","Sales Qty","NSV","Month","Year"}),\n'
         '  NoBC = Table.SelectRows(Rows, each Text.Trim([Store Type]) <> "Brand Counter"),\n'
         '  Typed = Table.TransformColumnTypes(NoBC, {{"NSV", type number}, {"Sales Qty", type number}, {"Year", Int64.Type}}),\n'
         '  Dated = Table.AddColumn(Typed, "MonthDate", each Date.FromText(Text.Start([Month],3) & " 1, " & Text.From([Year]))),\n'
         '  Packed = Table.AddColumn(Dated, "Pack Size", each if [Net Weight] = null or [Net Weight] = "" then "Not stated" else Text.From(Number.From([Net Weight])) & " g/ml"),\n'
         '  Grouped = Table.Group(Packed, {"MonthDate","Chain Name","Brand","Category","Sub_category","Pack Size"}, {{"NSV", each List.Sum([NSV]), type number}, {"Qty", each List.Sum([Sales Qty]), type number}})\n'
         'in\n  Grouped')
    pq["A3"] = m
    pq["A3"].alignment = Alignment(wrap_text=True, vertical="top")
    pq["A4"] = "Chain names in the CSVs have spelling variants (scripts/visit_cities.py CHAIN_STANDARD). Option A (Python) applies them; Option B does not."
    pq.column_dimensions["A"].width = 140
    pq.row_dimensions[3].height = 260

    order = ["README", "Dashboard", "Insights", "Control", "By_Chain", "By_Brand", "By_Category", "By_SubCategory", "By_PackSize", "Chain_x_Brand",
             "Chain_x_SubCat", "Brand_x_SubCat", "Brand_x_Pack", "Monthly", "Pending_Chains", "Primary_vs_Offtake", "Offtake_Data", "PowerQuery_Option"]
    wb._sheets = [wb[n] for n in order]
    wb.active = 1
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    print(f"wrote {out}: data rows {len(data)} (CY {len(cy)}, LY {len(ly)}, estimate {len(est)} for {len(pending)} chains = {est['NSV'].sum():.2f} L), CY actual NSV {cy['NSV'].sum():.2f} L, LY H1 chain-level {ly[ly['Month'].map(lambda x: x.month in (4,5,6,7,8,9))]['NSV'].sum():.2f} L")


if __name__ == "__main__":
    main()
