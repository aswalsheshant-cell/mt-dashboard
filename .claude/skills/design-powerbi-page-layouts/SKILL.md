---
name: design-powerbi-page-layouts
description: >
  Layout Studio design assistant for the Honasa / Mamaearth MT Analytics Platform.
  Use for: page layout design, visual placement and sizing, template selection, schema
  validation, accessibility review, export specification, and production readiness checks
  for Power BI reports. Do NOT use for Power BI Desktop PBIX/PBIR authoring (use the
  pbip plugin), DAX/Power Query (use semantic-models plugin), or data engineering tasks
  (use honasa-data-engineering agent).
---

# design-powerbi-page-layouts — Quick Reference

## Scope

This skill governs all work inside `apps/layout-studio/` and `packages/` that
support it. It covers:

1. **Visual placement and sizing** — grid-snapping, alignment, z-order, grouping
2. **Template selection** — choosing from the 12 Honasa report templates
3. **Schema compliance** — `SCHEMA_VERSION='1.0.0'`, Zod validation, `_raw` field rejection
4. **Accessibility** — every visual needs `accessibilityLabel`; status never communicated by colour alone
5. **Export specification** — JSON layout export only; no PBIX/PBIR produced
6. **Production readiness** — validation panel is green (0 errors) before export

## Non-negotiable constraints

| # | Constraint |
|---|---|
| C1 | Do NOT convert `dashboard/` to React |
| C2 | Do NOT modify Primary/Offtake/CM2/P&L/forecast/FY calculations |
| C3 | THE ONE FY RULE: Apr-Dec of year Y → FY(Y+1); Jan-Mar of year Y → FY(Y) |
| C4 | CM2 Provisional banner must remain locked, z-index 10, amber background `#FEF3C7` |
| C5 | Phase 10 AI generation: never accept browser-pasted provider keys; no localStorage secrets |
| C6 | Secret patterns that must never appear in exports: `sk-[A-Za-z0-9]{20,}` / `ghp_[A-Za-z0-9]{36}` / `Bearer\s+[A-Za-z0-9+/=]{20,}` |
| C7 | All 177 Python tests must remain green |

## Canvas presets

| Preset | Width | Height |
|--------|-------|--------|
| Power BI Desktop (default) | 1280 px | 720 px |
| Power BI Mobile | 360 px | 800 px |
| Wide / Dashboard | 1920 px | 1080 px |

Grid default: 10 px; snap-to-grid on by default.

## Available templates (12)

`executive-overview`, `primary-sales`, `offtake-sales`, `primary-vs-offtake`,
`performance-comparison`, `category-pack`, `forecast`, `distribution`, `pandl`,
`cm2-provisional` ⚠, `data-qc-reconciliation`, `insights-actions`

**`cm2-provisional`** always adds a mandatory locked amber warning banner — do not remove it.

## Visual types (17)

kpi-card, text, image-placeholder, bar-chart, column-chart, line-chart, combo-chart,
pie-chart, donut-chart, table, matrix, slicer, gauge, funnel, treemap,
decomposition-tree-placeholder, map-placeholder

Last two are placeholder types requiring Power BI Desktop to instantiate.

## Validation rules (validatePage)

- Missing `accessibilityLabel` → warning
- Negative coordinates → error
- Visual exceeds canvas boundary → warning
- Chart/KPI visual with no measure → error
- Placeholder visual type → info
- >10% area overlap between two visuals → warning

## Key file paths

```
apps/layout-studio/src/
  store/editorStore.ts      — Zustand editor state (MAX_HISTORY=100)
  utils/validation.ts       — validatePage()
  utils/export.ts           — exportLayoutJSON(), assertNoSecrets()
  utils/autosave.ts         — scheduleAutosave() debounce=2000ms
  components/Canvas/        — Canvas.tsx + CanvasVisual.tsx
  components/common/        — VisualPreview.tsx
  components/Toolbar/       — Toolbar.tsx
  components/PropertiesPanel/ — PropertiesPanel.tsx
  components/VisualPicker/  — VisualPicker.tsx
  components/TemplateGallery/ — TemplateGallery.tsx
  components/ValidationPanel/ — ValidationPanel.tsx
  App.tsx / main.tsx

packages/layout-schema/src/index.ts     — Zod schema, SCHEMA_VERSION='1.0.0'
packages/design-tokens/src/index.ts     — Brand tokens, Honasa teal #00A896
packages/dashboard-templates/src/index.ts — 12 DashboardTemplate entries
```

## Interaction with other skills

| Need | Route to |
|------|----------|
| PBIP/TMDL/PBIR file authoring | `pbip` plugin |
| DAX measures, Power Query M | `semantic-models` plugin |
| Report themes and accessibility audit | `reports` plugin |
| CM2 classification / provisional governance | `honasa-cm2-expense-classification` |
| Dashboard reconciliation / QC | `honasa-dashboard-qc-reconciliation` |
| Data lineage / schema validation | `honasa-data-engineering` |
| CI/CD pipeline / security testing | `run-devsecops-productivity` |
| Agent safety / prompt-injection | `run-evidence-grounded-agents` |
