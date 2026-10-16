# Metric gap register

Source strength: DEFINITION (standard, widely agreed), PRACTICE (common industry practice), OPINION (one
vendor or blog), OURS (our own recommendation, not sourced). Research run 2026-10-16. Most public sources
were vendor blogs; GS1, ASCM/APICS, Nielsen/Circana method papers, and DMart or Reliance vendor manuals
were NOT FOUND, and no Indian-chain penalty schedule was found. Re-check before quoting to leadership.

| ID | Card says | Why blank | Needs |
|---|---|---|---|
| G-01 | Stock / inventory days | No stock-on-hand feed | Closing stock by chain DC or store x SKU x snapshot date |
| G-02 | OSA / OOS / perfect store / store audit | No governed audit source (compliance file is synthetic) | Store-audit extract |
| G-03 | Fill rate / CFR / OTIF / lost revenue | No delivery or fill source | PO-line file with delivery dates and quantities |
| G-04 | Open PO SLA risk | No open-PO ageing source | Open PO list plus approved breach rule and penalty rate |
| G-05 | Promo ROI | Promo calendar not aligned to the sell-out months; no unit margin | Promo mechanics per month, funding split, unit margin |
| G-06 | NPD / NPI launches | Launch master not joined to transaction grain | Launch master by EAN |
| G-07 | Primary vs Offtake for a new month | File not supplied yet | Monthly MTD-Primary workbook and Offtake file (see playbook) |

## G-01 Stock cover / days of inventory
- Formula (PRACTICE): cover days = stock on hand (units) / average daily sell-out (units); weeks = days / 7.
  Value version = average inventory / (COGS / days). Same unit on both sides.
  https://timly.com/en/stock-management/calculate-inventory-days-on-hand/ ,
  https://racklify.com/encyclopedia/what-is-days-of-supply-formula-example-and-how-to-calculate-it/
- Backward cover uses past sales, forward cover uses forecast; short windows react fast, long windows smooth
  seasonality (OPINION): https://metricgate.com/calculator/days-of-supply-coverage
- Sales basis (OURS): use Offtake as the denominator for chain DC or store cover. Primary is billing, not
  consumer demand. Distributor Secondary only for distributor-held stock.
- Inputs: snapshot date, chain, DC or store ID, SKU/EAN, closing stock units (and value), sell-out window, lead time.
- Owner: chain replenishment team; distributor DMS for distributor stock.
- Benchmarks: NOT FOUND. Target cover is lead time plus buffer, set by the business.
- Pitfalls: cases vs pieces; stock snapshot date different from the sales window; promo weeks skewing the
  daily average; in-transit counted as on hand.

## G-02 OSA / OOS / perfect store
- OOS (DEFINITION, via a paper quoting ECR Europe 2003): a demanded product not available in the expected
  location or not saleable. https://dspace5old.zcu.cz/bitstream/11025/31105/1/EM_4_2018_13.pdf
- Corsten and Gruen worldwide study: average OOS 7.9% (US), 8.6% (Europe).
  https://www.emeraldinsight.com/doi/abs/10.1108/09590550310507731
- OOS rate = SKU-outlet checks with a listed SKU missing / total SKU-outlet checks; OSA = 1 - OOS
  (PRACTICE, vendor): https://wiser.com/?p=4787
- Perfect store (OPINION): compliance rate = outlets meeting all criteria / outlets audited; weighted score =
  weighted parameter scores / maximum score. https://content.bemyeye.com/blog/perfect-store-definition/
- Inputs: audit date, auditor ID, chain, door code, SKU/EAN, listed Y/N, present Y/N, shelf price vs MRP,
  facings, planogram OK, FSDU/POSM present, POSM type, photo ID, KPI weights.
- Owner: field force or third-party audit agency (audit app).
- Pitfalls: audits are a sample, not a census; weights differ by company; denominator (listed SKUs vs all).
  Standard sample size and POSM audit definition: NOT FOUND.

## G-03 Fill rate / CFR / OTIF / lost revenue
- OTIF (PRACTICE): cases received in the delivery window / cases ordered; a PO is "in full" only at 100%.
  Retailers differ on scoring at PO, line or case level. https://www.doss.com/glossary/on-time-in-full-otif
- Case fill rate = delivered cases / ordered cases (PRACTICE; no GS1 or ECR definition found).
- Lost revenue (OURS): (ordered - delivered qty) x invoice or list price per unit.
- Penalties (PRACTICE, US only): about 3% of cost of goods commonly cited for Walmart, 5% for Target;
  thresholds conflict across sources. https://spscommerce.com/blog/supply-chain-errors-discrepancies .
  India (DMart, Reliance) penalty schedules: NOT FOUND. Take them from each chain's contract.
- Inputs: PO number, line, SKU, chain, ship-to/DC, PO date, requested delivery date, delivery window,
  dispatch/ASN date, delivered (GRN) date, ordered qty, shipped qty, delivered qty, rejection reason, PO value.
- Owner: key account / customer service; chain portals and EDI/ASN; SAP delivery documents (assumption).
- Pitfalls: scoring level differs by chain; grace rules differ; GRN date vs dispatch date; partial deliveries.

## G-04 Open PO ageing / SLA risk
- Open PO = not fully received or invoiced; pending qty = ordered - received (or invoiced, per rule)
  (PRACTICE): https://help.servicegeeni.com/en/articles/12838544-report-open-outstanding-purchase-orders
- Buckets have no standard (Oracle example 0-3, 4-7, 8-14, 15-21, 22-30, 31-45, 46+ days):
  https://docs.oracle.com/cd/E68434_01/oroms/pdf/1512/cws_help/adf1016552.htm . The business sets its own.
- Business must approve (no public source): age basis (PO date, requested delivery date or milestone),
  bucket edges, SLA days per chain, breach rule, penalty rate and base. PO validity per chain contract: NOT FOUND.
- Inputs: all G-03 PO fields plus PO status, validity end date, cancellation date, pending qty and value.
- Pitfalls: cancelled or short-closed POs left open; draft POs included; partial receipts hiding a balance.

## G-05 Promo ROI
- Formulas (PRACTICE): incremental volume = promo-period actual - baseline - post-promo dip;
  ROI = (incremental gross profit - promo cost) / promo cost. https://www.talon.one/blog/measure-promotion-roi
- Baseline methods: pre/post average, matched control stores, regression with promo and lag terms
  (third-party description, unverified): https://metricgate.com/docs/nielsen-trade-promotion-uplift/
- Pitfalls (OPINION): pull-forward and post-promo dip (track 6-8 weeks after), cannibalisation, overlapping
  promos. Quoted shares such as "40-60% time-shifted" are unaudited vendor claims; do not repeat them as fact.
- Inputs: promo ID, chain, SKU/EAN, store scope, start and end dates, mechanic, depth, shelf price vs MRP,
  funding split (brand %, chain %, claim basis), planned and actual cost, unit margin, baseline window.
- Do not add provision, claim and settlement for the same event (FM-14). Do not mix Offtake and Primary.

## G-06 NPD / NPI
- Numeric distribution = share of outlets stocking the product; weighted distribution = share of category
  sales through stocking outlets (DEFINITION): https://nielseniq.com/global/en/insights/analysis/2023/optimizing-product-distribution-start-here/
- A 12-month window is supported by Circana's Pacesetters (about 13 quad-weeks, US programme):
  https://www.circana.com/post/new-product-pacesetters-2025
- Separating true-new from line extension, and distribution gain from rate of sale: NOT FOUND.
- OURS: cohort by first sale per Chain x EAN (already in the dashboard) plus a launch master by EAN with a
  true-new / extension / relaunch flag; split growth into stores-selling change and sales-per-store change.
- Inputs: EAN, planned and actual launch date, pack and price, chain listing dates, true-new flag.
- Owner: brand/innovation team; chain category team.
- Pitfalls: stocked doors counted as selling doors; universe changes distorting ND; re-coded EANs look new.

## G-07 Primary vs Offtake
- Primary = billing into the trade; Offtake = POS to shopper; the gap is timing, pipeline and returns
  (OPINION, vendor): https://www.terra-insight.com/insights/secondary-sales-gap-stock-in-trade-fmcg/
- OURS: compare same month, chain, unit; use a rolling or cumulative view; show the gap as implied stock
  movement; never blend into one growth rate; non-MT channels excluded from Primary on the MT basis.
