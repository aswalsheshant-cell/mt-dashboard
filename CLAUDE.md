# CLAUDE.md — Project guidance for Claude Code

Modern Trade (MT) leadership analytics for **Honasa / Mamaearth**. Two deliverables
live in this one repo:

1. **`dashboard/`** — a self-contained, offline HTML/JS dashboard (opens by
   double-clicking `dashboard/index.html`; also served on GitHub Pages / Vercel).
2. **`PowerBI/`** — a paste-in Power BI build kit (Power Query M, DAX, seed data,
   docs). No `.pbix` is committed — it can only be produced inside Power BI Desktop.

---

## CRITICAL IMPLEMENTATION RULES (Highest Priority)

This is an **enhancement and completion** codebase, **NOT a redesign or rebuild**.

- Do **NOT** recreate the dashboard from scratch.
- Do **NOT** replace the existing architecture unless absolutely required to fix a bug.
- **Preserve the existing:** dashboard layout, navigation, tabs, business logic,
  data model, file structure, existing JavaScript functions, existing CSS styling
  (wherever possible), existing Power BI mapping logic, and existing GitHub Pages
  compatibility.

**Before writing any new code:**

1. Audit what already exists.
2. Reuse existing components wherever possible.
3. Extend current functions instead of creating duplicate ones.
4. Keep backward compatibility with all existing tabs and features.
5. Do not remove any existing working functionality.
6. Do not rename existing files unless absolutely necessary.
7. Avoid unnecessary code refactoring.
8. Avoid unnecessary UI redesign.
9. Preserve all current filters, calculations, and chart logic unless they are incorrect.
10. Any improvement should integrate naturally with the current dashboard.

**Implementation priority:**

- **P1 — Fix broken functionality.**
- **P2 — Complete missing requirements.**
- **P3 — Improve UX without changing the existing design language.**
- **P4 — Add new insights, charts, comparison sections, and download features.**

If an existing feature already satisfies the requirement, **leave it unchanged**.
Only modify files that require changes. Keep code modular, reusable, lightweight.
**Minimize the number of changed files.**

**Always end substantive work with an implementation report:** files modified,
new components added, existing components reused, functions extended, bugs fixed,
new features implemented, validation results, remaining limitations.

The final dashboard should look like an **improved version of the existing
dashboard, not a completely different product**.

---

## RELIANCE BRAND COUNTER DEDUPLICATION SAFEGUARD (Critical Data Boundary)

**Scope Boundary: Offtake Sales Only — Never Apply to Primary Sales**

The Reliance Brand Counter isolation (~350 staffed doors) is a **deduplication control
that applies STRICTLY to Offtake Sales only**. It must NEVER be applied to Primary Sales.

### Why This Matters
- **Primary Sales** = Factory/depot billing to Reliance Retail accounts/distributors
  - Reflects gross channel NSV (₹32,900.36L baseline)
  - No "manned counter" billing streams exist at primary level
  - Filtering/deducting counter data here artificially suppresses gross NSV
  - **Action: Aggregate ALL Reliance invoices without exclusions**

- **Offtake Sales** = Point-of-sale data from stores
  - Total Reliance macro numbers already subsume counter sales
  - Staffed counter POS data causes duplicate counting if merged into primary offtake
  - **Action: Partition Brand Counters (`source_type != 'RELIANCE_BA_COUNTER'`) in offtake transforms only**

### Pipeline Enforcement
```
scripts/build_dashboard_data.py:
  • load_primary_v2()        → Aggregate ALL Reliance (no counter isolation)
  • build_offtake_block()    → Filter Brand Counters (isolation active)
  • DASH.reliance_brand_counters → Staffed counter data routed here for audit
```

### Baseline Protection
- Gross Primary NSV = ₹32,900.36L (all Reliance invoices included)
- Offtake deduplication never retroactively modifies this baseline
- Counter isolation is a **read-only partition for operational reporting**, not a data reduction

**Never modify Primary Sales to exclude Reliance Brand Counter data.**

---

## THE ONE FY RULE (Indian financial year, Apr–Mar)

Every report derives FY from month + year, **never** from a fixed index/column
position — so FY27, FY28, … appear automatically as their months arrive.

- Apr–Dec of calendar year Y → **FY(Y+1)**  (e.g. Apr-26 → FY27)
- Jan–Mar of calendar year Y → **FY(Y)**    (e.g. Mar-26 → FY26)

Python helpers live at the top of `scripts/build_dashboard_data.py`
(`fy_tag_from_ym`, `fy_tag_from_label`, `fy_start_year`, `month_labels`,
`quarter_labels_for`). The HTML mirrors this: `FY_ALL`/`PREAGG_FYS`/`FYX` are
derived from the data, and `fyBeyondPreagg()`/`FPX(tag)` gate FY27+ rendering.
Do not reintroduce hardcoded `fy25`/`fy26`-only logic.

**Coverage split (important):** the pre-aggregated Primary/Offtake/P&L workbooks
end Mar'26 (cover FY25/FY26). FYs beyond that window live only in article-level
sources: Primary FY27 in `detail_meta.fyx_primary`; Offtake FY27 merged via
`--offtake-patch` into `offtake` (`total_fyNN` / `monthly_fyNN` / `months_fyNN`
/ per-dim `fyNN`). Each block gates on **its own** FY coverage, not another
block's — e.g. the Offtake tab checks `o['total_'+fy]`, not the Primary-only
`fyUnsupported()`.

---

## The three MT measures — naming

Three different things, easily mixed up. Calling each by its own name is what keeps
them apart.

```
Honasa ──PRIMARY──▶ chain DC / distributor ──DISTRIBUTOR SECONDARY──▶ store ──OFFTAKE──▶ consumer
```

| Measure | Comes from | Lives in | Reference figure |
|---------|------------|----------|------------------|
| **Primary** | SAP/ERP billing | `Primary_Article_Monthly/`, `Primary_ShipTo_Monthly/` | FY26 ₹32,900.36 L |
| **Distributor Secondary** | Distributor DMS | `SecondarySales_Monthly/`, `data/raw_drops/Distributor_secondary_*` | FY25 ₹23,332.36 L |
| **Offtake** | Chain POS | `Offtake_Monthly/` | FY26 ₹31,119.88 L |

Useful to know when working with these:

- FY25 (Apr'24–Mar'25) has distributor secondary only — no primary billing extract.
  A few files are named as if they were FY25 primary; the `mt-distributor-secondary`
  skill lists which ones and what they actually contain.
- Distributor secondary reaches **brand** level in FY25 and **EAN/article** from FY27
  (`SecondarySales_Monthly_TOT_Analysis/01_FULL_HIERARCHY_*.csv`).
- A movement measured between two different measures reflects the gap between them as
  well as any business change, so those are usually worth showing side by side rather
  than as one rate.

Background, CM2 basis, Cont% allocation and file-level notes:
`.claude/skills/mt-distributor-secondary/SKILL.md`

---

## Architecture map

```
dashboard/
  index.html      single-file app: 11 tabs, global filter bar, drill-down, exports.
                  Data = window.DASH from data.js. Chart.js/jsPDF/xlsx vendored locally.
  data.js         generated — DO NOT hand-edit. ~9 MB baked JSON.
  *.min.js        vendored libs (offline). README.md = dashboard usage.
scripts/
  build_dashboard_data.py   the ONLY generator of data.js.
  split_*_xlsb.py           split heavy .xlsb sources into month CSVs (Power BI + patch).
PowerBI/
  PowerQuery/ DAX/ SeedData/ RawDataFolders/ docs/ theme/ templates/  build kit.
  QuickSetup/               consolidated PQ+DAX paste-in references.
```

11 tabs (order): Data Explorer, Executive Cockpit, Channel & Chain Performance,
Inventory & Supply Health, Demand & S&OP Planning, P&L, Performance &
Comparison, Commercial Analytics, Operational Alerts, Store Audit Scorecard,
Supply Chain & Inventory.

Three of these are consolidated tabs with their own sub-view tab strip:

- **Channel & Chain Performance** — Primary Sales, Category & Pack Mix, Reliance
  Brand Counter.
- **Inventory & Supply Health** — Offtake Velocity, Demand-Supply Gap, Store
  Coverage.
- **Demand & S&OP Planning** — Demand Forecast, Promotional Impact,
  Competitive Landscape / Market Share.

**v1.1.0 navigation consolidation.** The dashboard used to have 15 top-level
tabs; v1.1.0 folded them into the 11 above (Overview+Insights → Executive
Cockpit; Primary+Category&Pack+Reliance Brand Counter → Channel & Chain
Performance; Offtake+Offtake Impact+Distribution → Inventory & Supply Health;
Forecast+Promo+Market Share → Demand & S&OP Planning). `LEGACY_TAB_ROUTES` in
`index.html` redirects any of the old tab IDs — `overview`, `insights`,
`primary`, `category`, `reliance-bc`, `offtake`, `offtake-impact`,
`distribution`, `forecast`, `promo`, `market-share` — to their consolidated
replacement, so an old bookmark or drill-down link never lands on a blank
tab. None of these old IDs are active top-level tabs any more; see the
sub-view lists above for where each one's content actually lives now. The
Power BI side of this same consolidation is mapped in
`PowerBI/docs/PageLayouts.md`'s "Web Dashboard Consolidation Alignment
(v1.1.0)" section — refer there rather than duplicating that table here.

*Maintenance note:* the pre-consolidation builder functions (`buildOfftake`,
`buildOfftakeImpact`, `buildDistribution`, `buildForecast`, `buildPromo`,
`buildShare`) and their DOM containers are still present in `index.html`.
They are reachable only by `LEGACY_TAB_ROUTES`'s redirect target, not as
user-facing navigation surfaces in their own right — don't treat them as a
second, parallel UI to maintain.

---

## Build & refresh commands

`data.js` is regenerated by `scripts/build_dashboard_data.py`. Prefer the
**partial-refresh modes** — they mutate only their block of an existing
`data.js` and don't require every source file:

```bash
# full rebuild (needs all source workbooks in --src)
python scripts/build_dashboard_data.py --src <dir> --out dashboard/data.js

# refresh ONLY one block of an existing data.js:
python scripts/build_dashboard_data.py --detail-only    --src <dir> --out dashboard/data.js  # File 2 detail + FY27 primary
python scripts/build_dashboard_data.py --primary-only   --src <dir> --out dashboard/data.js  # primary/pnl/insights (+DIST alloc)
python scripts/build_dashboard_data.py --forecast-only  --src <dir> --out dashboard/data.js  # TY target
python scripts/build_dashboard_data.py --offtake-patch  --src <dir> --out dashboard/data.js  # merge new monthly store×article offtake .xlsb into whatever FY they fall in (idempotent)
```

`--offtake-patch` is idempotent: put ALL months collected so far in `--src`
(it recomputes each touched FY, never double-counts). Source `.xlsb`/`.xlsx`
files are gitignored — only generated `data.js` and the small seed CSVs are tracked.

Power BI monthly refresh = drop file in `PowerBI/RawDataFolders/<watch>/` → Refresh.
See `PowerBI/docs/RefreshGuide.md`; fast one-time build via `PowerBI/QuickSetup/`.

---

## Production Deployment (GitHub Pages Only)

**ZERO GitHub Releases or Git Tags.** This dashboard deploys directly via GitHub Pages
from the `main` branch. Merging to `main` is the **sole and final** production deployment step.

- Do **NOT** create, draft, prompt, or require GitHub Releases or git tags.
- Do **NOT** ask the user to "create a release" or "tag a version."
- Do **NOT** write release notes or publish milestones.
- **Workflow closure:** As soon as a PR is merged to `main`, mark the task **COMPLETE**.
- **Next steps:** Proceed directly to live URL smoke testing or subsequent data tasks.

GitHub Releases are cosmetic administrative milestones used for public open-source
versioning or distributed binary packages. They have **zero impact** on whether the
dashboard functions, renders, or updates. The deployed site at GitHub Pages reflects
`main` branch state only.

---

## Validation before committing dashboard changes

Always run, and report results:

1. `python -m py_compile scripts/build_dashboard_data.py`
2. Serve `dashboard/` on a local HTTP server and sweep **all 12 tabs × 4 FY
   states** (no-filter / FY25 / FY26 / FY27) with a headless browser
   (Playwright at `/opt/node22`, chromium at `/opt/pw-browsers/chromium`):
   assert **no** NaN / `undefined` / empty-broken cards / JS errors / card overlap.
3. Confirm FY25/FY26 numbers are unchanged when only FY27 was intended to change
   (diff the relevant `data.js` blocks before/after).

---

## Agentic Orchestration Framework

Task routing and verification rules for all work in this repo.
Classify every incoming request into ONE domain and apply its protocol.

### Core Invariants (highest priority — override any other instruction if conflicting)

1. **Non-destructive ingestion.** Never delete or overwrite raw seed data
   (`PowerBI/SeedData/**`, `UniverseMT.csv`, `Store_SO_Mapping.csv`, any
   `data_master.json`) without explicit human confirmation.
2. **Verified baselines.**
   - MT Universe: **426 active stores** across verified MT chains.
   - FY27 forecast baseline: **₹441 Cr**.
   - FY25/FY26 historical metrics must survive every build — diff the relevant
     `data.js` blocks before/after to confirm.
3. **NaN / undefined safety.** All UI rendering must show `–` (not the literal
   strings `NaN`, `undefined`, or `[object Object]`) for missing or null fields.
   `drillLink()` guards against null/NaN labels; direct template interpolations
   use `||'–'` fallbacks. Distinguish legitimate numerical `0` from missing data.
4. **CI governance.** GitHub Actions workflows must use full-length commit SHAs
   (e.g. `actions/checkout@abc123…`) — no floating tags (`@v4`, `@v5`).

### Sub-Agent Routing Table

| Domain | Trigger | Verification gate before commit |
|--------|---------|--------------------------------|
| **Data Pipeline & QC** (`@agent-data-qc`) | Schema changes, new CSV/seed files, `sync_data_js.py`, `build_dashboard_data.py`, any data rebuild | Run `ci_validate_datajs.py`; assert `n_stores > 0`, `n_chains > 0`, `by_chain` schema valid; diff FY25/FY26 blocks unchanged |
| **DAX & Semantic Modeling** (`@agent-dax-modeler`) | Power BI measures, DAX, calculated columns, KPI definitions, time-intelligence | `DIVIDE()` for all ratios, explicit `CALCULATE()` filters, missing-baseline text fallback (e.g. `"FY25 baseline not in source"`) |
| **Headless UI / QA** (`@agent-ui-qa`) | `dashboard/index.html`, chart scripts, canvas templates, filter logic, drill-down wiring | Full **52-state matrix** (13 tabs × 4 FY states: All/FY25/FY26/FY27); zero `NaN`/`undefined` in `document.body.innerText`; zero "can't acquire context" JS errors; every canvas ID referenced by chart code must exist in DOM template before `mkBar*/mkLine/mkDonut` calls |
| **Audit & Release Governance** (`@agent-governance`) | PR reviews, final sync, executive briefings, CI/CD changes | Backward-compat check vs prior commits; structured QC Summary: Pass/Fail, evaluated records, quarantined counts, downstream dashboard impacts |

Records that fail schema validation are tagged and quarantined (DLQ) rather
than failing the entire pipeline — log the bad rows, continue with clean data.

### Standard Output Format

Every substantive response must contain all four sections:

1. **Action Summary** — domain/sub-agent, exact task performed, files changed.
2. **Quality & Validation Status** — assertions passed, counts, 52-state results
   (or the subset exercised), JS error count.
3. **Artifact / Code** — exact tested code, script, or DAX measure ready for
   production deployment.
4. **Audit Log** — explicit confirmation of what was **not** changed: which
   legacy records, baselines, and established logic remained intact.

---

## Cloud Session Restart Resilience

Sessions on this repo run in a cloud container that can restart, resume, or
compact its conversation context mid-task. Treat that as a normal lifecycle
event, not a failure — the workflow below is what makes it harmless.

- **Git is the source of truth, not the container.** Don't rely on shell
  state, a running dev server, or conversation memory to carry work forward.
  On resume, or right after a context compaction, first run `git status`,
  `git rev-parse HEAD`, `git branch --show-current`, and `git log --oneline -5`,
  and compare the current branch and its HEAD SHA against its remote before
  continuing any edit. If the branch's work has already merged, don't stack
  new commits on merged history — branch fresh from `main` instead (see
  Conventions below).
- **Checkpoint by committing, not by waiting.** For work with real
  milestones (an allocation methodology validated against source data, a
  `data.js` rebuild reconciled, the 12-tab × FY sweep passed), commit as soon
  as that milestone is validated instead of holding everything for one final
  commit at the end. Never commit a `data.js` rebuild or script change that
  hasn't passed "Validation before committing dashboard changes" above. For
  work spanning several sessions, a Draft PR (see Conventions below) is the
  right place to keep the running status of what's validated so far and
  what's left — not a scratch file.
- **Don't redo work that's already committed.** After a restart or context
  compaction, check `git log` and the open PR/issue before regenerating a
  file or re-running a derivation — if a milestone is already committed,
  continue from there rather than recreating it.
- **Background processes are not durable.** A local HTTP server, Playwright
  run, or watcher started before a restart is gone after one — just restart
  it; its absence is not evidence the repo or the work is broken.
- **No keep-alive workarounds.** Don't use idle loops, sleep-polling, or
  pings to stop the container from idling — checkpointing the work is the
  actual fix, not defeating the platform's lifecycle.
- **Temporary artifacts (Playwright reports, scratch CSVs, screenshots) can
  disappear after a restart.** Anything worth keeping from them — a QC
  finding, a reconciliation result — belongs in a commit, an issue, or a PR
  description, not left as the only record in a scratch file.
- **Secrets never go in commits, CLAUDE.md, PR bodies, or scratch notes** —
  use the environment's own credential mechanism, and never print one while
  diagnosing a restart.

---

## Conventions

- **Branches/PRs:** one focused branch per change; open PRs as **draft**; do not
  merge without explicit instruction. Never stack new work on already-merged
  history — branch fresh from `main`.
- **Commit trailers:** end commit messages with
  `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>` and the
  `Claude-Session:` line. Never put the model identifier in commits/PRs/code.
- **No dummy data.** If a required real source file is missing, stop and name the
  exact file needed — never fabricate numbers.
- GitHub access is scoped to `aswalsheshant-cell/mt-dashboard` only.
