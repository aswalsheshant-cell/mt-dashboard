# Data request — Nielsen and TDP monthly feeds

**Raised:** 16 Aug 2026 · **Owner:** MT Channel Analyst Lead
**Background:** `docs/ANALYTICS_EXTERNAL_DATA_PLAYBOOK.html`

Both feeds are already modelled in Power BI and both folders are empty. Supplying these
files switches on twelve measures that already exist — no development work is needed on
our side. Column names below match the committed templates exactly, so a supplied file
drops into the watch folder and refreshes with no mapping.

---

## 1 — TDP / distribution monthly  (highest value)

**Drop into:** `PowerBI/RawDataFolders/TDP_Monthly/`
**Name as:** `TDP_<Mon>_<YY>.csv` — e.g. `TDP_Jul_26.csv`
**Template:** `_TEMPLATE_TDP_Monthly.csv` (committed, do not rename columns)

| Column | Notes |
|---|---|
| `Month` | `Jul'26` format |
| `FY Year` | `26-27` |
| `Chain` | must match `SeedData/Masters/ChainMaster.csv` |
| `Zone`, `State` | our zone naming, not Nielsen regions |
| `Brand`, `Category`, `Sub-category`, `Pack Size` | |
| `Article Code`, `Article Description` | match `ArticleMaster.csv` where possible |
| `ACV %` | all-commodity volume reach of the SKU |
| `AIC` | average items carried |
| **`Numeric Distribution`** | **the critical missing field** — outlets stocking us ÷ outlets stocking the category |
| `Weighted Distribution` | we currently see this only inside PowerPoint slides |
| `Data Source Name` | e.g. `Nielsen RMS` |

**Switches on:** `TDP`, `ACV %`, `AIC`, `Numeric Distribution`, `Weighted Distribution`,
`Sales per TDP`, `Offtake per TDP`, `Primary per TDP`, `TDP MoM/YoY Growth %`,
`Growth Driver` (distribution-led vs velocity-led), `TDP Opportunity Quadrant`,
`MS vs TDP Index` — all already written in `PowerBI/DAX/05_TDP_Measures.dax`.

**Why Numeric Distribution specifically.** Weighted distribution alone cannot tell us
whether 89.0% means "in most stores" or "in a few very large stores". The ratio
`WtD ÷ ND` separates those, and they call for opposite actions. A live recommendation
in the July pack — hold shampoo pack expansion because 81.5% WtD looks like enough
shelf — rests on a term we currently cannot see.

**Minimum useful version:** if the full article grain is hard, brand × category ×
month at national level still completes the decomposition. Article grain would let us
run the opportunity quadrant.

---

## 2 — Nielsen market share monthly

**Drop into:** `PowerBI/RawDataFolders/Nielsen_Monthly/`
**Name as:** `Nielsen_<Mon>_<YY>.csv`
**Template:** `_TEMPLATE_Nielsen_Monthly.csv`

| Column | Notes |
|---|---|
| `Month`, `FY Year` | as above |
| `Nielsen Category` | e.g. `Facewash`, `Shampoo` |
| `Brand` | **including competitors** — see `SeedData/Masters/NielsenCompetitorMaster.csv` |
| `Zone` | `Pan India` acceptable if zone splits are unavailable |
| `Market Value Sales`, `Our Brand Sales` | absolute values, so share can be re-derived and checked |
| `Value Market Share %` | |
| **`Volume Market Share %`** | **never yet supplied in any form** |
| `Data Source Name` | e.g. `Nielsen MS Val Urban` — state the panel |

**Switches on:** `Market Share %`, `Market Share Volume %`, `Market Share BPS Change`,
`Market Share YoY BPS`, `Category Value Growth %`, `Our Brand Growth %`,
`Share Gain Flag` — already written in `PowerBI/DAX/04_Nielsen_Measures.dax`.

**Why volume share specifically.** Value share rising while volume share is flat means
we are taking share on price or mix, not on demand. That distinction cannot be made from
value alone, and it changes whether a share gain is worth scaling investment behind.
Competitor rows matter as much as ours — without them we cannot attribute a share gain
to whoever lost it.

---

## 3 — June 2026 offtake month file

**Drop into:** `PowerBI/RawDataFolders/Offtake_Monthly/`
**Name as:** `offtake_store_article_Jun_26.csv` — same layout as the Apr / May / Jul files
already present.

Apr, May and Jul are in place; June is missing. Every Q1 series we produce currently
either skips June or derives it. With the file, the Q1 units and price/volume analysis
covers the full quarter on measured data.

---

## Cadence and quality

- **Monthly**, in line with the Nielsen release, is enough. Historical months welcome —
  a 12-month back-file would let us report YoY on every measure immediately.
- Send **as delivered**. Do not pre-aggregate, round, or drop competitor rows;
  `sales-data-reconciliation` profiles the file on arrival and reports anomalies back.
- Nielsen periods lag and cover a different universe from internal offtake. We will never
  reconcile a Nielsen figure to an internal one or present the difference as an error —
  external data is used for relative position and trend only.
- Every figure derived from these feeds will carry its period and panel on the slide.

## What we will publish once fed

1. Share decomposed into reach × store quality × velocity, by brand and category.
2. Value-vs-volume divergence, flagging any share gain that is price-bought.
3. The distribution-led vs velocity-led growth driver per chain — settling whether growth
   came from more shelf or better shelf.
4. A share-gain check against category growth, rather than reporting our growth alone.
