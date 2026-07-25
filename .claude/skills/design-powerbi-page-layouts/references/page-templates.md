# Repository Page Templates — Honasa / Mamaearth MT Analytics

One entry per dashboard page. Values shown are structural guidance only.
Do not copy real numerical data, targets, or credentials into specifications.

---

## executive-overview

**Audience**: Senior leadership, NSM, CMO, Finance head.
**Business question**: How is the MT channel performing this period against target and last year?

**Recommended KPIs (top strip)**:
- Primary RSP (₹ Cr) — YTD
- Offtake RSP (₹ Cr) — YTD
- Primary vs LY %
- Offtake vs LY %
- CM2 % (governed measure — Finance-approved)

**Visual hierarchy**:
1. KPI strip (top) — 5 KPI cards at y ≈ 20
2. Trend chart — Primary + Offtake monthly trend (combo or line) full-width below KPIs
3. Brand/Chain breakdown — bar chart or matrix (lower section)
4. Filter rail — FY, Brand, Chain, Zone slicers

**Required filters**: FY, Brand, Chain, Zone
**Expected source fields**: NSV, MRP, RSP, CM2 %, LY values, targets
**Missing-data behaviour**: show "—" for any KPI lacking a confirmed measure; do not extrapolate
**Validation checks**: CM2 % must come from `PowerBI/DAX/13_CM2_Measures.dax`; warn if not
**Mobile-layout guidance**: stack KPIs 2 per row; hide trend chart on mobile; show brand bar chart

---

## primary-sales

**Audience**: Sales team, Regional Manager, NSM.
**Business question**: How is Primary volume and value tracking by chain, brand, and period?

**Recommended KPIs**: Primary RSP (₹ Cr), Primary Units, NSV (₹ Cr), Growth vs LY
**Visual hierarchy**:
1. KPI strip
2. Month-on-month line/column chart (Primary RSP trend)
3. Chain-level bar chart or matrix
4. Brand-level bar chart
5. Detail table (chain × brand × month)

**Required filters**: FY, Month, Brand, Chain, Zone, Channel
**Expected source fields**: Primary NSV, MRP, RSP, Units, Ship-to Customer, Chain Name
**Missing-data behaviour**: article-level FY27 data comes from `detail_meta.fyx_primary`; prior FYs from pre-aggregated workbooks — flag gap if FY27 primary is absent
**Validation checks**: warn if FY filter is missing; error if Primary RSP measure is unbound
**Mobile-layout guidance**: KPI strip (2-up), single-chain selector, trend line

---

## offtake-sales

**Audience**: Sales, Trade Marketing, Key Account team.
**Business question**: What are store-level offtake volumes by brand and chain, and how do they compare to Primary?

**Recommended KPIs**: Offtake RSP (₹ Cr), Offtake Units, Offtake vs LY %, Sell-through %
**Visual hierarchy**:
1. KPI strip
2. Offtake trend (monthly line chart)
3. Chain-level breakdown (bar chart)
4. Store-level summary (matrix or table)

**Required filters**: FY, Month, Brand, Chain, Zone
**Expected source fields**: Offtake RSP, Units, Store code, Chain Name — from monthly `.xlsb` ingested via `--offtake-patch`
**Missing-data behaviour**: if a month's file is absent, show blank for that month with a footnote; do not fill forward
**Mobile-layout guidance**: chain selector + trend line; store table hidden on mobile

---

## primary-vs-offtake

**Audience**: NSM, Sales leadership, Trade Marketing.
**Business question**: Is channel inventory healthy — are Primary and Offtake aligned?

**Recommended KPIs**: Primary RSP, Offtake RSP, Primary/Offtake ratio, Inventory days (if available)
**Visual hierarchy**:
1. KPI strip (4 KPIs)
2. Combo chart — Primary (bar) vs Offtake (line) monthly
3. Chain-level gap matrix
4. Brand-level gap chart

**Required filters**: FY, Month, Brand, Chain
**Missing-data behaviour**: if one side is missing for a period, show it as "—" and flag in validation
**Mobile-layout guidance**: combo chart as simplified bar; gap table hidden

---

## pandl

**Audience**: Finance, NSM, Category head.
**Business question**: What are the P&L components (NSV, Gross Margin, CM2) by brand and period?

**Recommended KPIs**: NSV (₹ Cr), Gross Margin %, CM2 %, CM2 ₹ Cr
**Visual hierarchy**:
1. KPI strip
2. Waterfall or stacked bar — P&L bridge
3. Brand × FY matrix
4. Trend line — GM% and CM2%

**Required filters**: FY, Brand, Chain
**Expected source fields**: NSV, COGS, Gross Margin, Trade Spend, BA Cost, CM2 — all from `PowerBI/DAX/02_PnL_Measures.dax`
**Missing-data behaviour**: if CM2 is provisional (CM2_IS_PROVISIONAL flag), lock the CM2 card and show amber warning
**Validation checks**: CM2 provisional banner must be present if applicable
**Mobile-layout guidance**: KPI strip only; full P&L hidden on mobile

---

## cm2-provisional

**Audience**: Finance, NSM — during month-close before CM2 is confirmed.
**Business question**: What is the preliminary CM2 picture subject to Finance approval?

**Non-negotiable**: Amber banner (`#FEF3C7`, locked, zIndex ≥ 1000) must always be visible.
**Recommended KPIs**: Provisional CM2 %, Provisional CM2 ₹ Cr (with ⚠ suffix in title)
**Visual hierarchy**:
1. **CM2 Provisional warning banner** (full-width, top, locked)
2. KPI strip (with provisional labels)
3. Brand-level CM2 matrix
4. Comparison to prior confirmed period

**Required filters**: FY, Brand
**Missing-data behaviour**: if Finance-confirmed CM2 is available, switch to the `pandl` template instead
**Validation checks**: error if banner is missing or hidden; warn if CM2 measures are not sourced from `13_CM2_Measures.dax`

---

## category-pack

**Audience**: Category managers, Brand team.
**Business question**: Which categories, packs, and SKUs are driving volume and value?

**Recommended KPIs**: RSP by Category, Category Growth vs LY, Top SKU contribution
**Visual hierarchy**:
1. KPI strip
2. Category-level treemap or bar chart
3. Pack-size breakdown (bar or column)
4. Top-SKU table

**Required filters**: FY, Brand, Category, Chain
**Expected source fields**: Category, Sub-category, Pack size, Article code, NSV
**Mobile-layout guidance**: category bar chart only; SKU table hidden

---

## forecast

**Audience**: Finance, S&OP team.
**Business question**: How does the current run-rate compare to the FY target, and what is the projected year-end?

**Recommended KPIs**: Target (₹ Cr), Actuals YTD, Forecast Year-End, Variance vs Target
**Visual hierarchy**:
1. KPI strip
2. Forecast vs Actuals line chart (monthly)
3. Brand-level target vs actual gauge or bar
4. Assumption table (if override active)

**Required filters**: FY, Brand, Chain
**Expected source fields**: TY Target, Actuals (Primary), Forecast override — from `PowerBI/DAX/03_Forecast_Measures.dax`
**Missing-data behaviour**: if target is absent for a brand, show "—" and warn in validation
**Mobile-layout guidance**: KPI strip and forecast line; gauges hidden

---

## distribution

**Audience**: Field Sales, NSM, Distribution head.
**Business question**: How many stores stock our brands (TDP/WOD), and where are the gaps?

**Recommended KPIs**: TDP (Total Distribution Points), WOD (Weighted Distribution), Numeric Distribution %
**Visual hierarchy**:
1. KPI strip
2. Zone/State map placeholder or bar chart
3. Chain-level distribution trend (line chart)
4. Store-count table

**Required filters**: FY, Month, Brand, Chain, Zone, State
**Expected source fields**: TDP, WOD — from `PowerBI/DAX/05_TDP_Measures.dax`
**Validation checks**: map-placeholder requires Power BI Desktop and geography data type on State field
**Mobile-layout guidance**: KPI strip and chain bar chart; map hidden

---

## performance-comparison

**Audience**: NSM, Regional leads, Category head.
**Business question**: How do different brands, chains, or regions compare on key metrics?

**Recommended KPIs**: Selected metric (user-driven), YTD vs LY, Rank
**Visual hierarchy**:
1. Comparison selector slicer (metric to compare)
2. Bar chart — entity ranking by selected metric
3. Trend matrix (entity × period)
4. Top/bottom performers table

**Required filters**: FY, Brand, Chain, Zone, Metric selector
**Missing-data behaviour**: entities with no data in the selected period are shown as "—" in the table; not excluded
**Mobile-layout guidance**: ranking bar chart only; matrix hidden

---

## insights-actions

**Audience**: Leadership, Strategy team.
**Business question**: What are the key strategic findings and recommended actions from the data?

**Visual hierarchy**:
1. Key insight text boxes (structured finding + implication)
2. Supporting charts (reduced-detail, illustrative)
3. Action table (recommendation, owner, timeline)

**Required filters**: FY, Brand
**Missing-data behaviour**: all insight text is authored by the analyst — no AI-generated business conclusions without analyst review
**Validation checks**: no data bindings required for text boxes; warn if KPI cards are unbound

---

## data-qc-reconciliation

**Audience**: Data Engineering, Finance, QC team.
**Business question**: Are the source data, DAX outputs, and dashboard numbers consistent?

**Recommended KPIs**: Total Primary RSP (₹ Cr), Reconciliation delta, Row count, Missing fields count
**Visual hierarchy**:
1. Source vs. dashboard comparison matrix
2. Exception table (rows with mismatches)
3. Missing-field summary
4. Validation status card (PASS / WARN / FAIL)

**Required filters**: FY, Data layer (source / DAX / dashboard)
**Routing**: detailed numerical reconciliation → `honasa-dashboard-qc-reconciliation`; source data issues → `honasa-data-engineering`
**Mobile-layout guidance**: status card only; full matrix hidden on mobile
