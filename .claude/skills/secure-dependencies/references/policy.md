# Dependency Security & License Policy

**Effective:** 2026-07-25  
**Scope:** Honasa / Mamaearth MT Analytics Platform (dashboard + Power BI kit)

---

## Policy Statement

All dependencies (direct and transitive) must be:
1. **Known** — inventoried in SBOM, resolved from trusted sources
2. **Licensed** — SPDX-identifiable, compatible with project license
3. **Secure** — free of known critical/high CVEs, or approved exceptions
4. **Maintained** — not abandoned (active upstream support)

Approved exceptions must be documented with business justification, approver signature, and expiry date.

---

## Approval Matrix

| Finding Type | Severity | Auto-Gate | Approval Required | Escalation |
|---|---|---|---|---|
| CVE | Critical | NO | CISO + Engineering Lead | Exec review |
| CVE | High | YES (if exception exists) | Security Team | CTO if > 30 days old |
| CVE | Medium | YES (if exception exists) | Engineering Lead | Review on quarterly sweep |
| CVE | Low | YES (if exception exists) | Team member | Document in backlog |
| Unlicensed Package | Any | NO | Legal + Engineering | Immediate removal |
| GPL + Proprietary | Any | NO | Legal | Architectural redesign |
| Abandoned Package | Any | NO | Engineering Lead | Vendor or remove |
| Outdated (major) | Any | YES (if justified) | Engineering Lead | Re-evaluate every release |

---

## Exception Approval Workflow

1. **Finding Identified** → `pip-audit`, `safety`, or manual review
2. **Risk Assessment** → Engineer documents impact, exposure, mitigation
3. **Exception Draft** → Create entry in `config/security_exceptions.json`
4. **Approval** → Security Team (or CTO if Critical) signs off
5. **Timestamp** → Record approval date; set expiry (max 180 days for CVEs)
6. **CI Gate** → Approved exceptions are removed from FAIL list
7. **Expiry** → Before expiry date, re-evaluate (renew or remediate)

**Approval Template:**
```json
{
  "finding_id": "CVE-YYYY-XXXXX",
  "package": "...",
  "version": "...",
  "severity": "high",
  "reason": "Vendor confirmed not exploitable in our usage pattern. Waiting for fix release in v2.0 (ETA Aug 2026).",
  "approver": "security-lead@honasa.example",
  "approved_at": "2026-07-20",
  "expires_at": "2026-08-31",
  "mitigation": "Package isolation: no internet-facing exposure. Code audit completed 2026-07-15."
}
```

---

## License Compatibility Matrix

| License Category | Permissive | Copyleft | Proprietary |
|---|---|---|---|
| **Project (MIT)** | ✅ OK | ⚠️ Review | ❌ NO |
| **Transitive** | ✅ OK | ⚠️ Review* | ❌ NO |

*Copyleft (GPL, AGPL) requires full review. If the project would inherit copyleft obligations, reject or redesign.

**Approved Permissive Licenses:**
- MIT, Apache 2.0, BSD (2-clause, 3-clause), ISC, CC0-1.0

**Review Required:**
- GPL v2, GPL v3, AGPL, SSPL (copyleft with source-availability requirement)
- LGPL (lesser copyleft; usually OK if not modified)

**Rejected:**
- Any proprietary license without vendor approval
- Unlicensed (assume proprietary)
- Incompatible open-source (e.g., code under multiple conflicting licenses)

---

## Scanning & Reporting Requirements

### Mandatory Scanning Tools
1. **pip-audit** (bundled with pip 24+)
   - Scans Python dependencies + transitive
   - Uses PyPA advisory database
   - Gaps: does not catch all abandoned packages

2. **Safety** (free tier ~50k CVEs)
   - Industry-standard Python CVE database
   - Gaps: database updates lag; premium only for latest

3. **Manual Review** (quarterly)
   - Check for abandoned packages (github activity, commit recency)
   - Validate license compliance with upstream
   - Audit vendored JS libraries

### When Scanners Are Unavailable
- **pip-audit offline:** Use bundled pypa/warehouse data (may be <7 days stale)
- **safety database expired:** Use CVE.org + NVD direct lookup (manual process)
- **No network:** Skip CI gate; alert maintainers; retry on next network availability

**Gate Behavior:**
- Exit 0: All GREEN (no findings or all approved exceptions)
- Exit 1: FAIL (unresolved critical/high CVE, license conflict, unlicensed package)
- Exit 2: UNAVAILABLE (scanner offline, database stale) — alert ops, do not block CI

---

## Vendored JavaScript Libraries

All vendored `.js` files must include:
1. **Header comment** with source URL, version, license
2. **Last audit date** (commit message or separate manifest)
3. **Rationale** (why vendored vs. CDN) in `PowerBI/docs/` or inline

**Example Header:**
```javascript
/**
 * Chart.js v3.9.1
 * Source: https://github.com/chartjs/Chart.js
 * License: MIT
 * Last Audited: 2026-07-20
 * Rationale: Offline-first dashboard; bundled to eliminate CDN dependency
 */
```

**Manifest:** `outputs/dependencies/vendored-libraries.json`
```json
{
  "files": [
    {
      "path": "dashboard/Chart.min.js",
      "source": "https://github.com/chartjs/Chart.js",
      "version": "3.9.1",
      "license": "MIT",
      "last_audited": "2026-07-20",
      "reason": "Offline-first; required for chart rendering",
      "known_vulnerabilities": []
    }
  ]
}
```

---

## Python Dependency Pinning Requirements

**requirements.txt** MUST:
- Pin all transitive dependencies (`pip freeze` output)
- Include hashes for reproducibility (`--hash=sha256:...`)
- Comment any intentional unpinned ranges with justification

**Example:**
```
# Direct dependencies
requests==2.31.0 --hash=sha256:...
click==8.1.7 --hash=sha256:...

# Transitive (pinned for reproducibility)
certifi==2023.7.22 --hash=sha256:...

# INTENTIONAL: pandas range (minor updates allowed)
# Rationale: Security updates within v2.0.x; major version change evaluated separately
# Last reviewed: 2026-07-20
pandas>=2.0.0,<3.0.0
```

---

## Quarterly Review Schedule

| Month | Scope |
|---|---|
| Every push | Safety + pip-audit (automated) |
| End of March | Annual license audit + GPL/copyleft compliance |
| End of June | Vendored JS libraries + abandoned packages check |
| End of September | CVE backlog + exception expiry review |
| End of December | Full SBOM refresh + dependency upgrade plan |

---

## Remediation Priorities

| Priority | Condition | Target Resolution |
|---|---|---|
| **P0 (Immediate)** | Critical CVE + exploitable + no exception | Within 24h |
| **P1 (Urgent)** | High CVE + active exploitation known | Within 72h |
| **P2 (Planned)** | High CVE + low exposure + exception exists | Before expiry |
| **P3 (Backlog)** | Medium CVE + no business impact | Next release cycle |
| **P4 (Monitor)** | Low CVE + well-mitigated | Quarterly review |

---

## Exception Expiry & Re-evaluation

**Before exception expires:**
1. Check if upstream released a fix
2. Assess if upgrade is possible (breaking changes?)
3. Document new finding if not fixed
4. Renew exception (with updated justification) or remediate

**Expired exception = gate failure** (must renew or fix)

---

## Escalation Path

1. **Finding Detected** → Slack #security-alerts
2. **P0/P1** → Page CISO + CTO (24h response)
3. **P2/P3** → Email security-team@honasa.example (48h response)
4. **Architectural Change Required** → Architecture review board

---

## Compliance Reporting

**Monthly Summary** (sent to CISO):
- Total packages inventoried
- CVEs: critical, high, medium, low
- Approved exceptions (active, expiring soon)
- License issues (if any)
- Compliance status (GREEN / YELLOW / RED)

**Annual Report** (regulatory, audit):
- Complete SBOM (SPDX format)
- License compatibility matrix
- Exception register with business justification
- Incident log (breaches, false positives, remediation timeline)

---

## Questions & Escalation

**Contact:** security-team@honasa.example  
**Escalation:** CTO (cto@honasa.example) for policy exceptions or architecture changes  
**Audit Trail:** All exceptions committed to git with approver signature

---

*This policy is version-controlled and subject to change. Review quarterly for policy updates.*
