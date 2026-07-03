# SIS Reconciliation (Channel tag) — fixing "Primary SIS 250 vs 236"

## Root cause
The store×article **offtake** file has **no Channel column**, so SIS on the
offtake/derived side is inferred and can over/under-count. The **primary File 2**
(`Fact Primary Article`) *does* carry an explicit `Channel` (MT / EB2B / SIS) —
that is the **source of truth**. The HTML dashboard already shows the correct
**Primary SIS = ₹236 L**; a **₹250 L** reading comes from an SIS total not sourced
from File 2's explicit Channel (or double counting).

## Fix
1. **Channel maps** (editable): `ChannelMap_Store.csv` (Store/Site-code overrides,
   e.g. SIS shop-in-shop codes) and `ChannelMap_Chain.csv` (default channel per
   chain). Loaded by `PowerQuery/24_ChannelMap.pq`.
2. **`Offtake Channel`** calculated column (`DAX/10`): Store Code override →
   Chain default → **"Unmapped"** (never dropped).
3. **Single SIS definition:** use `[Primary SIS]` (File 2 explicit Channel)
   everywhere; do **not** derive SIS from the ship-to primary (File 1 is MT-only).

## Reconciliation (DAX 10)
| Measure | Meaning |
|---|---|
| `Primary SIS` / `Primary SIS (Cr)` | SIS from File 2 explicit Channel (truth) — expect ≈ ₹2.36 Cr |
| `Offtake SIS` / `Offtake SIS (Cr)` | SIS from derived `Offtake Channel` |
| `SIS Variance` / `(Lacs)` | Primary SIS − Offtake SIS |
| `SIS Match` | OK if |variance| < ₹1 L else "Gap - investigate" |
| `Offtake Channel Coverage %` | share of offtake resolved to a real channel (rest = Unmapped) |

**To locate the ₹14 L:** table visual with rows = `Chain`, values =
`Primary SIS (Cr)`, `Offtake SIS (Cr)`, `SIS Variance (Lacs)`, sorted by variance.
Slice `Offtake Channel = "Unmapped"` to list Store(Site) codes whose channel didn't
resolve — add those to `ChannelMap_Store.csv` and refresh; the gap closes as
coverage → 100%.
