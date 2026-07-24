"""Seed Manager — governed seed validation, listing and hash verification.

Governed seeds carry authoritative values from uncommittable source workbooks.
Only rows with Status=AUTHORITATIVE are used in production. Every row must carry
a Source_SHA256 so the source workbook can be identified if it reappears.

CLI:
    python3 -m scripts.dataeng.cli seed validate   # validate all seeds
    python3 -m scripts.dataeng.cli seed list        # list seeds with status
    python3 -m scripts.dataeng.cli seed resolve <metric> <month>  # resolve one value
    python3 -m scripts.dataeng.cli seed verify-hash <file>        # recheck a SHA256
"""
from __future__ import annotations

import csv
import hashlib
import pathlib

from .core import ROOT, Finding, rel

SEED_DIR = ROOT / "PowerBI" / "SeedData" / "Masters"

GOVERNED_SEEDS: list[dict] = [
    {
        "name": "FY27 Monthly GMV/MRP",
        "file": SEED_DIR / "FY27_Monthly_GMV_MRP.csv",
        "key_col": "Month",
        "value_col": "GMV_MRP_Sales_L",
        "control_col": "NSV_Control_L",
        "required_cols": {
            "Month", "GMV_MRP_Sales_L", "NSV_Control_L",
            "Source_File", "Source_SHA256", "Extraction_Rule",
            "Recorded_By", "Recorded_At", "Status",
        },
        "description": "Authoritative GMV/MRP for months where no article CSV exists.",
    },
]


def _load_seed(seed: dict) -> list[dict]:
    p: pathlib.Path = seed["file"]
    if not p.exists():
        return []
    with open(p, encoding="utf-8", errors="replace") as fh:
        return list(csv.DictReader(fh))


def _check_required_cols(seed: dict, rows: list[dict], findings: list[Finding]) -> bool:
    if not rows:
        findings.append(Finding(
            id=f"SEED-EMPTY-{seed['file'].stem}", skill="seed_manager",
            category="seed_integrity", severity="FAIL",
            summary=f"Seed '{seed['name']}' is empty or missing",
            location=rel(seed["file"]), owner="Data Engineering",
            remediation="Restore the seed file from version control."))
        return False
    actual = set(rows[0].keys())
    missing = seed["required_cols"] - actual
    if missing:
        findings.append(Finding(
            id=f"SEED-COLS-{seed['file'].stem}", skill="seed_manager",
            category="seed_integrity", severity="FAIL",
            summary=f"Seed '{seed['name']}' missing required columns: {sorted(missing)}",
            evidence=f"present: {sorted(actual)[:8]}",
            location=rel(seed["file"]), owner="Data Engineering",
            remediation="Re-export with the full governed column set."))
        return False
    return True


def _check_status(seed: dict, rows: list[dict], findings: list[Finding]) -> None:
    for i, row in enumerate(rows, 1):
        status = (row.get("Status") or "").strip().upper()
        key = row.get(seed["key_col"], f"row{i}")
        if status not in ("AUTHORITATIVE", "DRAFT", "SUPERSEDED", "REJECTED"):
            findings.append(Finding(
                id=f"SEED-BADSTATUS-{seed['file'].stem}-{key}", skill="seed_manager",
                category="seed_integrity", severity="FAIL",
                summary=f"Seed row {key!r} has unknown status {status!r}",
                location=rel(seed["file"]), owner="Data Engineering",
                remediation="Use AUTHORITATIVE / DRAFT / SUPERSEDED / REJECTED."))
        elif status == "DRAFT":
            findings.append(Finding(
                id=f"SEED-DRAFT-{seed['file'].stem}-{key}", skill="seed_manager",
                category="seed_integrity", severity="WARN",
                summary=f"Seed row {key!r} is DRAFT — not usable in production",
                location=rel(seed["file"]), owner="Data Engineering",
                remediation="Approve the row or mark REJECTED."))


def _check_sha_present(seed: dict, rows: list[dict], findings: list[Finding]) -> None:
    for row in rows:
        key = row.get(seed["key_col"], "?")
        sha = (row.get("Source_SHA256") or "").strip()
        if not sha:
            findings.append(Finding(
                id=f"SEED-NOSHA-{seed['file'].stem}-{key}", skill="seed_manager",
                category="seed_integrity", severity="FAIL",
                summary=f"Seed row {key!r} has no Source_SHA256 — source workbook unidentifiable",
                location=rel(seed["file"]), owner="Data Engineering",
                remediation="Record the SHA256 of the source workbook."))
        elif len(sha) != 64 or not all(c in "0123456789abcdef" for c in sha.lower()):
            findings.append(Finding(
                id=f"SEED-BADSHA-{seed['file'].stem}-{key}", skill="seed_manager",
                category="seed_integrity", severity="WARN",
                summary=f"Seed row {key!r} SHA256 appears malformed (length={len(sha)})",
                location=rel(seed["file"]), owner="Data Engineering",
                remediation="Re-record the full 64-character SHA256 hex digest."))


def _check_control_total(seed: dict, rows: list[dict], findings: list[Finding]) -> None:
    """NSV control total must be present on every AUTHORITATIVE row."""
    ctrl_col = seed.get("control_col")
    if not ctrl_col:
        return
    for row in rows:
        if (row.get("Status") or "").upper() != "AUTHORITATIVE":
            continue
        key = row.get(seed["key_col"], "?")
        ctrl = (row.get(ctrl_col) or "").strip()
        if not ctrl:
            findings.append(Finding(
                id=f"SEED-NOCTRL-{seed['file'].stem}-{key}", skill="seed_manager",
                category="seed_integrity", severity="WARN",
                summary=f"AUTHORITATIVE seed row {key!r} has no {ctrl_col}",
                location=rel(seed["file"]), owner="Data Engineering",
                remediation="Record the NSV control total to verify the extraction independently."))


def validate() -> list[Finding]:
    findings: list[Finding] = []
    for seed in GOVERNED_SEEDS:
        rows = _load_seed(seed)
        if not _check_required_cols(seed, rows, findings):
            continue
        _check_status(seed, rows, findings)
        _check_sha_present(seed, rows, findings)
        _check_control_total(seed, rows, findings)
        auth_n = sum(1 for r in rows if (r.get("Status") or "").upper() == "AUTHORITATIVE")
        findings.append(Finding(
            id=f"SEED-OK-{seed['file'].stem}", skill="seed_manager",
            category="seed_integrity",
            severity="PASS" if auth_n > 0 else "WARN",
            summary=f"Seed '{seed['name']}': {auth_n}/{len(rows)} rows AUTHORITATIVE",
            location=rel(seed["file"]), owner="Data Engineering"))
    return findings


def list_seeds() -> list[dict]:
    rows_out = []
    for seed in GOVERNED_SEEDS:
        rows = _load_seed(seed)
        for row in rows:
            key = row.get(seed["key_col"], "?")
            val = row.get(seed["value_col"], "")
            ctrl = row.get(seed.get("control_col", ""), "")
            rows_out.append({
                "Seed": seed["name"],
                "Key": key,
                "Value": val,
                "Control": ctrl,
                "Status": row.get("Status", ""),
                "Source_File": row.get("Source_File", ""),
                "Recorded_At": row.get("Recorded_At", ""),
                "Recorded_By": row.get("Recorded_By", ""),
                "SHA256_prefix": (row.get("Source_SHA256") or "")[:12],
            })
    return rows_out


def resolve(metric: str, month: str) -> tuple[str | None, str]:
    """Return (value, status) for the given metric and month from AUTHORITATIVE rows only."""
    for seed in GOVERNED_SEEDS:
        if metric.lower() not in seed["name"].lower():
            continue
        rows = _load_seed(seed)
        for row in rows:
            if row.get(seed["key_col"], "").strip() == month.strip():
                status = (row.get("Status") or "").upper()
                if status == "AUTHORITATIVE":
                    return row.get(seed["value_col"]), "AUTHORITATIVE"
                return None, status
    return None, "NOT_FOUND"


def verify_hash(source_path: str) -> tuple[str, bool | None]:
    """Return (sha256_hex, matched) — matched is None if no baseline SHA to compare."""
    p = pathlib.Path(source_path)
    if not p.exists():
        return "", None
    sha = hashlib.sha256(p.read_bytes()).hexdigest()
    for seed in GOVERNED_SEEDS:
        rows = _load_seed(seed)
        for row in rows:
            recorded = (row.get("Source_SHA256") or "").strip().lower()
            if recorded and recorded == sha:
                return sha, True
            if row.get("Source_File", "") in source_path and recorded:
                return sha, sha == recorded
    return sha, None
