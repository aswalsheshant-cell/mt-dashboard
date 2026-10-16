# Four types of analytics: where each one lives in this project

Descriptive = what happened. Diagnostic = why. Predictive = what could happen next. Prescriptive = what should we do.
This map shows what the project already has for each type, what was missing, and what is still blocked. Checked 2026-10-16.

| Type | What exists today | Where | Gap found | Status |
|---|---|---|---|---|
| Descriptive | NSV, growth, MoM, YoY, contribution %, chain / brand / category / zone cuts for Primary, Offtake and Distributor Secondary | Executive Cockpit, Channel & Chain Performance, Data Explorer, P&L | None | COVERED |
| Diagnostic | Primary vs Offtake gap by chain, gross-to-net bridge, CM2 by chain, Nielsen price / volume split, store LFL / NFL, ND / WD distribution gaps, promo depth | Channel & Chain, Inventory & Supply Health, P&L, Demand & S&OP | No single place that says why a chain moved. Pieces exist, the reader has to join them | PARTIAL |
| Predictive | FY27 forecast and target, run rate vs required run rate, forecast accuracy (WMAPE, bias), DOI watchlist | Executive Cockpit, Demand & S&OP, Inventory & Supply Health | No next-month projection by chain. Needs agreed method and enough monthly history (Offtake store level starts Apr'26) | PARTIAL |
| Prescriptive | Fixed "Recommended Actions" text (not tied to numbers) | Executive Cockpit | Actions were not driven by data, had no owner or timeline | FIXED in this change |

## Added in this change
- **"What should we do: priority actions"** card on the Executive Cockpit (`sjActionsCard()` in `dashboard/index.html`).
  Rules are shown on screen next to each action:
  1. Primary ÷ Offtake ≥ 1.15 and gap ≥ ₹100 L: check stock cover, hold or trim the next order.
  2. Primary ÷ Offtake ≤ 0.85 and gap ≤ −₹100 L: check fill rate and open POs.
  3. Largest indicative NSV from missing store × focus-article lines: get the lines listed (a ceiling, not a forecast).
  4. Break-even uplift ≥ 100% at 50% funding: confirm funding share with Finance, review depth.
  Each line has an owner role and a timeline. Fixed period FY27 YTD. No new data source; uses `primary_offtake_gap` and `dashboard/sj_kpis.js`.

## Still not possible (named, not invented)
- Why a chain moved, as one driver tree (volume, price, mix, distribution): needs a decision on method; Nielsen price / volume exists for market data only.
- Next-month projection by chain: needs agreed method and owner sign-off; Primary and Offtake are separate measures and must not share one growth rate.
- Optimisation or simulation (the stronger sense of prescriptive): needs promotion spend, funding share and cost heads that no source file has yet.

## Rules that stay in force
Primary, Distributor Secondary and Offtake are never mixed in one growth rate. Reliance Brand Counter is excluded from Offtake only. Missing numbers show "–", never 0.
