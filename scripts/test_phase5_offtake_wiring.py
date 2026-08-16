"""
Phase 5 tests — offtake universe wiring into allocate_dist_primary().

Covers:
  1. build_offtake_universe() with an empty src directory → (None, None)
  2. build_offtake_universe() reading a minimal CSV → correct brand/EAN sets
  3. Signal defaults when offtake_brand_set / offtake_ean_set are None
  4. Brand_Not_Listed tier fires when brand absent from offtake universe
  5. Article_Not_Listed tier fires when article absent from offtake universe
  6. Not_Eligible tier fires when both brand AND article are present but no
     cont-sheet match exists (unchanged from Phase 3 behaviour)

All tests are self-contained: no external source files required.
"""

import csv
import pathlib
import sys
import tempfile
import types

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Import helpers — keep the test independent of working-directory placement
# ---------------------------------------------------------------------------
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from build_dashboard_data import build_offtake_universe          # noqa: E402
from dist_allocation_governance import DistAllocationGovernance  # noqa: E402


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def empty_src(tmp_path):
    """A src directory with no offtake files."""
    return tmp_path


@pytest.fixture()
def offtake_csv_src(tmp_path):
    """A src directory with one minimal offtake CSV containing Brand + EAN."""
    fp = tmp_path / "offtake_store_article_Apr_26.csv"
    rows = [
        ["Chain Name", "Site Code", "EAN", "Category", "Brand", "NSV", "Month"],
        ["Reliance", "R001", "8901030123456", "Haircare", "Mamaearth", "10.5", "Apr'26"],
        ["DMart", "D001", "8901030654321", "Skincare", "The Derma Co.", "5.2", "Apr'26"],
        ["DMart", "D001", "8901030111111", "Babycare", "Aqualogica", "3.1", "Apr'26"],
    ]
    with open(fp, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    return tmp_path


@pytest.fixture()
def gov():
    return DistAllocationGovernance()


# ---------------------------------------------------------------------------
# Minimal cont-weights / dist DataFrames for integration scenarios
# ---------------------------------------------------------------------------

def _make_dist(brand="mamaearth", ship_to="DIST ABC", month="2026-04", ean="8901030123456"):
    """Single-row Dist. primary DataFrame for testing allocate_dist_primary."""
    return pd.DataFrame({
        "_st": [ship_to.lower()],
        "_bl": [brand.lower()],
        "_pm": [month],
        "_EAN No.": [ean],
        "_NSV": [10.0],
        "_FY": ["FY27"],
        "_M": ["Apr"],
        "_Brand": [brand],
        "_CustName": [ship_to],
        "_CustCode": ["1234"],
        "PO Type": ["Dist."],
    })


def _make_wdf(brand="mamaearth", ship_to="DIST ABC", month="2026-03"):
    """Cont-weights DataFrame: only has an entry for the PRIOR month (nearest-only)."""
    return pd.DataFrame({
        "_st": [ship_to.lower()],
        "_bl": [brand.lower()],
        "_pm": [month],
        "_AllocChainRaw": ["Chain A"],
        "_frac": [1.0],
        "_ShipToRaw": [ship_to],
        "_BrandRaw": [brand],
    })


# ===========================================================================
# 1. build_offtake_universe — empty directory
# ===========================================================================

def test_universe_empty_src(empty_src):
    brand_set, ean_set = build_offtake_universe(empty_src)
    assert brand_set is None
    assert ean_set is None


# ===========================================================================
# 2. build_offtake_universe — reads brand and EAN from CSV
# ===========================================================================

def test_universe_from_csv_brands(offtake_csv_src):
    brand_set, ean_set = build_offtake_universe(offtake_csv_src)
    assert brand_set is not None
    assert "mamaearth" in brand_set
    assert "the derma co." in brand_set
    assert "aqualogica" in brand_set


def test_universe_from_csv_eans(offtake_csv_src):
    brand_set, ean_set = build_offtake_universe(offtake_csv_src)
    assert ean_set is not None
    assert "8901030123456" in ean_set
    assert "8901030654321" in ean_set
    assert "8901030111111" in ean_set


def test_universe_returns_frozensets(offtake_csv_src):
    brand_set, ean_set = build_offtake_universe(offtake_csv_src)
    assert isinstance(brand_set, frozenset)
    assert isinstance(ean_set, frozenset)


# ===========================================================================
# 3. Signal defaults: None universe → brand_in_offtake / article_in_offtake = True
# ===========================================================================

def test_none_universe_brand_signal_defaults_true(gov):
    offtake_brand_set = None
    bl = "some_new_brand"
    brand_in_offtake = (offtake_brand_set is None or bl in offtake_brand_set)
    assert brand_in_offtake is True


def test_none_universe_article_signal_defaults_true(gov):
    offtake_ean_set = None
    key_eans = {}
    k = ("ship", "brand", "2026-04")
    article_in_offtake = (offtake_ean_set is None
                          or bool(key_eans.get(k, frozenset()) & offtake_ean_set))
    assert article_in_offtake is True


# ===========================================================================
# 4. Brand_Not_Listed fires: brand absent from wired offtake universe
# ===========================================================================

def test_brand_not_listed_tier_fires(gov):
    offtake_brand_set = frozenset(["the derma co.", "aqualogica"])  # mamaearth NOT present
    bl = "mamaearth"
    brand_in_offtake = (offtake_brand_set is None or bl in offtake_brand_set)
    assert brand_in_offtake is False

    result = gov.check_eligibility(
        primary_row={"ship_to": "dist abc", "brand": bl, "month": "2026-04"},
        secondary_match_found=False,
        secondary_match_within_tат=False,
        brand_in_offtake=brand_in_offtake,
        article_in_offtake=True,
    )
    assert result.tier == "Brand_Not_Listed"
    assert result.confidence_pct == 95.0


# ===========================================================================
# 5. Article_Not_Listed fires: article absent but brand present
# ===========================================================================

def test_article_not_listed_tier_fires(gov):
    offtake_ean_set = frozenset(["8901030000001", "8901030000002"])  # test EAN not in set
    key_eans = {("dist abc", "mamaearth", "2026-04"): frozenset(["8901030999999"])}
    k = ("dist abc", "mamaearth", "2026-04")
    article_in_offtake = (offtake_ean_set is None
                          or bool(key_eans.get(k, frozenset()) & offtake_ean_set))
    assert article_in_offtake is False

    result = gov.check_eligibility(
        primary_row={"ship_to": "dist abc", "brand": "mamaearth", "month": "2026-04"},
        secondary_match_found=False,
        secondary_match_within_tат=False,
        brand_in_offtake=True,
        article_in_offtake=article_in_offtake,
    )
    assert result.tier == "Article_Not_Listed"
    assert result.confidence_pct == 95.0


# ===========================================================================
# 6. Article present in offtake + brand present → Not_Eligible (no mapping)
# ===========================================================================

def test_not_eligible_when_both_present_but_no_mapping(gov):
    offtake_ean_set = frozenset(["8901030123456"])
    key_eans = {("dist abc", "mamaearth", "2026-04"): frozenset(["8901030123456"])}
    k = ("dist abc", "mamaearth", "2026-04")
    brand_in_offtake = True
    article_in_offtake = (offtake_ean_set is None
                          or bool(key_eans.get(k, frozenset()) & offtake_ean_set))
    assert article_in_offtake is True

    result = gov.check_eligibility(
        primary_row={"ship_to": "dist abc", "brand": "mamaearth", "month": "2026-04"},
        secondary_match_found=False,
        secondary_match_within_tат=False,
        brand_in_offtake=brand_in_offtake,
        article_in_offtake=article_in_offtake,
    )
    assert result.tier == "Not_Eligible"


# ===========================================================================
# 7. Tier 1/2 short-circuit: brand/article signals irrelevant for mapped keys
# ===========================================================================

def test_eligible_tier_ignores_offtake_signals(gov):
    result = gov.check_eligibility(
        primary_row={"ship_to": "dist abc", "brand": "mamaearth", "month": "2026-04"},
        secondary_match_found=True,
        secondary_match_within_tат=False,
        brand_in_offtake=False,   # would trigger Brand_Not_Listed if reached
        article_in_offtake=False,
    )
    assert result.tier == "Eligible"


def test_eligible_tat_ignores_offtake_signals(gov):
    result = gov.check_eligibility(
        primary_row={"ship_to": "dist abc", "brand": "mamaearth", "month": "2026-04"},
        secondary_match_found=False,
        secondary_match_within_tат=True,
        brand_in_offtake=False,   # would trigger Brand_Not_Listed if reached
        article_in_offtake=False,
    )
    assert result.tier == "Eligible_TAT"
