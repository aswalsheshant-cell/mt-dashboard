# Layout Guidelines — Power BI Page Design

## 1. Canvas and grid

- Default canvas: 1280 × 720 px (Power BI Desktop 16:9).
- Grid size: 10 px; snap-to-grid enabled by default.
- Safe margin: keep at least 20 px from canvas edges for all visuals.
- Group related KPIs in a horizontal strip at the top (y ≈ 20–130 px).
- Place filter slicers on the left rail (x ≈ 10–170 px) or top strip.

## 2. Visual hierarchy

| Layer | Z-range | Content |
|-------|---------|---------|
| Background | 0–9 | Background shapes, watermarks |
| Content | 10–99 | Charts, tables, matrices |
| Overlays | 100–199 | Slicers, KPI cards |
| Alerts | 1000+ | Validation banners (e.g. CM2 Provisional) |

Never place interactive slicers below z-index 100 — Power BI renders them in DOM order and overlapping may hide the hit area.

## 3. KPI strip (top of page)

Recommended layout for a standard Honasa executive page:

```
x=20,  y=20 → KPI: Primary RSP (₹ Cr)       220×100
x=260, y=20 → KPI: Offtake RSP (₹ Cr)       220×100
x=500, y=20 → KPI: Primary vs LY             220×100
x=740, y=20 → KPI: Offtake vs LY             220×100
x=980, y=20 → KPI: CM2 %                     220×100
```

## 4. Filter slicer rail

Recommended left-side placement for consistent UX:

```
x=10, y=140 → Brand slicer    160×200
x=10, y=360 → Channel slicer  160×180
x=10, y=560 → FY slicer       160×140
```

## 5. Chart area

Main chart area starts at x ≈ 190 px after the slicer rail. Typical grid:

- Half-width chart: 520×280 px
- Full-width chart: 1070×300 px
- Table/matrix: 1070×320 px (spans full width below charts)

## 6. Accessibility checklist

Every visual MUST have:
- [ ] `accessibilityLabel` — meaningful description (not just the visual title)
- [ ] `title` — brief display name
- [ ] Colour choices from `tokens.color.chart1–8` (WCAG-distinguishable)
- [ ] Avoid conveying meaning by colour alone — use patterns or labels

## 7. Mobile layout

When `isMobilePreview` is on:
- Apply `mobileOverride.{x,y,width,height}` to reposition for 360×800 viewport.
- Hide decorative visuals with `mobileOverride.hidden = true`.
- Use `mobileOverride.order` to linearise the reading order.

## 8. Template application order

1. Apply template via TemplateGallery → confirm dialog.
2. Review ValidationPanel — resolve all errors before exporting.
3. Set `accessibilityLabel` on every visual.
4. Adjust positions to suit the actual data fields being used.
5. Export JSON for handoff to Power BI Desktop implementation.
