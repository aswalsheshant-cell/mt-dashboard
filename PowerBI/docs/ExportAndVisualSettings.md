# Export & Visual Settings

Companion to `PageLayouts.md`. Covers three things: (1) exporting a full report
page as PDF, (2) exporting an individual visual's data to Excel/CSV, and (3)
the data-label / display-unit settings that keep every chart's values visible
and formatted the same way as the HTML dashboard (₹ Lakh/Crore, Qty Crore/Lakh
— see `DAX/11_ExportDisplay_Measures.dax`).

---

## 1. Export a full report page (PDF)

Power BI does not have a per-visual "download this chart as an image" button
built in the way the HTML dashboard does — the native export unit is the
**whole report page**, with whatever filters/slicers are currently applied.

**Power BI Desktop:**
`File ▸ Export ▸ Export to PDF`. This renders every visual on the *current*
page exactly as displayed (current slicer/filter state included) into one PDF
page. Switch to the page you want first — it only exports the active page,
not the whole report, unless you tick "Export all pages" in the dialog.

**Power BI Service (browser):**
Open the report ▸ `File ▸ Export to PDF` (or `Export ▸ PDF` in newer UI).
Same behaviour: current page + current filters. Service export also supports
`Export to PowerPoint` if you need editable slides instead of a flat PDF.

**Add this note to each report page** (a text box, bottom-right, matches the
HTML dashboard's page-download convention): *"Use File ▸ Export ▸ PDF to
download this page with current filters applied."* `PageLayouts.md` should
get this text box added to Pages 1–12 the next time layouts are built in
Desktop — it's a one-line text box per page, not a DAX/PQ change, so it isn't
duplicated file-by-file here.

**Export-friendly layout tips (avoids cut titles / overlapping legends):**
- Keep the page at the standard 16:9 canvas size (Desktop default) — PDF
  export maps 1:1 to canvas size, so an oversized custom canvas gets clipped.
- Leave the right-hand slicer panel un-collapsed **before** exporting so the
  active-filter state is visible in the PDF (matches Section 8's "repeat
  filter summary" requirement) — bookmark this state if you export the same
  scoped view often.
- Long tables (Page 11 Raw Data Export View, the Page 7 Article table when
  unfiltered) should **not** be squeezed onto the PDF page — export those via
  "Export data" (§2 below) to Excel instead, and keep the on-page table
  visual filtered/Top-N'd so what does render in the PDF is legible.

---

## 2. Export a single visual's data (Excel/CSV)

Every table, matrix, and chart visual has this built in — no custom
development needed:

1. Hover the visual ▸ click **`…` (More options)** ▸ **Export data**.
2. Choose **Summarized data** (what's currently aggregated/displayed) or
   **Underlying data** (row-level, pre-aggregation) — Underlying requires the
   "Read with underlying data" permission, see §4.
3. Choose **`.xlsx`** or **`.csv`**. Power BI names the file after the visual
   title — rename it to match the dashboard's convention if you need
   consistency with the HTML exports, e.g.
   `MT_Dashboard_ChainPerformance_May26_20260703.xlsx`.

This works identically for **charts** (bar/line/donut) — Export data on a
chart visual exports its underlying category/value pairs, not a screenshot,
so it's the Power BI equivalent of the HTML dashboard's "CSV/Excel" chart
download (there's no native PNG-of-a-single-chart export in Power BI; see the
Limitations section).

**Row limits** depend on your Power BI license tier (Pro vs Premium/PPU) and
tenant admin settings — Power BI Desktop caps Summarized-data export around
30K rows and Underlying-data export around 150K rows by default; Premium
capacities can raise this. If Page 11 or a large Article-level export hits
the cap, add slicers to scope the export (Month, Chain, Category) rather than
pulling the entire fact table in one go.

### Per-page export tables (Section 6/7 of the request)

These reuse the visuals/pages that already exist — no new physical DAX tables
were built, since Power BI's per-visual "Export data" already produces
exactly this output for any table/matrix/chart bound to the right fields:

| Requested export table | Where it already exists |
|---|---|
| Pack Size performance | Page 7 — "Pack-size performance" bar + Article table (`Pack Size`, `NSV`, `MoM Growth %` columns) |
| Sub-category → Range drill-down | Page 7 — build a matrix on `Sub-category` → `Range` (add `Range` next to the existing Product hierarchy, see §3) — drilling in the matrix and then hitting Export data exports **only the currently-drilled level**, matching the HTML dashboard's drill-scoped export behaviour automatically |
| Article-level table | Page 7 table (full column list in `PageLayouts.md` §Page 7) |
| SIS reconciliation table | `docs/SIS_Reconciliation.md` — kept as an audit doc, not a live report page (see **Known gaps** below) |
| Forecast table | Page 5 — Forecast Dashboard |
| P&L table | Page 4 — Chain-wise P&L |
| Market share table | Page 9 — Nielsen Market Share MoM |

---

## 3. Data labels, tooltips, and display units

**Turn on data labels (every key bar/column/line visual):**
Select the visual ▸ Format pane (paint-roller icon) ▸ **Data labels ▸ On**.
For bar/column: `Display units: None` (Lakh/Crore has no native Power BI
unit — see below), `Value decimal places: 0` for the raw number, or bind the
`*_Value Label` / `*_Qty Label` measure from `DAX/11_ExportDisplay_Measures.dax`
as the label field if the visual type supports a measure-driven label
(Matrix/Table always does; some chart types only support the plotted measure
itself as the label — in that case put the raw numeric measure in "Values"
and add the Label measure to **Tooltips** instead, so hovering shows the
correctly-formatted ₹ L/Cr or Qty Cr/L text).

**Donut/pie:** Format ▸ Data labels ▸ On, `Detail labels: Value, Percent of
total`. This gives both absolute value and % share, matching the HTML
dashboard's donut labels.

**Why not use Power BI's native "Display units" (Auto/K/M/Bn)?**
It doesn't understand Indian Lakh/Crore — "100 K" or "1.2 M" would read wrong
against the rest of the dashboard. Leave axis Display units set to **None**
and use the Label measures for anything that needs to show Lakh/Crore text.

**Tooltips:** Format pane ▸ Tooltips ▸ Fields — add `MoM Growth %`,
`YoY Growth %`, and the relevant `*_Value Label`/`*_Qty Label` measure to
every chart's tooltip so hovering shows the full detail the request asks for
("detailed tooltips ... total value where applicable").

**Long category names (avoid overlap):** Format ▸ X-axis ▸ enable
`Concatenate labels: Off` isn't needed — instead prefer horizontal bar charts
(already used for Pack-size/Article rankings per `PageLayouts.md`) over
vertical columns when category names are long, and set X-axis `Rotate
labels: 45°` on any vertical bar chart with more than ~8 categories.

---

## 4. Permissions (admin, one-time)

Same settings as raw-data export, documented in `RefreshGuide.md` §5:
- Tenant level: Admin Portal ▸ Tenant settings ▸ Export and sharing settings
  ▸ enable "Export data" for the MT analytics security group.
- Dataset level: workspace ▸ dataset ▸ Settings ▸ grant "Build" / "Read with
  underlying data" only to users who should export row-level detail.
- PDF export requires no extra permission beyond viewing the report.

---

## 5. Known limitations vs the HTML dashboard

Be upfront about these rather than pretending Power BI matches 1:1:

- **No per-visual PNG/image download.** Power BI's smallest export unit for
  an *image* is the whole page (via PDF, or Service's "Analyze in Excel" for
  data only). To get one chart as an image, export the page PDF and crop it,
  or use Service's "Export ▸ PowerPoint" and screenshot the slide.
- **No client-side filename templating.** Power BI names exported files after
  the visual/report title; you rename manually if you want the
  `MT_Dashboard_<Chart>_<Month>_<Timestamp>.xlsx` convention used by the HTML
  dashboard.
- **Row caps on Export data** (see §2) — not an issue for the HTML dashboard,
  which exports whatever's currently rendered client-side with no server-side
  cap.
- **Drill-scoped export needs a Matrix, not a bar chart.** The HTML
  dashboard's Category → Sub-category → Range → Pack Size → Article drill
  exports "whatever level you're drilled to" for any chart type. In Power BI
  that exact behaviour only works cleanly on **table/matrix** visuals with a
  hierarchy — a drilled-down bar/column chart's Export data still exports the
  chart's current (drilled) category axis correctly, but a treemap or donut
  drilled via hierarchy sometimes exports the full hierarchy depth instead of
  just the current level. If you see extra rows, switch that specific visual
  to Underlying data and manually filter, or rebuild it as a matrix.

### Two gaps flagged, not silently resolved

1. **"Chain-wise TOT% / On-Invoice Margin Pass-on / Weighted TOT% / MoM TOT Δ
   pp / Incremental Pass-on Impact"** — these metrics do not exist anywhere in
   the current data model (checked `DataDictionary.md`, all `DAX/*.dax`,
   `dashboard/data.js`). There's no TOT% (Trade Offer/Terms?) source column or
   defined formula to build a measure from. No export table was fabricated
   for these — flagging so the actual source file / calculation logic can be
   supplied, at which point the same Label-measure pattern in
   `DAX/11_ExportDisplay_Measures.dax` extends to them directly.
2. **SIS Reconciliation Drill-down** — this was removed from the visible HTML
   dashboard UI in an earlier round (kept only in `docs/SIS_Reconciliation.md`
   for audit record, per explicit instruction at the time). It was never a
   live Power BI report page either (only the audit doc exists), so nothing
   changed on the Power BI side. If SIS Reconciliation should come back as a
   visible page/section in either tool, say so explicitly — it wasn't
   silently re-added here since the earlier removal was a deliberate call.
