# Aug'26 Primary vs Offtake — Data Readiness Gate

Reusable validation utility: `scripts/aug26_data_readiness_gate.py`.

Every corrected or additional Aug'26 Primary, Secondary, or Offtake file should be
re-run through this gate instead of being manually patched into a one-off
CSV. It never modifies source files or dashboard code — it only reads inputs
and reports (or, with `--promote`, records) readiness.

## Approved baseline (frozen)

As of the first promoted run:

- **7 MATCHED chains**: D-Mart, Guardian Healthcare, H&G, Metro-CNC,
  Sancus (RMT, Delhi/NCR), Travel News Services-WSmith, Wellness Forever
- Matched Primary / Matched Offtake / coverage % — see
  `Aug26_Baseline_History.jsonl`, most recent line, `coverage` block.
- Status: **PARTIAL** (below the 80% value-coverage threshold) — every output
  must carry the label `"AUG'26 PARTIAL PRIMARY VS OFFTAKE -- COVERED CHAINS ONLY"`.
- Article-level reconciliation: **BLOCKED_BY_SOURCE_KEY_QUALITY** (Primary's
  EAN column is corrupted — see Phase 7 in the script output).

`Aug26_Baseline_History.jsonl` is append-only. Never edit or delete a line —
each promoted run is a permanent record so old vs new results stay comparable
(Phase 9 delta report).

## Two things this gate deliberately does NOT do

1. **It never uses "Customer name 2" to allocate Primary.** That field (in the
   raw Aug'26 primary export) lists several chain names against one pooled
   distributor row, and looks like it might be the same thing the allocation
   methodology doc (`PowerBI/docs/DistributorPrimaryAllocation_Logic.md`)
   calls `Dist chain ten` — but that is an **observation, not a confirmed
   mapping**. The gate uses it only as diagnostic evidence in the exception
   register (to tell `MAPPING_GAP` — real primary likely exists, pooled —
   apart from a genuine `PRIMARY_SOURCE_MISSING`). Do not promote it to an
   allocation input without the data owner confirming what the field means.
2. **It never uses free-text article descriptions as a production join key.**
   Phase 7 reports a description-based match rate for visibility only. Article
   comparison stays `BLOCKED` until Primary, Secondary and Offtake share a
   reliable non-text key (valid EAN, common SAP Article Code, or an approved
   crosswalk).

## Running it

```bash
python scripts/aug26_data_readiness_gate.py \
  --primary  <path to Aug'26 primary raw invoice CSV> \
  --secondary <path to the secondary hierarchy CSV that covers Aug'26> \
  --offtake  <path to the Aug'26 store x article offtake CSV> \
  --prior-primary  PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Jul_26.csv \
  --prior-offtake  PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Jul_26.csv
```

Without `--promote` it is a dry run: it prints the full Phase 1-10 report and
a delta vs the last promoted baseline, but writes nothing. Add `--promote`
only after you've reviewed the report and are ready to record this run as the
new reference point — it refuses to write if the gate itself FAILed.

## Governed chain mapping

Chain names are canonicalized ONLY via `canon_chain()` /
`CHAIN_ALIASES` in `scripts/build_dashboard_data.py` (the same governed table
the dashboard build uses) plus one narrow, reviewed exception:
`DISTRIBUTOR_NAME_ALIAS` in the gate script, which fixes 4 cases where the
same real-world distributor is spelled differently in the Primary Ship-To
Name column vs the Secondary Distributor column (verified by exact-string
cross-check, not a fuzzy guess). Any chain string the gate cannot resolve via
these governed sources is reported `NEEDS_REVIEW` in Phase 3 — it is never
silently fuzzy-matched.

## Sequence to close the current gaps

1. Confirm with the data owner what `Customer name 2` actually represents.
2. Get corrected Secondary chain-split for the 5 pooled distributors behind
   Lulu/Spencer/Ratnadeep (see the Phase 4 `pooled_distributors` evidence).
3. Re-run this gate — it will automatically re-check all 8 tracked exceptions.
4. Get the remaining Offtake chains (Reliance, Apollo, Nykaa, Azorte, etc.);
   re-run to recompute coverage.
5. Once value coverage clears 80%, chain-level comparison can move from
   PARTIAL to full publication.
6. Article-level stays BLOCKED until a valid EAN or SAP Article Code is
   available across all three sources.
