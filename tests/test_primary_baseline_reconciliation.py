"""Every documented Primary NSV figure must match the month window it covers
(rebuild of old PR #136 on main 370cdf3).

Found 2026-09-26: docs/DATA_LINEAGE.md and config/data_source_registry.yml both
cited scripts/reconcile_primary_baseline.py as their evidence, but that script
existed only on the unmerged #136 branch. PowerBI/docs/Desktop_Assembly_Checklist.md
Phase J told a Desktop user to expect "Grand total ... Rs46,560.34 L" with no month
window -- true only for the Apr'25-Jun'26 files; the folder now holds 17 months
(Rs55,139.95 L). The old #136 script grouped by the source's raw FY label, which
spells FY27 two ways, and explained figures as "grand total minus one month",
which stops working as soon as a second month lands.

The source files are tracked in git (PowerBI/RawDataFolders/Primary_Article_Monthly/),
so this runs in the required gate and reads the same files the docs describe.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import reconcile_primary_baseline as rpb  # noqa: E402

ROWS = rpb.month_totals()


def test_every_documented_figure_matches_its_month_window():
    bad = [x for x in rpb.reconcile(ROWS) if not x["ok"]]
    assert bad == [], bad


def test_every_file_fy_label_agrees_with_its_month():
    bad = [(r["file"], r["fy"], r["source_fy_labels"]) for r in ROWS if not r["labels_agree"]]
    assert bad == [], bad


def test_fy26_matches_the_governed_baseline():
    fy26 = sum(r["nsv"] for r in ROWS if r["fy"] == "FY26")
    assert abs(fy26 - 32900.36) <= rpb.TOLERANCE_L, fy26


def test_a_wrong_figure_or_a_missing_month_is_caught(monkeypatch):
    """Mutation checks: the reconciliation must fail closed, not explain anything away."""
    label, where, s, e, v = rpb.DOCUMENTED_FIGURES[0]
    monkeypatch.setattr(rpb, "DOCUMENTED_FIGURES", [(label, where, s, e, v + 1.0)])
    assert not rpb.reconcile(ROWS)[0]["ok"]
    monkeypatch.setattr(rpb, "DOCUMENTED_FIGURES", [(label, where, s, e, v)])
    gap = [r for r in ROWS if r["ym"] != (2025, 8)]
    res = rpb.reconcile(gap)[0]
    assert not res["ok"] and res["missing_months"] == [(2025, 8)]


def test_docs_cite_only_scripts_that_exist():
    for doc in ("docs/DATA_LINEAGE.md", "config/data_source_registry.yml",
                "PowerBI/docs/Desktop_Assembly_Checklist.md"):
        text = (ROOT / doc).read_text(encoding="utf-8")
        missing = sorted({s for s in re.findall(r"scripts/[A-Za-z0-9_/.-]+\.py", text) if not (ROOT / s).exists()})
        assert missing == [], f"{doc} cites scripts that do not exist: {missing}"


def test_checklist_total_names_its_month_window():
    text = (ROOT / "PowerBI/docs/Desktop_Assembly_Checklist.md").read_text(encoding="utf-8")
    line = next(ln for ln in text.splitlines() if "46,560.34" in ln and "Grand total" in ln)
    assert "Apr'25–Jun'26" in line, line
