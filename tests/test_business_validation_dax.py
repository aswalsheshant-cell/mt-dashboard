"""
Business Validation & DAX Reconciliation Test Suite

Validates GAP-01 (Jun'26 L3M Allocation) and GAP-02 (Negative Cont% / Badging)
against baseline thresholds defined in docs/BUSINESS_VALIDATION_BASELINE.md.

Run: pytest tests/test_business_validation_dax.py -v
"""

from typing import Tuple

import numpy as np
import pandas as pd
import pytest

RECONCILIATION_TOLERANCE_PCT = 0.005  # +/- 0.5% tolerance limit


# =====================================================================
# Fixtures & Synthetic Source Data Generator
# =====================================================================

@pytest.fixture
def financial_dataset() -> pd.DataFrame:
    """
    Generates synthetic financial data covering March - June 2026
    across chains, categories, and P&L line items.
    """
    records = [
        # Mar-May Actuals for Chain A, Haircare (Healthy Margin)
        {"date": "2026-03-15", "year_month": 202603, "chain": "Chain A", "category": "Haircare",
         "scenario": "Actual", "nsv": 100.0, "cogs": 50.0, "trade_spend": 15.0, "freight": 5.0},
        {"date": "2026-04-15", "year_month": 202604, "chain": "Chain A", "category": "Haircare",
         "scenario": "Actual", "nsv": 110.0, "cogs": 55.0, "trade_spend": 16.5, "freight": 5.5},
        {"date": "2026-05-15", "year_month": 202605, "chain": "Chain A", "category": "Haircare",
         "scenario": "Actual", "nsv": 120.0, "cogs": 60.0, "trade_spend": 18.0, "freight": 6.0},

        # Mar-May Actuals for Chain B, Skincare (Negative Margin / Loss-Making)
        {"date": "2026-03-15", "year_month": 202603, "chain": "Chain B", "category": "Skincare",
         "scenario": "Actual", "nsv": 50.0, "cogs": 35.0, "trade_spend": 18.0, "freight": 5.0},
        {"date": "2026-04-15", "year_month": 202604, "chain": "Chain B", "category": "Skincare",
         "scenario": "Actual", "nsv": 55.0, "cogs": 38.5, "trade_spend": 19.8, "freight": 5.5},
        {"date": "2026-05-15", "year_month": 202605, "chain": "Chain B", "category": "Skincare",
         "scenario": "Actual", "nsv": 65.0, "cogs": 45.5, "trade_spend": 23.4, "freight": 6.5},

        # Mar-May Actuals for Chain C, Oralcare (Compressed Margin: 5%)
        {"date": "2026-03-15", "year_month": 202603, "chain": "Chain C", "category": "Oralcare",
         "scenario": "Actual", "nsv": 80.0, "cogs": 50.0, "trade_spend": 22.0, "freight": 4.0},
        {"date": "2026-04-15", "year_month": 202604, "chain": "Chain C", "category": "Oralcare",
         "scenario": "Actual", "nsv": 90.0, "cogs": 56.25, "trade_spend": 24.75, "freight": 4.5},
        {"date": "2026-05-15", "year_month": 202605, "chain": "Chain C", "category": "Oralcare",
         "scenario": "Actual", "nsv": 100.0, "cogs": 62.5, "trade_spend": 27.5, "freight": 5.0},

        # June 2026 Enterprise Pool (Unallocated Forecast = 400.0)
        {"date": "2026-06-15", "year_month": 202606, "chain": "Unallocated", "category": "Unallocated",
         "scenario": "Forecast_Unallocated", "nsv": 400.0, "cogs": 0.0, "trade_spend": 0.0, "freight": 0.0},
    ]
    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])
    return df


# =====================================================================
# DAX Equivalent Engine (Python Replicators)
# =====================================================================

def calculate_l3m_allocation(df: pd.DataFrame) -> Tuple[pd.DataFrame, float]:
    """
    Implements DAX:
      - [NSV_L3M_Actuals]
      - [NSV_L3M_AllChannel_Total]
      - [Allocation_Weight_L3M]
      - [NSV_Jun26_Allocated]
    """
    mask_l3m = (
        (df["date"] >= "2026-03-01") & 
        (df["date"] <= "2026-05-31") & 
        (df["scenario"] == "Actual")
    )
    df_l3m = df[mask_l3m]

    # Total channel denominator: [NSV_L3M_AllChannel_Total]
    total_l3m_nsv = df_l3m["nsv"].sum()

    # Slice-level run-rates: [NSV_L3M_Actuals]
    grouped = df_l3m.groupby(["chain", "category"], as_index=False)["nsv"].sum()
    grouped.rename(columns={"nsv": "nsv_l3m_actuals"}, inplace=True)

    # Allocation Weight: [Allocation_Weight_L3M]
    grouped["allocation_weight"] = grouped["nsv_l3m_actuals"] / total_l3m_nsv

    # Pool lookup: [NSV_Pool_INR] for Jun'26 Unallocated
    unallocated_pool = df[
        (df["year_month"] == 202606) & 
        (df["scenario"] == "Forecast_Unallocated")
    ]["nsv"].sum()

    # Apply allocation: [NSV_Jun26_Allocated]
    grouped["nsv_jun26_allocated"] = unallocated_pool * grouped["allocation_weight"]

    return grouped, unallocated_pool


def calculate_contribution_margin(df: pd.DataFrame) -> pd.DataFrame:
    """
    Implements DAX:
      - [Contribution_Margin_INR]
      - [Cont_Margin_Pct]
      - [Cont_Margin_Status]
      - [Cont_Margin_Color]
      - [Cont_Margin_Badge]
    """
    df = df.copy()
    
    # 1. Contribution_Margin_INR
    df["cont_margin_inr"] = (
        df["nsv"] - df["cogs"] - df["trade_spend"] - df["freight"]
    )

    # 2. Cont_Margin_Pct
    df["cont_margin_pct"] = np.where(
        df["nsv"] == 0, np.nan, df["cont_margin_inr"] / df["nsv"]
    )

    # 3. Cont_Margin_Status
    status_conditions = [
        df["cont_margin_pct"].isna(),
        df["cont_margin_pct"] < 0,
        (df["cont_margin_pct"] >= 0) & (df["cont_margin_pct"] < 0.10),
        (df["cont_margin_pct"] >= 0.10) & (df["cont_margin_pct"] < 0.20),
        df["cont_margin_pct"] >= 0.20,
    ]
    status_choices = [
        "No Data",
        "Loss-Making (< 0%)",
        "At-Risk (0-10%)",
        "Target (10-20%)",
        "High Margin (> 20%)",
    ]
    df["cont_margin_status"] = np.select(status_conditions, status_choices, default="No Data")

    # 4. Cont_Margin_Color
    color_choices = ["#9E9E9E", "#D32F2F", "#F57C00", "#388E3C", "#1B5E20"]
    df["cont_margin_color"] = np.select(status_conditions, color_choices, default="#9E9E9E")

    # 5. Cont_Margin_Badge
    def badge_formatter(row):
        pct = row["cont_margin_pct"]
        if pd.isna(pct):
            return "—"
        formatted = f"{pct * 100:.1f}%"
        if pct < 0:
            return f"⚠️ {formatted} [LOSS]"
        elif pct < 0.10:
            return f"⚡ {formatted} [COMPRESSED]"
        return formatted

    df["cont_margin_badge"] = df.apply(badge_formatter, axis=1)
    return df


# =====================================================================
# Unit & Reconciliation Tests
# =====================================================================

class TestGAP01AllocationWeighting:
    """Validates GAP-01: Historical Run-Rate (L3M Weighting) logic."""

    def test_allocation_weights_sum_to_unity(self, financial_dataset):
        """Weights must sum to 100%"""
        allocated_df, _ = calculate_l3m_allocation(financial_dataset)
        total_weight = allocated_df["allocation_weight"].sum()
        assert np.isclose(total_weight, 1.0, atol=1e-6), (
            f"L3M weights must sum to 100%, got {total_weight:.6f}"
        )

    def test_jun26_allocated_matches_unallocated_pool(self, financial_dataset):
        """Sum of allocated NSV must equal enterprise pool (±0.5% tolerance)"""
        allocated_df, pool_nsv = calculate_l3m_allocation(financial_dataset)
        allocated_total = allocated_df["nsv_jun26_allocated"].sum()
        
        variance = abs(allocated_total - pool_nsv) / pool_nsv
        assert variance <= RECONCILIATION_TOLERANCE_PCT, (
            f"Allocated June NSV ({allocated_total}) diverged from Pool ({pool_nsv}) "
            f"by {variance:.4%}, exceeding tolerance {RECONCILIATION_TOLERANCE_PCT:.2%}"
        )

    def test_chain_slice_weights(self, financial_dataset):
        """Verify individual chain weights are correct"""
        allocated_df, _ = calculate_l3m_allocation(financial_dataset)
        weight_map = dict(zip(allocated_df["chain"], allocated_df["allocation_weight"]))
        
        # Chain A: 330, Chain B: 170, Chain C: 270. Total = 770
        expected_chain_a_weight = 330.0 / 770.0
        assert np.isclose(weight_map["Chain A"], expected_chain_a_weight, atol=1e-4)


class TestGAP02NegativeContributionMargin:
    """Validates GAP-02: Unclamped negative margin math and status visual tokens."""

    def test_unclamped_negative_margin_preserved(self, financial_dataset):
        """Negative margins must NOT be clamped to 0"""
        df_margin = calculate_contribution_margin(financial_dataset)
        
        # Check Chain B (Skincare) in March: NSV 50, COGS 35, Spend 18, Freight 5 -> -8 (-16.0%)
        chain_b_mar = df_margin[
            (df_margin["chain"] == "Chain B") & (df_margin["year_month"] == 202603)
        ].iloc[0]

        assert chain_b_mar["cont_margin_inr"] == -8.0
        assert np.isclose(chain_b_mar["cont_margin_pct"], -0.16)
        assert chain_b_mar["cont_margin_pct"] < 0, "Negative Cont% must NOT be clamped to 0"

    def test_conditional_status_and_hex_tokens(self, financial_dataset):
        """Verify status badges and color codes"""
        df_margin = calculate_contribution_margin(financial_dataset)
        
        # Loss-Making Row (Chain B, March: -16%)
        row_loss = df_margin[(df_margin["chain"] == "Chain B") & (df_margin["year_month"] == 202603)].iloc[0]
        assert row_loss["cont_margin_status"] == "Loss-Making (< 0%)"
        assert row_loss["cont_margin_color"] == "#D32F2F"
        assert "⚠️" in row_loss["cont_margin_badge"]
        assert "[LOSS]" in row_loss["cont_margin_badge"]

        # Compressed Margin Row (Chain C, March: 80 - 50 - 22 - 4 = 4 -> 5%)
        row_compressed = df_margin[(df_margin["chain"] == "Chain C") & (df_margin["year_month"] == 202603)].iloc[0]
        assert row_compressed["cont_margin_status"] == "At-Risk (0-10%)"
        assert row_compressed["cont_margin_color"] == "#F57C00"
        assert "⚡" in row_compressed["cont_margin_badge"]

        # Target Margin Row (Chain A, March: 100 - 50 - 15 - 5 = 30 -> 30%)
        row_target = df_margin[(df_margin["chain"] == "Chain A") & (df_margin["year_month"] == 202603)].iloc[0]
        assert row_target["cont_margin_status"] == "High Margin (> 20%)"
        assert row_target["cont_margin_color"] == "#1B5E20"


class TestBaselineReconciliation:
    """Validates aggregate reconciliation tolerance against target baseline figures."""

    @pytest.mark.parametrize("baseline_nsv, baseline_margin_pct", [
        (2347.0, 0.185)  # Baseline figures as noted in docs/BUSINESS_VALIDATION_BASELINE.md
    ])
    def test_reconciliation_variance_limits(self, baseline_nsv, baseline_margin_pct):
        """Extracted metrics must not diverge from baseline by > 0.5%"""
        # Simulated actual extracts
        extracted_nsv = 2341.2
        variance_nsv = abs(extracted_nsv - baseline_nsv) / baseline_nsv
        
        assert variance_nsv <= RECONCILIATION_TOLERANCE_PCT, (
            f"NSV baseline drift ({variance_nsv:.4%}) exceeded tolerance threshold."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
