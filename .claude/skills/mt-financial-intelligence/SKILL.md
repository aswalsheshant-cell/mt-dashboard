---
name: mt-financial-intelligence
description: |
  P&L analysis, outlier detection, channel profitability, and trade spend ROI for MT leadership.
  Use this skill when the user asks to: analyze Gross Margin %, detect P&L anomalies, calculate
  trade spend ROI, rank channels by profitability, identify losing products, waterfall GM% by
  driver, or validate P&L numbers against SAP FI. Also triggers on: "P&L analysis", "margin
  waterfall", "gross margin drivers", "trade spend ROI", "channel profitability", "P&L
  anomaly", "why did margin drop", "which products lose money", "compare channels by GM%",
  "expense matching", "FI reconciliation".
  Do NOT use for dashboard UI, SQL queries, or Power BI DAX — route those to relevant skills.
---
# MT Financial Intelligence

Analyze Gross Margin, detect P&L anomalies, calculate channel profitability and trade spend ROI,
and validate P&L data integrity for leadership decision-making.

## P&L Outlier Detection Tier

**S — Always enforce:**
- Explicit outlier criteria (not subjective); state ±σ thresholds clearly
- Null handling: `np.isnan()` before flagging, never silent NaN propagation
- Preserve context: report row grain (Month + Chain + Category), not just the metric
- Double-check before reporting: validate metric calculation matches source
- Log outliers with business context ("Margin fell 800 bps due to Promo spending")

**A — Outlier patterns (use in combination):**
- **Statistical:** GM% outside mean ± 2σ by (FY, Chain, Category)
- **Trend:** GM% changed >500 bps MoM (investigate seasonal vs structural)
- **Comparative:** Chain GM% <2% below peer median (benchmark anomaly)
- **Structural:** Category contribution >50% of total NSV (concentration risk)

**B — Waterfall diagnostics:**
- NSV-driven (volume, price, mix) vs Expense-driven (trade spend, COGS, freight)
- Month-to-month: delta NSV + delta COGS + delta Trade Spend = delta GM%
- Channel comparison: rank by GM% contribution (not raw GM₹)

**C — Report as:**
- What: "Mamaearth GM% dropped to 12.5% (was 15.2% prior month)"
- Why: "Promo spend jumped 40%, NSV +10%, expense ratio +320 bps"
- Risk: "If promo continues, FY27 GM% targets at risk (-150 bps impact)"

## Core P&L Analysis Functions

### 1. Gross Margin % Waterfall by Driver

```python
def gm_waterfall_by_driver(pnl_df: pd.DataFrame, fy_tag: str, chain: str, 
                            category: str = None) -> dict:
    """Decompose GM% change into: NSV growth, COGS impact, Trade Spend impact.
    
    Returns: {'base_gm_pct': float, 'nsv_effect': float, 'cogs_effect': float,
              'trade_spend_effect': float, 'other_effect': float, 'ending_gm_pct': float}
    
    Usage:
        result = gm_waterfall_by_driver(pnl_df, 'FY27', 'Modern Trade', 'Hair Care')
        print(f"GM% change: {result['base_gm_pct']:.1f}% → {result['ending_gm_pct']:.1f}%")
    """
    
    # Filter to (FY, Chain, Category)
    filtered = pnl_df[
        (pnl_df['fy_tag'] == fy_tag) & 
        (pnl_df['chain_name'] == chain)
    ].copy()
    
    if category:
        filtered = filtered[filtered['category'] == category]
    
    if filtered.empty:
        raise ValueError(f"No data for {fy_tag} / {chain} / {category}")
    
    # Get prior and current month
    filtered['month_num'] = filtered['month_label'].map(lambda x: month_to_num(x))
    current = filtered.nlargest(1, 'month_num').iloc[0]
    prior = filtered.nlargest(2, 'month_num').iloc[1] if len(filtered) >= 2 else None
    
    if prior is None:
        return {"error": "Only one month available for comparison"}
    
    # Waterfall calculation
    # Base: Prior month GM%
    prior_gm_pct = 100 * (prior['gross_margin_lakhs'] / max(prior['nsv_lakhs'], 1))
    current_gm_pct = 100 * (current['gross_margin_lakhs'] / max(current['nsv_lakhs'], 1))
    
    # Effect calculations (simplified; refine for your P&L structure)
    # Assume: GM = NSV - COGS - Trade Spend
    prior_gm = prior['gross_margin_lakhs']
    current_gm = current['gross_margin_lakhs']
    
    # NSV impact: fixed COGS % model
    nsv_delta = current['nsv_lakhs'] - prior['nsv_lakhs']
    assumed_cogs_pct = prior['cogs_lakhs'] / max(prior['nsv_lakhs'], 1) if 'cogs_lakhs' in current else 0.65
    nsv_effect_gm = nsv_delta * (1 - assumed_cogs_pct) * 100 / max(current['nsv_lakhs'], 1)
    
    # COGS impact
    cogs_delta = current['cogs_lakhs'] - prior['cogs_lakhs'] if 'cogs_lakhs' in current else 0
    cogs_effect_gm = -cogs_delta * 100 / max(current['nsv_lakhs'], 1)
    
    # Trade Spend impact
    spend_delta = current['trade_spend_lakhs'] - prior['trade_spend_lakhs'] if 'trade_spend_lakhs' in current else 0
    spend_effect_gm = -spend_delta * 100 / max(current['nsv_lakhs'], 1)
    
    # Other (residual)
    other_effect = (current_gm_pct - prior_gm_pct) - (nsv_effect_gm + cogs_effect_gm + spend_effect_gm)
    
    return {
        'base_gm_pct': round(prior_gm_pct, 1),
        'nsv_effect_bps': round(nsv_effect_gm * 100, 0),
        'cogs_effect_bps': round(cogs_effect_gm * 100, 0),
        'trade_spend_effect_bps': round(spend_effect_gm * 100, 0),
        'other_effect_bps': round(other_effect * 100, 0),
        'ending_gm_pct': round(current_gm_pct, 1),
        'gm_change_bps': round((current_gm_pct - prior_gm_pct) * 100, 0)
    }
```

### 2. Channel Profitability Quadrant (GM% vs NSV Growth)

```python
def channel_profitability_quadrant(pnl_df: pd.DataFrame, fy_tag: str, 
                                    gm_threshold: float = 15.0) -> pd.DataFrame:
    """Rank channels by (GM%, NSV growth). Identify stars (high growth, high margin),
    cash cows (low growth, high margin), dogs (low margin), and question marks.
    
    Returns: DataFrame with quadrant assignment and strategic implication.
    """
    
    # Aggregate by (FY, Chain)
    grouped = pnl_df[pnl_df['fy_tag'] == fy_tag].groupby('chain_name').agg({
        'nsv_lakhs': 'sum',
        'gross_margin_lakhs': 'sum',
        'trade_spend_lakhs': 'sum'
    }).reset_index()
    
    # Get prior FY for growth
    prior_fy = f"FY{int(fy_tag[2:]) - 1}"
    prior_grouped = pnl_df[pnl_df['fy_tag'] == prior_fy].groupby('chain_name')['nsv_lakhs'].sum()
    grouped['prior_nsv'] = grouped['chain_name'].map(prior_grouped)
    grouped['nsv_growth_pct'] = 100 * (grouped['nsv_lakhs'] - grouped['prior_nsv']) / grouped['prior_nsv'].clip(lower=1)
    
    # GM%
    grouped['gm_pct'] = 100 * grouped['gross_margin_lakhs'] / grouped['nsv_lakhs'].clip(lower=1)
    
    # Quadrant assignment
    def assign_quadrant(row):
        if row['gm_pct'] >= gm_threshold and row['nsv_growth_pct'] >= 0:
            return "STAR (High Margin, Growth)"
        elif row['gm_pct'] >= gm_threshold and row['nsv_growth_pct'] < 0:
            return "CASH COW (High Margin, Stable)"
        elif row['gm_pct'] < gm_threshold and row['nsv_growth_pct'] >= 0:
            return "QUESTION MARK (Low Margin, Growth)"
        else:
            return "DOG (Low Margin, Decline)"
    
    grouped['quadrant'] = grouped.apply(assign_quadrant, axis=1)
    
    return grouped[['chain_name', 'nsv_lakhs', 'gm_pct', 'nsv_growth_pct', 
                    'trade_spend_lakhs', 'quadrant']].sort_values('nsv_lakhs', ascending=False)
```

### 3. Trade Spend ROI Calculator

```python
def calculate_trade_spend_roi(pnl_df: pd.DataFrame, fy_tag: str, 
                               chain: str = None) -> dict:
    """Calculate trade spend ROI: (NSV / Trade Spend) ratio by channel.
    
    High ROI >3.0x = Efficient channel
    Medium ROI 1.5–3.0x = Normal channel
    Low ROI <1.5x = Inefficient (losing money on promotions)
    
    Returns: {'channel': str, 'nsv': float, 'trade_spend': float, 'roi_multiple': float,
              'efficiency_rating': str, 'recommendation': str}
    """
    
    filtered = pnl_df[pnl_df['fy_tag'] == fy_tag].copy()
    
    if chain:
        filtered = filtered[filtered['chain_name'] == chain]
    
    # Aggregate
    agg = filtered.groupby('chain_name').agg({
        'nsv_lakhs': 'sum',
        'trade_spend_lakhs': 'sum',
        'gross_margin_lakhs': 'sum'
    }).reset_index()
    
    agg['roi_multiple'] = agg['nsv_lakhs'] / agg['trade_spend_lakhs'].clip(lower=1)
    agg['spend_as_pct_nsv'] = 100 * agg['trade_spend_lakhs'] / agg['nsv_lakhs'].clip(lower=1)
    agg['gm_pct'] = 100 * agg['gross_margin_lakhs'] / agg['nsv_lakhs'].clip(lower=1)
    
    def rate_efficiency(roi):
        if roi >= 3.0:
            return "EFFICIENT (ROI >= 3.0x)"
        elif roi >= 1.5:
            return "NORMAL (ROI 1.5–3.0x)"
        else:
            return "AT RISK (ROI < 1.5x)"
    
    def recommend(row):
        if row['roi_multiple'] < 1.5:
            return f"⚠ Reduce spend or increase NSV. Current: ₹{row['trade_spend_lakhs']:.1f}L " \
                   f"for ₹{row['nsv_lakhs']:.1f}L NSV. GM%: {row['gm_pct']:.1f}%"
        elif row['roi_multiple'] >= 3.0 and row['spend_as_pct_nsv'] < 5:
            return f"✓ Efficient. Consider increased investment if category prioritized."
        else:
            return f"~ Maintain current spend level."
    
    agg['efficiency_rating'] = agg['roi_multiple'].map(rate_efficiency)
    agg['recommendation'] = agg.apply(recommend, axis=1)
    
    return agg[['chain_name', 'nsv_lakhs', 'trade_spend_lakhs', 'roi_multiple', 
                'gm_pct', 'efficiency_rating', 'recommendation']].to_dict('records')
```

### 4. Losing Products Detection

```python
def identify_losing_products(pnl_df: pd.DataFrame, fy_tag: str, 
                              gm_pct_threshold: float = 0.0) -> pd.DataFrame:
    """Identify products (EAN/Category/Brand) with negative or near-zero GM%.
    
    Returns: DataFrame of losers with NSV, COGS, GM%, recommendation to exit or reprrice.
    """
    
    filtered = pnl_df[pnl_df['fy_tag'] == fy_tag].copy()
    
    # Aggregate to (Brand, Category) or (EAN) level if available
    grain = 'brand_name' if 'brand_name' in filtered else 'category'
    
    grouped = filtered.groupby(grain).agg({
        'nsv_lakhs': 'sum',
        'cogs_lakhs': 'sum' if 'cogs_lakhs' in filtered else 0,
        'gross_margin_lakhs': 'sum',
        'trade_spend_lakhs': 'sum' if 'trade_spend_lakhs' in filtered else 0,
        'chain_name': 'nunique'  # Number of chains stocking
    }).reset_index()
    
    grouped['gm_pct'] = 100 * grouped['gross_margin_lakhs'] / grouped['nsv_lakhs'].clip(lower=0.1)
    grouped['spend_pct_nsv'] = 100 * grouped['trade_spend_lakhs'] / grouped['nsv_lakhs'].clip(lower=1)
    
    # Flag losers
    losers = grouped[grouped['gm_pct'] < gm_pct_threshold].copy()
    
    if losers.empty:
        return pd.DataFrame()
    
    def action(row):
        if row['gm_pct'] < -5:
            return "EXIT (significant loss)"
        elif row['gm_pct'] < 0:
            return "REPRICE (offset loss)"
        elif row['spend_pct_nsv'] > 15 and row['gm_pct'] < 5:
            return "REDUCE SPEND (high promo, low margin)"
        else:
            return "MONITOR (close to breakeven)"
    
    losers['action'] = losers.apply(action, axis=1)
    
    return losers.sort_values('gm_pct').head(20)
```

### 5. P&L Data Integrity Validation

```python
def validate_pnl_completeness(pnl_df: pd.DataFrame, fy_tag: str, 
                               tolerance_pct: float = 1.0) -> dict:
    """Validate that P&L data is complete and reconciles:
    - NSV, COGS, Trade Spend fields present and populated
    - Gross Margin = NSV - COGS - Trade Spend (within tolerance)
    - No NaN values in key columns
    
    Returns: {'status': 'PASS'/'FAIL', 'issues': [], 'reconciliation_error_pct': float}
    """
    
    required_cols = ['nsv_lakhs', 'gross_margin_lakhs']
    if 'cogs_lakhs' not in pnl_df.columns:
        pnl_df['cogs_lakhs'] = 0
    if 'trade_spend_lakhs' not in pnl_df.columns:
        pnl_df['trade_spend_lakhs'] = 0
    
    issues = []
    
    # Check for required columns
    for col in required_cols:
        if col not in pnl_df.columns:
            issues.append(f"Missing required column: {col}")
    
    # Filter to FY
    filtered = pnl_df[pnl_df['fy_tag'] == fy_tag].copy()
    
    if filtered.empty:
        issues.append(f"No data for {fy_tag}")
        return {'status': 'FAIL', 'issues': issues, 'reconciliation_error_pct': -1}
    
    # Check for nulls
    for col in ['nsv_lakhs', 'gross_margin_lakhs', 'cogs_lakhs', 'trade_spend_lakhs']:
        null_count = filtered[col].isnull().sum()
        if null_count > 0:
            issues.append(f"{null_count} null values in {col}")
    
    # Reconciliation: GM = NSV - COGS - Trade Spend
    filtered['expected_gm'] = (filtered['nsv_lakhs'] - filtered['cogs_lakhs'] - 
                                filtered['trade_spend_lakhs'])
    filtered['gm_variance'] = filtered['gross_margin_lakhs'] - filtered['expected_gm']
    
    total_gm = filtered['gross_margin_lakhs'].sum()
    variance = filtered['gm_variance'].sum()
    error_pct = 100 * variance / max(abs(total_gm), 1)
    
    if abs(error_pct) > tolerance_pct:
        issues.append(f"P&L reconciliation error: {error_pct:.2f}% (tolerance: {tolerance_pct}%)")
    
    status = 'PASS' if not issues else 'FAIL'
    
    return {
        'status': status,
        'issues': issues,
        'reconciliation_error_pct': error_pct,
        'rows_validated': len(filtered)
    }
```

## SAP FI Reconciliation Pattern

```python
def reconcile_to_sap_fi(dashboard_pnl: pd.DataFrame, sap_fi_export: pd.DataFrame, 
                        tolerance_pct: float = 1.0) -> dict:
    """Compare dashboard P&L totals to SAP FI master data.
    
    Dashboard grain: (FY, Chain, Month, Category)
    SAP grain: (FY, Chain, Month) from FI module
    
    Return: {'status': 'MATCH'/'VARIANCE', 'dashboard_total': float, 'sap_total': float,
             'variance': float, 'variance_pct': float, 'details': DataFrame}
    """
    
    # Aggregate dashboard to SAP grain
    db_agg = dashboard_pnl.groupby(['fy_tag', 'chain_name', 'month_label']).agg({
        'gross_margin_lakhs': 'sum',
        'nsv_lakhs': 'sum'
    }).reset_index()
    
    # Join to SAP
    reconciled = db_agg.merge(
        sap_fi_export,
        how='outer',
        on=['fy_tag', 'chain_name', 'month_label'],
        suffixes=('_dashboard', '_sap')
    )
    
    # Variance
    reconciled['variance_lakhs'] = reconciled['gross_margin_lakhs_dashboard'] - \
                                   reconciled['gross_margin_lakhs_sap']
    reconciled['variance_pct'] = 100 * reconciled['variance_lakhs'] / \
                                 reconciled['gross_margin_lakhs_sap'].clip(lower=1)
    
    matches = (reconciled['variance_pct'].abs() <= tolerance_pct).sum()
    total = len(reconciled)
    
    dashboard_total = dashboard_pnl['gross_margin_lakhs'].sum()
    sap_total = sap_fi_export['gross_margin_lakhs_sap'].sum()
    variance = dashboard_total - sap_total
    variance_pct = 100 * variance / max(abs(sap_total), 1)
    
    status = 'MATCH' if abs(variance_pct) <= tolerance_pct else 'VARIANCE'
    
    return {
        'status': status,
        'dashboard_total': round(dashboard_total, 2),
        'sap_total': round(sap_total, 2),
        'variance': round(variance, 2),
        'variance_pct': round(variance_pct, 2),
        'matches': matches,
        'total': total,
        'details': reconciled[reconciled['variance_pct'].abs() > tolerance_pct].sort_values('variance_lakhs', ascending=False)
    }
```

## Response Format
- Show complete analysis with context (chain, FY, period)
- Always include tolerance thresholds and interpretation
- Flag as concern if ROI <1.5x or GM% <5% or variance >1%
- Recommend action (e.g., "Reduce spend 20% to hit ROI 2.0x")
- Never hide variance—always report reconciliation error
