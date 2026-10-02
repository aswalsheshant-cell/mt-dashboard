"""Reliance Brand Counter rule: Offtake only, never Primary (CLAUDE.md safeguard).

Primary is gross billing (FY26 Rs 32,900.36 L). Brand Counter rows are removed
from Offtake only, because counter POS is already inside the Reliance totals.
If the same filter leaks into Primary, gross NSV drops and the baseline breaks.

Until now only a JS test (not run in CI) touched this. This test reads the
build script source with `ast` (no pandas import) and checks:
  1. load_primary_v2 has no Brand Counter filter.
  2. The offtake loaders still have it (the rule was not removed by mistake).
  3. data.js still carries a real Reliance Retail Primary figure.
"""
import ast
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BUILD = REPO / "scripts" / "build_dashboard_data.py"
DATA_JS = REPO / "dashboard" / "data.js"

# Text the offtake counter filter is written with (see build_dashboard_data.py).
COUNTER_MARKERS = ("brand counter", "_is_bc")
OFFTAKE_LOADERS = ("offtake_block", "patch_offtake_new_months", "offtake_rebuild_block")


def _function_sources():
    text = BUILD.read_text(encoding="utf-8")
    tree = ast.parse(text)
    return {
        n.name: (ast.get_source_segment(text, n) or "")
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef)
    }


class PrimaryKeepsRelianceCounter(unittest.TestCase):
    def test_load_primary_v2_has_no_counter_filter(self):
        src = _function_sources().get("load_primary_v2")
        self.assertTrue(src, "load_primary_v2 not found in build_dashboard_data.py")
        low = src.lower()
        for marker in COUNTER_MARKERS:
            self.assertNotIn(
                marker, low,
                f"load_primary_v2 contains '{marker}': Brand Counter exclusion must "
                "never apply to Primary (aggregate ALL Reliance invoices).")

    def test_offtake_path_still_excludes_counter(self):
        funcs = _function_sources()
        hits = [n for n in OFFTAKE_LOADERS
                if n in funcs and any(m in funcs[n].lower() for m in COUNTER_MARKERS)]
        # The filter also lives inside the loader helpers the blocks call, so
        # fall back to the whole file if none of the named wrappers carry it.
        whole = BUILD.read_text(encoding="utf-8").lower()
        self.assertTrue(
            hits or all(m in whole for m in COUNTER_MARKERS),
            "Offtake Brand Counter exclusion not found: the deduplication rule was removed.")

    def test_datajs_reliance_primary_is_present_and_positive(self):
        text = DATA_JS.read_text(encoding="utf-8")
        d = json.loads(text[text.index("{"): text.rindex("}") + 1])
        chains = {c["name"]: c for c in d["primary"]["by_chain"]}
        self.assertIn("Reliance Retail", chains)
        self.assertGreater(chains["Reliance Retail"].get("fy26") or 0, 0)


if __name__ == "__main__":
    unittest.main()
