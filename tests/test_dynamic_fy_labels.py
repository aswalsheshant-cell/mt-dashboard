"""FY27+ must flow without code edits (CLAUDE.md "THE ONE FY RULE").

1. primary_offtake_gap_block builds one window per FY found in fyx_primary,
   so an FY28 article-level Primary feed gets its own fy28 window and FY27 is
   untouched. (Used to read only the 'FY27' key.)
2. Power BI: the "YY-YY" FY text is typed in ONE place (TY FY Label /
   Baseline FY Label in 03_Forecast_Measures.dax); no other measure may
   hardcode it.
"""
import copy
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
import build_dashboard_data as b  # noqa: E402

DAX_DIR = REPO / "PowerBI" / "DAX"


def _inputs():
    primary = {"monthly_fy26": [10.0, 20.0],
               "by_chain": [{"name": "A", "fy26": 30.0}]}
    offtake = {"monthly_fy26": [9.0, 18.0], "months_fy26": ["Apr-25", "May-25"],
               "monthly_fy27": [5.0], "months_fy27": ["Apr-26"],
               "monthly_fy28": [7.0], "months_fy28": ["Apr-27"],
               "by_chain": [{"name": "A", "fy26": 27.0, "fy27": 5.0, "fy28": 7.0}]}
    fyx = {"FY27": {"monthly_canon": [6.0], "months_canon": ["Apr-26"],
                    "by_chain": [{"name": "A", "nsv": 6.0}]},
           "FY28": {"monthly_canon": [8.0], "months_canon": ["Apr-27"],
                    "by_chain": [{"name": "A", "nsv": 8.0}]}}
    return primary, offtake, fyx


class GapBlockDynamicFY(unittest.TestCase):
    def test_every_fy_in_fyx_gets_a_window(self):
        r = b.primary_offtake_gap_block(*_inputs())
        self.assertEqual({"fy26", "fy27", "fy28", "note"}, set(r))
        self.assertEqual(r["fy28"]["by_month"]["rows"][0]["gap"], 1.0)
        self.assertEqual(r["fy27"]["by_month"]["rows"][0]["gap"], 1.0)

    def test_fy27_unchanged_when_fy28_added(self):
        p, o, fyx = _inputs()
        only27 = b.primary_offtake_gap_block(p, o, {"FY27": fyx["FY27"]})
        both = b.primary_offtake_gap_block(p, o, fyx)
        self.assertEqual(only27["fy27"], both["fy27"])
        self.assertNotIn("fy28", only27)

    def test_no_offtake_for_fy_means_no_window(self):
        p, o, fyx = _inputs()
        o = copy.deepcopy(o)
        del o["monthly_fy28"]
        self.assertNotIn("fy28", b.primary_offtake_gap_block(p, o, fyx))


class DaxFyTextTypedOnce(unittest.TestCase):
    def test_fy_text_only_in_label_measures(self):
        pat = re.compile(r'"\d{2}-\d{2}"')
        offenders = []
        for f in sorted(DAX_DIR.glob("*.dax")):
            for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                code = line.split("//")[0]
                if pat.search(code) and not re.match(r"\s*(TY|Baseline) FY Label\s*=", code):
                    offenders.append(f"{f.name}:{n}: {line.strip()[:90]}")
        self.assertEqual([], offenders,
                         "FY text must come from [TY FY Label] / [Baseline FY Label]")


if __name__ == "__main__":
    unittest.main()
