#!/usr/bin/env python3
"""
NPI Sales Data Loaders — Extract article-level primary & offtake data for performance fact computation.

Provides:
  - load_article_primary_sales(): Extract article-level primary by month/chain/article
  - load_article_offtake_sales(): Extract article-level offtake by month/chain/article
  - match_articles_to_npi(): Link article sales data to NPI master by article_id
  - compute_npi_performance_facts(): Orchestrate fact computation across all dimensions
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import pandas as pd
import re


def normalize_article_id(article_name: str) -> str:
    """
    Generate a normalized article ID from article name/description.

    Examples:
        "Aqualogica Face Wash 50ml" → "AQ_FW_50ML"
        "Mamaearth Hair Oil 200ml" → "ME_HS_200ML"

    For now, returns the input as-is; in production, would use a mapping table.
    """
    return article_name.strip()


def load_article_primary_sales(primary_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract article-level primary sales from raw primary data.

    Args:
        primary_df: DataFrame from detail_records_real() or primary_article.xlsb
                   Expected columns: Month, FY, brand, category, sub_category,
                   Zone, Chain name for Dashboard, Inv. Net value(LOC), EAN No.,
                   Description, Inv Qty

    Returns:
        DataFrame with columns:
            article_id, article_name, month_label, month, fy, chain,
            primary_nsv_lakhs, primary_qty, zone, brand, category
    """
    if primary_df is None or len(primary_df) == 0:
        return pd.DataFrame(columns=[
            'article_id', 'article_name', 'month_label', 'month', 'fy', 'chain',
            'primary_nsv_lakhs', 'primary_qty', 'zone', 'brand', 'category'
        ])

    df = primary_df.copy()

    # Ensure required columns exist
    required_cols = ['Month', 'FY', 'brand', 'category', 'sub_category',
                     'Zone', 'Inv. Net value(LOC)', 'Inv Qty', 'Description']

    # Find chain column (various names possible)
    chain_col = None
    for c in df.columns:
        if 'chain' in c.lower():
            chain_col = c
            break

    if chain_col is None:
        print("⚠ Warning: No chain column found in primary data, using 'Unknown'")
        df['Chain'] = 'Unknown'
        chain_col = 'Chain'

    # Generate article_id from EAN or Description
    if 'EAN No.' in df.columns:
        df['article_id'] = df['EAN No.'].astype(str).str.strip()
        df['article_id'] = df['article_id'].where(df['article_id'] != '', None)
    else:
        df['article_id'] = None

    # Fallback to Description if no EAN
    df['article_id'] = df.apply(
        lambda row: str(row['Description']).replace(' ', '_')[:50]
        if pd.isna(row['article_id']) or row['article_id'] == ''
        else row['article_id'],
        axis=1
    )
    df['article_name'] = df['Description'].astype(str).str.strip()

    # Normalize month label (e.g., "May'25" → "May-25")
    def normalize_month(m):
        if pd.isna(m):
            return None
        s = str(m).strip()
        s = re.sub(r"'", "-", s)  # May'25 → May-25
        return s

    df['month_label'] = df['Month'].apply(normalize_month)
    df['fy'] = df['FY'].astype(str).str.strip()
    df['chain'] = df[chain_col].astype(str).str.strip() if chain_col else 'Unknown'

    # Convert NSV to Lakh
    df['primary_nsv_lakhs'] = pd.to_numeric(df['Inv. Net value(LOC)'], errors='coerce').fillna(0.0) / 1e5
    df['primary_qty'] = pd.to_numeric(df['Inv Qty'], errors='coerce').fillna(0).astype(int)
    df['zone'] = df['Zone'].astype(str).str.strip() if 'Zone' in df.columns else 'Unknown'
    df['brand'] = df['brand'].astype(str).str.strip()
    df['category'] = df['category'].astype(str).str.strip()

    # Filter: keep only rows with valid article_id, month, and chain
    df = df[df['article_id'].notna() & df['month_label'].notna() & df['chain'].notna()]

    # Aggregate by article/month/chain (sum NSV, aggregate qty)
    result = df.groupby(['article_id', 'article_name', 'month_label', 'fy', 'chain']).agg({
        'primary_nsv_lakhs': 'sum',
        'primary_qty': 'sum',
        'zone': lambda x: ','.join(x.dropna().unique()),
        'brand': 'first',
        'category': 'first',
    }).reset_index()

    result['month'] = result['month_label'].str.split('-').str[0]  # Extract month abbr

    return result[['article_id', 'article_name', 'month_label', 'month', 'fy', 'chain',
                   'primary_nsv_lakhs', 'primary_qty', 'zone', 'brand', 'category']]


def load_article_offtake_sales(src_dir: Path) -> pd.DataFrame:
    """
    Extract article-level offtake sales from store×article extracts.

    Args:
        src_dir: Directory containing offtake_store_article_*.xlsb/.csv files

    Returns:
        DataFrame with columns:
            article_id, article_name, month_label, month, fy, chain,
            offtake_units, offtake_nsv_lakhs, stocking_stores, zone
    """
    frames = []

    # Find all offtake_store_article files
    offtake_files = sorted([
        *src_dir.glob("offtake_store_article_*.xlsb"),
        *src_dir.glob("offtake_store_article_*.xlsx"),
        *src_dir.glob("offtake_store_article_*.csv")
    ])

    if not offtake_files:
        return pd.DataFrame(columns=[
            'article_id', 'article_name', 'month_label', 'month', 'fy', 'chain',
            'offtake_units', 'offtake_nsv_lakhs', 'stocking_stores', 'zone'
        ])

    for fp in offtake_files:
        try:
            if fp.suffix.lower() == '.csv':
                df = pd.read_csv(fp, low_memory=False)
            else:
                # Try header=0 first, fallback to header=1
                try:
                    df = pd.read_excel(fp, sheet_name=0, header=0, engine='pyxlsb' if 'xlsb' in fp.suffix else None)
                except:
                    df = pd.read_excel(fp, sheet_name=0, header=1, engine='pyxlsb' if 'xlsb' in fp.suffix else None)

            # Normalize column names
            df.columns = [str(c).strip() for c in df.columns]

            # Check for required columns
            if not {'Chain Name', 'Month', 'Article'} <= set(df.columns):
                # Try alternate column names
                if 'SKU' in df.columns:
                    df['Article'] = df['SKU']
                elif 'EAN' in df.columns:
                    df['Article'] = df['EAN']
                else:
                    continue  # Skip if no article column

            df = df[df['Chain Name'].notna() & df['Month'].notna() & df['Article'].notna()]

            # Extract article_id and month
            df['article_id'] = df['Article'].astype(str).str.strip()
            df['article_id'] = df['article_id'].str.replace(r'[^\w]', '_', regex=True)[:50]
            df['article_name'] = df['Article'].astype(str).str.strip()

            # Normalize month
            def normalize_month(m):
                if pd.isna(m):
                    return None
                s = str(m).strip()
                s = re.sub(r"'", "-", s)
                return s

            df['month_label'] = df['Month'].apply(normalize_month)
            df['chain'] = df['Chain Name'].astype(str).str.strip()
            df['zone'] = df['Zone'].astype(str).str.strip() if 'Zone' in df.columns else 'Unknown'

            # Units and NSV
            unit_col = next((c for c in df.columns if 'unit' in c.lower()), None)
            nsv_col = next((c for c in df.columns if 'nsv' in c.lower() or 'value' in c.lower()), None)
            qty_col = next((c for c in df.columns if 'qty' in c.lower() or 'quantity' in c.lower()), None)

            df['offtake_units'] = pd.to_numeric(df[unit_col], errors='coerce').fillna(0).astype(int) if unit_col else 0
            df['offtake_nsv_lakhs'] = pd.to_numeric(df[nsv_col], errors='coerce').fillna(0.0) if nsv_col else 0.0

            # Count stocking stores (distinct stores with non-zero offtake)
            store_col = next((c for c in df.columns if 'store' in c.lower()), None)
            if store_col:
                # Count distinct stores per article/chain/month, then merge back
                store_counts = df.groupby(['article_id', 'chain', 'month_label'])[store_col].nunique().reset_index(name='stocking_stores')
                df = df.merge(store_counts, on=['article_id', 'chain', 'month_label'], how='left')
                # Fill any missing with 0
                df['stocking_stores'] = df['stocking_stores'].fillna(0).astype(int)
            else:
                # Fallback: count as 1 if we have any offtake
                df['stocking_stores'] = (df['offtake_units'] > 0).astype(int)

            # Infer FY from month
            def infer_fy(month_label):
                if pd.isna(month_label):
                    return None
                # Extract year from month_label (e.g., "Jun-26" → 26)
                m = re.search(r'-(\d{2})$', str(month_label))
                if m:
                    year = 2000 + int(m.group(1))
                    month = str(month_label)[:3]  # First 3 chars
                    month_num = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                 'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                    mn = month_num.get(month.lower(), 0)
                    if mn >= 4:
                        return f"FY{(year + 1) % 100:02d}"
                    else:
                        return f"FY{year % 100:02d}"
                return None

            df['fy'] = df['month_label'].apply(infer_fy)
            df['month'] = df['month_label'].str.split('-').str[0]

            # Aggregate by article/month/chain
            agg_df = df.groupby(['article_id', 'article_name', 'month_label', 'fy', 'chain']).agg({
                'offtake_units': 'sum',
                'offtake_nsv_lakhs': 'sum',
                'stocking_stores': 'sum',
                'zone': lambda x: ','.join(x.dropna().unique()),
                'month': 'first',
            }).reset_index()

            frames.append(agg_df)
            print(f"  ✓ Loaded {len(agg_df)} offtake facts from {fp.name}")

        except Exception as e:
            print(f"  ⚠ Error loading {fp.name}: {e}")
            continue

    if not frames:
        return pd.DataFrame(columns=[
            'article_id', 'article_name', 'month_label', 'month', 'fy', 'chain',
            'offtake_units', 'offtake_nsv_lakhs', 'stocking_stores', 'zone'
        ])

    result = pd.concat(frames, ignore_index=True)
    return result[['article_id', 'article_name', 'month_label', 'month', 'fy', 'chain',
                   'offtake_units', 'offtake_nsv_lakhs', 'stocking_stores', 'zone']]


def match_articles_to_npi(primary_sales: pd.DataFrame,
                          offtake_sales: pd.DataFrame,
                          npi_master: dict) -> dict:
    """
    Match article-level sales data to NPI master articles by article_id.

    Returns:
        {
            "matched": {
                "AQ_FW_50ML": {
                    "article_data": {...},
                    "npi_article": {...},
                    "matched_by": "exact" | "fuzzy"
                }
            },
            "unmatched_sales": [...],
            "unmatched_npi": [...]
        }
    """
    npi_ids = {a['article_id']: a for a in npi_master.get('npi_articles', [])}

    # Handle empty DataFrames
    primary_ids = set(primary_sales['article_id'].unique()) if len(primary_sales) > 0 else set()
    offtake_ids = set(offtake_sales['article_id'].unique()) if len(offtake_sales) > 0 else set()
    sales_ids = primary_ids | offtake_ids

    matched = {}
    unmatched_sales = []

    for article_id in sales_ids:
        if article_id in npi_ids:
            matched[article_id] = {
                'npi_article': npi_ids[article_id],
                'matched_by': 'exact'
            }
        else:
            # Try fuzzy matching on article_name
            sales_row = primary_sales[primary_sales['article_id'] == article_id]
            if len(sales_row) > 0:
                unmatched_sales.append(article_id)

    unmatched_npi = [a for a in npi_ids if a not in matched]

    return {
        'matched': matched,
        'unmatched_sales': unmatched_sales,
        'unmatched_npi': unmatched_npi,
        'n_matched': len(matched),
        'n_unmatched_sales': len(unmatched_sales),
        'n_unmatched_npi': len(unmatched_npi)
    }


def compute_npi_performance_facts(primary_sales: pd.DataFrame,
                                   offtake_sales: pd.DataFrame,
                                   npi_master: dict,
                                   universe_df: pd.DataFrame | None = None,
                                   reference_date: str | None = None) -> list[dict]:
    """
    Compute NPI performance facts from sales data.

    Args:
        primary_sales: Output from load_article_primary_sales()
        offtake_sales: Output from load_article_offtake_sales()
        npi_master: Enriched NPI master from enrich_npi_master_with_lifecycle()
        universe_df: Store universe DataFrame (optional, for distribution calc)
        reference_date: Reference date (default: today)

    Returns:
        List of performance facts ready for aggregation
    """
    from npi_performance import NPIPerformanceCalculator

    calc = NPIPerformanceCalculator(
        npi_master=npi_master,
        detail_meta=None,
        universe_df=universe_df,
        reference_date=reference_date
    )

    # Join primary and offtake on article_id/month_label/chain
    # Note: merge only on ID + date + chain, not article_name (names may differ between sources)
    if len(primary_sales) > 0 and len(offtake_sales) > 0:
        combined = primary_sales.merge(
            offtake_sales[['article_id', 'month_label', 'chain', 'offtake_units', 'offtake_nsv_lakhs', 'stocking_stores', 'zone', 'fy']],
            on=['article_id', 'month_label', 'chain'],
            how='outer',
            suffixes=('', '_offtake')
        )
        # Reconcile FY if both present
        if 'fy' in combined.columns and 'fy_offtake' in combined.columns:
            combined['fy'] = combined['fy'].fillna(combined['fy_offtake'])
            combined = combined.drop('fy_offtake', axis=1)
    elif len(primary_sales) > 0:
        combined = primary_sales.copy()
        combined['offtake_units'] = 0
        combined['stocking_stores'] = None
    elif len(offtake_sales) > 0:
        combined = offtake_sales.copy()
        combined['primary_nsv_lakhs'] = 0.0
    else:
        return []

    # Compute facts
    facts = []
    for _, row in combined.iterrows():
        fact = calc.derive_performance_facts(
            article_id=row['article_id'],
            article_name=row['article_name'],
            chain=row['chain'],
            month_label=row['month_label'],
            primary_nsv_lakhs=row.get('primary_nsv_lakhs'),
            offtake_units=row.get('offtake_units'),
            stocking_stores=row.get('stocking_stores')
        )
        facts.append(fact)

    return facts


if __name__ == "__main__":
    print("NPI Sales Data Loaders — ready for integration")
