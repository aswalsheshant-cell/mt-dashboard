import tempfile
import unittest
from pathlib import Path

from mtagent.dax_validator import (check_balance, extract_definitions,
                                   strip_comments_and_strings, validate_file,
                                   validate_paths)
from mtagent.metadata import ModelInventory

REPO = Path(__file__).resolve().parents[2]
DAX_DIR = REPO / "PowerBI" / "DAX"

GOOD = """\
// a comment with ( unbalanced and "quotes
Total NSV = SUM ( 'Fact Offtake Sales'[Offtake NSV] )
Growth % =
VAR cur = [Total NSV]
VAR prev = CALCULATE ( [Total NSV], DATEADD ( 'Date Table'[Date], -1, MONTH ) )
RETURN DIVIDE ( cur - prev, prev )
"""


def _tmp(content: str) -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=".dax", delete=False,
                                    encoding="utf-8")
    f.write(content)
    f.close()
    return Path(f.name)


class TestLexer(unittest.TestCase):
    def test_comments_and_strings_removed(self):
        cleaned, lits = strip_comments_and_strings(
            'X = "a (string" // trailing ( comment\nY = 1')
        self.assertNotIn("string", cleaned)
        self.assertNotIn("comment", cleaned)
        self.assertEqual(lits, [(1, '"a (string"')])
        self.assertEqual(cleaned.count("("), 0)

    def test_escaped_quotes(self):
        cleaned, lits = strip_comments_and_strings('X = "say ""hi"" now" & Y')
        self.assertEqual(len(lits), 1)
        self.assertIn("& Y", cleaned)


class TestBalance(unittest.TestCase):
    def test_good(self):
        cleaned, _ = strip_comments_and_strings(GOOD)
        self.assertEqual(check_balance(cleaned, "x"), [])

    def test_unclosed(self):
        f = check_balance("A = SUM ( T[c]", "x")
        self.assertEqual(len(f), 1)
        self.assertEqual(f[0].code, "DAX001")

    def test_mismatched(self):
        f = check_balance("A = SUM ( T[c) ]", "x")
        self.assertEqual(f[0].code, "DAX001")


class TestDefinitions(unittest.TestCase):
    def test_extracts_names(self):
        cleaned, _ = strip_comments_and_strings(GOOD)
        names = [d.name for d in extract_definitions(cleaned, "x")]
        self.assertEqual(names, ["Total NSV", "Growth %"])

    def test_var_and_return_are_not_definitions(self):
        cleaned, _ = strip_comments_and_strings(GOOD)
        names = [d.name for d in extract_definitions(cleaned, "x")]
        self.assertNotIn("VAR cur", names)
        self.assertTrue(all(not n.lower().startswith(("var ", "return")) for n in names))

    def test_real_core_measures_found(self):
        text = (DAX_DIR / "01_CoreMeasures.dax").read_text(encoding="utf-8-sig")
        cleaned, _ = strip_comments_and_strings(text)
        names = {d.name for d in extract_definitions(cleaned, "x")}
        for expected in ("Total Offtake NSV", "NSV", "MoM Growth %",
                         "YoY Growth %", "Contribution %"):
            self.assertIn(expected, names)


class TestChecks(unittest.TestCase):
    def test_duplicate_across_files(self):
        a, b = _tmp("Dup X = 1 + 1"), _tmp("Dup X = 2 + 2")
        findings = validate_paths([a, b])
        self.assertTrue(any(f.code == "DAX002" for f in findings))

    def test_unknown_table_flagged(self):
        inv = ModelInventory(tables={"Fact Offtake Sales"}, source="docs")
        p = _tmp("M = SUM ( 'No Such Table'[c] )")
        findings = validate_file(p, inv)
        self.assertTrue(any(f.code == "DAX003" for f in findings))

    def test_known_table_not_flagged(self):
        inv = ModelInventory(tables={"Fact Offtake Sales"}, source="docs")
        p = _tmp("M = SUM ( 'Fact Offtake Sales'[c] )")
        findings = validate_file(p, inv)
        self.assertFalse(any(f.code == "DAX003" for f in findings))

    def test_raw_division_info(self):
        findings = validate_file(_tmp("M = [A] / [B]"))
        self.assertTrue(any(f.code == "DAX004" for f in findings))

    def test_divide_not_flagged(self):
        findings = validate_file(_tmp("M = DIVIDE ( [A], [B] )"))
        self.assertFalse(any(f.code == "DAX004" for f in findings))

    def test_hardcoded_fy_literal(self):
        findings = validate_file(_tmp('M = CALCULATE ( [X], T[FY Year] = "25-26" )'))
        self.assertTrue(any(f.code == "DAX005" for f in findings))


class TestOnRealRepoFiles(unittest.TestCase):
    """The repo's own DAX corpus is the regression fixture."""

    def test_no_new_errors(self):
        from mtagent.evalrun import KNOWN_DAX_ERRORS, _allowlisted
        from mtagent.metadata import load_inventory
        inv = load_inventory(REPO / "agent" / "metadata", REPO)
        findings = validate_paths(sorted(DAX_DIR.glob("*.dax")), inv)
        errors = [f for f in findings if f.severity == "error" and not _allowlisted(f)]
        self.assertEqual(errors, [], [f.format() for f in errors])

    def test_known_duplicate_still_detected(self):
        # 'QC Mapping Coverage %' is genuinely defined twice (08_ vs 09_) —
        # the validator must keep catching it until the repo fixes it.
        findings = validate_paths(sorted(DAX_DIR.glob("*.dax")))
        self.assertTrue(any(f.code == "DAX002" and "QC Mapping Coverage %" in f.message
                            for f in findings))


if __name__ == "__main__":
    unittest.main()
