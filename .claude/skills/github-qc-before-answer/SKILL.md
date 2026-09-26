---
name: github-qc-before-answer
description: Use before stating any Primary, Offtake, Distributor Secondary, conversion or chain-level sales figure in chat, a PPT or an email. Fetches the number from dashboard/data.js or scripts/data/july_mt_chart_series.json on main in the same turn, labels it QC VERIFIED or NOT IN REPO, and names the missing source file instead of estimating.
---

# GitHub QC — Mandatory Repository Check Before Answering

**Trigger:** Any question about a sales number, primary, offtake, conversion, chain
performance, or any figure that could come from the dashboard data must run this QC
before stating an answer. **No number leaves this skill unverified.**

---

## Rule 1 — Block, then verify

Never state a primary, offtake, or conversion figure from memory or a previous turn
without first completing the data fetch below. If the fetch fails, say so and name the
exact file needed rather than guessing.

---

## QC sequence (run in this order, in parallel where possible)

### Step 1 — Fetch the validated monthly series

**File:** `scripts/data/july_mt_chart_series.json` on `main`

```
mcp__github__get_file_contents(
  owner="aswalsheshant-cell", repo="mt-dashboard",
  path="scripts/data/july_mt_chart_series.json",
  ref="refs/heads/main"
)
```

This gives **exact** Jul-26 primary and offtake by chain (slide 16 / chart22):
- Reliance Primary Jul-26, DMart Primary Jul-26, Apollo Primary Jul-26, etc.

### Step 2 — Fetch annual chain totals

**File:** `dashboard/data.js` on `main` — extract the `primary.by_chain` block
and `detail_meta.fyx_primary.FY27.by_chain`.

Use local file if already cloned (parse the JSON — a plain text search for
`"by_chain"` finds an earlier block, not `primary.by_chain`):
```bash
python3 -c "
import json
t = open('dashboard/data.js').read()
d = json.loads(t[t.index('{'):t.rindex('}')+1])
print([c for c in d['primary']['by_chain'] if 'Reliance' in c['name']])             # FY26 annual (Rs Lac)
print([c for c in d['detail_meta']['fyx_primary']['FY27']['by_chain'] if 'Reliance' in c['name']])
print(d['detail_meta']['fyx_primary']['FY27']['months_covered'])                    # FY27 months included
"
```

This gives:
- Reliance FY26 annual primary (`primary.by_chain[].fy26`, Rs Lac)
- Reliance FY27 year-to-date primary (`detail_meta.fyx_primary.FY27.by_chain[].nsv`) —
  always state the months it covers; it grows every month, so never quote an old value
- **No FY25 primary.** `primary.fy_tags` is `['fy26']` only; FY25 has no real Primary
  extract (`docs/DATA_AVAILABILITY_MATRIX.md`). Answer FY25 with `[QC: NOT IN REPO]`.

### Step 3 — Fetch monthly offtake (Reliance BC series)

Extract `reliance_bc.monthly` (with `reliance_bc.months`) from `dashboard/data.js`. This
is the Reliance **brand-counter** (staffed door) offtake series — a partition kept for
audit, not total Reliance offtake. Never add it to Reliance offtake or subtract it from
Reliance primary (CLAUDE.md, Reliance Brand Counter deduplication safeguard).

```bash
python3 -c "
import json
t = open('dashboard/data.js').read()
bc = json.loads(t[t.index('{'):t.rindex('}')+1])['reliance_bc']
print(list(zip(bc['months'], bc['monthly'])))
"
```

### Step 4 — State branch coverage

Report which branches were checked and confirm `main` is the source of the answer.
If a question references LY months not covered by monthly data, say so explicitly
rather than estimating.

---

## What is and is not in the repository

Values change with every monthly build, so this table lists **where** each figure lives,
not the figure. Fetch it in the current turn.

| Data point | Available? | Source |
|---|---|---|
| Reliance Primary FY25 annual | ❌ No real source (FY25 has Distributor Secondary only) | `docs/DATA_AVAILABILITY_MATRIX.md` |
| Reliance Primary FY26 annual | ✅ | `primary.by_chain[].fy26` |
| Reliance Primary FY27 year-to-date | ✅ (state months covered) | `detail_meta.fyx_primary.FY27.by_chain` |
| Reliance Primary Jul-26 (monthly) | ✅ | `july_mt_chart_series.json` |
| Reliance Primary FY26 monthly (Apr-25 → Mar-26) | ✅ Full series validated | `Primary_ShipTo_FY25-26_to_May26.csv` |
| National Primary monthly FY26 | ✅ Full series | `primary.monthly_fy26` |
| Reliance brand-counter offtake monthly | ✅ Partition only | `reliance_bc.monthly` |
| Total Reliance Offtake Jul-26 | ✅ | `july_mt_chart_series.json` |

### Step 2b — Reliance Primary FY26 monthly (closed year; reconciled to ₹83.49 Cr annual)

FY26 is closed, so this table is a **check value**: if a fresh fetch differs, report the
difference — do not quote this table over the fetched number.

Source: `PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY25-26_to_May26.csv`
Chain tag: `Reliance Retail` (includes Direct + Distributor-allocated)

| Month | ₹ Lac | ₹ Cr |
|---|---|---|
| Apr-25 | 1093.17 | 10.93 |
| May-25 | 600.99 | 6.01 |
| Jun-25 | 442.73 | 4.43 |
| Jul-25 | 667.85 | 6.68 |
| Aug-25 | 542.27 | 5.42 |
| Sep-25 | 318.02 | 3.18 |
| Oct-25 | 781.50 | 7.82 |
| Nov-25 | 795.11 | 7.95 |
| Dec-25 | 745.23 | 7.45 |
| Jan-26 | 1317.77 | 13.18 |
| Feb-26 | 344.88 | 3.45 |
| Mar-26 | 699.38 | 6.99 |
| **FY26 Total** | **8348.90** | **83.49** |

FY27 months are not listed here — they change as each month is loaded. Fetch them from
`detail_meta.fyx_primary.FY27.monthly` (national) or the article CSVs in
`PowerBI/RawDataFolders/Primary_Article_Monthly/`.

---

## Output format

After completing the QC, present findings as:

```
[QC VERIFIED — source: <file name on main branch>]
Reliance Primary <month>: ₹<value fetched this turn> Cr
Source: <file> → <key or slide/chart>
```

For any figure the QC cannot locate, write:

```
[QC: NOT IN REPO — Reliance Primary <month>: no monthly chain-level data stored]
Available: <what the repo does hold, fetched this turn>
Required file to get monthly: Primary source workbook (e.g. MT_Primary_FY26.xlsb)
```

---

## Mandatory guardrails

- **Never estimate** a chain-level figure from a national total without labelling it
  explicitly as `(est. — derived from national share, not chain-level data)`.
- **Never reuse** a figure from a prior conversation turn without re-fetching it from
  the repo in the current turn.
- If the requested metric does not exist in any branch, **stop and name the exact
  source file** the user must supply (e.g. `MT_Primary_FY26_MonthlyByChain.xlsb`).
- For PPT edits: only write a number to a slide after it appears in the QC output
  above as `[QC VERIFIED]`. A `[QC: NOT IN REPO]` number must be labelled `(est.)` on
  the slide or omitted entirely.
