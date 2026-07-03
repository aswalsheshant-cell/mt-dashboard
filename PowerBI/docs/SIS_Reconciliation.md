# SIS Reconciliation — gap open for reconciliation (NOT resolved)

> **Correction to an earlier version of this doc:** an earlier pass claimed the
> ₹250 L reading was caused by the offtake side deriving SIS with no Channel
> column, and that ₹236 L (from an older, differently-scoped dashboard build)
> was the correct figure. **That theory is ruled out below.**

## Summary (current status)
- **File 2 real SIS FY26 Primary = ₹250.17 L** — computed directly from File 2's
  own `Channel` field (`primary_article.xlsb`), no derivation, no offtake data
  involved. This is the **verified, authoritative** number.
- **The earlier ₹236 L figure is not reproduced from File 2.** It is treated
  here only as an **unresolved reference / MIS number**, not the correct value.
- **Gap = approx ₹14.16 L**, and it is **flagged OPEN for reconciliation** — not
  closed, not explained.
- **Possible reasons for the gap:** a different MIS extract, a PO-type filter, a
  sale-type filter, a different date cut, or an exclusion logic not present in
  File 2 (see the investigation and hypotheses below).
- **Final closure needs the source/definition of the ₹236 L figure** — see
  "What's needed to close this."

> ## ⛔ MERGE GATE
> **Do not merge PR #2 until either:**
> 1. the ₹236 L reference's source/definition is confirmed and diffed against
>    File 2, **or**
> 2. business explicitly accepts **₹250.17 L (File 2)** as the source of truth
>    for Primary SIS FY26.
>
> This status is also encoded in `dashboard/data.js` → `detail_meta.sis_gap_status`
> and surfaced as a red "DO NOT MERGE" banner on the dashboard's SIS
> Reconciliation Drill-down card (Data Explorer tab) — see below.

## SIS Reconciliation Drill-down (dashboard, exportable)
The **Data Explorer → SIS Reconciliation Drill-down** card gives the full,
row-count-uncapped breakdown for audit, with a CSV export:

1. **Total SIS Sales** — ₹275.44 L (gross, `MTD-Sale type = "Sales"`)
2. **MRN / Returns** — −₹25.27 L (`MTD-Sale type = "MRN"`)
3. **Cancelled Invoices** — ₹0.00 L (`MTD-Sale type = "Cancel Invoice"`, near-zero)
4. **Net SIS Value** — ₹250.17 L (1 + 2 + 3; matches `Primary SIS` exactly)
5. **Chain-wise SIS value** — Shoppers Stop ₹121.19 L, Azorte ₹68.09 L, Lifestyle
   ₹32.79 L, Broadway ₹24.69 L, Today's Basket ₹2.24 L, Lifestyle Babyshop ₹1.17 L
6. **Month-wise SIS value** — May'25 through Mar'26 (all 11 months present)
7. **Brand-wise SIS value** — The Derma Co ₹125.36 L, Mamaearth ₹61.65 L,
   Aqualogica ₹44.01 L, BBlunt ₹10.05 L, Staze ₹7.69 L, Dr. Sheth's ₹1.40 L
8. **Exclusions / inclusions applied** — computed from all 13,277 SIS rows in the
   full source (not the 20,000-row display cap); MRN and cancelled invoices
   included, not excluded; 153 exact-duplicate invoice lines detected and
   **not** deduplicated (impact ₹0.48 L, checked, negligible); no rows or chains
   excluded.

**Export SIS reconciliation (CSV)** button on that card downloads
`sis_reconciliation_fy26.csv` with all 8 sections for offline audit against
whatever produced the ₹236 L figure. Computed in
`scripts/build_dashboard_data.py` (`_sis_reconciliation()`), stored in
`detail_meta.sis_reconciliation`.

## What the real primary source (File 2) shows
Loaded `primary_article.xlsb` (289,144 invoice lines, FY25-26 + FY26-27) and
summed `Inv. Net value(LOC)` by its own `Channel` field, **before any row
capping** (so this is exact, not affected by the dashboard's row cap):

| FY | MT | EB2B | SIS |
|---|---|---|---|
| FY26 (Apr'25–Mar'26) | ₹30,684.99 L | ₹1,965.20 L | **₹250.17 L** |
| FY27 (Apr'26 onward, partial) | ₹9,032.06 L | ₹452.68 L | ₹7.86 L |

SIS FY26 = **₹250.17 L**, not ₹236 L. This is computed straight from File 2's own
`Channel` column — no derivation, no join, no offtake data involved.

## Investigation performed on the ₹14.16 L gap
None of the checks below land exactly on ₹236 L, so each is a ruled-out or
partial cause, not a confirmed fix:

| Check | Result |
|---|---|
| Positive vs negative (return) lines | Sales +₹280.41 L, negative lines −₹30.24 L → net ₹250.17 L |
| By `MTD-Sale type` | `Sales` ₹275.44 L, `MRN` (returns) −₹25.27 L, `Cancel Invoice` ≈ ₹0.00 L → excluding cancelled invoices changes nothing (net still ₹250.17 L) |
| Exact-duplicate invoice lines (same Inv No. + Article + Qty + NSV) | 153 rows, ≈ ₹0.48 L impact — negligible, not the driver |
| By sub-chain (`Dist chain ten`) | Shoppers Stop ₹121.19 L, Azorte ₹68.09 L, Lifestyle ₹32.79 L, Broadway ₹24.69 L, Today's Basket ₹2.24 L, Lifestyle Babyshop ₹1.17 L — sums to ₹250.17 L, no single outlier chain explains ₹14.16 L cleanly |

None of these reproduce ₹236 L exactly, so the gap is **not** explained by
returns, cancellations, duplicate lines, or a single mis-tagged sub-chain alone.

## Candidate hypotheses (unverified — need more info to test)
1. **₹236 L comes from a different source/definition** — e.g. a certified/
   finalized MIS extract, a GST-filing figure, or a report with its own filters
   (specific PO types, excluding certain sub-chains, a different date cut-off).
   *This is the most likely explanation given nothing in File 2 alone reproduces
   ₹236 L.*
2. **Some SIS-tagged rows are mis-coded** at source (should be MT/EB2B) — e.g.
   `Azorte` (₹68.09 L) is a Reliance-owned beauty retail format that could
   arguably be EB2B depending on the business's channel definition.
3. **A different FY/date boundary** — "last year" may mean a specific 12-month
   window that doesn't align exactly with the Apr'25–Mar'26 split used here.

## What's needed to close this
To pinpoint the exact ₹14.16 L driver, please share:
- **The source of the ₹236 L reference** (which report/MIS pack, and its filter
  logic — e.g. does it exclude specific sale types, chains, or PO types?), or
- **A row-level extract** of what that ₹236 L figure includes, so it can be
  diffed directly against File 2's 13,277 SIS FY26 rows.

## Model artifacts (unchanged, still useful once the true definition is known)
- `SeedData/Masters/ChannelMap_Store.csv` / `ChannelMap_Chain.csv` +
  `PowerQuery/24_ChannelMap.pq` — resolve Channel on the offtake side (Store
  override → Chain default → "Unmapped", never dropped). Still valid for
  tagging offtake by channel; just not the explanation for this particular gap.
- `DAX/10_SIS_Reconciliation.dax` — `Primary SIS`, `Offtake SIS`, `SIS Variance`,
  `Offtake Channel Coverage %`. Once the ₹236 L definition is confirmed, add a
  filter/measure here (e.g. by `MTD-Sale type`, or an excluded sub-chain list)
  to reproduce it exactly, and the variance measure will then mean something.
- Dashboard: `dashboard/index.html` Explorer → **SIS — Channel check (Primary)**
  card shows the exact File 2 channel total (`detail_meta.channel_totals`,
  computed pre-cap) and states the gap is open, not fixed.
