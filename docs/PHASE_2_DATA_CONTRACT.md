# Phase 2 Data Contract — FY26 Store×Article Offtake History

Defines the exact input this repo needs to compute real Same-Store Growth
(SSG). This is a contract to hand to whoever supplies the monthly
`Offtake_Monthly` drops — not a description of something already received.
No FY26 file exists in this repository as of this document (see
`docs/PHASE2_SSG_FEASIBILITY.md` for the full inventory that established
that).

## 1. What's being requested

**Apr'25–Mar'26 (FY26), store × article grain**, in the same shape as the
real FY27 files already in `PowerBI/RawDataFolders/Offtake_Monthly/`
(`offtake_store_article_Apr_26.csv` etc.) — ideally one file per month, 12
files, or one consolidated file covering all 12 months.

### Minimum required fields

| Field | Maps to (in the existing FY27 files) | Notes |
|---|---|---|
| Month | `Month` / `Revised Month` / `Year` | Must resolve to a real FY26 calendar month (THE ONE FY RULE: Apr'25–Mar'26) |
| Chain | `Chain Name` | Same chain-naming variability as FY27 — will run through the existing `canon_chain()` alias table |
| Store Code | `Site Code` | **This is the field the entire cohort key depends on** — see `docs/STORE_IDENTITY_GOVERNANCE.md` |
| Store Name | `Site Name` | Used to sanity-check Store Code matches, never as the join key itself (see governance doc for why) |
| Article Code / EAN | `Article`, `Article_1`, `EAN` | FY27 files carry multiple article-identifier columns of varying reliability — document which one FY26 actually populates |
| Brand | `Brand` | |
| Category / Sub-category | `Category`, `Sub_category` | |
| Units | `Sales Qty` | |
| Offtake Value / NSV | `NSV` | Confirm currency/unit convention (FY27 files are pre-computed Lakh-equivalent; do not assume, verify) |

### Recommended, not required

| Field | Why it helps |
|---|---|
| Distributor | Not present in the FY27 files at all — if FY26 has it, it's new capability, not a gap to fill |
| State, City | Present in FY27 (`Zone`, `State`, `City`) — helps disambiguate a Store Code collision across chains without relying on Chain alone |
| Store Format | Not present in FY27 either — useful context if available, not a blocker if absent |

## 2. What the real FY27 files actually look like (audited, not assumed)

Audited directly from the 5 real files in
`PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_{Apr,May,Jun,Jul,Aug}_26.csv`
(the `_TEMPLATE_Offtake_Monthly.csv` in the same folder is a **synthetic
example row only** — its column names, e.g. `Store Code`/`Store Name`, do
NOT match the real files' actual columns, e.g. `Site Code`/`Site Name` —
this mismatch is itself worth flagging back to whoever maintains the
template):

- **Grain:** one row per (Month, Chain, Site Code, Article) — matches
  `config/data_source_registry.yml`'s registered primary key
  `["Month", "Site Code", "Article", "Chain Name"]`.
- **Store identifier:** `Site Code`, format varies **by chain**, not by
  month (e.g. one chain uses alphanumeric mnemonics like `HINOP:003`,
  another uses small integers like `1.0`) — confirmed stable practice, not
  drift, once scoped to `(Chain Name, Site Code)`. See
  `docs/PHASE2_SSG_FEASIBILITY.md` §2 for the exact persistence numbers
  (87.9% month-over-month, 97.0% name-match on matched codes).
- **Article identifier:** three overlapping columns — `Article`,
  `Article_1`, `EAN` — with no single one confirmed as always-populated
  across all 5 months; needs a real column-by-column completeness check
  once a FY26 file exists (not assumed here).
- **Date format:** `Month` column plus a separate `Year` column in some
  files, `Revised Month` as an Excel-serial fallback in others — the
  production loader (`load_offtake_article_files()` in
  `scripts/build_dashboard_data.py`) already handles this variability with
  a fallback chain; the new Phase 2 validator (§4 below) reuses the same
  month-parsing logic rather than re-deriving it.
- **Financial measures:** `NSV`, `MRP Sales Value`, `Sales Qty`, `Margin`,
  `MRP` — column presence varies slightly month to month (e.g. `Offtake
  Status`, `Stock report`, `MRP 2` appear in only some files).
- **Chain mapping:** raw `Chain Name` strings go through `canon_chain()`'s
  alias table (`scripts/build_dashboard_data.py`) before use anywhere —
  the same table Phase 2 must reuse, never a second copy.

**Important, already-documented production behavior that Phase 2 must NOT
inherit:** `load_offtake_article_files()` (the function that actually
builds the chain-level `offtake` block in `dashboard/data.js` today)
aggregates straight to chain/zone/state-month and does **not** retain
`Site Code` downstream at all (`df.groupby(...)` never includes it), and it
converts a missing `NSV` to `0.0` via `.fillna(0.0)` during that
aggregation. That fillna is correct for a chain-level rollup (a genuinely
absent row shouldn't inflate a sum), but it would be exactly the wrong
pattern for a store-level cohort validator, which must be able to tell
"this store had a real zero-sales month" apart from "this store has no row
at all" (see the Data Readiness Gate's explicit check for this in
`docs/PHASE_2_DATA_READINESS_GATE.md` §3, item 9). Phase 2's validator is
therefore intentionally a **separate** code path from
`load_offtake_article_files()`, not a reuse of it — reusing it would
silently inherit a rollup-appropriate behavior into a grain where it isn't safe.

## 3. Registry

Not yet added to `config/data_source_registry.yml` — every existing entry
in that file describes a source that actually exists in this repo, and
registering a FY26 source before it exists would violate that convention.
Once supplied, register it there following the same 10-point "New data
source checklist" `CLAUDE.md` already requires (grain, business date
column, FY mapping, effective-dating, coverage vs. expected, duplicate
risk, downstream KPI, validation, unattended-refresh behavior) — before it
feeds any calculation, per that checklist's own rule.
