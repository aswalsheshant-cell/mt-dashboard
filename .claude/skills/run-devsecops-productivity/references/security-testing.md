# Security Testing — SAST, DAST, Secret Scanning, and Risk Assessment

**Scope:** Application-security testing protocols, tooling, risk-assessment
templates, and remediation prioritisation for the Honasa MT Analytics Platform.

---

## Security Testing Coverage

| Layer | Method | Tool | Frequency |
|---|---|---|---|
| Python source | SAST | bandit | Every PR |
| JS source (vendored) | SAST | eslint-security / grep patterns | Every PR touching dashboard/ |
| Dependencies | SCA | pip-audit + safety | Every push |
| Secrets in source | Secret scan | detect-secrets + GitHub secret scanning | Every push |
| Running dashboard | DAST (manual) | Browser sweep + DevTools | Every data.js rebuild |
| JS runtime patterns | Manual audit | XSS / prototype pollution checklist | Quarterly |
| Workflow permissions | Permissions audit | Manual YAML review | Every new workflow |

---

## SAST — Python (bandit)

### Configuration

Run with medium+ severity, all plugins enabled:

```bash
bandit -r scripts/ -ll -f json -o outputs/security/bandit_report.json
```

Flags:
- `-ll` — report LOW and above (use `-lll` for LOW only, `-l` for MEDIUM+)
- `-f json` — machine-readable output for CI integration
- `-o` — write report to derived artifact (never committed; gitignored)

### Severity Gates

| Severity | CI Behaviour |
|---|---|
| HIGH | Pipeline fail — must fix before merge |
| MEDIUM | Pipeline warn — reported in PR comment; must triage |
| LOW | Informational — logged to report; not blocking |

### Common False Positives (Suppress with `# nosec`)

```python
# Subprocess with controlled, non-user-input args is safe
result = subprocess.run(["python", "-m", "py_compile", path], ...)  # nosec B603,B607
```

Document every `# nosec` suppression with a reason. Unsuppressed false positives
accumulate technical debt — add them to `config/bandit_baseline.json` instead:

```bash
bandit -r scripts/ -ll --baseline config/bandit_baseline.json
```

---

## SAST — JavaScript (vendored libraries)

No Node.js build step exists in this project; eslint is not always available.
Use the grep-based manual checklist for every PR that modifies `dashboard/`:

```bash
# Dangerous patterns — flag for manual review
grep -n "eval\|new Function\|innerHTML\|document\.write" dashboard/index.html
grep -n "localStorage\|sessionStorage\|cookie" dashboard/index.html
grep -n "location\.href\|location\.replace" dashboard/index.html
grep -n "prototype\[" dashboard/*.min.js
grep -rn "\.src\s*=" dashboard/index.html
```

Any hit requires a comment in the PR explaining why the pattern is safe.

### Vendored Library Policy

Every `*.min.js` in `dashboard/` must have a header comment with source, version,
and license (per `secure-dependencies` policy). Additionally, for each vendored lib:

1. Check the library's GitHub release notes for the vendored version
2. Check CVE databases for known issues at that version
3. Record `last_audited` date in `outputs/dependencies/vendored-libraries.json`
4. If a CVE exists: assess exploitability in offline-dashboard context; document
   in `config/security_exceptions.json` if accepting risk

---

## Secret Scanning

### Pre-commit (Local)

Install `detect-secrets` as a pre-commit hook:

```bash
pip install detect-secrets
detect-secrets scan > .secrets.baseline
```

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
```

### CI (GitHub Secret Scanning)

GitHub secret scanning is enabled on this repository. It runs automatically and
alerts the repository owner on push. No manual configuration required — verify
it is enabled in repository Settings → Security → Secret scanning.

### Secret Pattern Categories (Flag Immediately)

| Pattern | Example | Action |
|---|---|---|
| GitHub PAT | `ghp_`, `github_pat_` | Revoke immediately; force-push not allowed — open security advisory |
| API key | `sk-`, `AKIA`, `AIza` | Revoke + rotate; notify key owner |
| Vercel token | `vercel_`, `vc_` | Revoke in Vercel dashboard |
| Generic bearer | `Bearer [A-Za-z0-9+/]{20,}` | Identify service; revoke |
| Password in URL | `://user:pass@` | Rotate; restructure to env var |

A secret committed to git history is permanently compromised — assume exposure
even if the commit is reverted. Rotate the credential first, then clean history.

### History Cleaning (After Secret Exposure)

```bash
# Using git-filter-repo (preferred over BFG)
pip install git-filter-repo
git filter-repo --path <file-with-secret> --invert-paths

# Force-push requires explicit authorisation (ADMIN gate)
# Notify all collaborators: local clones must re-clone after history rewrite
```

---

## DAST — Dashboard Manual Sweep

After every `data.js` rebuild, sweep all 12 dashboard tabs:

### Sweep Checklist

```
For each tab × {no-filter, FY25, FY26, FY27}:
  [ ] No NaN in any metric card
  [ ] No "undefined" in any label or value
  [ ] No broken/empty chart (canvas present and rendered)
  [ ] No overlapping elements (card overlap regression)
  [ ] No JS errors in DevTools console
  [ ] No network requests to external hosts (offline-first check)
  [ ] FY25/FY26 numbers unchanged from prior build (when only FY27 was intended to change)
```

**Tabs:** Data Explorer, Overview, Primary, Offtake, P&L, Category & Pack,
Forecast, Promo & Trade Spend, Market Share, Distribution, Performance &
Comparison, Insights & Way Forward.

### Playwright Automation (Supplemental)

For CI environments, use Playwright to automate the core sweep:

```python
# Headless check: all 12 tabs render without console errors
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    page = browser.new_page()
    page.goto("file:///home/user/mt-dashboard/dashboard/index.html")
    # Check for NaN and undefined in page text
    content = page.content()
    assert "NaN" not in content, "NaN found in rendered dashboard"
    assert "undefined" not in content, "undefined found in rendered dashboard"
    browser.close()
```

---

## Security Risk Assessment

### Risk Rating Formula

```
Risk = Likelihood × Impact

Likelihood: 1 (Rare) / 2 (Possible) / 3 (Likely)
Impact:     1 (Low)  / 2 (Medium)   / 3 (High)

Risk Score: 1–3 = LOW | 4–6 = MEDIUM | 7–9 = HIGH | 9 = CRITICAL
```

### Risk Assessment Template

```markdown
## Security Risk: <Title>

**Date:** YYYY-MM-DD
**Assessor:** <name>

### Finding
<What is the vulnerability or exposure?>

### Likelihood: <1-3>
<Why this likelihood? What conditions would need to be true?>

### Impact: <1-3>
<What happens if exploited? Data loss, exposure, availability impact?>

### Risk Score: <L×I> — <LOW/MEDIUM/HIGH/CRITICAL>

### Mitigations in Place
- <existing control 1>
- <existing control 2>

### Residual Risk: <LOW/MEDIUM/HIGH/CRITICAL>
<Risk after mitigations>

### Recommended Action
- [ ] <remediation step 1>
- [ ] <remediation step 2>

### Approval (if accepting residual risk)
Approver: <name>
Approved at: YYYY-MM-DD
Expires: YYYY-MM-DD
```

Store completed assessments in `outputs/security/risk-assessments/`.

---

## Remediation Prioritisation

| Priority | Condition | Target |
|---|---|---|
| P0 | CRITICAL risk score + active exposure | Within 24 hours |
| P1 | HIGH risk score + no mitigation | Within 72 hours |
| P2 | HIGH risk score + mitigation in place | Before next release |
| P3 | MEDIUM risk score | Next sprint cycle |
| P4 | LOW risk score | Quarterly sweep |

Remediation is tracked in GitHub issues with the label `security` and the
appropriate priority label (`s/p0`, `s/p1`, etc.).

---

## Quarterly Security Review

**Scope of each quarterly review:**

1. **Dependency audit** — run `secure-dependencies` skill; resolve or re-approve exceptions
2. **Vendored JS audit** — update `outputs/dependencies/vendored-libraries.json`; check for new CVEs
3. **Secret scanning baseline** — rotate `.secrets.baseline`; verify no new patterns
4. **Workflow permissions audit** — review all `.github/workflows/*.yml` for `write-all` or excess permissions
5. **Risk register review** — re-evaluate all open risk assessments; close resolved; renew approved exceptions
6. **Access review** — verify repository collaborators and deploy keys are still needed

Document results in `outputs/security/quarterly-review-<YYYY-QN>.md`.

---

**Reference version:** 2026-07-25
