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
currently live, deployed dashboard too. Root cause: `Dist_primary_cont_based_on_
secondary_MOM.xlsx` (the cont% master this join depends on) is not present in this
environment (confirmed: not in the working tree, never added to Git history under
that name — it is a gitignored raw source file that must live only on whichever
machine last ran a full `--src`-complete build). Whether the join actually succeeds
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

## STOP condition triggered

Per this review's own Section 34 ("STOP and report rather than guess when...
allocation evidence is insufficient"): **this environment cannot fully validate
the cont%-based allocation mechanism because its one required source file
(`Dist_primary_cont_based_on_secondary_MOM.xlsx`) is not present and is gitignored
by design.** A session running with that file in `--src` would be needed to confirm
whether the exact-match/nearest-fallback logic works at all, or whether the 0%
match rate reflects a genuine, deeper join-key defect (e.g. a Ship-To name
normalization mismatch) that would persist even with the file present. **This is a
P1 finding requiring the source file (or a session run with it) to resolve**, not
something to guess at further from here.
