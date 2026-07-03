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

## Traced: where ₹236 L came from (evidence, not speculation)
`git log --all -S "236.01" -- dashboard/data.js` shows the ₹236.01 L figure was
first introduced in commit `bbeaeab` ("Add interactive MT leadership
dashboard"), the very first HTML-dashboard build, from a **different, earlier
session (PR #1)**. That build's `load_primary()` reads:
```python
df = pd.read_excel(src / "primary.xlsx", sheet_name="Sheet1", header=1)
```
i.e. a file named **`primary.xlsx`** ("Primary FY-2024-26.xlsx" per that
script's source-file comment) — **not** `primary_article.xlsb` (File 2, used
for this investigation). Both files have a similar shape (row-level primary
with `Chain Name`, `Brand`, `Zone`, `Channel`, `FY`, `NSV`), but they are **two
different extracts**, most likely pulled at different times or with different
scope/filters, both self-describing as "primary" data.

**Update — `primary.xlsx`-equivalent file since supplied and checked:**
`Primary_FY202426_10.xlsx` was provided and matches this file's shape exactly
(`Dump` sheet: `Format, Chain Mapping, Bill to customer, Direct/Distributor,
Chain Name, State, Zone, NSV, MRP value, Brand, Revised month, Month, FY,
Channel, Chain Name for TGT, KAM` — 18,128 rows). Computed SIS FY26 directly
from it:

| Source (within this one file) | SIS FY26 |
|---|---|
| `Dump` sheet (raw rows, filtered `FY='FY_25-26'`, `Channel='SIS'`) | **₹250.17 L** |
| `PVT` sheet, `SIS Total` row (Excel-native PivotTable, independently built) | **₹250.17 L** (month-by-month matches File 2 exactly: May 13.23, Jun 15.45, Jul 35.44, Aug 21.90, Sep 34.33, Oct 16.66 L, …) |

**This is now THREE independent computations — File 2 (invoice-line grain),
this file's raw `Dump` sheet, and this file's own Excel PivotTable — all
agreeing exactly on ₹250.17 L.** None reproduce ₹236.01 L.

**Dated evidence for staleness:** this file's metadata (`docProps/core.xml`)
shows `created: 2026-03-12`, **`modified: 2026-06-29`**. The original dashboard
build that produced ₹236.01 L is commit `bbeaeab`, dated **2026-06-27** — i.e.
**two days before** this file was last modified. The most likely explanation:
the ₹236.01 L figure was computed from an **earlier, staler pull** of this same
underlying primary data (fewer captured invoices/rows as of ~June 27), and the
dataset has since been updated/appended (new invoices, corrections) between
June 27 and June 29, growing the true SIS FY26 total to ₹250.17 L. This is a
strong hypothesis based on real dated evidence, not a proven fact — the exact
state of the data as of June 27 was not preserved/version-controlled, so a
byte-for-byte "before" snapshot is not available to prove it conclusively.

## Other candidate hypotheses (secondary, weaker given the above)
1. **A filter within `primary.xlsx` itself** — if that file's `Channel` field
   was populated by a different rule than File 2's, or the extract had its own
   date cut-off / PO-type / sale-type filter applied upstream before export.
2. **Some SIS-tagged rows are mis-coded** at source (should be MT/EB2B) — e.g.
   `Azorte` (₹68.09 L) is a Reliance-owned beauty retail format that could
   arguably be EB2B depending on the business's channel definition.
3. **A different FY/date boundary** — "last year" may mean a specific 12-month
   window that doesn't align exactly with the Apr'25–Mar'26 split used here.

## What's needed to close this (updated)
`Primary_FY202426_10.xlsx` was supplied and checked (see above) — it does
**not** reproduce ₹236.01 L; it independently confirms ₹250.17 L three ways.
So the row-level diff against a "different file" lead is now exhausted without
finding the ₹236.01 L origin. To close the gap, one of the following is needed:
- **The exact snapshot/export used for the original ₹236.01 L figure** — if it
  was pulled before 2026-06-27 and archived anywhere (email attachment, an
  earlier saved copy of this workbook, a report generated on/before that date),
  sharing that would let it be diffed directly, **or**
- **Confirmation of the staleness hypothesis** — if business can confirm the
  primary dataset was updated with new SIS invoices/corrections between
  2026-06-27 and 2026-06-29 (matching this file's `modified` timestamp), that
  would explain the ₹14.16 L gap as a data-freshness difference, not a
  definitional one, **or**
- **Business sign-off** that ₹250.17 L (now confirmed by three independent
  computations) is the source of truth going forward, superseding the earlier
  ₹236.01 L figure.

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
