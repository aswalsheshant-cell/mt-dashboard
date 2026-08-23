# Workflow Governance Policy — mt-dashboard

## Policy Statement

Every `.github/workflows/` file is a production artifact. Changes to workflows follow
the same review standard as changes to `scripts/build_dashboard_data.py` or `dashboard/data.js`.
A broken workflow blocks every CI run until fixed — the blast radius is the entire team.

---

## Adding a New Workflow

Before creating a `.yml` file in `.github/workflows/`:

1. **Does an existing workflow already cover this?** Check `docs/ci-cd-standards.md` first. Do not duplicate.
2. **Name it clearly.** The `name:` field in the YAML is what shows in the Actions UI. Make it a noun phrase that states what it checks, e.g. "Repository Health" not "check".
3. **Declare the trigger explicitly.** Every workflow must have an `on:` key with at least one trigger. An `on: push` with no branches filter runs on every branch — confirm that is intended.
4. **Never commit an empty file.** `workflow-validation.yml` blocks this; don't try to push a placeholder.
5. **Reference only known environments.** This repo's environments are `Development`, `Preview`, `Production`. Any other `environment:` value will cause `startup_failure` on that job.
6. **Test locally before pushing:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('.github/workflows/new.yml'))"
   wc -c .github/workflows/new.yml
   ```

---

## Modifying an Existing Workflow

1. **Never leave the file empty** at any commit. Edit in one atomic change.
2. **Do not rename a workflow's `name:` field without updating `docs/ci-cd-standards.md`.**
3. **Do not change a workflow's trigger** without confirming the new trigger is intentional (e.g. removing a path filter changes `push` to run on all file changes).
4. **Changing `environment:`** requires verifying the environment exists first (Settings → Environments).

---

## Deleting a Workflow

1. Confirm no branch protection rule references it as a required check.
2. Remove it from `docs/ci-cd-standards.md` in the same commit.
3. Open a PR — do not delete directly on `main`.

---

## Workflow File Ownership

| File | Owner | Review required |
|---|---|---|
| `qc.yml` | Data Engineering | 1 approval |
| `dataeng.yml` | Data Engineering | 1 approval |
| `main.yml` | DevOps / Platform | 1 approval |
| `workflow-validation.yml` | DevOps / Platform | 1 approval |
| `repo-health.yml` | DevOps / Platform | 1 approval |
| `deployment-readiness.yml` | DevOps / Platform | 1 approval |
| `codeql.yml` | Security | 1 approval |
| `label.yml` | Platform | 1 approval |
| `python-package-conda.yml` | Data Engineering | 1 approval |

---

## Guard Workflows (Never Disable)

These three workflows exist to protect the CI system itself:

| Workflow | What it protects |
|---|---|
| `workflow-validation.yml` | Blocks empty/invalid workflow files from reaching main |
| `repo-health.yml` | Confirms required repo assets exist on every push |
| `deployment-readiness.yml` | Validates environment references before deployment |

Disabling any of these removes a layer of protection that has already caught a production incident (2026-08-23).

---

## Failure Classification Quick Reference

See `docs/runner-failure-runbook.md` for the full decision tree.

| Symptom | Do NOT do | DO |
|---|---|---|
| `startup_failure` on one workflow | Edit unrelated code | Check: file empty? environment missing? |
| `startup_failure` on ALL workflows | Edit any workflow YAML | Check: billing, Actions enabled, githubstatus.com |
| `conclusion: failure` with logs | Assume infrastructure | Read the job log; find the failing step |
| Deployment badge red | Assume code error | Classify: Category A–J first |
