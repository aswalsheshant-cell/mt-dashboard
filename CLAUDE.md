# CLAUDE.md — Project guidance for Claude Code

Modern Trade (MT) leadership analytics for **Honasa / Mamaearth**. Two deliverables
live in this one repo:

---

## ENGINEERING CONSTITUTION (Load Before Every Task)

Before starting any task, follow these engineering standards in order:

1. **`docs/ENGINEERING_STANDARDS.md`** — 20 engineering laws, 4 governance layers, skill routing
2. **`docs/BUSINESS_RULES.md`** — Every business rule for Primary, Offtake, Allocation, P&L
3. **`docs/QC_FRAMEWORK.md`** — 10 QC gates; nothing ships without passing all gates

**Active Claude Skills (auto-activate based on task):**

| Skill | Activates for |
|---|---|
| `mt-enterprise-architecture` | Any change — architecture review first |
| `mt-data-governance` | Business logic, QC, reconciliation, data quality |
| `mt-intelligence-engine` | Insights, NKAM decisions, root cause, forecast |
| `mt-production-readiness` | Before marking anything complete |
| `mt-sql-analytics` | SQL queries for MT data |
| `mt-python-pipeline` | Python/Pandas automation scripts |
| `mt-financial-intelligence` | P&L, GM%, trade spend, financial analysis |
| `mt-executive-storytelling` | Leadership narratives, decks, QBR |
| `mt-powerbi-dax` | DAX measures, Power Query M, star schema |
| `mt-error-resolution` | Debugging, data issues, reconciliation failures |
| `mt-deck-builder` | Build QBR / leadership / NKAM / launch decks |
| `mt-trade-promotion` | Trade spend ROI, scheme analysis, BTL investment |
| `mt-campaign-analytics` | Promo experiments, A/B testing, attribution, ICE scoring |
| `mt-channel-decision-log` | NKAM decision log, commitments, channel intelligence |

**Feed project context to Claude (for deep-context sessions):**
```bash
pip install files-to-prompt
files-to-prompt dashboard/ scripts/ docs/ CLAUDE.md --ignore "data.js" --ignore "*.min.js" --cxml
```

---


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

## Architecture map

```
dashboard/
  index.html      single-file app: 12 tabs, global filter bar, drill-down, exports.
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

12 tabs (order): Data Explorer, Overview, Primary, Offtake, P&L, Category & Pack,
Forecast, Promo & Trade Spend, Market Share, Distribution, Performance &
Comparison, Insights & Way Forward.

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
