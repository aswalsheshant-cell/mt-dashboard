# Field parameters: level toggles (Page 5 and Page 10)

A field parameter lets one chart switch its axis from a slicer. Page 5 (Forecast) gets **Forecast Level**.
Page 10 (TDP) gets **TDP Level**. One chart replaces four or six near-copies.

## What is in the model
| Table | Levels | Drives |
|---|---|---|
| `Forecast Level` | Chain, Zone, Brand, Category | Page 5 forecast bars and table |
| `TDP Level` | Brand, Category, Sub-category, Chain, Article, Pack Size | Page 10 TDP bars and scatter |

Both are built into `model.bim` by `scripts/build_model_bim.py` (`FIELD_PARAMETERS`). Use these if you load the model with Tabular Editor.
`23_FieldParameter_Measures.dax` adds `Forecast Level Selected` and `TDP Level Selected` for chart titles.

**Held back on purpose:**
- **Sales Person** (forecast): `Sales Team Mapping` has no relationship to the facts, so the forecast would not split by it. Keep the existing Sales person bar.
- **Article** (forecast): the forecast is not allocated to article, so the total would not tie to the TY target.
- **Zone and State** (TDP): `Fact TDP` is not related to `Zone State Master`, so NSV would not follow the zone. Add that link first, then add the two rows.

## If you build it in Desktop instead (about 5 minutes each)
1. Modeling ▸ **New parameter ▸ Fields**.
2. Name it `Forecast Level` (or `TDP Level`). Tick **Add slicer to this page**.
3. Add the fields in the order of the table above. Use the columns shown in `build_model_bim.py` (for example `'Chain Master'[Chain]`, `'Zone State Master'[Zone]`).
4. Rename each row label if you want shorter text.

## Hook up the page (Desktop)
1. Page 5: drag the `Forecast Level` column (not the Fields column) to the **Axis** of the forecast bar. Keep `FY27 Forecast` as the value.
2. Page 10: drag `TDP Level` to the Axis of the TDP bar. Values stay `TDP` and `Sales per TDP`.
3. Chart title: use fx on the title and pick `Forecast Level Selected` / `TDP Level Selected`, so the title reads "FY27 Forecast by Zone".
4. Sort the visual by the value (descending), not by the level.

## Auto-expand hierarchy (October 2026 update, GA)
The model already has the `Geography` (Zone, State) and `Product` (Category, Sub-category, Brand, Article Code) hierarchies.
A field parameter can hold a hierarchy level. Add the hierarchy to the parameter, and the axis expands one level on drill, so one toggle can start at Zone and open to State.
Do this only after the plain level toggle works.

## Checks (do these once in Desktop)
| Check | Expected |
|---|---|
| Forecast Level = Chain, then Zone, then Brand, then Category | Total of the bars is the same every time and equals `TY Target (Cr)` |
| `QC Variance` on Page 5 | About 0 for all four levels |
| TDP Level = Brand, then Chain | `Sales per TDP` is not blank on any row that has TDP |
| Slicer shows 4 and 6 rows, in the order above | Yes |

If a level shows the same number on every row, that column is not related to the fact. Tell me which one and I will fix the relationship.

Status: written and checked in the repo. Not opened in Desktop from this environment.
