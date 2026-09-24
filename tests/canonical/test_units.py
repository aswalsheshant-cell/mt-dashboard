"""ADR-006: canonical storage is INR Lakh; Crore conversion is presentation-only."""
import math

from canonical.units import format_inr, round_lakh, to_crore


def test_round_lakh_rounds_to_two_decimals():
    assert round_lakh(1.23456) == 1.23


def test_round_lakh_never_converts_missing_to_a_number():
    assert round_lakh(None) is None
    assert round_lakh(float("nan")) is None
    assert round_lakh(float("inf")) is None


def test_to_crore_divides_by_100_and_never_before_storage():
    assert to_crore(32900.36) == 329.0
    assert to_crore(None) is None


def test_format_inr_selects_l_or_cr_by_magnitude():
    assert format_inr(50.0).endswith("L")
    assert format_inr(150.0).endswith("Cr")


def test_format_inr_missing_is_en_dash_never_a_number():
    assert format_inr(None) == "–"
