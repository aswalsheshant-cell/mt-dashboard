# Jun'26 Distributor Allocation — Provisional Status

**Status:** PROVISIONAL — Finance approval pending  
**Last updated:** 2026-08-06  
**Populated by:** Query 41 v2.0 (nearest-month fallback from May'26)

---

## The Gap

The ShipTo CSV (`Primary_ShipTo_FY25-26_to_May26.csv`) covers **May'25 – May'26**.
The `DistCont_Patch_Approved_2026-07-04.csv` covers specific backfill months (Oct'25, Nov'25).
**Jun'26 has no approved secondary-derived contribution sheet.**

## Jun'26 Distributor Row Counts

| Metric | Value |
|--------|-------|
| Total Jun'26 primary article rows | 23,192 |
| Jun'26 Dist. rows (PO Type = Dist.) | **1,909** |
| Jun'26 Direct rows | 21,283 |
| Jun'26 Dist NSV (₹ Lakhs) | **~1,377 L** |
| Distinct distributors (ship-to names) | **21** |

## Fallback Coverage

All 21 Jun'26 distributors have exact-key matches in May'26 data.
**Fallback coverage: 100% of Jun'26 Dist rows.**

The 21 distributors are:

| Ship To Name |
|---|
| Az Enterprises |
| BALAJI ASSOCIATES Distributor MT |
| Chhabra Traders |
| CHHABRA TRADERS_Ship To |
| CHOUDHARY ENTERPRISES-MT-MP |
| D.L. Sales - MT |
| G.V Enterprises |
| JUST MARK-Dmart_ship to |
| Kiran Trading Co_Shipto (Solapur) |
| Kiran Trading Company_Ship to |
| M/S KOTTARAM BUSINESS CORPORATION-MT |
| MANOJ SOAP AGENCY-MT |
| MARK ENTERPRISE |
| PRAGATI SALES-D-MART |
| REAL TIME LOGISTICS_MT_BR |
| RR Traders-MT |
| Sancus Networks Private Limited-RMT |
| Sehaj Enterprises -MT-JK |
| Sri Vijaya Durga Agencies_Mt |
| United Marketing_Mt-Ship to |
| VENKATESHWARA AGENCIES-TG |

## Fallback Method

The nearest-month fallback is the **approved business methodology** (mirrors
`allocate_dist_primary()` in `scripts/build_dashboard_data.py`). It copies
May'26 chain-split fractions verbatim to Jun'26 for each distributor.

**Assumption:** chain mix did not materially change from May'26 to Jun'26.

## What to Do

1. Finance team: produce the Jun'26 secondary-derived contribution sheet
2. Analyst: run `scripts/build_dashboard_data.py --detail-only` to generate
   a `DistCont_Patch_Proposed.csv` proposal using the new Jun'26 article data
3. Finance: review the proposal, approve, and save as
   `PowerBI/SeedData/Mapping/DistCont_Patch_Approved_<YYYY-MM-DD>.csv`
4. Update Query 41 to reference the new approved patch file
5. Refresh the Power BI report

Until step 4–5 are complete, Jun'26 allocation rows carry:
- `Allocation Status` = **"Provisional"**
- `Provisional Flag` = **TRUE**
- `Source Type` = **"Nearest-Month Fallback"**
- `Approval Status` = **"Provisional – Jun'26 gap; awaiting Finance approval"**

These columns are surfaced on the Data Quality page.

## Reconciliation Note

An earlier run of the reconciliation script reported 4,810 Jun Dist rows and
~2,271 L. That figure included **Jun'25** rows (2,901 Dist rows) in addition
to Jun'26 (1,909 rows). The Jun'26-specific figures above are confirmed.
