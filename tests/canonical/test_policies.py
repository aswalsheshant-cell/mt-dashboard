"""ADR-001 (no cross-FY fallback) and ADR-007 (missing != zero) enforcement,
proven against the shared choke-point exact_fy_or_not_available()."""
from canonical.policies import NotAvailable, exact_fy_or_not_available, is_available


def test_exact_fy_returns_the_real_value_when_present():
    assert exact_fy_or_not_available("X", "fy27", {"fy26": 10.0, "fy27": 20.0}) == 20.0


def test_missing_fy_returns_not_available_not_zero():
    result = exact_fy_or_not_available("X", "fy27", {"fy26": 10.0})
    assert isinstance(result, NotAvailable)
    assert result != 0


def test_never_falls_back_to_a_different_fy():
    """The exact KI-OFFTAKE-001 defect this function exists to prevent:
    a request for fy27 must never return fy26's value."""
    result = exact_fy_or_not_available("X", "fy27", {"fy26": 999.0})
    assert result != 999.0
    assert isinstance(result, NotAvailable)


def test_never_falls_back_to_an_all_period_value_field():
    """Simulates the real defect shape: a dict that ALSO carries a generic
    'value' key (mirroring offtake.by_chain[]'s all-months-combined field)
    must not be consulted by this function at all -- it only ever looks up
    the exact fy key passed to it."""
    values = {"fy26": 15.19, "value": 15.19}  # 'value' deliberately not a real FY key
    result = exact_fy_or_not_available("X", "fy27", values)
    assert isinstance(result, NotAvailable)


def test_null_value_present_is_still_not_available():
    result = exact_fy_or_not_available("X", "fy27", {"fy27": None})
    assert isinstance(result, NotAvailable)


def test_real_zero_is_available_and_distinct_from_not_available():
    """A real 0.0 (e.g. a chain that genuinely sold nothing this FY) must
    be returned as 0.0, not silently promoted to NOT_AVAILABLE -- the two
    are different facts (ADR-007)."""
    result = exact_fy_or_not_available("X", "fy27", {"fy27": 0.0})
    assert result == 0.0
    assert is_available(result)


def test_not_available_is_falsy_but_not_equal_to_zero():
    na = NotAvailable("test")
    assert not na and na != 0 and not is_available(na)
