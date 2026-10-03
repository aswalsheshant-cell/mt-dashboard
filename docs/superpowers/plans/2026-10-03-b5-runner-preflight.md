# B5 Runner Preflight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make draft PR #291's Desktop runner launch its governed queries reliably without changing evidence pass rules or claiming B5 clearance.

**Architecture:** Change only runner process invocation and preflight validation on PR #291's branch. Exercise discovery, exit-code handling, SHA and clean-tree checks without a DAX engine; preserve the separate live Desktop evidence workflow.

**Tech Stack:** PowerShell, Python/pytest, governed Power BI DAX/PQ files.

**Spec:** `docs/superpowers/specs/2026-10-03-cm2-dual-level-dashboard-design.md` (Validation, sequencing and release); `docs/evidence/B5_RUN_SHEET.md` on PR #291.

## Global Constraints

- Work only on PR #291's draft branch; do not mix this fix into the CM2 implementation branch.
- Keep every governed DAX/PQ case and the Python evidence renderer's pass rules unchanged.
- Do not mark B5 `CLEARED`; live Desktop execution, screenshots, reviewed results and a frozen main SHA remain mandatory.
- Preserve all source data, evidence and PR history; do not merge.

## Review Focus

1. PowerShell single-item arrays unwrap to strings; Task 1 tests Python executable discovery.
2. Generator stdout must not be compared to an exit code; Task 1 tests both outputs.
3. An untracked file means the tree is not clean; Task 1 tests that case.
4. A short SHA prefix collision is possible; Task 1 tests full expected SHA equality.
5. An absent Desktop engine must stop without writing fabricated results; Task 1 tests that preflight.

---

### Task 1: Repair PowerShell Runner Preflight

**Files:** On PR #291 only, modify `scripts/B5-DesktopRunner.ps1`; create `tests/test_b5_desktop_runner_preflight.ps1` or an equivalent Python-invoked PowerShell test; retain `scripts/b5_evidence.py` and governed query files unchanged.

**Interfaces:** Python discovery returns one executable path/string. `Invoke-Python` sends generator stdout to console/log but returns only integer process exit code. Preflight compares full expected SHA, checks tracked and untracked files, and records any authorized dirty exception. No engine connection means no evidence file.

- [ ] **Step 1:** Write failing preflight tests with a temporary Git checkout and stub Python executable for single-command discovery, stdout plus exit code 0, nonzero exit, wrong full SHA, untracked file, and absent engine.
- [ ] **Step 2:** Run the preflight suite; expect the existing runner to fail the discovery and status cases.
- [ ] **Step 3:** Make the smallest runner-only fix. Keep CLI switches and the governed query hashes stable.
- [ ] **Step 4:** Rerun the preflight and `python -m pytest tests/test_b5_evidence.py tests/test_b5_exit_condition.py -q`; expect PASS. Inspect the PR diff for only runner/test changes.
- [ ] **Step 5:** Push one signed GitHub-verified commit to PR #291 and report the static result. Run the first real Desktop session separately; B5 stays blocked until reviewed evidence exists.
