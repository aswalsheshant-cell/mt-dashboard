# MT Platform — Operations Runbook (V1)

Day-to-day operation of the Modern Trade analytics platform. Commands here are
meant to be run, not read.

For what the project *is* and what must not change silently, see `CLAUDE.md`.
For current status and the next approved task, see `docs/PROJECT_STATE.md`.

---

## 0. Where the source data lives

Source workbooks are **not in Git** and never will be — they carry employee
identity, incentive rates and commercial detail. `.gitignore` and
`tests/test_published_assets_privacy.py` enforce that.

**Approved durable location: `D:\sALES & eXPENSES`** (local Windows storage).

The repository stores *how to find the input*, never the input itself. Nothing is
hardcoded to that path — every script takes the location as an argument or an
environment variable, so a different machine only changes the value.

### The one thing that bites

That folder name contains a space **and** an ampersand. In a shell, an unquoted
`&` ends the command and backgrounds it. **Always quote the path.**

```bash
# WRONG - the shell splits at the &, the script never sees the full path
--employees D:\sALES & eXPENSES\Employee_wise_grade_for_payment.xlsx

# RIGHT - quoted
--employees "D:\sALES & eXPENSES\Employee_wise_grade_for_payment.xlsx"
```

Set it once per session instead of retyping it:

```bash
# Git Bash / WSL
export MT_SRC="/d/sALES & eXPENSES"

# PowerShell
$env:MT_SRC = "D:\sALES & eXPENSES"
```

### Durability, honestly

This location survives a cloud container being replaced, because it is not in the
container. It does **not** give GitHub Actions or a cloud session access to the
files — anything needing them runs on the machine that has the D: drive. If that
drive is not backed up, it is a single point of failure. Moving to approved
company storage (SharePoint, OneDrive, a data lake) later changes only the value
of `MT_SRC`, not any code.

---

## 1. Start a session

```bash
git pull origin main
./scripts/setup_environment.sh      # only needed on a fresh machine or container
```

The SessionStart hook prints repo state, resources and the next approved task
automatically. If dependencies are missing it restores them with `npm ci`.

---

## 2. Validate before you trust a number

```bash
python3 scripts/ci_validate_datajs.py          # JSON + 7 baseline invariants
python3 -m unittest discover -s tests -p "test_*.py"
```

Expected: `OK baseline invariants hold (7 checked)` and `64 passed, 1 skipped`.

A baseline failure names the figure, the class and who approves a change. A
`frozen_history` failure is a build defect — investigate, never "update the
baseline to match".

---

## 3. Refresh dashboard data

```bash
# one block only - preferred, does not need every source workbook
python3 scripts/build_dashboard_data.py --primary-only  --src "$MT_SRC" --out dashboard/data.js
python3 scripts/build_dashboard_data.py --offtake-patch --src "$MT_SRC" --out dashboard/data.js
python3 scripts/build_dashboard_data.py --detail-only   --src "$MT_SRC" --out dashboard/data.js

# full rebuild - needs all source workbooks present
python3 scripts/build_dashboard_data.py --src "$MT_SRC" --out dashboard/data.js
```

`--offtake-patch` is idempotent: put **all** months collected so far in `--src`.

---

## 4. Dashboard QC (run before every commit that touches the dashboard)

```bash
python3 -m py_compile scripts/build_dashboard_data.py
bash scripts/run_dashboard_sweep.sh tests/dashboard_sweep.js
```

Expected: `states swept: 44 | failing: 0 | total JS errors: 0`. The sweep reads
the tab list from the page, so the count follows the dashboard.

---

## 5. Incentive working model (restricted)

Outputs land in `incentive_working/`, which is gitignored. Never commit them.

```bash
python3 scripts/target_scope_diagnostic.py \
  --targets "$MT_SRC/All_India_RKAM_Target_Planning__Compiled_File.xlsx"

python3 scripts/build_actual_attribution.py \
  --woa    "$MT_SRC/WOA_APril26_to_July26_working_sheet.csv" \
  --massit "$MT_SRC/Massit_apr26.csv" "$MT_SRC/Massit_may26.csv" \
           "$MT_SRC/Massit_june26.csv" "$MT_SRC/Massit_july26.csv"

python3 scripts/build_incentive_workbook.py \
  --employees "$MT_SRC/Employee_wise_grade_for_payment.xlsx" \
  --slabs     "$MT_SRC/INCENTIVE_SLAB.xlsx" \
  --targets   "$MT_SRC/All_India_RKAM_Target_Planning__Compiled_File.xlsx"
```

Run them in that order — the workbook reads what the first two produce.

If a file is missing, the script stops with its name and purpose and produces
nothing. That is intended. Supply the real file; nothing is ever substituted.

---

## 6. Update a business baseline

Only when the change is genuinely approved.

1. Edit `config/baselines.json` — change the value, and say why in `why`.
2. `python3 scripts/ci_validate_datajs.py`
3. Commit the baseline edit **on its own**, so review sees the figure change.

`frozen_history` entries are closed years and should never need this.

---

## 7. Skills

```bash
python3 skill-suite/scripts/validate_skills.py                      # before any edit
python3 skill-suite/scripts/sync_skills.py --check  --target project-claude
python3 skill-suite/scripts/sync_skills.py --install --target project-claude
```

Edit skills in `skill-suite/` (canonical) — never in `.claude/skills/`, which is
generated. Hand-written skills in `.claude/skills/` that are not in the receipt
are never pruned by sync.

---

## 8. Release

There are **no tags and no GitHub Releases** in this project. Merging to `main`
deploys via GitHub Pages and is the whole release process.

```bash
git checkout -b <branch> main
# work, commit
git push -u origin <branch>
# open a DRAFT PR, wait for CI and review, then merge
```

---

## 9. Recover in a new environment

```bash
git clone <repo> && cd mt-dashboard
./scripts/setup_environment.sh
python3 scripts/ci_validate_datajs.py
bash scripts/run_dashboard_sweep.sh tests/dashboard_sweep.js
```

This reproduces the dashboard completely — verified from a clean clone.

Incentive outputs need the workbooks from `D:\sALES & eXPENSES`; point `$MT_SRC`
at them and re-run section 5. Nothing is lost, because every output is
regenerable and no output is a system of record.

---

## 10. Roll back

```bash
git log --oneline -10
git revert <sha>            # each commit is independently reversible
```

Never force-push a shared branch. Never rewrite history on someone else's branch.
