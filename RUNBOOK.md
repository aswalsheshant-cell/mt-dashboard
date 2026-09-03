# MT Dashboard Production Runbook

**Release Version:** v1.0.0  
**Date:** 2026-09-03  
**Status:** Production Ready ✅

---

## Overview

This runbook documents operational procedures for the MT Dashboard production environment. The dashboard operates in two modes: (1) **Static HTML/JS** served offline or on GitHub Pages, and (2) **Power BI analytics** for detailed modeling and executive reporting.

---

## 1. Strict CI/CD Pipeline (Sept 2026)

### Validation Gates Active
- **validate.yml** — Python syntax, JSON schema, JavaScript linting, dashboard markup
- **deploy-pages.yml** — Automated GitHub Pages deployment on every `main` push
- **pbi-windows-ci.yml** — Power BI model validation on Windows runner

**Key Change:** `continue-on-error: true` flags removed from critical validation steps.  
→ **Failures now halt the pipeline.** Do not bypass; fix the root cause.

### Monitoring CI Health
```bash
# Check recent runs (local verification)
git log main -5 --oneline

# GitHub Actions status: https://github.com/aswalsheshant-cell/mt-dashboard/actions
# Verify: validate.yml and deploy-pages.yml show ✓ (success)
```

---

## 2. Monthly Offtake Patch (Refresh Cycle)

### Trigger
When monthly offtake CSVs arrive in `PowerBI/RawDataFolders/Offtake_Monthly/`:

### Procedure
```bash
# 1. Verify files arrived
ls PowerBI/RawDataFolders/Offtake_Monthly/*.xlsx | wc -l

# 2. Run offtake patch (idempotent — recomputes all touched FYs)
python scripts/build_dashboard_data.py \
  --offtake-patch \
  --src PowerBI/RawDataFolders/Offtake_Monthly \
  --out dashboard/data.js

# 3. Validate data integrity
python tests/validate_data_integrity.py dashboard/data.js

# 4. Commit and push to main (CI will validate + deploy)
git add dashboard/data.js
git commit -m "data(offtake): refresh monthly patch [FYMM]"
git push origin main

# 5. Verify GitHub Pages updated: https://aswalsheshant-cell.github.io/mt-dashboard/
```

**Important:** `--offtake-patch` is **idempotent** — it safely re-processes all touched FYs. No double-counting. Can re-run the same files multiple times.

---

## 3. FY25/FY26/FY27 Coverage Rules

### THE ONE FY RULE
- **Apr–Dec of year Y** → **FY(Y+1)**  (e.g., Apr-26 → FY27)
- **Jan–Mar of year Y** → **FY(Y)**  (e.g., Mar-26 → FY26)

### Data Segments Locked
| Block | FY Coverage | Source | Status |
|-------|-------------|--------|--------|
| Primary | FY25, FY26, FY27 | Pre-agg + Article detail | ✅ Live |
| Offtake | FY25, FY26, FY27 | Monthly CSVs (patch) | ✅ Live |
| P&L | FY25, FY26 | Pre-aggregated workbook | ✅ Complete |
| Forecast | FY27 | TY target workbook | ✅ Complete |
| Insights | FY25, FY26, FY27 | Generated at build-time | ✅ Live |

### Validation
```bash
# Check FY tags and chain count in data.js
python3 -c "
import json, re
with open('dashboard/data.js') as f:
    data = json.loads(re.sub(r'^.*?window.DASH\s*=\s*', '', f.read()).rstrip(';'))
    print(f'FYs: {data[\"primary\"].get(\"fy_tags\", [])}')
    print(f'Chains: {len(data[\"primary\"].get(\"by_chain\", []))}')
"
```

---

## 4. Data Integrity Assertions (Locked at Release)

These assertions gate every build and PR merge:

1. **55 unique chains** in primary.by_chain ✅
2. **6 zones** (Central, East, North, South-1, South-2, West) ✅
3. **FY26 baseline** ₹32,900.36L ± 0.1% ✅
4. **FY27 data present** (sum > 0) ✅
5. **No legacy chain names** (D-Mart, H&G, Vishal Mega Mart, etc.) ✅
6. **Offtake zones:** No "Pan India" in by_zone (only raw source) ✅
7. **Channels:** MT, EB2B, SIS all present ✅
8. **No null/NaN in FY26** across primary.by_chain ✅
9. **dims.Zone** matches authorized set (spaces: "South 1", "South 2") ✅
10. **primary.n_chains** reported == actual count ✅

**On failure:**
```bash
# Run full validation and fix
python tests/validate_data_integrity.py dashboard/data.js

# If FY26 total drifts > 0.1%, investigate source
# If chains added/removed, update tests/validate_data_integrity.py
```

---

## 5. GitHub Pages Deployment

### Automatic (No Action Required)
- Every push to `main` triggers `deploy-pages.yml`
- Dashboard files copied to `gh-pages` branch
- Live at: https://aswalsheshant-cell.github.io/mt-dashboard/

### Manual Verification
```bash
# Check gh-pages branch updated
git log origin/gh-pages -1 --format="%h %ai %s"

# Expected: recent commit from deploy-pages workflow
```

### Smoke Test (External Workstation)
```bash
# Open in browser
https://aswalsheshant-cell.github.io/mt-dashboard/

# DevTools (F12):
# 1. Console: no window.DASH parsing errors
# 2. Network: data.js loads with HTTP 200
# 3. Dashboard renders: 55 chains in dropdowns
# 4. Filter & export functional
```

---

## 6. Skills Framework (Agentic Routing)

### Available Skills
- **16 domain skills** from `.claude/skills/` (mt-python-pipeline, mt-ppt-presentation, mt-powerbi-dax, etc.)
- **3 reference skills** from `skills/` (promo-query, data-validation, report-generator)

### Usage (For Future Agents)
```python
from skills_loader import SkillRegistry, build_system_prompt

registry = SkillRegistry(".claude/skills")  # Load domain skills
prompt = build_system_prompt(BASE_PROMPT, registry, active_skill="mt-python-pipeline")

# Output: full system prompt with skill catalog + active skill body
```

### Test Skills Framework
```bash
python -m pytest tests/unit/test_skills_loader.py -v
# Expected: 21 passed
```

---

## 7. Incident Response

### CI Failure on `validate.yml`
**Do NOT skip validation.** Failures are legitimate.

```bash
# 1. Examine the failure in GitHub Actions
# 2. Pull latest and reproduce locally
git pull origin main
python -m py_compile scripts/build_dashboard_data.py
python tests/validate_data_integrity.py dashboard/data.js

# 3. Fix the root cause (usually data or script)
# 4. Commit and push (CI will re-run)
```

### Data Anomaly Detected
```bash
# 1. Load data.js and inspect
python3 -c "
import json, re
with open('dashboard/data.js') as f:
    data = json.loads(re.sub(r'^.*?window.DASH\s*=\s*', '', f.read()).rstrip(';'))
    # Inspect data['primary']['by_chain'], data['offtake'], etc.
"

# 2. Compare against prior committed data.js
git show HEAD~1:dashboard/data.js | wc -c  # size check
git diff HEAD~1 dashboard/data.js | grep -A2 -B2 '@@' | head -20

# 3. If it's bad, revert
git revert HEAD
```

### GitHub Pages Not Updating
```bash
# 1. Check deploy-pages.yml last run
git log origin/gh-pages -1

# 2. Re-trigger manually
git push origin main --force-with-lease  # Last resort; use with care
```

---

## 8. Scheduled Tasks & Notifications

### Monthly Refresh (e.g., 1st of each month)
- Offtake CSVs arrive → Place in `PowerBI/RawDataFolders/Offtake_Monthly/`
- Run command from **Section 2**
- CI validates and deploys automatically

### Quarterly Planning (End of FY quarters)
- Verify FY forecast targets are updated in `PowerBI/RawDataFolders/TDP_Monthly/`
- Rebuild forecast block: `python scripts/build_dashboard_data.py --forecast-only --src ... --out dashboard/data.js`

### Annual Archive (End of FY)
- Tag release: `git tag -a vX.Y.Z -m "FY{Y} archive"`
- Backup data.js and seed files

---

## 9. Rollback Procedure

### Quick Rollback (Last Commit)
```bash
git revert HEAD
git push origin main
```

### Roll to Specific Release
```bash
# List releases
git tag -l | grep v

# Checkout release commit
git checkout v1.0.0

# Create new branch and push
git checkout -b restore/v1.0.0
git push origin restore/v1.0.0
```

---

## 10. Production Release Checklist

- [ ] All tests pass (pytest, validate_data_integrity.py)
- [ ] CI/CD green on main (validate.yml, deploy-pages.yml)
- [ ] Data.js loads on GitHub Pages without errors
- [ ] All 55 chains render in dashboard
- [ ] Skills framework loads (21 unit tests pass)
- [ ] Release tag created: `git tag -a vX.Y.Z`
- [ ] Runbook reviewed and signed off

---

## Contact & Escalation

**Operational Owner:** aswal.sheshant@gmail.com  
**Repository:** https://github.com/aswalsheshant-cell/mt-dashboard  
**Dashboard Live:** https://aswalsheshant-cell.github.io/mt-dashboard/

**For issues:**
1. Check CI logs at https://github.com/aswalsheshant-cell/mt-dashboard/actions
2. Run local validation: `python tests/validate_data_integrity.py dashboard/data.js`
3. Review CLAUDE.md for architecture

---

**Document Version:** 1.0  
**Last Updated:** 2026-09-03  
**Next Review:** 2026-10-01
