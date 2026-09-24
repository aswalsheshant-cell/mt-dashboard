"""Canonical missing-data, fallback, and negative-value policies
(ADR-001, ADR-007), shared by every metric function in this package.
"""


class NotAvailable:
    """Sentinel distinguishing 'genuinely missing' from a real 0.

    Per ADR-007, missing financial data must never silently become 0 --
    a chain/FY combination with no real transactions IS a real 0 (a valid
    NSV value); a chain/FY combination with NO DATA AT ALL for the
    requested period is NOT_AVAILABLE, a different thing entirely. Every
    canonical metric function returns one of: a real number (including a
    real 0.0), or NOT_AVAILABLE. Never anything else standing in for
    either.
    """

    def __init__(self, reason):
        self.reason = reason

    def __repr__(self):
        return f"NotAvailable({self.reason!r})"

    def __eq__(self, other):
        return isinstance(other, NotAvailable) and self.reason == other.reason

    def __bool__(self):
        # Deliberately falsy, so `if value:` correctly treats it as "no
        # value" -- but code must still branch on isinstance(), not
        # truthiness alone, to distinguish it from a real 0.0 (also
        # falsy in a boolean sense but NOT the same thing -- see the
        # module docstring). This is enforced by tests, not by Python's
        # type system, so every metric function below is written to check
        # `is None` / `isinstance(x, NotAvailable)` explicitly rather than
        # relying on `if x:`.
        return False


NOT_AVAILABLE = NotAvailable  # constructor alias for readability at call sites


def exact_fy_or_not_available(entity_name, requested_fy, values_by_fy):
    """The canonical ADR-001 accessor: return values_by_fy[requested_fy] if
    (and only if) that exact key is present with a real numeric value, else
    NOT_AVAILABLE. NEVER falls back to another FY, a 'value'/'total' field
    with no FY subscript, or 0. This is the single choke point every
    FY-keyed canonical metric routes through, so the no-cross-FY-fallback
    policy is enforced in one place rather than re-implemented (and
    potentially mis-implemented) per metric -- precisely the discipline
    KI-OFFTAKE-001 shows this codebase lacked before this package existed.
    """
    if requested_fy not in values_by_fy:
        return NotAvailable(
            f"{entity_name}: no data for {requested_fy} "
            f"(available: {sorted(values_by_fy.keys())})"
        )
    v = values_by_fy[requested_fy]
    if v is None:
        return NotAvailable(f"{entity_name}: {requested_fy} present but null")
    return v


def is_available(value):
    return not isinstance(value, NotAvailable)
