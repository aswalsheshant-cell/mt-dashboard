# Historical Primary Chain Backfill — Apr'25 to Jul'26

Frozen methodology for CHAIN attribution of Primary billing across the 16
months Apr'25–Jul'26. Generator: `scripts/historical_primary_chain_backfill.py`.
Tests: `scripts/test_historical_primary_chain_backfill.py`.

**Scope.** This solves *which chain* a rupee of Primary belongs to. It does
**not** solve article/EAN-level Primary-vs-Offtake reconciliation — that
needs a common stable article key across Primary/Secondary/Offtake, which
does not exist yet (Primary's EAN column is corrupted — only 4 distinct
rounded values in the raw upload used for the Aug'26 work). That problem
stays `BLOCKED_PENDING_STABLE_KEY`. A clean chain backfill must not be read
as implying article reconciliation is ready — it isn't, and this PR does not
touch it.

---

## 1. Mapping-field equivalence test (systematic, not illustrative)

Question: do `Dist chain ten` (legacy schema, Apr'25–May'26), `Chain name
for Dashboard` (locked schema, Jun'26–Jul'26) and `Customer name 2` (Aug'26
raw upload) represent the same business-mapping concept?

**Method.** For every distributor appearing under 2+ of these field-name
vintages across any two months, every month's value was pulled and grouped.
"Same" means the value normalizes to an identical chain-list string (case,
whitespace, `/`-order); anything else is `CONFLICTING`.

**Result:**

| Metric | Value |
|---|---|
| Distinct distributors tested | 45 |
| Total distributor-month records compared | 439 |
| Cross-vintage-tested (2+ field names for the same distributor) | 28 |
| Distributors with a `STABLE` value across every occurrence | 22 |
| Distributors with `CONFLICTING` values somewhere | 23 |

At first read, 23 "conflicts" looks like the fields disagree. They don't —
every conflict decomposes into one specific, explainable pattern once you
group by cause:

| Category | Distributors | What's actually happening |
|---|---|---|
| `NEVER_SELF_REFERENTIAL` | 14 | Value is a real, stable chain list every month — trustworthy as-is |
| `ALWAYS_SELF_REFERENTIAL` | 9 | Value legitimately equals the distributor's own name every month (e.g. Sancus — independently corroborated earlier via 100% Delhi/NCR offtake evidence). This IS the chain identity, not a gap |
| `SOMETIMES_SELF_REFERENTIAL` | 22 | In specific months (concentrated in Sep'25, Oct'25, some Jun'26) the field falls back to echoing the distributor's own name instead of the real multi-chain list seen in every other month for that same distributor — a **data population gap**, not the field changing meaning |

**Verdict: PASS, with the conflict fully attributed.** The three field
names are the same underlying mapping concept (confirmed further by a
byte-identical row-level match: `Az Enterprises(Apollo/More)Mt` shows
`Dist chain ten` = `Customer name 2` = "Apollo/Lulu/Max Hyper/More Retails").
The "conflicts" are a known, bounded data-quality pattern in specific
months for specific distributors — never treated as evidence in those
months (see Level 1.5 exclusion below), and never silently assumed away.

Regenerate: the systematic test itself is exploratory analysis, not part of
the frozen pipeline — reproduce it by joining `primary_article_<month>.csv`
files on distributor across vintages if it needs re-running.

---

## 2. Evidence hierarchy (frozen)

One rupee of Primary enters **exactly one** level, per row, per month:

| Level | Name | Source | Governed? |
|---|---|---|---|
| 1 | `ACTUAL_CHAIN_PRIMARY` | Direct-billed rows; `Chain name` column when present, else the pooled field (locked schema has no `Chain name`) | Yes — via `canon_chain()` |
| 1.5 | `DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY` | Dist.-billed rows where the pooled field names exactly one chain (no `/`), excluding self-referential-fallback values unless already a governed alias | Yes — via `canon_chain()` |
| 2 | `PROVISIONAL_BUSINESS_MAPPED_PRIMARY` | Remaining multi-chain rows, split by `Chain_Wise_Primary_Sale_2.xlsx` (Dump sheet) ratio, same Distributor × Brand × Month | **No — PENDING OWNER APPROVAL** |
| 3 | `SECONDARY_DERIVED_PRIMARY` | Secondary-ratio fallback, only where a Secondary source exists for that month | No — modelled |
| 4 | `UNALLOCATED_PRIMARY` | No evidence anywhere | N/A — never guessed |

Every allocated row carries full provenance in `Mapping_Source`: which
level resolved it, which source file/field, and (for Level 2) the explicit
"PENDING OWNER APPROVAL" flag. `Provenance.json` (see Section 9) carries the
SHA-256 fingerprint of every source file consumed.

**Never promoted:** Level 1.5 is never reclassified as Level 1 (it's a
different governance path — a single-value pooled field, not a per-row
Direct billing chain). Level 2 is never reclassified as governed/actual
without an explicit owner approval event.

---

## 3. Exclusivity proof

For every month: `Level1 + Level1.5 + Level2 + Level3 + Level4 == raw Primary total`,
to the rupee. See `Monthly_Reconciliation_Summary.csv` — every one of the 16
months carries `Reconciliation_Diff_L = 0.000000` and `Status = PASS`,
including May'26 (via its Level 4 anomaly bucket, not a masked difference).
No row is dropped, duplicated, or fell through unclassified — every input
row appears in exactly one output row (Level 1/1.5/4) or is exploded into
1+ output rows whose values sum back to the input row (Level 2/3 splits).

---

## 4. May'26 SOURCE_SCHEMA_ANOMALY

- **Row count:** 86
- **Value:** ₹1.4237 L (₹1,42,366.17)
- **Affected Ship-To:** 100% `Reliance Retail Ltd (Azorte)_Shipto`
- **Root cause:** `PO Type` column holds `Sales`/`MRN` — values that belong
  to `MTD-Sale type`, not `PO Type` — on these 86 rows only, in
  `primary_article_May_26.csv`. Looks like a column-shift export glitch.
- **Treatment:** classified `SOURCE_SCHEMA_ANOMALY`, routed to
  `UNALLOCATED_PRIMARY`. **Not** inferred as Direct or Dist. despite the
  pattern looking guessable — a source-owner confirmation of the true
  `PO Type` is the right fix, not an assumption. Included in the
  reconciliation via the Level 4 bucket, so May'26 still reconciles exactly.
- **Source file:** `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_May_26.csv`
  — SHA-256 fingerprint recorded in `Provenance.json` under `May'26`.

---

## 5. Unallocated register (Apr'25–Jul'26)

16 register lines (grouped by Month × Distributor × Brand × Category),
532 underlying rows, summing to **₹183.1625 L** — exactly the Level 4 total
across all 16 months.

| Category | Register lines | Value (₹L) |
|---|---|---|
| `SOURCE_SCHEMA_ANOMALY` | 3 | 1.4236 |
| `MAPPING_NOT_FOUND` | 13 | 181.7389 |
| `AMBIGUOUS_MAPPING` | 0 | 0.0000 |
| `OTHER` | 0 | 0.0000 |

No mapping was invented to shrink this number. `MAPPING_NOT_FOUND` rows are
concentrated in Oct'25–Nov'25 (Az Enterprises across several brands) and
Apr'26 (Az Enterprises(Apollo/More)Mt) — the same distributor whose pooled
field is `SOMETIMES_SELF_REFERENTIAL` (Section 1), and for which no
workbook row exists in those specific months. Recommended action: add the
missing Distributor × Brand × Chain rows to the next workbook refresh; see
`Unallocated_Register.csv` for the full line-by-line detail and recommended
action per row.

---

## 6. D-Mart-Offline (Oct'25, ₹629.9 L) — resolved as a script defect, not a business ambiguity

**Investigation.** The pooled field (`Dist chain ten`) reads
`D-Mart-Offline` for 864 Oct'25 rows and `DC-D-Mart-Offline` for 498 Sep'25
rows — both ungoverned or narrowly-governed strings distinct from the
"D-Mart" seen in other months. This looked like it might be a second,
distinct D-Mart entity requiring an alias decision.

**Finding.** These are **Direct** rows (`PO Type = Direct`), and Direct
rows' true chain field is `Chain name`, not the pooled field. For every one
of these 864 (Oct'25) and 498 (Sep'25) rows, `Chain name = "D-Mart"` —
unanimous — and the Ship-To roster (`Avenue Supermarts Ltd.-DC-####`) is
identical to the roster that resolves to plain `D-Mart` in every adjacent
month (Nov'25, Dec'25, and Sep'25/Oct'25 too, via `Chain name`). The
pooled-field value (`D-Mart-Offline` / `DC-D-Mart-Offline`) is an
operational/warehouse-routing tag that happens to live in the same column
as the chain-pooling field for distributor rows — it was never meant to
override `Chain name` for Direct rows.

**Verdict: SAME_CHAIN_CONFIRMED.** This did **not** require an owner
alias decision, because the underlying source data was never ambiguous —
`Chain name = "D-Mart"` was correct and available all along. The apparent
ambiguity was introduced by an early draft of this backfill script, which
(incorrectly) keyed Direct rows off the pooled field instead of `Chain
name`. **Fixed** in `historical_primary_chain_backfill.py`: Direct rows now
use `Chain name` whenever that column exists (Apr'25–May'26); only the
locked schema (Jun'26–Jul'26, which drops `Chain name` entirely) falls back
to the pooled field for Direct rows, and that fallback is flagged
explicitly in `Mapping_Source`. No new chain alias was added — `DMart` was
already governed via `canon_chain("D-Mart")`; the fix routes Direct rows to
the field that already resolves there.

Confirmed no regression on any other chain: fixing this only relabels
which chain Direct rows are credited to (still Level 1 either way) — it
does not move any rupee between hierarchy levels, so Section 3's and
Section 7's per-level totals are unaffected by this fix.

---

## 7. Month-by-month reconciliation

See `Monthly_Reconciliation_Summary.csv` for the full table (Raw Primary,
Actual, DistChainTenSingle, Provisional, Secondary-Derived, Unallocated,
Reconciliation Diff, Status — one row per month, Apr'25–Jul'26). Every
month: `Status = PASS`, `Reconciliation_Diff_L = 0.000000`.

Aggregate across all 16 months:

| Level | ₹L | % of total |
|---|---|---|
| Total Primary | 51,481.65 | 100.00% |
| ACTUAL_CHAIN_PRIMARY | 33,364.99 | 64.81% |
| DIST_CHAIN_TEN_SINGLE_CHAIN_PRIMARY | 7,478.42 | 14.53% |
| PROVISIONAL_BUSINESS_MAPPED_PRIMARY (pending owner approval) | 9,455.51 | 18.37% |
| SECONDARY_DERIVED_PRIMARY | 0.00 | 0.00% |
| UNALLOCATED_PRIMARY | 183.16 | 0.36% |

Secondary-derived is 0 across the board because no Secondary source exists
in this repo for any of the FY26 months (Apr'25–Mar'26); FY27 months
(Apr'26–Jul'26) have a Secondary hierarchy file, but every Dist. row in
those months resolved earlier in the hierarchy (Level 1.5 or Level 2)
before reaching Level 3.

---

## 8. Regression / adversarial tests

`scripts/test_historical_primary_chain_backfill.py`, 18 tests, all passing.
Covers: legacy schema, locked schema (including the Direct-row fallback),
blank mapping, single-chain mapping, multi-chain mapping (unresolved and
workbook-resolved), malformed/unknown PO Type, missing required column,
unknown distributor, cross-month workbook isolation, same-distributor
different-month splits, the **Kottaram alias-ordering regression**
(workbook lookup must use the raw Ship-To spelling, not the Secondary alias),
the **self-referential-fallback regression** (a distributor echoing its own
name is not trusted as Level 1.5 unless it's a governed alias), the
**D-Mart-Offline fix** (Direct rows key off `Chain name`, not the pooled
field), no NaN/Infinity, no silent row loss, and exact reconciliation on a
mixed batch.

---

## 9. Provenance

Every run writes `Provenance.json` alongside the outputs: generation
timestamp, the list of months covered, and a SHA-256 fingerprint (path,
hash, byte size) for every `primary_article_<month>.csv` file consumed plus
the workbook Dump-sheet snapshot and the Secondary hierarchy file. The
per-month reconciliation summary is embedded in the same file so a given
output set is self-describing: which source files, which hashes, which
totals.

The workbook itself (`Chain_Wise_Primary_Sale_2.xlsx`, business-maintained,
authored by Kanhaiya Pandey, 2026-07-15) is not committed — Excel binaries
don't diff cleanly and the repo's real Secondary/Primary sources are
already CSV. Its `Dump` sheet is committed as a frozen CSV snapshot at
`PowerBI/SeedData/Mapping/ChainWisePrimarySale_Dump_Snapshot.csv` (columns:
`Month, Bill to customer, Brand, Chain Name, NSV`) so the backfill is
reproducible without needing the original upload. Refreshing this snapshot
from a newer workbook version is a deliberate, visible action — re-export
the `Dump` sheet with `pandas.read_excel(path, sheet_name="Dump", header=1)`
and overwrite the snapshot file; the change shows up as a normal diff.

---

## 10. Regenerating the outputs

```bash
python scripts/historical_primary_chain_backfill.py \
    --out-dir historical_primary_chain_backfill_output
```

Defaults read `PowerBI/RawDataFolders/Primary_Article_Monthly/`,
`PowerBI/SeedData/Mapping/ChainWisePrimarySale_Dump_Snapshot.csv`, and
`PowerBI/RawDataFolders/SecondarySales_Monthly/secondary_sales_tot_hierarchy_Apr_Aug_2026.csv`.
Output directory is gitignored (`historical_primary_chain_backfill_output/`)
— it is large (~120 MB combined detail across 16 months, ~430K rows) and
fully reproducible from committed sources, so it is not committed. No raw
source file is modified by this script.

---

## Explicitly out of scope for this methodology / this PR

- **Article-level Primary-vs-Offtake reconciliation.** Blocked on a common
  stable article key; this backfill solves chain attribution only.
- **Owner approval of the Level 2 provisional mappings** (₹9,455.51 L,
  18.37%). This PR freezes the *methodology* — the mappings stay
  provisional until the business owner reviews and approves them. This
  status must never be reported as governed/actual before that approval.
- **The D-Mart-Offline decision was NOT an owner-approval item** — see
  Section 6; it resolved to a code fix, not a business judgement call, so
  there is nothing pending owner sign-off there.
- Dashboard UI, Issue #113, and promoting any provisional mapping to
  governed are all untouched by this PR.
