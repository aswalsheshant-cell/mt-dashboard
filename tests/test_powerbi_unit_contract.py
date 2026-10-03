"""Structural unit contract for Power Query; live M refresh remains a Desktop gate."""

import re
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OFFTAKE = ROOT / "PowerBI" / "PowerQuery" / "11_Fact_OfftakeSales.pq"


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

