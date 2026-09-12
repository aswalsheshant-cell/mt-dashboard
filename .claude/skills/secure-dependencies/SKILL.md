---
name: secure-dependencies
description: |
  Dependency security, SBOM generation, vulnerability scanning, license compliance, and
  vendored-library inventory for the Honasa / Mamaearth MT Dashboard. Use this skill for:
  Python dependency manifests and lockfiles, dependency inventory and SBOM generation,
  vendored JavaScript libraries, vulnerability scanning, open-source license review,
  exceptions and remediation tracking, automated CI dependency/security checks, and
  reporting when scanner or advisory coverage is unavailable.
---

# Secure Dependencies — Dependency & License Governance

## Purpose

Maintain a complete, auditable inventory of all dependencies (direct and transitive),
vendor-supplied libraries, and open-source licenses. Identify vulnerabilities, track
exceptions, enforce compliance, and gate CI on unresolved security findings.

## Scope

### Python Dependencies

**Manifests:**
- `requirements*.txt` files (direct and pinned transitive)
- `setup.py` / `setup.cfg` / `pyproject.toml` (project definitions)
- `Pipfile` / `Pipfile.lock` (if Pipenv is used)
- `poetry.lock` (if Poetry is used)

**Lockfiles:**
- Pinned versions, hashes, source URLs
- Transitive dependency tree (resolved at lock time)

**Scanning:**
- Safety check: `safety check` (knows ~50k CVEs; gaps noted)
- Pip audit: `pip-audit` (bundled with pip 24+; includes dependencies.io feeds)
- Custom: scan for known-bad patterns (e.g., abandoned packages, typosquatting)

**Reporting:**
- Installed packages inventory (frozen at lock time)
- SBOM export (CycloneDX or SPDX format)
- CVE matches and severity (CVSS v3.1)
- Remediation paths (update, patch, accept risk + evidence)

### Vendored JavaScript Libraries

**Inventory:**
- `dashboard/*.min.js` — Chart.js, jsPDF, SheetJS/xlsx, and others
- `PowerBI/**/*.js` — Query, DAX, theme helpers
- Each file tagged with source, version, license, last audit date

**Scanning:**
- SPDX license identifier from source comments or metadata
- Known-vulnerable patterns (e.g., XSS, prototype pollution, parser bombs)
- License compatibility check vs. project license (MIT / Apache 2.0 / GPL / proprietary)

**Reporting:**
- Vendored library manifest (source URL, version, license, last updated)
- License compliance matrix (permissive vs. copyleft vs. proprietary)
- Vulnerability advisories for each library
- Reason and date for each vendored choice

### Open-Source License Review

**License Categories:**
- **Permissive** (MIT, Apache 2.0, BSD, ISC) — OK to use, acknowledge in ATTRIBUTION
- **Copyleft** (GPL v2/v3, AGPL, SSPL) — must review; may require source availability
- **Proprietary** (commercial, source-restricted) — document approval, vendor agreement

**Compliance:**
- No unlicensed packages in dependency tree
- License ATTRIBUTION file updated when dependencies change
- Project license is compatible with all dependencies (no GPL → proprietary link)

**Exceptions:**
- `config/license_exceptions.json`: approved exceptions with justification, approver, date, expiry
- Format: `{ "package": "<name>", "reason": "...", "approver": "<name>", "approved_at": "YYYY-MM-DD", "expires_at": "YYYY-MM-DD or null" }`

### Automated CI Dependency Checks

**On every push:**
1. Resolve `requirements*.txt` (or `poetry.lock`, etc.)
2. Run Safety check + pip-audit (record results even if tools unavailable)
3. Validate SBOM is up to date (`git diff outputs/dependencies/sbom.json`)
4. Check for unlicensed packages
5. Scan for breaking changes in pinned versions (major version bump without documented reason)

**Reporting:**
- Find results in `outputs/dependencies/` (derived artifact)
- Exit 0 if all GREEN (no CVEs, licenses OK)
- Exit 1 if CVE without exception or license compliance failure
- Exit 2 if scanner unavailable (Safety down, pip-audit can't resolve)

**Outputs:**
- `sbom.json` (SPDX or CycloneDX; machine-readable)
- `inventory.csv` (human-readable: package, version, license, CVE count, last scanned)
- `licenses.json` (all unique licenses found, compatibility)
- `vulnerabilities.json` (CVEs, severity, remediation status)

### Exceptions & Remediation

**Exception Workflow:**
1. Security finding (CVE, outdated, license conflict)
2. Evaluate fix cost vs. risk
3. If accept risk: add to `config/security_exceptions.json` with:
   - Finding ID (CVE-XXXX, or custom id)
   - Package and version
   - Severity (critical / high / medium / low)
   - Reason (outdated library no longer maintained, but security exposure low / waiting for fix release / vendor approval to use)
   - Approver (person or team)
   - Approved date
   - Expiry date (when re-evaluation is due; null = permanent)
   - Mitigation (isolation, firewall rule, code audit, monitoring, etc.)

**Exception Format:**
```json
{
  "exceptions": [
    {
      "finding_id": "CVE-2021-12345",
      "package": "old-library",
      "version": "1.2.3",
      "severity": "high",
      "reason": "Vendor confirmed not exploitable in our usage; fix releasing next major version.",
      "approver": "security-team@honasa.example",
      "approved_at": "2026-07-20",
      "expires_at": "2026-12-31",
      "mitigation": "No internet-facing exposure; library used only for offline data processing."
    }
  ]
}
```

### Unavailable Scanner / Advisory Coverage

**When tools are unavailable:**
- `pip-audit` requires internet (depends on deps.dev feed): may fail in airgapped environments
- `safety` requires a current vulnerability database: database updates may lag
- Github Dependabot: only available if repo is on GitHub
- Snyk: requires paid account or open-source plan

**Reporting:**
- Flag clearly in output: `[UNAVAILABLE] pip-audit: could not reach deps.dev; using bundled pypa/warehouse data (may be stale)`
- Suggest fallback (e.g., manual vendor check, known-vulnerable-patterns scan)
- Exit code 2 (skipped) vs. 1 (failed)
- CI should alert on exit 2 but not gate (retry later when tool available)

## Implementation

### 1. Dependency Manifest Validation

```python
# scripts/secure_dependencies/manifest.py
def validate_requirements(path: str) -> list[Finding]:
    """Parse requirements.txt, check for hashes, detect pinning."""
    # Each line must have ==<version>
    # Hashes preferred (--hash=sha256:...)
    # Return Finding for each unpinned or non-hashed dependency
```

### 2. SBOM Generation

```python
# scripts/secure_dependencies/sbom.py
def generate_sbom(format: str = "spdx") -> dict:
    """Export all dependencies to SPDX or CycloneDX JSON."""
    # Query installed packages (pip freeze)
    # Resolve transitive tree
    # Include license, source, hash
```

### 3. Vulnerability Scanning

```python
# scripts/secure_dependencies/scan.py
def scan_vulnerabilities() -> list[Finding]:
    """Run safety + pip-audit, reconcile results."""
    # safety check (local or API)
    # pip-audit --skip-editable (handles transitive)
    # Report CVE ID, CVSS, remediation
```

### 4. License Compliance

```python
# scripts/secure_dependencies/licenses.py
def check_licenses() -> list[Finding]:
    """Validate all packages have known licenses; check compatibility."""
    # Extract SPDX identifier from metadata
    # Check against compatibility matrix
    # Report copyleft + proprietary combo as FAIL
```

### 5. Exception Management

```python
# scripts/secure_dependencies/exceptions.py
def apply_exceptions(findings: list[Finding]) -> list[Finding]:
    """Filter findings by approved exceptions."""
    # Load config/security_exceptions.json
    # Remove findings matching approved exceptions (if not expired)
    # Return remaining findings
```

## CI Integration

**GitHub Actions Example:**

```yaml
# .github/workflows/secure-dependencies.yml
name: Secure Dependencies Gate

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:
  dependencies:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install tools
        run: pip install safety pip-audit
      - name: Run security checks
        id: scan
        run: python3 -m scripts.secure_dependencies.cli scan
        continue-on-error: true
      - name: Upload reports
        uses: actions/upload-artifact@v4
        with:
          name: dependency-reports-${{ github.sha }}
          path: outputs/dependencies/
          retention-days: 30
      - name: Gate on critical findings
        run: |
          if [ "${{ steps.scan.outcome }}" == "failure" ]; then
            echo "::error::Security findings found; review outputs/dependencies/"
            exit 1
          fi
```

## Files & Locations

- `config/license_exceptions.json` — approved exceptions (committed)
- `config/security_exceptions.json` — CVE/vulnerability exceptions (committed with approver trail)
- `outputs/dependencies/sbom.json` — generated SBOM (derived artifact)
- `outputs/dependencies/inventory.csv` — human-readable package list (derived artifact)
- `outputs/dependencies/licenses.json` — license summary (derived artifact)
- `outputs/dependencies/vulnerabilities.json` — CVE scan results (derived artifact)
- `scripts/secure_dependencies/` — implementation modules

## Reporting

**Output to `outputs/dependencies/findings.json`:**

```json
{
  "timestamp": "2026-07-25T12:00:00Z",
  "tool_versions": {
    "safety": "2.3.5",
    "pip-audit": "2.6.1",
    "python": "3.11.15"
  },
  "scanner_availability": {
    "safety": "OK",
    "pip-audit": "OK",
    "github-dependabot": "UNAVAILABLE (not github.com)",
    "snyk": "UNAVAILABLE (no token)"
  },
  "findings": [
    {
      "id": "DEP-001",
      "tool": "pip-audit",
      "package": "requests",
      "version": "2.25.1",
      "finding_type": "vulnerability",
      "severity": "high",
      "cve": "CVE-2020-12345",
      "description": "...",
      "remediation": "Update to 2.31.0 or later",
      "status": "OPEN",
      "exception_id": null
    }
  ],
  "summary": {
    "total_packages": 47,
    "critical_cves": 0,
    "high_cves": 1,
    "license_issues": 0,
    "approved_exceptions": 2,
    "gate_status": "FAIL"
  }
}
```

## Non-negotiable Rules

1. **No secrets in dependencies.** If a package requires credentials or tokens, document the exception + approval in `security_exceptions.json`.
2. **Licenses are discoverable.** Every package must have a resolvable SPDX ID or documented exception.
3. **Exceptions are temporal.** Each exception must have an expiry date (or explicit null for permanent). Re-evaluate quarterly.
4. **Scanners are best-effort.** If a tool is unavailable, report the gap clearly. Do not fail CI just because a third-party service is down.
5. **Transitive vulnerabilities count.** Security findings apply to the full dependency tree, not just direct imports.

## Manual Inspection Triggers

- Unlicensed packages (rare, but catch typosquatting)
- Major version bumps in pinned dependencies
- New GPL-licensed dependencies (review compatibility)
- CVEs with no remediation path (vendor won't fix)
- Abandoned packages (github stars declining, no commits for >2 years)

---

**Last Updated:** 2026-07-25  
**Maintained By:** Data Engineering / Security  
**Scope:** Python & JS dependencies for Honasa MT Analytics Platform
