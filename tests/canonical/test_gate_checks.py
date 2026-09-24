"""Proves the Canonical Financial Truth Gate script (scripts/canonical_gate_checks.py)
actually catches the regressions it claims to catch -- a gate that always
prints PASS is worse than no gate at all, because it hides that fact behind
a green checkmark."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import canonical_gate_checks as gate  # noqa: E402


def test_all_checks_pass_against_the_certified_baseline():
    for name, fn in gate.CHECKS.items():
        problems = fn()
        assert problems == [], f"check {name!r} found problems against the certified baseline: {problems}"


def test_missing_never_becomes_zero_would_catch_a_broken_choke_point(monkeypatch):
    import canonical.policies as policies

    def broken(entity_name, requested_fy, values_by_fy):
        return values_by_fy.get(requested_fy, 0)  # the exact regression this guards against

    monkeypatch.setattr(gate, "exact_fy_or_not_available", broken, raising=False)
    monkeypatch.setattr(policies, "exact_fy_or_not_available", broken)
    problems = gate.check_missing_never_becomes_zero()
    assert problems, "expected the check to catch a choke point that returns 0 for a missing FY"


def test_numeric_safety_would_catch_a_broken_round_lakh(monkeypatch):
    import canonical.units as units_mod

    monkeypatch.setattr(units_mod, "round_lakh", lambda x, nd=2: x)
    monkeypatch.setattr(gate, "round_lakh", lambda x, nd=2: x)
    problems = gate.check_numeric_safety()
    assert any("round_lakh" in p for p in problems)


def test_governance_integrity_would_catch_an_unregistered_governed_row(monkeypatch):
    fake_exception = type(
        "FakeExc", (), {"exception_id": "GOV-999-NOT-REGISTERED", "status": "APPROVED_GOVERNED"}
    )()
    fake_row = type(
        "FakeRow", (), {"result": "APPROVED_GOVERNED", "exception": fake_exception,
                          "metric": "FAKE_METRIC", "scope": "fake=scope"}
    )()

    monkeypatch.setattr(gate, "build_report", lambda data: [fake_row])
    problems = gate.check_governance_integrity()
    assert any("GOV-999-NOT-REGISTERED" in p for p in problems)


def test_fallback_safety_would_catch_a_reintroduced_value_fallback(tmp_path, monkeypatch):
    bad_source = 'def chain_offtake_nsv(data, fy, chain):\n    return data.value\n'
    fake_dir = tmp_path
    (fake_dir / "facts.py").write_text(bad_source)
    (fake_dir / "primary.py").write_text("def f():\n    return 1\n")
    (fake_dir / "offtake.py").write_text("def f():\n    return 1\n")
    monkeypatch.setattr(gate, "CANONICAL_DIR", fake_dir)
    problems = gate.check_fallback_safety()
    assert any("facts.py" in p for p in problems)


def test_unit_isolation_would_catch_a_stray_conversion_outside_units_py(tmp_path, monkeypatch):
    (tmp_path / "primary.py").write_text("def f(x):\n    return x / 100.0\n")
    monkeypatch.setattr(gate, "CANONICAL_DIR", tmp_path)
    problems = gate.check_unit_conversion_isolation()
    assert any("primary.py" in p for p in problems)


def test_source_contracts_would_catch_a_new_unpinned_primary_violation(monkeypatch):
    fake_problems = ["row 5: missing required field 'Brand'", "row 9: missing required field 'Chain'"]
    monkeypatch.setattr(gate.contract_validation, "validate_primary_contract", lambda data: fake_problems)
    monkeypatch.setattr(gate.contract_validation, "validate_offtake_contract", lambda data: [])
    problems = gate.check_source_contracts()
    assert problems, "expected new, unpinned primary contract violations to fail the gate"


def test_source_contracts_allows_only_the_one_pinned_category_exception(monkeypatch):
    monkeypatch.setattr(
        gate.contract_validation, "validate_primary_contract",
        lambda data: ["row 121185: required field 'Category' is null"])
    monkeypatch.setattr(gate.contract_validation, "validate_offtake_contract", lambda data: [])
    problems = gate.check_source_contracts()
    assert problems == []


def test_main_exits_nonzero_when_a_check_fails(monkeypatch, capsys):
    monkeypatch.setitem(gate.CHECKS, "always-fails", lambda: ["synthetic failure"])
    rc = gate.main(["always-fails"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "synthetic failure" in out
    assert "FAIL" in out


def test_main_exits_zero_when_all_requested_checks_pass():
    rc = gate.main(["reconciliation", "availability-metadata"])
    assert rc == 0


def test_list_flag_prints_every_check_name(capsys):
    gate.main(["--list"])
    out = capsys.readouterr().out
    for name in gate.CHECKS:
        assert name in out
