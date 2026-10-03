import csv
import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_dashboard_units import audit_csv, audit_sources, main, write_report


def test_audit_preserves_rows_and_signed_sum(tmp_path):
    source = tmp_path / "offtake_store_article_Apr_26.csv"
    with source.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Month", "NSV", "MRP Sales Value"])
        writer.writeheader()
        writer.writerows([
            {"Month": "Apr'26", "NSV": "1.5", "MRP Sales Value": "300000"},
            {"Month": "Apr'26", "NSV": "-0.2", "MRP Sales Value": "0"},
            {"Month": "Apr'26", "NSV": "2.5", "MRP Sales Value": "500000"},
        ])
    before = source.read_bytes()

    result = audit_csv(source, "NSV", "MRP Sales Value", sample_stride=1)

    assert source.read_bytes() == before
    assert result["sha256"] == hashlib.sha256(before).hexdigest()
    assert result["rows"] == 3
    assert result["raw_sum"] == "3.8"
    assert result["rupees_if_lakh"] == "380000.0"
    assert result["rupees_if_rupees"] == "3.8"
    assert result["median_nsv_mrp_if_lakh"] == 0.5
    assert result["months"] == {"Apr'26": 3}


def test_missing_amount_column_fails_without_changing_source(tmp_path):
    source = tmp_path / "bad.csv"
    source.write_text("Month,Other\nApr'26,4\n", encoding="utf-8")
    before = source.read_bytes()

    with pytest.raises(ValueError, match="missing column NSV"):
        audit_csv(source, "NSV")

    assert source.read_bytes() == before


def test_offtake_keeps_gross_rows_and_reports_governed_rbc_scope(tmp_path):
    source = tmp_path / "offtake_store_article_Apr_26.csv"
    source.write_text(
        "Month,Chain Name,Store Type,NSV,MRP Sales Value\n"
        "Apr'26,Reliance Retail,Non-Brand Counter,1.5,300000\n"
        "Apr'26,Reliance Retail,Brand Counter,0.5,100000\n"
        "May'26,D-Mart,Brand Counter,-0.2,40000\n",
        encoding="utf-8",
    )
    before = source.read_bytes()

    result = audit_csv(source, "NSV", "MRP Sales Value", sample_stride=1, exclude_reliance_bc=True)

    assert source.read_bytes() == before
    assert result["rows"] == 3
    assert result["raw_sum"] == "1.8"
    assert result["governed_raw_sum"] == "1.3"
    assert result["rbc_excluded_rows"] == 1
    assert result["rbc_excluded_raw_sum"] == "0.5"
    assert result["month_totals_raw"] == {"Apr'26": "2.0", "May'26": "-0.2"}
    assert result["month_totals_governed_raw"] == {"Apr'26": "1.5", "May'26": "-0.2"}
    assert "Jun'26" not in result["month_totals_governed_raw"]


def test_source_audit_skips_templates_and_reports_each_file_without_mutation(tmp_path):
    root = tmp_path / "repo"
    offtake = root / "PowerBI" / "RawDataFolders" / "Offtake_Monthly"
    primary = root / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
    shipto = root / "PowerBI" / "RawDataFolders" / "Primary_ShipTo_Monthly"
    for folder in (offtake, primary, shipto):
        folder.mkdir(parents=True)
    (offtake / "_TEMPLATE_Offtake_Monthly.csv").write_text("NSV\n999\n", encoding="utf-8")
    (offtake / "offtake_store_article_Apr_26.csv").write_text(
        "Month,Chain Name,Store Type,NSV,MRP Sales Value\n"
        "Apr'26,D-Mart,Non-Brand Counter,1.5,300000\n", encoding="utf-8"
    )
    (primary / "primary_article_Apr_26.csv").write_text(
        "Month,Inv. Net value(LOC),Total MRP sales\nApr'26,200000,400000\n", encoding="utf-8"
    )
    (shipto / "Primary_ShipTo_FY24-25.csv").write_text(
        "Month,Primary NSV,MRP Value\nApr'24,100000,200000\n", encoding="utf-8"
    )
    originals = {p: p.read_bytes() for p in root.rglob("*.csv")}

    report = audit_sources(root, sample_stride=1)
    out = tmp_path / "unit-audit.json"
    write_report(report, out, root)

    assert [p["path"] for p in report["files"]] == [
        "PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_Apr_26.csv",
        "PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Apr_26.csv",
        "PowerBI/RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_FY24-25.csv",
    ]
    assert report["files"][0]["median_nsv_mrp_if_lakh"] == 0.5
    assert report["files"][1]["median_nsv_mrp_raw"] == 0.5
    assert out.exists()
    assert all(p.read_bytes() == before for p, before in originals.items())


def test_report_refuses_published_dashboard_destination(tmp_path):
    root = tmp_path / "repo"
    (root / "dashboard").mkdir(parents=True)
    with pytest.raises(ValueError, match="published dashboard"):
        write_report({"files": []}, root / "dashboard" / "unit-audit.json", root)


def test_cli_writes_only_aggregate_json(tmp_path):
    root = tmp_path / "repo"
    specs = (
        ("Offtake_Monthly", "offtake_store_article_Apr_26.csv", "Chain Name,Store Type,NSV,MRP Sales Value", "D-Mart,Non-Brand Counter,1.5,300000"),
        ("Primary_Article_Monthly", "primary_article_Apr_26.csv", "Inv. Net value(LOC),Total MRP sales", "200000,400000"),
        ("Primary_ShipTo_Monthly", "Primary_ShipTo_FY24-25.csv", "Primary NSV,MRP Value", "100000,200000"),
    )
    for folder, filename, header, values in specs:
        directory = root / "PowerBI" / "RawDataFolders" / folder
        directory.mkdir(parents=True)
        (directory / filename).write_text(header + "\n" + values + "\n", encoding="utf-8")
    out = tmp_path / "report.json"

    assert main(["--repo-root", str(root), "--out", str(out), "--sample-stride", "1"]) == 0
    saved = out.read_text(encoding="utf-8")
    assert '"mode": "READ_ONLY_SOURCE_AUDIT"' in saved
    assert '"raw_sum": "1.5"' in saved
    assert len(__import__("json").loads(saved)["files"]) == 3

