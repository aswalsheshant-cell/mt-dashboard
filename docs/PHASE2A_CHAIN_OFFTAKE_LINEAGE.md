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

## Open scope question (raised, not resolved, by this lineage trace)

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

**Recommendation, not yet acted on:** keep Phase 2A scoped to consumer #1 only (matches
the literal instruction and Issue #195's actual subject), and record consumer #2 as a
new, separate, tracked finding — its own follow-up issue — rather than silently folding
it in or silently ignoring it now that it's been found. This preserves Phase 2A's
narrow scope while not letting a real discovered defect go unrecorded.
