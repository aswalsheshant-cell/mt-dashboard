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

## STOP condition -- still applies, now scoped correctly

Per Section 34 ("STOP and report rather than guess when allocation evidence is
insufficient"): **this environment still cannot run the corrected logic against
real data, because the workbook itself is not available here.** Two separate
things are needed before FM-16 can move past P1: (1) the loader fix above,
reviewed and merged, and (2) the real workbook, placed at the location named
below, so the fixed loader has something real to read. Neither can be completed
unilaterally from this session.
