# Phase 2 Source Intake Checklist — FY26 Store×Article Offtake

The checklist to run through the moment a FY26 file lands, before it's
treated as anything more than "a file that arrived." Pairs with
`docs/PHASE_2_DATA_CONTRACT.md` (what was requested) and
`docs/PHASE_2_DATA_READINESS_GATE.md` (the automated validator this
checklist front-ends).

## 1. Filename & landing location

- **Where it goes:** `PowerBI/RawDataFolders/Offtake_Monthly/` (same folder
  as the real FY27 files) — a `FY26/` subfolder under it works identically,
  since the production loader (`load_offtake_article_files()`) already
  searches this tree recursively (`rglob`).
- **Filename convention:** follow the existing FY27 pattern —
  `offtake_store_article_<Mon>_<YY>.csv` (e.g. `offtake_store_article_Apr_25.csv`)
  for one file per month, or a single consolidated file if that's how it's
  supplied — the readiness gate handles either shape.
- **Never rename or edit the file** once landed — source files in this
  folder are gitignored, untouched inputs; the validator reads them
  in place.

## 2. Accepted file formats

- `.csv` (preferred, matches the real FY27 files exactly)
- `.xlsx` / `.xlsb` also acceptable — the production loader already handles
  both; `scripts/store_history_readiness.py`'s CLI currently reads `.csv`
  only (`pd.read_csv`) — a `.xlsx`/`.xlsb` file needs converting to CSV
  first, or the CLI's read step extended, before running the gate.

## 3. Mandatory columns

Exactly `docs/PHASE_2_DATA_CONTRACT.md`'s minimum set, using **this
contract's column names** (not necessarily the source's raw names — see
§5 below for the rename step):

`Month`, `Chain`, `Store Code`, `Article`, `Units`, `NSV`

The validator hard-blocks (`BLOCKED_BY_DATA_QUALITY`) if any of these is
absent.

## 4. Optional but expected columns

`Store Name`, `State`, `City` — not hard-required, but every identity and
continuity check gets materially weaker without them (no name-match
fallback, no geography corroboration for confidence scoring). Their
absence doesn't block the gate; it does widen the `PENDING_REVIEW` /
`BLOCKED_FOR_REVIEW` pile in the crosswalk.

## 5. Column rename step (before running the validator)

The real FY27 files use different raw names for the same concepts
(`Site Code` → `Store Code`, `Site Name` → `Store Name`, `Chain Name` →
`Chain`, `Sales Qty` → `Units`). **Rename to this contract's names before
calling the validator** — it deliberately doesn't guess a source's raw
naming, so it behaves identically regardless of which system produced the
file. A one-line `df.rename(columns={...})` before `validate_store_history()`
is enough; do this in a throwaway script, never by hand-editing the source
CSV.

## 6. Expected month coverage

12 months, Apr'25 through Mar'26 (THE ONE FY RULE). Partial coverage is not
a hard block (`READY_WITH_GOVERNED_EXCEPTIONS`, not `BLOCKED`) — but it
must be visible and accounted for, never silently treated as "close
enough."

## 7. Expected grain

One row per (Month, Chain, Store Code, Article) — matches the real FY27
files' registered primary key
(`config/data_source_registry.yml`, `["Month", "Site Code", "Article", "Chain Name"]`).

## 8. Allowable nulls

- `Store Name`, `State`, `City`: may be null — degrades match confidence,
  doesn't block.
- `NSV` / `Units`: may be null for a genuinely unrecorded row — the gate
  counts this separately from a real zero (`missing_as_zero_treatment`
  check) and never assumes one.

## 9. Disallowed nulls (hard block)

- `Month`, `Chain`, `Store Code`, `Article`: any of these null/blank on a
  row makes that row unusable for cohort matching — reported via
  `missing_identifiers` (warns, doesn't block the whole file, but every
  such row is excluded from the crosswalk, never guessed).

## 10. Duplicate rules

- **Duplicate rows at declared grain** (same Month+Chain+Store
  Code+Article twice): flagged (`duplicate_grain`), never silently
  deduplicated by picking one arbitrarily — a human decides whether to sum,
  keep the latest, or reject.
- **Store identity conflicts** (same Chain+Store Code resolving to >1
  Store Name/State/City within one month): flagged
  (`store_identity_conflicts`) — this is a data problem in the source, not
  something the gate can resolve on its own.

## 11. Financial-value validation rules

- Non-numeric `NSV`/`Units` after coercion: flagged, not silently zeroed.
- Negative values: reported for visibility (returns/credit notes are real,
  per PR #167's precedent), never itself a block.
- `NaN`/`Infinity`: hard block (`nan_infinity`) — these can never reach any
  downstream calculation.

## 12. Control-total requirement

**Request a Finance-confirmed FY26 total (or 12 monthly totals) alongside
the file.** Without one, `source_total_reconciliation` reports
`NOT_CHECKED` — never assumed to pass. A control total lets the gate prove
the file's own `SUM(NSV)` reconciles before anyone builds on it.

## 13. Running the gate

```bash
python3 scripts/store_history_readiness.py \
  --src PowerBI/RawDataFolders/Offtake_Monthly/<renamed FY26 file>.csv \
  --fy27-reference PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Apr_26.csv \
  --control-total <Finance-confirmed FY26 total, if supplied> \
  --out docs/phase2_qc/store_history_readiness_report.json
```

Exit codes: `0` = `READY`, `2` = `READY_WITH_GOVERNED_EXCEPTIONS`,
`3` = `BLOCKED_BY_SOURCE_DATA`, `4` = `BLOCKED_BY_DATA_QUALITY`.

**The first goal is understanding every exception, not making the exit
code green.** A `READY_WITH_GOVERNED_EXCEPTIONS` result with a fully
reviewed, named exception list is a legitimate place to build from; a
`READY` result reached by narrowing the input until nothing is left to
flag is not the same thing and defeats the point of the gate.
