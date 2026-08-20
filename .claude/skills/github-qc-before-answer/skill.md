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

Use local file if already cloned:
```bash
python3 -c "
import re
with open('dashboard/data.js') as f:
    c = f.read()
# primary.by_chain
idx = c.find('\"by_chain\"')
print(c[idx:idx+2000])
# detail_meta FY27 chain totals
idx2 = c.find('fyx_primary')
print(c[idx2:idx2+3000])
"
```

This gives:
- Reliance FY25 annual primary, FY26 annual primary
- Reliance FY27 Apr–Jul 26 combined primary (₹47.53 Cr as of Jul-26 build)

### Step 3 — Fetch monthly offtake (Reliance BC series)

Extract `reliance_bc.monthly` from `dashboard/data.js`. This gives month-by-month
Reliance brand-counter offtake from Jan-24 to the latest month.

```bash
python3 -c "
with open('dashboard/data.js') as f:
    c = f.read()
idx = c.find('reliance_bc')
print(c[idx:idx+2000])
"
```

### Step 4 — State branch coverage

Report which branches were checked and confirm `main` is the source of the answer.
If a question references LY months not covered by monthly data, say so explicitly
rather than estimating.

---

## What is and is not in the repository (as of Jul-26 build)

| Data point | Available? | Source |
|---|---|---|
| Reliance Primary FY25 annual | ✅ ₹64.43 Cr | `primary.by_chain` |
| Reliance Primary FY26 annual | ✅ ₹83.49 Cr | `primary.by_chain` |
| Reliance Primary FY27 Apr–Jul 26 | ✅ ₹47.53 Cr | `detail_meta.fyx_primary` |
| Reliance Primary Jul-26 (monthly) | ✅ ₹15.66 Cr | `july_mt_chart_series.json` |
| Reliance Primary FY26 monthly (Apr-25 → Mar-26) | ✅ Full series validated | `Primary_ShipTo_FY25-26_to_May26.csv` |
| National Primary monthly FY26 | ✅ Full series | `primary.monthly_fy26` |
| Reliance Offtake monthly Jan-24 → latest | ✅ Brand-counter series | `reliance_bc.monthly` |
| Total Reliance Offtake Jul-26 | ✅ ₹8.06 Cr | `july_mt_chart_series.json` |

### Step 2b — Reliance Primary FY26 Monthly (validated, reconciled to ₹83.49 Cr annual)

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

FY27 partial (same source):

| Month | ₹ Lac | ₹ Cr |
|---|---|---|
| Apr-26 | 1063.36 | 10.63 |
| May-26 | 1007.66 | 10.08 |
| Jun-26 | n/a (use article CSVs: ₹893.67 Lac / ₹8.94 Cr) | — |
| Jul-26 | ₹15.66 Cr (use `july_mt_chart_series.json`) | validated |

---

## Output format

After completing the QC, present findings as:

```
[QC VERIFIED — source: <file name on main branch>]
Reliance Primary Jul-26: ₹15.66 Cr
Source: july_mt_chart_series.json → slide16/chart22
```

For any figure the QC cannot locate, write:

```
[QC: NOT IN REPO — Reliance Primary <month>: no monthly chain-level data stored]
Available: FY annual total only (FY26 = ₹83.49 Cr)
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
