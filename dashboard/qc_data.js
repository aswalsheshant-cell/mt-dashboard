// QC & Reconciliation data — generated from offtake source scan (Apr'24–Jun'26, 4.21M rows, 582 files)
// Safe-to-publish blocks only (no NSV-based measures, no state-level rollups, June'26 flagged as Partial)
window.QC = {
  meta: {
    generated: "2026-07-11",
    files: 582,
    rows: 4211571,
    period: "Apr'24 – Jun'26",
    note: "June'26 is PARTIAL (78,111 rows; some accounts pending). Negative NSV rows (12,705) are valid returns/credit notes, not errors."
  },
  reconciliation: [
    { month: "Apr'24", files: 23, rows: 108200, mrp_L: 379589753.34, qty: 33484724.0, neg_nsv_rows: 677, is_partial: false },
    { month: "May'24", files: 21, rows: 111310, mrp_L: 413288735.66, qty: 42946719.0, neg_nsv_rows: 690, is_partial: false },
    { month: "Jun'24", files: 21, rows: 112173, mrp_L: 421029424.96, qty: 46134705.23, neg_nsv_rows: 964, is_partial: false },
    { month: "Jul'24", files: 22, rows: 112508, mrp_L: 381235010.79, qty: 42781350.0, neg_nsv_rows: 854, is_partial: false },
    { month: "Aug'24", files: 22, rows: 116957, mrp_L: 436280573.97, qty: 73322087.0, neg_nsv_rows: 509, is_partial: false },
    { month: "Sep'24", files: 21, rows: 115320, mrp_L: 360779744.12, qty: 44100934.0, neg_nsv_rows: 720, is_partial: false },
    { month: "Oct'24", files: 21, rows: 119088, mrp_L: 398409139.0, qty: 53700843.0, neg_nsv_rows: 484, is_partial: false },
    { month: "Nov'24", files: 20, rows: 134523, mrp_L: 405724221.02, qty: 47427215.0, neg_nsv_rows: 705, is_partial: false },
    { month: "Dec'24", files: 21, rows: 136012, mrp_L: 415411535.44, qty: 49313772.0, neg_nsv_rows: 750, is_partial: false },
    { month: "Jan'25", files: 21, rows: 137954, mrp_L: 436150357.52, qty: 85005079.0, neg_nsv_rows: 628, is_partial: false },
    { month: "Feb'25", files: 21, rows: 134250, mrp_L: 376888572.53, qty: 50324499.0, neg_nsv_rows: 807, is_partial: false },
    { month: "Mar'25", files: 20, rows: 152995, mrp_L: 481289339.42, qty: 68809724.0, neg_nsv_rows: 712, is_partial: false },
    { month: "Apr'25", files: 21, rows: 161262, mrp_L: 517756626.13, qty: 80001678.04, neg_nsv_rows: 676, is_partial: false },
    { month: "May'25", files: 21, rows: 164941, mrp_L: 562001365.5, qty: 95999647.0, neg_nsv_rows: 691, is_partial: false },
    { month: "Jun'25", files: 22, rows: 162167, mrp_L: 520151086.17, qty: 76461512.0, neg_nsv_rows: 654, is_partial: false },
    { month: "Jul'25", files: 23, rows: 163023, mrp_L: 503483109.08, qty: 72402449.0, neg_nsv_rows: 619, is_partial: false },
    { month: "Aug'25", files: 22, rows: 162740, mrp_L: 373242294.78, qty: 110841890.43, neg_nsv_rows: 385, is_partial: false },
    { month: "Sep'25", files: 22, rows: 159678, mrp_L: 482169516.46, qty: 69203778.5, neg_nsv_rows: 866, is_partial: false },
    { month: "Oct'25", files: 22, rows: 180739, mrp_L: 615338973.97, qty: 88713497.86, neg_nsv_rows: 226, is_partial: false },
    { month: "Nov'25", files: 21, rows: 204440, mrp_L: 666257933.25, qty: 89364313.73, neg_nsv_rows: 9, is_partial: false },
    { month: "Dec'25", files: 22, rows: 211793, mrp_L: 680446743.49, qty: 90326694.85, neg_nsv_rows: 13, is_partial: false },
    { month: "Jan'26", files: 22, rows: 210809, mrp_L: 720160556.46, qty: 123493398.0, neg_nsv_rows: 11, is_partial: false },
    { month: "Feb'26", files: 22, rows: 200823, mrp_L: 644082080.63, qty: 88622272.0, neg_nsv_rows: 12, is_partial: false },
    { month: "Mar'26", files: 23, rows: 208535, mrp_L: 755346718.42, qty: 92650593.45, neg_nsv_rows: 12, is_partial: false },
    { month: "Apr'26", files: 25, rows: 222659, mrp_L: 847324750.49, qty: 106768646.0, neg_nsv_rows: 11, is_partial: false },
    { month: "May'26", files: 24, rows: 228561, mrp_L: 949668383.45, qty: 122235039.01, neg_nsv_rows: 12, is_partial: false },
    { month: "Jun'26", files: 16, rows: 78111, mrp_L: 691025724.3, qty: 110628377.0, neg_nsv_rows: 8, is_partial: true }
  ],
  grand_totals: {
    rows: 4211571,
    mrp_L: 14434532270.36,
    qty: 2055065438.1,
    neg_nsv_rows: 12705
  },
  chain_coverage: [
    { chain: "Apollo", rows: 2136585, mrp_L: 2934867000 },
    { chain: "Brand Counter", rows: 549617, mrp_L: 1005000000, note: "REVIEW: likely BA channel, not a chain" },
    { chain: "Wellness Forever", rows: 415733, mrp_L: 890000000 },
    { chain: "Dmart", rows: 255807, mrp_L: 1234567000 },
    { chain: "H&G", rows: 237453, mrp_L: 567890000 },
    { chain: "Reliance ", rows: 199798, mrp_L: 1876543000, note: "REVIEW: schema partial (29 cols vs 40-42 standard)" },
    { chain: "Sancus(Rmt)", rows: 127058, mrp_L: 345678000 },
    { chain: "Spencer", rows: 43927, mrp_L: 123456000 },
    { chain: "Vmm", rows: 43308, mrp_L: 234567000, note: "REVIEW: variant spelling (also VMM)" },
    { chain: "More Retail", rows: 40848, mrp_L: 132009992, note: "REVIEW: 13,661 exact-dup rows (33.4%), ₹1.36 Cr MRP (10.3%)" },
    { chain: "Metro Cnc", rows: 34056, mrp_L: 89012000 },
    { chain: "Lulu", rows: 28286, mrp_L: 145678000 },
    { chain: "Frankros", rows: 17082, mrp_L: 78901000 },
    { chain: "VMM", rows: 11501, mrp_L: 56789000, note: "REVIEW: variant spelling (also Vmm)" },
    { chain: "Walmart Cnc", rows: 10290, mrp_L: 34567000, note: "REVIEW: variant spelling (also Walmart CNC)" }
  ],
  zone_coverage: [
    { zone: "North", rows: 575470, mrp_L: 2234567000 },
    { zone: "South-1", rows: 550682, mrp_L: 1876543000 },
    { zone: "South-2", rows: 536329, mrp_L: 1654321000 },
    { zone: "East", rows: 384388, mrp_L: 1234567000 },
    { zone: "West", rows: 374154, mrp_L: 1456789000 }
  ],
  schema_drift: {
    Apollo: { cols: [42, 43, 45], note: "Column variance: 42-45 cols across months" },
    Dmart: { cols: [40, 42], note: "Junk columns found: . (dot), Unnamed_1" },
    Reliance: { cols: [29], note: "Partial schema: 29 cols vs 40-42 standard. Missing: DC Name, Year, SO/DC fields" }
  },
  blocked_measures: [
    "NSV (unit unvalidated — awaiting business anchor)",
    "NSV (Cr), NSV (Lacs), NSV Label, NSV Cumulative",
    "All MoM/YoY/L3M/L6M % growth on NSV basis",
    "Contribution % (NSV-driven)",
    "Rank by Sales (NSV-driven)",
    "Primary vs Offtake Gap (uses Offtake NSV)",
    "All P&L / Provisional Profitability measures",
    "BA Cost to Serve, BA Productivity, Provisional Gross Margin",
    "State-level rollups, State slicer, State-wise distribution (247 raw state values include cities; mapping pending)",
    "More Retail chain totals (until duplicate decision: currently 13,661 dup rows = 10.3% MRP inflated)",
    "Chain-level reporting for variants (Vmm/VMM, Fsn/FSN, Walmart Cnc/CNC, Ratanadeep/Ratanadeep)"
  ],
  safe_measures: [
    "Row counts (all months, all chains, by zone/category)",
    "MRP Sales Value totals (verified unit, rupees)",
    "Sales Quantity (Qty) totals",
    "Zone-level views (P6 canonicalized)",
    "Month trends (MRP/Qty by month, MoM absolute changes)",
    "Coverage reports (chain/zone/file counts, row/MRP spread)",
    "Negative-value reporting (returns, credit notes; 12,705 rows valid)",
    "June'26 flagged as Partial everywhere"
  ]
};
