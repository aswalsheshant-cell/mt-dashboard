# Store Identity Governance — Canonical Crosswalk & Cohort Classification

Governs how a store in one FY's extract is matched to "the same" store in
another FY's extract, and how each match is classified before any
Same-Store Growth number is computed from it. Written before any FY26 data
exists, so every rule here is a design to validate against real data when
it arrives — not a description of a crosswalk already built.

## 1. Why this needs its own governance layer

`docs/PHASE2_SSG_FEASIBILITY.md` established that `(Chain Name, Site Code)`
is a reasonably stable join key **within the 5 real FY27 months** (87.9%
persistence, 97.0% name-match on matches). That was checked month-to-month,
4 months apart, inside one fiscal year, with files that share the same
column set and loading path. A FY26-vs-FY27 join crosses a much larger gap
(a full year, and files that may come from a different extraction process
or template revision), so the same identifier stability **cannot be
assumed** to carry over — it must be re-verified against the real FY26
file the same way, not inherited from the FY27-internal number.

## 2. Canonical Store Identity Crosswalk — schema

| Field | Meaning |
|---|---|
| `Canonical_Store_ID` | A stable ID this repo assigns once a match is confirmed — never a raw `Site Code`, since those aren't guaranteed unique across chains or years on their own |
| `FY26_Store_Code` | The raw `Site Code` (or equivalent) as it appears in the FY26 source, verbatim |
| `FY27_Store_Code` | The raw `Site Code` as it appears in the FY27 source, verbatim |
| `Chain` | Canonical chain name (post `canon_chain()`) |
| `Store_Name` | Display name — for human review only, never the join key |
| `State`, `City` | From source, where available — supporting evidence for a match, not the primary key |
| `Match_Method` | One of §3 below |
| `Match_Confidence` | `HIGH` / `MEDIUM` / `LOW` — see §4 |
| `Review_Status` | `AUTO_CONFIRMED` / `PENDING_REVIEW` / `REJECTED` |
| `Exception_Reason` | Free text — populated whenever `Review_Status` isn't `AUTO_CONFIRMED` |

## 3. Match methods (in order of preference)

1. **`EXACT_CODE_MATCH`** — `(Chain, Site Code)` identical in both FY26 and
   FY27 rows. Matches `docs/PHASE2_SSG_FEASIBILITY.md`'s validated approach
   for FY27-internal matching; whether it holds FY26-to-FY27 is exactly
   what the readiness gate (§4 of `docs/PHASE_2_DATA_READINESS_GATE.md`)
   must check before this method is trusted at that distance.
2. **`NORMALIZED_NAME_MATCH`** — `(Chain, normalized Store_Name)` matches
   when the code doesn't (handles a code renumbering that a name survives).
   Normalization = lowercase, trim, collapse whitespace, strip punctuation
   — the same class of transform that explained the 3% code-matched-but-
   name-differs cases in the FY27-internal check (`GARHAT` vs `GARIAHAT`),
   applied here as the primary method for code mismatches instead of an
   after-the-fact explanation.
3. **`CHAIN_PROVIDED_MAPPING`** — an explicit old-code→new-code mapping
   supplied by the chain or distributor, when one exists. Highest trust
   *if* the source is documented and dated; never assumed to exist.
4. **`MANUAL_REVIEW`** — anything not resolved by the above. Goes to
   `PENDING_REVIEW`, never auto-resolved.

**No fuzzy/probabilistic match may become financial truth automatically.**
A method beyond exact code or normalized name (e.g. a geographic-distance
heuristic, a partial string similarity score) may be *proposed* for a
human to confirm, but must never set `Review_Status = AUTO_CONFIRMED`
itself.

## 4. Confidence levels

| Confidence | Criteria | Auto-confirmable? |
|---|---|---|
| `HIGH` | `EXACT_CODE_MATCH`, or `NORMALIZED_NAME_MATCH` with matching State+City too | Yes |
| `MEDIUM` | `NORMALIZED_NAME_MATCH` alone (no State/City corroboration), or `CHAIN_PROVIDED_MAPPING` from an undated/informal source | No — `PENDING_REVIEW` |
| `LOW` | Any method that required a similarity threshold, partial match, or human guess | No — `PENDING_REVIEW`, flagged prominently |

A `LOW` confidence match is never silently dropped either — it stays a
named row awaiting a decision, per this repo's general "never fabricate,
never silently discard" convention (the same principle behind the
"Unallocated" disclosure bucket pattern used elsewhere, e.g.
`reliance_bc`'s FY26 zone/state/brand detail).

## 5. Cohort classifications

Applied per store, per comparison window, downstream of the crosswalk:

| Classification | Meaning |
|---|---|
| `COMPARABLE_STORE` | Matched (any confidence that reached `AUTO_CONFIRMED`), present with valid sales data in both periods |
| `NEW_STORE` | No FY26 counterpart found by any method — genuinely new in FY27, or a FY26 store this crosswalk couldn't match (the crosswalk output must distinguish these two cases via `Exception_Reason`, not conflate them) |
| `CLOSED_OR_LOST_STORE` | Matched in FY26 but has no valid FY27 sales data |
| `UNMATCHED_STORE` | Present in both years' raw source but the crosswalk could not confirm identity — mirrors `PENDING_REVIEW`/`REJECTED` crosswalk rows |
| `DATA_INCOMPLETE` | Matched, but one side has partial-month coverage insufficient for a fair comparison (mirrors `same_period_block()`'s existing shared-months discipline, applied per store instead of per portfolio) |
| `BLOCKED_FOR_REVIEW` | A `LOW`-confidence or conflicting match sitting in `PENDING_REVIEW` — excluded from every SSG calculation until resolved, not defaulted into any of the above |

This is a direct, one-grain-lower extension of the `comparability` flag
PR #167 already shipped (`COMPARABLE` / `NEW_ACCOUNT` / `EXITED` /
`NOT_COMPARABLE` on `same_period_block()`'s chain/zone/brand rows) — same
philosophy, more classes because store-level identity is a harder problem
than account-level identity (an account name rarely changes; a store code
can).

## 6. What this document does not do

It does not contain a real crosswalk — there is no FY26 data to build one
from. It is the schema and rules a crosswalk-building function
(`scripts/store_history_readiness.py`, see
`docs/PHASE_2_DATA_READINESS_GATE.md`) is validated against using synthetic
fixtures now, and will run for real the moment a FY26 file exists.
