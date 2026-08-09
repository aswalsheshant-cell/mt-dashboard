---
name: mt-python-pipeline
description: |
  Python and Pandas automation patterns for Modern Trade data pipelines — reading Excel/XLSB/CSV
  files, cleaning, joining, aggregating, and outputting MT reports. Use this skill whenever the
  user asks to: write a Python script for MT data, automate a report, process an xlsb or xlsx
  file, build a data pipeline, do EDA on sales data, create a Python-based reconciliation,
  debug a pandas script, or says "write me a script", "automate this", "Python for this",
  "read this Excel", "clean the data", "merge these files", "pandas groupby", "can you code this".
  Do NOT use for SQL queries (use mt-sql-analytics), Excel formulas (use excel-automation),
  or dashboard HTML/JS changes.
---

# MT Python Data Pipeline

Write production-grade Python scripts for Modern Trade data processing — reading XLSB/Excel/CSV
files, cleaning, joining on MT keys, aggregating, validating, and exporting reports.

## Core Stack

```python
import pandas as pd
import numpy as np
from pathlib import Path
```

For XLSB files always use `pyxlsb`:
```python
import pyxlsb  # pip install pyxlsb
df = pd.read_excel("file.xlsb", engine="pyxlsb", sheet_name="Sheet1")
```

## MT Data Processing Principles

1. **Preserve identifiers as text** — Site Code, EAN, Article Code must stay as strings
2. **Grain-first thinking** — state what one row represents before any join
3. **No silent drops** — count rows before and after every filter; log what was removed
4. **Idempotent reruns** — running the same input twice must not duplicate records
5. **FY derivation from month+year** — never hardcode FY25/FY26; compute from date

## Canonical Patterns

### 1. Safe File Loading (Excel / XLSB / CSV)

```python
def load_mt_file(path: str | Path, sheet_name: str = "Sheet1") -> pd.DataFrame:
    """Load MT source file with identifier columns preserved as text."""
    p = Path(path)
    if p.suffix.lower() == ".xlsb":
        df = pd.read_excel(p, engine="pyxlsb", sheet_name=sheet_name, dtype=str)
    elif p.suffix.lower() in {".xlsx", ".xls"}:
        df = pd.read_excel(p, sheet_name=sheet_name, dtype=str)
    else:
        df = pd.read_csv(p, dtype=str)

    # Strip whitespace from all string columns
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].str.strip()

    # Preserve MT identifiers as text (leading zeros, no scientific notation)
    for col in ["Site Code", "EAN", "Article Code", "Client ID", "Store Code"]:
        if col in df.columns:
            df[col] = df[col].fillna("NA").astype(str).str.strip()
            df.loc[df[col].isin(["nan", "None", "none", ""]), col] = "NA"

    return df
```

### 2. FY Tag Derivation (Indian FY, Apr–Mar)

```python
def fy_tag(month_label: str) -> str:
    """
    Convert 'Apr-26' or 'Jan-26' to 'FY27' / 'FY26'.
    Apr–Dec of year Y → FY(Y+1); Jan–Mar of year Y → FY(Y).
    """
    import datetime
    dt = datetime.datetime.strptime(month_label, "%b-%y")
    if dt.month >= 4:
        return f"FY{dt.year + 1 - 2000:02d}"
    return f"FY{dt.year - 2000:02d}"

# Vectorised version for a DataFrame column:
df["fy_tag"] = df["month_label"].apply(fy_tag)
```

### 3. Numeric Column Conversion (safe, with logging)

```python
def to_numeric_safe(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Convert columns to float; log any values that fail conversion."""
    for col in cols:
        if col not in df.columns:
            print(f"WARNING: column '{col}' not found — skipped")
            continue
        before_nulls = df[col].isna().sum()
        df[col] = pd.to_numeric(df[col].str.replace(",", "").str.replace("₹", ""), errors="coerce")
        after_nulls = df[col].isna().sum()
        new_nulls = after_nulls - before_nulls
        if new_nulls > 0:
            print(f"WARNING: {new_nulls} values in '{col}' could not be converted to numeric")
    return df
```

### 4. Reliance Brand Counter Filter (Mamaearth-specific)

```python
def filter_reliance_brand_counter(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove Reliance Brand Counter rows to prevent double-counting.
    Uses exact match on 'brand counter' — must NOT match 'non brand counter'.
    """
    if "Data status" not in df.columns:
        print("WARNING: 'Data status' column not found — Reliance BC filter skipped")
        return df

    chain_lower = df["Chain Name"].astype(str).str.strip().str.lower()
    status_lower = df["Data status"].astype(str).str.strip().str.lower()
    is_reliance = chain_lower.str.contains("reliance", na=False)
    is_brand_counter = (status_lower == "brand counter")  # exact match — not str.contains

    rows_before = len(df)
    df = df[~(is_reliance & is_brand_counter)].copy()
    print(f"Reliance BC filter: removed {rows_before - len(df)} rows")
    return df
```

### 5. Primary vs Offtake Reconciliation

```python
def reconcile_primary_offtake(
    primary_df: pd.DataFrame,
    offtake_df: pd.DataFrame,
    keys: list[str] = ["fy_tag", "month_label", "chain_name"],
    primary_val: str = "nsv_lakhs",
    offtake_val: str = "value_sold_lakhs",
    tolerance_pct: float = 5.0,
) -> pd.DataFrame:
    """
    Merge primary and offtake on keys and compute gap.
    Rows with gap > tolerance_pct are flagged as REVIEW.
    """
    p = primary_df.groupby(keys)[primary_val].sum().reset_index()
    o = offtake_df.groupby(keys)[offtake_val].sum().reset_index()

    rec = p.merge(o, on=keys, how="outer")
    rec[primary_val] = rec[primary_val].fillna(0)
    rec[offtake_val] = rec[offtake_val].fillna(0)
    rec["gap_lakhs"] = rec[primary_val] - rec[offtake_val]
    rec["gap_pct"] = np.where(
        rec[primary_val] != 0,
        rec["gap_lakhs"] / rec[primary_val] * 100,
        np.nan,
    )
    rec["status"] = np.where(
        rec["gap_pct"].abs() > tolerance_pct, "REVIEW", "OK"
    )
    return rec.sort_values("gap_pct", key=abs, ascending=False)
```

### 6. Exploratory Data Analysis (EDA) Quick-Start

```python
def mt_eda(df: pd.DataFrame, label: str = "dataset") -> None:
    """Print key EDA stats for an MT dataframe."""
    print(f"\n{'='*60}")
    print(f"EDA: {label}")
    print(f"  Rows: {len(df):,}  |  Columns: {len(df.columns)}")
    print(f"  Columns: {list(df.columns)}")

    # Null summary (only columns with nulls)
    null_counts = df.isna().sum()
    null_cols = null_counts[null_counts > 0]
    if len(null_cols):
        print(f"\n  Null counts:")
        for col, n in null_cols.items():
            print(f"    {col}: {n} ({n/len(df)*100:.1f}%)")

    # Numeric summary
    num_cols = df.select_dtypes("number").columns.tolist()
    if num_cols:
        print(f"\n  Numeric summary:")
        print(df[num_cols].describe().round(2).to_string())

    # Cardinality for key string columns
    for col in ["Chain Name", "chain_name", "fy_tag", "month_label"]:
        if col in df.columns:
            vals = df[col].value_counts()
            print(f"\n  {col} ({len(vals)} unique): {vals.index[:8].tolist()}")
    print('='*60)
```

### 7. Output to Excel with Formatting

```python
def export_mt_report(df: pd.DataFrame, output_path: str, sheet_name: str = "Report") -> None:
    """Export a MT report DataFrame to Excel with auto-column widths."""
    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).str.len().max(), len(col)) + 2
            ws.set_column(i, i, min(max_len, 40))
    print(f"Exported {len(df):,} rows → {output_path}")
```

## Validation Checklist (always run before releasing output)

```python
def validate_mt_output(df: pd.DataFrame, name: str, expected_grain: str) -> bool:
    """
    Minimal validation gate. Returns True if all checks pass.
    expected_grain: human description e.g. "month_label + chain_name + brand_name"
    """
    print(f"\nValidating: {name}  (grain: {expected_grain})")
    passed = True

    if len(df) == 0:
        print("  FAIL: empty output")
        return False

    # Check for all-null numeric columns
    for col in df.select_dtypes("number").columns:
        if df[col].isna().all():
            print(f"  FAIL: column '{col}' is entirely null")
            passed = False

    # Check for NaN in string key columns
    for col in ["chain_name", "Chain Name", "month_label", "fy_tag"]:
        if col in df.columns and df[col].isna().any():
            print(f"  WARN: null values in key column '{col}'")

    # Duplicate grain check (example using first two columns as proxy)
    grain_cols = [c for c in df.columns if c in
                  ["month_label", "chain_name", "brand_name", "fy_tag", "site_code"]]
    if len(grain_cols) >= 2:
        dups = df.duplicated(subset=grain_cols[:4]).sum()
        if dups:
            print(f"  WARN: {dups} duplicate rows on grain cols {grain_cols[:4]}")

    print(f"  {'PASS' if passed else 'BLOCKED'}: {len(df):,} rows")
    return passed
```

## Response Format

1. Show the complete, runnable script first
2. State assumptions (column names, file format, grain)
3. Add a brief explanation of each function's purpose
4. Flag any data quality risks specific to MT sources
