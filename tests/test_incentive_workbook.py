"""Validate the governed incentive workbook.

The workbook itself is RESTRICTED and gitignored, so these tests skip when it has
not been generated. Regenerate with scripts/build_incentive_workbook.py.

No spreadsheet engine is available in CI (libreoffice-core ships without the Calc
filter), so formulas are checked by resolving them statically: every function name
must exist in the Excel baseline the office actually runs, every structured
reference must resolve to a real table and column, and no column may depend on
itself.
"""
import re
import unittest
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parent.parent
WB_PATH = REPO / "incentive_working" / "MT_Incentive_Working_FY27.xlsx"

SHEETS = ["00_Control", "01_Employee_Master", "02_Incentive_Criteria", "03_Targets",
          "04_Actuals", "05_WoA_Mapping", "06_Achievement", "07_Incentive_Calc",
          "08_Exceptions", "09_Finance_Approval", "10_Summary", "11_Data_Quality",
          "12_Rule_Decisions", "13_Target_Scope"]

# Functions available in Excel 2016 / 2019 too. XLOOKUP, LET, FILTER and friends are
# Microsoft-365-only and would show #NAME? on an older office build.
ALLOWED_FUNCS = {"IF", "IFERROR", "INDEX", "MATCH", "SUMIFS", "COUNTIFS", "COUNTA",
                 "OR", "AND", "LEFT", "ROUND"}

EXPECTED_COUNTS = {"tblEmployee": 51, "tblSlab": 85, "tblTarget": 3124,
                   "tblWoA": 67, "tblAchievement": 51, "tblCalc": 51}


def load():
    return openpyxl.load_workbook(WB_PATH)


def table_of(ws):
    """The sheet's table, its header row, and {column name: 1-based index}.

    Sheets that carry a note start their header at row 3, not row 1, so the header
    row is read from the table ref rather than assumed.
    """
    t = next(iter(ws.tables.values()))
    hdr = int(re.sub(r"[A-Z]", "", t.ref.split(":")[0]))
    return t, hdr, {c.name: i + 1 for i, c in enumerate(t.tableColumns)}


@unittest.skipUnless(WB_PATH.exists(), f"{WB_PATH.name} not generated")
class IncentiveWorkbook(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.wb = load()
        cls.tables = {}          # table name -> (worksheet, {column header: index})
        cls.rowcount = {}
        for ws in cls.wb.worksheets:
            for t in ws.tables.values():
                cls.tables[t.displayName] = (ws, {c.name: i for i, c in enumerate(t.tableColumns)})
                a, b = t.ref.split(":")
                cls.rowcount[t.displayName] = int(re.sub(r"[A-Z]", "", b)) - int(re.sub(r"[A-Z]", "", a))

    # ---- structure --------------------------------------------------------
    def test_opens_with_all_sheets(self):
        self.assertEqual(self.wb.sheetnames, SHEETS)

    def test_every_sheet_has_exactly_one_table(self):
        for ws in self.wb.worksheets:
            self.assertEqual(len(ws.tables), 1, f"{ws.title} has {len(ws.tables)} tables")

    def test_table_row_counts_reconcile_with_sources(self):
        for name, n in EXPECTED_COUNTS.items():
            self.assertIn(name, self.tables)
            self.assertEqual(self.rowcount[name], n, f"{name} row count")

    # ---- formulas ---------------------------------------------------------
    def _formulas(self):
        for ws in self.wb.worksheets:
            tname = next(iter(ws.tables))
            for row in ws.iter_rows():
                for cell in row:
                    if isinstance(cell.value, str) and cell.value.startswith("="):
                        yield ws, tname, cell

    def test_formulas_use_only_widely_available_functions(self):
        for ws, _, cell in self._formulas():
            for fn in re.findall(r"([A-Z][A-Z0-9.]*)\s*\(", cell.value):
                self.assertIn(fn, ALLOWED_FUNCS, f"{ws.title}!{cell.coordinate} uses {fn}")

    def test_structured_references_resolve(self):
        for ws, tname, cell in self._formulas():
            own = self.tables[tname][1]
            for col in re.findall(r"\[@\[([^\]]+)\]\]", cell.value):
                self.assertIn(col, own, f"{ws.title}!{cell.coordinate} -> [@[{col}]]")
            for tbl, col in re.findall(r"\b(tbl[A-Za-z]+)\[([^@\]]+)\]", cell.value):
                self.assertIn(tbl, self.tables, f"{ws.title}!{cell.coordinate} -> {tbl}")
                self.assertIn(col, self.tables[tbl][1], f"{ws.title}!{cell.coordinate} -> {tbl}[{col}]")

    def test_no_column_depends_on_itself(self):
        for ws, tname, cell in self._formulas():
            headers = list(self.tables[tname][1])
            own = headers[cell.column - 1]
            self.assertNotIn(f"[@[{own}]]", cell.value,
                             f"{ws.title}!{cell.coordinate} ({own}) is circular")

    def test_formulas_are_balanced(self):
        for ws, _, cell in self._formulas():
            self.assertEqual(cell.value.count("("), cell.value.count(")"),
                             f"{ws.title}!{cell.coordinate} unbalanced")
            self.assertEqual(cell.value.count('"') % 2, 0,
                             f"{ws.title}!{cell.coordinate} unbalanced quotes")

    def test_no_stale_error_values_were_written(self):
        for ws in self.wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                for v in row:
                    if isinstance(v, str):
                        self.assertNotIn("#REF!", v, ws.title)
                        self.assertNotIn("#VALUE!", v, ws.title)
                        self.assertNotIn("#NAME?", v, ws.title)

    # ---- governance -------------------------------------------------------
    def test_no_payout_amount_is_produced(self):
        ws = self.wb["07_Incentive_Calc"]
        _, hdr, cols = table_of(ws)
        col = cols["Final_Calculated_Amount"]
        for r in range(hdr + 1, ws.max_row + 1):
            self.assertIn(ws.cell(r, col).value, ("", None),
                          f"07_Incentive_Calc!row {r} carries a payout")

    def test_calculation_status_is_blocked(self):
        ws = self.wb["00_Control"]
        _, hdr, _ = table_of(ws)
        items = {ws.cell(r, 1).value: ws.cell(r, 2).value for r in range(hdr + 1, ws.max_row + 1)}
        self.assertEqual(items.get("Calculation status"), "BLOCKED")
        self.assertEqual(items.get("Approved WoA identities"), 0)
        self.assertEqual(items.get("Target_Scope_Status"), "UNKNOWN_SCOPE")
        self.assertEqual(items.get("Rule version"), "PENDING")

    def test_approval_sheet_is_empty_not_zero_filled(self):
        ws = self.wb["09_Finance_Approval"]
        _, hdr, _ = table_of(ws)
        body = [v for row in ws.iter_rows(min_row=hdr + 1, values_only=True) for v in row]
        self.assertTrue(all(v is None for v in body), "09_Finance_Approval was pre-filled")

    def test_actuals_are_loaded(self):
        ws = self.wb["04_Actuals"]
        _, hdr, cols = table_of(ws)
        n = sum(1 for r in range(hdr + 1, ws.max_row + 1) if ws.cell(r, cols["Month"]).value)
        self.assertGreater(n, 0, "04_Actuals should carry the attribution layer")

    def test_no_credit_without_an_approved_identity(self):
        """The whole point of the layer: a candidate must never be paid as approved."""
        ws = self.wb["04_Actuals"]
        _, hdr, cols = table_of(ws)
        for r in range(hdr + 1, ws.max_row + 1):
            emp = ws.cell(r, cols["Employee_ID"]).value
            cred = ws.cell(r, cols["Credited_Actual"]).value
            if not emp:
                self.assertIn(cred, ("", None), f"04_Actuals row {r} credits an unapproved identity")

    def test_unattributed_value_is_classified_not_dropped(self):
        ws = self.wb["04_Actuals"]
        _, hdr, cols = table_of(ws)
        allowed = {"ATTRIBUTED", "UNATTRIBUTED_PENDING_APPROVAL", "AMBIGUOUS_IDENTITY",
                   "INVALID_SOURCE_PERSON", "SOURCE_POPULATION_MISSING"}
        for r in range(hdr + 1, ws.max_row + 1):
            if ws.cell(r, cols["Month"]).value:
                self.assertIn(ws.cell(r, cols["Mapping_Status"]).value, allowed, f"row {r}")

    def test_readiness_names_the_failing_gate(self):
        """KA-15: a generic BLOCKED sends the request to nobody."""
        ws = self.wb["06_Achievement"]
        _, hdr, cols = table_of(ws)
        f = ws.cell(hdr + 1, cols["Readiness"]).value
        for gate in ("GRADE_BLOCKED", "IDENTITY_BLOCKED", "TARGET_BLOCKED",
                     "RULE_BLOCKED", "READY_TO_CALCULATE"):
            self.assertIn(gate, f)

    def test_target_scope_sheet_reports_the_unexplained_residual(self):
        ws = self.wb["13_Target_Scope"]
        _, hdr, cols = table_of(ws)
        dims = [ws.cell(r, cols["Dimension"]).value for r in range(hdr + 1, ws.max_row + 1)]
        self.assertTrue(any("unexplained residual" in str(d) for d in dims),
                        "the residual must be stated, never absorbed (KA-16)")

    def test_grade_counts_reconcile(self):
        ws = self.wb["01_Employee_Master"]
        _, hdr, cols = table_of(ws)
        vals = [ws.cell(r, cols["Grade_Status"]).value for r in range(hdr + 1, ws.max_row + 1)]
        self.assertEqual(vals.count("VALID"), 42)
        self.assertEqual(len(vals) - vals.count("VALID"), 9)

    def test_every_unusable_grade_has_an_exception_row(self):
        emp = self.wb["01_Employee_Master"]
        _, ehdr, ecols = table_of(emp)
        bad = {emp.cell(r, ecols["Employee_ID"]).value
               for r in range(ehdr + 1, emp.max_row + 1)
               if emp.cell(r, ecols["Grade_Status"]).value not in (None, "VALID")}
        exc = self.wb["08_Exceptions"]
        _, xhdr, xcols = table_of(exc)
        listed = {exc.cell(r, xcols["Item"]).value
                  for r in range(xhdr + 1, exc.max_row + 1)
                  if exc.cell(r, xcols["Area"]).value == "Grade"}
        self.assertEqual(bad, listed)

    def test_target_rows_carry_project_month_labels(self):
        ws = self.wb["03_Targets"]
        _, hdr, cols = table_of(ws)
        vals = {ws.cell(r, cols["Month"]).value for r in range(hdr + 1, ws.max_row + 1)}
        self.assertTrue(vals)
        for v in vals:
            self.assertRegex(v, r"^[A-Z][a-z]{2}-\d{2}$", "month label must read like Apr-26")

    def test_workbook_stays_outside_the_published_dashboard(self):
        self.assertFalse(list((REPO / "dashboard").glob("*Incentive*")))
        self.assertFalse(list((REPO / "dashboard").glob("*.xlsx")))


if __name__ == "__main__":
    unittest.main()
