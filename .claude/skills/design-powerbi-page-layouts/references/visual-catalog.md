# Visual Catalog

For each visual type: analytical fit, unsuitable uses, required/optional bindings,
supported aggregations, recommended default size, formatting notes,
accessibility requirements, validation rules, and Power BI implementation notes.

---

## kpi-card

**Suitable for**: single governed measure with optional target or trend spark line.
**Unsuitable for**: comparisons across many values, time series with > 2 data points.

| Binding | Requirement |
|---------|-------------|
| measures[0] | Required — the primary KPI value |
| measures[1] | Optional — comparison target or prior-period value |
| categories | Not used |

**Aggregations**: sum, avg, count, min, max.
**Default size**: 200 × 100 px.
**Formatting**: large value font (≥24 px), trend arrow or spark line optional, colour-coding paired with icon or text label — never colour alone.
**Accessibility**: `accessibilityLabel` must state the measure name and context (e.g. "Primary RSP for selected FY and brand").
**Validation**: error if no measure binding. Warning if title is blank.
**Power BI notes**: use Card or New Card visual; conditional formatting requires a separate measure — do not embed DAX in the layout spec.

---

## line-chart

**Suitable for**: continuous trends over time; comparing two or more measures across the same time axis.
**Unsuitable for**: unordered categories, part-to-whole, single data points.

| Binding | Requirement |
|---------|-------------|
| categories[0] | Required — time dimension (date, month, FY) |
| measures | Required — ≥1 measure |
| series | Optional — breakdown dimension (adds multiple lines) |

**Aggregations**: sum, avg, count, min, max.
**Default size**: 520 × 280 px.
**Formatting**: enable markers for sparse data; use distinct line patterns or labels when multiple series present, never only colour.
**Accessibility**: label each series by name; do not rely on colour alone to distinguish lines.
**Validation**: error if no time category. Error if no measure. Warning if series has > 8 values (colour distinguishability).
**Power BI notes**: X-axis must be a Date or continuous field for proper time scaling.

---

## bar-chart

**Suitable for**: comparing a measure across categories, especially when category names are long.
**Unsuitable for**: time series (use line-chart), part-to-whole with > 8 segments (use table).

| Binding | Requirement |
|---------|-------------|
| categories[0] | Required — categorical dimension |
| measures | Required — ≥1 measure |
| series | Optional — breakdown |

**Aggregations**: sum, avg, count, min, max.
**Default size**: 520 × 280 px.
**Formatting**: sort descending by measure; show data labels for key comparisons.
**Accessibility**: ensure bar labels or data labels convey values; avoid colour-only encoding.
**Validation**: error if no measure. Warning if category has > 20 values.
**Power BI notes**: horizontal orientation; sort by value in visual properties.

---

## column-chart

**Suitable for**: comparing a measure across a small number of categories (≤12); time periods on X-axis.
**Unsuitable for**: long category labels, > 20 categories.

Same bindings, aggregations, and validation as bar-chart.
**Default size**: 520 × 280 px.
**Power BI notes**: vertical orientation; may be stacked or clustered.

---

## combo-chart

**Suitable for**: overlaying two measures with different scales (e.g. volume as bar, growth% as line).
**Unsuitable for**: more than two Y-axes; unrelated dimensions.

| Binding | Requirement |
|---------|-------------|
| categories[0] | Required — shared X-axis (usually time) |
| measures[0] | Required — bar/column measure (left axis) |
| measures[1] | Required — line measure (right axis) |

**Aggregations**: sum, avg.
**Default size**: 520 × 280 px.
**Formatting**: label each axis; use distinct visual encodings (bar vs. line).
**Power BI notes**: Line and Clustered Column Chart or Line and Stacked Column Chart visual.

---

## pie-chart / donut-chart

**Suitable for**: part-to-whole with ≤6 categories where relative proportions matter.
**Unsuitable for**: time series, negative values, > 8 categories (segments become unreadable).

| Binding | Requirement |
|---------|-------------|
| categories[0] | Required — categorical dimension |
| measures[0] | Required — value measure |

**Aggregations**: sum, count.
**Default size**: 280 × 280 px.
**Formatting**: show labels with percentages; avoid light-on-light adjacent slices.
**Accessibility**: list values in the accessibility label; do not rely on colour alone.
**Validation**: error if > 8 category values. Warning if any slice < 2% (invisible).
**Power BI notes**: Donut variant shows centre metric well; Pie shows no centre space.

---

## table

**Suitable for**: detailed evidence, row-level comparisons, export-ready data.
**Unsuitable for**: aggregated summaries where a KPI card or chart is clearer.

| Binding | Requirement |
|---------|-------------|
| measures | Required — ≥1 column |
| categories | Optional — dimension columns |

**Default size**: 1070 × 320 px (full-width).
**Formatting**: alternate row shading; bold header; freeze header row in Power BI.
**Accessibility**: column headers must be meaningful; screen readers read column by column.
**Validation**: warning if > 20 columns (horizontal scroll in Power BI becomes poor UX).
**Power BI notes**: Table visual supports conditional formatting per cell. For export, pair with Export Data in report settings.

---

## matrix

**Suitable for**: cross-tabulated analysis (rows × columns), subtotals, drill-down hierarchies.
**Unsuitable for**: flat lists, single-dimension summaries.

| Binding | Requirement |
|---------|-------------|
| categories (rows) | Required — ≥1 row dimension |
| series (columns) | Required — ≥1 column dimension |
| measures | Required — ≥1 value |

**Default size**: 1070 × 320 px.
**Formatting**: enable subtotals; collapse hierarchy levels by default for readability.
**Accessibility**: row and column headers must be descriptive.
**Validation**: error if no row dimension. Error if no measure.
**Power BI notes**: Matrix visual; step-layout or compact layout for deep hierarchies.

---

## slicer

**Suitable for**: user-controlled filtering of the page or report.
**Unsuitable for**: displaying analytical results.

| Binding | Requirement |
|---------|-------------|
| categories[0] | Required — dimension to filter by |

**Default size**: 160 × 200 px.
**Formatting**: place in a consistent rail (left or top); label clearly; use dropdown style for long lists.
**Accessibility**: label must state what is being filtered (e.g. "Filter by Brand").
**Validation**: error if no binding. Warning if slicer z-index < 100 (may be obscured by charts).
**Power BI notes**: Slicer visual; sync slicers across pages via View → Sync Slicers. Always visible — never hidden by default.

---

## gauge

**Suitable for**: progress against a single meaningful target (e.g. 85% of target achieved).
**Unsuitable for**: comparisons across multiple dimensions; situations where the target is undefined.

| Binding | Requirement |
|---------|-------------|
| measures[0] | Required — current value |
| measures[1] | Optional — target value |
| measures[2] | Optional — minimum value |

**Aggregations**: sum, avg.
**Default size**: 240 × 160 px.
**Formatting**: label the target explicitly; include numeric readout, not only arc fill.
**Accessibility**: state current value, target, and percentage in the label.
**Validation**: warning if no target binding (gauge arc is meaningless without a target).
**Power BI notes**: Gauge visual; set min, target, and max in the visual's Field well.

---

## funnel

**Suitable for**: ordered stages with progressive reduction (e.g. awareness → trial → purchase).
**Unsuitable for**: unrelated categories, stages without a logical order.

| Binding | Requirement |
|---------|-------------|
| categories[0] | Required — stage dimension (must be orderable) |
| measures[0] | Required — value at each stage |

**Default size**: 360 × 280 px.
**Formatting**: label each stage with absolute value and conversion rate.
**Accessibility**: order stages in the accessibility label from widest to narrowest.
**Validation**: warning if category values cannot be logically ordered. Error if no measure.
**Power BI notes**: Funnel visual. Sort category by stage order, not alphabetically.

---

## treemap

**Suitable for**: hierarchical contribution where proportional area communicates relative size (e.g. brand contribution to total NSV).
**Unsuitable for**: negative values, time series, > 20 leaf nodes (rectangles become tiny).

| Binding | Requirement |
|---------|-------------|
| categories[0] | Required — primary grouping |
| categories[1] | Optional — sub-grouping (hierarchy) |
| measures[0] | Required — size value |

**Default size**: 520 × 280 px.
**Formatting**: use data labels on tiles ≥ a minimum area threshold only; set a label minimum size in Power BI.
**Accessibility**: do not rely on tile area alone — include a tooltip with the numeric value.
**Validation**: warning if > 20 leaf nodes. Error if measure can be negative.
**Power BI notes**: Treemap visual. Category hierarchy drills down on click.

---

## text

**Suitable for**: titles, section headings, disclaimers, instructional text.
**Unsuitable for**: data display.

No data bindings required.
**Default size**: 400 × 60 px.
**Formatting**: use meaningful text; do not use placeholder "Lorem ipsum" in production specs.
**Accessibility**: ensure text contrast ratio ≥ 4.5:1 against the background.
**Power BI notes**: Text Box visual. Supports rich text formatting including hyperlinks.

---

## image-placeholder

**Suitable for**: reserving space for a logo, brand image, or illustration.
**Unsuitable for**: data visualisation.

No data bindings required.
**Default size**: 160 × 80 px.
**Validation**: info — label as placeholder in the handoff.
**Power BI notes**: Image visual. The actual image asset must be provided at implementation time.

---

## decomposition-tree-placeholder

**Suitable for**: AI-driven decomposition of a measure into contributing factors.
**Unsuitable for**: static summaries; must be created in Power BI Desktop.

| Binding | Requirement |
|---------|-------------|
| measures[0] | Required — measure to decompose |
| categories | Optional — dimensions to split by |

**Default size**: 800 × 400 px.
**Validation**: always flagged as "placeholder — Power BI Desktop required".
**Power BI notes**: Decomposition Tree visual (standard); requires AI Insights enabled in the service for AI splits.

---

## map-placeholder

**Suitable for**: geographic distribution across states, zones, or cities.
**Unsuitable for**: non-geographic dimensions; use this placeholder when geo-data is unavailable at design time.

| Binding | Requirement |
|---------|-------------|
| categories[0] | Required — geography field (State, City, Zone) |
| measures[0] | Required — measure to plot |

**Default size**: 600 × 400 px.
**Validation**: always flagged as "placeholder — Power BI Desktop required".
**Power BI notes**: Map visual or Azure Maps visual. Requires geographic data type set on the field in the semantic model.
