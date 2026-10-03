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


def _measure(name):
    import re
    text = (MODEL/'tables/_Measures.tmdl').read_text(encoding='utf-8')
    return re.search(r"\tmeasure '"+re.escape(name)+r"' =\n(.*?)(?=\n\tmeasure |\Z)", text, re.S).group(1)

def test_brand_preserves_exception_visual_population():
    page=json.loads((ROOT/'ModernTrade_Report.Report/definition/pages/CM2Governed/page.json').read_text())
    assert {'source':'Filterbrand','target':'Exceptions','type':'NoFilter'} in page.get('visualInteractions',[])
    assert 'REMOVEFILTERS(Fact_CM2[brand])' in _measure('CM2 Unallocated BA')

def test_exception_row_types_and_ba_binding():
    for name,kind in [('CM2 Unallocated Claim','UNALLOCATED_CLAIM'),('CM2 Unallocated BA','UNALLOCATED_BA')]:
        assert f'KEEPFILTERS(Fact_CM2[record_type] = "{kind}")' in _measure(name)
        assert 'REMOVEFILTERS(Fact_CM2[brand])' in _measure(name)
    visual=(ROOT/'ModernTrade_Report.Report/definition/pages/CM2Governed/visuals/Exceptions/visual.json').read_text()
    assert 'CM2 Unallocated BA' in visual

def test_monetary_qc_is_scoped_and_visible():
    visual=(ROOT/'ModernTrade_Report.Report/definition/pages/CM2Governed/visuals/Status/visual.json').read_text()
    for name,field in [('CM2 Reviewed Amount','reviewed_amount'),('CM2 Reviewed NSV','reviewed_nsv'),('CM2 Reviewed Tax','reviewed_tax'),('CM2 Missing Tax NSV','missing_tax_nsv')]:
        dax=_measure(name)
        assert f'SUM(Fact_CM2[{field}])' in dax
        assert 'HASONEVALUE(Fact_CM2[view])' in dax and '"SALES"' in dax
        assert name in visual

def test_finance_sums_are_measures_not_context_transition_columns():
    fact=(MODEL/'tables/Fact_Financials.tmdl').read_text()
    measures=(MODEL/'tables/_Measures.tmdl').read_text(encoding='utf-8')
    for name in ['NSV_Actual_INR_Sum','COGS_INR_Sum','Trade_Spend_INR_Sum','Freight_INR_Sum']:
        assert f'column {name}' not in fact
        assert f'measure {name} = SUM(' in measures
