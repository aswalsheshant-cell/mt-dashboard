# Phase 2A — `CHAIN_OFFTAKE_NSV` Lineage Trace

**Purpose:** Step 1 of the Phase 2A migration plan — document both the legacy and
canonical lineages end to end, with exact file:line citations, before writing any
shadow-comparison or cutover code. Verified directly against the current source
files and the live `dashboard/data.js`, not assumed from prior docstrings.

---

## Legacy (current production) lineage

```
Raw monthly extracts (offtake_fy26/<Mon'YY>/<Chain>.csv, + FY25 secondary CSVs)
        │  load_offtake_month_folders() / load_fy25_secondary()
        ▼
offtake_rebuild_block(prev, off_m, ctr_m, sec_m)     build_dashboard_data.py:2151
        │  canon_chain() name normalization applied at load time  build_dashboard_data.py:387-394
        │  per-row aggregation via nested dim_rows(key)           build_dashboard_data.py:2192-2206
        ▼
row = {"name": n, "<fy_tag_lower>": <FY sum>, "value": <ALL-MONTHS-COMBINED sum>,
       "secondary_<fy>": <FY25 secondary sum>}                    build_dashboard_data.py:2196-2205
out["by_chain"] = dim_rows("chain")                                build_dashboard_data.py:2219
        ▼
obj["offtake"] = new_off  →  json.dumps(obj)  →  dashboard/data.js
        ▼
window.DASH.offtake.by_chain   (verified live: dashboard/data.js:553-1166)
        ▼
dashboard/index.html consumers (THREE found, not one — see below)
```

**The `.value` field is confirmed all-months-combined, no FY subscript** — `dim_rows()`
(`build_dashboard_data.py:2192-2206`) computes `row["value"]` by summing every month in
`months` regardless of FY tag. Verified empirically in `data.js`: chains with no FY27
months in source (e.g. `Vijetha`) have `value == fy26` and no `fy27` key at all — so
`.value` silently equals a prior-FY total whenever a chain lacks real current-FY data.
This is exactly KI-OFFTAKE-001 (Issue #195).

There is a second, older aggregator, `offtake_block()` (`build_dashboard_data.py:862`),
with a different row shape (`{"name","raw","total"(scalar),<fy_tag>,"yoy"}`). The live
`data.js` rows match `offtake_rebuild_block()`'s `dim_rows()` shape, not `offtake_block()`'s
— confirming the `--offtake-patch`/rebuild path, not the plain full-rebuild path, is what
actually produced today's certified `data.js`. Phase 2A's canonical engine already reads
this correctly (`facts.offtake_chain_fy_values()` excludes `value`/`total`/`raw`/`yoy`
unconditionally, so it is correct against either aggregator's shape).

### Consuming UI — three distinct call sites found (not the one previously documented)

| # | Location | Feature | Fallback expression | Same KI-OFFTAKE-001 defect? |
|---|---|---|---|---|
| 1 | `dashboard/index.html:1618` | `renderInventorySubview()` — Inventory Health tab → Offtake Velocity subview → **"Top Chains by Offtake" table**. This is the consumer Issue #195 and `governance.py`'s `GOV-003` are about. | `(ch_data.total&&ch_data.total[fyR])\|\|ch_data['total_'+fyR]\|\|ch_data[fyR]\|\|ch_data.value\|\|0` | **Yes — the documented, tracked defect.** |
| 2 | `dashboard/index.html:3761` | `computeChannelHealth()` — a **different feature**: the channel/alerts stock-health ratio (feeds Operational Alerts, not the Inventory tab's chain table). | `off[r.name]=(offKey&&r[offKey]!=null)?r[offKey]:r.value;` | **Yes, same defect pattern, but NOT previously documented anywhere in `scripts/canonical/*` or Issue #195.** New finding from this lineage trace. |
| 3 | `dashboard/index.html:3524` | `fy25SecondarySection()` — Comparison tab's FY25 Secondary chain/brand view. | Reads only `c.secondary_fy25` directly; filters out chains lacking it. | **No** — a different field (`secondary_fy25`, Distributor Secondary, a different measure per CLAUDE.md's three-measures table), no fallback-to-`.value` bug. Correctly out of scope. |

**Consumer #2 is a real, previously-undocumented instance of the same class of defect,
in a different feature (Channel Health scoring) than the one Issue #195 names.** It is
not part of "the Top Chains by Offtake table" and migrating it is a separate scope
decision — see "Open scope question" below.

---

## Canonical lineage (`scripts/canonical/`, shadow mode, merged via PR #198)

```
dashboard/data.js (same certified source, D.offtake.by_chain)
        │
        ▼
canonical.facts.offtake_chain_fy_values(data, chain_name)     scripts/canonical/facts.py:77-95
    - finds the row where row["name"] == chain_name
    - returns {k: v for k, v in row.items()
               if k not in ("name","raw","value","total","yoy")
               and not k.startswith("secondary_")}
    - structurally excludes 'value'/'total' at the FACT layer -- no metric function
      built on top of this can reach them even by accident
        │
        ▼
canonical.fiscal.normalize_fy(fy) / data_key(fy)               scripts/canonical/fiscal.py
    - "FY27" -> canonical tag; data_key -> "fy27" (matches data.js's lowercase field naming)
        │
        ▼
canonical.offtake.chain_offtake_nsv(data, fy, chain)           scripts/canonical/offtake.py:28-47
    - fy = normalize_fy(fy); key = data_key(fy)
    - values = facts.offtake_chain_fy_values(data, chain)
    - if not values: return NotAvailable("no chain named ...")
    - return exact_fy_or_not_available(f"CHAIN_OFFTAKE_NSV[{chain}]", key, values)
        │
        ▼
canonical.policies.exact_fy_or_not_available(...)              scripts/canonical/policies.py:42-60
    - returns values_by_fy[requested_fy] ONLY if that exact key is present and non-null
    - else NotAvailable(reason) -- NEVER falls back to another key or field
        │
        ▼
Output: a real Lakh value (units.round_lakh applied) OR NotAvailable
        │
        ▼
Current consumers: NONE in production. Only scripts/canonical/shadow_report.py
(reconciliation proof) and tests/canonical/*.
canonical.offtake.chain_offtake_nsv_all_chains(data, fy)        scripts/canonical/offtake.py:50-57
    - {chain: chain_offtake_nsv(data, fy, chain) for chain in facts.offtake_chain_names(data)}
    - this is the function Phase 2A's shadow comparison and eventual cutover will call
```

---

## Scope question — RESOLVED

**Decision: "Table only."** Phase 2A migrates exactly consumer #1 below (`index.html:1618`).
Consumer #2 (`computeChannelHealth()`) is filed separately, not folded into this PR — see
the tracked follow-up issue this decision produced. Detail as originally raised:

Phase 2A's instruction is to migrate **exactly one production consumer: `CHAIN_OFFTAKE_NSV`**,
and explicitly **not** to modify unrelated dashboard behavior. This trace found that the
underlying data field (`offtake.by_chain[]`) actually has two live consumers exhibiting
the KI-OFFTAKE-001 defect, not one:

1. `renderInventorySubview()`'s "Top Chains by Offtake" table (`index.html:1618`) — the
   named target, matching Issue #195 and `GOV-003`.
2. `computeChannelHealth()` (`index.html:3761`) — a different feature (Operational Alerts'
   stock-health scoring), independently exhibiting the same fallback-to-`.value` pattern.

Migrating only #1 leaves #2's real defect live in a different feature after Phase 2A
"closes" the `CHAIN_OFFTAKE_NSV` migration — the underlying data-correctness problem
would only be half-fixed. Migrating both means touching a feature (Channel Health) that
was not named in Phase 2A's scope and that behaves differently enough (it computes a
ratio/score, not a displayed NSV figure) that its migration would need its own dedicated
shadow comparison, not a copy-paste of the Inventory table's.

This preserves Phase 2A's narrow scope while not letting a real discovered defect go
unrecorded — filed as [Issue #200](https://github.com/aswalsheshant-cell/mt-dashboard/issues/200).

---

## Gate 1 result — PASS, with a second real finding and its own governance entry

Running `scripts/canonical/phase2_chain_offtake.py`'s shadow comparison (Chain x FY,
the real achievable grain — see the module's docstring for why Chain x Month isn't
possible) against the certified `data.js` surfaced a SECOND real finding, distinct from
consumer-scope question above: **8 chains onboarded via a later `--offtake-patch` merge
run** (`build_dashboard_data.py:1499-1504`) have no real FY26 entry *and no `value`
fallback field at all* in `offtake.by_chain` — a row shape `{"name","raw","total":0.0,"fy27":X}`,
not the usual `dim_rows()` shape. Legacy's fallback expression therefore falls through
every link (no `.total` dict, no `total_fy26`, no `fy26` key, no `value` key) to its
final `|| 0` and silently displays a literal `0` — not a stale number like KI-OFFTAKE-001,
but the same ADR-007 missing-as-zero anti-pattern via a different mechanism.

This was deliberately **not** folded into `GOV-003` (different root cause, different
evidence) and was **not** self-approved by the agent that found it — per the self-approval
guard's own principle, `reconcile_one()` correctly returned `UNKNOWN` for these 8 chains
until an explicit approval decision was made. That decision was presented with full
evidence and approved; the resulting registry entry is `GOV-005` in `scripts/canonical/governance.py`.

**Gate 1 final result:** 58 PASS / 12 APPROVED_GOVERNED (4 via `GOV-003`, 8 via `GOV-005`)
/ 0 FAIL / 0 UNKNOWN — 100% clean population. Conservation check passes within a small,
documented rounding tolerance (~0.02–0.03 L on ~19,000–31,000 L totals, same class already
documented for `PRIMARY_NSV`). Edge-case sweep otherwise clean: no duplicate/blank/unmapped
chain names, no negative values. Proven in `tests/canonical/test_phase2_chain_offtake.py`.
