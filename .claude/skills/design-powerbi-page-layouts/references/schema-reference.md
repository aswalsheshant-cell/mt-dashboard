# Layout Schema Reference — v1.0.0

## Root structure

```typescript
{
  schemaVersion: '1.0.0',      // literal — MUST match SCHEMA_VERSION
  projectId: string,            // alphanumeric + hyphens
  projectName: string,
  pages: Page[],                // 1..50 pages
  theme: string,                // default: 'honasa-teal'
  author?: string,
  source?: string,
  createdAt: string,            // ISO 8601 datetime
  updatedAt: string,
}
```

## Page

```typescript
{
  id: string,
  name: string,                 // 1..100 chars
  size: { width: number, height: number, unit: 'px'|'mm'|'in' },
  background: { color: string, imageUrl?: string, imageTransparency: number },
  visuals: Visual[],
  groups: VisualGroup[],
  filters: Filter[],
  gridSize: number,             // 1..100 px
  snapToGrid: boolean,
  mobileLayout: boolean,
}
```

## Visual (strict — unknown keys rejected)

```typescript
{
  id: string,                   // /^[a-zA-Z0-9_-]+$/
  type: VisualType,
  title: string,
  subtitle: string,
  x: number,   y: number,       // ≥0
  width: number, height: number, // ≥10
  zIndex: number,               // 0..9999
  locked: boolean,
  hidden: boolean,
  groupId?: string,
  measures: Binding[],
  categories: Binding[],
  series: Binding[],
  filters: Filter[],
  interactions: Interaction,
  tooltip: Tooltip,
  drillthrough: Drillthrough,
  formatting: Formatting,
  accessibilityLabel: string,
  mobileOverride?: MobileOverride,
  // _raw MUST NOT appear — schema.strict() rejects it
}
```

## VisualType enum

```
kpi-card | text | image-placeholder |
bar-chart | column-chart | line-chart | combo-chart |
pie-chart | donut-chart | table | matrix | slicer |
gauge | funnel | treemap |
decomposition-tree-placeholder | map-placeholder
```

## Binding

```typescript
{ field: string, table?: string, aggregation: 'sum'|'avg'|'count'|'min'|'max'|'none', displayName?: string }
```

## Filter

```typescript
{ field: string, table?: string, operator: 'eq'|'neq'|'gt'|'gte'|'lt'|'lte'|'in'|'notIn'|'contains'|'all', values: (string|number|boolean)[] }
```

## Formatting (selected fields)

| Field | Type | Default |
|-------|------|---------|
| `backgroundColor` | string | — |
| `borderColor` | string | — |
| `borderWidth` | 0..10 | 0 |
| `borderRadius` | 0..24 | 4 |
| `padding` | 0..40 | 8 |
| `titleVisible` | boolean | true |
| `titleFontSize` | 8..32 | 14 |
| `fontWeight` | 'normal'\|'bold'\|'600' | 'normal' |
| `legendVisible` | boolean | true |
| `legendPosition` | top\|bottom\|left\|right\|none | bottom |
| `dataLabelsVisible` | boolean | false |
| `colorPalette` | string[] | [] |

## Secret rejection patterns

Applied in both `exportLayoutJSON()` and `saveLayout()`:

```
/sk-[A-Za-z0-9]{20,}/         — OpenAI / Anthropic key
/ghp_[A-Za-z0-9]{36}/          — GitHub personal access token
/Bearer\s+[A-Za-z0-9+/=]{20,}/ — Generic Bearer token
```

Any layout containing these patterns will be rejected before save or export.
Never store provider keys in layout JSON, localStorage, or bundle files.

## Schema migration

`MIGRATION_REGISTRY` maps old schemaVersion strings to migration functions.
When schema version increments, add a migration and bump `SCHEMA_VERSION`.
`importLayout()` automatically calls `migrateLayout()` before validation.
