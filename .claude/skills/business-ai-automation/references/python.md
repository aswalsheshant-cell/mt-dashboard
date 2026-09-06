# Python and pandas for MT data

Grain, fiscal-year and denominator rules are in the parent SKILL.md. This file
covers pandas mechanics: ingestion, cleaning, aggregation, formatting, export.

## Repo context

This repo already has working Python. **Reuse it, do not rewrite it.**

- `scripts/build_dashboard_data.py` — the only generator of `dashboard/data.js`.
  FY helpers live at the top: `fy_tag_from_ym`, `fy_tag_from_label`, `fy_start_year`,
  `month_labels`, `quarter_labels_for`. Import or mirror these; never re-derive FY.
- `scripts/split_offtake_store_article_xlsb.py`, `scripts/split_primary_article_xlsb.py`
  — split heavy `.xlsb` sources into month CSVs.
- `scripts/qc_dashboard.py`, `scripts/test_*.py` — existing validation. Extend these
  rather than writing a parallel checker.

## Standard imports and options

```python
import numpy as np
import pandas as pd

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 60)
pd.set_option("display.float_format", lambda v: f"{v:,.2f}")
```

## 1. Read the file — the right reader for the right extension

```python
# .xlsx / .xlsm  -> openpyxl
df = pd.read_excel(path, sheet_name="Data", engine="openpyxl")

# .xlsb (binary, what most heavy MT extracts arrive as) -> pyxlsb
df = pd.read_excel(path, sheet_name="Data", engine="pyxlsb")

# .csv from a retailer portal: never trust the encoding or the thousands separator
df = pd.read_csv(
    path,
    dtype={"site_code": "string", "ean": "string"},   # keep codes as text
    thousands=",",
    encoding="utf-8-sig",                              # strips the BOM Excel adds
)
```

**Always force identifier columns to `string`.** Site codes, EANs and customer codes
with leading zeros become `1234` instead of `001234` the moment pandas guesses `int64`,
and every downstream join then fails silently.

Reading many month files:

```python
from pathlib import Path

frames = []
for file_path in sorted(Path(src_dir).glob("*.csv")):
    month_df = pd.read_csv(file_path, dtype={"site_code": "string", "ean": "string"})
    month_df["source_file"] = file_path.name     # keep provenance
    frames.append(month_df)

raw = pd.concat(frames, ignore_index=True)
```

Keeping `source_file` is what lets you answer "which file caused this spike".

## 2. Profile before you calculate

Never skip this. Run it every time a new file arrives.

```python
def profile(df: pd.DataFrame, keys: list[str]) -> None:
    """Print the six facts you need before trusting a file."""
    print(f"rows={len(df):,}  cols={df.shape[1]}")
    print(df.dtypes)
    print("nulls:\n", df.isna().sum().loc[lambda s: s > 0])
    print("duplicate key rows:", df.duplicated(subset=keys).sum())
    print("blank keys:", df[keys].isna().any(axis=1).sum())
    print(df.describe(include="number").T[["min", "max", "mean"]])
```

Six checks, in order: shape, dtypes, nulls, duplicate keys, blank keys, value ranges.
`df.info()` and `df.describe()` on their own are not enough — the duplicate-key count is
the one that catches a double-loaded month.

## 3. Clean — the five defects every raw MT file has

```python
# a. header/column noise: trailing spaces, mixed case, non-breaking spaces
df.columns = (
    df.columns.astype(str)
      .str.replace(" ", " ", regex=False)
      .str.strip()
      .str.lower()
      .str.replace(r"[^\w]+", "_", regex=True)
      .str.strip("_")
)

# b. text values with hidden whitespace, which break joins
for col in ["chain_name", "site_code", "ean", "article_name"]:
    df[col] = df[col].astype("string").str.replace(" ", " ", regex=False).str.strip()

# c. numbers stored as text ("1,234", "(500)", "-", "")
def to_number(series: pd.Series) -> pd.Series:
    cleaned = (
        series.astype("string")
        .str.replace(",", "", regex=False)
        .str.replace("(", "-", regex=False)
        .str.replace(")", "", regex=False)
        .replace({"-": None, "": None, "NA": None, "#N/A": None})
    )
    return pd.to_numeric(cleaned, errors="coerce")

df["offtake_value"] = to_number(df["offtake_value"])

# d. dates stored as text or Excel serials
df["bill_date"] = pd.to_datetime(df["bill_date"], errors="coerce", dayfirst=True)

# e. total rows hiding inside the data
df = df[~df["chain_name"].str.upper().isin(["TOTAL", "GRAND TOTAL", "SUM"])]
```

`errors="coerce"` turns bad values into `NaN` instead of raising — then **count the
NaNs it created** and report them. Silent coercion is how wrong numbers reach a deck.

```python
bad_rows = df["offtake_value"].isna().sum()
if bad_rows:
    print(f"WARNING: {bad_rows:,} rows had unparseable offtake_value")
```

## 4. Derive the Indian FY — never hardcode

This is the exact helper from `scripts/build_dashboard_data.py:42` — import it rather
than re-implementing it:

```python
def fy_tag_from_ym(year, month):
    """Calendar (year, month) -> 'FY27' style tag. Apr-2026 -> FY27; Mar-2026 -> FY26."""
    return f"FY{(year + 1 if month >= 4 else year) % 100:02d}"


df["fy_tag"] = [fy_tag_from_ym(d.year, d.month) for d in df["bill_date"]]
df["fy_month_index"] = (df["bill_date"].dt.month - 4) % 12   # 0 = Apr ... 11 = Mar
df["quarter"] = "Q" + (df["fy_month_index"] // 3 + 1).astype(str)
```

Sort months by `fy_month_index`, never alphabetically — alphabetical puts Apr after
Aug and every trend chart lies.

Note the two casings in this repo: the Python helper returns `FY27`, while the
`data.js` block keys are lowercase (`total_fy27`, `monthly_fy27`, `months_fy27`).
Lowercase with `.lower()` at the point where you build a key, not at the source.

## 5. Aggregate to a stated grain

```python
GRAIN = ["fy_tag", "month_label", "chain_name"]

agg = (
    df.groupby(GRAIN, as_index=False, dropna=False)
      .agg(
          offtake_value_inr=("offtake_value", "sum"),
          offtake_units=("offtake_qty", "sum"),
          selling_stores=("site_code", "nunique"),
      )
)
```

`dropna=False` matters — without it, rows whose chain is blank vanish and the total no
longer ties to source. Named aggregation (`new_col=("src_col", "func")`) keeps column
names explicit; never rely on the MultiIndex that plain `.agg()` produces.

Always reconcile after aggregating:

```python
assert np.isclose(agg["offtake_value_inr"].sum(), df["offtake_value"].sum()), \
    "aggregation lost value — check for NaN keys"
```

## 6. Merge with validation

```python
merged = agg.merge(
    dim_chain,
    on="chain_name",
    how="left",
    validate="many_to_one",   # raises if dim_chain has duplicate chain_name
    indicator=True,
)

unmapped = merged.loc[merged["_merge"] == "left_only", "chain_name"].unique()
if len(unmapped):
    print(f"UNMAPPED chains ({len(unmapped)}): {list(unmapped)[:20]}")
merged = merged.drop(columns="_merge")
```

`validate=` and `indicator=True` together are the whole defence against row explosion
and silent mapping loss. Use `validate="one_to_one"`, `"many_to_one"` or `"one_to_many"`
deliberately — if you cannot name which one applies, you do not yet know your grains.

## 7. Growth, contribution, rank

```python
# YoY on a matched month index (safe when FY month coverage differs)
pivot = agg.pivot_table(
    index=["month_label", "chain_name"],
    columns="fy_tag",
    values="offtake_value_inr",
    aggfunc="sum",
).reset_index()

pivot["yoy_growth_pct"] = (pivot["fy27"] - pivot["fy26"]) / pivot["fy26"].replace(0, np.nan)

# contribution and cumulative contribution (ABC)
agg = agg.sort_values("offtake_value_inr", ascending=False)
agg["contribution_pct"] = agg["offtake_value_inr"] / agg["offtake_value_inr"].sum()
agg["cumulative_pct"] = agg["contribution_pct"].cumsum()
agg["abc_class"] = np.select(
    [agg["cumulative_pct"] <= 0.80, agg["cumulative_pct"] <= 0.95],
    ["A", "B"],
    default="C",
)

# rank within a group
agg["rank_in_zone"] = agg.groupby("zone_name")["offtake_value_inr"].rank(
    method="first", ascending=False
).astype(int)

# month-on-month within a chain, in FY month order
agg = agg.sort_values(["chain_name", "fy_month_index"])
agg["mom_growth_pct"] = agg.groupby("chain_name")["offtake_value_inr"].pct_change()
```

`.replace(0, np.nan)` before dividing is the pandas equivalent of `nullif` — it yields
`NaN` rather than `inf`, which then formats cleanly as "NA" instead of printing `inf`
on a slide.

## 8. Indian number formatting

Leadership reads ₹ Cr and Lac, and Indian digit grouping (`12,34,567`), not `1,234,567`.

```python
def to_crore(value: float, decimals: int = 1) -> str:
    """1234567 -> '0.1 Cr'"""
    return f"{value / 1e7:,.{decimals}f} Cr"


def to_lac(value: float, decimals: int = 1) -> str:
    return f"{value / 1e5:,.{decimals}f} L"


def indian_format(value: float) -> str:
    """1234567 -> '12,34,567' (last 3 digits, then groups of 2)."""
    sign = "-" if value < 0 else ""
    whole = f"{abs(value):.0f}"
    if len(whole) <= 3:
        return sign + whole
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return sign + ",".join(groups) + "," + tail


def pct(value: float, decimals: int = 1) -> str:
    """Growth with an explicit sign — leadership scans the sign first."""
    return "NA" if pd.isna(value) else f"{value * 100:+.{decimals}f}%"
```

Rules: absolute values in Cr with 1 decimal; growth as a signed percentage with 1
decimal; never mix units in one column; state the unit in the header, not in each cell.

## 9. Export

```python
with pd.ExcelWriter(out_path, engine="xlsxwriter") as writer:
    summary.to_excel(writer, sheet_name="Summary", index=False)
    detail.to_excel(writer, sheet_name="Detail", index=False)

    workbook = writer.book
    money = workbook.add_format({"num_format": "#,##0.0"})
    growth = workbook.add_format({"num_format": "+0.0%;-0.0%;0.0%"})

    sheet = writer.sheets["Summary"]
    sheet.set_column("A:A", 28)
    sheet.set_column("B:D", 14, money)
    sheet.set_column("E:E", 12, growth)
    sheet.freeze_panes(1, 1)
    sheet.autofilter(0, 0, len(summary), summary.shape[1] - 1)
```

Freeze panes, autofilter and a number format on every export — a raw dump gets
reformatted by hand by whoever receives it, which is where errors enter.

## 10. Charts

For any chart, load the host environment's `dataviz` skill first for colour and form choices. Mechanics:

```python
import matplotlib
matplotlib.use("Agg")            # required — headless, no display
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 5), dpi=150)
ax.bar(plot_df["month_label"], plot_df["offtake_value_inr"] / 1e7)
ax.set_ylabel("Offtake (₹ Cr)")
ax.set_title("MT offtake by month — FY27")
ax.spines[["top", "right"]].set_visible(False)
fig.tight_layout()
fig.savefig(out_png, bbox_inches="tight")
plt.close(fig)
```

`matplotlib.use("Agg")` before importing pyplot, and `plt.close(fig)` after saving —
without the close, a loop over 30 chains leaks memory and eventually fails.

## Script skeleton

Any script this skill produces follows this shape:

```python
"""One line: what this script produces and from what."""
from pathlib import Path
import argparse
import pandas as pd


def load(src: Path) -> pd.DataFrame: ...
def clean(df: pd.DataFrame) -> pd.DataFrame: ...
def transform(df: pd.DataFrame) -> pd.DataFrame: ...
def validate(raw: pd.DataFrame, out: pd.DataFrame) -> None:
    """Raise before writing anything if the output does not tie to source."""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    raw = load(args.src)
    out = transform(clean(raw))
    validate(raw, out)          # validate BEFORE writing
    out.to_excel(args.out, index=False)
    print(f"wrote {len(out):,} rows -> {args.out}")


if __name__ == "__main__":
    main()
```

Validate before writing, never after. A written bad file gets emailed.

