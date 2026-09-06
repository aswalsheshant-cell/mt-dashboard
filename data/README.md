# Nielsen Data Schema

Monthly JSON files for the Market Share Intelligence Dashboard.

## File naming

```
data/nielsen_<mon><yy>.json    e.g. data/nielsen_aug26.json
```

Pushing a new file to `main` triggers **Build Nielsen Dashboard** automatically
and creates a versioned GitHub Release with the compiled HTML attached.

---

## Required top-level keys

| Key | Type | Description |
|-----|------|-------------|
| `reporting_period` | string | Human label shown in dashboard meta — e.g. `"August 2026"` |
| `months` | string[] | 16 month labels, rolling window, newest last — e.g. `["May 25", … , "Aug 26"]` |
| `ms` | number[] | Market share % — same length as `months` |
| `nsv` | number[] | Net Sales Value ₹ Cr — same length as `months` |
| `wd` | number[] | Weighted Distribution % — same length as `months` |
| `stores` | number[] | Stores selling (integer) — same length as `months` |
| `brands` | object[] | Competitive landscape — see **Brand object** below |
| `fw_packs` | object[] | Facewash pack-size split — see **Pack object** below |
| `sh_packs` | object[] | Shampoo pack-size split — see **Pack object** below |
| `aug_actions` | object[] | Phase 1 tracker items — see **Action object** below |
| `sep_actions` | object[] | Phase 2 tracker items |
| `gates` | object[] | Decision gates — see **Gate object** below |

> `aug_actions`, `sep_actions`, and `gates` are optional (default to empty arrays).

---

## Object shapes

### Brand object
```json
{
  "n":      "Himalaya",   // display name
  "nsv":    18.7,         // NSV ₹ Cr for the reporting month
  "ms":     22.8,         // market share % for the reporting month
  "pp":     -0.4,         // pp change YoY (positive = gain)
  "yoy":    13.9,         // NSV growth % YoY
  "stores": 20376,        // stores selling (integer)
  "wd":     99.5,         // weighted distribution %
  "pdo":    9177          // per-door output ₹ (integer)
}
```

### Pack object
```json
{
  "sz":  "50–75ml",   // size label shown on bars / donut
  "val": 38.4,        // % share of category NSV  (all packs must sum ~100%)
  "yoy": 14.2,        // % change YoY
  "clr": "#2563EB"    // hex colour for the bar / donut slice
}
```

### Action object (tracker items)
```json
{
  "title":  "Hero-EAN OSA Audit — All Chains",
  "owner":  "NKAM · Dist team",
  "budget": "₹0 (ops)",      // use "—" if no spend
  "due":    "Aug 15",
  "desc":   "Short description shown below the title"
}
```

### Gate object
```json
{
  "date":   "Sep 30",
  "q":      "NSV run-rate ≥ ₹10 Cr — confirm #3 position target",
  "impact": "Re-forecast FY27 to ₹115 Cr+"
}
```

---

## Validation rules (enforced by build script)

| Check | Rule |
|-------|------|
| Series length | `months`, `ms`, `nsv`, `wd`, `stores` must all have the same length |
| Pack mix | `fw_packs[*].val` sum must be 98–102% |
| Pack mix | `sh_packs[*].val` sum must be 98–102% |
| Brand MS | Sum of all `brands[*].ms` must be ≤ 100% |

Warnings print to the CI log; missing required keys abort the build.

---

## Monthly workflow

```bash
# 1. Export from Nielsen Retail Intelligence portal → save as JSON
#    matching the schema above (16-month rolling window, shift oldest off)

# 2. Drop the file in and push
cp ~/Downloads/nielsen_aug26.json data/nielsen_aug26.json
git add data/nielsen_aug26.json
git commit -m "data: add Nielsen Aug 26 market share extract"
git push

# → GitHub Actions triggers automatically
# → dist/Nielsen_MS_Dashboard_AUG26.html built and validated
# → Release created at github.com/<org>/mt-dashboard/releases
#    with HTML attached for stakeholder download
```

## Colour palette reference (fw_packs / sh_packs)

| Pack tier | Facewash hex | Shampoo hex |
|-----------|-------------|-------------|
| Smallest  | `#60A5FA`   | `#6EE7B7`   |
| Mid-low   | `#2563EB`   | `#10B981`   |
| Mid-high  | `#1D4ED8`   | `#059669`   |
| Largest   | `#1E40AF`   | `#047857`   |
