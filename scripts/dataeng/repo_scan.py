"""Skill: repository_scan — Phase 1 repository intelligence.

Classifies every tracked file by role (authoritative / generated / reference /
seed / code / doc / artifact) and builds the dependency edges between them.
Classification is evidence-based: a file is 'generated' only because something
in the repo demonstrably writes it, not because of its name.
"""
from __future__ import annotations

import pathlib
import re

from .core import ROOT, Finding, git, rel

# role  <- (path globs, why). Order matters: first match wins.
ROLE_RULES: list[tuple[str, tuple[str, ...], str]] = [
    ("generated", ("dashboard/data.js",),
     "written by scripts/build_dashboard_data.py; header says DO NOT hand-edit"),
    ("generated", ("outputs/**",),
     "staging outputs produced by scripts/"),
    ("authoritative", ("PowerBI/RawDataFolders/**",),
     "raw monthly source extracts -- the ground truth for primary/offtake"),
    ("seed", ("PowerBI/SeedData/**",),
     "small governed seed/master tables, hand-maintained under approval"),
    ("config", ("config/**",),
     "governed business configuration (taxonomy, rules, formula, decisions)"),
    ("reference", ("PowerBI/Excluded_Data/**",),
     "preserved excluded-brand records; must never enter an aggregation"),
    ("code", ("scripts/**",), "transformation and build code"),
    ("powerbi", ("PowerBI/PowerQuery/**", "PowerBI/DAX/**", "PowerBI/QuickSetup/**",
                 "PowerBI/templates/**", "PowerBI/theme/**"),
     "Power BI build kit -- M queries, DAX measures, templates"),
    ("app", ("dashboard/**",), "offline dashboard app and vendored libs"),
    ("doc", ("**/*.md", "**/*.txt", "PowerBI/docs/**"), "documentation"),
    ("test", ("tests/**",), "automated tests"),
    ("agent", (".claude/**",), "agent/skill definitions"),
    ("artifact", ("**/*.pptx", "**/*.pbix"), "binary deliverable"),
]

# Files a build script demonstrably writes, discovered by scanning for writes.
WRITE_HINTS = re.compile(
    r"""(?:open\(\s*|to_csv\(\s*|write_text\(|\bout\b\s*=\s*)["']?([\w./\-]+\.(?:js|csv|json))""")


def _match(path: str, globs: tuple[str, ...]) -> bool:
    p = pathlib.PurePath(path)
    return any(p.match(g) or path.startswith(g.rstrip("*").rstrip("/") + "/")
               for g in globs)


def classify(path: str) -> tuple[str, str]:
    for role, globs, why in ROLE_RULES:
        if _match(path, globs):
            return role, why
    return "unclassified", "no rule matched"


def scan() -> tuple[list[dict], list[dict], list[Finding]]:
    """Returns (inventory, edges, findings)."""
    findings: list[Finding] = []
    tracked = [f for f in git("ls-files").splitlines() if f]

    inventory = []
    for f in tracked:
        p = ROOT / f
        if not p.exists():
            continue
        role, why = classify(f)
        size = p.stat().st_size
        inventory.append({
            "path": f, "role": role, "rationale": why,
            "ext": p.suffix.lstrip(".").lower(), "size_bytes": size,
            "size_h": f"{size/1e6:.1f}MB" if size > 1e6 else f"{size//1024}KB",
            "last_commit": git("log", "-1", "--format=%h %ad", "--date=short", "--", f),
        })
        if role == "unclassified":
            findings.append(Finding(
                id=f"SCAN-UNCLASSIFIED-{len(findings)+1:03d}", skill="repository_scan",
                category="inventory", severity="INFO",
                summary=f"File has no classification rule: {f}",
                location=f, remediation="Add a rule to ROLE_RULES or confirm the file is obsolete."))

    # Dependency edges: which script writes / reads which data file.
    edges = []
    for f in tracked:
        if not f.endswith(".py"):
            continue
        try:
            src = (ROOT / f).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for target in set(WRITE_HINTS.findall(src)):
            for cand in tracked:
                if cand.endswith(target.lstrip("./")):
                    edges.append({"from": f, "to": cand, "kind": "writes"})
        for cand in tracked:
            base = pathlib.PurePath(cand).name
            if base and base in src and cand != f and not cand.endswith(".py"):
                edges.append({"from": cand, "to": f, "kind": "read_by"})

    # de-dup
    seen, uniq = set(), []
    for e in edges:
        k = (e["from"], e["to"], e["kind"])
        if k not in seen:
            seen.add(k)
            uniq.append(e)

    # Dead-code signal: a script nothing references and that writes nothing tracked.
    referenced = {e["to"] for e in uniq} | {e["from"] for e in uniq}
    all_text = "\n".join(
        (ROOT / f).read_text(encoding="utf-8", errors="replace")
        for f in tracked if f.endswith((".py", ".md", ".txt", ".json")) and (ROOT / f).exists())
    for row in inventory:
        f = row["path"]
        if row["role"] != "code" or not f.endswith(".py"):
            continue
        name = pathlib.PurePath(f).name
        mentions = all_text.count(name)
        if mentions <= 1 and f not in referenced:
            findings.append(Finding(
                id=f"SCAN-ORPHAN-{name}", skill="repository_scan", category="dead_code",
                severity="INFO",
                summary=f"Script is not referenced anywhere and writes no tracked file: {f}",
                evidence=f"filename appears {mentions}x across tracked text files",
                location=f, owner="Dashboard team",
                remediation="Confirm it is a one-off migration, then archive or document it."))

    by_role: dict[str, int] = {}
    for r in inventory:
        by_role[r["role"]] = by_role.get(r["role"], 0) + 1
    findings.append(Finding(
        id="SCAN-SUMMARY", skill="repository_scan", category="inventory", severity="PASS",
        summary=f"Scanned {len(inventory)} tracked files across {len(by_role)} roles",
        evidence="; ".join(f"{k}={v}" for k, v in sorted(by_role.items()))))

    return inventory, uniq, findings
