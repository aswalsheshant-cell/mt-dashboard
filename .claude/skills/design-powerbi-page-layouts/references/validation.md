# Validation Rules

Validation must run before every export, and may be run on demand at any time.
Results are categorised as **error** (blocks export), **warning** (flagged but
does not block), or **info** (informational).

---

## Per-visual rules

| Rule | Severity | Condition |
|------|----------|-----------|
| Unique stable ID | error | Two visuals share the same `id` on the same page |
| ID format | error | `id` does not match `/^[a-zA-Z0-9_-]+$/` |
| Required bindings present | error | Chart or KPI visual has no `measures` binding |
| Measure vs. dimension | error | A dimension field is used where a measure is required, or vice versa |
| Aggregation appropriate | warning | A non-aggregatable field (e.g. text) is assigned `sum` or `avg` |
| Inside canvas boundary | warning | `x + width > canvas.width` or `y + height > canvas.height` |
| Non-negative coordinates | error | `x < 0` or `y < 0` |
| Minimum size | error | `width < 10` or `height < 10` |
| Accessibility label present | warning | `accessibilityLabel` is blank or missing |
| Meaningful title | warning | `title` is blank |
| Category count (pie/donut) | warning | Category dimension has more than 8 known values |
| Category count (bar/column) | warning | Category dimension has more than 20 known values |
| Placeholder type | info | Visual type is `decomposition-tree-placeholder` or `map-placeholder` |
| Colour-only status signal | warning | Formatting uses colour to convey status with no accompanying icon, pattern, or label |
| Contrast | warning | Text colour and background colour have an estimated contrast ratio below 4.5:1 |
| Funnel order | warning | Funnel categories cannot be logically ordered |
| Gauge without target | warning | Gauge visual has no target measure binding |
| Treemap negative values | error | Treemap measure binding can produce negative values |

---

## Per-page rules

| Rule | Severity | Condition |
|------|----------|-----------|
| Visual overlap | warning | Two visible visuals overlap by more than 10% of the smaller visual's area (unless one is locked as a background) |
| Safe margin | warning | Any visual is closer than `safeMargin` pixels to a canvas edge |
| Page density | warning | More than 30 visible visuals on a single page |
| Filters reachable | warning | No slicer on the page and page-level filters are empty |
| Mobile overrides present | warning | `mobileLayout` is true but fewer than half the visuals have a `mobileOverride` |
| Grid size | warning | `gridSize` is 0 or greater than 100 |
| CM2 provisional banner | error | Page uses the `cm2-provisional` template and the amber warning banner visual is missing or `hidden: true` |

---

## Schema and security rules

| Rule | Severity | Condition |
|------|----------|-----------|
| Schema version present | error | `schemaVersion` is absent or does not match `SCHEMA_VERSION` |
| Unknown fields in strict sections | error | Any unrecognised key appears in a `Visual` object (`strict()` rejects `_raw` and other extras) |
| Secret pattern in export | error | Serialised JSON matches `/sk-[A-Za-z0-9]{20,}/`, `/ghp_[A-Za-z0-9]{36}/`, or `/Bearer\s+[A-Za-z0-9+/=]{20,}/` |
| Executable content | error | Layout JSON contains `<script`, `javascript:`, or SQL/DAX keywords in non-label fields |
| Fabricated data | error | A measure value is hardcoded as a literal number instead of a field binding |

---

## Implementation comparison

When comparing an **approved layout specification** against an **implemented
Power BI page** (e.g. from PBIP metadata or a screenshot):

### Comparison checklist

For each visual in the approved specification:

| Check | Pass condition |
|-------|---------------|
| Visual present | A corresponding visual exists in the implementation |
| Visual type matches | The Power BI visual type maps to the specified type |
| Position within tolerance | x/y within ±10 px |
| Size within tolerance | width/height within ±10 px |
| Primary measure bound | The main measure is connected to the correct field |
| Category/dimension bound | Dimension fields match |
| Aggregation | Aggregation type matches (sum, avg, count, etc.) |
| Active filters | Page-level and visual-level filters applied |
| Cross-filter enabled | Visual Interactions set correctly |
| Accessibility label set | Alt text present in Power BI |
| Conditional formatting | Where specified, conditional formatting is applied |
| Mobile override applied | Phone Layout reflects the mobileOverride values |

### Comparison output format

```
LAYOUT COMPARISON REPORT
Page: {pageName}
Specification version: {schemaVersion}
Compared: {date}

MISSING VISUALS (in spec, not in implementation):
  - {id}: {title} ({type})

EXTRA VISUALS (in implementation, not in spec):
  - {id}: {title}

POSITION DIFFERENCES:
  - {id}: spec x={sx} y={sy}, impl x={ix} y={iy} (delta: Δx={dx} Δy={dy})

SIZE DIFFERENCES:
  - {id}: spec {sw}×{sh}, impl {iw}×{ih}

BINDING DIFFERENCES:
  - {id}: spec measure='{sm}', impl measure='{im}'

FORMATTING DIFFERENCES:
  - {id}: spec {field}={sv}, impl {field}={iv}

INTERACTION DIFFERENCES:
  - {id}: crossFilter expected={e} actual={a}

ACCESSIBILITY DIFFERENCES:
  - {id}: accessibilityLabel expected, not found in implementation

UNSUPPORTED ITEMS:
  - {id}: type '{type}' requires Power BI Desktop; verify implementation visually

SEVERITY SUMMARY:
  Errors:   {n}
  Warnings: {n}
  Info:     {n}

RECOMMENDED ACTIONS:
  {actionable steps in priority order}
```

---

## Routing from validation

| Finding | Route |
|---------|-------|
| Measure values wrong | `honasa-dashboard-qc-reconciliation` |
| Chart series missing or blank | `debug-dashboard-comparisons` |
| PBIP/PBIR file needs editing | `pbip` plugin |
| Source field missing from semantic model | `honasa-data-engineering` |
| CM2 provisional governance | `honasa-cm2-expense-classification` |

---

## Honasa-specific validation additions

- **CM2 Provisional page**: amber warning banner visual must be present, `locked: true`, `zIndex ≥ 1000`, `hidden: false`.
- **KPI cards**: KPI measures must come from governed DAX measures listed in `PowerBI/DAX/01_CoreMeasures.dax` or `PowerBI/DAX/13_CM2_Measures.dax` — not derived inline in the layout spec.
- **FY filter**: pages covering multiple financial years must include an FY slicer or page-level FY filter. THE ONE FY RULE applies: Apr–Dec → FY(Y+1), Jan–Mar → FY(Y).
- **Data availability boundary**: FY25/FY26 come from pre-aggregated workbooks; FY27+ come from article-level detail files. Layout specs must not mix these sources without explicit coverage notes.
