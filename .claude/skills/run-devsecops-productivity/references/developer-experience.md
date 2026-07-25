# Developer Experience — Local Setup, IDE Practices, and AI-Assisted Development

**Scope:** Local environment setup, branch and PR conventions, IDE configuration,
responsible AI-assistant adoption, and continuous feedback practices for the
Honasa MT Analytics Platform.

---

## Local Environment Setup

### Prerequisites

```bash
python3 --version   # 3.11+ required
node --version      # optional — needed only for eslint-security checks
git --version       # 2.40+
```

### First-Time Setup

```bash
git clone https://github.com/aswalsheshant-cell/mt-dashboard.git
cd mt-dashboard

# Install Python dependencies
pip install -r requirements.txt

# Verify setup: full test suite must pass within 30 minutes of clone
python -m unittest discover -s tests -p 'test_*.py'
# Expected: 177 tests, 0 failures

# Verify data engineering engines load
python3 -m scripts.dataeng.cli health
```

**Onboarding gate:** A new contributor should be able to clone, install, and run
the full test suite to a green result within 30 minutes. If they cannot, the
environment setup documentation is broken — fix it, do not ask the contributor
to work around it.

### Pre-commit Hooks

Install these hooks to catch issues before they reach CI:

```bash
pip install pre-commit
```

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.8
    hooks:
      - id: bandit
        args: ["-r", "scripts/", "-ll"]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  - repo: local
    hooks:
      - id: compile-check
        name: compile check
        entry: python -m py_compile scripts/build_dashboard_data.py
        language: system
        pass_filenames: false

      - id: unit-tests
        name: unit tests (fast)
        entry: python -m unittest discover -s tests -p 'test_*.py'
        language: system
        pass_filenames: false
```

**Total pre-commit time target:** < 30 seconds. If any hook exceeds this, move it
to CI only.

---

## Branch and PR Conventions

### Branch Naming

```
<type>/<short-description>
```

Types:
- `feature/` — new capability
- `fix/` — bug fix
- `hotfix/` — urgent production fix (bypasses draft convention)
- `refactor/` — code change with no functional difference
- `chore/` — maintenance (dependency updates, config changes)
- `claude/` — agent-initiated branches (convention: `claude/<date>-<description>`)

Examples:
- `feature/fy27-offtake-monthly`
- `fix/nan-in-overview-tab`
- `claude/june-26-sales-data-xzbhub`

### PR Size Convention

Target < 400 lines changed per PR. Large PRs:
- Are harder to review thoroughly
- Accumulate more merge conflicts
- Produce less actionable feedback

For large changes, split by logical layer (data layer → build script → dashboard
rendering → tests) and stack PRs with clear dependency notes.

### PR Checklist (Author)

Before marking a PR "Ready for Review":

```
[ ] All CI checks pass
[ ] All 177 existing tests pass; new tests added for new behaviour
[ ] py_compile passes on any modified script
[ ] FY25/FY26 numbers unchanged if only FY27 was intended to change (data.js diff reviewed)
[ ] No NaN/undefined in dashboard tabs (preview URL swept)
[ ] No secrets or PII in changed files
[ ] bandit HIGH findings: 0
[ ] PR description explains WHAT changed and WHY
[ ] CLAUDE.md implementation rules satisfied (enhance, don't redesign)
```

### PR Review Conventions

**Reviewer responsibility:**
- Review the diff line-by-line — AI-generated code is not pre-reviewed
- Confirm FY rule applied correctly (no hardcoded FY lists)
- Confirm rounding differences are within `max_rounding_l` ceiling
- Confirm excluded brands (Pure Origin, Lumineve, Staze) are absent from aggregations
- Confirm `[ai-assist]` commits have the required human verification sign-off

**Label to add after review:**
- `s/agent-reviewed` — PR reviewed; no changes requested
- `s/agent-changes-requested` — PR reviewed; changes needed

---

## IDE Configuration

### VS Code (Recommended Settings)

`.vscode/settings.json` (project-scoped, committed):
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.banditEnabled": true,
  "python.testing.unittestEnabled": true,
  "python.testing.unittestArgs": ["-v", "-s", "tests", "-p", "test_*.py"],
  "editor.formatOnSave": false,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "outputs/": true
  }
}
```

### Useful Extensions

- **Python** (ms-python.python) — linting, testing, IntelliSense
- **GitLens** — blame, history, PR context inline
- **Error Lens** — inline error display for bandit/flake8 output
- **Todo Tree** — tracks `# TODO` and `# FIXME` comments

### JetBrains (PyCharm / IntelliJ)

Run configurations for the project:

1. **All Tests:** `python -m unittest discover -s tests -p 'test_*.py'`
2. **Health Check:** `python3 -m scripts.dataeng.cli health`
3. **Compile Check:** `python -m py_compile scripts/build_dashboard_data.py`

---

## Responsible AI-Assistant Adoption

### Permitted Uses of Copilot / Claude Code

| Use Case | Permitted | Note |
|---|---|---|
| Boilerplate generation (CSV parsing, file I/O) | Yes | Review every line |
| Unit test scaffolding | Yes | Verify assertions are correct |
| Refactoring within existing functions | Yes | Confirm behaviour unchanged via tests |
| FY rule implementation | Caution | Must use `fy_tag_from_ym`; never accept hardcoded logic |
| New business logic (CM2, allocation) | No | Requires human authorship + governance |
| Security-sensitive code (auth, secret handling) | No | Human authorship only |
| Data.js interpretation or "explain this number" | Caution | Cite source; never trust model memory |

### Mandatory Review for AI-Generated Code

All AI-generated or AI-assisted code must go through the checklist in
`run-evidence-grounded-agents/references/code-generation.md` before committing.
Key gates:

1. Human reads every line — no bulk-accept
2. bandit scan passes (0 HIGH findings)
3. Existing tests pass without modification
4. `[ai-assist]` in commit message

### Copilot-Specific Risks

- **Outdated patterns:** Copilot may suggest deprecated APIs or Python 2 idioms
- **Hallucinated function names:** Verify every suggested import is a real package
- **Incorrect FY logic:** Always verify FY derivation against `fy_tag_from_ym`
- **Context bleed:** Copilot suggestions may reference patterns from other projects
  not applicable here — treat suggestions as hints, not answers

### What AI Assistants Must Not Do

- Approve or modify governance decisions (D1, D9, or any decision register entry)
- Mark provisional CM2 data as approved
- Commit directly to main without PR + review
- Interpret financial figures without a retrieved, cited source

---

## Continuous Feedback and Improvement

### Weekly Retro (Engineering)

15-minute sync focused on CI/CD health:

- Which PRs were blocked longest and why?
- Any flaky tests or slow pipeline stages this week?
- Any security findings that surprised us?
- One experiment to try next week

Keep notes in `outputs/retro/<YYYY-WNN>.md` (lightweight; a few bullet points).

### Feedback on Claude Code / AI Agents

When an agent produces an incorrect or unhelpful result:

1. Document the failure case in `outputs/agent-runs/<session-id>/feedback.md`
2. Identify which skill or agent instruction led to the failure
3. Propose a rule addition or clarification to the relevant SKILL.md
4. Open a PR with the skill update — treat skill improvements like code improvements

### Developer Friction Log

Maintain a running list of things that slow contributors down:

```markdown
# Developer Friction Log

| Date | Issue | Proposed Fix | Status |
|---|---|---|---|
| 2026-07-25 | Pre-commit takes 45s (too slow) | Move unit tests to CI only | Proposed |
| 2026-07-20 | `data.js` rebuild requires source workbooks not in repo | Document in onboarding | Done |
```

File: `outputs/friction-log.md`. Review monthly and address top items first.

---

**Reference version:** 2026-07-25
