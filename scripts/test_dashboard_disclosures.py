#!/usr/bin/env python3
"""Wrapper to import dashboard disclosure tests from tests/ directory.

This allows pytest to find the tests regardless of whether it's run from
tests/ or scripts/ directory.
"""
import sys
from pathlib import Path

# Add tests directory to path so we can import the actual tests
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

# Import all test classes from the actual test module
from test_dashboard_disclosures import (  # noqa: F401, E402
    TestDashboardDisclosures,
    TestProvisionalBannerDisplay,
    TestGovernanceDisclosureCompleteness,
)

if __name__ == "__main__":
    import unittest
    unittest.main()
