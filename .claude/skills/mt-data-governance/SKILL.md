---
name: mt-data-governance
description: |
  Business logic validation, data quality, reconciliation, PBIP standards, and performance
  engineering for the Honasa MT Analytics Platform. Auto-activates when: changing any
  business calculation; processing Primary, Offtake, Allocation, MRN, GST, NSV, or Returns
  data; running a pipeline or automation; checking data quality; reconciling numbers;
  or the user says: "validate this", "check the logic", "data quality", "reconcile",
  "completeness check", "why are the numbers different", "mapping issue", "duplicate",
  "allocation check", "master data", "business rule", "source of truth",
  "schema check", "null check", "QC this", "data health", "model performance",
  "Power Query optimization", "star schema review".
  Always run BEFORE marking any automation or pipeline output as complete or correct.
---

# MT Data Governance

Business logic validation, data quality scoring, reconciliation, and performance standards
for every pipeline and dashboard release in the Honasa MT Analytics Platform.

## Business Logic Guardian

The following logic MUST be validated before any change is marked complete.
No business rule may be altered without explicit validation at every level.

### Primary Sales Rules
```
NSV = Gross Billing − Returns (MRN) − Schemes − Damages
FY  = Apr–Mar (Apr-YY to Mar-YY+1 → FY(YY+1))
Grain: Month + Chain + Brand + Pack Size
Deduplication: Reliance Brand Counter rows MUST be excluded (exact match, not contains)
Allocation: Distributor NSV → Chain → Brand → Article via controlled mapping tables
```

### Offtake Rules
```
Grain: Month + Chain + Site Code + EAN
Sources: Store-level XLSB files (one per chain or period)
Patch mode: --offtake-patch is idempotent — include ALL months collected; never double-count
FY gating: Offtake tab checks o['total_'+fy] — independent of Primary FY coverage
Coverage: Pre-agg ends Mar-26 (FY25/FY26); FY27+ via patch only
```

### Allocation Rules
```
Level 1: Distributor → Chain (geography + channel mapping)
Level 2: Chain → Brand (brand-chain relationship table)
Level 3: Brand → Article/EAN (product master)
Conflict: If store maps to multiple chains, priority chain wins (mapping table priority col)
Missing: All unmapped records logged to alloc.missing_mapping — NEVER silently dropped
```

### Financial / P&L Rules
```
GM % = Gross Margin / NSV × 100
Trade Spend % = BTL Trade Spend / NSV × 100
Channel EBITDA = GM − Trade Spend − Field Force Cost
Returns: MRN reduces NSV in the month of credit note, not original billing month
GST: Not included in NSV — NSV is always ex-GST
```

## Data Quality Scoring (run on every pipeline output)

Calculate and report all six dimensions:

```python
def data_quality_score(df: pd.DataFrame, config: dict) -> dict:
    """
    Returns a quality scorecard for an MT dataset.
    config = {
        "required_cols": [...],
        "key_cols": ["month_label", "chain_name"],
        "numeric_cols": ["nsv_lakhs"],
        "allowed_fy": ["FY25", "FY26", "FY27"],
        "date_col": "month_label"
    }
    """
    scores = {}
    n = len(df)

    # 1. Completeness: required columns present and non-null
    for col in config.get("required_cols", []):
        null_rate = df[col].isna().mean() if col in df.columns else 1.0
        scores[f"completeness_{col}"] = round((1 - null_rate) * 100, 1)

    # 2. Uniqueness: no duplicate keys
    key_dups = df.duplicated(subset=config.get("key_cols", [])).sum()
    scores["uniqueness_pct"] = round((1 - key_dups / max(n, 1)) * 100, 1)

    # 3. Validity: FY values in allowed set
    if "fy_tag" in df.columns:
        valid_fy = df["fy_tag"].isin(config.get("allowed_fy", [])).mean()
        scores["validity_fy_pct"] = round(valid_fy * 100, 1)

    # 4. Accuracy: numeric columns within expected range
    for col in config.get("numeric_cols", []):
        if col in df.columns:
            neg_rate = (df[col] < 0).mean()
            scores[f"accuracy_{col}_neg_rate"] = round(neg_rate * 100, 1)

    # 5. Consistency: no unmapped records
    if "chain_name" in df.columns:
        unmapped = df["chain_name"].isin(["UNMAPPED", "NA", "", None]).mean()
        scores["consistency_mapped_pct"] = round((1 - unmapped) * 100, 1)

    # 6. Timeliness: latest month present
    if "month_label" in df.columns:
        scores["latest_month"] = df["month_label"].max()

    # Overall health score (weighted average of completeness + uniqueness + validity)
    key_scores = [v for k, v in scores.items()
                  if any(x in k for x in ["completeness", "uniqueness", "validity"])]
    scores["health_score"] = round(sum(key_scores) / max(len(key_scores), 1), 1)

    return scores
```

### Health Score Thresholds
```
95–100  GREEN   → Release approved
85–94   YELLOW  → Release with documented exceptions
< 85    RED     → BLOCKED — do not release
```

## Automated QC Checklist (run before every release)

```
QC GATE — MUST ALL PASS BEFORE MARKING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
□ Duplicates: Zero duplicate rows on business key grain
□ Nulls: No nulls in mandatory columns (chain_name, month_label, fy_tag, nsv_lakhs)
□ Missing mappings: alloc.missing_mapping count ≤ approved threshold
□ GST check: NSV is ex-GST (no GST-inclusive values in primary)
□ EAN validity: EAN codes are 13-digit numeric strings
□ Allocation mismatch: Distributor total ≈ Chain total (±0.5%)
□ Primary mismatch: Sum of article NSV = chain NSV (±0.1L)
□ Offtake mismatch: Offtake tab total ≈ store-level sum (±0.5%)
□ Customer mismatch: Every chain in Primary exists in chain mapping table
□ Date mismatch: All month_label values parse to valid dates
□ Financial variance: P&L vs Primary delta documented and within tolerance
□ Reliance BC: Brand Counter rows excluded from Reliance chain total
□ FY continuity: No gap months within a FY (Apr through available month)
□ Regression: Prior approved FY25/FY26 totals unchanged
```

## Reconciliation Standard (nothing accepted until all levels match)

```
Level 1 — Raw Source
  Source file row count = loaded DataFrame row count

Level 2 — After Cleaning
  Pre-filter total = post-filter total + documented exclusions

Level 3 — After Mapping
  Mapped records + unmapped records = input records

Level 4 — After Aggregation
  Sum of detail = sum of aggregated output (±rounding tolerance 0.01L)

Level 5 — Cross-Source
  Primary NSV ≈ Offtake value (gap documented if >10%)
  P&L GM ≈ Primary NSV × standard GM% (±2pp tolerance)

Level 6 — Executive Summary
  Dashboard total = QC report total = manually verified sample
```

## Master Data Governor

Before any mapping change:

```
MASTER DATA CHANGE CONTROL
━━━━━━━━━━━━━━━━━━━━━━━━━━
Change type:     [Chain / Store / EAN / Brand / Distributor / Employee]
Record affected: [exact key value]
Old value:       [current mapping]
New value:       [proposed mapping]
Effective from:  [YYYY-MM — historical records: update? or new records only?]
Impacted FYs:    [FY25 / FY26 / FY27]
Approved by:     [Business owner name]
Regression test: [confirm prior period totals unchanged]
```

Mapping files owned by `build_dashboard_data.py` — never edited in Excel directly.

## Performance Engineering Checklist

Review whenever dashboard is slow or model is large:

```
POWER BI / DASHBOARD PERFORMANCE
□ Power Query: are transformations pushed to source (query folding)?
□ Model size: unused columns removed from imported tables?
□ Relationships: all MANY-to-ONE, single direction unless justified?
□ Cardinality: high-cardinality columns (EAN, site_code) — are they needed in visuals?
□ DAX: no SUMX over millions of rows where SUM(column) works?
□ Unused measures: remove measures not used in any visual
□ Incremental refresh: configured for large fact tables?
□ Visual rendering: no more than 10 visuals per page?
□ data.js: ~9MB is the ceiling — profile which blocks are largest

PYTHON PIPELINE
□ XLSB loading: using pyxlsb engine, not xlrd?
□ dtype=str on load: prevents silent numeric conversion of IDs?
□ groupby dropna=False: not silently dropping NA groups?
□ Memory: processing one FY at a time for large offtake files?
□ Idempotent: does re-running produce the same output?
```
