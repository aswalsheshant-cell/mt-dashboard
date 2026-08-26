#!/usr/bin/env python3
"""Synchronise the canonical skill suite to its install targets.

The canonical source in skill-suite/skills is the only editable location.
Every installed copy is a generated artifact; a difference between an installed
copy and its receipt is drift and stops the install.

Usage:
    python skill-suite/scripts/sync_skills.py --check
    python skill-suite/scripts/sync_skills.py --install --target project-claude
    python skill-suite/scripts/sync_skills.py --install --target all --dry-run
    python skill-suite/scripts/sync_skills.py --install --target user-claude --force

Targets:
    project-codex   .agents/skills            (repo, shared discovery)
    project-claude  .claude/skills            (repo, Claude discovery)
    user-codex      ~/.codex/skills           (user-wide Codex)
    user-claude     ~/.claude/skills          (user-wide Claude)
    all             every target above

Exit code 0 on success, 1 on validation failure, 2 on unresolved drift.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SUITE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = SUITE_ROOT.parent

sys.path.insert(0, str(SCRIPT_DIR))
from validate_skills import sha256_file, validate  # noqa: E402

RECEIPT_NAME = ".skill-suite-receipt.json"
STAGING_PREFIX = ".skill-suite-staging"
BACKUP_ROOT = REPO_ROOT / "work" / "skill-suite-backups"

TARGETS = {
    "project-codex": REPO_ROOT / ".agents" / "skills",
    "project-claude": REPO_ROOT / ".claude" / "skills",
    "user-codex": Path.home() / ".codex" / "skills",
    "user-claude": Path.home() / ".claude" / "skills",
}

CLEAN, OUTDATED, DIVERGED, ABSENT = "clean", "outdated", "diverged", "absent"


# --------------------------------------------------------------------------- helpers


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def checksum_tree(directory: Path) -> dict[str, str]:
    """Map every file under directory to its sha256, keyed by relative POSIX path."""
    if not directory.is_dir():
        return {}
    return {
        p.relative_to(directory).as_posix(): sha256_file(p)
        for p in sorted(directory.rglob("*"))
        if p.is_file()
    }


def load_manifest(suite: Path) -> dict:
    return json.loads((suite / "manifest.json").read_text(encoding="utf-8"))


def read_receipt(target: Path) -> dict:
    receipt = target / RECEIPT_NAME
    if not receipt.is_file():
        return {}
    try:
        return json.loads(receipt.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def classify(name: str, target: Path, source_sums: dict[str, str], receipt: dict) -> str:
    """Determine the drift state of one installed skill."""
    installed_dir = target / name
    if not installed_dir.is_dir():
        return ABSENT

    installed_sums = checksum_tree(installed_dir)
    if installed_sums == source_sums:
        return CLEAN

    recorded = receipt.get("skills", {}).get(name, {}).get("sha256", {})
    if not recorded:
        # Installed but never recorded by this pipeline: treat as hand-managed.
        return DIVERGED
    if installed_sums == recorded:
        # Matches what we last wrote; the canonical source has moved on.
        return OUTDATED
    return DIVERGED


def diff_summary(source_sums: dict[str, str], installed_sums: dict[str, str]) -> list[str]:
    lines = []
    for path in sorted(set(source_sums) | set(installed_sums)):
        in_source, in_target = source_sums.get(path), installed_sums.get(path)
        if in_source is None:
            lines.append(f"    only in target : {path}")
        elif in_target is None:
            lines.append(f"    only in source : {path}")
        elif in_source != in_target:
            lines.append(f"    differs        : {path}")
    return lines


# --------------------------------------------------------------------------- actions


def backup(target: Path, name: str, stamp: str) -> Path:
    destination = BACKUP_ROOT / stamp / target.name / name
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(target / name, destination)
    return destination


def install_target(
    suite: Path,
    manifest: dict,
    target_key: str,
    target: Path,
    source_sums: dict[str, dict[str, str]],
    force: bool,
    dry_run: bool,
) -> tuple[bool, list[str]]:
    """Install every suite skill into one target. Returns (ok, log lines)."""
    log: list[str] = []
    receipt = read_receipt(target)
    states = {
        name: classify(name, target, sums, receipt)
        for name, sums in source_sums.items()
    }

    diverged = [n for n, s in states.items() if s == DIVERGED]
    if diverged and not force:
        log.append(f"  DRIFT: {len(diverged)} skill(s) modified after installation")
        for name in diverged:
            log.append(f"  - {name}")
            log.extend(diff_summary(source_sums[name], checksum_tree(target / name)))
        log.append("  Re-run with --force to overwrite (the current copy is backed up first).")
        return False, log

    planned = [n for n, s in states.items() if s != CLEAN]
    for name in sorted(states):
        log.append(f"  {states[name]:<9} {name}")

    if not planned:
        log.append("  nothing to do")
        return True, log

    if dry_run:
        log.append(f"  DRY RUN: would write {len(planned)} skill(s) to {target}")
        return True, log

    stamp = now_iso().replace(":", "").replace("-", "")
    staging = target.parent / f"{STAGING_PREFIX}-{target.name}-{stamp}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    try:
        # Stage every skill, then verify the staged copy before touching the target.
        for name in planned:
            shutil.copytree(suite / "skills" / name, staging / name)

        for name in planned:
            staged_sums = checksum_tree(staging / name)
            if staged_sums != source_sums[name]:
                log.append(f"  ABORTED: staged copy of {name} does not match source checksums")
                return False, log

        target.mkdir(parents=True, exist_ok=True)
        for name in planned:
            existing = target / name
            if existing.exists():
                if states[name] == DIVERGED:
                    saved = backup(target, name, stamp)
                    log.append(f"  backed up diverged {name} -> {saved}")
                shutil.rmtree(existing)
            shutil.move(str(staging / name), str(existing))
            log.append(f"  installed {name}")
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    # Prune skills this pipeline installed previously that are no longer canonical.
    for name in sorted(set(receipt.get("skills", {})) - set(source_sums)):
        stale = target / name
        if stale.is_dir():
            saved = backup(target, name, stamp)
            shutil.rmtree(stale)
            log.append(f"  removed retired {name} (backed up -> {saved})")

    # Receipt: what was written, from where, when, and with which checksums.
    new_receipt = {
        "schema_version": manifest.get("schema_version"),
        "suite_version": manifest.get("suite_version"),
        "installed_at": now_iso(),
        "source": str(suite),
        "target": str(target),
        "target_key": target_key,
        "skills": {
            entry["name"]: {
                "version": entry["version"],
                "sha256": source_sums[entry["name"]],
            }
            for entry in manifest["skills"]
            if entry["name"] in source_sums
        },
    }
    (target / RECEIPT_NAME).write_text(json.dumps(new_receipt, indent=2) + "\n", encoding="utf-8")

    # Post-install verification against the freshly written receipt.
    failures = [
        name for name, sums in source_sums.items()
        if checksum_tree(target / name) != sums
    ]
    if failures:
        log.append(f"  POST-INSTALL VERIFICATION FAILED: {failures}")
        return False, log

    log.append(f"  verified {len(source_sums)} skill(s) at {target}")
    return True, log


def check_target(
    target_key: str, target: Path, source_sums: dict[str, dict[str, str]]
) -> tuple[bool, list[str]]:
    receipt = read_receipt(target)
    log = []
    ok = True
    for name in sorted(source_sums):
        state = classify(name, target, source_sums[name], receipt)
        log.append(f"  {state:<9} {name}")
        if state == DIVERGED:
            ok = False
            log.extend(diff_summary(source_sums[name], checksum_tree(target / name)))
    if not target.exists():
        log.append(f"  (target directory does not exist yet: {target})")
    return ok, log


# --------------------------------------------------------------------------- driver


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                      help="compare canonical and installed copies without writing")
    mode.add_argument("--install", action="store_true",
                      help="validate, then synchronise the selected targets")
    parser.add_argument("--target", default="project-claude",
                        choices=[*TARGETS, "all"],
                        help="install target (default: project-claude)")
    parser.add_argument("--force", action="store_true",
                        help="replace a diverged target after reporting and backing it up")
    parser.add_argument("--dry-run", action="store_true",
                        help="display planned changes without writing")
    parser.add_argument("--suite", type=Path, default=SUITE_ROOT,
                        help="path to the skill-suite root")
    args = parser.parse_args()

    suite = args.suite.resolve()

    # 1-7: validate before anything is compared or written.
    report = validate(suite)
    if report.errors:
        print("Validation failed; nothing was written.\n")
        for finding in report.errors:
            print(finding.render())
        return 1
    if report.warnings:
        for finding in report.warnings:
            print(finding.render())
        print()

    manifest = load_manifest(suite)
    source_sums = {
        entry["name"]: checksum_tree(suite / entry["source"])
        for entry in manifest["skills"]
    }

    print(f"suite {manifest['suite_version']}  ({len(source_sums)} skills, validated)")

    selected = list(TARGETS) if args.target == "all" else [args.target]
    overall_ok = True
    drift = False

    for key in selected:
        target = TARGETS[key]
        print(f"\n{key}  ->  {target}")
        if args.check:
            ok, log = check_target(key, target, source_sums)
            if not ok:
                drift = True
        else:
            ok, log = install_target(
                suite, manifest, key, target, source_sums, args.force, args.dry_run
            )
            if not ok:
                drift = True
        overall_ok &= ok
        for line in log:
            print(line)

    print()
    if overall_ok:
        print("OK")
        return 0
    print("UNRESOLVED DRIFT" if drift else "FAILED")
    return 2 if drift else 1


if __name__ == "__main__":
    raise SystemExit(main())
