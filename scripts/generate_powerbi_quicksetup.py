#!/usr/bin/env python3
"""
Regenerate the "missing sections" tail of PowerBI/QuickSetup/AllPowerQuery_Consolidated.txt
and AllDAX_Consolidated.txt so every file under PowerBI/PowerQuery/ and PowerBI/DAX/ is
represented in the fast-path reference, and fix the stale total counts in each file's
own preamble/step numbering.

Why this exists: PowerBI/PowerQuery/42-46 and PowerBI/DAX/14-15 were added after the
consolidated files were last hand-assembled, so a build following PBIX_Build_Guide.md's
"use QuickSetup for a faster paste-in" path would silently skip Pack Size Buckets,
Secondary Sales Efficiency, Fact Secondary Sales, Fact Claim Master, Dim Promo Calendar,
Secondary Sales Measures and Promo Measures. This script appends the missing sections
(preserving every existing hand-curated section byte-for-byte) and corrects the "STEP
n/25" style counters so the file's own numbering is accurate again.

Usage: python3 scripts/generate_powerbi_quicksetup.py [--check]
  --check   exit 1 if the consolidated files are NOT already in sync (used in CI/local
            verification); makes no changes.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PQ_DIR = ROOT / "PowerBI" / "PowerQuery"
DAX_DIR = ROOT / "PowerBI" / "DAX"
PQ_CONSOLIDATED = ROOT / "PowerBI" / "QuickSetup" / "AllPowerQuery_Consolidated.txt"
DAX_CONSOLIDATED = ROOT / "PowerBI" / "QuickSetup" / "AllDAX_Consolidated.txt"

STEP_RE = re.compile(r"# STEP (\d+)/(\d+)\s+--\s+SOURCE FILE:\s+(\S+)")


def sorted_source_files(directory: Path, suffix: str) -> list[Path]:
    return sorted(directory.glob(f"*{suffix}"), key=lambda p: p.name)


def present_in_consolidated(consolidated_text: str) -> set[str]:
    return {m.group(3) for m in STEP_RE.finditer(consolidated_text)}


def query_display_name(pq_text: str, fallback: str) -> str:
    m = re.search(r"//\s*QUERY:\s*(.+)", pq_text)
    if m:
        return m.group(1).strip()
    m = re.search(r"Power Query:\s*(.+)", pq_text)
    if m:
        return m.group(1).strip()
    return fallback


def build_missing_sections(files: list[Path], start_step: int, total: int, kind: str) -> str:
    out = []
    for i, f in enumerate(files):
        step = start_step + i
        text = f.read_text(encoding="utf-8")
        name = query_display_name(text, f.stem)
        out.append("#" * 78)
        out.append(f"# STEP {step}/{total}  --  SOURCE FILE: {f.name}")
        out.append(f"# RENAME {'QUERY' if kind == 'pq' else 'MEASURE GROUP'} TO: {name}")
        out.append(
            "# NOTE: added by scripts/generate_powerbi_quicksetup.py -- see the file's own "
            "header comment below for source/grain/dependency detail; not independently "
            "re-verified against a live Power BI session."
        )
        out.append("#" * 78)
        out.append(text.rstrip("\n"))
        out.append("")
    return "\n".join(out) + "\n"


def renumber_totals(text: str, old_total: int, new_total: int) -> str:
    """Rewrite only the '/<old_total>' inside actual '# STEP n/<old_total> --' header
    lines to '/<new_total>' -- never a blind find/replace, so an unrelated number
    elsewhere in the file (a percentage, a fraction in a business-logic comment) can
    never be touched."""

    def _sub(m: "re.Match[str]") -> str:
        step, total, fname = m.group(1), m.group(2), m.group(3)
        if int(total) != old_total:
            return m.group(0)
        return f"# STEP {step}/{new_total}  --  SOURCE FILE: {fname}"

    return STEP_RE.sub(_sub, text)


def main() -> int:
    check_only = "--check" in sys.argv

    pq_files = sorted_source_files(PQ_DIR, ".pq")
    dax_files = sorted_source_files(DAX_DIR, ".dax")

    pq_text = PQ_CONSOLIDATED.read_text(encoding="utf-8")
    dax_text = DAX_CONSOLIDATED.read_text(encoding="utf-8")

    pq_present = present_in_consolidated(pq_text)
    dax_present = present_in_consolidated(dax_text)

    missing_pq = [f for f in pq_files if f.name not in pq_present]
    missing_dax = [f for f in dax_files if f.name not in dax_present]

    if check_only:
        problems = []
        if missing_pq:
            problems.append(f"AllPowerQuery_Consolidated.txt missing: {[f.name for f in missing_pq]}")
        if missing_dax:
            problems.append(f"AllDAX_Consolidated.txt missing: {[f.name for f in missing_dax]}")
        if problems:
            for p in problems:
                print(f"OUT OF SYNC: {p}")
            return 1
        print(f"OK: {len(pq_files)} PQ files and {len(dax_files)} DAX files all represented in QuickSetup.")
        return 0

    if missing_pq:
        old_total = len(pq_files) - len(missing_pq)
        new_total = len(pq_files)
        pq_text = renumber_totals(pq_text, old_total, new_total)
        pq_text = pq_text.rstrip("\n") + "\n\n" + build_missing_sections(
            missing_pq, start_step=old_total + 1, total=new_total, kind="pq"
        )
        PQ_CONSOLIDATED.write_text(pq_text, encoding="utf-8")
        print(f"Appended {len(missing_pq)} PQ section(s): {[f.name for f in missing_pq]}")

    if missing_dax:
        old_total = len(dax_files) - len(missing_dax)
        new_total = len(dax_files)
        dax_text = renumber_totals(dax_text, old_total, new_total)
        dax_text = dax_text.rstrip("\n") + "\n\n" + build_missing_sections(
            missing_dax, start_step=old_total + 1, total=new_total, kind="dax"
        )
        DAX_CONSOLIDATED.write_text(dax_text, encoding="utf-8")
        print(f"Appended {len(missing_dax)} DAX section(s): {[f.name for f in missing_dax]}")

    if not missing_pq and not missing_dax:
        print("Already in sync -- no changes made.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
