# August 2026 MT Pipeline — Pre-Flight Ingest Checklist

**Reporting period:** August 2026 (FY27, month 5 of Q2)  
**Target completion:** within 5 business days of August month-close  
**Validation script:** `python scripts/validation_gates.py --month Aug-26`

---

## Sequential Steps

| # | Step | Owner | Gate | Done |
|---|------|--------|------|------|
| 1 | **Collect offtake CSV** — download `offtake_store_article_Aug_26.csv` from the MT reporting portal and drop into `PowerBI/RawDataFolders/Offtake_Monthly/` | Data team | Gate 1 | ☐ |
| 2 | **Collect primary article CSV** — download `MT_Primary_Aug_26.csv` (or equivalent) and drop into `PowerBI/RawDataFolders/Primary_Article_Monthly/` | Data team | Gate 1 | ☐ |
| 3 | **Run validation gates** — `python scripts/validation_gates.py --month Aug-26`; all gates must reach PASS or PASS_WITH_FLAG before proceeding | Analyst | All | ☐ |
| 4 | **Run channel split** — `python scripts/mt_channel_split.py`; confirm `august_mt_channel_split.json` written to `scripts/data/` with correct MT / eB2B / SIS totals | Analyst | Gate 6 | ☐ |
| 5 | **Run reconciliation** — `python scripts/mt_channel_reconciliation.py`; all 5 checks must be ≤ PASS WITH WARNINGS; BLOCKED on any check = stop and fix before continuing | Analyst | Gate 4 | ☐ |
| 6 | **Rebuild data.js** — `python scripts/build_dashboard_data.py --offtake-patch --src PowerBI/RawDataFolders/Offtake_Monthly --out dashboard/data.js`; sweep the 12 tabs × 4 FY states in the browser; confirm no NaN / broken cards | Analyst | Gate 6 | ☐ |
| 7 | **Generate Command Centre deck** — `node scripts/build_july_mt_command_centre.js` (update month label to August first); run `python scripts/check_deck_geometry.py`; fix any overflow | Analyst | — | ☐ |
| 8 | **Commit and push** — stage `dashboard/data.js`, `scripts/data/august_mt_channel_split.json`, the updated generator, and the deck `.pptx`; push to `claude/data-analytics-learning-g8ggyw` | Analyst | — | ☐ |

---

## Known Carry-Forwards from July

| Item | Status | Action required |
|------|--------|-----------------|
| June 2026 offtake absent | Structural — Q1 FY27 series = Apr + May + Jul only | Document in deck footnote; do **not** impute June even if August is now available |
| Nielsen feed (`Nielsen_Monthly/`) empty | Tier 3 placeholder | Keep "not yet fed" copy in deck; re-evaluate when Nielsen CSV is supplied |
| TDP feed (`TDP_Monthly/`) empty | Tier 3 placeholder | Same as above |
| CHECK 5 grain limitation | Tier 2 warning | Continue to document in audit slide footnote |

---

## FY Rule Reminder

August 2026 (month 8, calendar year 2026) → **FY27**  
`THE ONE FY RULE: Apr–Dec of calendar year Y → FY(Y+1)`

The validation script enforces this automatically. If any source file is labelled FY26 for August, that is a source error — flag it before ingest.

---

## Exclusion Rules (unchanged from July)

- **Store Type = 'Brand Counter'**: excluded from all offtake aggregations
- **Discontinued brands**: Lumineve, Pure Origin, Staze, Luminev — excluded
- **eB2B chains** (Nykaa/FSN, Eremedium): included in MT national totals; excluded from zone rollup
- **SIS chains** (Azorte, Shoppers Stop, Broadway, Lifestyle, Today's Basket): included in MT national totals; excluded from zone rollup

Any new chain added in August that falls outside the six geographic zones must be classified as eB2B or SIS before the zone rollup runs. Confirm with the channel master (`scripts/data/channel_master.json`) before committing.

---

## Quick Commands

```bash
# Step 3 — gate check
python scripts/validation_gates.py --month Aug-26

# Step 3 JSON (for CI)
python scripts/validation_gates.py --month Aug-26 --json

# Step 4 — channel split
python scripts/mt_channel_split.py

# Step 5 — reconciliation
python scripts/mt_channel_reconciliation.py

# Step 6 — rebuild (offtake-patch mode, idempotent)
python scripts/build_dashboard_data.py \
  --offtake-patch \
  --src PowerBI/RawDataFolders/Offtake_Monthly \
  --out dashboard/data.js

# Step 7 — geometry check
python scripts/check_deck_geometry.py
```
