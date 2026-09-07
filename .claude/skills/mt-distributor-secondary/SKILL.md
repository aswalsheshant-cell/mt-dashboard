---
name: mt-distributor-secondary
description: Use whenever distributor secondary sell-out is involved — distributor billing, Ship-To to chain allocation, Cont% weights, distributor-to-chain-to-customer-to-article deep dives, TOT hierarchy, or CM2 built on secondary NSV. Also use whenever a number must be classified as Primary, Secondary or Offtake, when a file is labelled "primary" but may be secondary, or when a two-measure comparison (primary vs offtake, FY-on-FY) needs its basis checked. Handles the third pillar of the MT data model. Excludes pure offtake or primary questions with no secondary component and hands off to `modern-trade-sales-growth`; excludes release verdicts and hands off to `sales-data-reconciliation`.
---

# Distributor Secondary — the third pillar

Modern Trade has **three** measurement pillars, not two. Every MT number belongs to
exactly one of them, and the single most expensive mistake in this repo is treating a
number from one pillar as if it came from another.

```
Honasa ──PRIMARY──▶ chain DC / distributor ──SECONDARY──▶ retailer store ──OFFTAKE──▶ consumer
        (billing)                            (sell-out to trade)          (sell-out to shopper)
```

| | **Primary** | **Distributor Secondary** | **Offtake** |
|---|---|---|---|
| What it measures | Honasa invoices out | Distributor invoices on to the chain | Consumer purchases at till |
| Owner system | SAP / ERP billing | Distributor DMS returns | Chain POS extracts |
| Repo home | `Primary_Article_Monthly/`, `Primary_ShipTo_Monthly/` | `SecondarySales_Monthly/`, `data/raw_drops/Distributor_secondary_*` | `Offtake_Monthly/` |
| `data.js` block | `primary` | `offtake.secondary_*` and `*_fy25` keys | `offtake` |
| FY26 scale | ₹32,900.36 L | — | ₹31,119.88 L |
| Direction of error | over-states if channel is loaded | sits between the other two | under-states if a feed drops |

**Secondary is not a fallback for primary.** It is its own measure, one step down the
trade chain. It answers questions primary cannot: what the distributor actually pushed
into each chain, and therefore what trade spend and CM2 attach to.

---

## Rule 1 — Never compare across pillars without saying so

A ratio between two pillars measures the **gap between the measures** at least as much
as it measures business movement. Channel inventory, trade margin, returns and claim
timing all sit in that gap.

| Comparison | Verdict | What it actually tells you |
|---|---|---|
| Primary vs Offtake, same period | **Valid** | Channel loading / sell-through. The standard check. |
| Secondary vs Offtake, same period | **Valid** | Distributor-served sell-through |
| Primary vs Secondary, same period | **Valid, with care** | Distributor stock build |
| **Secondary (year A) vs Primary (year B)** | **NEVER** | Nothing. Do not compute a growth %. |

That last row is the FY25-vs-FY26 trap: FY25 has only secondary, FY26 has primary. Put
them in **separate labelled columns** and state on the artifact that no growth rate is
available. This is a real constraint, not a formatting preference.

---

## Rule 2 — The trap-file register

These files are named or columned as **primary** and are not. All four are the same
FY25 distributor secondary data. Verified by row-level join: 7,050 of 7,150 keys match
within ₹0.05 L; totals differ by 0.03%.

| File | Why it deceives | Truth |
|---|---|---|
| `PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY24-25.csv` | Column literally named **`Primary NSV`**; `FY Year = FY_24-25` | Secondary, rounded to 1dp, ×1e5. ₹23,325.30 L |
| `PowerBI/SeedData/Mapping/DistPrimary_Sheet1_FY24-25.csv` | Filename says "DistPrimary" | The Excel working sheet behind the above |
| `PowerBI/RawDataFolders/Primary_Derived_FY25/Primary_Article_Synthesized_FY25.csv` | Article-level, looks like a real extract | 54,328 of 67,545 rows are `Brand_Pareto_Assortment_Fallback` |
| `PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv` | Filename reads as FY25 | `FY Year` is **only** `FY_25-26` / `FY_26-27`. Zero FY_24-25 rows. Also runs to Jul'26, not May'26 |

**There is no true FY25 primary billing anywhere in this repo.** Before quoting any
FY25 "primary" number, check the file's `FY Year` values and its provenance. If asked
to *derive* FY25 primary, say plainly that it cannot be derived — only requested. See
"Requesting real FY25 primary" below.

**Classification test — apply to any unfamiliar file:**
1. What system emitted it? Billing → primary. DMS → secondary. POS → offtake.
2. Does it have `Direct/Distributor`, `Ship To`, `Cont%` or `Dist chain ten`? → secondary or distributor-allocated primary.
3. Does it have `Site Code`, `Store Type`, `Sales Qty`? → offtake.
4. Does the total tie to a known pillar baseline? FY26 primary ₹32,900.36 L, FY26 offtake ₹31,119.88 L, FY25 secondary ₹23,332.36 L.
5. A column *named* `Primary NSV` proves nothing. Rule 4 of this list beats the header.

---

## Rule 3 — Secondary grain changes by era. Know which you have.

This asymmetry decides whether an article-level question is answerable at all.

| Era | File | Deepest grain | Article/EAN? |
|---|---|---|---|
| **FY25** (Apr'24–Mar'25) | `data/raw_drops/Distributor_secondary_FY25_Apr24_Mar25.csv` | Ship-to × Chain × **Brand** × State × Month | **No** |
| **FY27** (Apr'26→) | `SecondarySales_Monthly_TOT_Analysis/01_FULL_HIERARCHY_*.csv` | Distributor × Chain × Brand × **EAN × Article** | **Yes** |

FY25 columns: `Format, Ship to customer, Direct/Distributor, Chain Name, State, Zone,
NSV, MRP value, Brand, Revised month, Month, FY, Channel, Chain Mapping`.

FY25 stops at brand. That is precisely why `Primary_Article_Synthesized_FY25.csv` had
to invent article splits with a Pareto fallback. **Any FY25 article-level or
category-level CM2 is modelled, not measured** — label it so, or refuse it.

---

## Rule 4 — The distributor → chain → customer → article deep dive

For CM2 and trade-spend work, the hierarchy file is the one to use:

`PowerBI/RawDataFolders/SecondarySales_Monthly_TOT_Analysis/01_FULL_HIERARCHY_Apr_Jul_2026.csv`
28,537 rows · 34 distributors · 76 chains · 23 brands · 799 EANs · **₹4,281.34 L (₹42.81 Cr)**
(`secondary_sales_tot_hierarchy_Apr_Aug_2026.csv` extends this to Aug'26, 41,671 rows.)

| Column | Level | Use |
|---|---|---|
| `Source_Month` | period | FY tag via the Apr–Mar rule |
| `Distributor` | **billing party** | Who Honasa billed. Claim and TOT settle here |
| `Dist_Monthly_Total` | distributor total | **In rupees**, not lakh |
| `Chain` | **customer** | Which chain the distributor served |
| `Chain_Monthly_Total` | chain total | **In rupees** |
| `Chain_TOT_Pct` | chain share | **Do not use — see below** |
| `Brand`, `Brand_Monthly_Total` | brand | Total in rupees |
| `Brand_TOT_Pct` | brand share | **Do not use — see below** |
| `EAN`, `Article` | **article** | The CM2 denominator at SKU level |
| `NSV_Value` | measure | **Rupees.** This is the one to sum |
| `NSV_Lakh` | measure | Rupees / 1e5, **rounded to 2dp** |

**Standard drill path:** Distributor → Chain → Brand → EAN.

Three defects in this file, all verified — handle every one of them:

1. **Never sum `NSV_Lakh`.** It is rounded to 2 decimals, and most rows are small, so
   the rounding compounds. Summing it gives ₹4,273.75 L against a true ₹4,281.34 L —
   **₹7.59 L lost**. Always `sum(NSV_Value) / 1e5`.
2. **Never trust `Chain_TOT_Pct` or `Brand_TOT_Pct`.** They do not reconcile to the
   totals sitting in their own rows: **93%** of rows disagree with
   `Chain_Monthly_Total / Dist_Monthly_Total`, and **95%** disagree with
   `Brand_Monthly_Total / Chain_Monthly_Total`. Per distributor-month the chain
   percentages sum to anywhere between −0.17% and 158.87%, not 100%. **Recompute every
   share from the totals.**
3. **Units are mixed inside one row.** `Dist_Monthly_Total`, `Chain_Monthly_Total`,
   `Brand_Monthly_Total` and `NSV_Value` are rupees; `NSV_Lakh` is lakh. Convert before
   any comparison, or the answer is out by 1e5.

Verify at each level that the children sum to the parent (using recomputed shares)
before attributing anything. A level that does not sum means the level below is
incomplete, and CM2 built on it is understated.

Companion cuts: `02_DISTRIBUTOR_CHAIN_TOT_*.csv` (235 rows, distributor × chain only)
and the by-distributor / by-chain / by-brand files in `SecondarySales_Monthly/`.

---

## Rule 5 — CM2 on secondary

The repo's definition, enforced in `scripts/validate_dashboard_qc.py:158`:

```
CM2 Value = NSV − Expense
CM2 %     = CM2 Value / NSV × 100
```

Tolerances the QC applies: CM2 value ±₹0.01 L, CM2 % ±0.1 pp.

Rules that keep a CM2 number defensible:

1. **Name the NSV basis on every CM2 figure.** Secondary NSV and primary NSV give
   different CM2 on the same expense. "CM2 47%" without a basis is unusable.
2. **Match the grain of expense to the grain of NSV.** A distributor-level claim
   spread to EAN by `Brand_TOT_Pct` is allocated, not actual — say so.
3. **Never carry expense across pillars.** A claim settled against distributor billing
   belongs on secondary NSV, not on offtake.
4. **Guard the denominator.** `NSV = 0` → CM2 % is undefined, not 0 and not 100.
   Negative NSV (net-credit months) makes CM2 % meaningless — show the value, suppress
   the percentage. FY25 has real cases: B&N −₹3.80 L, Mother Care −₹0.06 L.
5. **Release gate G9** covers CM2 expense matching; **G10** carries
   `jun26_allocation_status` and `negative_frac_treatment_status`. Read them before
   publishing; a `BLOCKED` on either stops the release.

---

## Rule 6 — Cont% allocation (how distributor NSV becomes chain NSV)

Distributor rows carry a distributor name, not a chain. Attributing them to chains uses
secondary-derived **Cont%** weights at Ship-To × Brand × Month × Chain grain
(`scripts/build_dashboard_data.py:342` onward; logic documented in
`PowerBI/docs/DistributorPrimaryAllocation_Logic.md`).

Consequences to respect:

- **A naive `groupby('Chain name')` on `primary_article_*.csv` is wrong.** For `Dist.`
  rows that column holds the *distributor* ("Kiran Trading Company", "Az Enterprises"),
  so roughly **₹8,700 L** gets stranded away from the chains it belongs to — it makes
  Lulu and More Retail look absent and cuts Health & Glow to a fraction of its real
  value. Use the post-allocation `primary.by_chain` in `data.js`, or apply the weights.
- The field that makes allocation possible is **`Dist chain ten`** (which chains each
  Ship-To serves). Without it, distributor rows cannot be split at all.
- Where a month has no approved Cont% sheet, allocation falls back to the nearest month.
  Jun'26 does this from May'26 — disclosed in `PowerBI/docs/Jun26_Provisional_Allocation.md`,
  Finance-approved 2026-08-09. A fallback month must be labelled **PROVISIONAL**.

---

## Rule 7 — Zone integrity on secondary

Two defects confirmed in the FY25 secondary file. Check both before any zone cut.

1. **Central looks absent but is mis-filed.** The FY25 source `Zone` column has no
   Central at all: Madhya Pradesh is tagged **North**, Chhattisgarh **West/East**.
   `ZoneStateMaster.csv` puts Madhya Pradesh, Chhattisgarh and Maharashtra-Vidarbha in
   Central. Re-derived, Central is **₹1,052.77 L, 4.51% of FY25**. Reporting
   "Central = 0" is wrong.
   **Watch the spelling:** the FY25 file writes Chhattisgarh as **"Chattishgarh"**. A
   state match on the correct spelling silently drops it and leaves Central at
   ₹756.15 L — a ₹296 L hole with no error raised. Match state names
   case-insensitively against a spelling-variant list, never on exact equality.
2. **South-1 and South-2 are swapped** versus `ZoneStateMaster.csv`. The source puts
   Karnataka/Kerala/Tamil Nadu in South-1 and Telangana/AP in South-2; the master is the
   reverse. About ₹376 L moves. **Pick one master, state which, and stay on it.**

Always re-derive zone from `State` via `canon_zone_from_state()`. Never trust a `Zone`
column. Note also that `canon_zone()` emits `South 1` (space) while `ZoneStateMaster.csv`
and `offtake_fy26.json` use `South-1` (hyphen) — normalise before joining.

---

## Rule 8 — Before publishing any secondary number

- [ ] Pillar named on the artifact: Primary / **Secondary** / Offtake
- [ ] Unit stated (₹ Lakh vs ₹ Cr; source NSV is already Lakh in most secondary files)
- [ ] FY derived from month via Apr–Mar, never a column position
- [ ] Chain names through `canon_chain()`; zones re-derived from State
- [ ] Total ties to source (FY25 secondary = **₹23,332.36 L**)
- [ ] Channel split declared — FY25 is ₹21,723.43 L MT + ₹1,608.93 L EB2B. MT-only work
      must filter `Channel`, or the number is 7% high
- [ ] No cross-pillar growth % anywhere on the artifact
- [ ] Allocated figures marked as allocated; provisional months marked PROVISIONAL

---

## Requesting real FY25 primary

When someone asks for FY25 primary, this is the ask to send — an SAP/ERP invoice-level
billing extract for Apr'24–Mar'25, dropped as `primary_article_Apr_24.csv` …
`primary_article_Mar_25.csv` into `PowerBI/RawDataFolders/Primary_Article_Monthly/`:

`Month` · `Ship To Name` · `Cust-SAP Code` · `Direct/Distributor` · `Chain name` ·
**`Dist chain ten`** · `Zone` · `State` · `brand` · `Article Code` · `EAN No.` ·
`Inv. Net value(LOC)` · `MRP Rate` · `Total MRP sales` · `Inv Qty` ·
**`MTD-Sale type`** (Sales vs MRN, so returns net correctly) · `Channel`

`Dist chain ten` and `MTD-Sale type` are the two that get forgotten and the two that
make the extract unusable if missing.

---

## Handoffs

- Number is validated, question turns commercial → `modern-trade-sales-growth`
- Reconciliation verdict, PASS/FAIL, release gate → `sales-data-reconciliation`
- Building the script, DAX or query → `business-ai-automation` / `mt-python-pipeline`
- Margin, trade spend ROI, P&L beyond CM2 → `mt-financial-intelligence`
- Leadership wording for the finding → `executive-commercial-storytelling`
