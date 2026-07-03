# SIS Reconciliation — "Primary SIS 250 vs 236" (investigation, still OPEN)

> **Correction to an earlier version of this doc:** an earlier pass claimed the
> ₹250 L reading was caused by the offtake side deriving SIS with no Channel
> column, and that ₹236 L (from an older, differently-scoped dashboard build)
> was the correct figure. **That theory is ruled out below** — once the real
> File 2 (`primary_article.xlsb`, the article-wise primary billing with its own
> explicit `Channel` field) was actually loaded, it independently nets to
> **₹250.17 L for SIS FY26**, not ₹236 L. Since File 2's own Channel field is the
> intended source of truth for Primary SIS, the ₹14.16 L gap is **not** an
> offtake-derivation artifact. Root cause is still **unresolved** — see
> "What's needed to close this" below.

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
