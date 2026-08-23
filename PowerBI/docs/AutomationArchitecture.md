# Power BI Build Kit — Automation Architecture (Stage 1: Research, Gap Analysis, Target Architecture)

**Status:** Stage 1 deliverable — research and design only. **No pipeline code, no
config directory, no workflow changes have been made by this document.** Stage 2
(implementation) starts only after the architecture below is approved.

**Date:** 2026-08-16 · **Repo state:** `main` @ `59da1f4` (issue-#23 Phase 6 merged)

---

## 0. How to read this, and how it was verified

This document answers the ten deliverables in the automation brief. Two rules were
applied throughout:

1. **Preserve → Assess → Identify gaps → Standardize → Automate → Add QC gates → Deploy.**
   Nothing existing is proposed for replacement unless a specific defect is named.
2. **Confirmed fact vs. recommendation is marked explicitly.** Repository facts were
   verified by reading the files. Microsoft platform facts were verified against
   `learn.microsoft.com` and the Fabric/Power BI blogs.

> **Verification caveat, stated plainly:** in this session direct page fetches to
> `learn.microsoft.com` were blocked by the network egress proxy. Microsoft claims
> below come from indexed search results over official Microsoft domains
> (`learn.microsoft.com`, `powerbi.microsoft.com`, `blog.fabric.microsoft.com`,
> `microsoft.github.io`), not from reading the rendered pages end-to-end. Every such
> claim carries its source link in §11. **Before Phase F/G work begins, re-verify the
> licensing and API prerequisites in §7 and §8 directly against those pages** — they
> gate spend, and Microsoft has active deprecation dates landing in 2026.

Legend used in tables: **[F]** = confirmed fact (verified in repo or MS docs) ·
**[R]** = recommendation · **[A]** = assumption needing your confirmation.

---

## 1. Deliverable 1 — Current-State Architecture

### 1.1 The two halves of the repo

The repo contains **two deliverables that share source data but share no code path.**

```
                    ┌──────────────────────────────────────────────┐
   RAW MONTHLY      │  .xlsb / .xlsx business files (GITIGNORED,   │
   BUSINESS FILES   │  live only on the analyst's machine/Drive)   │
                    └───────────────┬──────────────────────────────┘
                                    │  scripts/split_*_xlsb.py
                                    │  scripts/extract_xlsx_to_csv.py   (manual, local)
                                    ▼
                    ┌──────────────────────────────────────────────┐
                    │  PowerBI/RawDataFolders/**.csv    (31 tracked)│
                    │  PowerBI/SeedData/**.csv          (masters,  │
                    │      mapping, DIST weights, targets)         │
                    └───────┬──────────────────────────┬───────────┘
                            │                          │
        ══════ AUTOMATED ═══╪══════════      ══════════╪═══ MANUAL ══════
                            ▼                          ▼
        scripts/build_dashboard_data.py       Power BI Desktop (local .pbix,
          + dist_allocation_governance.py       NOT in repo)
                            │                    ▲ paste-in from
                            ▼                    │ PowerQuery/*.pq + DAX/*.dax
                    dashboard/data.js            │ (one-time, ~2-3 hrs GUI)
                            │                    │
                            ▼                    ▼
              .github/workflows/qc.yml     Home ▸ Refresh (human clicks)
              .github/workflows/dataeng.yml       │
                 → scripts/qc_dashboard.py        ▼
                 → Playwright browser sweep   Page 12 eyeball check (human)
                            │                     │
                            ▼                     ▼
                  Vercel (vercel.json) /      Publish to Service (human)
                  GitHub Pages
```

### 1.2 Classification of every component

| Component | Files | Classification |
|---|---|---|
| Dashboard data build | `scripts/build_dashboard_data.py` (3,659 lines) | **Automated** — full + 4 partial-refresh modes |
| DIST governance engine | `scripts/dist_allocation_governance.py`, imported at `build_dashboard_data.py:27` | **Automated & authoritative** — 5-tier gate + zero-tolerance reconciliation run inline in the build |
| Dashboard QC gate | `scripts/qc_dashboard.py` (449 lines, 4 statuses PASS/WARN/FAIL/BLOCKED) | **Automated** — incl. headless-Chromium tab sweep |
| Dashboard CI | `.github/workflows/qc.yml`, `dataeng.yml` | **Automated but duplicated** — see gap G-08 |
| Dashboard deploy | `vercel.json` (`outputDirectory: dashboard`) | **Automated** — via Vercel's own GitHub integration, no workflow file |
| Skill-suite governance | `.githooks/pre-commit`, `skill-suite/scripts/validate_skills.py`, `sync_skills.py` | **Automated** — an existing, working validate/sync/drift-check pattern worth reusing (see §4.4) |
| Raw → CSV extraction | `scripts/split_primary_article_xlsb.py`, `split_offtake_store_article_xlsb.py`, `extract_xlsx_to_csv.py` | **Semi-automated** — scripts exist, invocation is manual with hand-passed `--header-row` |
| DIST patch consolidation | `scripts/consolidate_dist_patches.py` | **Semi-automated** — run by hand, not wired to CI |
| Power BI model definition | `PowerBI/PowerQuery/*.pq` (28 files), `PowerBI/DAX/*.dax` (14 files) | **Manual** — text to paste into Desktop; no machine-consumable model artifact exists |
| Power BI refresh | `PowerBI/docs/RefreshGuide.md` §1–4 | **Manual** — drop file, Home ▸ Refresh, eyeball Page 12 |
| Power BI publish | RefreshGuide.md §"Quick monthly checklist" | **Manual** |
| Power BI page assembly | `PowerBI/docs/PageLayouts.md` (14 pages specified) | **Manual, one-time** |
| Power BI QC | `PowerBI/DAX/06_DataQuality_Measures.dax` (Page 12) | **Manual** — measures compute counts; a human reads them |
| Article allocation eligibility in PBI | `PowerBI/DAX/09_ArticleAllocation_Eligibility.dax` (159 lines) | **Duplicated** — a second, independent implementation of the Python 5-tier logic |
| Pre-refresh validation of raw files | — | **Missing** |
| Schema / data contracts | — | **Missing** as data; exists only as prose in 3 places (G-05) |
| Dataset/page status metadata | — | **Missing** entirely |
| Sample/WIP data framework | — | **Missing** entirely |
| Run manifest / audit trail | — | **Missing** (partial: `alloc.governance` block inside `data.js`) |

### 1.3 The fragile points — verified defects, not opinions

These are the findings that matter most, all confirmed by reading the files.

**G-01 — `41_DistContWeights.pq` reads a file that is not in the repo. [F] P1**
`PowerBI/PowerQuery/41_DistContWeights.pq:20` sources
`pRootFolder & "\RawDataFolders\Dist_primary_cont_based_on_secondary_MOM.xlsx"`.
That `.xlsx` is gitignored (`.gitignore` line `*.xlsx`) and is **not present in the
repo**. Meanwhile the governed, git-tracked, patch-approved seed
`PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv` (27 data rows, carrying
`Approval_Status`, `Approved_Date`, `Basis`, `Patch_File` audit columns) **exists and
is consumed by Python** (`build_dashboard_data.py:2411`).

*Consequence:* the Power BI model and the HTML dashboard are allocating distributor
primary from **two different inputs**, and the Power BI one cannot be reproduced from
the repository by anyone. The brief assumed query 41 had been migrated in Phase 1 —
it has not. This is the single highest-value fix in the whole programme and it is a
~15-line M change.

**G-02 — `ChainAllocationWeights.csv` does not exist; Python silently falls back to the gitignored XLSX. [F] P1**
`build_dashboard_data.py:292` prefers `PowerBI/SeedData/DIST/ChainAllocationWeights.csv`,
else falls back to `Dist_primary_cont_based_on_secondary_MOM.xlsx` Sheet2. `ls
PowerBI/SeedData/DIST/` shows **only** `DistPrimaryContWeightsArticle.csv`. So the
*chain-level* weights path is not repo-reproducible either, and `return None` on a
missing file means the failure is **silent** — allocation degrades rather than stops.
This violates the fail-closed principle you asked for.

**G-03 — Governance logic exists twice, in two languages, with no equivalence test. [F] P2**
Python `dist_allocation_governance.py` defines tiers `Eligible / Eligible_TAT /
Brand_Not_Listed / Article_Not_Listed / Not_Eligible` with confidence percentages.
DAX `09_ArticleAllocation_Eligibility.dax` independently defines
`Eligibility Status` = `Eligible / Eligible due to TAT / Brand not listed / Article
not listed` — same concept, **different string values**, no confidence, and its
`Blocked Primary NSV` uses a different rule (chain-brand denominator = 0) than
Python's tier assignment. Nothing tests that they agree. This is the duplication the
brief warned about, and it already exists.

**G-04 — Python's TAT window and DAX's TAT window differ. [F] P2**
Python docstring and `check_eligibility` describe TAT as **"within ±3 months"**
(`dist_allocation_governance.py:16, 100–106`). DAX defines TAT as **M+1 only**
(`09_ArticleAllocation_Eligibility.dax:6–7, 25–26`). These are not the same business
rule. One of them is wrong. **Needs business confirmation** (see MIR-01).

**G-05 — The data contract is prose, restated in three-plus places. [F] P2**
The Offtake column list appears in `RefreshGuide.md` §3, in
`RawDataFolders/Offtake_Monthly/_README.txt`, and as a hard-coded
`Table.SelectColumns(...)` in `11_Fact_OfftakeSales.pq`. The Primary-Article list
appears in `16_Fact_PrimaryArticle.pq`'s header comment, in its `SelectColumns`, and
in `docs/DistributorPrimaryAllocation_Logic.md` §"File 2 header mapping — LOCKED".
Nothing validates a delivered file against any of them. Header drift is caught only
when Power Query throws, or silently as nulls via `MissingField.UseNull`.

**G-06 — Three of six fact tables have no data at all. [F] P2**
`git ls-files` on `RawDataFolders/`: Primary_Article 16 data files, Offtake 3,
Primary_ShipTo 1 — but **Primary_Weekly, Nielsen_Monthly and TDP_Monthly contain only
`_README.txt` + `_TEMPLATE_*.csv`**. Pages 9 (Nielsen), 10 (TDP) and every weekly-grain
visual therefore have no production source. This is exactly the "incomplete data must
not block development" case, and today it has no controlled representation — the
pages would simply render empty or error.

**G-07 — Nothing validates the Power BI side. [F] P2**
`qc_dashboard.py` parses `dashboard/data.js` only. Zero automated checks run against
`RawDataFolders/`, `SeedData/`, the `.pq`/`.dax` text, or any Power BI artifact. The
CI badge being green says nothing about whether next month's Power BI refresh will
succeed.

**G-08 — The two CI workflows overlap almost completely. [F] P3**
`qc.yml` and `dataeng.yml` both check out, install the same deps, `py_compile` the
build script, run four of the same pytest files, and run `qc_dashboard.py`. `qc.yml`
additionally runs `qc_dashboard.py` **twice** (lines 34 and 40) — once for the log,
once to grep its own output. Consolidating is safe, cheap, and removes a place for the
two to drift apart.

**G-09 — There is no model artifact to version, diff, deploy or roll back. [F] P1 for automation**
No `.pbix`, no `.pbip`, no `.bim`, no TMDL. The model exists as 42 text files a human
retypes into a GUI. Every automation ambition downstream (refresh API, deployment
pipeline, post-refresh QC via XMLA) is blocked on this one fact.

**G-10 — `docs/Desktop_Assembly_Checklist.md`, referenced in the brief, does not exist. [F] P3**
`ls PowerBI/docs/` returns seven files; that is not one of them. `PowerBI/README.md`
§"One-time setup" (steps 1–11) is the de facto assembly checklist.

**G-11 — `DistCont_Patch_Proposed.csv` is header-only. [F] info**
1 line, no rows. The propose → approve → consolidate workflow described in
`DistributorPrimaryAllocation_Logic.md` §"Nearest-month fallback + patch-proposal
workflow" is real but currently idle. Good — it means the workflow can be formalised
without disturbing pending business decisions.

### 1.4 What is already right, and must be preserved

Stated explicitly so Stage 2 does not "improve" these:

- **The `--*-only` partial-refresh modes** in `build_dashboard_data.py` are the correct
  automation primitive. `--offtake-patch` being *idempotent* (recomputes each touched
  FY, never double-counts) is exactly the property a pipeline needs. Build on these.
- **The FY derivation rule** (`fy_tag_from_ym` etc.) is data-driven, not index-driven.
  Any config schema must not reintroduce a hardcoded FY list.
- **The four-status QC vocabulary** (PASS / WARN / FAIL / BLOCKED) with BLOCKED meaning
  "documented data dependency, needs business approval not a code fix" is already the
  right model for a WIP framework. **Extend it — do not invent a parallel vocabulary.**
- **`fnCombineFolder`'s `_`-prefix ignore rule** and its automatic `[Data Source File]`
  + `[Refresh Date]` audit columns are a working lineage primitive.
- **The DIST seed's audit columns** (`Source, Approved_Date, Approval_Status, Basis,
  Patch_File`) are already a governed-input pattern. Generalise this shape, don't
  design a new one.
- **The skill-suite `validate → sync → --check drift` pre-commit pattern** is a proven
  in-repo template for contract enforcement.

---

## 2. Deliverable 2 — Automation Gap Matrix

Priority uses the CLAUDE.md scale: P1 fix broken, P2 complete missing, P3 UX, P4 new.

| # | Component | Current state | Target state | Gap | Solution | Pri | Dependency |
|---|---|---|---|---|---|---|---|
| G-01 | DIST article weights → PBI | PQ 41 reads gitignored XLSX | PQ 41 reads governed CSV seed | PBI not repo-reproducible; two sources of truth | Rewrite `41_DistContWeights.pq` to `Csv.Document(File.Contents(pRootFolder & "\SeedData\DIST\DistPrimaryContWeightsArticle.csv"))`, filter `Approval_Status="Approved"`, keep the `Raw Pct Sum` QC column | **P1** | none — do first |
| G-02 | DIST chain weights → Python | `ChainAllocationWeights.csv` absent; silent XLSX fallback | Committed governed CSV; missing file = hard fail | Chain-level allocation not reproducible; fails open | Generate the CSV via `extract_xlsx_to_csv.py`, commit it, change `load_chain_allocation_weights` `return None` → raise unless `--allow-missing-weights` | **P1** | one-time extract from the source XLSX |
| G-03 | Governance logic | Python authoritative + DAX reimplementation | Python authoritative; DAX consumes Python output | Silent divergence | Python emits `GovernedAllocation.csv`; new PQ query 44 reads it; DAX 09 demoted to display/QC of that column | P2 | G-01, MIR-01 |
| G-04 | TAT window | Python ±3 months vs DAX M+1 | One rule, one place | Business rule ambiguity | Confirm with business, encode once in `qc_rules.yml`, delete the loser | P2 | **business decision** |
| G-05 | Data contract | Prose in ≥3 places per dataset | One machine-readable `schemas/*.yml` per dataset | Header drift undetected | `schemas/` + `pipeline/validate/validate_sources.py`; generate the prose docs from it | P2 | none |
| G-06 | Nielsen / TDP / Primary_Weekly | No data, no status | `SAMPLE` or `MISSING` state, page shows WIP banner | Empty pages look broken or, worse, look real | Sample-data framework §5 + `PageReadiness` table | P2 | schemas first |
| G-07 | Pre-refresh QC | None | Blocking Stage-A gate in CI | Bad files reach Power BI | `pipeline/validate/` + extend `qc_dashboard.py` vocabulary | P2 | G-05 |
| G-08 | CI workflows | 2 workflows, duplicated, one runs QC twice | 1 reusable workflow, called by both triggers | Drift + wasted minutes | Merge into `.github/workflows/pipeline.yml` with jobs | P3 | none |
| G-09 | Model artifact | None in git | PBIP (PBIR + TMDL) committed | No deploy / diff / rollback / rebuild possible | §7 recommendation — **Option C hybrid** | **P1 for automation** | Power BI Desktop, one session |
| G-10 | Assembly checklist | Referenced, absent | Exists | Onboarding friction | Create `Desktop_Assembly_Checklist.md` from README §"One-time setup" — or retire the reference. Becomes largely obsolete once PBIP lands | P3 | G-09 |
| G-11 | Refresh trigger | Human clicks Refresh in Desktop | Service scheduled refresh + REST API on-demand | Whole SOP is a person | §8 — requires Pro/PPU/Fabric + gateway or cloud-hosted source | P2 | G-09, **licensing** |
| G-12 | Publish | Human publishes | `fabric-cicd` from GitHub Actions | Deployment not reproducible | §8 Phase G | P2 | G-09, **service principal** |
| G-13 | Post-refresh QC | Human reads Page 12 | Automated DAX-over-XMLA/API assertions | Manual, unrecorded | §6 Stage C | P2 | G-09, G-11, XMLA (PPU/Fabric) |
| G-14 | Run manifest | Partial (`alloc.governance` in data.js) | `reports/runs/<RunID>.json` | Cannot answer "what produced this refresh" | §8.4 | P2 | pipeline exists |
| G-15 | Raw extraction | Manual script invocation, hand-passed `--header-row` | `source_registry.yml`-driven | Monthly operational knowledge lives in a person's head | Move `--header-row`, sheet name, glob into config | P2 | G-05 |
| G-16 | Mapping validation loop | `README_Mapping_Validation.md` prose, human-filled columns | Validated columns enforced by a QC rule | Corrections may never flow back | Add mapping-completeness check to Stage A | P3 | G-05 |
| G-17 | Sample data | None | `PowerBI/SampleData/` + `IsSampleData` flag | Cannot build/test incomplete areas safely | §5 | P2 | schemas |
| G-18 | Page readiness | None | `PageReadiness` seed table + DAX banner | WIP pages indistinguishable from broken ones | §5.3 | P2 | G-17 |

---

## 3. Deliverable 3 — Recommended Target Architecture

### 3.1 The one decision that shapes everything else

**Do not automate the Desktop SOP literally.** [R, strongly held]

Power BI Desktop is an interactive application: it does not support running under a
system account (WebView2 does not support system accounts), its command-line switches
cover installation only, and UI-automation tools cannot reliably reach its elements.
Any GitHub-Actions-drives-Desktop scheme would be fragile, unsupported, and would need
a Windows runner babysitting a GUI.

The supported destination is: **the model becomes a source-controlled PBIP artifact,
and refresh/deploy happen in the Power BI Service via REST APIs**, driven from GitHub
Actions. Desktop remains the *authoring* tool — which is correct and fine — but stops
being the *operating* tool.

### 3.2 Authoritative source of truth, stage by stage

This is the table to argue about now, because everything in Stage 2 follows from it.

| Stage | Authoritative source of truth | Rationale |
|---|---|---|
| Raw monthly data | `PowerBI/RawDataFolders/**.csv` **in git** | Already true and already tracked (31 files, via the `!PowerBI/**/*.csv` negation in `.gitignore`). Big enabler — the repo *already is* the data landing zone |
| Schema / contract | `schemas/<dataset>.yml` **[new]** | Single definition; `.pq` `SelectColumns` lists and the prose docs get generated from it |
| Master & mapping data | `PowerBI/SeedData/Masters/`, `.../Mapping/` | Unchanged. Already git-tracked and hand-editable, which is right for business-owned reference data |
| DIST allocation weights | `PowerBI/SeedData/DIST/*.csv` | Governed CSV with approval columns. **Both** Python and Power Query must read these and only these (fixes G-01, G-02) |
| **Allocation governance rules** | **Python — `scripts/dist_allocation_governance.py`** | **Keep Python authoritative.** See §3.3 |
| Governed allocation output | `PowerBI/SeedData/DIST/GovernedAllocation.csv` **[new, generated]** | Python's decision, materialised as a governed input table for Power BI |
| Dashboard data | `dashboard/data.js` (generated) | Unchanged |
| Semantic model + report | `PowerBI/Project/*.pbip` **[new]** | PBIR + TMDL, git-diffable |
| Dataset/page readiness | `PowerBI/SeedData/Status/PageReadiness.csv` **[new]** | One table both the PBI report and CI read |
| QC rules | `config/qc_rules.yml` **[new]** | Thresholds out of code |
| Run history | `reports/runs/<RunID>.json` **[new]** | Audit trail |

### 3.3 The DIST governance question — answered

The brief asked whether Python should stay authoritative, move to PQ, move to DAX,
become governed input tables, or go hybrid. **Recommendation: Python stays
authoritative, and its output becomes a governed input table for Power BI.** [R]

Reasons, specific to this repo:

- Python governance is **already integrated and already tested** —
  `build_dashboard_data.py` imports it at line 27 and threads it through six numbered
  steps (2581–2905), with `test_dist_allocation_governance.py` and
  `test_phase5_offtake_wiring.py` covering it. That is a working authoritative engine.
- The 5-tier gate needs **cross-dataset set membership** (is this brand/article in the
  offtake universe?) plus a **±3-month temporal fallback** plus **approval-file
  precedence**. Expressing that in DAX means row-context gymnastics across three fact
  tables; expressing it in M means re-reading the whole offtake fact inside a
  transformation. Python already does it once, cheaply, with a real test suite.
- The **governance decision is an auditable business artifact**, not a display concern.
  It should be a *file with an approval trail* that both consumers read — which is
  precisely the shape `DistPrimaryContWeightsArticle.csv` already has.
- Duplicating it in DAX has already produced divergence (G-03, G-04). Doubling down
  would be the wrong lesson.

Concretely:

```
dist_allocation_governance.py  (authoritative rules)
        │  invoked by build_dashboard_data.py
        ▼
GovernedAllocation.csv         ← NEW generated artifact, committed
   columns: Month, ShipTo_Key, Brand_Key, Article_Key, Chain,
            Frac, Eligibility_Tier, Confidence_Pct, Reasoning,
            Override_Applied, Approval_Status, RunID
        │                                    │
        ▼                                    ▼
 dashboard/data.js                   PQ 44_GovernedAllocation.pq  [NEW]
                                            │
                                            ▼
                                     DAX 09 → demoted to *display + QC only*:
                                       reads [Eligibility_Tier] as a column,
                                       keeps QC Reconciliation Variance = 0 as
                                       an independent cross-check in the model
```

DAX 09 keeps one genuinely valuable job: **it independently re-derives the
reconciliation** (`Original = Allocated + Blocked`) inside the semantic model. Keeping
that as a *check on* Python's output — rather than a *reimplementation of* Python's
rules — is the hybrid worth having. The tier *derivation* measures
(`Eligibility Status`, `Article Eligible`, `Article Allocation Ratio %`) get replaced
by reads of the governed column.

### 3.4 End-to-end target flow

```
 [1] ANALYST drops approved monthly source into RawDataFolders/<type>/  (CSV, git)
                     │  git push / PR
                     ▼
 [2] FILE DETECTION      GitHub Actions, paths: filter on RawDataFolders/**
                     ▼
 [3] SCHEMA VALIDATION   pipeline/validate/validate_sources.py  ← schemas/*.yml
                         naming, extension, required cols, dtypes, period, dupes
                     ▼
 [4] MASTER/MAPPING VAL. unmapped chain/brand/article/zone vs SeedData/Masters
                     ▼
 [5] DIST GOVERNANCE     dist_allocation_governance.py → GovernedAllocation.csv
                         + Not_Eligible rows → DistAllocationGovernance_FlaggedRows.csv
                     ▼
 [6] TRANSFORMATION      build_dashboard_data.py --offtake-patch / --detail-only / …
                     ▼
 [7] PRE-REFRESH QC      qc_dashboard.py (extended) — FAIL ⇒ STOP, no refresh
                     ▼          BLOCKED ⇒ proceed to WIP/sample lane only
 [8] COMMIT ARTIFACTS    data.js, GovernedAllocation.csv, reports/runs/<RunID>.json
                     ▼
 [9] DASHBOARD DEPLOY    Vercel / GitHub Pages          ← works today, no license
 ───────────────────────────────────────────────────────────────────────────────
        everything below this line requires Power BI Service licensing (§7.4)
 ───────────────────────────────────────────────────────────────────────────────
 [10] PBI REFRESH        POST /datasets/{id}/refreshes  (enhanced refresh API)
                     ▼
 [11] SEMANTIC MODEL QC  poll refresh status; then DAX queries via
                         /datasets/{id}/executeQueries  → Page-12 measures = 0
                     ▼
 [12] POST-REFRESH RECON control totals vs the Python-computed totals in data.js
                     ▼
 [13] DEPLOY / PUBLISH   fabric-cicd → target workspace (gated: manual approval)
                     ▼
 [14] NOTIFY + RECORD    run manifest finalised, GitHub summary, failure issue
```

Steps 1–9 are implementable **today, with the repo and free GitHub Actions**. Steps
10–14 need licensing and cloud identity you may or may not have (see §9 MIR-05/06/07).
That boundary is the honest answer to "how close can we get" — and it is much further
than the current state, because 1–9 already eliminate every manual step except the
Desktop refresh itself.

---

## 4. Deliverable 4 — Metadata & Data-Contract Design

### 4.1 Where config should live

**Recommendation:** a top-level `config/` for pipeline behaviour + a top-level
`schemas/` for per-dataset contracts. [R]

Rationale: schemas describe data that serves *both* deliverables (dashboard and Power
BI), so burying them under `PowerBI/` would misrepresent ownership. `config/` and
`schemas/` sit alongside `scripts/`, `dashboard/`, `PowerBI/` — matching the existing
top-level-by-concern layout.

```
config/
  source_registry.yml    ← folder ⇄ dataset ⇄ extraction script ⇄ status
  qc_rules.yml           ← thresholds + severity, replaces magic numbers
  refresh_config.yml     ← PBI workspace/dataset ids, refresh policy   [Phase F]
  report_pages.yml       ← page ⇄ dataset ⇄ readiness                 [Phase D]
schemas/
  primary_article_monthly.yml
  offtake_monthly.yml
  primary_shipto_monthly.yml
  primary_weekly.yml
  nielsen_monthly.yml
  tdp_monthly.yml
  dist_cont_weights.yml
  masters_*.yml
```

**Format: YAML.** [R] Python-native via `PyYAML`, comment-friendly (these files carry
business meaning that needs annotating), and diff-readable in PRs. Not JSON — no
comments. Not TOML — poor for deep nesting. `PyYAML` is one line added to the CI pip
install.

### 4.2 The dataset contract — worked example

This is a real contract for a real dataset, derived from
`16_Fact_PrimaryArticle.pq` + `split_primary_article_xlsb.py` + the LOCKED header
mapping in `DistributorPrimaryAllocation_Logic.md`. Every field the brief listed is
either present or deliberately omitted with a note.

```yaml
# schemas/primary_article_monthly.yml
dataset_id: primary_article_monthly
name: Primary Sales — Article Level (File 2)
description: >
  Article-wise primary invoicing at Month x Customer(Ship-to) x Brand x Article.
  PO Type 'Dist.' rows carry a blank chain and are exploded across chains by the
  governed DIST weights. Source of FY27 primary in detail_meta.fyx_primary.
owner: MT Channel Analyst
source_system: SAP invoice extract (article-wise .xlsb)
status: PRODUCTION            # PRODUCTION | WIP | SAMPLE | MISSING | QC_FAILED | NOT_APPLICABLE
approval_state: Approved
schema_version: 1.0.0

location:
  folder: PowerBI/RawDataFolders/Primary_Article_Monthly
  filename_pattern: "primary_article_{MMM}_{YY}.csv"   # e.g. primary_article_Jul_26.csv
  extensions: [.csv]
  ignore_prefix: "_"                                    # matches fnCombineFolder
  extraction:
    script: scripts/split_primary_article_xlsb.py
    header_row: 1          # annotation row sits ABOVE the real header — G-15 fix
    source_hint: primary_article.xlsb

reporting_period:
  column: Month
  format: "MMM'YY"
  grain: monthly
  fy_rule: indian_fy         # Apr-Dec Y -> FY(Y+1); Jan-Mar Y -> FY(Y). Never hardcode a FY list.
  allow_reprocess: true      # replacing one month's file is the documented correction path
  duplicate_period_action: replace_file   # two files covering one month => FAIL

columns:
  - {name: "FY",                      type: text,   required: true}
  - {name: "Month",                   type: text,   required: true, key: true}
  - {name: "Cust-SAP Code",           type: text,   required: true, key: true}
  - {name: "Ship To Name",            type: text,   required: true, key: true}
  - {name: "EAN No.",                 type: text,   required: false, note: "article key priority 1"}
  - {name: "brand",                   type: text,   required: true, key: true, master: BrandMaster}
  - {name: "category",                type: text,   required: true, master: CategoryMaster}
  - {name: "sub_category",            type: text,   required: false}
  - {name: "Description",             type: text,   required: true, note: "article key priority 3"}
  - {name: "MRP",                     type: number, required: false, note: "per-unit; NOT scaled by allocation"}
  - {name: "Inv Qty",                 type: number, required: true,  allocatable: true}
  - {name: "Inv. Net value(LOC)",     type: number, required: true,  allocatable: true, measure: NSV}
  - {name: "Inv. Tax Amount(LOC)",    type: number, required: false, allocatable: true}
  - {name: "Total MRP sales",         type: number, required: false, allocatable: true}
  - {name: "Avg Tot",                 type: number, required: false, note: "ratio; invariant under split"}
  - {name: "MTD-Sale type",           type: text,   required: true, allowed: [Sales, MRN, Cancel Invoice, FOC]}
  - {name: "PO Type",                 type: text,   required: true, allowed: [Direct, "Dist."], note: "the Direct/Dist flag lives HERE, not in MTD-Sale type"}
  - {name: "Chain name for Dashboard", type: text,  required: false, normalize: collapse_linebreak,
     note: "blank is EXPECTED and meaningful for PO Type='Dist.'"}
  - {name: "Zone",                    type: text,   required: true, master: ZoneStateMaster}
  - {name: "State",                   type: text,   required: true, master: ZoneStateMaster}

business_keys: [Month, "Cust-SAP Code", brand, "EAN No."]
unexpected_columns: warn        # warn | fail | ignore  — source adds columns occasionally
missing_optional_columns: warn

dependencies:
  masters: [BrandMaster, CategoryMaster, ZoneStateMaster, ArticleMaster, ChainMaster]
  mapping: [DistPrimaryContWeightsArticle, PrimaryAllocationOverride]
  governance: dist_allocation_governance

transformation:
  powerquery: PowerBI/PowerQuery/16_Fact_PrimaryArticle.pq
  python: scripts/build_dashboard_data.py --detail-only
  output_table: "Fact Primary Article"

qc_rules: [schema_match, no_dup_business_keys, nulls_within_threshold,
           masters_resolve, period_continuity, dist_reconciliation_zero]

consumers:
  powerbi_pages: ["Page 2B", "Page 3", "Page 7", "Page 12"]
  dashboard_tabs: ["Primary", "Category & Pack", "Performance & Comparison"]
```

**Deliberately omitted, with reasons:** per-column null thresholds (belong in
`qc_rules.yml` so one threshold change doesn't touch six schema files); DAX measure
lists (they live in `DAX/` and would rot); row-count expectations (data-dependent —
belongs in the run manifest as observed, not in the contract as asserted).

### 4.3 `qc_rules.yml` — thresholds out of code

```yaml
# config/qc_rules.yml
version: 1.0.0
rules:
  schema_match:
    severity: FAIL
    description: Delivered header set matches schemas/<dataset>.yml required columns
  no_dup_business_keys:
    severity: FAIL
    max_duplicate_rows: 0
  nulls_within_threshold:
    severity: WARN
    max_null_pct: {default: 1.0, "EAN No.": 5.0}
  masters_resolve:
    severity: FAIL
    description: Every fact chain/brand/category/zone exists in its master
    exempt_values: ["Unmapped Chain"]      # a deliberate, documented sentinel
  period_continuity:
    severity: WARN
    description: No month gap between earliest and latest delivered period
  dist_reconciliation_zero:
    severity: FAIL
    tolerance_lakh: 0.0                     # matches reconcile_qc() default — do not loosen
  data_health_pct:
    severity: FAIL
    min: 99.0                               # matches RefreshGuide.md §4.1
  sample_data_in_production:
    severity: FAIL
    description: No row with IsSampleData=TRUE may reach a PRODUCTION-status dataset
```

### 4.4 Reuse, not reinvention

The repo already contains a working "declare it, validate it, sync it, check for
drift" pattern: `skill-suite/manifest.json` + `validate_skills.py` +
`sync_skills.py --check`, enforced by `.githooks/pre-commit`. **Model
`pipeline/validate/validate_sources.py` on `validate_skills.py`**, and extend the
existing pre-commit hook with a second guarded block rather than adding a second hook.
The hook's `grep -qE '^(skill-suite/|...)' || exit 0` early-exit makes this a clean,
additive change.

---

## 5. Deliverable 5 — WIP / Sample-Data Strategy

### 5.1 States, and where they are recorded

Adopt the six states from the brief, but **map them onto the QC vocabulary the repo
already uses** rather than inventing a parallel one:

| DataStatus | Meaning | QC behaviour | Visible to users as |
|---|---|---|---|
| `PRODUCTION` | Approved real data | Must PASS all rules | Normal |
| `WIP` | Real data, incomplete coverage or unapproved mapping | FAIL blocks; BLOCKED allowed | Banner: "Partial — coverage to \<month\>" |
| `SAMPLE` | Synthetic, schema-conformant | Never gates production refresh | Banner: "SAMPLE DATA — not business results" |
| `MISSING` | No file at all | Reported, does not fail the build | Banner: "Work in Progress — source pending" |
| `QC_FAILED` | Real data that failed a rule | **Blocks production refresh** | Banner: "Data quality hold" + last good period |
| `NOT_APPLICABLE` | Deliberately out of scope | Silent | Page hidden |

### 5.2 Metadata columns — a smaller set than the brief proposed

The brief listed fourteen candidate columns. Carrying fourteen on every row is
expensive in an import model and most are per-*file*, not per-*row*. **Split them:**

**Per-row, on every fact table (4 columns):**
`DataStatus` · `IsSampleData` (bool) · `SourceFile` · `SchemaVersion`

`SourceFile` and a refresh timestamp are **already added automatically by
`fnCombineFolder`** as `[Data Source File]` and `[Refresh Date]` — so the true
increment is `DataStatus` + `IsSampleData` + `SchemaVersion`. Three columns, low
cardinality, dictionary-compresses to near-nothing.

**Per-file, in the run manifest (not in the model):**
`SourceFileHash` · `RowCount` · `ValidationStatus` · `QCStatus` · `LastRefreshUTC` ·
`ReportingPeriod` · `RunID` · `GitCommit`. These belong in
`reports/runs/<RunID>.json`, queryable when someone asks "what produced this number",
without bloating the semantic model.

### 5.3 `PageReadiness` — the WIP control table

Location: `PowerBI/SeedData/Status/PageReadiness.csv` [R] — next to the other
hand-maintained governed tables, loaded by a new `PowerQuery/45_PageReadiness.pq`.

```csv
Page,PageName,Dataset,DataStatus,ProductionReady,Blocker,Owner,ExpectedSource,LastUpdated,Notes
1,Executive Summary,primary_article_monthly,PRODUCTION,TRUE,,MT Analyst,,2026-08-16,
2B,Ship-to Primary Allocation,primary_shipto_monthly,WIP,FALSE,Coverage ends May'26,MT Analyst,Primary_ShipTo_Monthly,2026-08-16,History file only
9,Nielsen Market Share,nielsen_monthly,MISSING,FALSE,No Nielsen file supplied,TBD,Nielsen_Monthly,2026-08-16,Template only — see G-06
10,TDP Distribution,tdp_monthly,MISSING,FALSE,No TDP file supplied,TBD,TDP_Monthly,2026-08-16,Template only — see G-06
12,Data Quality Check,ALL,PRODUCTION,TRUE,,MT Analyst,,2026-08-16,
```

Two consumers, one table:

- **In Power BI:** a card on every page bound to
  `Page WIP Banner = ` a DAX measure over `PageReadiness` filtered by a page-name
  disconnected parameter, returning `""` when `ProductionReady = TRUE` and the
  blocker text otherwise. Conditional-format the card so a non-empty banner is
  unmissable. This is additive — no existing visual changes.
- **In CI:** `validate_sources.py` cross-checks that every dataset referenced in
  `PageReadiness.csv` has a matching `schemas/*.yml` and that its declared status
  matches what the folder actually contains. A page claiming `PRODUCTION` over an
  empty folder is a **FAIL** — that is the "sample must never masquerade as
  production" control, enforced mechanically.

### 5.4 Sample-data generation and automatic retirement

**Location:** `PowerBI/SampleData/<dataset_id>/` [R] — deliberately *not* inside
`RawDataFolders/`, so that `fnCombineFolder` can never accidentally combine sample
rows into a production fact.

**Generator:** `pipeline/sample/generate_sample.py --dataset nielsen_monthly --months 6`,
driven entirely by `schemas/*.yml` — so a sample generator never needs updating when a
schema changes. Rules:

- Every generated row carries `IsSampleData = TRUE`, `DataStatus = SAMPLE`.
- Text keys are drawn from the **real masters** (so joins exercise real cardinality)
  but every measure is synthetic and every generated file is named
  `_SAMPLE_<dataset>_<period>.csv` — note the leading underscore, which means
  `fnCombineFolder` **already ignores it** even if someone misplaces it. Defence in
  depth using an existing mechanism.
- Loading sample data is opt-in via a Power BI parameter `pIncludeSampleData`
  (default `false`) and a Python flag `--include-sample`.

**Automatic retirement:** when a real file lands in the dataset's `folder`,
`validate_sources.py` sees `status: PRODUCTION` satisfied by real rows and **fails the
build if sample rows are still being loaded for that dataset** (`sample_data_in_production`
rule). Retirement is therefore not a remembered chore — it is a gate.

---

## 6. Deliverable 6 — QC Framework

### 6.1 Where each control should live — with no duplication

The principle: **each check runs exactly once, in the cheapest layer that can see what
it needs**, and the layers are ordered so a failure stops work as early as possible.

| Check | Python/CI | Power Query | DAX | PBI/Fabric API | Rationale for placement |
|---|---|---|---|---|---|
| File present, named correctly | **✔ Stage A** | — | — | — | Filesystem concern; Power Query cannot report it usefully |
| Extension / not corrupt | **✔ A** | — | — | — | Fail before Desktop is involved |
| Header set matches contract | **✔ A** | — | — | — | Today PQ fails opaquely via `MissingField.UseNull` |
| Data types | **✔ A** | — | — | — | |
| Required fields non-null | **✔ A** | — | — | — | |
| Duplicate business keys | **✔ A** | — | — | — | pandas `duplicated()` beats DAX `SUMMARIZE` |
| Duplicate *master* rows (store/article) | — | — | **✔ keep** | — | `06_DataQuality.dax` `Duplicate Store/Article Count` already does this; masters are small; leave it |
| Reporting-period detect / gap / duplicate month | **✔ A** | — | — | — | |
| Master reconciliation (unmapped chain/brand/cat/zone) | **✔ A** | — | **✔ keep** | — | **Intentional double**: CI blocks the merge; DAX Page 12 stays as the analyst's in-report view. Same rule, two audiences — the DAX version is display, not gate |
| Mapping completeness (validated columns filled) | **✔ A** | — | — | — | G-16 |
| DIST eligibility tiers | **✔ A (authoritative)** | — | display only | — | §3.3 |
| DIST reconciliation = 0 | **✔ A (authoritative)** | — | **✔ independent cross-check** | — | Worth having twice — one checks the *other engine's* arithmetic |
| Allocation weights sum to 1 | — | **✔ keep** | — | — | `41_DistContWeights.pq` normalises by construction and exposes `[Raw Pct Sum]`; keep, add a CI assertion on the seed |
| Row counts vs expectation | **✔ A + manifest** | — | — | — | |
| Query/refresh completion | — | — | — | **✔ Stage B** | Only the API knows |
| Refresh duration / errors | — | — | — | **✔ B** | `GET /datasets/{id}/refreshes` |
| Expected tables present, non-empty | — | — | ✔ via measure | **✔ B** (executeQueries) | |
| Page-12 issue counts all zero | — | — | **✔ authored** | **✔ C reads them** | Reuse `06_DataQuality.dax` verbatim — the API just *reads* the existing measures. Zero new logic |
| Latest reporting month correct | ✔ computes expected | — | ✔ measure | **✔ C compares** | |
| Executive-summary control totals | ✔ from `data.js` | — | ✔ measure | **✔ C compares** | **The single most valuable new check**: Python total vs semantic-model total, two independent engines over the same source |
| Data Health % ≥ 99 | — | — | **✔ keep** | **✔ C asserts** | |
| Sample data in production | **✔ A** | ✔ `pIncludeSampleData` | ✔ banner | — | Defence in depth, three cheap layers |

### 6.2 The three stages

**Stage A — Pre-refresh (Python, GitHub Actions, no license needed).**
`pipeline/validate/validate_sources.py` + the extended `qc_dashboard.py`. Exit codes
keep the existing contract: `0` = PASS/WARN, `1` = any FAIL. **Any FAIL stops
everything downstream including the Power BI refresh.** BLOCKED items annotate and,
per the existing convention, need business approval rather than a code fix — they
route work into the WIP lane instead of killing the run.

**Stage B — Refresh (Power BI REST API).**
Enhanced refresh via `POST /groups/{gid}/datasets/{did}/refreshes` with
`notifyOption`, then poll `GET .../refreshes/{rid}` until terminal. Capture
`status`, `startTime`, `endTime`, `serviceExceptionJson` into the run manifest.
**Confirmed [F]:** the enhanced refresh API requires a semantic model in Power BI
Premium, Premium-Per-User, or Power BI Embedded, needs the `Dataset.ReadWrite.All`
scope, and — for service-principal auth — the tenant setting *"Allow service
principals to use Power BI APIs"* enabled plus the SPN added as workspace Admin or
Member.

**Stage C — Post-refresh (DAX over the API).**
`POST /datasets/{id}/executeQueries` with a DAX query evaluating the *existing*
Page-12 measures plus control totals, asserted against the Python-side numbers already
present in `data.js`. This is the automated replacement for "open Page 12, everything
should be 0" and "confirm Latest Month is right" — and it reuses
`06_DataQuality_Measures.dax` without rewriting a line of it.

---

## 7. Deliverable 7 — PBIX vs PBIP Recommendation

### 7.1 What is confirmed about the platform direction [F]

- **PBIP** saves report + semantic model into a folder using source-control-friendly
  formats: **PBIR** for the report, **TMDL** for the model.
- **TMDL has reached General Availability.** Its integration with PBIP and Fabric Git
  integration was still flagged preview at the time of the cited posts, but GA of the
  language itself signals stability.
- **PBIR is becoming the default report format**: from January 2026 all new reports
  created in the Power BI *service* use PBIR by default, with rollout completing by end
  of February 2026. **PBIP GA is planned for 2026.**
- PBIR stores each visual, page and bookmark as a **separate JSON file**, which is what
  makes merge conflicts tractable.
- Microsoft ships **`fabric-cicd`**, an officially supported, Microsoft-backed
  open-source Python library for code-first deployment of Fabric items, integrating
  with Fabric Git integration, the Fabric REST APIs and the Fabric CLI. There is a
  documented path for deploying PBIP from GitHub Actions on merge to a branch.
- **Power BI Desktop cannot be run unattended**: it does not support system accounts
  (WebView2 limitation), and its command-line switches govern installation only.

Direction of travel is unambiguous: **Microsoft is investing in PBIP/PBIR/TMDL and
API-driven deployment; `.pbix` is the legacy binary.**

### 7.2 The three options against this repo

| Criterion | A: stay `.pbix` | B: full `.pbip` | C: hybrid (**recommended**) |
|---|---|---|---|
| Git friendliness | None — binary, and today not even committed | Full — per-visual JSON + per-table TMDL | Full |
| Automated deployment | Not possible | `fabric-cicd` | `fabric-cicd` |
| CI capability | Zero | Lint TMDL/PBIR, diff measures, assert model rules | Same |
| Model versioning | None | Per-table TMDL files | Same |
| Merge conflicts | Unresolvable | Tractable | Tractable |
| Developer experience | Familiar GUI | Same GUI — PBIP is a *save format*, not a different tool | Same |
| Licensing to adopt the **format** | — | **Free** — Desktop feature | **Free** |
| Licensing to **deploy** it | n/a | Fabric/Premium (§7.4) | Deferred until you have it |
| Migration effort | — | Save-As once, plus theme/param check | **Save-As once** |
| Rollback | Restore a file from someone's disk | `git revert` + redeploy | `git revert`; redeploy once licensed |
| Risk to current SOP | — | Medium if forced immediately | **Near zero** |

### 7.3 Recommendation — Option C, sequenced [R]

**Adopt PBIP as the committed artifact now; defer API deployment until licensing is
resolved.** Concretely:

1. In Power BI Desktop, enable developer mode and **Save As → Power BI project (.pbip)**
   into `PowerBI/Project/MT_Leadership_Dashboard/`, with **PBIR + TMDL** selected.
   Commit it. *This alone closes G-09 and costs one Desktop session and zero licence
   spend.*
2. Keep the `.pbix` workflow working in parallel for one month as the fallback. Do not
   delete anything.
3. **Keep `PowerQuery/*.pq` and `DAX/*.dax` as the readable, reviewable, paste-in
   source** — they are documentation and onboarding assets that PBIP's generated JSON
   is not. Add a CI check that measure names in `DAX/*.dax` exist in the TMDL, so the
   two cannot silently diverge. This preserves the build-kit character of the repo,
   which is the point of the project.
4. Only when a Fabric capacity / PPU workspace exists, wire `fabric-cicd`.

**Migration risks, named:** [F/A] the theme (`HonasaMT_Theme.json`) and the
`pRootFolder` parameter must be re-verified after the first PBIP save; PBIP/Git
integration for TMDL was preview-flagged in the cited posts, so pin your Desktop
version and re-test after upgrades; **from 12 February 2026 Fabric deployment pipelines
retire support for semantic models not upgraded to Enhanced Metadata** — confirm the
model is Enhanced Metadata before relying on pipelines; and Fabric Git integration
caps a single commit at **50 MB** total, which the PBIP folder will sit well under but
`dashboard/data.js` (~9 MB) plus raw CSVs makes worth watching if the same repo is ever
connected directly to a Fabric workspace.

### 7.4 Licensing — free vs paid, stated bluntly [F]

| Capability | Requirement |
|---|---|
| Save/commit PBIP, PBIR, TMDL | **Free** — Power BI Desktop |
| Everything in §3.4 steps 1–9 (validation, governance, transform, QC, dashboard deploy) | **Free** — GitHub Actions + Vercel, already in place |
| Publish a report to Service; share it | **Power BI Pro** per user (minimum) |
| **Enhanced refresh REST API** | Semantic model in **Premium, PPU, or Embedded** — Pro alone is not enough |
| **XMLA read/write** (external tools, model write-back) | **Premium / PPU / Embedded**; read-only by default, must be switched to Read Write at capacity level |
| **Fabric Git integration** | **Fabric capacity** (existing Power BI Premium capacity may qualify; some Power BI SKUs support Power BI items only). Tenant switches must be enabled, incl. a GitHub-specific one; GitHub cloud only, no GitHub Enterprise Server; 50 MB per commit |
| **Fabric deployment pipelines / `fabric-cicd`** | Fabric capacity + **service principal with Contributor/Admin on the workspace** + tenant setting allowing SPNs to use Fabric APIs |
| Refresh from **local folders** (today's `pRootFolder` design) | **On-premises data gateway** — and note a OneDrive/SharePoint-*synced local path* still counts as on-premises. Reconnecting via the **SharePoint Folder connector** makes it a true cloud source and removes the gateway requirement |
| Service principal for dataflows | **Not supported** |

**The consequential one:** today every `.pq` sources `pRootFolder & "\..."`, a Windows
local path. In the Service that is an on-premises source needing a gateway — *even if
the folder is inside OneDrive*. Two supported ways out, both worth costing (MIR-07):
(a) install a gateway on an always-on machine, or (b) re-point `00_Parameters.pq` at a
**SharePoint Folder** / OneDrive-for-Business URL and let the Service read it natively.
**(b) is the cleaner target** — the same CSVs that live in git get published to a
SharePoint folder by CI, and no gateway infrastructure is needed.

---

## 8. Deliverable 8 — CI/CD Design

### 8.1 Trigger recommendation

**Pull-request merge to `main`, path-filtered on `RawDataFolders/**`, `SeedData/**`,
`schemas/**`, `scripts/**` — plus a nightly cron as a safety net, plus
`workflow_dispatch` for manual reruns.** [R]

Not a raw push: monthly data landing deserves a reviewable diff, and the PR *is* the
approval gate the brief asks for at step 9. Not file-arrival events on cloud storage:
that adds infrastructure for no gain, since the files must reach git anyway. Not a
scheduled-only pipeline: it would refresh on stale data.

### 8.2 Stage table

`local?` = runs on a laptop · `GHA?` = runs in GitHub Actions free tier · `PBI?` = needs Power BI Service/Fabric.

| Stage | Trigger | Script/tool | Inputs | Outputs | QC | On failure | Secrets | local? | GHA? | PBI? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 Detect | PR opened/sync | GHA `paths:` filter | changed files | dataset list | — | skip run | — | ✔ | ✔ | ✘ |
| 2 Schema validate | after 1 | `pipeline/validate/validate_sources.py` | raw CSVs, `schemas/*.yml` | `reports/validation.json` | A1–A6 | **FAIL ⇒ block PR** | — | ✔ | ✔ | ✘ |
| 3 Master/mapping | after 2 | same script, `--masters` | facts + `SeedData/` | unmapped-values report | A7–A8 | FAIL ⇒ block; emit `Unmapped_*.csv` artifact | — | ✔ | ✔ | ✘ |
| 4 DIST governance | after 3 | `dist_allocation_governance.py` via build | weights seed, offtake universe, overrides | `GovernedAllocation.csv`, `..._FlaggedRows.csv` | tiers + recon=0 | FAIL ⇒ block | — | ✔ | ✔ | ✘ |
| 5 Transform | after 4 | `build_dashboard_data.py --<mode>` | raw + seeds | `dashboard/data.js` | build asserts | FAIL ⇒ block | — | ✔ | ✔ | ✘ |
| 6 Pre-refresh QC | after 5 | `qc_dashboard.py` (extended) + Playwright | `data.js`, `qc_rules.yml` | `qc_report.txt` | Stage A full | FAIL ⇒ block; BLOCKED ⇒ warn + WIP lane | — | ✔ | ✔ | ✘ |
| 7 Dashboard deploy | merge to `main` | Vercel GitHub integration | `dashboard/` | live URL | smoke fetch | alert | Vercel (already set) | ✘ | ✔ | ✘ |
| 8 Publish sources to cloud | merge | `pipeline/publish/sync_sharepoint.py` **[new]** | raw CSVs + seeds | SharePoint folder | hash compare | retry ×3, then FAIL | `SP_CLIENT_ID/SECRET/TENANT` | ✔ | ✔ | ✘ |
| 9 PBI refresh | after 8 | `pipeline/publish/refresh_dataset.py` | workspace+dataset ids | refresh id | Stage B | FAIL ⇒ open issue, **no publish** | `PBI_TENANT_ID`, `PBI_CLIENT_ID`, `PBI_CLIENT_SECRET`, `PBI_WORKSPACE_ID`, `PBI_DATASET_ID` | ✔ | ✔ | **✔** |
| 10 Semantic QC | after 9 | `pipeline/validate/postrefresh_qc.py` (executeQueries) | DAX assertions | `reports/runs/<RunID>.json` | Stage C | FAIL ⇒ issue + **no publish** | same | ✔ | ✔ | **✔** |
| 11 Deploy report | after 10, **manual approval** | `fabric-cicd` | `PowerBI/Project/*.pbip` | deployed items | post-deploy smoke | rollback = redeploy prior tag | same + workspace ids | ✔ | ✔ | **✔** |
| 12 Notify + record | always | GHA job summary + `send-notification` | manifest | GH summary, issue on failure | — | — | `GITHUB_TOKEN` | ✘ | ✔ | ✘ |

**Stages 1–7 are buildable now with zero new licensing.** Stages 8–11 are the licensed
frontier. Note that even if you never buy a Fabric capacity, stages 1–6 remove every
manual step *except* the Desktop refresh click — and give it a guarantee that its input
is valid, which today it does not have.

### 8.3 Workflow consolidation (fixes G-08)

Replace `qc.yml` + `dataeng.yml` with one `pipeline.yml` exposing jobs
`validate → govern → transform → qc → (gated) refresh → (gated) deploy`, using
`needs:` chaining, GitHub **environments** for the approval gate on refresh/deploy,
and `if: github.ref == 'refs/heads/main'` on the deploy legs. Keep the existing
artifact upload of `qc_report.txt` (30-day retention) exactly as-is — it works. Run
`qc_dashboard.py` **once**, `tee` to file, and evaluate the file.

### 8.4 Run manifest — `reports/runs/<RunID>.json`

```json
{
  "RunID": "2026-08-16T04-12-33Z-a1b2c3d",
  "RunTimestamp": "2026-08-16T04:12:33Z",
  "GitCommit": "a1b2c3d...",
  "TriggeredBy": "pull_request#42 merge",
  "ReportingPeriod": "Jul'26",
  "Datasets": [
    {"dataset_id": "offtake_monthly", "status": "PRODUCTION", "SchemaVersion": "1.0.0",
     "InputFiles": ["offtake_store_article_Jul_26.csv"],
     "InputHashes": {"offtake_store_article_Jul_26.csv": "sha256:…"},
     "InputRowCounts": {"offtake_store_article_Jul_26.csv": 184203},
     "ValidationStatus": "PASS"},
    {"dataset_id": "nielsen_monthly", "status": "MISSING", "ValidationStatus": "BLOCKED"}
  ],
  "MappingVersion": "DistCont_Patch_Approved_2026-07-04.csv",
  "GovernanceVersion": "dist_allocation_governance.py@a1b2c3d",
  "Governance": {"Eligible": 0, "Eligible_TAT": 0, "Not_Eligible": 0, "ReconciliationVariance": 0.0},
  "QCResult": {"PASS": 0, "WARN": 0, "FAIL": 0, "BLOCKED": 0},
  "OutputRowCounts": {"dashboard/data.js": {"offtake_records": 0}},
  "PowerBIRefreshID": null,
  "RefreshResult": "NOT_ATTEMPTED — no Fabric capacity configured",
  "DeploymentStatus": "SKIPPED"
}
```

This answers the brief's audit question directly — *which source files, mapping
version, code version and QC results produced this refresh* — in one file per run,
committed under `reports/runs/`.

### 8.5 Failure handling — the decision table

Default principle, as you specified: **fail closed for production accuracy; allow
controlled WIP/sample development.**

| Scenario | Behaviour | Status | Blocks PBI refresh? |
|---|---|---|---|
| Missing file for a `PRODUCTION` dataset | Halt, name the exact expected filename+folder | FAIL | **Yes** |
| Missing file for a `WIP`/`MISSING` dataset | Record, banner the page, continue | BLOCKED | No |
| Malformed / unreadable file | Halt, name file + parse error | FAIL | **Yes** |
| Changed schema — column **added** | Continue, list new columns for contract update | WARN | No |
| Changed schema — required column **missing/renamed** | Halt | FAIL | **Yes** |
| New unmapped brand / article | Halt, emit `Unmapped_Brands.csv` naming exactly which master row to add | FAIL | **Yes** |
| Invalid chain | Halt with the same remediation artifact | FAIL | **Yes** |
| Missing DIST weight for a Dist. row | Governance tiers it; `Not_Eligible` rows go to the flagged CSV; NSV stays in the **blocked** bucket, never forced | WARN + BLOCKED | No — blocked value is reported, not lost |
| DIST reconciliation variance ≠ 0 | Halt — zero tolerance, matching `reconcile_qc(tolerance_lakh=0.0)` | FAIL | **Yes** |
| Duplicate reporting period (two files, one month) | Halt, name both files | FAIL | **Yes** |
| Late-arriving correction (replace one month's file) | Allowed by design — `allow_reprocess: true`; `--offtake-patch` idempotency handles it; manifest records the supersede | PASS + note | No |
| Python transformation failure | Halt, full traceback in the job log | FAIL | **Yes** |
| PBI refresh failure | Do **not** publish; open a GitHub issue with `serviceExceptionJson`; keep last good version live | FAIL | n/a |
| PBI Service unavailable / throttled | Retry ×4 with exponential backoff (2/4/8/16 s), then FAIL and open an issue | FAIL | n/a |
| Deployment failure | Previous deployed version stays live; rollback = redeploy the previous git tag via `fabric-cicd` | FAIL | n/a |
| Sample data reaching production | `sample_data_in_production` rule halts the build; `_`-prefixed filenames mean `fnCombineFolder` would have ignored them anyway | FAIL | **Yes** |
| FY beyond pre-agg coverage (FY27+) | Not a failure — existing per-block FY gating handles it. Contract must never hardcode a FY list | PASS | No |

---

## 9. Deliverable 9 — Missing Information Register

Classification per the brief. **Nothing here blocks Stage 2 from starting** — the
`CAN_USE_SAMPLE` and `CAN_INFER` items all have a defined temporary path.

| ID | Missing information | Why needed | Impact | Temporary solution | Sample possible? | Final info required | Owner | Automation can proceed? | Class |
|---|---|---|---|---|---|---|---|---|---|
| MIR-01 | **Is the DIST TAT window ±3 months (Python) or M+1 (DAX)?** | The two engines disagree today (G-04) | Different allocation results between dashboard and Power BI | Keep Python ±3m authoritative, flag DAX as non-authoritative in a comment | n/a | One confirmed rule | MT Analyst + Finance | **Yes** — Python is authoritative meanwhile | **NEEDS_BUSINESS_CONFIRMATION** |
| MIR-02 | `ChainAllocationWeights.csv` — the chain-level weights seed | `build_dashboard_data.py:292` wants it; falls back to a gitignored XLSX (G-02) | Chain allocation not reproducible from repo | Run `extract_xlsx_to_csv.py` once against your local XLSX and commit the CSV | No — must be real | The real Sheet2 extract, committed | MT Analyst | **Yes**, after a one-time local extract | **BLOCKER for reproducibility**, trivially fixable |
| MIR-03 | Nielsen monthly data | Page 9, Market Share tab | Page empty | `SAMPLE` dataset + WIP banner | **Yes** | Nielsen subscription extract | TBD | **Yes** | CAN_USE_SAMPLE |
| MIR-04 | TDP / ACV monthly data | Page 10, Distribution tab | Page empty | `SAMPLE` + WIP banner | **Yes** | TDP extract | TBD | **Yes** | CAN_USE_SAMPLE |
| MIR-05 | Primary **weekly** files | `10_Fact_PrimarySales.pq`; weekly grain | Weekly visuals empty; monthly unaffected (comes from article file) | Mark `MISSING`; monthly path unaffected | **Yes** | Weekly extract, or a decision to retire the weekly grain | MT Analyst | **Yes** | CAN_USE_SAMPLE |
| MIR-06 | **Do you have Power BI Pro / PPU / Fabric capacity, and which?** | Gates §3.4 steps 10–14 entirely | Determines whether refresh automation is possible at all | Build stages 1–7; leave 8–11 behind a config flag that no-ops | n/a | Tenant + SKU + workspace | You / Honasa IT | **Yes** for stages 1–7 | **NEEDS_TECHNICAL_CONFIRMATION** |
| MIR-07 | **Gateway or SharePoint?** Where will the Service read source files from? | Local `pRootFolder` needs a gateway (§7.4) | Determines stage 8 design | Design stage 8 for SharePoint Folder (the cleaner path) and keep a gateway variant documented | n/a | A decision + the SharePoint site URL | You / Honasa IT | **Yes** | NEEDS_TECHNICAL_CONFIRMATION |
| MIR-08 | Service principal — can one be registered, and can the tenant setting *"allow SPNs to use Power BI APIs"* be enabled? | Required for `fabric-cicd` and unattended refresh | Without it, deployment stays manual | Stages 1–7 need no identity | n/a | App registration + workspace role | Honasa IT / Entra admin | **Yes** for 1–7 | NEEDS_TECHNICAL_CONFIRMATION |
| MIR-09 | Does a `.pbix` with the 14 pages actually exist and is it current? | PBIP migration starts from it | Determines whether §7.3 step 1 is one hour or a full assembly | Assume yes; if not, §7.3 step 1 becomes "assemble per PageLayouts.md first" | n/a | The file, or confirmation it's unbuilt | MT Analyst | **Yes** | NEEDS_TECHNICAL_CONFIRMATION |
| MIR-10 | Owners for each dataset/page (`PageReadiness.Owner`) | Failure routing | Failures have no addressee | Default all to "MT Analyst" | n/a | Real names | You | **Yes** | CAN_INFER |
| MIR-11 | Per-column null tolerances | `nulls_within_threshold` | Threshold guessed | Infer from current data: set to observed max + headroom, mark `[inferred]` in the YAML | n/a | Business-confirmed thresholds | MT Analyst | **Yes** | CAN_INFER |
| MIR-12 | Mapping validation columns are still `Pending` in `ChainAccount_Mapping_Inferred.csv` (1,536 rows; 276 prioritised) | Feeds mapping-completeness QC | Rule would fail immediately if made blocking | Ship the rule at **WARN** first; promote to FAIL once the 276 priority rows are validated | n/a | Filled `Validation Status` columns | MT Analyst | **Yes** | CAN_INFER |
| MIR-13 | `docs/Desktop_Assembly_Checklist.md` | Referenced by your brief, absent (G-10) | Doc reference dangles | Point at `PowerBI/README.md` §"One-time setup" | n/a | Decide: create or retire the reference | You | **Yes** | FUTURE_ENHANCEMENT |
| MIR-14 | Retention policy for `reports/runs/` | Repo growth | Unbounded growth eventually | Keep 24 months, prune in CI | n/a | Confirmed policy | You | **Yes** | FUTURE_ENHANCEMENT |

---

## 10. Deliverable 10 — Implementation Roadmap

Every phase names exact files. **Phases A–D need no licensing and no Power BI at all.**

### Phase A — Discovery & baseline ✅ complete
**This document.** Acceptance: gap matrix and target architecture approved by you.
Rollback: n/a.

---

### Phase B — Fix the two broken source-of-truth paths *(P1, do first, do alone)*
**Why first:** these are defects, not enhancements, and they're the reason the Power BI
model cannot be rebuilt from the repo.

**Create/change:**
- `PowerBI/PowerQuery/41_DistContWeights.pq` — repoint from the gitignored XLSX to
  `SeedData\DIST\DistPrimaryContWeightsArticle.csv`; filter `Approval_Status="Approved"`;
  preserve the normalise-to-1 logic and the `[Raw Pct Sum]` QC column verbatim.
- `PowerBI/SeedData/DIST/ChainAllocationWeights.csv` — **new, generated once** via
  `scripts/extract_xlsx_to_csv.py`, then committed.
- `scripts/build_dashboard_data.py` — `load_chain_allocation_weights`: replace the
  silent `return None` with a raised error unless an explicit `--allow-missing-weights`
  flag is passed.
- `PowerBI/docs/DistributorPrimaryAllocation_Logic.md` — record the source switch in
  the existing audit-trail section.

**Dependencies:** MIR-02 (one local extract from your machine).
**Tests:** existing `test_dist_allocation_governance.py`, `test_phase5_offtake_wiring.py`;
new assertion that per-key `Frac` sums to 1.0 in the committed seed.
**Acceptance:** FY25/FY26 numbers in `data.js` **byte-identical** before/after (the
CLAUDE.md rule); PQ 41 loads with only repo files present.
**Rollback:** `git revert`; single focused commit.

---

### Phase C — Data contracts
**Create:** `schemas/*.yml` (7 datasets), `config/source_registry.yml`,
`config/qc_rules.yml`, `pipeline/validate/validate_sources.py`,
`scripts/test_schemas.py`.
**Change:** `RefreshGuide.md` §3 and each `RawDataFolders/*/_README.txt` become
*generated* from the schemas (removes G-05's triplication); add `PyYAML` to both
workflows' pip install.
**Dependencies:** Phase B. **Tests:** every schema validates against the files
currently in the repo — the contract must describe reality on day one.
**Acceptance:** `validate_sources.py` exits 0 on the current repo and exits 1 on a
deliberately corrupted copy of a real file.
**Rollback:** delete `schemas/` + `config/`; nothing else depends on them yet.

---

### Phase D — QC automation & workflow consolidation
**Create:** `.github/workflows/pipeline.yml`; `pipeline/report/manifest.py`.
**Change:** extend `scripts/qc_dashboard.py` with the Stage-A source checks (reusing
its existing `qc()` helper and PASS/WARN/FAIL/BLOCKED vocabulary — **do not** add a
fifth status); retire `qc.yml` and `dataeng.yml` **only after** `pipeline.yml` is green
on a PR.
**Acceptance:** one workflow, `qc_dashboard.py` invoked once, `qc_report.txt` artifact
retained, first `reports/runs/*.json` written.
**Rollback:** restore the two old workflow files (kept in git history).

---

### Phase E — Sample / WIP framework
**Create:** `PowerBI/SampleData/`, `pipeline/sample/generate_sample.py`,
`PowerBI/SeedData/Status/PageReadiness.csv`,
`PowerBI/PowerQuery/45_PageReadiness.pq`, `PowerBI/DAX/14_Readiness_Measures.dax`.
**Change:** add `pIncludeSampleData` to `00_Parameters.pq` (default `false`);
`PageLayouts.md` gains a one-line "WIP banner card" note per page — no visual moves.
**Dependencies:** Phase C. **Acceptance:** Nielsen and TDP pages render a WIP banner
instead of empty visuals; the `sample_data_in_production` rule fails a deliberately
mis-flagged file.
**Rollback:** set `pIncludeSampleData=false` and delete the readiness query; all
additive.

---

### Phase F — Power BI source control (PBIP)
**Create:** `PowerBI/Project/MT_Leadership_Dashboard/` (PBIR + TMDL),
`scripts/test_model_parity.py` (measure names in `DAX/*.dax` ⊆ TMDL measures).
**Change:** `PowerBI/README.md` gains a "developing from the PBIP" section; the
paste-in path stays documented and supported.
**Dependencies:** MIR-09; one Desktop session. **No licensing.**
**Acceptance:** PBIP opens in Desktop, refreshes locally against repo files only, and
`git diff` on a measure change shows a readable one-line TMDL diff.
**Rollback:** the `.pbix` workflow is untouched throughout; delete `Project/`.

---

### Phase G — Refresh & deployment automation *(licensing gate)*
**Blocked on MIR-06/07/08.** Create `pipeline/publish/{sync_sharepoint,refresh_dataset}.py`,
`pipeline/validate/postrefresh_qc.py`, `config/refresh_config.yml`; add
`fabric-cicd` to a `requirements-deploy.txt`; add the gated jobs to `pipeline.yml`
behind a GitHub environment with required reviewers.
**Acceptance:** a merge to `main` refreshes the Service dataset, Stage-C DAX assertions
pass, and the run manifest carries a real `PowerBIRefreshID`.
**Rollback:** disable the environment; stages 1–7 continue unaffected.

---

### Phase H — Production hardening
Failure→GitHub-issue automation; notification routing; `reports/runs/` retention
(MIR-14); secret rotation runbook; a documented rollback drill (redeploy previous tag
via `fabric-cicd`); promote `mapping_completeness` from WARN to FAIL once MIR-12 lands.

---

## 11. Final Answer

> *What is the safest, most maintainable, least-manual architecture that lets the Power
> BI Build Kit become a repository-driven automated BI system while incomplete
> datasets/pages remain operational as controlled WIP components?*

**A metadata-driven Python pipeline in GitHub Actions that owns validation,
governance and QC; a PBIP-versioned semantic model deployed by `fabric-cicd`; and
Power BI Service doing refresh via REST API — with Power BI Desktop demoted from
operating tool to authoring tool.**

Five load-bearing decisions:

1. **Do not automate Power BI Desktop.** It cannot run under a system account and its
   command line is installer-only. Automating the current SOP literally would build
   something fragile and unsupported. Automate the *outcome* — a refreshed, validated
   semantic model — through documented APIs instead.
2. **Python stays the authoritative governance engine.** It is already integrated,
   already tested, and already handles cross-dataset temporal logic that DAX and M
   express badly. Its output becomes a **governed input table** for Power BI. DAX 09
   keeps only its independent reconciliation cross-check — which is worth having twice
   — and loses its duplicate tier derivation.
3. **The repository is already the landing zone.** 31 raw monthly CSVs are tracked
   today. That is the single biggest enabler in the current state, and it means
   validation, governance, transformation and QC — steps 1–9 of the target flow — can
   be fully automated **now, with no licensing at all**.
4. **PBIP adoption is free and should not wait for licensing.** Committing PBIR+TMDL
   closes the "no versionable artifact" gap for the cost of one Save-As, and it is the
   direction Microsoft is actively moving the platform. Deployment automation attaches
   later, when a capacity exists.
5. **WIP is a first-class state, expressed in the vocabulary the repo already has.**
   PASS / WARN / FAIL / **BLOCKED** already encodes "documented data dependency, needs
   business approval not a code fix". Extending it — rather than inventing a parallel
   status system — is what lets Nielsen, TDP and weekly-primary stay visibly
   unfinished without either breaking the report or lying to its readers.

**Start with Phase B.** Two files are pointing at data that isn't in the repository;
until that's fixed, no amount of pipeline sits on solid ground.

---

## 12. Sources

Microsoft platform claims in §7 and §8 were verified against these official pages via
indexed search (direct page fetch was blocked by this environment's egress proxy —
re-verify before committing spend):

- [Power BI Desktop projects (PBIP) — overview](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-overview)
- [Power BI Desktop project semantic model folder (TMDL)](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-dataset)
- [Create a Power BI report in enhanced report format (PBIR)](https://learn.microsoft.com/en-us/power-bi/developer/embedded/projects-enhanced-report-format)
- [PBIR will become the default Power BI Report Format — get ready for the transition](https://powerbi.microsoft.com/en-us/blog/pbir-will-become-the-default-power-bi-report-format-get-ready-for-the-transition/)
- [Announcing general availability of TMDL](https://powerbi.microsoft.com/en-us/blog/announcing-general-availability-of-tabular-model-definition-language-tmdl/)
- [Deploy Power BI projects (PBIP) using fabric-cicd](https://learn.microsoft.com/en-us/power-bi/developer/projects/projects-deploy-fabric-cicd)
- [Deploy a Power BI project using Fabric APIs](https://learn.microsoft.com/en-us/rest/api/fabric/articles/get-started/deploy-project)
- [Overview of Fabric Git integration](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/intro-to-git-integration)
- [Get started with Git integration (GitHub prerequisites, 50 MB limit)](https://learn.microsoft.com/en-us/fabric/cicd/git-integration/git-get-started)
- [Overview of Fabric deployment pipelines](https://learn.microsoft.com/en-us/fabric/cicd/deployment-pipelines/intro-to-deployment-pipelines)
- [Fabric lifecycle management FAQ (Enhanced Metadata retirement, 12 Feb 2026)](https://learn.microsoft.com/en-us/fabric/cicd/faq)
- [Enhanced refresh with the Power BI REST API](https://learn.microsoft.com/en-us/power-bi/connect-data/asynchronous-refresh)
- [Automate Power BI Premium workspace and semantic model tasks with service principals](https://learn.microsoft.com/en-us/power-bi/enterprise/service-premium-service-principal)
- [Semantic model connectivity and management with the XMLA endpoint](https://learn.microsoft.com/en-us/fabric/enterprise/powerbi/service-premium-connect-tools)
- [Configure scheduled refresh](https://learn.microsoft.com/en-us/power-bi/connect-data/refresh-scheduled-refresh)
- [Manage your data source — import and scheduled refresh (gateway)](https://learn.microsoft.com/en-us/power-bi/connect-data/service-gateway-enterprise-manage-scheduled-refresh)
- [Download Power BI Desktop (system-account / WebView2 limitation, install-only switches)](https://learn.microsoft.com/en-us/power-bi/fundamentals/desktop-get-the-desktop)
- [Plan CI/CD for Microsoft Fabric solutions](https://learn.microsoft.com/en-us/fabric/fundamentals/understand-best-practices-fabric-cicd)
- [fabric-cicd documentation](https://microsoft.github.io/fabric-cicd/0.1.31/)
