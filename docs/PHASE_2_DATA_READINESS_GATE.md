# Phase 2 Data Readiness Gate

Defines the non-destructive validator that must classify a supplied FY26
store×article extract before any cohort/SSG calculation is allowed to use
it. Implementation: `scripts/store_history_readiness.py`. Tests (synthetic
fixtures only, no real FY26 data exists to test against):
`scripts/test_store_history_readiness.py`.

## 1. Folder structure — adapted to this repo's existing convention

The generic `data/raw/` / `data/processed/` / `data/qc/` layout doesn't
match how this repo actually organizes source data, and creating it would
stand up a second landing-zone convention alongside the one already in
use — exactly the "two pipelines for the same thing" risk
`docs/FAILURE_MODE_REGISTER.md` (FM-05/FM-10) warns about. Using the
existing convention instead:

```
PowerBI/RawDataFolders/
  Offtake_Monthly/                          <- already exists, holds the real FY27 files
    offtake_store_article_Apr_26.csv        <- already exists
    ...
    offtake_store_article_Apr_25.csv        <- FY26 files land HERE, same folder,
    ...                                         once supplied (the production loader
                                                 already searches this folder recursively
                                                 via rglob(), so a FY26/ subfolder under
                                                 it works exactly the same as flat files)
```

Source files are never modified or moved once landed — the existing
convention's own discipline (this repo's raw folders are gitignored,
untouched inputs; only generated outputs like `dashboard/data.js` are
tracked).

**Readiness-gate output** (the validator's report, crosswalk candidates,
and any QC findings) does **not** go into `dashboard/data.js` or any
tracked production block — it follows the existing precedent set by
`scripts/npi_reconciliation_report.py --out-dir`: a JSON evidence report
written to a caller-specified, non-production directory (default
`docs/phase2_qc/` for a run against real data, or a `tmp_path` for tests).
Nothing under a QC output directory is tracked in git by default; if a run
against real data produces a report worth keeping as permanent evidence,
it gets committed explicitly and named for what it validated (mirroring
how `docs/ALLOCATION_CAPABILITY_MATRIX.md`'s before/after evidence was
committed deliberately, not auto-tracked).

## 2. What the validator checks

Implemented in `scripts/store_history_readiness.py`, function
`validate_store_history(df, control_total=None)`. Each check produces an
independent pass/fail/warn result — the overall verdict (§4) is derived
from all of them together, never from one check alone.

| # | Check | What it catches |
|---|---|---|
| 1 | Required-column presence | Missing `Month`/`Chain`/`Store Code`/`Article`/`Units`/`NSV` — hard block, nothing downstream can run without these |
| 2 | Month coverage | Which of the 12 FY26 months (Apr'25–Mar'26) are actually present; partial coverage is reported exactly, never rounded up |
| 3 | Duplicate rows at declared grain | More than one row for the same (Month, Chain, Store Code, Article) — aggregated, never silently deduplicated by picking one arbitrarily |
| 4 | Duplicate/conflicting store identity | The same (Chain, Store Code) resolving to more than one Store_Name, State, or City within a single month |
| 5 | Missing identifiers | Null/blank Store Code, Article identifier, or Chain — counted and reported, rows not silently dropped |
| 6 | Article/EAN mapping quality | % of rows with a plausible identifier (non-blank, matches an expected format) vs. blank/garbage |
| 7 | Invalid financial values | Non-numeric NSV/Units after coercion, or values outside a sane range (e.g. NSV magnitude wildly inconsistent with the rest of the file) |
| 8 | NaN/Infinity | Explicit `pd.isna()`/`isinf()` check on every numeric column — this is the boundary check PR #167's own tests already established the pattern for, applied here at ingestion instead of publication |
| 9 | Missing-as-zero treatment | The validator itself never calls `.fillna(0)` on NSV/Units when computing its own report — a genuinely absent row and a real recorded zero are counted and reported as two different numbers, never merged (see `docs/PHASE_2_DATA_CONTRACT.md` §2 for why the production loader's `.fillna(0.0)` pattern must NOT be inherited here) |
| 10 | Source total reconciliation | Only run when a `control_total` is explicitly supplied by the caller (e.g. a Finance-confirmed FY26 total) — compares `SUM(NSV)` in the file against it within a stated tolerance; marked `NOT_CHECKED` (never assumed to pass) when no control total is given |
| 11 | FY26-vs-FY27 store identity continuity | Runs the same `(Chain, Site Code)` overlap and name-match check `docs/PHASE2_SSG_FEASIBILITY.md` did manually for Apr-vs-Aug FY27, now as reusable code, against the real FY27 files already in this repo — this is the check that actually tells us whether §2 of `docs/STORE_IDENTITY_GOVERNANCE.md`'s assumption holds at a full-year distance, not just within FY27 |

## 3. Crosswalk builder

`scripts/store_history_readiness.py`'s `build_crosswalk_candidates(fy26_df,
fy27_df)` implements the match-method cascade from
`docs/STORE_IDENTITY_GOVERNANCE.md` §3 and emits rows in that document's
exact schema (§2), each with a `Match_Method`, `Match_Confidence`, and
`Review_Status`. It never sets `Review_Status = AUTO_CONFIRMED` for
anything below `HIGH` confidence (§4 of the governance doc) — this is
enforced in code, not left to the caller's discipline.

## 4. Verdict logic and CLI exit codes

```
Verdict                          Exit code   Meaning
BLOCKED_BY_SOURCE_DATA           3           no --src given, or the file doesn't exist
BLOCKED_BY_DATA_QUALITY          4           file present, a hard-block check failed
                                              (required columns missing, or NaN/Infinity found)
READY                            0           every check passes, zero warnings
READY_WITH_GOVERNED_EXCEPTIONS   2           no hard-block failures, but some checks WARN --
                                              named, counted, never silently included or dropped
```

When no `--src` is given at all, the CLI prints both
`READY_FOR_SOURCE_INGESTION` (the gate itself is built, tested, and
waiting) and `BLOCKED_BY_SOURCE_DATA` (the actual file isn't here) — two
complementary signals, not a contradiction.

A file with real, honest gaps (some low-confidence store matches, a
partial month) is `READY_WITH_GOVERNED_EXCEPTIONS`, not `BLOCKED_BY_DATA_QUALITY`
— the gate's job is to make every exception visible and excluded, not to
demand perfection before any work can start. The first goal of running it
is to understand every exception, not to reach exit code 0 — see
`docs/PHASE_2_SOURCE_INTAKE_CHECKLIST.md` §13.

Every run also writes a machine-readable QC artifact (default
`docs/phase2_qc/store_history_readiness_report.json`, overridable via
`--out`) containing: validator version, source filename and SHA-256
checksum, row count, canonical date range, every individual check's
result, and — when a `--fy27-reference` file is supplied — the full
crosswalk candidate count, cohort-status counts, and match-method counts.
This is read-only reporting: the CLI accepts a `--dry-run` flag (default
on) for forward-compatibility, though today the validator has no write
path against production data at all to guard against — it never touches
`dashboard/data.js`, any source file, or any tracked mapping.

## 5. Current status

**No FY26 file has been supplied.** `scripts/store_history_readiness.py`
has been built and tested against synthetic fixtures only
(`scripts/test_store_history_readiness.py`). Running it against real data
is the next action once `docs/PHASE_2_DATA_CONTRACT.md`'s request is
fulfilled — see `docs/PHASE_2_EXECUTION_STATUS.md` for the standing
tracker.

**Verdict for this repository's current state: `BLOCKED_BY_SOURCE_DATA`.**
Missing dependency: a real FY26 (Apr'25–Mar'26) store×article offtake
extract, landed in `PowerBI/RawDataFolders/Offtake_Monthly/` per §1 above.
