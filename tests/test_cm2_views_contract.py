import sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import cm2_reporting as cm

def fixture():
    p = pd.DataFrame([dict(_FY='FY27', _M='Jul', _Chain='A', _Brand=b,
        _category='Skin', **{'_EAN No.':'1'}, _NSV=n, _TaxLOC=n*.05,
        _MRP=n*2, _Chan='MT') for b,n in [('X',10.004),('Y',-2)]])
    def cut(amount, status='PROVISION'):
        return pd.DataFrame([dict(month='2026-07', chain='A', head='Claim',
             amount_lakh=amount, source_row=2, source_status=status)])
    return p,cut(3),cut(1),cut(5,'PARTIAL_REGISTER')

def test_signed_alternative_views_and_unresolved_model():
    p,c,b,d=fixture()
    result=cm.build_cm2_views(p,c,b,d,cogs_basis_status='UNRESOLVED')
    provision=result['provision']; dn=result['recorded_dn']
    assert sum(r['claim_amount'] for r in provision['rows']) == pytest.approx(3)
    assert sum(r['claim_amount'] for r in dn['rows']) == pytest.approx(5)
    assert sum(r['ba_amount'] for r in provision['rows']) == pytest.approx(1)
    assert any(r['nsv']<0 for r in dn['rows'])
    assert all(r['cm2_value'] is None and r['cm2_pct'] is None for r in dn['rows'])
    assert all(r['status']=='NOT_AVAILABLE' and r['source_status']=='PARTIAL_REGISTER' for r in dn['rows'])
    assert result['matched_bridge']['nsv']==pytest.approx(8.004)
    assert result['matched_bridge']['claim_difference']==pytest.approx(2)
    assert result['matched_bridge']['claim_gap_pct']==pytest.approx(200/8.004)
    assert result['rounding_bridge']['raw_minus_workbook_nsv'] is None

def test_absent_workbook_and_safe_export():
    p,*_=fixture()
    result=cm.build_cm2_views(p,None,None,None,cogs_basis_status='UNRESOLVED')
    assert result['provision']['status']=='NOT_AVAILABLE'
    assert all(r['claim_amount'] is None for r in result['provision']['rows'])
    import io
    target=io.StringIO()
    cm.write_cm2_powerbi_export(result,target)
    text=target.getvalue()
    assert '2026-07' in text and 'NOT_AVAILABLE' in text
    assert all(s not in text for s in ('source_row','Customer','invoice','EAN','source_event_id'))

def test_matched_23_keys_and_rounding_bridge():
    p,c,b,d=fixture()
    p=pd.concat([p.assign(_Chain=f'C{i}') for i in range(23)],ignore_index=True)
    c=pd.concat([c.assign(chain=f'C{i}') for i in range(23)],ignore_index=True)
    d=pd.concat([d.assign(chain=f'C{i}') for i in range(23)],ignore_index=True)
    c.attrs['workbook_primary']=pd.DataFrame([dict(month='2026-07',chain=f'C{i}',brand=b,nsv=n) for i in range(23) for b,n in [('X',10),('Y',-2)]])
    result=cm.build_cm2_views(p,c,b.iloc[:0],d,cogs_basis_status='UNRESOLVED')
    assert result['matched_bridge']['key_count']==23
    assert result['rounding_bridge']['raw_minus_workbook_nsv']==pytest.approx(.004*23)

def test_builder_integration_withholds_uncovered_legacy_cells():
    import build_dashboard_data as bd
    p,*_=fixture()
    p['_CustCode']=''; p['_method']='source'
    p=pd.concat([p,p.assign(_FY='FY26')],ignore_index=True)
    result=bd.cm2_block(p,[])
    assert result['views']['provision']['source_available'] is False
    assert result['cm2_pct'] is None and result['cm2_pct_status']=='NOT_AVAILABLE'
    assert all(r['cm2_pct'] is None for r in result['monthly'])
    assert any(r['nsv']<0 for r in result['by_brand'])

def test_unallocated_and_zero_claim_evidence_export_parity():
    import io, csv
    p,c,b,d=fixture()
    c.loc[0,'amount_lakh']=0
    d=pd.concat([d,pd.DataFrame([dict(month='2026-08',chain='Absent',head='Claim',amount_lakh=-3,source_row=4,source_status='PARTIAL_REGISTER')])],ignore_index=True)
    result=cm.build_cm2_views(p,c,b,d,cogs_basis_status='UNRESOLVED')
    assert result['provision']['coverage']['covered_nsv']==pytest.approx(8.004)
    assert all(r['claim_amount']==0 for r in result['provision']['rows'])
    assert result['recorded_dn']['unallocated']==[dict(month='2026-08',chain='Absent',amount_lakh=-3,status='UNALLOCATED_NO_SALES')]
    target=io.StringIO(); cm.write_cm2_powerbi_export(result,target)
    exported=[r for r in csv.DictReader(io.StringIO(target.getvalue())) if r['record_type']=='SALES']
    expected=[(name,r) for name in ('provision','recorded_dn') for r in result[name]['rows']]
    assert len(exported)==len(expected)
    for actual,(name,row) in zip(exported,expected):
        assert actual['view']==name
        assert all(actual[k]==('' if v is None else str(v)) for k,v in row.items())

def test_rejects_swapped_or_overlapping_claim_cuts():
    p,c,b,d=fixture()
    c['source_type']='DIRECT_DN_ACTUAL'
    with pytest.raises(ValueError,match='PROVISION_CLAIM'):
        cm.build_cm2_views(p,c,b,d,cogs_basis_status='UNRESOLVED')

def test_builder_full_month_names_and_empty_population():
    import build_dashboard_data as bd
    p,c,b,d=fixture(); p['_M']='July'
    result=cm.build_cm2_views(p,c,b,d,cogs_basis_status='UNRESOLVED')
    assert result['matched_bridge']['key_count']==1
    empty=cm.build_cm2_views(p.iloc[:0],None,None,None,cogs_basis_status='UNRESOLVED')
    assert empty['provision']['rows']==[]
    for month in bd._MONTH_IDX:
        cm.build_cm2_views(p.assign(_M=month),None,None,None,cogs_basis_status='UNRESOLVED')

def test_rounding_bridge_uses_chain_month_scope_when_workbook_collapses_brands():
    p,c,b,d=fixture()
    c.attrs['workbook_primary']=pd.DataFrame([dict(month='2026-07',chain='A',brand='Other brands',nsv=8)])
    result=cm.build_cm2_views(p,c,b,d,cogs_basis_status='UNRESOLVED')
    assert result['rounding_bridge']['raw_minus_workbook_nsv']==pytest.approx(.004)

def export_rows(views):
    import io,csv
    stream=io.StringIO(); cm.write_cm2_powerbi_export(views,stream)
    reader=csv.DictReader(io.StringIO(stream.getvalue()))
    return reader.fieldnames,list(reader)

def test_aggregate_exception_export_conserves_all_claim_and_ba_totals():
    p,c,b,d=fixture()
    def extra(frame,chain,amounts):
        return pd.concat([frame]+[frame.assign(chain=chain,amount_lakh=a,source_row=i+10) for i,a in enumerate(amounts)],ignore_index=True)
    c=extra(c,'Absent',[7,-2]); b=extra(b,'UNMAPPED',[-4,1]); d=extra(d,'Absent',[9,-1])
    v=cm.build_cm2_views(p,c,b,d,cogs_basis_status='UNRESOLVED')
    assert v['provision']['unallocated']==[dict(month='2026-07',chain='Absent',status='UNALLOCATED_NO_SALES',amount_lakh=5)]
    assert v['provision']['ba_unallocated']==[dict(month='2026-07',chain='UNMAPPED',status='UNMAPPED',amount_lakh=-3)]
    _,rows=export_rows(v)
    assert {r['record_type'] for r in rows}=={'SALES','UNALLOCATED_CLAIM','UNALLOCATED_BA'}
    for name,claim_total,ba_total in [('provision',float(c.amount_lakh.sum()),float(b.amount_lakh.sum())),('recorded_dn',float(d.amount_lakh.sum()),0)]:
        selected=[r for r in rows if r['view']==name]
        assert sum(float(r['claim_amount'] or 0) for r in selected)==pytest.approx(claim_total)
        assert sum(float(r['ba_amount'] or 0) for r in selected)==pytest.approx(ba_total)
        assert sum(float(r['nsv'] or 0) for r in selected)==pytest.approx(p._NSV.sum())
    exceptions=[r for r in rows if r['record_type']!='SALES']
    assert len(exceptions)==3
    dn_exception=next(r for r in exceptions if r['view']=='recorded_dn')
    assert dn_exception['source_status']=='PARTIAL_REGISTER'
    assert dn_exception['timing_status']=='PARTIAL_REGISTER'
    assert all(r['nsv']=='' and r['brand']=='' and r['cm2_value']=='' for r in exceptions)
    assert all('source_row' not in r and 'source_event_id' not in r for r in rows)

def test_full_versioned_csv_schema_when_population_empty():
    p,c,b,d=fixture()
    full,_=export_rows(cm.build_cm2_views(p,c,b,d,cogs_basis_status='UNRESOLVED'))
    empty,rows=export_rows(cm.build_cm2_views(p.iloc[:0],None,None,None,cogs_basis_status='UNRESOLVED'))
    assert empty==full and not rows
    assert {'schema_version','record_type','claim_amount','ba_amount','nsv','status','gst_review_count'}<=set(empty)

def test_additive_selected_scope_tax_review_and_missing_exposure():
    p,c,b,d=fixture()
    review=p.iloc[[0]].assign(_NSV=-1,_TaxLOC=.2,_MRP=-2)
    missing=p.iloc[[0]].assign(_NSV=2,_TaxLOC=float('nan'),_MRP=4)
    p=pd.concat([p,review,missing],ignore_index=True)
    v=cm.build_cm2_views(p,c,b,d,cogs_basis_status='UNRESOLVED')
    selected=[r for r in v['provision']['rows'] if r['brand']=='X']
    assert sum(r['gst_review_count'] for r in selected)==1
    assert sum(r['gst_missing_tax_count'] for r in selected)==1
    assert sum(r['gst_valid_5_count'] for r in selected)==1
    assert sum(r['reviewed_amount'] for r in selected)==1
    assert sum(r['reviewed_nsv'] or 0 for r in selected)==-1
    assert sum(r['reviewed_tax'] or 0 for r in selected)==pytest.approx(.2)
    assert sum(r['missing_tax_nsv'] or 0 for r in selected)==2
    _,rows=export_rows(v)
    exported=[r for r in rows if r['view']=='provision' and r['brand']=='X']
    for field in ('gst_review_count','gst_missing_tax_count','gst_valid_5_count','reviewed_amount','reviewed_nsv','reviewed_tax','missing_tax_nsv'):
        assert sum(float(r[field] or 0) for r in exported)==pytest.approx(sum(r[field] or 0 for r in selected))
