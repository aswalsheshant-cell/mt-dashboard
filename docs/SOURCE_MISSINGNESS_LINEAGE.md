# Source Missingness Lineage — F14 & F6 Resolution (Phase 2B-A2)

**Read-only investigation. No code changed.** Resolves the two `UNKNOWN` findings
from `docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md` (F14, F6) before any Phase 2B-B
remediation begins on F2/F7/F8, per instruction: prove the source layer before
trusting or fixing any consumer built on top of it.

---

## F14 — Python-side missing-vs-zero mechanics

### End-to-end lineage traced

```
raw monthly extracts (chain-month .xlsb/.csv, article-level detail)
        │
        ▼
THREE independent chain-level writer functions (all confirmed live, dispatched by CLI flag in main()):
        │
        ├─ offtake_block()              build_dashboard_data.py:862   (default full rebuild)
        ├─ offtake_rebuild_block()      build_dashboard_data.py:2151  (--offtake-rebuild)
        └─ patch_offtake_new_months()   build_dashboard_data.py:1417  (--offtake-patch -- the
                                          mechanism that actually built today's certified data.js,
                                          per CLAUDE.md's documented monthly-refresh workflow)
        │
        ▼
JSON / dashboard/data.js publication (window.DASH.offtake.by_chain, window.DASH.primary.by_chain)
        │
        ▼
canonical accessor (scripts/canonical/policies.py::exact_fy_or_not_available) -- checks
"is this exact FY key present and non-null", never "is the value truthy"
```

### Per-writer classification

| Writer | Missing chain-FY behaviour | Zero classification | Evidence |
|---|---|---|---|
| `offtake_block()` (:862-888) | `fy_sum(d["months"], t)` = `sum(v for k,v in mn.items() if fy_of_month.get(k)==t and v)` — a **plain Python `sum()` over a generator**, unconditionally computed for **every** chain × every FY tag the whole dataset covers, regardless of whether that chain has any real months in that FY. `sum()` of an empty generator is `0`, not `None`. | **MISSING silently becomes STRUCTURAL_ZERO (fabricated)** — confirmed by direct code reading and by a controlled fixture (below) | `fy_sum` empirically returns `0`, not `None`, for a chain with zero real months in the FY |
| `offtake_rebuild_block()`'s `dim_rows()` (:2192-2206) | `names = {n for m in months for n in off_m[m][key]}` — a chain enters `names` only if it appears in **some** month of the invocation's own `off_m`. For each tag `t`, `row[lo] = r2(sum(off_m[m][key].get(n,0.0) for m in months if fy_tag_from_label(m)==t))` — **also unconditional per tag**, once a chain is in `names` it gets every tag key, defaulting missing months within a covered tag to 0.0 | **MISSING silently becomes STRUCTURAL_ZERO (fabricated)**, same mechanism as `offtake_block()`, for any tag covered by the invocation's `months` | Direct code reading, this pass |
| `patch_offtake_new_months()` (:1417-1527, **the live pipeline**) | Line 1499: `for chain, months in chain_month.items():` — **only iterates over chains present in the new source extract**. A chain absent from the new source is never touched; if it also has no prior key for that FY tag, the key stays genuinely **absent** (`undefined` in JS, not `0`). New chains get `row = {"name": chain, "raw": chain, "total": 0.0}` (:1502) — the `"total"` scalar is initialized to 0.0 and never updated by this function, but the per-FY key (`row[lo]`) is only ever set from a real source value for chains actually present in `chain_month` | **MISSING correctly stays ABSENT — no fabrication** | Confirmed both by code reading and empirically: `Vijetha`/`CNC`/`EB2B`/`Others` (`GOV-003`) genuinely lack an `fy27` key; the 8 `GOV-005` chains genuinely lack an `fy26` key AND a `.value` key, matching exactly the `{"name","raw","total":0.0}` shape this function creates for a brand-new chain |
| `primary_block()`'s `dim_rows()` (:776-789) | `pv = df.pivot_table(index=index_col, columns="FY", values="NSV", aggfunc="sum").fillna(0)` — **unconditional, for every chain × every FY tag the whole `df` covers** | **MISSING silently becomes STRUCTURAL_ZERO (fabricated)** — confirmed structurally and empirically (fixture below) | Controlled pandas fixture; also confirmed no `D.primary.by_chain` row is ever missing an `fy26` key (all 45 rows have it) — consistent with `fillna(0)` guaranteeing universal presence |

### Controlled fixtures (this session, 2026-09-24)

```python
# Reproduces primary_block()'s exact dim_rows() pattern
df = pd.DataFrame([
    {'chain':'X','FY':'FY26','NSV':100.0}, {'chain':'X','FY':'FY26','NSV':50.0},
    {'chain':'Y','FY':'FY26','NSV':10.0},  {'chain':'Y','FY':'FY27','NSV':20.0},
])
pv = df.pivot_table(index='chain', columns='FY', values='NSV', aggfunc='sum')
# BEFORE fillna(0): chain X's FY27 cell is NaN (correctly distinguishable from real data)
# AFTER  fillna(0): chain X's FY27 cell is 0.0 -- INDISTINGUISHABLE from a real recorded zero
```

| Case (per instruction) | Result | Correct? |
|---|---|---|
| A. `[100, 200]` → sum | `300` | Yes |
| B. `[100, NaN]` → sum (default `skipna=True`) | `100.0` | Yes — one real observation exists |
| C. `[NaN, NaN]` / empty group → `sum()`, default `min_count=0` | `0.0` | **No** — pandas' own docs confirm `min_count=0` (the default) lets an all-missing/empty sum return a real `0` rather than `NA`; `sum(min_count=1)` correctly returns `NaN` instead, empirically verified this session |
| D. empty group (Python builtin `sum()`, not pandas — `offtake_block()`'s `fy_sum`) | `0` | **No** — plain Python `sum()` has no `min_count` escape hatch at all; the risk is structurally identical to Case C but with no available fix short of an explicit `if not values: return None` guard |
| E. missing chain-month entirely | **Correctly `NOT_AVAILABLE`** in `patch_offtake_new_months()` (key absent); **incorrectly `0`** in `offtake_block()`, `offtake_rebuild_block()`'s `dim_rows()`, and `primary_block()`'s `dim_rows()` | Mixed — depends on which writer |
| F. real chain-month with sales = 0 | `0` (a REAL_ZERO) | Yes, and correctly indistinguishable from Case E's fabricated zero **only in the three unconditional writers** — `patch_offtake_new_months()` doesn't have this ambiguity since it never fabricates a key at all |

### Classification of every finding, per the required taxonomy

- `offtake_block()` (default full-rebuild path): **STRUCTURAL_ZERO fabrication confirmed** for any chain-FY the dataset doesn't cover for that chain. **Not currently live** — today's certified `data.js` was built via `--offtake-patch` (`patch_offtake_new_months()`), not the default full rebuild. **Real latent risk**: if anyone ever runs a full rebuild without `--offtake-patch`/`--offtake-rebuild`, this defect activates.
- `offtake_rebuild_block()` (`--offtake-rebuild` path): same conclusion — latent, not live in the current build.
- `patch_offtake_new_months()` (the actual live pipeline): **no fabrication — confirmed clean**. `CHAIN_OFFTAKE_NSV`'s `GOV-003`/`GOV-005` classifications in Phase 1/2A remain fully correct and unaffected by F14 — the canonical engine's `exact_fy_or_not_available()` choke point is working exactly as intended against the real, live source.
- `primary_block()`'s `dim_rows()` (the only Primary chain-level writer, no incremental-patch equivalent exists for Primary): **STRUCTURAL_ZERO fabrication confirmed AND live** — every row in `D.primary.by_chain` has every FY tag key present, with `fillna(0)` guaranteeing any chain lacking real data for a tag gets a literal `0.0`. **Empirically checked against the real certified data.js**: 2 chains (`Dabur New U`, `Medanta`) show `fy26: 0` — genuinely indistinguishable from "this chain had a documented real zero" vs. "this chain had zero source rows." Not yet possible to tell which without going back to the raw source workbook (out of scope for this pass — flagged, not resolved).

**F14 verdict: `MIXED — resolved, not UNKNOWN`.** The live offtake pipeline (`--offtake-patch`) is clean. The live primary pipeline (`primary_block()`, no incremental alternative) has a confirmed, currently-active fabrication for at least 2 chains, magnitude unknown without raw-source access. Two dormant offtake writers (`offtake_block()`, `offtake_rebuild_block()`) carry the same latent risk if ever invoked.

### Correction to F2's stated live impact (discovered while resolving F14)

Tracing `D.primary.by_chain`'s actual shape (zero FY27 coverage, zero `.value` field on
any row) against `computeChannelHealth()`'s exact accessors shows the originally-reported
"confidently produces a wrong result today" for F2 **overstated present-day live impact**:

- At FY27: `D.primary.by_chain` has **no** `fy27` key on any of its 45 rows (Primary's
  pre-aggregated source ends Mar'26, per CLAUDE.md's documented coverage split) — so
  `pri[c]` resolves to `undefined` → `p=0` for **every** chain, not just `GOV-003`'s 4 —
  and the `p>0&&o>0` ratio guard filters everything out. Result: the Commercial Analytics
  "Channel Health" list is simply **empty** at FY27, not populated with a wrong number.
- At FY26: `GOV-005`'s 8 chains lack **both** a `fy26` key **and** a `.value` key in
  `offtake.by_chain` (their rows come from `patch_offtake_new_months()`'s new-chain shape,
  `{"name","raw","total":0.0}`, which never gets a `.value` field) — so `off[c]` resolves
  to `undefined` → `o=0` → same guard, same safe exclusion.
- `GOV-003`'s 4 chains (`CNC`/`EB2B`/`Others`/`Vijetha`) DO have a `.value` field (their
  rows predate the patch pipeline) and DO lack `fy27`, so at FY27 the offtake side *would*
  resolve to a stale nonzero via `.value` — but the primary side's universal FY27 absence
  means `p=0` for them too, so the ratio guard still excludes them.

**Net effect: `computeChannelHealth()`'s ratio-fabrication mechanism does not currently
produce a visible wrong number in the certified data.js — it produces an empty result
where a populated one might be expected.** The underlying code defect (the offtake-side
`.value` fallback) is still real and still exactly the KI-OFFTAKE-001 anti-pattern — it is
one data-shape change away from firing (e.g. if `D.primary.by_chain` ever gains FY27
coverage while `D.offtake.by_chain` still lacks it for some chain, the primary-side `p>0`
guard would stop protecting against the offtake-side fallback). F2's classification stays
**UNCONTROLLED_FINANCIAL_TRUTH** — a real, unsafe pattern — but its urgency framing changes
from "fix a live wrong number" to "close a landmine before the next data shape change
arms it," similar in character to F8 and F10.

---

## F6 — Primary-vs-Offtake: duplicate, or legitimately different?

### The three implementations, traced end to end

| | `computeChannelHealth()` (F2) | `primary_offtake_gap_block()` (`D.primary_offtake_gap`) | `sales_actuals_block()` (noted, not deep-traced) |
|---|---|---|---|
| Location | `dashboard/index.html:3757-3794` (client-side JS) | `scripts/build_dashboard_data.py:2702-2799` (Python, pre-built) | `build_dashboard_data.py:4248` |
| Primary source (FY27) | `D.primary.by_chain` — **wrong**: has zero FY27 coverage | `fyx_primary` (`detail_meta.fyx_primary`) — **correct**: the real article-level FY27 source | Not traced |
| Offtake source | `D.offtake.by_chain`, with the unsafe `.value` fallback | `offtake.by_chain`, filtered to `if c.get("fy26")`/`if c.get("fy27")` — **never falls back to `.value`/`.total`** | Not traced |
| Missing-data policy | Falls back to a stale/wrong value (offtake side) or silently zeroes (primary side) | **Explicit, three-way split**: `matched` (both sides present) / `primary_only` / `offtake_only` — a chain missing on either side is never blended into a ratio. (Minor gap: a real `0` and a missing value are both `falsy` in the dict-comprehension filter, so a genuinely-zero chain is excluded the same as a missing one — undercounts coverage, never fabricates a wrong ratio) | `NO_SALES_DATA` bucket per its own docstring — explicit, not silent |
| Grain | Chain only | Chain **and** month, both with matched/unmatched splits | Chain, with DMS/Massit gap-fill |
| Output | Single ranked top-8 list, categorical status string | Two windows (FY26/FY27) × (by_month + by_chain, 3-way split) | Separate sales-actuals dataset |
| Consumer | Commercial Analytics `cvHealth` chart | Performance & Comparison `pogMonthChart` + table | `scripts/ingest_massit_sales.py` only — not reached by the dashboard build's own `main()` |

### Classification

**Not the same computation, and not equally correct.** `primary_offtake_gap_block()` is
the more carefully engineered of the two dashboard-facing implementations: it sources FY27
Primary from the right place, has an explicit (if imperfect) missing-data policy, and
never fabricates a wrong ratio the way `computeChannelHealth()`'s offtake-side `.value`
fallback can. They answer a related but not identical question (`computeChannelHealth()`:
"which chains look most out of balance right now, ranked" vs. `D.primary_offtake_gap`:
"here is the gap and ratio for every chain, honestly split by data coverage") using
overlapping but not identical missing-data handling.

Per the required classification: **`DERIVED_ANALYTIC`, legitimately different in grain
and correctness — not `UNCONTROLLED_FINANCIAL_TRUTH` duplication in the sense of two
implementations that could silently diverge on identical, complete inputs.** They already
diverge, but because one is right and the other has a real defect, not because of
arbitrary implementation drift on equally-valid computations.

**F6 verdict: `RESOLVED, not UNKNOWN`.** `docs/VISUAL_REGISTRY.md` finding #8's original
framing ("not proven inconsistent... a real drift risk") undersold what this trace found:
they are provably inconsistent in the specific KI-OFFTAKE-001-adjacent way F2 documents,
and the fix for F2 should **not** be a second, standalone patch — it should point
`computeChannelHealth()` (or whatever replaces it) at `D.primary_offtake_gap`'s
already-correct, already-governed by-chain data instead of recomputing a parallel,
less-correct version from raw `by_chain` arrays. `sales_actuals_block()` remains an open,
untraced fifth candidate — lower priority since it's reached only via a separate CLI
entry point, not the main dashboard build.

---

## Updated exit criteria

```
F14 classification != UNKNOWN     MET -- MIXED (live offtake path clean, live primary
                                    path confirmed fabricating, two dormant offtake
                                    writers carry the same latent risk)
F6 classification != UNKNOWN      MET -- legitimately different implementations, one
                                    demonstrably more correct than the other; the fix
                                    path is consolidation onto the correct one, not
                                    two independent patches
UNKNOWN findings = 0              MET for F6/F14. sales_actuals_block()'s own missing-
                                    data policy remains untraced (new, lower-priority
                                    open item, not one of the two required exits)
All missing->zero paths evidenced YES -- table above, per writer function
All all-null aggregations
evidenced                         YES -- Case C/D fixtures above
All empty-group aggregations
evidenced                         YES -- same fixtures; `offtake_block()`'s fy_sum and
                                    primary_block()'s dim_rows both confirmed vulnerable
No silent fallback unexplained    YES
```

## Recommended remediation proposal (not implemented — approval required)

1. **`primary_block()`'s `dim_rows()`** (`build_dashboard_data.py:776-789`): replace
   `.fillna(0)` with a policy that distinguishes "chain never had a row for this FY" from
   "chain had rows summing to a real zero" — e.g. track which (chain, FY) pairs actually
   appeared in `df` before pivoting, and only fill those with 0; leave genuinely absent
   pairs as `NaN`/dropped, matching `exact_fy_or_not_available()`'s semantics on the
   Python side instead of only the JS/canonical side. **This is a data.js-shape change**
   and needs its own shadow comparison before any cutover, per this repo's established
   playbook (Phase 2A's exact gate structure) — not a quick patch.
2. **`offtake_block()`/`offtake_rebuild_block()`**: lower priority since dormant, but the
   same fix (or an explicit doc note that these paths must never be used for a production
   rebuild until fixed) should be applied before either is ever invoked again.
3. **F2 (`computeChannelHealth()`)**: once (1) is addressed, point its Primary-side lookup
   at `fyx_primary`-derived data (matching `primary_offtake_gap_block()`'s pattern) instead
   of raw `D.primary.by_chain`, and its Offtake-side lookup at the same governed,
   no-fallback accessor `dashboard/index.html:1618` already uses (`canonicalChainOfftakeNSV`-style).
   Ideally, this becomes "read `D.primary_offtake_gap`'s by-chain data directly" rather
   than a third independent recomputation.
4. **F7/F8**: unaffected by F14/F6, still independently ready per the original inventory.

**Per instruction: none of the above is implemented. This document presents evidence and
a remediation proposal only.**
