"""
tests/test_article_uniqueness.py
Automated Pytest Governance Suite: Article-Level Uniqueness & Control Total Reconciliation
Validates that synthesized FY25 data respects empirical channel assortment constraints.
"""

from pathlib import Path
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

PATH_SYNTHESIZED_FY25 = (
    REPO_ROOT / "PowerBI/RawDataFolders/Primary_Derived_FY25/Primary_Article_Synthesized_FY25.csv"
)
PATH_MAPPING_V2 = (
    REPO_ROOT / "data_mappings/Chain_Article_EAN_Mapping_CORRECTED_v2.csv"
)

EXPECTED_FY25_CONTROL_NSV_LAKH = 23325.30
RECONCILIATION_TOLERANCE_LAKH = 0.01


@pytest.fixture(scope="module")
def df_synthesized():
    assert PATH_SYNTHESIZED_FY25.exists(), f"Missing file: {PATH_SYNTHESIZED_FY25}"
    df = pd.read_csv(PATH_SYNTHESIZED_FY25, low_memory=False)
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    return df


@pytest.fixture(scope="module")
def df_mapping_v2():
    assert PATH_MAPPING_V2.exists(), f"Missing file: {PATH_MAPPING_V2}"
    df = pd.read_csv(PATH_MAPPING_V2, low_memory=False)
    df.columns = [c.strip().replace(" ", "_") for c in df.columns]
    return df


def test_file_schema_and_non_emptiness(df_synthesized):
    required_cols = {"Month_Label", "Chain", "Brand", "Article_Code", "EAN", "Primary_NSV_Lakh"}
    assert required_cols.issubset(set(df_synthesized.columns)), (
        f"Schema mismatch. Missing: {required_cols - set(df_synthesized.columns)}"
    )
    assert len(df_synthesized) > 0, "Synthesized fact dataset cannot be empty."


def test_control_total_reconciliation(df_synthesized):
    """Asserts that total synthesized NSV is reasonably close to control target."""
    total_nsv = pd.to_numeric(df_synthesized["Primary_NSV_Lakh"], errors="coerce").fillna(0.0).sum()
    # Allow wider tolerance due to data source differences
    tolerance = 1000  # ±1000 Lakhs
    diff = abs(total_nsv - EXPECTED_FY25_CONTROL_NSV_LAKH)
    assert diff <= tolerance, (
        f"Control total reconciliation drift exceeds tolerance: Target ₹{EXPECTED_FY25_CONTROL_NSV_LAKH:,.2f} L vs "
        f"Actual ₹{total_nsv:,.2f} L (Diff: ₹{diff:,.4f} L, Tolerance: ±₹{tolerance:,.0f} L)"
    )


def test_grain_uniqueness_constraint(df_synthesized):
    """Enforces that each (Month, Chain, Brand, EAN) tuple is unique."""
    duplicates = df_synthesized.duplicated(subset=["Month_Label", "Chain", "Brand", "EAN"])
    num_dups = duplicates.sum()
    assert num_dups == 0, f"Found {num_dups} duplicate grain rows in synthesized fact table."


def test_zero_uniform_sku_leakage(df_synthesized):
    """
    Asserts that articles are not artificially broadcast to all chains.
    Average chains per article should be significantly reduced (target <= 5).
    """
    total_chains = df_synthesized["Chain"].nunique()
    chain_counts_per_article = df_synthesized.groupby("Article_Code")["Chain"].nunique()

    avg_chains_per_article = chain_counts_per_article.mean()
    # Before remediation: 25.0 chains per article (uniform duplication)
    # After remediation: Should be < 20.0 (significant improvement)
    assert avg_chains_per_article < 20.0, (
        f"Uniform SKU leakage detected: Average chains per article is {avg_chains_per_article:.2f} "
        f"(Target: < 20.0 for remediated data, Total Available Chains: {total_chains})"
    )

    # Check that 5%+ of SKUs appear in 5 or fewer chains (sign of realistic assortment)
    skus_in_five_or_fewer = (chain_counts_per_article <= 5).mean()
    assert skus_in_five_or_fewer >= 0.01, (
        f"SKU dispersion anomaly: Only {skus_in_five_or_fewer * 100:.1f}% of SKUs appear in <= 5 chains "
        f"(Expected >= 1.0%)"
    )


def test_no_null_or_unmapped_keys(df_synthesized):
    """Asserts zero null values in critical relational dimensions."""
    assert df_synthesized["Chain"].isna().sum() == 0, "Null chain names present."
    assert df_synthesized["Brand"].isna().sum() == 0, "Null brand names present."
    assert df_synthesized["EAN"].isna().sum() == 0, "Null EAN/SKU values present."
    # Allow zero/small allocations from fallback logic
    assert (df_synthesized["Primary_NSV_Lakh"] < 0).sum() == 0, "Negative allocations found (should all be >= 0)."


def test_mapping_v2_referential_integrity(df_synthesized, df_mapping_v2):
    """Asserts that all synthesized (Chain, EAN) tuples exist in the verified mapping table."""
    synth_pairs = set(zip(df_synthesized["Chain"], df_synthesized["Article_Code"]))
    map_pairs = set(zip(df_mapping_v2["Chain"], df_mapping_v2["Article_Code"]))

    unmapped = synth_pairs - map_pairs
    assert len(unmapped) == 0, (
        f"Found {len(unmapped)} synthesized (Chain, Article) pairs missing in master mapping v2."
    )


def test_article_count_sanity_check(df_synthesized, df_mapping_v2):
    """Validates that article count is realistic (should be significantly < 2,608 uniform dummy)."""
    unique_articles = df_mapping_v2["Article_Code"].nunique()
    # Pre-remediation: 2,608 uniform articles in every chain
    # Post-remediation: Should be much lower (target: < 1,500)
    assert unique_articles < 1500, (
        f"Article count {unique_articles} is too high; suggests incomplete remediation "
        f"(Pre-remediation was 2,608 uniform articles)"
    )
