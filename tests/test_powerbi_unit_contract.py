"""Structural unit contract for Power Query; live M refresh remains a Desktop gate."""

import re
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFTAKE = ROOT / "PowerBI" / "PowerQuery" / "11_Fact_OfftakeSales.pq"
SECONDARY_DAX = ROOT / "PowerBI" / "DAX" / "14_SecondarySales_Measures.dax"
EFFICIENCY_PQ = ROOT / "PowerBI" / "PowerQuery" / "43_SecondarySalesEfficiency.pq"
CORE_DAX = ROOT / "PowerBI" / "DAX" / "01_CoreMeasures.dax"
DATE_DAX = ROOT / "PowerBI" / "DAX" / "00_DateTable.dax"
FY_FUNCTION = ROOT / "PowerBI" / "PowerQuery" / "02_fnFYLabel.pq"
QUICKSETUP_CONFIG = ROOT / "PowerBI" / "QuickSetup" / "quicksetup_steps.json"


def _code(path):
    return "\n".join(line.split("//", 1)[0] for line in path.read_text(encoding="utf-8").splitlines())


def test_offtake_nsv_scales_once_at_import_boundary_and_mrp_stays_rupees():
    code = _code(OFFTAKE)
    scaling = re.search(
        r"\bScaled\s*=\s*Table\.TransformColumns\(Typed,\s*\{\s*\{\s*"
        r'"Offtake NSV"\s*,\s*each\s+if\s+_\s*=\s*null\s+then\s+null\s+else\s+_\s*\*\s*(\d+)',
        code,
    )
    assert scaling, "Offtake NSV must have an explicit null-safe source-lakh to model-rupee conversion"
    factor = int(scaling.group(1))
    assert factor == 100000
    assert Decimal("1.5") * factor == Decimal("150000")
    assert Decimal("-0.2") * factor == Decimal("-20000")
    assert re.search(r"\bTrimmed\s*=\s*Table\.TransformColumns\(Scaled,", code)
    assert not re.search(r'"MRP Sales"\s*,\s*each[^\n]*[*/]', code)
    assert code.count('"Offtake NSV", each if _ = null then null else _ * 100000') == 1


def test_distributor_sell_through_uses_lakh_on_both_sides():
    code = _code(SECONDARY_DAX)
    body = code.split("[Sell-Through %] =", 1)[1].split("[Sell-Through % (Capped 200)]", 1)[0]
    assert re.search(r"VAR\s+_secondary\s*=\s*\[Secondary NSV Lakh\]", body)
    assert re.search(
        r"VAR\s+_primary\s*=\s*DIVIDE\s*\(\s*\[Total Primary Article NSV\]\s*,\s*100000\s*\)",
        body,
    ), "Primary Article NSV is model rupees and must be converted to lakh"
    assert re.search(r"DIVIDE\s*\(\s*_secondary\s*,\s*_primary\s*\)", body)
    assert Decimal("150000") / Decimal(100000) == Decimal("1.5")


def test_efficiency_table_documents_model_rupee_operands():
    text = EFFICIENCY_PQ.read_text(encoding="utf-8")
    assert "Primary NSV      — Rupees" in text
    assert "Offtake NSV      — Rupees" in text
    code = _code(EFFICIENCY_PQ)
    assert re.search(r"\[Offtake NSV\]\s*/\s*\[Primary NSV\]", code)


def test_reliance_chain_mapping_keeps_rbc_separate_without_dropping_rows():
    code = _code(OFFTAKE)
    assert '"Reliance Brand Counter"' in code
    assert '"Reliance Retail"' in code
    assert re.search(r'Text\.Lower\s*\(\s*Text\.Trim\s*\(\s*\[Store Type\]', code)
    assert re.search(r"\bFixBrand\s*=\s*Table\.ReplaceValue\(RenameChain,", code)
    assert code.count("Table.SelectRows(") == 1  # existing nonempty-row guard only


def test_mixed_month_labels_use_file_fallback_and_fy_from_monthstart():
    code = _code(OFFTAKE)
    assert "Data Source File" in code
    assert "offtake_store_article_" in code
    assert "Number.FromText" in code  # Excel serial and quoted year
    assert "MonthStart" in code
    assert "fnFYLabel([MonthStart])" in code
    assert "error Error.Record" in code  # missing or contradictory period fails refresh


def test_offtake_business_totals_use_mt_scope_while_rbc_remains_visible():
    code = _code(CORE_DAX)
    assert "Total RBC NSV =" in code
    assert re.search(r"^NSV\s*=\s*\[Total MT NSV\]", code, re.MULTILINE)
    assert re.search(r"^Actual \(Basis\)\s*=\s*\[Total MT NSV\]", code, re.MULTILINE)
    assert re.search(r"^Primary vs Offtake Gap\s*=\s*\[Total Primary NSV\]\s*-\s*\[Total MT NSV\]", code, re.MULTILINE)
    assert re.search(r"^Primary vs Offtake Gap %\s*=\s*DIVIDE\s*\(\s*\[Total Primary NSV\]\s*-\s*\[Total MT NSV\],\s*\[Total MT NSV\]\s*\)", code, re.MULTILINE)


def test_efficiency_does_not_turn_missing_months_into_zero_sales():
    code = _code(EFFICIENCY_PQ)
    assert not re.search(r"Table\.ReplaceValue\([^\n]+null,\s*0,", code)
    assert re.search(r"\bAddOutlier\s*=\s*Table\.AddColumn\(Expanded,", code)
    assert "[Offtake NSV] = null" in code
    assert "[Primary NSV] = null" in code
    assert '"No Offtake Data"' in code


def test_fy_function_is_available_and_date_table_uses_two_digit_fy():
    fn = _code(FY_FUNCTION)
    assert "if m >= 4 then y else y - 1" in fn
    assert "Number.Mod(startYear, 100)" in fn
    assert '"02_fnFYLabel.pq"' in QUICKSETUP_CONFIG.read_text(encoding="utf-8")
    date = _code(DATE_DAX)
    assert 'FORMAT(MOD(y, 100), "00")' in date
    assert 'FORMAT(MOD(y - 1, 100), "00")' in date


def test_primary_kpi_uses_loaded_article_fact_and_secondary_date_refs_resolve():
    core = _code(CORE_DAX)
    assert "Total Primary NSV = SUM ( 'Fact Primary Article'[Primary NSV] )" in core
    assert "Total Primary Qty = SUM ( 'Fact Primary Article'[Primary Qty] )" in core
    secondary = _code(SECONDARY_DAX)
    assert "'Date'[" not in secondary
    assert "'Date Table'[Date]" in secondary
    assert "'Date Table'[FY Year] = \"26-27\"" in secondary

