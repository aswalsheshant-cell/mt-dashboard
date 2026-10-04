import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def inspect(root, manifest):
    # A missing implementation must fail as a behavioral assertion first.
    assert (ROOT / 'scripts/powerbi_full_sources.py').exists(), 'source inspector is not implemented'
    from scripts.powerbi_full_sources import inspect_sources
    path = root / 'manifest.json'
    path.write_text(json.dumps(manifest), encoding='utf-8')
    return inspect_sources(root, path)['sources']


def contract(required=None):
    return {'required_periods': required or [], 'sources': [{'id': 'sales', 'paths': ['PowerBI/RawDataFolders/Offtake_Monthly/*.csv'], 'key_columns': ['Month', 'Store'], 'period_columns': ['Month'], 'grain': 'month/store', 'dimensions': ['date', 'store']}]}


def test_empty_current_period_is_unavailable_not_zero(tmp_path):
    folder = tmp_path / 'PowerBI/RawDataFolders/Offtake_Monthly'
    folder.mkdir(parents=True)
    (folder / '_TEMPLATE_data.csv').write_text('Month,Store\n2026-09,A\n')
    assert inspect(tmp_path, contract(['2026-09']))['sales']['row_count'] is None
    (folder / 'old.csv').write_text('Month,Store\n2026-08,A\n')
    result = inspect(tmp_path, contract(['2026-09']))['sales']
    assert result['available'] is False
    assert result['row_count'] == 1
    assert result['missing_periods'] == ['2026-09']


def test_header_only_file_is_available_zero_rows(tmp_path):
    folder = tmp_path / 'PowerBI/RawDataFolders/Offtake_Monthly'
    folder.mkdir(parents=True)
    (folder / 'empty.csv').write_text('Month,Store\n')
    result = inspect(tmp_path, contract())['sales']
    assert result['available'] is True
    assert result['row_count'] == 0


def test_duplicate_source_keys_are_reported_without_modifying_input(tmp_path):
    folder = tmp_path / 'PowerBI/RawDataFolders/Offtake_Monthly'
    folder.mkdir(parents=True)
    path = folder / 'sales.csv'
    content = 'Month,Store\n2026-09,A\n2026-09,A\n'
    path.write_text(content)
    result = inspect(tmp_path, contract())['sales']
    assert result['row_count'] == 2
    assert any(issue['type'] == 'duplicate_key' for issue in result['key_issues'])
    assert path.read_text() == content


def test_actual_repository_paths_and_query_filters():
    assert (ROOT / 'scripts/powerbi_full_sources.py').exists(), 'source inspector is not implemented'
    from scripts.powerbi_full_sources import inspect_sources
    manifest = ROOT / 'PowerBI/full_report_sources.json'
    result = inspect_sources(ROOT, manifest)['sources']
    assert result['Fact_OfftakeSales']['files']
    assert result['Fact_PrimaryArticle']['files']
    assert result['Fact_PrimarySales']['available'] is False
    assert result['Fact_Nielsen']['row_count'] is None
    assert all(Path(p).name.startswith('secondary_sales_distributor_') for p in result['Fact_SecondarySales']['files'])
    assert all(Path(p).name.startswith('claim_master_chain_') for p in result['Fact_ClaimMaster']['files'])
    config = json.loads(manifest.read_text())
    assert {p.name for p in (ROOT / 'PowerBI/PowerQuery').glob('*.pq') if 10 <= int(p.name[:2]) <= 46} == {Path(s['query']).name for s in config['sources']}

def test_repository_month_formats(tmp_path):
    folder = tmp_path / 'PowerBI/RawDataFolders/Offtake_Monthly'
    folder.mkdir(parents=True)
    (folder / 'sales.csv').write_text("Month,Store,Year\nApr'26,A,2026.0\n")
    assert inspect(tmp_path, contract(['2026-04']))['sales']['available'] is True


def test_duplicate_manifest_ids_are_rejected(tmp_path):
    manifest = contract()
    manifest['sources'] *= 2
    with pytest.raises(ValueError, match='Duplicate source IDs'):
        inspect(tmp_path, manifest)


def test_quarter_source_covers_only_its_three_months(tmp_path):
    folder = tmp_path / 'PowerBI/RawDataFolders/Offtake_Monthly'
    folder.mkdir(parents=True)
    (folder / 'sales.csv').write_text('Month,Store\nApr-Jun 2026,A\n')
    result = inspect(tmp_path, contract(['2026-07']))['sales']
    assert result['periods'] == ['2026-04', '2026-05', '2026-06']
    assert result['available'] is False

def test_expense_fiscal_year_text_resolves_april_and_january(tmp_path):
    folder = tmp_path / 'PowerBI/RawDataFolders/Offtake_Monthly'
    folder.mkdir(parents=True)
    (folder / 'sales.csv').write_text('Month,Store,FY\nApril,A,FY25-26\nJanuary,B,FY25-26\n')
    result = inspect(tmp_path, contract(['2025-04', '2026-01']))['sales']
    assert result['available'] is True
    assert result['periods'] == ['2025-04', '2026-01']

def test_historical_source_without_selected_period_is_unassessed(tmp_path):
    folder = tmp_path / 'PowerBI/RawDataFolders/Offtake_Monthly'
    folder.mkdir(parents=True)
    (folder / 'old.csv').write_text('Month,Store\n2026-04,A\n')
    result = inspect(tmp_path, contract())['sales']
    assert result['available'] is True
    assert result['current_period_status'] == 'unassessed'
    assert result['current_period_available'] is False


def test_missing_required_file_in_multi_file_source_fails_closed(tmp_path):
    (tmp_path / 'present.csv').write_text('Month,Store\n2026-09,A\n')
    manifest = contract(['2026-09'])
    manifest['sources'][0]['paths'] = ['present.csv', 'missing.csv']
    result = inspect(tmp_path, manifest)['sales']
    assert result['available'] is False
    assert result['missing_paths'] == ['missing.csv']
    assert any(i['type'] == 'missing_file' for i in result['key_issues'])


def test_physical_source_dependency_propagates_without_losing_rows(tmp_path):
    (tmp_path / 'sales.csv').write_text('Month,Store\n2026-09,A\n')
    manifest = contract(['2026-09'])
    manifest['sources'][0]['paths'] = ['sales.csv']
    manifest['sources'][0]['dependencies'] = ['weights']
    manifest['sources'].append({'id': 'weights', 'paths': ['weights.csv'], 'period_columns': ['Month']})
    result = inspect(tmp_path, manifest)['sales']
    assert result['available'] is False
    assert result['current_period_available'] is False
    assert result['row_count'] == 1
    assert result['files'] == ['sales.csv']
    assert any(i['type'] == 'unavailable_dependency' for i in result['key_issues'])
    config = json.loads((ROOT / 'PowerBI/full_report_sources.json').read_text())
    assert 'DistContWeights' in next(s for s in config['sources'] if s['id'] == 'Fact_PrimaryArticle')['dependencies']


def test_short_csv_row_is_diagnosed_and_other_sources_are_inspected(tmp_path):
    (tmp_path / 'bad.csv').write_text('Month,Year,Store\n2026-09\n')
    (tmp_path / 'good.csv').write_text('Month,Store\n2026-09,A\n')
    manifest = contract(['2026-09'])
    manifest['sources'][0]['paths'] = ['bad.csv']
    manifest['sources'].append({'id': 'other', 'paths': ['good.csv'], 'period_columns': ['Month']})
    result = inspect(tmp_path, manifest)
    assert result['sales']['available'] is False
    assert any(i['type'] == 'malformed_row' for i in result['sales']['key_issues'])
    assert result['other']['current_period_available'] is True

def test_forward_dependencies_propagate_current_period_unassessment(tmp_path):
    (tmp_path / 'sales.csv').write_text('Month,Store\n2026-04,A\n')
    manifest = contract()
    manifest['sources'][0]['paths'] = ['sales.csv']
    manifest['sources'] = [{'id': 'outer', 'dependencies': ['inner']}, {'id': 'inner', 'dependencies': ['sales']}] + manifest['sources']
    result = inspect(tmp_path, manifest)
    assert result['outer']['available'] is True
    assert result['outer']['current_period_status'] == 'unassessed'
    assert result['outer']['current_period_available'] is False
    assert result['outer']['row_count'] is None
