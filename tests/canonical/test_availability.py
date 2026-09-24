"""Proves the ADR-003 Reliance Brand Counter availability statement is a
real, tested function output, not just a report table observation:

    RBC_PRIMARY_NSV = AVAILABLE
    RBC_OFFTAKE_NSV = NOT_AVAILABLE
    RBC_GAP_NSV = NOT_AVAILABLE

RBC_OFFTAKE_NSV is NOT_AVAILABLE because the certified D.reliance_brand_counters
structure is an empty availability stub -- see docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md's
Phase 1 implementation-discovery note. This must never be papered over with a
calculated substitute or an allocation of Reliance chain-level Offtake down to
Brand Counter (ADR-003)."""
from canonical import availability
from canonical.policies import NotAvailable


def test_rbc_primary_nsv_is_available(data):
    report = availability.rbc_availability_report(data)
    assert report["RBC_PRIMARY_NSV"]["status"] == "AVAILABLE"
    assert report["RBC_PRIMARY_NSV"]["reason"] is None


def test_rbc_offtake_nsv_is_not_available(data):
    report = availability.rbc_availability_report(data)
    assert report["RBC_OFFTAKE_NSV"]["status"] == "NOT_AVAILABLE"
    assert report["RBC_OFFTAKE_NSV"]["reason"]


def test_rbc_gap_nsv_is_not_available_because_offtake_operand_is_missing(data):
    report = availability.rbc_availability_report(data)
    assert report["RBC_GAP_NSV"]["status"] == "NOT_AVAILABLE"
    assert "RBC_OFFTAKE_NSV" in report["RBC_GAP_NSV"]["reason"]


def test_report_shape_covers_exactly_the_three_adr003_measures(data):
    report = availability.rbc_availability_report(data)
    assert set(report.keys()) == {"RBC_PRIMARY_NSV", "RBC_OFFTAKE_NSV", "RBC_GAP_NSV"}
    for entry in report.values():
        assert set(entry.keys()) == {"status", "reason"}
        assert entry["status"] in ("AVAILABLE", "NOT_AVAILABLE")


def test_gap_would_be_available_only_if_both_operands_were(data, monkeypatch):
    """Regression guard: the gap-availability derivation actually looks at
    both operands rather than hardcoding NOT_AVAILABLE -- if both underlying
    metric functions report AVAILABLE, the gap must too."""
    from canonical import primary as primary_mod
    from canonical import offtake as offtake_mod

    monkeypatch.setattr(primary_mod, "rbc_primary_nsv", lambda data, fy: 100.0)
    monkeypatch.setattr(offtake_mod, "rbc_offtake_nsv", lambda data, fy: 40.0)
    report = availability.rbc_availability_report(data)
    assert report["RBC_PRIMARY_NSV"]["status"] == "AVAILABLE"
    assert report["RBC_OFFTAKE_NSV"]["status"] == "AVAILABLE"
    assert report["RBC_GAP_NSV"] == {"status": "AVAILABLE", "reason": None}
