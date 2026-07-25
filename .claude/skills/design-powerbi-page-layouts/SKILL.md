---
name: design-powerbi-page-layouts
description: >
  Design, specify, validate, and review Power BI dashboard page layouts.
  Use for dashboard blueprints, wireframes, visual placement, visual hierarchy,
  canvas design, page templates, mobile layouts, JSON layout specifications,
  implementation handoffs, overlap or clipping problems, accessibility reviews,
  AI-generated layout proposals, and comparing an implemented Power BI page
  against its approved design.
---

# design-powerbi-page-layouts

## Workflow

Follow all steps in order. Skip only steps that are inapplicable to the request.

1. **Audience and decision** — identify who reads the page and what business decision it supports.
2. **Page purpose** — state the page's analytical question in one sentence.
3. **Data inventory** — list available KPIs, measures, dimensions, filters, and source coverage; flag anything missing.
4. **Canvas setup** — specify width × height, safe margins (≥20 px), grid size, snap behaviour, and responsive requirement.
5. **Visual selection** — choose visual types suited to the analytical question; consult `references/visual-catalog.md`.
6. **Visual definitions** — for each visual specify: position (x, y), size (width, height), zIndex, title, accessibilityLabel, data bindings, aggregation, filters, interactions, and formatting.
7. **Validation** — check hierarchy, density, overlap, clipping, contrast, and unsupported bindings; consult `references/validation.md`.
8. **JSON layout spec** — produce a versioned layout conforming to `references/layout-contract.md` and the schema in `references/schema-reference.md`.
9. **Implementation handoff** — produce a checklist or PDF-ready guide; consult `references/export-handoff.md`.
10. **Distinguish spec from file** — always state explicitly that the output is a design specification, not a PBIX, PBIR, or semantic model.
11. **Preserve existing architecture** — when reviewing an existing page, record existing positions, sizes, bindings, and interactions before proposing any change.
12. **Route numerical reconciliation** — flag any data accuracy question and route to `honasa-dashboard-qc-reconciliation`.
13. **Route missing or zero series** — if charts show no data or unexpected blanks, route to `debug-dashboard-comparisons`.
14. **Route PBIP/PBIR implementation** — actual Power BI file creation goes to the `pbip` or `reports` marketplace plugin.
15. **Report honestly** — state when required data is unavailable or when a visual type is unsupported; never fabricate measures or values.

---

## Non-negotiable constraints

| # | Constraint |
|---|---|
| C1 | Do NOT convert `dashboard/` to React |
| C2 | Do NOT modify Primary/Offtake/CM2/P&L/forecast/FY calculations |
| C3 | THE ONE FY RULE: Apr–Dec of year Y → FY(Y+1); Jan–Mar of year Y → FY(Y) |
| C4 | CM2 Provisional banner must remain locked, z-index ≥1000, amber `#FEF3C7` |
| C5 | Never request or store AI provider keys in browser storage, URLs, or layout JSON |
| C6 | Secret patterns must never appear in exports: `sk-[A-Za-z0-9]{20,}` / `ghp_[A-Za-z0-9]{36}` / `Bearer\s+[A-Za-z0-9+/=]{20,}` |
| C7 | All 177 Python regression tests must remain green |

---

## Canvas presets

| Preset | Width | Height |
|--------|-------|--------|
| Power BI Desktop (default) | 1280 px | 720 px |
| Power BI Mobile | 360 px | 800 px |
| Wide / Executive | 1920 px | 1080 px |

Grid default: 10 px. Safe margin: 20 px from all edges.

---

## Available templates (12)

`executive-overview`, `primary-sales`, `offtake-sales`, `primary-vs-offtake`,
`performance-comparison`, `category-pack`, `forecast`, `distribution`, `pandl`,
`cm2-provisional` ⚠, `data-qc-reconciliation`, `insights-actions`

**`cm2-provisional`** always adds a mandatory locked amber warning banner — do not remove it.

---

## Visual types (17)

`kpi-card`, `text`, `image-placeholder`, `bar-chart`, `column-chart`, `line-chart`,
`combo-chart`, `pie-chart`, `donut-chart`, `table`, `matrix`, `slicer`, `gauge`,
`funnel`, `treemap`, `decomposition-tree-placeholder`, `map-placeholder`

The last two are placeholder types — they require Power BI Desktop to instantiate.

---

## Reference files

| File | Content |
|------|---------|
| `references/layout-contract.md` | Versioned layout JSON specification and field definitions |
| `references/visual-catalog.md` | Per-type analytical fit, bindings, defaults, and Power BI notes |
| `references/editor-interactions.md` | Design-time editor behaviour contract |
| `references/export-handoff.md` | JSON export and PDF implementation guide specification |
| `references/ai-layout-generation.md` | Safe AI-assisted layout generation workflow |
| `references/validation.md` | Validation rules and implementation comparison checklist |
| `references/layout-guidelines.md` | Honasa-specific positioning and KPI strip templates |
| `references/schema-reference.md` | Zod schema fields and secret-rejection patterns |

---

## Routing

| Need | Route to |
|------|----------|
| Numerical reconciliation, release readiness | `honasa-dashboard-qc-reconciliation` |
| Missing, zero, stale, or mismatched chart series | `debug-dashboard-comparisons` |
| Source pipelines, lineage, data quality | `honasa-data-engineering` |
| CM2 classification, provisional governance | `honasa-cm2-expense-classification` |
| PBIP/TMDL/PBIR file authoring | `pbip` plugin |
| DAX, Power Query, semantic models | `semantic-models` plugin |
| Themes, visuals, accessibility audit | `reports` plugin |
| Agent safety, prompt-injection | `run-evidence-grounded-agents` |
| CI/CD, security testing | `run-devsecops-productivity` |
| Portfolio presentation, KPI storytelling | `build-sales-bi-portfolio` |
