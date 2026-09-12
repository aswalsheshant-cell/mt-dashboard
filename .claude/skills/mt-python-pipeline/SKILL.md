---
name: mt-python-pipeline
description: |
  Safe file I/O, FY derivation, validation patterns, and reconciliation helpers for MT data pipelines.
  Use this skill when the user asks to: load XLSB/CSV files safely, derive FY from month+year,
  validate data integrity, reconcile Primary vs Offtake, handle missing files, build idempotent
  transformations, or debug pipeline failures. Also triggers on: "write a script", "read xlsb",
  "FY logic in Python", "validate primary data", "check for duplicates", "reconcile offtake",
  "handle missing files", "safe file loading", "idempotent transform", "pipeline error".
  Do NOT use for Power BI/DAX code, SQL queries, or dashboard UI logic — route those to relevant skills.
---
# MT Python Pipeline

Write production-grade Python for MT data ETL — safe file loading, FY derivation, validation
patterns, reconciliation functions, and error-resistant pipeline design.

## File I/O Safety Tier

**S — Always enforce:**
- Check file existence before read; raise clear `FileNotFoundError(f"Required file not found: {path}")`
- Use `try`/`except` for I/O with specific error classes (not bare `except`)
- Close file handles (use `with` statements for file/sheet context managers)
- Validate encoding (`encoding='utf-8'`)
- Log file paths and row counts after load

**A — Use for XLSB/CSV pipelines:**
- `openpyxl` for `.xlsb` files (via `pyxlsb.convert_date` for dates)
- `pandas.read_csv()` with dtype hints for numeric cols (avoid silent type coercion)
- `pandas.read_excel()` for `.xlsx` with `engine='openpyxl'`
- Column name cleanup: `df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')`
- Null handling: `df.fillna(value=...)` ONLY after explicit check—never silent NaN propagation

**B — Validation before transform:**
- Schema validation: required columns, dtypes, row count thresholds
- Duplicate detection: `df.duplicated(subset=[...])` with action (raise, drop, aggregate)
- Null census: `df.isnull().sum()` before proceeding (log nulls; decide treatment)
- Numeric range checks: min/max values (NSV in ₹L, Qty ≥ 0, % in 0–100)

**C — Transformation safety:**
- Preserve row identity: one row in = one row out (unless aggregating by design)
- Reconciliation check after each transform: `assert original_nsv ≈ transformed_nsv` with tolerance
- Never modify source data; write to new column / new DataFrame
- Use `copy()` to avoid SettingWithCopyWarning

## FY Derivation (Indian Financial Year Apr–Mar)

**Core Logic:**
```python
def fy_tag_from_ym(year: int, month: int) -> str:
    """Derive FY tag from calendar year + month (1–12).
    
    Apr–Dec of year Y → FY(Y+1)  [e.g. Apr-26 → FY27]
    Jan–Mar of year Y → FY(Y)    [e.g. Mar-26 → FY26]
    """
    if month >= 4:
        return f"FY{(year - 2000) + 1}"
    else:
        return f"FY{year - 2000}"

def fy_tag_from_label(label: str) -> str:
    """Parse month label (e.g. 'Apr-26', 'Mar-26', 'Apr-25') and return FY tag."""
    # Expected format: "Mon-YY" (e.g. "Apr-26", "Dec-25")
    parts = label.strip().split('-')
    if len(parts) != 2:
        raise ValueError(f"Invalid month label format: {label}")
    month_str, year_str = parts
    
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    month = month_map.get(month_str.lower())
    if not month:
        raise ValueError(f"Invalid month: {month_str}")
    
    year = 2000 + int(year_str)
    return fy_tag_from_ym(year, month)
```

## Validation Patterns

### 1. Required Columns Check
```python
def validate_schema(df: pd.DataFrame, required_cols: list[str]) -> None:
    """Raise KeyError if any required column is missing."""
    missing = set(required_cols) - set(df.columns)
    if missing:
        raise KeyError(f"Missing required columns: {missing}. Found: {df.columns.tolist()}")
```

### 2. Duplicate Detection (Chain × Month × Site × Article)
```python
def check_duplicates(df: pd.DataFrame, grain_cols: list[str]) -> int:
    """Count and log duplicates at grain. Raise if any found."""
    dups = df.duplicated(subset=grain_cols, keep=False).sum()
    if dups > 0:
        dup_rows = df[df.duplicated(subset=grain_cols, keep=False)]
        print(f"⚠ {dups} duplicate rows found at grain {grain_cols}:")
        print(dup_rows.head(10))
        raise ValueError(f"Duplicate rows violate grain constraint: {grain_cols}")
    return dups
```

### 3. Null Census with Decision Logic
```python
def census_nulls(df: pd.DataFrame, action: str = 'log') -> dict:
    """Report nulls per column. action='log' (report), 'drop' (remove), 'fail' (raise)."""
    null_counts = df.isnull().sum()
    null_counts = null_counts[null_counts > 0]
    
    if null_counts.empty:
        print("✓ No nulls found")
        return {}
    
    print(f"⚠ Null summary ({null_counts.sum()} total):")
    for col, count in null_counts.items():
        pct = 100 * count / len(df)
        print(f"  {col}: {count} ({pct:.2f}%)")
    
    if action == 'fail':
        raise ValueError(f"Null values present in {null_counts.index.tolist()}")
    elif action == 'drop':
        df_clean = df.dropna(subset=null_counts.index)
        dropped = len(df) - len(df_clean)
        print(f"Dropped {dropped} rows")
        return df_clean
    return null_counts.to_dict()
```

### 4. Numeric Range Validation
```python
def validate_ranges(df: pd.DataFrame, constraints: dict[str, tuple]) -> None:
    """Validate numeric columns within range.
    
    constraints: {'nsv_lakhs': (0, 10000), 'qty': (0, 1e6), 'pct': (0, 100)}
    """
    for col, (min_val, max_val) in constraints.items():
        if col not in df.columns:
            continue
        out_of_range = ((df[col] < min_val) | (df[col] > max_val)).sum()
        if out_of_range > 0:
            violators = df[(df[col] < min_val) | (df[col] > max_val)]
            print(f"⚠ {out_of_range} rows out of range [{min_val}, {max_val}] in {col}:")
            print(violators[[col]].describe())
            raise ValueError(f"Range violation in {col}")
```

## Reconciliation Function (Primary vs Offtake)

```python
def reconcile_primary_vs_offtake(primary_df: pd.DataFrame, 
                                  offtake_df: pd.DataFrame, 
                                  tolerance: float = 0.01) -> dict:
    """Compare Primary NSV vs Offtake value by FY+Chain+Month.
    
    Returns: {'variance_pct': float, 'matches': int, 'mismatches': int, 'details': DataFrame}
    """
    # Aggregate by FY, Chain, Month
    p_agg = primary_df.groupby(['fy_tag', 'chain_name', 'month_label'])['nsv_lakhs'].sum().reset_index()
    o_agg = offtake_df.groupby(['fy_tag', 'chain_name', 'month_label'])['value_sold_lakhs'].sum().reset_index()
    
    # Join and compute variance
    merged = p_agg.merge(o_agg, how='outer', on=['fy_tag', 'chain_name', 'month_label'], 
                         suffixes=('_primary', '_offtake'))
    merged['variance_lakhs'] = merged['nsv_lakhs'] - merged['value_sold_lakhs']
    merged['variance_pct'] = (merged['variance_lakhs'] / 
                              merged['nsv_lakhs'].replace(0, 1) * 100)
    
    within_tolerance = (merged['variance_pct'].abs() <= tolerance).sum()
    total = len(merged)
    
    print(f"Reconciliation: {within_tolerance}/{total} within {tolerance}% tolerance")
    
    if within_tolerance < total:
        print("Mismatches:")
        print(merged[merged['variance_pct'].abs() > tolerance].sort_values('variance_lakhs', 
                                                                           ascending=False))
    
    return {
        'variance_pct': merged['variance_pct'].abs().max(),
        'matches': within_tolerance,
        'mismatches': total - within_tolerance,
        'details': merged
    }
```

## EDA Helper: Distribution Allocation Validation

```python
def validate_distribution_allocation(primary_df: pd.DataFrame, 
                                      allocation_df: pd.DataFrame) -> dict:
    """Verify Distributor primary is correctly split across chains.
    
    Grain: (month, chain, article)
    Returns: {'reconciliation_variance': float, 'blocked_nsv': float, 'unallocated': int}
    """
    # Distributor rows before split
    dist_nsv_original = primary_df[primary_df['chain_name'] == 'Dist.']['nsv_lakhs'].sum()
    
    # Allocated rows (post-split)
    allocated_nsv = allocation_df['nsv_lakhs'].sum()
    
    # Blocked rows (unmapped, not re-split)
    blocked_nsv = primary_df[primary_df['nsv_status'] == 'blocked']['nsv_lakhs'].sum()
    
    # Reconciliation: Original = Allocated + Blocked + Variance
    variance = dist_nsv_original - (allocated_nsv + blocked_nsv)
    variance_pct = 100 * variance / max(dist_nsv_original, 1)
    
    print(f"Distributor Allocation Validation:")
    print(f"  Original Dist NSV:  ₹{dist_nsv_original:.2f}L")
    print(f"  Allocated NSV:      ₹{allocated_nsv:.2f}L")
    print(f"  Blocked NSV:        ₹{blocked_nsv:.2f}L")
    print(f"  Variance:           ₹{variance:.4f}L ({variance_pct:.3f}%)")
    
    if abs(variance_pct) > 0.01:
        raise ValueError(f"Allocation variance exceeds tolerance: {variance_pct:.3f}%")
    
    return {
        'reconciliation_variance': variance_pct,
        'blocked_nsv': blocked_nsv,
        'unallocated': 0 if variance_pct < 0.01 else 1
    }
```

## Idempotent Transform: Offtake Patch

```python
def apply_offtake_patch_idempotent(existing_offtake: pd.DataFrame,
                                    new_offtake_files: list[str]) -> pd.DataFrame:
    """Merge new monthly offtake files into existing data.js offtake block.
    
    Idempotent: reprocesses all touched FYs, never double-counts.
    Returns: Updated offtake DataFrame with all FYs merged.
    """
    all_offtake = existing_offtake.copy()
    
    for filepath in new_offtake_files:
        print(f"Loading {filepath}...")
        new_df = pd.read_csv(filepath)
        validate_schema(new_df, ['fy_tag', 'chain_name', 'month_label', 'value_sold_lakhs'])
        
        # Remove rows from touched FYs (idempotent)
        touched_fys = new_df['fy_tag'].unique()
        all_offtake = all_offtake[~all_offtake['fy_tag'].isin(touched_fys)]
        
        # Append new data
        all_offtake = pd.concat([all_offtake, new_df], ignore_index=True)
        print(f"  ✓ Merged {len(new_df)} rows")
    
    # Final reconciliation
    print(f"Final offtake: {len(all_offtake)} rows, {all_offtake['fy_tag'].nunique()} FYs")
    return all_offtake.reset_index(drop=True)
```

## Response Format
- Show complete, runnable code first
- Assume Python 3.9+
- Include inline comments for non-obvious steps
- For scripts: show full error handling + logging
- For one-liners: inline validation checks
- Reference build_dashboard_data.py helpers when applicable
