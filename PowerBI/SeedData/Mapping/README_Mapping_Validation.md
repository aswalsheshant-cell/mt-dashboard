# Chain–Account Mapping Validation

Two files:

- **`ChainAccount_Mapping_Inferred.csv`** — the full mapping (1,536 rows,
  Ship-To × Chain × Brand). The **inferred columns are reference only — do not
  edit them.** Apply your corrections in the **editable validation columns**.
- **`ChainAccount_Mapping_PriorityView.csv`** — the 276 rows that need attention
  first, tagged with a `Priority Buckets` column and sorted by severity.

## Inferred columns (read-only reference)
`Chain Name · Ship-To Name · Bill-To / Account (inferred) · Direct/Distributor ·
Brand · Month Logic · Months Covered · Month Range · Avg/Min/Max Cont% ·
Mapping Confidence · Remarks`

## Priority flag columns (Y / blank) — for filtering
| Column | Meaning | Count |
|---|---|---|
| `Pri: Low Confidence` | confidence = Low | 8 |
| `Pri: Medium Confidence` | confidence = Medium | 217 |
| `Pri: Multi-Chain Distributor` | distributor splits across >1 chain by secondary Cont% | 239 |
| `Pri: Negative NSV/Cont` | a negative NSV/Cont% appears — review | 8 |
| `Pri: Name Variant (Merge Candidate)` | same distributor/account under 2+ ship-to names (e.g. Az Enterprises, Chhabra Traders, Apollo Healthco) | 89 |

> Branch/DC structures (Metro 29 DCs, Avenue E-Commerce, Travel News) are
> **not** flagged as variants — they are legitimately one account with many
> ship-to points.

## Editable validation columns (you fill these)
| Column | Allowed values | Notes |
|---|---|---|
| `Validation Status` | Pending / Confirmed / Corrected / Exclude | starts at **Pending** |
| `Validated Chain` | free text | your corrected chain (blank = accept inferred) |
| `Validated Account / Bill-To` | free text | your corrected account / bill-to |
| `Mapping Action` | Keep / Merge / Split / Exclude / Needs Check | pre-defaulted: High→Keep, variants→Merge, else→Needs Check |
| `Validation Remarks` | free text | your note |
| `Validated By` | name/initials | |
| `Validated Date` | date | |

## How it flows back into the model (later)
Once you've validated, this file becomes a normal master the model reads:
a `Validated Chain`/`Validated Account` (when filled) overrides the inferred
chain at **Chain × Brand × Month** grain — no measure changes. We extend to
**Chain + Brand + Article/EAN + Month** only after you share the article-level
primary feed and sign off on this mapping.

## Suggested working order
1. `Pri: Low Confidence` + `Pri: Negative NSV/Cont` (16 rows) — data issues.
2. `Pri: Name Variant (Merge Candidate)` (89) — set `Mapping Action = Merge` and
   the `Validated Account`.
3. `Pri: Multi-Chain Distributor` (239) — confirm each distributor→chain split.
4. Remaining `Pri: Medium Confidence`.
5. High-confidence rows can be bulk-set `Validation Status = Confirmed`.
