# Export and Implementation Handoff

A layout export produces two artefacts: a **JSON specification** and a
**PDF-ready implementation guide**. Neither is a PBIX file, a PBIR project,
or a semantic model. Neither proves that underlying measures or source data
are correct.

---

## Artefact 1 — JSON Layout Specification

### Purpose
A machine-readable, version-controlled description of the page design.
Intended for import into Layout Studio or another compliant tool, and as
the authoritative design record for Power BI Desktop implementation.

### Required contents

```
schemaVersion         — must equal the current SCHEMA_VERSION constant
projectId             — stable identifier for the report
projectName           — human-readable name
pages[]               — all page definitions (see layout-contract.md)
  pageId
  pageName
  pagePurpose
  audience
  canvas (width, height, background, gridSize, safeMargin)
  visuals[]
    id, type, title, subtitle
    x, y, width, height, zIndex
    locked, hidden
    dataBindings (measures, categories, series)
    aggregation
    filters, sort
    interactions (filterTargets, highlightTargets, crossFilter, drillthrough)
    tooltip
    style (formatting)
    accessibilityLabel
    mobileOverride?
  groups[]
  filters[]
requiredDataFields    — list of all DAX measures and dimension fields needed
theme
metadata (author, createdAt, updatedAt, source)
```

### Quality requirements

- All visuals must have unique stable IDs.
- `schemaVersion` must appear at the root.
- Output must be deterministic: same logical layout → same JSON on successive exports.
- No executable JavaScript, SQL, DAX, HTML, or shell commands inside the JSON.
- Before writing the file, scan the serialised string for secret patterns:
  `sk-[A-Za-z0-9]{20,}`, `ghp_[A-Za-z0-9]{36}`, `Bearer\s+[A-Za-z0-9+/=]{20,}`.
  Abort the export if any pattern matches; notify the user.
- Validation must pass (0 errors) before export is permitted.

### File naming

`{projectName}_{pageName}_layout_v{schemaVersion}.json`

Special characters in names should be replaced with underscores.

---

## Artefact 2 — PDF-Ready Implementation Guide

### Purpose
A human-readable document for the Power BI Desktop developer who will
implement the design. Contains all information needed to recreate the
page without access to Layout Studio.

### Structure

**Cover / summary section**
- Project name
- Page name and purpose
- Intended audience
- Generation date and schema version
- Canvas dimensions and background
- Theme name and colour palette summary
- Top-level disclaimer (see below)

**Visual inventory (one entry per visual)**
- Visual type and title
- X/Y position and width × height (in pixels)
- zIndex, locked status, hidden status
- Measure and category bindings with table and aggregation
- Active filters and sort order
- Cross-filter and drillthrough settings
- Formatting instructions (font size, colours, border, padding)
- Accessibility label
- Mobile override (if applicable)
- Power BI implementation step (which visual type to use in Desktop)

**Validation summary**
- Error count (must be 0 before export)
- Warning list with severity and recommended action
- Missing data fields (fields listed in requiredDataFields but not confirmed available)

**Implementation checklist**
- [ ] Canvas size set correctly in Power BI Desktop
- [ ] Background colour and image applied
- [ ] All visuals placed at specified coordinates
- [ ] All measure bindings configured
- [ ] Conditional formatting applied where specified
- [ ] Cross-filter interactions configured (Visual Interactions panel)
- [ ] Drillthrough pages created and linked
- [ ] Slicer sync configured across pages
- [ ] Accessibility labels set in Power BI (Alt text)
- [ ] Mobile layout created in Phone Layout view
- [ ] Report published and preview verified

### Required disclaimer

Include verbatim on the cover page:

```
DESIGN SPECIFICATION ONLY

This document is a layout design specification produced in Layout Studio.
It is NOT a Power BI file (PBIX or PBIR). It does NOT contain DAX measures,
Power Query scripts, or a semantic model. It does NOT prove that the
underlying data sources are correct or complete.

CM2 figures and provisional data require Finance approval before use.
Numerical accuracy must be verified through the QC reconciliation process.
```

---

## Routing from export

| Concern | Route |
|---------|-------|
| Measures or data incorrect | `honasa-dashboard-qc-reconciliation` |
| Missing or zero chart series | `debug-dashboard-comparisons` |
| Actual PBIX/PBIR file creation | `pbip` plugin |
| DAX measure definitions | `semantic-models` plugin |
