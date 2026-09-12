# Layout Contract — Versioned Layout Specification

A layout specification is a machine-readable, human-reviewable document that
describes a Power BI page design. It is **not** a PBIX file, a PBIR project,
or a semantic model. It contains no executable code.

---

## Top-level fields

```
schemaVersion    string   — must match SCHEMA_VERSION constant (currently '1.0.0')
projectId        string   — alphanumeric + hyphens; stable across sessions
projectName      string   — human-readable report name
pages            Page[]   — 1..50 pages
theme            string   — e.g. 'honasa-teal' (default)
author           string?  — designer name
source           string?  — originating tool or session
createdAt        string   — ISO 8601 datetime
updatedAt        string   — ISO 8601 datetime
```

---

## Page fields

```
id               string   — unique within layout; stable
name             string   — 1..100 chars
pagePurpose      string?  — one-sentence analytical question this page answers
audience         string?  — intended reader (e.g. 'Regional Sales Manager')
canvas:
  width          number   — pixels
  height         number   — pixels
  unit           'px'|'mm'|'in'
background:
  color          string   — CSS hex or named colour
  imageUrl       string?  — background image (optional)
  imageTransparency number — 0–100
gridSize         number   — 1..100 px (default 10)
snapToGrid       boolean
mobileLayout     boolean
safeMargin       number?  — minimum distance from canvas edge (default 20 px)
visuals          Visual[]
groups           VisualGroup[]
filters          Filter[]
```

### Recommended canvas defaults (when the repository does not specify otherwise)

| Preset | Width | Height | Grid | Safe margin |
|--------|-------|--------|------|-------------|
| Desktop (16:9) | 1280 px | 720 px | 10 px | 20 px |
| Wide | 1920 px | 1080 px | 20 px | 20 px |
| Mobile | 360 px | 800 px | 10 px | 10 px |

These are recommendations. If the repository defines other values, use those.

---

## Visual fields

```
id               string   — /^[a-zA-Z0-9_-]+$/, unique within page, stable
type             VisualType
title            string
subtitle         string?
x                number   — ≥0
y                number   — ≥0
width            number   — ≥10
height           number   — ≥10
zIndex           number   — 0..9999
locked           boolean
hidden           boolean
groupId          string?
measures         Binding[]
categories       Binding[]
series           Binding[]
filters          Filter[]
sort             Sort?
interactions     Interaction
tooltip          Tooltip
drillthrough     Drillthrough
style            Formatting
accessibilityLabel string  — required; must be meaningful (not just the title)
mobileOverride   MobileOverride?
```

### Recommended layout positions (Honasa standard page)

```
KPI strip:    y ≈ 20–130 px, KPI cards stacked horizontally from x=20
Slicer rail:  x ≈ 10–170 px, slicers stacked vertically from y=140
Chart area:   x ≥ 190 px (after slicer rail)
Table/matrix: full-width below charts, y ≈ 420+ px
```

These are starting points. Adjust to the actual content and canvas size.

---

## Binding

```
field          string   — DAX measure or dimension field name
table          string?  — source table
aggregation    'sum'|'avg'|'count'|'min'|'max'|'none'
displayName    string?  — label shown in visual header
```

---

## Filter

```
field          string
table          string?
operator       'eq'|'neq'|'gt'|'gte'|'lt'|'lte'|'in'|'notIn'|'contains'|'all'
values         (string|number|boolean)[]
```

---

## Interaction

```
filterTargets          string[]   — visual IDs this visual filters
highlightTargets       string[]   — visual IDs this visual highlights
drillthroughEnabled    boolean
crossFilterEnabled     boolean    — default true
```

---

## Tooltip

```
enabled        boolean   — default true
fields         Binding[]
reportPage     string?   — tooltip page name in Power BI
```

---

## Drillthrough

```
enabled        boolean   — default false
targetPage     string?   — page name to drillthrough to
passFilters    string[]  — filter fields to pass through
```

---

## MobileOverride

```
hidden         boolean
x              number?
y              number?
width          number?
height         number?
order          number?   — reading order for linearised mobile layout
```

---

## VisualGroup

```
id             string
name           string
visualIds      string[]  — must all exist in the same page
```

---

## Requirements

- **Stable IDs**: visual and page IDs must not change between versions of the same specification.
- **Explicit schema version**: schemaVersion must appear in every exported document.
- **Runtime validation**: all imports must pass schema validation before display.
- **Deterministic serialisation**: same logical layout → same JSON when round-tripped.
- **No executable content**: layout JSON must contain no JavaScript, SQL, DAX, HTML, or shell commands.
- **Safe import rejection**: unknown keys in strict sections must be rejected.
- **Missing-data behaviour**: if a required field is absent, surface an error — do not substitute fabricated data.
- **Migration guidance**: when schemaVersion increments, include a migration function and document the changes.
- **Secret rejection**: any export containing `sk-[A-Za-z0-9]{20,}`, `ghp_[A-Za-z0-9]{36}`, or `Bearer\s+[A-Za-z0-9+/=]{20,}` must be blocked.

---

## Required data fields

Each page specification should list `requiredDataFields` — the DAX measures,
dimension fields, and source tables that the visuals depend on. If any field
is unavailable at implementation time, the handoff document must flag it
explicitly. Never substitute invented values.

---

## Schema migration

When `schemaVersion` changes:
1. Define a migration function `migrate_x_to_y(layout)`.
2. Register it in `MIGRATION_REGISTRY`.
3. `importLayout()` calls `migrateLayout()` before validation.
4. Document breaking changes in the commit message and handoff guide.
