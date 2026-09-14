# Allocation Capability Matrix

**Created:** 2026-09-13, from real repository/data evidence — not a hypothetical
cascade design. Answers: what does the DATA actually support for Distributor SAP
Primary -> Chain allocation, right now, in this repository.

## What the current allocation mechanism actually does (traced, not assumed)

`scripts/build_dashboard_data.py`'s DIST allocation (`alloc` block in
`dashboard/data.js`) works like this: rows tagged `PO Type='Dist.'` with a blank
`Chain name for Dashboard` are matched against a cont%-split master file
(`Dist_primary_cont_based_on_secondary_MOM.xlsx`, joined on Ship-To Name x Brand x
Month, falling back to the nearest month within 3 months if the exact month has no
entry) and redistributed across real chains proportionally to that master's cont%
weights. Rows with no match at all keep `Chain='Unmapped Chain'`.

## Verified current coverage (real numbers, checked against both this session's
rebuild AND the live `origin/main` production `dashboard/data.js`)

| Metric | This session's data.js | `origin/main` (live production) |
|---|---|---|
| `alloc.dist_rows_in` (distributor rows eligible for cont% split) | 55,455 | 53,136 |
| `alloc.rows_unmapped` (rows that failed to match the cont% master) | 55,455 (100%) | 53,136 (100%) |
| `alloc.chains_allocated_to` (distinct chains successfully split to) | **0** | **0** |
| `alloc.rows_nearest` (rows that used the nearest-month fallback) | 0 | 0 |
| `alloc.unmapped_nsv` | Rs18,318.41L | Rs17,104.9L |
| `alloc.governance.not_eligible_pct` | 100.0 | 0.0 (see open question below) |

**The cont%-split mechanism matches 0 rows in both cases.** This is not a
regression introduced by this session's Aug'26 ingestion — it is the state of the
currently live, deployed dashboard too. **Root cause, corrected below after a
deeper trace: not simply "file missing" — a loader-priority defect means the code
would ignore the real workbook even if it were supplied.** See "CORRECTION
2026-09-13" further down this document before reading the rest of this section.
Whether the join actually succeeds
when that file IS present is genuinely unverified from this session — this
environment cannot test that path.

## The other, broader completeness metric — already disclosed to users

`mapping_health.by_fy` (a **different, broader** measure — counts a row as mapped
if it carries ANY real chain tag, whether from Direct billing's own native chain
field or a successful cont% split, not only the cont%-split subset above) shows:

| FY | Total NSV | Mapped NSV | Unmapped NSV | Completeness | RAG (production) |
|---|---|---|---|---|---|
| FY26 | Rs32,904.08L | Rs21,808.26L | Rs11,095.82L | 66.28% | RED |
| FY27 | Rs18,581.54L | Rs12,570.24L | Rs6,011.30L | 67.65% | RED |

**This is the number already shown to users** — the Zone & Chain Scorecard's own
warning banner ("Chain-level Primary reporting: not yet reliable. Needs
mapping_completeness_pct >= 85%. Measured: 67.65%") already discloses this. Nothing
here contradicts what the dashboard already tells its users; the 0%-match cont%
finding above is a narrower, additional piece of evidence about WHY that number is
66-68% and not higher, not a hidden problem on top of it.

**Open question, not resolved this pass:** how `mapping_health`'s 66-68% mapped
figure and `alloc`'s 0-successful-chains figure relate exactly (e.g. whether most
of the "mapped" 66-68% comes entirely from Direct rows' own native chain tag, with
the Distributor cont%-split subset contributing ~0% either way) would need a
dedicated read of `mapping_health_block()`'s exact row-classification logic against
real Distributor rows carrying a non-blank chain tag from source. Flagged as a
genuine next investigation, not guessed at here.

## Named unmapped exceptions (already computed, real, actionable)

`mapping_health.exceptions` already lists the largest unmapped ship-to parties by
NSV — this is real, useful, already-computed data that answers "which specific
distributors need attention first," not a hypothetical:

| Ship-To | Cust Code | NSV (L) | Rows | Brands | Cumulative % of unmapped |
|---|---|---|---|---|---|
| Sri Vijaya Durga Agencies_Mt | 1101181 | 2,675.60 | 3,937 | Aqualogica, BBlunt, Mamaearth, The Derma Co | 15.64% |
| JUST MARK-Dmart_ship to | 1102442 | 2,360.62 | 1,268 | Mamaearth, The Derma Co | 29.44% |
| G.V Enterprises | 1101211 | 2,152.85 | 4,016 | (see full list in `data.js mapping_health.exceptions`) | ... |

This list (full version in `dashboard/data.js`'s `mapping_health.exceptions` array)
is exactly what would be sent to the business as the "please confirm the
chain for these ship-tos" request — the mechanism to close this gap already
exists (`PowerBI/SeedData/Mapping/DistAllocationGovernance_FlaggedRows.csv` +
`DistCont_Patch_Proposed.csv`, regenerated on every build), it just needs the
business decisions this session cannot make unilaterally.

## Governed allocation cascade — assessed against what the data supports

Per the instruction not to implement a hierarchy the data doesn't support: the
**smallest defensible cascade this repo's evidence supports today is two levels**,
not six:

| Level | Method | Evidence this pass found |
|---|---|---|
| A1_EXACT | Ship-To x Brand x exact Month match in the cont% master | 0 rows matched in this environment (file absent); unverified whether it works with the file present |
| B2_FALLBACK | Ship-To x Brand, nearest month within 3 months | 0 rows matched (same root cause) |
| U_UNALLOCATED | `Chain='Unmapped Chain'`, value preserved, never dropped | 100% of the cont%-eligible population, this environment |

A finer cascade (Month x Distributor x Chain x Article, Chain x Brand, Distributor x
Brand, etc., as sketched in the proposal under review) is **not evidenced by
anything in this repository** — the actual code only ever joins on Ship-To x Brand
x Month. Designing a 6-level cascade without that granularity of source evidence
would be inventing structure the data doesn't have, which this pass declines to do.

## Conservation check (real, computed from this session's rebuild)

`alloc.recon.overall` shows exact conservation (0.0 variance) for
NSV/Qty/MRP/Tax between "original" and "allocated" article-level redistribution —
**but this only proves no value was created or destroyed while passing every
unmatched row through unchanged to `Unmapped Chain`.** It does not prove the
cont%-split allocation worked; per the finding above, it did not run at all this
session. The stronger identity requested by the review (`Direct SAP Primary +
Allocated Distributor Primary + Unallocated Distributor Primary = Total SAP
Primary`) is not separately computed as three distinct, named buckets anywhere in
the current code — `alloc.unmapped_nsv` is the closest existing proxy for
"Unallocated," but "Allocated" vs. "Direct" are not separately surfaced as their
own totals. Building that explicit three-way split is real, scoped, valuable
future work — not attempted this pass given the file-availability blocker above
makes it untestable in this environment regardless.

## CORRECTION 2026-09-13 (same day, later pass) — the real root cause is not "file missing," it's a code defect that would ignore the file even if supplied

`Dist_primary_cont_based_on_secondary_MOM.xlsx` is a **legitimate, business-
maintained monthly input**, owned by the MT Channel Analyst Lead, correctly kept
outside Git for security reasons. Its absence from this build environment is
expected and by design -- not itself a defect. **The defect is in the code, found
by tracing `load_dist_cont_weights()` (`scripts/build_dashboard_data.py:4123`)
line by line:**

```python
csv_f = Path("PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv")
if csv_f.exists():
    w = pd.read_csv(csv_f)          # <-- used EXCLUSIVELY if this file exists
else:
    f = src / "Dist_primary_cont_based_on_secondary_MOM.xlsx"   # never reached
    ...
```

`PowerBI/SeedData/DIST/DistPrimaryContWeightsArticle.csv` **does exist** in this
repo (versioned in Git) and **always has** -- checked its full history
(`git log --follow`, 3 commits): it has held exactly **27 data rows** since it was
first added, every one of them an "Approved Patch" exception row (dated
2026-07-04), never the full monthly Distributor x Chain x Brand x Article
contribution weights the real workbook contains.

**This means the `if/else` is an exclusive either/or, not a per-key fallback.**
Because the 27-row CSV exists, the function returns after reading only those 27
rows and **never even checks whether the XLSX exists**, regardless of how
incomplete the CSV's coverage is. **Supplying the real workbook today, into the
`--src` directory, would have zero effect on the current code path** -- the CSV
would still win by existing at all.

Confirms exactly the pattern the business review's own Section 11 warned about
("remove single-file fragility") -- except the fragility isn't in the workbook, it's
in the loader function silently preferring an incomplete governance-patch file over
the authoritative monthly source whenever both exist.

**Recommended fix (PROPOSE_FIX, not applied without review, per the change-
governance classification this review itself defines):** change
`load_dist_cont_weights()` to load the XLSX (when present in `--src`) as the base
weights, then apply the CSV's rows as an **overlay/patch on top of it** (matching
what the CSV's own name and `Basis`/`Patch_File` columns already imply it's for),
rather than the current all-or-nothing switch. This is a deterministic, non-
semantic correction to a loading bug -- it does not touch the allocation formula
itself (Chain Contribution % x SAP Distributor Primary, confirmed to match the
business rule below), so it does not require Finance/business approval, only a
code review before merging.

## FM-16B FIX APPLIED AND VERIFIED — 2026-09-13, same day

The loader-priority fix described above has been implemented (not just proposed)
and verified with synthetic data (`tests/test_dist_cont_loader_fix.py`, 4 tests,
all real business-column shapes but no real business data):
- Base workbook alone loads correctly.
- Base + patch: the patch overrides only its own (Ship-To, Brand, Month) keys;
  every other base row survives untouched.
- Patch alone (base absent): falls through to the Priority-1 ShipTo-primary
  fallback, exactly as before this fix -- the 27-row patch never masquerades as
  a complete allocation universe.
- Malformed patch schema: fails loudly (`SystemExit`), never silently ignored.

**A second, independent bug was found and fixed in the same investigation**: the
month-parsing branch (`if w[month_col].dtype == 'object':`) silently broke under
pandas 3.x, which introduced a distinct `str` dtype for text columns that pandas
2.x never had (all text used to be `'object'`). A text month column was
therefore falling into the wrong parsing branch and returning no valid month for
any row -- this would have caused a 0%-match result even with the loader-
priority fix alone, and even with the real workbook supplied, until this pandas-
version issue was also fixed. Replaced the fragile dtype-name check with
`pd.api.types.is_numeric_dtype()` so the branch decision no longer depends on
which pandas version drew the boundary between "object" and "str".

## Real-data result -- even before the business workbook is supplied

The real workbook is still not available in this environment. But the fix
changes what happens when it's absent, too: previously, the 27-row patch file
being merely PRESENT caused the loader to use ONLY those 27 rows as if they were
the entire weights table (near-total mismatch against 55,455 real distributor
rows). Now, with no base workbook, the loader correctly falls through to the
Priority-1 ShipTo-primary fallback (`Primary_ShipTo_FY25-26_to_May26.csv`, which
IS present in this repo) -- a real source that was always available but was
never being reached because of the FM-16B defect.

| Metric | BEFORE this fix | AFTER this fix (same environment, no workbook added) |
|---|---|---|
| `alloc.rows_unmapped` | 55,455 (100%) | **167 (0.3%)** |
| `alloc.chains_allocated_to` | 0 | **29** |
| `alloc.unmapped_nsv` | Rs18,318.41L (Rs183.18 Cr) | **Rs12.13L (Rs0.12 Cr)** |
| `alloc.governance.not_eligible_pct` | 100.0 | **0.07** |
| `alloc.recon.overall` (NSV/Qty/MRP/Tax) | exact (0.0 variance) | **exact (0.0 variance), unchanged** |
| `alloc.source_label` | `dist_cont_csv` (the bug) | `shipto_primary_csv` (Priority-1 fallback, correctly reached) |
| Primary FY26 / FY27 totals | Rs32,900.37L / Rs22,239.59L | **unchanged, exact** |
| `detail_records` coverage | 100% | **unchanged, 100%** |
| Dashboard sweep | 44/44, 0 errors | **44/44, 0 errors** |

**Known remaining gap, reported honestly, not glossed over**: `mapping_health`'s
own completeness % (the one shown in the dashboard's red warning banner, 66.28%/
67.65%) is **unchanged** by this fix in this pass, because `mapping_health_block()`
is only invoked in the full/`--primary-only` build path, not `--detail-only` (the
mode used here, since a full rebuild needs source files not staged this
session). It reads the `alloc` block as an input, so it would very likely also
improve once a `--primary-only` or full rebuild is run with the newly-fixed
loader -- but that has not been run or verified this pass. Do not assume the
banner's number has already moved; it has not, yet.

## Residual certification -- 2026-09-13, same day, after the FM-16B fix

The 167 rows (Rs12.13 L) FM-16B's fix still leaves Unmapped were checked one more
way: for each row's article (EAN), does that EAN sell almost exclusively through
one chain elsewhere in the dataset? If so, that's real, defensible evidence for
where this row belongs -- not a guess.

**Corrected percentage.** Rs12.13 L against the FY26 Primary baseline of
Rs32,900.36 L is **0.037%** (12.13 / 32,900.36 x 100 = 0.0369%), not 0.07%. (The
0.07 figure that appeared in a chat reply was `alloc.governance.not_eligible_pct`,
which is correctly computed but against a *different* denominator -- total
Distributor NSV, not total Primary -- so it was the wrong number to quote for
"share of total Primary baseline." `not_eligible_pct` itself was never wrong.)

**Result** (`_classify_ean_affinity()`, wired into `allocate_dist_primary()`,
`scripts/build_dashboard_data.py`):

| Confidence | Residual class | Rows | NSV (Lakh) |
|---|---|---:|---:|
| HIGH (>=95% of the EAN's known sales go to one chain) | `DEFENSIBLE_MAPPING_AVAILABLE` | 1 | 0.10 |
| MEDIUM (80-95%) | `BUSINESS_REVIEW_REQUIRED` | 6 | 0.41 |
| LOW (<80%) | `AMBIGUOUS_MULTI_CHAIN` | 158 | 11.24 |
| No EAN match elsewhere | `NO_EVIDENCE` | 2 | 0.38 |
| **Total** | | **167** | **12.13** |

(An earlier, throwaway debug-script version of this same check, run before it was
built into the pipeline, counted the "known" population without excluding
negative-NSV rows [returns/credit notes] from the affinity denominator, and got
8 MEDIUM / 156 LOW. The production version excludes negative NSV from "known"
sales evidence -- a return at one chain shouldn't count as that chain's share of
the article's footprint -- which moved 2 rows from MEDIUM to LOW. The numbers
above are from the actual shipped code, not the earlier scratch estimate.)

**Governance decision (per business instruction, matches this project's existing
proposal-not-auto-apply pattern):**
- HIGH -> written to the proposal file as `APPROVE_CANDIDATE` (still requires
  sign-off before being turned into a real mapping -- not auto-applied).
- MEDIUM -> written to the proposal file as `REVIEW_REQUIRED`. Never auto-applied.
- LOW / NO_EVIDENCE -> remain `Unmapped Chain`. Not proposed as mappings anywhere
  (they appear only in the residual counts above) -- the article genuinely sells
  across multiple chains, so no single answer is defensible.

**New reviewable proposal file** (regenerated every `--detail-only`/full build,
same governance pattern as `DistCont_Patch_Proposed.csv`, never auto-applied):
`PowerBI/SeedData/Mapping/EanAffinity_ResidualProposal.csv` -- 7 rows (the
HIGH+MEDIUM set only). Columns: Ship To Name, Month, Brand, Article/EAN, Current
Chain, Proposed Chain, Affinity %, Confidence, Primary NSV (Lakh), Evidence
Basis, Recommended Action. Approving a row means adding it to
`PowerBI/SeedData/Masters/PrimaryAllocationOverride.csv` (the existing override
mechanism) and rebuilding -- this proposal file itself changes nothing in
`data.js` on its own.

**Machine-readable residual block** -- `alloc.residual` in `data.js`:
`residual_row_count`, `residual_nsv_lakh`, `residual_distributor_count`,
`residual_brand_count`, `residual_article_count`, `by_class` (the 4-way split
above), `residual_pct_of_total_primary` (0.022% -- computed against the full
multi-FY Primary total this `--detail-only` block processes, Rs55,139.95 L,
which is *not* the same denominator as the FY26-only 0.037% above; both are
correct for what they measure, and the doc figure above is the one that matches
the FY26 baseline this project reports elsewhere), and `materiality`:
`MATERIALITY_THRESHOLD_NOT_GOVERNED` -- this project has several *other*
materiality floors (zone recovery Rs0.25 Cr, incentive identity 3-store floor,
mapping-compression 0.20 residual-share), each governing a different metric; none
of them is an approved threshold for "unmapped chain-allocation residual as % of
Primary," so none was borrowed. The actual percentage is disclosed either way.

**Decision going forward**: this residual is not a defect to keep chasing. At
0.037% of FY26 Primary, forcing a chain guess onto the 158 LOW-confidence rows
would reduce analytical quality, not improve it (they are genuinely multi-chain
SKUs with no single correct answer). `Unmapped Chain` is treated as a valid,
disclosed, conserved state, not a gap to close by any means necessary.

Validation for this change: `python -m py_compile` clean; `--detail-only` rebuild
-- conservation exact (0.0 variance on NSV/Qty/MRP/Tax), FY26/FY27 Offtake totals
byte-identical before/after, 7/7 baseline invariants, 66 unittest (1 skipped) +
84 pytest (1 skipped) unchanged, 44/44 dashboard-sweep states clean, 0 JS errors.

## STOP condition -- narrowed to exactly one remaining item

Per Section 34: **the only thing this environment cannot do is validate the fix
against the REAL business workbook**, since it isn't present here. Everything
else in the fix (priority logic, merge semantics, schema validation, the
independent pandas-dtype bug) has been implemented and verified with synthetic
data. See "EXACT FILE NEEDED / EXACT APPROVED LOCATION" in the session's closure
report for the one remaining step.
