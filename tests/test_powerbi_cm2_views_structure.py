from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'ModernTrade_Report.Dataset/definition'

def test_cm2_fact_preserves_contract_and_signed_rows():
    text = (MODEL / 'tables/Fact_CM2.tmdl').read_text(encoding="utf-8")
    from scripts.cm2_reporting import CM2_EXPORT_FIELDS
    for field in CM2_EXPORT_FIELDS:
        assert f'column {field}' in text
    assert 'RepoRoot' in text and 'schema_version' in text
    assert 'Table.SelectRows' not in text
    assert 'Number.Abs' not in text

def test_unique_month_relationship():
    text = (MODEL / 'tables/Dim_CM2Month.tmdl').read_text(encoding="utf-8")
    assert 'Table.Distinct' in text and 'isKey' in text
    rel = (MODEL / 'relationships.tmdl').read_text(encoding="utf-8")
    assert 'fromColumn: Fact_CM2.month' in rel
    assert 'toColumn: Dim_CM2Month.month' in rel
    assert 'toCardinality: one' in rel

def test_governed_measures():
    text = (MODEL / 'tables/_Measures.tmdl').read_text(encoding="utf-8")
    for name in ('CM2 Provision Claim','CM2 Recorded DN Claim','CM2 Provision BA','CM2 Covered NSV','CM2 Source Tax','CM2 GST QC','CM2 Modeled','CM2 Source Status','CM2 Matched Claim Gap','CM2 Matched NSV'):
        assert f"measure '{name}'" in text
    governed = text[text.index("measure 'CM2 Provision Claim'"):]
    assert 'INTERSECT(' in governed and 'BLANK()' in governed
    assert 'AVERAGE(' not in governed and '1.18' not in governed
    assert '[CM2 Provision Claim] + [CM2 Recorded DN Claim]' not in governed

def test_real_pbip_page_and_descriptors():
    assert (MODEL.parent / 'definition.pbism').exists()
    root = ROOT / 'ModernTrade_Report.Report/definition'
    pages = json.loads((root/'pages/pages.json').read_text(encoding="utf-8"))
    assert 'CM2Governed' in pages['pageOrder']
    page = json.loads((root/'pages/CM2Governed/page.json').read_text(encoding="utf-8"))
    assert 'CM2' in page['displayName']
    visuals = list((root/'pages/CM2Governed/visuals').glob('*/visual.json'))
    assert len(visuals) >= 3
    payload = '\n'.join(p.read_text(encoding="utf-8") for p in visuals)
    assert 'CM2 Provision Claim' in payload and 'CM2 Recorded DN Claim' in payload

