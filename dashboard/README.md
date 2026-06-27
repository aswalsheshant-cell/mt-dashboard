# MT Leadership Dashboard

A self-contained, interactive dashboard for **Honasa / Mamaearth Modern Trade (MT)**
covering Primary, Offtake, chain-wise P&L, Forecast, Market Share and data-driven
Insights / Way Forward.

## Open it

Open `dashboard/index.html` in any modern browser — no server or internet needed.
Chart.js is vendored locally (`chart.umd.js`) and all data is baked into `data.js`,
so the dashboard works fully offline.

## Tabs

| Tab | What it shows |
|-----|---------------|
| **Overview** | Headline KPIs, Primary-vs-Offtake monthly trend, channel split, top chains, brand mix |
| **Primary** | Sell-in NSV (FY24-25 vs FY25-26) by month, zone, channel, brand and chain (with YoY) |
| **Offtake** | Sell-out trend, zone & state YoY, and a Primary-vs-Offtake inventory-health view by chain |
| **P&L** | Chain-wise gross MRP → net NSV bridge, trade-discount intensity, and promo activity |
| **Forecast** | Seasonally-indexed FY26-27 offtake projection with the method stated |
| **Market Share** | Distribution footprint (store universe) and share-of-business across MT chains |
| **Insights & Way Forward** | Auto-generated risks/opportunities plus prioritised leadership actions |

## Data sources

Built from the Honasa MT working files (FY24-26), kept in Google Drive (not committed):

- **Primary FY-2024-26.xlsx** — row-level primary sell-in (NSV, MRP, chain, brand, zone, channel)
- **Chain Offtake Master File State Wise FY 24-26.xlsx** — chain-wise & zone/state offtake pivots
- **Universe MT.xlsx** — MT store universe (distribution footprint)
- **Promo Master -MT.xlsx** — promo / trade-spend calendar

All monetary values are **INR Lakh** in the data and displayed as **INR Crore** (Cr = Lakh / 100)
where labelled.

## Rebuilding `data.js`

```bash
pip install pandas openpyxl
# place the four source workbooks (+ the offtake text dump 'offtake_flat.txt') in <src>
python scripts/build_dashboard_data.py --src <src> --out dashboard/data.js
```

`scripts/build_dashboard_data.py` normalises chain/brand/zone spellings across the four
files onto a common key, aggregates every view, derives the P&L bridge and forecast, and
emits `window.DASH` into `data.js`.

## Assumptions & caveats

- **P&L** uses real Primary data for the gross **MRP → net NSV** bridge. COGS is not in the
  source, so this is a **gross-to-net trade contribution** view (retail margin + taxes + trade
  terms), not a full statutory P&L.
- **Market share** is **internal share-of-business + distribution reach**; external category
  share vs competitors is not in the source data.
- **Forecast** is directional for planning (seasonally-indexed run-rate at the realised offtake
  YoY rate, clamped to 0-60%), not a financial commitment. Refresh monthly as actuals land.
