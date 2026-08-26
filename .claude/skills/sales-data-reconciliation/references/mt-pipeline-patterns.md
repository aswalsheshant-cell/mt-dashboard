# MT pipeline defensive patterns

Repo-specific patterns for `scripts/build_dashboard_data.py` and any automation
ingesting MT source files. These encode defects that have actually occurred.

## Reliance Brand Counter filtering (double-count prevention)

```python
if "Data status" in df.columns:
    _chain_c = df["Chain Name"].astype(str).str.strip().str.lower()
    _ds_c = df["Data status"].astype(str).str.strip().str.lower()
    _is_rel = _chain_c.str.contains("reliance", na=False)
    _is_bc = (_ds_c == "brand counter")  # exact match required
    df = df[~(_is_rel & _is_bc)].copy()
```

Use exact `==` for `"brand counter"`, never `str.contains()` — the value
`"non brand counter"` also contains the substring `"brand counter"`, so a `contains`
test silently removes the rows it was meant to keep.

## Site Code NA handling

```python
site_cols = ["Site Code", "Site Name"]
for col in site_cols:
    if col in df.columns:
        df[col] = df[col].fillna("NA")
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(["nan", "None", "none", ""]), col] = "NA"
```

## Column presence guard

```python
if "Data status" not in df.columns:
    print("WARNING: 'Data status' column not found. Reliance BC filter skipped.")
```

A guard that warns is correct; a guard that silently skips is not. The warning is what
makes a missing column visible in the run log.

## Identifier preservation

```python
text_cols = ["Site Code", "EAN", "Article Code", "Client ID"]
for col in text_cols:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()
```

Force these to text at read time as well, via `dtype={"site_code": "string"}` — once
pandas has inferred `int64`, the leading zeros are already gone.

## Groupby NA safety

```python
# dropna=False keeps NA groups visible instead of silently dropping rows
df.groupby(["Chain Name", "Site Code"], dropna=False).sum()
```

Without `dropna=False`, rows with a blank key vanish and the output no longer ties to
source — a reconciliation break with no error message.

## Fiscal year derivation

The canonical helper, from `scripts/build_dashboard_data.py:42`:

```python
def fy_tag_from_ym(year, month):
    """Calendar (year, month) -> 'FY27' style tag. Apr-2026 -> FY27; Mar-2026 -> FY26."""
    return f"FY{(year + 1 if month >= 4 else year) % 100:02d}"
```

Import it rather than re-implementing it. Note the casing split in this repo: the
helper returns `FY27`, while `data.js` block keys are lowercase (`total_fy27`,
`monthly_fy27`, `months_fy27`). Lowercase at the point where a key is constructed, not
at the source.

Month ordering uses `(month - 4) % 12`, giving 0 for April through 11 for March. Sorting
month labels alphabetically puts April after August and every trend chart then lies.

## Coverage split

The pre-aggregated Primary, Offtake and P&L workbooks end March 2026 and cover FY25 and
FY26. Later fiscal years exist only in article-level sources: FY27 primary in
`detail_meta.fyx_primary`, FY27 offtake merged through `--offtake-patch`. Each block
gates on its own FY coverage, never another block's. Checking the Primary-only gate
before rendering an Offtake figure produces a false BLOCKED.

## Partial refresh modes

`--offtake-patch` is idempotent: place every month collected so far in `--src` and it
recomputes each touched FY without double counting. Re-running is safe; running with a
partial `--src` is not, because a fiscal year is recomputed from what is present.

After any partial refresh, verify that fiscal years which were not intended to change
are byte-identical in the relevant `data.js` blocks.
