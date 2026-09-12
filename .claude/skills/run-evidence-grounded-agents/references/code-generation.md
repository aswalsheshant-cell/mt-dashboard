# Code-Generation Controls — AI-Assisted Code Verification

**Scope:** Review checklist, security scanning, and commit standards for all
AI-generated or AI-assisted code on the Honasa MT Analytics Platform.

---

## Core Principle

AI-generated code is a draft. It must pass the same quality and security bar as
human-authored code. No AI-generated code reaches production without:

1. A human reading every line
2. Automated security scan (bandit / eslint-security)
3. Existing test suite passing with no regressions
4. `[ai-assist]` label in the commit message

---

## Pre-Execution Checklist (Shell Commands)

Before running any AI-generated shell command, verify each line:

- [ ] Does the command write to any path outside scratchpad without a WRITE gate?
- [ ] Does the command delete files (`rm`, `git clean`, `DROP TABLE`)?
- [ ] Does the command send data to an external endpoint (`curl`, `wget`, `requests.post`)?
- [ ] Does the command modify git history (`--amend`, `--force`, `rebase`)?
- [ ] Does the command install packages (`pip install`, `npm install`) not in requirements?
- [ ] Does the command read from an environment variable and log it?

If any answer is "yes", pause and request human review before executing.

---

## Python Code Review Checklist

Before committing AI-generated Python:

### Correctness
- [ ] Output matches expected values against at least one known test case
- [ ] FY rule is applied via `fy_tag_from_ym` / `fy_tag_from_label`, not hardcoded
- [ ] Money uses `Decimal`, not `float` (rounding errors compound across rows)
- [ ] Sort keys are explicit (no `set()` iteration, no `hash()` — use `hashlib.sha256`)
- [ ] No hardcoded file paths — use `ROOT / "..."` relative to repo root
- [ ] No hardcoded FY25/FY26 lists — FY list must be derived from data

### Security (Python — bandit)
- [ ] No `subprocess` with `shell=True` and user-controlled input (command injection)
- [ ] No `eval()` / `exec()` on external data
- [ ] No `pickle.loads()` from untrusted sources (arbitrary code execution)
- [ ] No SQL string concatenation (use parameterised queries)
- [ ] No secrets in source code or print statements
- [ ] No `os.system()` with dynamic strings

Run bandit before committing:
```bash
pip install bandit
bandit -r scripts/ -ll  # medium+ severity only; adjust as needed
```

### Data Integrity
- [ ] Excluded brands (Pure Origin, Lumineve, Staze) are never in any aggregation
- [ ] Blank / unallocated rows stay visible (never filtered to make totals tie)
- [ ] Net-negative chains are retained, not dropped
- [ ] New output is byte-identical on two consecutive deterministic runs

---

## JavaScript Code Review Checklist

Before committing AI-generated JS (vendored libs or dashboard patches):

### Correctness
- [ ] No global variable collisions with `window.DASH` or Chart.js namespace
- [ ] No modification of `data.js` at runtime (read-only source)
- [ ] Event listeners are removed when tabs are destroyed (memory leak check)
- [ ] No `innerHTML` set with user-controlled or fetched strings (XSS)

### Security (JS — eslint-security)
- [ ] No `eval()` / `new Function()` with external strings
- [ ] No `document.write()` with dynamic content
- [ ] No hardcoded URLs pointing to external hosts (CSP will block; flag as a bug)
- [ ] No `localStorage`/`sessionStorage` of sensitive data

Run eslint-security (if Node available):
```bash
npx eslint --plugin security --rule 'security/detect-eval-with-expression: error' dashboard/
```

For offline environments, do a manual grep:
```bash
grep -n "eval\|innerHTML\|document\.write\|localStorage" dashboard/index.html
```

---

## Commit Standards for AI-Assisted Code

### Required Commit Message Format

```
<subject line (imperative, ≤72 chars)>

<body: what changed and why — mandatory for WRITE-level changes>

[ai-assist] Generated with Claude Code claude-haiku-4-5-20251001
Verified: bandit clean, tests pass, FY25/FY26 unchanged
Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_...
```

The `[ai-assist]` label allows the team to audit which commits were AI-assisted
and cross-reference against quality reports.

### What Must Not Appear in Commits

- Secrets, tokens, API keys (even masked)
- Model identifiers in subject lines or code comments
- Fabricated numbers not traced to a real source
- `TODO: verify this` items (verify before committing, not after)

---

## Build and Determinism Checks

Before marking AI-generated build output as ready:

```bash
# 1. Compile check
python -m py_compile scripts/build_dashboard_data.py

# 2. Full test suite — no regressions
python -m unittest discover -s tests -p 'test_*.py'

# 3. Determinism — two consecutive builds must be byte-identical
python scripts/build_dashboard_data.py --detail-only --src <dir> --out /tmp/build1.js
python scripts/build_dashboard_data.py --detail-only --src <dir> --out /tmp/build2.js
diff /tmp/build1.js /tmp/build2.js  # must produce no output

# 4. FY invariant — FY25/FY26 numbers unchanged
git diff HEAD dashboard/data.js | grep -E '^\+.*"(fy25|fy26)"'
# Any unexpected FY25/FY26 changes are a blocker
```

---

## Dependency Hygiene for AI-Suggested Packages

If AI-generated code introduces a new `import` or `require`:

1. Check if the package already exists in `requirements.txt` or vendored JS
2. If new: run through the `secure-dependencies` skill before adding to manifest
3. Never `pip install <package-name-from-ai>` without checking the exact package name
   against PyPI (typosquatting risk — AI may hallucinate package names)
4. Pin the exact version; do not use `>=` ranges for AI-suggested packages without review

---

**Reference version:** 2026-07-25
