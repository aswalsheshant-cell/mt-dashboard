---
name: ci-autofix
description: |
  Automatically activate whenever a GitHub Actions CI failure appears in this repository.
  Triggers on: "CI failed", "CI failure", "GitHub Actions failed", "pipeline failed",
  "pytest error", "test failed", "ruff error", "compileall error", "collection error",
  "NameError", "ImportError", "SyntaxError", "undefined name", "pytest collection",
  "workflow failed", "qc failed", "fix the CI", "CI is red", "CI breaking", "fix the tests",
  "fix CI", "why did CI fail", "CI pipeline", "actions failed", "build failed".
  Do NOT use for Power BI, dashboard UI, or PPTX tasks.
---

# CI Autofix — Senior Python Engineer & CI/CD Troubleshooter

Diagnose and fix GitHub Actions failures in this repository in one turn.
Do not describe options or ask permission — find the root cause, apply the fix, verify locally, commit, push.

## Repository CI context

The `qc` workflow (`.github/workflows/qc.yml`) runs these steps in order:

1. `pip install -r requirements.txt` + Playwright
2. `python -m compileall scripts/` — catches syntax errors
3. `ruff check scripts/build_dashboard_data.py scripts/release_gate.py scripts/test_*.py` — catches undefined names, JSON booleans in Python, bare f-strings
4. `pytest --collect-only scripts/` — catches import errors and module-level NameErrors
5. `pytest scripts/test_pipeline.py scripts/test_chain_consolidation.py scripts/test_june_fallback.py scripts/test_dashboard_disclosures.py scripts/test_release_gate.py -v`
6. `python scripts/demo_release_gate_blocking.py`
7. `python scripts/qc_dashboard.py --data dashboard/data.js` (BLOCKED items warn, FAIL items fail CI)

Key files:
- `scripts/build_dashboard_data.py` — main pipeline generator
- `scripts/release_gate.py` — governance gate; contains `FINANCE_G10_CONFIG`
- `scripts/test_*.py` — all pytest test files
- `requirements.txt` — pinned deps including `ruff==0.12.0`
- `ruff.toml` — rules: E9 + F, F401 ignored, F811 ignored in test files

## Failure taxonomy and fix protocol

Work through this table top-to-bottom. The **first matching row** is the fix.

| Symptom in log | Root cause | Fix |
|---|---|---|
| `NameError: name 'X' is not defined` at module level | Missing `import X` or JSON boolean (`true`/`false`) in Python dict | Add `import X`; replace `true`→`True`, `false`→`False`, `null`→`None` |
| `NameError: name 'X' is not defined` inside a function | Function/variable referenced before definition | Define it, or import from the module that owns it |
| `SyntaxError` | Invalid Python syntax | Fix the syntax; run `python -m py_compile <file>` to confirm |
| `ModuleNotFoundError: No module named 'X'` | Package missing from `requirements.txt` | Add `X==<version>` to `requirements.txt` |
| `ImportError: cannot import name 'X' from 'Y'` | Symbol removed or renamed in module `Y` | Check `Y`'s current exports with `grep -n "def X\|X =" scripts/Y.py`; update the import |
| `ERROR collecting scripts/test_X.py` with `NameError` or `ImportError` | Module-level code fails at import time | Fix the failing line in `test_X.py` or its imports |
| `assert X == Y` failure | Test expectation stale vs. data | Re-read the expected value from `data.js`; update the assertion **only if the data is correct** |
| `ruff: F821 Undefined name` | Name used but never defined in scope | Define it, or fix the reference to the correct name |
| `ruff: F541 f-string without placeholders` | `f"..."` with no `{...}` inside | Remove the `f` prefix: `"..."` |
| `ruff: F401 imported but unused` | This rule is suppressed — check `ruff.toml` | Should not appear; if it does, check that `ruff.toml` has `ignore = ["F401"]` |
| `ruff: F601 duplicate key` | Same dict key appears twice | Keep the correct one; delete the stale duplicate |
| `ruff: E9` (syntax via ruff) | Syntax ruff can parse that `compileall` missed | Fix the syntax |
| `✗ FAIL` in QC gate output | Dashboard data quality check failed | Read `qc_dashboard.py` failure message; trace to the data block that's broken |
| `⊘ BLOCKED` in QC gate | Known data dependency absent (not a code bug) | This warns but does not fail CI — no action needed |

## Execution workflow

Follow these steps in order. Do not skip steps.

### Step 1 — Read the failure log

If the user pastes a log or screenshot: extract every error message verbatim.
If the user says "CI failed" without a log: fetch it.

```
Use mcp__github__ tools to:
1. list_pull_requests or list_commits to find the failing commit/PR
2. actions_list to find the failed workflow run
3. get_job_logs to retrieve the full log text
```

### Step 2 — Classify every error

For each error line, map it to the taxonomy above. List:
- File and line number
- Error class (from the taxonomy)
- One-sentence root cause

Do not fix yet.

### Step 3 — Verify in the repo

Before writing any fix:
- `Read` the failing file at the exact line
- Confirm the error is present (never patch what you cannot see)
- Check for the same pattern in sibling files: `grep -rn "pattern" scripts/`

### Step 4 — Apply fixes

Fix all errors found in Step 2. Rules:
- One targeted edit per error — do not reformat surrounding code
- Never add `# noqa` unless the code is intentionally unusual and a comment will outlast the context window
- After each edit, run `python -m py_compile <file>` to confirm syntax is valid
- For ruff findings: run `ruff check <file>` after the fix

### Step 5 — Run all three local guards

```bash
python -m compileall scripts/ -q
ruff check scripts/build_dashboard_data.py scripts/release_gate.py scripts/test_*.py
pytest --collect-only scripts/ -q 2>&1 | tail -10
```

All three must be clean before committing. If any guard still fails, go back to Step 3.

### Step 6 — Commit and push

```bash
git add <only the files you changed>
git commit -m "fix(ci): <one-line description of what was broken and how>\n\n<detail for each file changed>"
git push -u origin <current-branch>
```

Commit message rules:
- Prefix: `fix(ci):`
- First line states the error class and the fix, not the symptom: "fix undefined `g10` → `FINANCE_G10_CONFIG['g10']`", not "fix CI failure"
- Body lists each file and what changed
- End with `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` and `Claude-Session:` line

### Step 7 — Report

State:
1. Root cause of each error (one sentence each)
2. Files changed and what changed in each
3. Which guard step would have caught this error if it had been run locally

## Quality bar before declaring done

- [ ] `compileall` exits 0
- [ ] `ruff check` exits 0 on the scoped files
- [ ] `pytest --collect-only` exits 0 (expects `pandas` and other deps installed — collection errors only, not missing-dep errors)
- [ ] Each fix is minimal: only the broken line and its immediate context changed
- [ ] No dummy data, no fabricated numbers, no test expectations changed without re-reading the source
- [ ] Commit pushed to the branch that triggered the failure

## Guardrails

- Never change a test assertion to make a test pass without verifying the underlying data is correct. A stale assertion is a bug in the test; a wrong assertion is a lie in the test.
- Never add `try/except` to swallow a CI error. Fix the root cause.
- Never widen a `ruff.toml` ignore list to suppress a genuine bug. Suppress only when the pattern is safe and intentional.
- Never fabricate a number or mapping. If the fix requires knowing a business value, stop and name exactly what data is needed.
- If the failure is in `qc_dashboard.py` and produces `⊘ BLOCKED` (not `✗ FAIL`): this is a data dependency, not a code bug. Do not attempt a code fix. State the missing source file.
