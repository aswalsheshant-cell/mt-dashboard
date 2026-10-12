"""The dashboard PO fill rate must match the committed MT billing summary."""

import csv
from pathlib import Path

from scripts.build_po_fill_rate_dashboard import build_payload, render_js


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "PowerBI/SeedData/Forecast/PO_Fill_Rate_Monthly_Apr25_to_Aug26.csv"
SIDECAR = ROOT / "dashboard/po_fill_rate.js"


def test_fill_rate_uses_weighted_mt_totals_and_keeps_missing_distinct(tmp_path):
    source = tmp_path / "fill_rate.csv"
    fields = ["Month", "FY", "Channel", "PO_Qty", "Billed_Qty", "PO_Value_L", "Billed_Value_L"]
    with source.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows([
            dict(zip(fields, ["Apr-26", "FY27", "MT", "10", "8", "100", "80"])),
            dict(zip(fields, ["May-26", "FY27", "MT", "30", "27", "300", "240"])),
            dict(zip(fields, ["May-26", "FY27", "EB2B", "100", "100", "1000", "1000"])),
            dict(zip(fields, ["Apr-27", "FY28", "MT", "0", "0", "0", "0"])),
        ])

    by_fy = build_payload(source)["by_fy"]
    assert by_fy["fy27"]["qty_pct"] == 87.5
    assert by_fy["fy27"]["value_pct"] == 80.0
    assert by_fy["fy27"]["months"] == ["Apr-26", "May-26"]
    assert by_fy["fy28"]["qty_pct"] is None
    assert by_fy["fy28"]["value_pct"] is None


def test_committed_sidecar_matches_source_and_is_loaded_before_dashboard():
    payload = build_payload(SOURCE)
    assert payload["by_fy"]["fy27"]["qty_pct"] == 87.2
    assert payload["by_fy"]["fy27"]["value_pct"] == 86.7
    assert payload["by_fy"]["fy27"]["months"] == ["Apr-26", "May-26", "Jun-26", "Jul-26", "Aug-26"]
    assert SIDECAR.read_text(encoding="utf-8") == render_js(payload)
    html = (ROOT / "dashboard/index.html").read_text(encoding="utf-8")
    assert html.index('<script src="po_fill_rate.js"></script>') < html.index("const D = window.DASH;")
    assert "PO billing fill rate" in html
