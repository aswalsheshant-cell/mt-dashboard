"""
Tests for the pure helper functions in scripts/build_dashboard_data.py.

Run with:  pytest tests/test_fy_helpers.py -v
"""
import math
import sys
from pathlib import Path

import pytest

# Import without executing main() — the script has no __all__ so we import
# the module directly after adding scripts/ to sys.path.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from build_dashboard_data import (
    fy_tag_from_ym,
    fy_start_year,
    fy_source_key,
    fy_tag_from_label,
    month_labels,
    quarter_labels_for,
    canon_brand,
    canon_chain,
    canon_zone,
    r2,
)


# ---------------------------------------------------------------------------
# fy_tag_from_ym
# ---------------------------------------------------------------------------
class TestFyTagFromYm:
    @pytest.mark.parametrize("year,month,expected", [
        # Apr–Dec of year Y  →  FY(Y+1)
        (2024, 4,  "FY25"),
        (2024, 9,  "FY25"),
        (2024, 12, "FY25"),
        (2025, 4,  "FY26"),
        (2025, 12, "FY26"),
        (2026, 4,  "FY27"),
        # Jan–Mar of year Y  →  FY(Y)
        (2025, 1,  "FY25"),
        (2025, 3,  "FY25"),
        (2026, 1,  "FY26"),
        (2026, 3,  "FY26"),
        (2027, 3,  "FY27"),
        # Boundary months
        (2025, 3,  "FY25"),   # last month of FY25
        (2025, 4,  "FY26"),   # first month of FY26
    ])
    def test_standard(self, year, month, expected):
        assert fy_tag_from_ym(year, month) == expected

    def test_zero_padded_two_digit(self):
        # FY tags must always be two-digit (FY05, not FY5)
        assert fy_tag_from_ym(2004, 4) == "FY05"

    def test_roundtrip_with_fy_start_year(self):
        """fy_start_year(fy_tag_from_ym(y, 4)) must equal y for any year."""
        for y in range(2020, 2035):
            tag = fy_tag_from_ym(y, 4)   # April = first month of a new FY
            assert fy_start_year(tag) == y


# ---------------------------------------------------------------------------
# fy_start_year
# ---------------------------------------------------------------------------
class TestFyStartYear:
    @pytest.mark.parametrize("tag,expected", [
        ("FY25", 2024),
        ("FY26", 2025),
        ("FY27", 2026),
        ("FY28", 2027),
        (" FY27 ", 2026),   # tolerates surrounding whitespace
    ])
    def test_standard(self, tag, expected):
        assert fy_start_year(tag) == expected


# ---------------------------------------------------------------------------
# fy_source_key
# ---------------------------------------------------------------------------
class TestFySourceKey:
    @pytest.mark.parametrize("tag,expected", [
        ("FY25", "FY_24-25"),
        ("FY26", "FY_25-26"),
        ("FY27", "FY_26-27"),
    ])
    def test_standard(self, tag, expected):
        assert fy_source_key(tag) == expected


# ---------------------------------------------------------------------------
# fy_tag_from_label
# ---------------------------------------------------------------------------
class TestFyTagFromLabel:
    @pytest.mark.parametrize("label,expected", [
        ("Apr-24", "FY25"),
        ("Mar-25", "FY25"),   # last month of FY25
        ("Apr-25", "FY26"),   # first month of FY26
        ("Mar-26", "FY26"),
        ("Apr-26", "FY27"),
        ("Sep-25", "FY26"),
        ("Jan-26", "FY26"),
        ("Dec-25", "FY26"),
    ])
    def test_valid_labels(self, label, expected):
        assert fy_tag_from_label(label) == expected

    @pytest.mark.parametrize("bad", [
        "April-24",   # full month name
        "04-24",      # numeric month
        "Apr24",      # missing hyphen
        "Apr-2024",   # four-digit year
        "",
        "Total",
        None,
        123,
    ])
    def test_invalid_labels_return_none(self, bad):
        assert fy_tag_from_label(bad) is None

    def test_case_insensitive_month(self):
        # regex is case-insensitive via title()
        assert fy_tag_from_label("apr-24") == "FY25"
        assert fy_tag_from_label("APR-24") == "FY25"


# ---------------------------------------------------------------------------
# month_labels
# ---------------------------------------------------------------------------
class TestMonthLabels:
    def test_default_starts_at_april_2024(self):
        labels = month_labels(2024, 24)
        assert labels[0] == "Apr-24"

    def test_length(self):
        assert len(month_labels(2024, 12)) == 12
        assert len(month_labels(2024, 26)) == 26

    def test_year_wraparound(self):
        # 12 months from Apr-24: Apr-24 .. Mar-25
        labels = month_labels(2024, 12)
        assert labels[-1] == "Mar-25"

    def test_multi_year_span(self):
        # 24 months from Apr-24: Apr-24 .. Mar-26
        labels = month_labels(2024, 24)
        assert labels[0] == "Apr-24"
        assert labels[-1] == "Mar-26"

    def test_26_month_span(self):
        # Apr-24 .. May-26
        labels = month_labels(2024, 26)
        assert labels[24] == "Apr-26"
        assert labels[25] == "May-26"

    def test_all_labels_parseable(self):
        """Every generated label must be parseable back to a valid FY tag."""
        for lab in month_labels(2024, 36):
            tag = fy_tag_from_label(lab)
            assert tag is not None, f"Unparseable label: {lab}"
            assert tag.startswith("FY")

    def test_fy_boundary_in_sequence(self):
        labels = month_labels(2024, 24)
        # Month 11 (index 11) = Mar-25 → FY25; Month 12 (index 12) = Apr-25 → FY26
        assert fy_tag_from_label(labels[11]) == "FY25"
        assert fy_tag_from_label(labels[12]) == "FY26"


# ---------------------------------------------------------------------------
# quarter_labels_for
# ---------------------------------------------------------------------------
class TestQuarterLabelsFor:
    def test_single_fy_span(self):
        # Apr-24..Mar-25 = FY25, start year 2024 → Q1-24..Q4-24
        months = month_labels(2024, 12)
        ql = quarter_labels_for(months)
        assert ql == ["Q1-24", "Q2-24", "Q3-24", "Q4-24"]

    def test_two_fy_span(self):
        # Apr-24..Mar-26 = FY25+FY26
        months = month_labels(2024, 24)
        ql = quarter_labels_for(months)
        assert ql == ["Q1-24", "Q1-25", "Q2-24", "Q2-25",
                      "Q3-24", "Q3-25", "Q4-24", "Q4-25"]

    def test_no_duplicates(self):
        months = month_labels(2024, 26)
        ql = quarter_labels_for(months)
        assert len(ql) == len(set(ql))

    def test_empty_returns_empty(self):
        assert quarter_labels_for([]) == []


# ---------------------------------------------------------------------------
# canon_brand
# ---------------------------------------------------------------------------
class TestCanonBrand:
    @pytest.mark.parametrize("raw,expected", [
        ("mamaearth",      "Mamaearth"),
        ("MAMAEARTH",      "Mamaearth"),   # via lower()
        ("Mamaearth",      "Mamaearth"),
        ("bblunt",         "BBlunt"),
        ("the derma co.",  "The Derma Co"),
        ("the derma co",   "The Derma Co"),
        ("dr. sheth's",    "Dr. Sheth's"),
        ("dr.sheth's",     "Dr. Sheth's"),
        ("dr. sheth",      "Dr. Sheth's"),
        ("aqualogica",     "Aqualogica"),
        ("staze",          "Staze"),
    ])
    def test_known_aliases(self, raw, expected):
        assert canon_brand(raw) == expected

    def test_unknown_brand_passthrough(self):
        assert canon_brand("NewBrand X") == "NewBrand X"

    def test_none_returns_none(self):
        assert canon_brand(None) is None

    def test_nan_returns_none(self):
        assert canon_brand(float("nan")) is None

    def test_strips_whitespace(self):
        assert canon_brand("  mamaearth  ") == "Mamaearth"


# ---------------------------------------------------------------------------
# canon_chain
# ---------------------------------------------------------------------------
class TestCanonChain:
    @pytest.mark.parametrize("raw,expected", [
        ("reliance retail",         "Reliance Retail"),
        ("Reliance Retail Limited", "Reliance Retail"),
        ("reliance retail ltd.",    "Reliance Retail"),
        ("rrl",                     "Reliance Retail"),
        # NOTE: "metro-cnc-rrl" appears in BOTH Reliance Retail and Metro C&C alias lists;
        # Metro C&C is defined later in CHAIN_ALIASES so it silently wins (last-write wins).
        # This is a data-quality ambiguity — investigate which canon is correct in source data.
        ("metro-cnc-rrl",           "Metro C&C"),
        ("dmart",                   "Dmart"),
        ("d-mart",                  "Dmart"),
        ("d-mart ",                 "Dmart"),
        ("FSN",                     "Nykaa (FSN)"),
        ("nykaa ss(fsn)",           "Nykaa (FSN)"),
        ("apollo",                  "Apollo"),
        ("apollo healthco",         "Apollo"),
        ("walmart cnc",             "Walmart"),
        ("wal-mart",                "Walmart"),
        ("sumosave",                "Sumo Save"),
        ("ratandeep",               "Ratnadeep"),
        ("frank ross",              "Frankross"),
        ("sastasundar",             "Sasta Sundar"),
    ])
    def test_known_aliases(self, raw, expected):
        assert canon_chain(raw) == expected

    def test_unknown_chain_passthrough(self):
        assert canon_chain("SomeNewChain") == "SomeNewChain"

    def test_none_returns_none(self):
        assert canon_chain(None) is None

    def test_nan_returns_none(self):
        assert canon_chain(float("nan")) is None

    def test_nbsp_stripped(self):
        # Non-breaking space should be treated like a regular space
        assert canon_chain("dmart\xa0") == "Dmart"

    def test_case_insensitive(self):
        assert canon_chain("DMART") == "Dmart"
        assert canon_chain("Dmart") == "Dmart"


# ---------------------------------------------------------------------------
# canon_zone
# ---------------------------------------------------------------------------
class TestCanonZone:
    @pytest.mark.parametrize("raw,expected", [
        ("north",   "North"),
        ("North",   "North"),
        ("NORTH",   "North"),
        ("west",    "West"),
        ("east",    "East"),
        ("south-1", "South 1"),
        ("south 1", "South 1"),
        ("south-2", "South 2"),
        ("south 2", "South 2"),
    ])
    def test_known_zones(self, raw, expected):
        assert canon_zone(raw) == expected

    def test_none_returns_none(self):
        assert canon_zone(None) is None

    def test_unknown_zone_passthrough(self):
        assert canon_zone("Central") == "Central"


# ---------------------------------------------------------------------------
# r2 (rounding helper)
# ---------------------------------------------------------------------------
class TestR2:
    def test_rounds_to_two_decimal_places(self):
        assert r2(1.23456) == 1.23

    def test_rounds_to_specified_places(self):
        assert r2(1.23456, 3) == 1.235

    def test_integer_input(self):
        assert r2(5) == 5.0

    def test_none_returns_none(self):
        assert r2(None) is None

    def test_nan_returns_none(self):
        assert r2(float("nan")) is None

    def test_inf_returns_none(self):
        assert r2(float("inf")) is None
        assert r2(float("-inf")) is None

    def test_zero(self):
        assert r2(0) == 0.0

    def test_negative(self):
        assert r2(-3.456) == -3.46

    def test_already_rounded(self):
        assert r2(1.5) == 1.5

    def test_string_numeric(self):
        # r2 tries float() conversion — a numeric string should work
        assert r2("3.14") == 3.14

    def test_non_numeric_string_returns_none(self):
        assert r2("abc") is None
