# SIS-Channel Offtake, Apr'25-Jun'26 — Ingest Notes

Generated 2026-07-22 from a real uploaded source file (not simulated):
`SIS_offtake_from_apr25_to_june26.xlsb` (SIS-channel store x article offtake,
58,373 rows, 6 chains: Shoppers Stop, Reliance Trends, Broadway, Lifestyle,
Azorte, Lifestyle Babyshop -- the same 6 chains SIS_Reconciliation.md's
primary-side channel breakdown already names as SIS).

## What "do not repeat June'26, add only what's missing" meant in practice
Row-level signature checks (Site Code + EAN + NSV, as an exact multiset
match, not just matching aggregate totals) confirmed:

| Chain | Jun'26 rows in this file | Already in `offtake_store_article_Jun_26.csv`? |
|---|---|---|
| Reliance Trends | 4,122 | **Yes — byte-identical rows.** Excluded here. |
| Broadway | 20 | **Yes — byte-identical rows.** Excluded here. |
| Azorte | 128 | **Yes — byte-identical rows.** Excluded here. |
| Shoppers Stop | 647 | **No — zero rows for this chain in Jun_26.csv.** Kept. |
| Lifestyle, Lifestyle Babyshop | 0 (no June rows in this file) | n/a |

Apr'26 and May'26 have **zero** rows for any of these 6 chains in the
existing `offtake_store_article_Apr_26.csv` / `May_26.csv` (confirmed) —
entirely missing, kept in full. Apr'25-Mar'26 (FY26): no article-level
offtake CSV exists for these months at all in this repo — entirely missing,
kept in full.

3 rows (Azorte, Month="May", Year=2027) fall outside this file's own
declared Apr'25-Jun'26 scope and can't be confidently placed in any FY
without guessing — excluded, disclosed here, not fabricated into a bucket
and not silently dropped.

**Row accounting: 58,373 source rows = 54,100 written + 4,270 excluded as
Jun'26 duplicates + 3 excluded as the 2027 anomaly.** Every row is
parsed-into-a-file or explicitly accounted for.

## Chain mapping
`Baby Shop` (1,133 rows across Apr'25-Dec'25) needed one new alias:
`Baby Shop -> Lifestyle Babyshop` in `ChainAliases.csv` (the informal/
shop-floor name for Landmark Group's existing canonical `Lifestyle
Babyshop` chain). Shoppers Stop, Reliance Trends (from the prior commit),
Broadway, Lifestyle, and Azorte all resolve directly against
`ChainMaster.csv`/`ChainAliases.csv` with no further changes needed.

## Where the files live, and why NOT in `Offtake_Monthly/`
Written to a new sibling folder, `PowerBI/RawDataFolders/Offtake_Monthly_SIS/`,
as `SIS_offtake_store_article_<Mon>_<YY>.csv` (15 files, Apr'25-Jun'26 minus
the excluded Jun'26 duplicate chains). **Deliberately not** dropped into
`Offtake_Monthly/` itself, and deliberately not named to match the
`offtake_store_article_*.csv` convention, for two concrete reasons found
while testing this exact scenario:

1. `pbi_dataset.discover_offtake_files()` / `build_dataset()` picks a
   **single latest (year, month) file** — it has no notion of merging two
   files for the same month. A same-month file sitting in `Offtake_Monthly/`
   risks being silently selected INSTEAD of the real pan-MT file (verified:
   for Jun'26 specifically, `SIS_offtake_store_article_Jun_26.csv` sorted
   alphabetically ahead of the real file among files sharing that month, so
   depending on naming this can flip which one `build_dataset()` treats as
   "the" June source).
2. `diffengine.py`'s `analyze_offtake()` (the `place`/`meeting --drilldown`
   proactive exception report) globs `*.csv` broadly in `Offtake_Monthly/`,
   not just the `offtake_store_article_` prefix. This was caught for real:
   an earlier attempt at naming these files `offtake_store_article_SIS_*.csv`
   inside `Offtake_Monthly/` made `analyze_offtake()` pick the SIS Jun'26
   file as the "prior" month instead of the real May'26 file, corrupting
   `test_diffengine.py`'s `TestAnalyzeRealData` (caught by the full suite,
   fixed by moving the files out — not shipped).

Verified after the move: `discover_offtake_files()`, `reconcile.py`'s
`_csv_fy_sums` glob, and `analyze_offtake()` all still see exactly the same
3 files (`Apr_26`, `May_26`, `Jun_26`) as before this ingest — `build-dataset`
and `reconcile-model` re-run afterward produced byte-identical results
(`source_row_count: 229460`, `unmapped_chains: 0`, `37 metrics / 0 FAIL`).
Full test suite: 349/349 passing, 3 skipped (DuckDB unavailable, unrelated).

## What this does NOT yet do
This data is now tracked, real, and available in the repo, but it is **not
yet flowing into any Fact table, `agent/pbi_build/` output, or
`dashboard/data.js`.** Two ways to close that gap, neither done here without
a deliberate decision given the blast radius on core build logic:

1. **Enhance `discover_offtake_files()`/`build_dataset()` to aggregate
   multiple files per (year, month)** instead of picking a single latest
   file — the more durable fix, but a real behavior change to code every
   existing monthly build depends on, so it needs sign-off and its own test
   coverage before shipping, not a quiet change bundled into a data-ingest
   commit.
2. **Manually merge** the Apr'26/May'26/Jun'26 SIS rows into the existing
   `offtake_store_article_Apr_26.csv`/`May_26.csv`/`Jun_26.csv` files.
   Attempted and deliberately not done here: `offtake_store_article_Apr_26.csv`'s
   header has several columns with apparently corrupted names (`0xf`, `0x2a`,
   a bare backtick) in place of what May/June's files call `With Tax` /
   `Stock report` — a pre-existing data-quality issue in that file, unrelated
   to this task. Appending SIS rows built for the clean 38-column layout
   under that mismatched header risked silently misaligning columns, so this
   was not attempted blind.
3. **Apr'25-Mar'26 (FY26)** has no existing article-level file to merge
   into at all — building a dataset from these months today would mean
   running `build_dataset()` against the SIS-only file directly (giving an
   SIS-channel-only Fact for that month, not a pan-MT one), which is honest
   about what the file actually contains but is a decision for whoever
   drives that build, not something to do silently as a side effect of
   ingest.

`dashboard/data.js` is separately still not rebuildable in this environment
(pandas unavailable, unrelated to this file) — not attempted or claimed.
