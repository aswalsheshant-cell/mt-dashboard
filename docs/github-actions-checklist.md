# GitHub Actions Pre-Merge Checklist

Run every item before merging any PR that touches `.github/workflows/`.

---

## Workflow File Checks

```bash
# 1. No empty files
for f in .github/workflows/*.yml; do
  size=$(wc -c < "$f")
  echo "$size bytes — $f"
  [ "$size" -lt 10 ] && echo "  !! FAIL: empty file"
done

# 2. All YAML parses with on: trigger
python - <<'EOF'
import glob, yaml, pathlib, sys
errors = []
for path in glob.glob(".github/workflows/*.yml"):
    try:
        doc = yaml.safe_load(pathlib.Path(path).read_text())
        if not isinstance(doc, dict) or ("on" not in doc and True not in doc):
            errors.append(f"FAIL {path}: missing on: trigger")
        else:
            print(f"✓ {path}")
    except yaml.YAMLError as e:
        errors.append(f"FAIL {path}: {e}")
[print(e) for e in errors]
sys.exit(len(errors))
EOF

# 3. No duplicate workflow names
python - <<'EOF'
import glob, yaml, pathlib
names = {}
for path in glob.glob(".github/workflows/*.yml"):
    doc = yaml.safe_load(pathlib.Path(path).read_text()) or {}
    name = doc.get("name", "")
    if name in names:
        print(f"DUPLICATE name '{name}': {names[name]} and {path}")
    names[name] = path
print(f"✓ {len(names)} unique workflow names")
EOF
```

---

## Repository Asset Checks

```bash
# Required files
for f in dashboard/index.html dashboard/data.js requirements.txt environment.yml .github/labeler.yml; do
  [ -f "$f" ] && echo "✓ $f" || echo "MISSING: $f"
done

# Python scripts compile
python -m compileall scripts/ -q && echo "✓ all scripts compile"
```

---

## Code Quality Checks

```bash
ruff check scripts/build_dashboard_data.py scripts/release_gate.py
python -m pytest scripts/ -v --tb=short
```

---

## Environment Reference Check

```bash
python - <<'EOF'
import glob, yaml, pathlib
KNOWN = {"Development", "Preview", "Production", "Testing"}
for path in glob.glob(".github/workflows/*.yml"):
    doc = yaml.safe_load(pathlib.Path(path).read_text()) or {}
    for job_name, job in (doc.get("jobs") or {}).items():
        env = (job or {}).get("environment")
        if env and env not in KNOWN:
            print(f"UNKNOWN environment '{env}' in {path} job '{job_name}'")
        elif env:
            print(f"✓ {path} → environment: {env}")
EOF
```

---

## Manual Infrastructure Checks

These cannot be automated from the CLI. Verify manually before a major release:

- [ ] **Actions enabled:** Repo Settings → Actions → General → "Allow all actions and reusable workflows"
- [ ] **Billing:** github.com/settings/billing → Actions minutes remaining > 500
- [ ] **Environments exist:** Settings → Environments → `Development` listed
- [ ] **No GitHub incident:** githubstatus.com → GitHub Actions row is green
- [ ] **Branch protection:** main branch requires status checks (qc, repo-health)

---

## After Merge — Verify

1. Go to Actions tab on GitHub
2. Find the run triggered by your merge commit
3. Confirm ALL jobs show `conclusion: success` (not `startup_failure`, not `failure`)
4. If ANY workflow shows `startup_failure`: use `docs/runner-failure-runbook.md`
5. Confirm Deployments panel (repo main page → right sidebar) shows Development ✓

---

## Checklist Summary

| # | Check | Tool |
|---|---|---|
| 1 | No empty workflow files | `workflow-validation.yml` auto-blocks |
| 2 | All YAML parses | `workflow-validation.yml` auto-checks |
| 3 | Required files present | `repo-health.yml` auto-checks |
| 4 | Python scripts compile | `repo-health.yml` auto-checks |
| 5 | Environment names valid | `deployment-readiness.yml` auto-checks |
| 6 | Tests pass | `qc.yml` auto-checks |
| 7 | Billing / Actions enabled | Manual — browser |
| 8 | No GitHub incident | Manual — githubstatus.com |
