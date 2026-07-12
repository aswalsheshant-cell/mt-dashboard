import tempfile
import unittest
from pathlib import Path

from mtagent.pq_checks import _let_bindings, validate_file, validate_paths
from mtagent.dax_validator import strip_comments_and_strings

REPO = Path(__file__).resolve().parents[2]
PQ_DIR = REPO / "PowerBI" / "PowerQuery"

GOOD = """\
let
    Source = fnCombineFolder(pRootFolder & "\\RawDataFolders\\Offtake_Monthly", 0),
    Typed = Table.TransformColumnTypes(Source, {{"NSV", type number}}),
    Cleaned = Table.SelectRows(Typed, each [NSV] <> null)
in
    Cleaned
"""


def _tmp(content: str) -> Path:
    f = tempfile.NamedTemporaryFile("w", suffix=".pq", delete=False,
                                    encoding="utf-8")
    f.write(content)
    f.close()
    return Path(f.name)


class TestLetBindings(unittest.TestCase):
    def test_steps_and_result(self):
        cleaned, _ = strip_comments_and_strings(GOOD)
        steps, result = _let_bindings(cleaned)
        self.assertEqual([s for s, _ in steps], ["Source", "Typed", "Cleaned"])
        self.assertEqual(result, "Cleaned")

    def test_quoted_step_names(self):
        text = 'let\n    #"My Step" = 1,\n    Next = #"My Step" + 1\nin\n    Next'
        cleaned, _ = strip_comments_and_strings(text, keep_hash_identifiers=True)
        steps, result = _let_bindings(cleaned)
        self.assertEqual([s for s, _ in steps], ['#"My Step"', "Next"])
        self.assertEqual(result, "Next")

    def test_nested_records_not_mistaken_for_steps(self):
        text = ('let\n    Source = Csv.Document(File.Contents("x"),'
                '[Delimiter=",", Encoding=65001])\nin\n    Source')
        cleaned, _ = strip_comments_and_strings(text, keep_hash_identifiers=True)
        steps, _ = _let_bindings(cleaned)
        self.assertEqual([s for s, _ in steps], ["Source"])


class TestChecks(unittest.TestCase):
    def test_good_file_clean(self):
        findings = validate_file(_tmp(GOOD))
        self.assertEqual([f for f in findings if f.severity == "error"], [])

    def test_missing_let(self):
        findings = validate_file(_tmp('Table.FromRows({})'))
        self.assertTrue(any(f.code == "PQ001" for f in findings))

    def test_parameter_query_exempt_from_let(self):
        findings = validate_file(_tmp(
            '"C:\\MT" meta [IsParameterQuery=true, Type="Text"]'))
        self.assertFalse(any(f.code in ("PQ001", "PQ005") for f in findings))

    def test_unbalanced(self):
        findings = validate_file(_tmp("let\n    A = Table.X((1)\nin\n    A"))
        self.assertTrue(any(f.code == "PQ002" for f in findings))

    def test_in_result_undefined(self):
        findings = validate_file(_tmp("let\n    A = 1\nin\n    B"))
        self.assertTrue(any(f.code == "PQ003" for f in findings))

    def test_dead_step(self):
        findings = validate_file(_tmp("let\n    A = 1,\n    B = 2\nin\n    B"))
        self.assertTrue(any(f.code == "PQ004" for f in findings))

    def test_hardcoded_path(self):
        findings = validate_file(_tmp(
            'let\n    S = File.Contents("C:\\data\\x.csv")\nin\n    S'))
        self.assertTrue(any(f.code == "PQ005" for f in findings))

    def test_proot_path_not_flagged(self):
        findings = validate_file(_tmp(GOOD))
        self.assertFalse(any(f.code == "PQ005" for f in findings))


class TestOnRealRepoFiles(unittest.TestCase):
    def test_no_errors_in_repo_queries(self):
        findings = validate_paths(sorted(PQ_DIR.glob("*.pq")), REPO)
        errors = [f for f in findings if f.severity == "error"]
        self.assertEqual(errors, [], [f.format() for f in errors])

    def test_gitignored_xlsx_source_not_flagged_missing(self):
        findings = validate_paths([PQ_DIR / "41_DistContWeights.pq"], REPO)
        self.assertFalse(any(f.code == "PQ006" and ".xlsx" in f.message
                             for f in findings))


if __name__ == "__main__":
    unittest.main()
