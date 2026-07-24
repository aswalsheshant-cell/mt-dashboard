"""Skill: schema_validator / build_validator — Phase 4 repository validation.

Structural and consistency checks over code + config + source layout. These are
the checks that catch a defect BEFORE a build runs, as opposed to reconcile.py
which checks numbers AFTER it has run.
"""
from __future__ import annotations

import re

from .core import (ROOT, Finding, fy_months, load_config_csv, load_dash,
                   parse_month_cell, rel)

BUILD_SCRIPT = ROOT / "scripts" / "build_dashboard_data.py"
ARTICLE_DIR = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
OFFTAKE_DIR = ROOT / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"


def _hardcoded_fy(findings: list[Finding]) -> None:
    """THE ONE FY RULE: FY must be derived from month+year, never hardcoded."""
    pat = re.compile(r"""["']fy2[5-9]["']""")
    for py in sorted(ROOT.glob("scripts/*.py")):
        src = py.read_text(encoding="utf-8", errors="replace")
        hits = [(i, l.strip()) for i, l in enumerate(src.splitlines(), 1)
                if pat.search(l) and "fy_tag" not in l and not l.strip().startswith("#")]
        # A handful of literals is normal (dict keys for the pre-agg window);
        # a large count means FY logic was pinned to specific years.
        if len(hits) > 12:
            findings.append(Finding(
                id=f"VAL-FY-HARDCODE-{py.stem}", skill="schema_validator",
                category="fiscal_year", severity="WARN",
                summary=f"{len(hits)} hardcoded FY literals in {py.name}",
                evidence=f"first: line {hits[0][0]}: {hits[0][1][:90]}",
                location=f"{rel(py)}:{hits[0][0]}", owner="Dashboard team",
                remediation="Derive FY via fy_tag_from_ym/fy_tag_from_label so FY28+ appear automatically."))


def _month_coverage(findings: list[Finding]) -> None:
    """Gaps in the monthly source series, per FY, derived not hardcoded."""
    dash = load_dash()
    fy27 = dash.get("detail_meta", {}).get("fyx_primary", {}).get("FY27", {})
    monthly = fy27.get("monthly") or []
    labels = fy_months("fy27")

    have_csv = {p.name for p in ARTICLE_DIR.glob("primary_article_*.csv")}
    for i, lbl in enumerate(labels):
        mon, yy = lbl.split("-")
        nsv = monthly[i] if i < len(monthly) else 0
        csv_name = f"primary_article_{mon}_{yy}.csv"
        if nsv and csv_name not in have_csv:
            findings.append(Finding(
                id=f"VAL-SRC-MISSING-{lbl}", skill="schema_validator",
                category="missing_source", severity="WARN",
                summary=f"{lbl} has NSV in data.js but no article CSV in the repo",
                evidence=f"data.js NSV={nsv} L; expected {csv_name}",
                amount_l=str(nsv), location=rel(ARTICLE_DIR), owner="Sales MIS",
                remediation="Supply the month's article CSV so the figure is recomputable from source."))


def _schema_drift(findings: list[Finding]) -> None:
    """Every article CSV must expose the same critical columns."""
    import csv as _csv
    critical = {"FY", "Month", "brand", "Inv. Net value(LOC)", "Total MRP sales",
                "Chain name", "Zone", "EAN No."}
    baseline: set[str] | None = None
    for p in sorted(ARTICLE_DIR.glob("primary_article_*.csv")):
        with open(p, encoding="latin-1", errors="replace") as fh:
            cols = set(next(_csv.reader(fh), []))
        missing = critical - cols
        if missing:
            findings.append(Finding(
                id=f"VAL-SCHEMA-{p.stem}", skill="schema_validator", category="schema_drift",
                severity="FAIL", summary=f"{p.name} is missing critical columns",
                evidence=f"missing: {sorted(missing)}", location=rel(p), owner="Sales MIS",
                remediation="Re-export with the standard column set."))
        if baseline is None:
            baseline = cols
        elif cols != baseline:
            added, dropped = cols - baseline, baseline - cols
            findings.append(Finding(
                id=f"VAL-DRIFT-{p.stem}", skill="schema_validator", category="schema_drift",
                severity="INFO", summary=f"{p.name} column set differs from the first file scanned",
                evidence=f"+{sorted(added)[:4]} -{sorted(dropped)[:4]}",
                location=rel(p), owner="Sales MIS",
                remediation="Confirm the difference is intentional."))


def _mixed_schema_guard(findings: list[Finding]) -> None:
    """Regression guard for the Reliance column-shift class of defect: a CSV
    whose month column does not parse as a month on every row."""
    import csv as _csv
    SAMPLE = 5000
    for p in sorted(OFFTAKE_DIR.glob("*.csv")):
        if p.name.startswith("_"):
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            rdr = _csv.DictReader(fh)
            cols = [c for c in (rdr.fieldnames or []) if c and "month" in c.lower()]
            if not cols:
                continue
            # Prefer the canonical label column; a 'Revised Month' column
            # legitimately carries Excel serials and is not the month of record.
            col = next((c for c in cols if c.strip().lower() in ("month", "month_std")), cols[0])
            bad, seen = [], 0
            for row in rdr:
                if seen >= SAMPLE:
                    break
                seen += 1
                if parse_month_cell(row.get(col)) is None:
                    bad.append(seen)
        if bad:
            # A minority of unparseable rows is the mixed-schema signature; a
            # wholesale failure usually means the wrong column was inspected.
            share = len(bad) / max(seen, 1) * 100
            findings.append(Finding(
                id=f"VAL-MIXEDSCHEMA-{p.stem}", skill="schema_validator",
                category="mixed_schema", severity="FAIL" if share < 100 else "WARN",
                summary=f"{p.name}: {len(bad)} of {seen} sampled rows have an unparseable month",
                evidence=f"column {col!r} ({share:.1f}% of sample) -- possible column shift; "
                         f"first bad row #{bad[0]}",
                location=rel(p), owner="Trade Marketing",
                remediation="Validate column alignment before aggregating; quarantine ambiguous rows."))


def _config_integrity(findings: list[Finding]) -> None:
    """Governed configs must be internally consistent."""
    tax = load_config_csv("cm2_expense_taxonomy.csv")
    rules = load_config_csv("cm2_allocation_rules.csv")
    formula = load_config_csv("cm2_formula.csv")

    if not tax or not rules or not formula:
        findings.append(Finding(
            id="VAL-CFG-MISSING", skill="schema_validator", category="governance",
            severity="FAIL", summary="One or more CM2 governance configs are missing",
            evidence=f"taxonomy={len(tax)} rules={len(rules)} formula={len(formula)}",
            location="config/", owner="Finance",
            remediation="Restore the governed configs; the CM2 engine cannot run without them."))
        return

    rule_ids = {r["Allocation_Rule_ID"] for r in rules}
    for t in tax:
        rid = t.get("Allocation_Rule_ID", "")
        if rid and rid not in rule_ids:
            findings.append(Finding(
                id=f"VAL-CFG-ORPHANRULE-{rid}", skill="schema_validator",
                category="governance", severity="FAIL",
                summary=f"Taxonomy references unknown allocation rule {rid}",
                evidence=f"expense head {t.get('Normalized_Expense_Head')!r}",
                location="config/cm2_expense_taxonomy.csv", owner="Finance",
                remediation="Add the rule to cm2_allocation_rules.csv or repoint the head."))

    # An INCLUDE head must not depend on a rule that is not APPROVED.
    status = {r["Allocation_Rule_ID"]: r.get("Status", "") for r in rules}
    for t in tax:
        if t.get("CM2_Inclusion_Status") == "INCLUDE" and status.get(
                t.get("Allocation_Rule_ID", ""), "") != "APPROVED":
            findings.append(Finding(
                id=f"VAL-CFG-DRAFTRULE-{t.get('Normalized_Expense_Head')}",
                skill="schema_validator", category="governance", severity="BLOCKED",
                summary=f"Head '{t.get('Normalized_Expense_Head')}' is INCLUDE but its rule is not APPROVED",
                evidence=f"rule {t.get('Allocation_Rule_ID')} status={status.get(t.get('Allocation_Rule_ID'))}",
                location="config/cm2_expense_taxonomy.csv", owner="Finance",
                remediation="Approve the rule or revert the head to PENDING_APPROVAL."))

    # No formula component may default silently to NSV.
    for f in formula:
        if not (f.get("Calculation_Basis") or "").strip():
            findings.append(Finding(
                id=f"VAL-CFG-NOBASIS-{f.get('Component','?')[:20]}", skill="schema_validator",
                category="unit_basis", severity="FAIL",
                summary=f"Formula component '{f.get('Component')}' has no explicit Calculation_Basis",
                location="config/cm2_formula.csv", owner="Finance",
                remediation="Set an explicit basis; a blank one risks silently defaulting to NSV."))


def run() -> list[Finding]:
    findings: list[Finding] = []
    _hardcoded_fy(findings)
    _month_coverage(findings)
    _schema_drift(findings)
    _mixed_schema_guard(findings)
    _config_integrity(findings)
    if not findings:
        findings.append(Finding(id="VAL-OK", skill="schema_validator",
                                category="validation", severity="PASS",
                                summary="All repository validation checks passed"))
    return findings
