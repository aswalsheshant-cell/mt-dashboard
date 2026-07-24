"""Skill: finance_governance — Phase 6.

Enforces that no business assumption reaches production without an approved,
evidenced decision. This engine is deliberately strict: it treats an approval
lacking an approver, a date or evidence as not an approval at all.
"""
from __future__ import annotations

from .core import Finding, load_config_csv

REQUIRED_ON_APPROVAL = ("approved_option", "approved_by", "approved_at", "evidence_reference")
VALID_STATUS = {"APPROVED", "PENDING_APPROVAL", "REJECTED", "SUPERSEDED"}


def run() -> tuple[list[dict], list[Finding]]:
    reg = load_config_csv("cm2_decision_register.csv")
    findings: list[Finding] = []

    if not reg:
        return [], [Finding(
            id="GOV-NOREGISTER", skill="finance_governance", category="governance",
            severity="BLOCKED", summary="No decision register found",
            location="config/cm2_decision_register.csv", owner="Finance",
            remediation="Create config/cm2_decision_register.csv before any CM2 change.")]

    for r in reg:
        did = r.get("decision_id", "?")
        status = (r.get("status") or "").strip().upper()

        if status not in VALID_STATUS:
            findings.append(Finding(
                id=f"GOV-BADSTATUS-{did}", skill="finance_governance", category="governance",
                severity="FAIL", summary=f"{did} has invalid status {status!r}",
                evidence=f"allowed: {sorted(VALID_STATUS)}",
                location="config/cm2_decision_register.csv", owner="Finance",
                remediation="Use one of the allowed status values."))
            continue

        if status == "APPROVED":
            gaps = [f for f in REQUIRED_ON_APPROVAL if not (r.get(f) or "").strip()]
            if gaps:
                findings.append(Finding(
                    id=f"GOV-WEAKAPPROVAL-{did}", skill="finance_governance",
                    category="governance", severity="FAIL",
                    summary=f"{did} is APPROVED but missing {', '.join(gaps)}",
                    evidence=f"decision: {(r.get('decision') or '')[:90]}",
                    location="config/cm2_decision_register.csv", owner="Finance",
                    decision_ref=did,
                    remediation="An approval without approver, date and evidence is not an approval."))
            else:
                findings.append(Finding(
                    id=f"GOV-APPROVED-{did}", skill="finance_governance",
                    category="governance", severity="PASS",
                    summary=f"{did} approved by {r.get('approved_by')} on {r.get('approved_at')}",
                    evidence=(r.get("evidence_reference") or "")[:120],
                    amount_l="", decision_ref=did))
        else:
            findings.append(Finding(
                id=f"GOV-PENDING-{did}", skill="finance_governance", category="governance",
                severity="WARN" if status == "PENDING_APPROVAL" else "INFO",
                summary=f"{did} {status}: {(r.get('decision') or '')[:80]}",
                evidence=f"safe default in force: {(r.get('recommended_safe_default') or '')[:80]}",
                amount_l="", location="config/cm2_decision_register.csv",
                owner=r.get("owner", "Finance"), decision_ref=did,
                remediation="Blocks any production use of the affected component."))

    # Gate: formula must not be presented as final while DRAFT.
    formula = load_config_csv("cm2_formula.csv")
    if formula and any((f.get("Status") or "").upper() == "DRAFT" for f in formula):
        findings.append(Finding(
            id="GOV-FORMULA-DRAFT", skill="finance_governance", category="governance",
            severity="BLOCKED",
            summary="CM2 formula is DRAFT -- every CM2 figure must be labelled provisional",
            evidence=f"{sum(1 for f in formula if (f.get('Status') or '').upper()=='DRAFT')}"
                     f"/{len(formula)} components DRAFT",
            location="config/cm2_formula.csv", owner="Finance", decision_ref="D1",
            remediation="Display 'CM2 PROVISIONAL — FORMULA APPROVAL PENDING'; do not publish as final."))

    rows = [{"Decision_ID": r.get("decision_id"), "Status": r.get("status"),
             "Decision": (r.get("decision") or "")[:120], "Owner": r.get("owner"),
             "Amount_Affected": r.get("amount_affected"),
             "Approved_By": r.get("approved_by"), "Approved_At": r.get("approved_at"),
             "Evidence": (r.get("evidence_reference") or "")[:160]} for r in reg]
    return rows, findings


def production_gate() -> tuple[bool, list[str]]:
    """May anything be published right now? Returns (allowed, blocking reasons)."""
    _, findings = run()
    blockers = [f"{f.id}: {f.summary}" for f in findings if f.severity in ("BLOCKED", "FAIL")]
    return (not blockers), blockers
