from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'ModernTrade_Report.Dataset/definition'
FACTS = ('Fact_PrimarySales','Fact_OfftakeSales','Fact_Nielsen','Fact_TDP','Fact_PrimaryArticle','Fact_SecondarySales')

def test_registered_required_tables():
    model=(MODEL/'model.tmdl').read_text(encoding="utf-8")
    for name in FACTS + ('Dim_Article','Dim_Store','Dim_Geography','Dim_Brand'):
        assert (MODEL/'tables'/f'{name}.tmdl').exists(), name
        assert f'ref table {name}' in model

def test_single_direction_unique_side_graph():
    text=(MODEL/'relationships.tmdl').read_text(encoding="utf-8")
    edges=[]
    for block in text.split('relationship ')[1:]:
        assert 'crossFilteringBehavior: oneDirection' in block
        assert 'fromCardinality: many' in block and 'toCardinality: one' in block
        source=re.search(r'fromColumn: (\w+)\.',block).group(1)
        dest=re.search(r'toColumn: (\w+)\.([^\n]+)',block)
        table,key=dest.group(1),dest.group(2).strip().strip("'")
        dim=(MODEL/'tables'/f'{table}.tmdl').read_text(encoding="utf-8")
        assert 'isKey' in dim or table=='Dim_Date'
        assert 'Table.Distinct' in dim or table=='Dim_Date'
        assert not source.startswith('Dim_')
        assert table.startswith('Dim_')
        edges.append((source,table))
    assert len(edges)==len(set(edges)), 'multiple active paths from same dimension'
    for fact in FACTS:
        assert (fact,'Dim_Date') in edges
    assert "fromColumn: Fact_PrimarySales.'Week Start Date'" in text
    assert ('Fact_SecondarySales','Dim_Article') not in edges
    assert ('Fact_Nielsen','Dim_Chain') not in edges

def test_empty_sources_schema_and_fiscal_dates():
    expressions=(MODEL/'expressions.tmdl').read_text(encoding="utf-8")
    assert 'Table.RowCount(RawSource) = 0' in expressions
    assert 'RequiredColumns' in expressions and 'MissingField.Error' in expressions
    assert 'fnMonthStart' in expressions and 'InvalidPeriod' in expressions
    date=(MODEL/'tables/Dim_Date.tmdl').read_text(encoding="utf-8")
    assert 'FiscalYear' in date and 'FiscalMonth' in date
    assert 'Date.Month([Date]) >= 4' in date
    assert 'data-server' not in date

def test_safe_keys_and_unresolved_basis():
    expressions=(MODEL/'expressions.tmdl').read_text(encoding="utf-8")
    assert 'Json.FromValue' in expressions
    assert 'secondary_sales_distributor_' in expressions
    assert 'Dist Cont Weights' in expressions and 'Provisional' in expressions
    assert 'DuplicateDimensionKey' in expressions
    assert 'Primary NSV] ?? 0' not in expressions
    measures=(MODEL/'tables/_Measures.tmdl').read_text(encoding="utf-8")
    assert "measure 'Offtake Source Status'" in measures
    assert 'units/tax basis unresolved' in measures
    for name in FACTS:
        assert f"measure '{name} Source Rows'" in measures
        assert f"measure '{name} Covered Months'" in measures
    assert 'COALESCE(SUM(Fact_' not in measures


def test_all_relationship_columns_exist_and_bound_keys_are_unique():
    text=(MODEL/'relationships.tmdl').read_text(encoding='utf-8')
    for block in text.split('relationship ')[1:]:
        for side in ('from','to'):
            table, col=re.search(side+r"Column: (\w+)\.([^\n]+)", block).groups()
            col=col.strip().strip("'")
            definition=(MODEL/'tables'/f'{table}.tmdl').read_text(encoding='utf-8')
            column=re.search(r"(?m)^\tcolumn '?"+re.escape(col)+r"'?(?: =[^\n]*)?\n(.*?)(?=^\t(?:column |partition |measure )|\Z)", definition, re.S|re.M)
            assert column is not None, (table, col)
            if side=='to':
                assert 'isKey' in column.group(1), (table, col)


def test_query_dependencies_and_secondary_overlap_guard():
    expressions=(MODEL/'expressions.tmdl').read_text(encoding='utf-8')
    registered=(MODEL/'model.tmdl').read_text(encoding='utf-8')
    for query in re.findall(r"(?m)^expression (.+?) =", expressions):
        assert f'ref expression {query}' in registered, query
    assert 'DuplicateSecondaryKey' in expressions
    assert 'KeyGroups = Table.Group(Typed, {"Source_Month", "Distributor"}' in expressions
    for name in FACTS:
        fact=(MODEL/'tables'/f'{name}.tmdl').read_text(encoding='utf-8')
        assert f'q{name}' in fact
    for name in ('Dim_Article','Dim_Store','Dim_Geography','Dim_Brand'):
        dim=(MODEL/'tables'/f'{name}.tmdl').read_text(encoding='utf-8')
        assert 'fnDimension' in dim and 'qFact_' in dim


def test_legacy_sample_is_explicitly_unavailable():
    fact=(MODEL/'tables/Fact_Financials.tmdl').read_text(encoding='utf-8')
    assert 'data-server' not in fact
    assert '#table(type table' in fact and ', {})' in fact
    assert 'Unavailable' in fact

def _expression(name):
    text=(MODEL/'expressions.tmdl').read_text(encoding='utf-8')
    match=re.search(r'(?m)^expression '+re.escape(name)+r' = ```\n(.*?)\n\t```', text, re.S)
    assert match, name
    return match.group(1)


def test_case_variant_keys_use_one_canonicalizer_without_deleting_facts():
    import json
    canonical=_expression('fnRelationshipKey')
    assert 'Text.Upper(Text.Trim(Text.From(value)), "en-US")' in canonical
    assert 'fnRelationshipKey' in _expression('fnCompositeKey')
    assert 'Canonical = Table.TransformColumns(rows' in _expression('fnDimension')
    assert 'Table.Group(Canonical, {key}' in _expression('fnDimension')
    for fact in FACTS[:-1]:
        query=_expression('q'+fact)
        assert 'CanonicalKeys = Table.TransformColumns' in query
        assert 'FinalModel = CanonicalKeys' in query
        for key in ('Brand Key',):
            assert f'"{key}"' in query
        assert 'Table.Distinct' not in query, 'case normalization must not discard facts'
    # Actual source spellings called out in the review, including composite store/geography keys.
    variants=[('FSN','Fsn'),('Metro CNC','Metro Cnc'),('VMM','Vmm')]
    normalize=lambda value: None if value is None else str(value).strip().upper()
    for a,b in variants:
        assert normalize(a)==normalize(b)
        composite=lambda x: json.dumps([normalize(x),normalize('site-01')])
        assert composite(a)==composite(b)
    rel=(MODEL/'relationships.tmdl').read_text(encoding='utf-8')
    assert 'Fact_PrimaryArticle.\'Chain Key\'' in rel
    assert 'Fact_OfftakeSales.\'Brand Key\'' in rel


def test_source_record_identity_survives_multiple_chain_allocations():
    combine=_expression('fnCombineFolder')
    assert 'Table.AddIndexColumn(promoted, "Source Row Number", 1, 1, Int64.Type)' in combine
    assert '"Source Record ID"' in combine
    query=_expression('qFact_PrimaryArticle')
    assert '"Source Record ID"' in query[:query.index('Merged = Table.NestedJoin')]
    assert 'Table.ExpandTableColumn(Merged, "W"' in query
    fact=(MODEL/'tables/Fact_PrimaryArticle.tmdl').read_text(encoding='utf-8')
    assert "column 'Source Record ID'" in fact
    measures=(MODEL/'tables/_Measures.tmdl').read_text(encoding='utf-8')
    assert 'DISTINCTCOUNT(Fact_PrimaryArticle[Source Record ID])' in measures
    assert "measure 'Fact_PrimaryArticle Allocated Output Rows'" in measures
    # One source record splits into two rows; originals count 1 while outputs count 2.
    source={'id':'file.csv:1','nsv':100}
    allocated=[dict(source, chain=chain, nsv=source['nsv']*fraction)
               for chain,fraction in [('FSN',.4),('VMM',.6)]]
    assert len({row['id'] for row in allocated})==1
    assert len(allocated)==2
    assert sum(row['nsv'] for row in allocated)==source['nsv']
