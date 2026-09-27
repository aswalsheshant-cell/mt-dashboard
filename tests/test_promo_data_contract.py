"""Promo data contract (2026-09-27): the promo source carries offer depth
only -- no spend, no baseline. Guards against the two ways that drifted:
docs calling Promo Master a "trade-spend" source, and the registry entry
losing its not-available list (which would let spend/uplift/ROI look sourced)."""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _entry():
    reg = yaml.safe_load((ROOT / "config" / "data_source_registry.yml").read_text())
    ds = reg.get("datasets", reg)
    return ds["promotions_offtake_correlation"]


def test_registry_marks_promo_contract_partial():
    e = _entry()
    assert e["contract_status"] == "PARTIAL"
    assert e["available_fields"], "available fields must be listed"


def test_spend_uplift_roi_listed_as_not_available():
    na = " ".join(_entry()["not_available_fields"]).lower()
    for term in ("spend", "baseline", "uplift", "roi"):
        assert term in na, f"'{term}' must stay in not_available_fields until a governed source exists"


def test_no_doc_calls_promo_master_a_trade_spend_source():
    files = [ROOT / "scripts" / "build_dashboard_data.py", ROOT / "dashboard" / "README.md",
             ROOT / "PRODUCTION_DEPLOYMENT_RUNBOOK.md", ROOT / "DEPLOYMENT_READY.md"]
    bad = re.compile(r"promo[^\n]{0,40}trade[- ]spend (calendar|allocation)", re.IGNORECASE)
    for f in files:
        hit = bad.search(f.read_text())
        assert hit is None, f"{f.name}: '{hit.group(0)}' -- Promo Master carries no spend"


def test_metric_registry_defines_promo_measures_as_not_available():
    txt = (ROOT / "docs" / "METRIC_REGISTRY.md").read_text()
    sec = txt[txt.index("## Promo measurement contract"):txt.index("## Cross-references")]
    for mid in ("PROMO_SPEND", "PROMO_BASELINE", "PROMO_INCREMENTAL_SALES",
                "PROMO_UPLIFT_PCT", "PROMO_ROI_REVENUE", "PROMO_ROI_CONTRIBUTION"):
        row = next(l for l in sec.splitlines() if l.startswith(f"| `{mid}`"))
        assert "NOT_AVAILABLE" in row, mid
    # Not-computed measures stay out of the main (computed-today) table.
    main = txt[:txt.index("## What this registry deliberately does not cover yet")]
    assert "PROMO_ROI" not in main and "PROMO_SPEND" not in main
