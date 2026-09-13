# Git Recovery Matrix

**Created:** 2026-09-13, in response to a direct request to search merged/unmerged
Git history for valid business data that existed at some point but is missing,
superseded, or unused in the current canonical project state — before doing any
further dashboard-visual work. Non-destructive throughout: every historical file
below was inspected with `git show <commit>:<path>` (read-only), never `git
checkout`/`git reset` against the working tree, and nothing on `main` or the
current branch's history was altered by this investigation.

**Scope of this pass:** targeted searches for Primary/Offtake/Secondary/Claims/
Promotions/Trade-Spend/COGS/Logistics/CM2-related file additions and deletions
across `git log --all` (1,124 commits, ~140 local + remote-tracking branches).
This is a search, not an exhaustive line-by-line audit of every historical
commit — a new candidate found later should be added as a new row, not treated
as evidence this pass was incomplete.

## Method

```
git log --all --diff-filter=D --summary          # every file ever deleted, any branch
git log --all -S"<term>" --oneline               # commits that added/removed a string
git log --all --follow --oneline -- <path>        # full history of one path incl. renames
git show <commit>:<path>                          # read a historical version, no checkout
git branch -a --contains <commit>                 # which branches carry a commit
git merge-base --is-ancestor <commit> main         # was it ever merged
```

## Recovery Candidates

| # | Commit | Date | Path (old -> new if renamed) | What it is | Classification | Action taken |
|---|---|---|---|---|---|---|
| 1 | `13fe0ac` | 2026-07-24 | `config/cm2_decision_register.csv`, `config/cm2_formula.csv`, `config/cm2_expense_taxonomy.csv`, `outputs/cm2/cm2_fy27_cogs_logistics.csv`, `scripts/cm2_cogs_logistics_fy27.py` | A properly-governed BL-16 CM2/logistics rate-card decision register (D1-D11, every decision correctly `PENDING_APPROVAL`), built the same day the business supplied a real (screenshot) FY27 COGS/logistics rate card. **Never merged to `main`** -- lives only on `remotes/origin/claude/june-26-sales-data-xzbhub`, superseded on `main` by a later, less rigorous session that self-certified the same rate card as "Approved" with no real Finance sign-off (the BL-16 authenticity finding from an earlier pass in this engagement). | `VALID_RECOVERY_CANDIDATE` (the governance structure) | **Recovered** verbatim to `PowerBI/Reference/CM2_Provisional/recovered_governance_20260724/` (see that folder's `README.md` for full provenance). BL-16 updated in `docs/BUSINESS_LOGIC_REGISTRY.md`. Not wired into any production calculation -- still `PENDING_APPROVAL` throughout. |
| 2 | `2e038ce` (added) / `98d582a` (deleted) | Aug 21 -> later reverted | `PowerBI/SeedData/Primary/Primary_FY202426_10.csv` | Customer-grain Primary snapshot, `FY_25-26`/`FY_26-27` only (11,032 rows) -- same shape and period as data already in production, just coarser grain and an older snapshot. Deleted by a revert of a diagnostic branch. | `SUPERSEDED` | Not restored -- current production Primary (article-grain, `Primary_Article_Monthly/`) already covers this same period at finer grain and a later snapshot date. No unique data lost. |
| 3 | `2e038ce` (earliest seen) | Aug 21 | `PowerBI/SeedData/Mapping/DistPrimary_Sheet1_FY24-25.csv` | **Still present in the current repo (not deleted).** Ship-To x Chain x Brand x Month grain, FY_24-25 only, 8,769 rows, 38 chains, 6 brands. Total NSV = Rs23,325.30L -- matches the already-registered FY25 Distributor Secondary national total (Rs23,332.36L) to within 0.03%, i.e. **this is the same real FY25 Distributor Secondary data, at a materially finer grain than what dashboard/data.js currently exposes** (`offtake.secondary_monthly_fy25` is a national-only monthly series -- no chain or brand breakdown is currently in production). | `VALID_RECOVERY_CANDIDATE` (a finer grain of an already-registered source, not new external data) | **Registered, not yet ingested** -- see `config/data_source_registry.yml` entry `fy25_secondary_chain_brand_detail`. Wiring a chain/brand-level FY25 Secondary view into the dashboard is a genuine, bounded follow-up (next autonomous action, below) -- not attempted in this pass to avoid rushing a new dashboard feature past its own reconciliation. |
| 4 | (multiple: `fbc8ab0`, `b8a8feb`, `cefbe24`, `e499f3f`, `a7d629e`) | Jul-Aug 2026 | `scripts/derive_fy25_article_primary.py` (still present, unused), `Primary_Derived_FY25/Primary_Article_Synthesized_FY25.csv` (referenced, not found in current tree) | An article-level "FY25 Primary" **synthesis** pipeline: allocates the real FY25 Distributor Secondary total down to article grain using a Pareto-assortment fallback for the ~80% of rows with no real article-level split. Its own docstring says "using distributor secondary billing ratio as PROXY." A later commit, `bccb974` (authored by a different, less careful session — "Claude Haiku 4.5"), briefly wired this synthesized Rs233.25 Cr figure into `dashboard/data.js` as if it were real FY25 Primary ("Enable FY25 (Apr'24-Mar'25) primary data in dashboard"). | `SYNTHETIC` | **Correctly NOT restored.** This is the exact dataset the `mt-distributor-secondary` skill already documents as unreliable (54,328 of 67,545 rows are `Brand_Pareto_Assortment_Fallback`). Its removal from the live `dashboard/data.js` (current `primary.fy_tags == ['fy26']` only, no `fy25` key) was correct governance, not a bug -- confirmed here so a future session doesn't "recover" it back in as if it had been lost by accident. |
| 5 | n/a (negative result) | n/a | Claims (`ClaimMaster_Quarterly/*.csv`), Promotions (`promo` block sources), Trade Spend (`MT_Spend.xlsx`, rate cards) | Searched `git log --all --diff-filter=D` for any of these domains' files being deleted anywhere in reachable history. **None found deleted.** The claim-master files, promo sources, and the still-missing `MT_Spend.xlsx`/`MTIndirect_Claim_*.xlsb` (BL-16's own flagged gaps) were never present and later lost -- they were never present in this repo's Git history at all, on any branch searched. | `NOT_FOUND_IN_ACCESSIBLE_PROJECT` | No action -- these remain genuine external-source requests (see BL-16), not a recovery task. |

## FY24-25 Primary / Offtake — reassessed after full history search

Per the governing instruction ("re-test the FY24-25 gap after Git history search
rather than continuing to describe it as an external-source gap by default"):

| Dataset | Classification after this search |
|---|---|
| FY24-25 **Primary** (real SAP/ERP billing) | `NO_REAL_SOURCE_FOUND_IN_FULL_GIT_HISTORY`. The only FY24-25 "primary" artifacts found anywhere in history (candidate #4 above) are synthetic derivations of the real Distributor Secondary total, explicitly self-labelled as a proxy by their own generating script. No genuine SAP/ERP extract for this period exists on any branch searched. |
| FY24-25 **Offtake** (chain POS) | `NO_REAL_SOURCE_FOUND_IN_FULL_GIT_HISTORY`. No file, on any branch, at any point in history, was found containing chain-level POS data for Apr'24-Mar'25. |
| FY24-25 **Distributor Secondary** | `REAL_DATA_FOUND_AND_RECOVERED` at finer grain (candidate #3) -- the national total was already known and correctly registered; what this search adds is confirmation that a real chain+brand-level breakdown of that same total exists and can be exposed, which the project did not previously have registered. |

**This does not overturn the standing conclusion** that real FY24-25 Primary and
Offtake billing/POS data must be requested from the business -- it strengthens it:
an unusually thorough, multi-month effort (visible across a dozen-plus commits) was
already made to construct a FY25 Primary proxy from Secondary data, and the project
correctly concluded that proxy wasn't good enough for production use. A future
session does not need to re-attempt this synthesis; if asked, point to
`scripts/derive_fy25_article_primary.py` and this row as the record of why it was
rejected.

## Summary table (as requested: PR/Commit, Date, Purpose, Files, Recovery Candidate)

| Commit | Date | Purpose | Files Added | Files Deleted | Recovery Candidate? |
|---|---|---|---|---|---|
| `13fe0ac` | 2026-07-24 | Stage FY27 COGS+logistics CM2 calc from a real business-supplied rate card | 4 new configs + 1 script | 0 | YES -- recovered (#1) |
| `2e038ce` | 2026-08-21 | Chhattisgarh zone correction to primary FY26 data | (modified `Primary_FY202426_10.csv`) | 0 | Superseded (#2) -- but the sibling `DistPrimary_Sheet1_FY24-25.csv` in the same lineage is a live recovery candidate (#3) |
| `98d582a` | (revert) | Revert an offtake-pipeline diagnosis branch | 0 | `Primary_FY202426_10.csv` + others | No (#2, superseded content) |
| `bccb974` | 2026-08-31 | (Incorrectly) enable synthesized FY25 Primary in the live dashboard | `scripts/derive_fy25_article_primary.py` | 0 | No -- synthetic (#4), correctly reverted since |
| `a617391` | (already known from prior pass) | Reorganize CM2_Provisional folder | -- | -- | Context for #1's "superseded on main" note |

## What this investigation deliberately did not do

- Did not run any destructive Git command (no `reset --hard`, no `checkout` of an
  old commit over the working tree, no branch deletion).
- Did not restore old **code** wholesale -- only inspected it, and only copied
  data/config files that are inert until explicitly wired in (candidate #1's
  files are not read by `build_dashboard_data.py`).
- Did not exhaustively diff every one of the ~140 branches against `main` --
  targeted string/filename searches were used, consistent with the size of this
  repository's history. A branch-by-branch full diff is a much larger task that
  would need its own explicit scoping if genuinely wanted.
