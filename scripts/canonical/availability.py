"""Explicit availability-state reporting for metrics whose data may or may
not exist in a given build, independent of any FY. This is the module the
Phase 1 certification's "RBC_OFFTAKE_NSV = NOT_AVAILABLE" statement comes
from, as a real, tested function output rather than only a report table
observation.
"""
from . import offtake, primary
from .policies import NotAvailable


def rbc_availability_report(data, fy="FY27"):
    """{measure: {"status": "AVAILABLE"|"NOT_AVAILABLE", "reason": str}}
    for the three ADR-003 Reliance Brand Counter measures. RBC_GAP_NSV is
    never independently computed here -- per ADR-003 rule 5, it is
    NOT_AVAILABLE whenever either operand is, with no separate check of
    its own possible (there is no rbc_gap_nsv() function at all -- see
    tests/canonical/test_reliance_metrics.py)."""
    rbc_primary = primary.rbc_primary_nsv(data, fy)
    rbc_offtake = offtake.rbc_offtake_nsv(data, fy)

    def _entry(value):
        if isinstance(value, NotAvailable):
            return {"status": "NOT_AVAILABLE", "reason": value.reason}
        return {"status": "AVAILABLE", "reason": None}

    primary_entry = _entry(rbc_primary)
    offtake_entry = _entry(rbc_offtake)
    if primary_entry["status"] == "AVAILABLE" and offtake_entry["status"] == "AVAILABLE":
        gap_entry = {"status": "AVAILABLE", "reason": None}
    else:
        missing = []
        if primary_entry["status"] != "AVAILABLE":
            missing.append("RBC_PRIMARY_NSV")
        if offtake_entry["status"] != "AVAILABLE":
            missing.append("RBC_OFFTAKE_NSV")
        gap_entry = {
            "status": "NOT_AVAILABLE",
            "reason": f"requires both operands available (ADR-003 rule 5); missing: {', '.join(missing)}",
        }

    return {
        "RBC_PRIMARY_NSV": primary_entry,
        "RBC_OFFTAKE_NSV": offtake_entry,
        "RBC_GAP_NSV": gap_entry,
    }
