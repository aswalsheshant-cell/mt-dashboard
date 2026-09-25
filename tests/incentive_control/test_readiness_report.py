"""Phase 3B, STEP 11 -- readiness-report CLI tests."""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "incentive_readiness_report.py"
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "incentive_decisions"


def _run(register_path, verbose=False):
    args = [sys.executable, str(SCRIPT), "--register", str(register_path)]
    if verbose:
        args.append("--verbose")
    result = subprocess.run(args, capture_output=True, text=True, cwd=REPO_ROOT)
    return result.returncode, result.stdout


def test_all_pending_reports_blocked_and_exit_3():
    code, out = _run(FIXTURES / "synthetic_all_pending.json")
    assert code == 3
    assert "OVERALL: BLOCKED_LEADERSHIP_DECISION" in out
    assert "PENDING_LEADERSHIP" in out


def test_fully_approved_reports_ready_and_exit_0():
    code, out = _run(FIXTURES / "synthetic_fully_approved_offtake.json")
    assert code == 0
    assert "OVERALL: READY_FOR_SHADOW_CALCULATION" in out
    assert "Blocking items" not in out


def test_default_output_does_not_expose_approver_or_evidence():
    code, out = _run(FIXTURES / "synthetic_fully_approved_offtake.json", verbose=False)
    assert "SYNTHETIC_FIXTURE_APPROVER" not in out
    assert "synthetic-test-fixture-evidence" not in out


def test_verbose_output_includes_approver_and_evidence():
    code, out = _run(FIXTURES / "synthetic_fully_approved_offtake.json", verbose=True)
    assert "SYNTHETIC_FIXTURE_APPROVER" in out
    assert "synthetic-test-fixture-evidence" in out
