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
from openpyxl.utils import get_column_letter

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
                   "tblWoA": 67, "tblAchievement": 51, "tblCalc": 51,
                   "tblExceptions": 87}


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

    def test_every_woa_register_row_is_visible_in_exceptions(self):
        """QC-WOA-EXC-01. 08_Exceptions used to filter WoA rows down to just
        OWNER_ROW_EXCEPTION/SOURCE_DATA_FIX_REQUIRED, silently dropping every
        INSUFFICIENT_EVIDENCE and OWNER_RULE_APPROVAL row from the one sheet
        meant to be the complete list of what's open (36 of 67 rows in the
        FY27 run). Assert the control sheet's WoA-mapping rows and the
        05_WoA_Mapping table agree on both count and the set of raw names --
        a key-set check catches a swap that a count-only check would miss.
        """
        woa_ws, woa_cols = self.tables["tblWoA"]
        exc_ws, exc_cols = self.tables["tblExceptions"]
        _, woa_hdr, _ = table_of(woa_ws)
        _, exc_hdr, _ = table_of(exc_ws)

        woa_names = {
            row[woa_cols["WoA_Raw_Name"]].value
            for row in woa_ws.iter_rows(min_row=woa_hdr + 1)
        }
        exc_names = {
            row[exc_cols["Item"]].value
            for row in exc_ws.iter_rows(min_row=exc_hdr + 1)
            if row[exc_cols["Area"]].value == "WoA mapping"
        }
        self.assertEqual(len(woa_names), 67)
        self.assertEqual(woa_names, exc_names)

    def test_basup01_scope_gate_covers_every_ba_supervisor_row(self):
        """BA Supervisor is not a role category in 01_Employee_Master -- that's
        a business-scope question (BASUP-01), not a name-matching defect, so
        it must never be silently folded into an ordinary identity exception.
        """
        exc_ws, exc_cols = self.tables["tblExceptions"]
        _, exc_hdr, _ = table_of(exc_ws)
        gated = [
            row for row in exc_ws.iter_rows(min_row=exc_hdr + 1)
            if row[exc_cols["Area"]].value == "WoA mapping"
            and "BASUP-01" in (row[exc_cols["Exception_Type"]].value or "")
        ]
        self.assertEqual(len(gated), 29)

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

    # ---- manual-entry status columns are a governed list, not free text ----
    STATUS_VALIDATIONS = {
        "05_WoA_Mapping": ("Approval_Status", {"PENDING", "APPROVED", "REJECTED"}),
        "08_Exceptions": ("Status", {"OPEN", "RESOLVED", "NOT_APPLICABLE"}),
        "09_Finance_Approval": ("Payout_Status", {"PENDING", "APPROVED", "REJECTED", "NOT_APPLICABLE"}),
        "12_Rule_Decisions": ("Status", {"ASSUMED", "CONFLICT", "MISSING", "OPEN", "CONFIRMED"}),
    }

    def test_manual_status_columns_carry_a_governed_dropdown(self):
        for sheet_name, (col_name, choices) in self.STATUS_VALIDATIONS.items():
            ws = self.wb[sheet_name]
            t, hdr, cols = table_of(ws)
            dvs = list(ws.data_validations.dataValidation)
            self.assertEqual(len(dvs), 1, f"{sheet_name} should carry exactly one governed dropdown")
            dv = dvs[0]
            self.assertEqual(dv.type, "list")
            got_choices = set(dv.formula1.strip('"').split(","))
            self.assertEqual(got_choices, choices, f"{sheet_name}!{col_name} dropdown list mismatch")
            letter = get_column_letter(cols[col_name])
            self.assertIn(f"{letter}{hdr + 1}", str(dv.sqref),
                          f"{sheet_name} dropdown must start at the first data row, not the header")

    def test_status_dropdowns_never_reach_formula_or_read_only_sheets(self):
        """Only a column a human actually types into gets a dropdown -- a
        formula-driven or generated-only sheet (e.g. tblCalc, tblAchievement,
        tblControl) must carry none."""
        untouched = ["00_Control", "01_Employee_Master", "02_Incentive_Criteria",
                     "03_Targets", "04_Actuals", "06_Achievement", "07_Incentive_Calc",
                     "10_Summary", "11_Data_Quality", "13_Target_Scope"]
        for sheet_name in untouched:
            ws = self.wb[sheet_name]
            self.assertEqual(len(ws.data_validations.dataValidation), 0,
                              f"{sheet_name} should carry no data validation")


if __name__ == "__main__":
    unittest.main()


class SafeMissingSchemaBehavior(unittest.TestCase):
    """A source file that exists but doesn't match the expected schema must fail
    with a named reason -- never a raw StopIteration, never a partial/misleading
    output. This is the matrix-vs-flattened-slab failure mode found during
    Windows acceptance: a real business workbook, wrong shape for this parser.
    """

    @staticmethod
    def _matrix_fixture(tmp_path):
        wb = openpyxl.Workbook(); wb.remove(wb.active)
        ws = wb.create_sheet("Sales Team")
        ws.append([None] * 4)
        ws.append([None] * 4)
        ws.append([None, None, "Slab", "BDO", "BDE", "Sr BDE"])
        ws.append([None, None, "90% to 105%", 7200, 9000, 13300])
        p = tmp_path / "matrix_slab.xlsx"
        wb.save(p)
        return p

    def test_matrix_shaped_slab_file_fails_cleanly(self):
        import sys, tempfile
        from pathlib import Path as _P
        sys.path.insert(0, str(REPO / "scripts"))
        from build_incentive_workbook import read_slabs
        with tempfile.TemporaryDirectory() as td:
            fixture = self._matrix_fixture(_P(td))
            with self.assertRaises(SystemExit) as cm:
                read_slabs(fixture)
            msg = str(cm.exception)
            self.assertIn("Designation", msg)
            self.assertIn(str(fixture), msg)
            self.assertNotIn("Traceback", msg)

    def test_missing_header_never_raises_bare_stopiteration(self):
        """The failure mode this whole test class exists to prevent."""
        import sys, tempfile
        from pathlib import Path as _P
        sys.path.insert(0, str(REPO / "scripts"))
        from build_incentive_workbook import read_slabs, read_employees, read_targets
        with tempfile.TemporaryDirectory() as td:
            fixture = self._matrix_fixture(_P(td))
            for fn in (read_slabs, read_employees):
                try:
                    fn(fixture)
                    self.fail(f"{fn.__name__} should have raised")
                except StopIteration:
                    self.fail(f"{fn.__name__} leaked a raw StopIteration")
                except SystemExit:
                    pass  # the correct, actionable failure


class QcWoaExc01(unittest.TestCase):
    """QC-WOA-EXC-01's failure path, tested directly against the pure
    function -- proves the check actually catches a missing/duplicate/extra
    key, not just that today's real data happens to satisfy it (that's
    IncentiveWorkbook.test_every_woa_register_row_is_visible_in_exceptions,
    the positive case).
    """

    @staticmethod
    def _qc():
        import sys
        sys.path.insert(0, str(REPO / "scripts"))
        from build_incentive_workbook import qc_woa_exc_01
        return qc_woa_exc_01

    def test_passes_on_identical_key_sets(self):
        qc_woa_exc_01 = self._qc()
        keys = [("RKAM", "Dimple", "North"), ("SO Name", "Suraj Jha", "East")]
        result = qc_woa_exc_01(keys, list(keys))
        self.assertTrue(result["ok"])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["extra"], [])

    def test_catches_a_row_silently_dropped(self):
        """The exact bug this QC exists to prevent: 08_Exceptions used to
        drop INSUFFICIENT_EVIDENCE rows entirely."""
        qc_woa_exc_01 = self._qc()
        woa = [("RKAM", "Dimple", "North"), ("SO Name", "Suraj Jha", "East")]
        exc = [("RKAM", "Dimple", "North")]  # second row missing
        result = qc_woa_exc_01(woa, exc)
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing"], [("SO Name", "Suraj Jha", "East")])
        self.assertEqual(result["extra"], [])

    def test_catches_a_swap_same_total_count(self):
        """The failure mode a count-only check (67 == 67) would miss: one
        row dropped, a different one double-counted, net count unchanged."""
        qc_woa_exc_01 = self._qc()
        woa = [("RKAM", "Dimple", "North"), ("SO Name", "Suraj Jha", "East")]
        exc = [("RKAM", "Dimple", "North"), ("RKAM", "Dimple", "North")]
        result = qc_woa_exc_01(woa, exc)
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing"], [("SO Name", "Suraj Jha", "East")])
        self.assertEqual(result["extra"], [])
        self.assertEqual(result["exc_dupes"], [("RKAM", "Dimple", "North")])

    def test_catches_an_extra_key_not_in_register(self):
        qc_woa_exc_01 = self._qc()
        woa = [("RKAM", "Dimple", "North")]
        exc = [("RKAM", "Dimple", "North"), ("BA Lead", "Ghost Row", "West")]
        result = qc_woa_exc_01(woa, exc)
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["extra"], [("BA Lead", "Ghost Row", "West")])

    def test_catches_a_duplicate_in_the_register_itself(self):
        qc_woa_exc_01 = self._qc()
        woa = [("RKAM", "Dimple", "North"), ("RKAM", "Dimple", "North")]
        exc = [("RKAM", "Dimple", "North")]
        result = qc_woa_exc_01(woa, exc)
        self.assertFalse(result["ok"])
        self.assertEqual(result["woa_dupes"], [("RKAM", "Dimple", "North")])
