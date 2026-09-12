#!/usr/bin/env python3
"""Pytest wrapper to import release gate tests from tests/ directory.

This allows pytest to find the tests when run from scripts/ directory.
Not discovered by unittest (due to filename pattern), but pytest will find it.
"""
import sys
from pathlib import Path

# Dynamically import tests from tests/ directory to avoid circular imports
_ROOT = Path(__file__).resolve().parent.parent
_tests_path = str(_ROOT / "tests")
if _tests_path not in sys.path:
    sys.path.insert(0, _tests_path)

# Import using exec to avoid circular import issues with unittest
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "test_release_gate_impl",
    _ROOT / "tests" / "test_release_gate.py"
)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

# Re-export the test classes for pytest discovery
ReleaseGateCheck = _module.ReleaseGateCheck  # noqa: F405
TestReleaseGateGovernance = _module.TestReleaseGateGovernance  # noqa: F405
TestReleaseGateDataQuality = _module.TestReleaseGateDataQuality  # noqa: F405
TestReleaseGateSecurityChecks = _module.TestReleaseGateSecurityChecks  # noqa: F405
TestReleaseGateSummary = _module.TestReleaseGateSummary  # noqa: F405
