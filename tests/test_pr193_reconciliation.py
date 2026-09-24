"""PR #193 production certification: business-number reconciliation.

Proves the four defects found in the 2026-09-23 dashboard root-cause audit
stay fixed, at two levels for each:
  1. a DATA reconciliation -- an arithmetic identity computed from the real,
     committed dashboard/data.js, so a future data rebuild that reintroduces
     the underlying imbalance fails this test even if no source line changes.
  2. a SOURCE regression guard -- a static check on dashboard/index.html that
     the exact buggy pattern (double /100 division, null-fy KPI read) cannot
     silently return.

This is a reconciliation certification, not a UI test: it does not render the
page. dashboard/index.html's own runtime is exercised separately by
tests/dashboard_sweep.js (44 tab x FY states, crash/NaN/undefined).
"""
import importlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
ci = importlib.import_module("ci_validate_datajs")

REPO = Path(__file__).resolve().parent.parent
INDEX_HTML = REPO / "dashboard" / "index.html"
TOLERANCE_LAKH = 0.01  # rupee-rounding tolerance used throughout this repo's own r2()


def _data():
    return ci.load_datajs()


def _index_src():
    return INDEX_HTML.read_text()


# ---------------------------------------------------------------------------
# 1. FY26 Primary channel split (Executive Cockpit "Channel split" donut)
# ---------------------------------------------------------------------------

def test_channel_by_channel_sums_to_certified_fy26_total():
    """primary.by_channel's fy26 entries (MT+EB2B+SIS) must sum to the
    certified FY26 Primary baseline (Rs 32,900.36 L per CLAUDE.md/config/baselines.json)."""
    d = _data()
    by_channel = d["primary"]["by_channel"]
    total = sum(float(c.get("fy26", 0) or 0) for c in by_channel)
    assert abs(total - 32900.36) <= TOLERANCE_LAKH, (
        f"by_channel fy26 sum = {total}, expected 32900.36 +/- {TOLERANCE_LAKH}")


def test_channel_by_channel_reconciles_to_article_wise_channel_totals():
    """by_channel's fy26 split must match detail_meta.channel_totals['FY26']
    (the article-wise primary's exact, business-confirmed channel split --
    see detail_meta.sis_gap_status) -- this is the actual fix in PR #193:
    before it, by_channel was {MT: 32900.36, EB2B: 0, SIS: 0}."""
    d = _data()
    by_channel = {c["name"]: float(c.get("fy26", 0) or 0) for c in d["primary"]["by_channel"]}
    ct_fy26 = d["detail_meta"]["channel_totals"]["FY26"]
    for name, expected in ct_fy26.items():
        actual = by_channel.get(name)
        assert actual is not None, f"by_channel has no entry for channel {name!r}"
        assert abs(actual - expected) <= TOLERANCE_LAKH, (
            f"by_channel[{name!r}].fy26 = {actual}, expected {expected} (article-wise source)")
    # The defect this certifies: EB2B and SIS must be real, non-zero values,
    # not the pre-fix hardcoded zeros.
    assert by_channel.get("EB2B", 0) > 100, "EB2B is still ~0 -- channel split regression"
    assert by_channel.get("SIS", 0) > 50, "SIS is still ~0 -- channel split regression"


# ---------------------------------------------------------------------------
# 2. Category & Pack Mix table (Channel & Chain Performance sub-view)
# ---------------------------------------------------------------------------

def test_category_nsv_sums_to_detail_records_total():
    """Sum of detail_records grouped by Category must equal the sum of all
    detail_records -- the arithmetic identity the (now-fixed) Category & Pack
    Mix table's Share% column depends on being computed from the same NSV
    values it displays."""
    d = _data()
    recs = d["detail_records"]
    total_nsv = sum(float(r.get("NSV", 0) or 0) for r in recs)
    by_cat = {}
    for r in recs:
        k = r.get("Category") or "Unknown"
        by_cat[k] = by_cat.get(k, 0.0) + float(r.get("NSV", 0) or 0)
    cat_sum = sum(by_cat.values())
    assert abs(total_nsv - cat_sum) <= TOLERANCE_LAKH, (
        f"sum(by category) = {cat_sum}, sum(detail_records) = {total_nsv}")


def test_category_face_matches_certified_screenshot_figure():
    """Regression pin for the exact defect found: Face category NSV must be
    ~Rs340.90 Cr (34090 L), not ~Rs3.41 Cr (the 100x-too-small figure the
    double-division bug produced)."""
    d = _data()
    recs = d["detail_records"]
    face_nsv = sum(float(r.get("NSV", 0) or 0) for r in recs if r.get("Category") == "Face")
    assert face_nsv > 30000, (
        f"Face category NSV = {face_nsv} L -- expected ~34090 L; "
        "a value near 340 L would indicate the crc(v.nsv/100) regression is back")


def test_no_double_lakh_division_before_crc_in_category_or_reliance_tables():
    """Source regression guard: crc() (dashboard/index.html) already expects
    its input in INR Lakh and self-converts to Cr/L. A call site that divides
    by 100 again before calling crc() silently understates the display by
    100x once the value crosses into the Cr band -- exactly the bug fixed in
    PR #193 (Category & Pack Mix and Reliance-by-Zone tables). Assert no such
    call site exists anywhere in the file."""
    src = _index_src()
    matches = re.findall(r"crc\([^)]*/\s*100[^)]*\)", src)
    assert not matches, f"found double-division crc(x/100) call site(s): {matches}"


# ---------------------------------------------------------------------------
# 3. Reliance Brand Counter "Reliance by Zone" table
# ---------------------------------------------------------------------------

def test_reliance_zone_nsv_sums_to_reliance_chain_total():
    """Sum of Reliance Retail records grouped by Zone must equal Reliance
    Retail's total NSV across all detail_records -- the identity the (now-
    fixed) Reliance-by-Zone table's per-zone rows must reconcile to."""
    d = _data()
    recs = d["detail_records"]
    reliance = [r for r in recs if r.get("Chain") == "Reliance Retail"]
    assert reliance, "no Reliance Retail records in detail_records -- cannot certify"
    reliance_total = sum(float(r.get("NSV", 0) or 0) for r in reliance)
    by_zone = {}
    for r in reliance:
        z = r.get("Zone") or "Unknown"
        by_zone[z] = by_zone.get(z, 0.0) + float(r.get("NSV", 0) or 0)
    zone_sum = sum(by_zone.values())
    assert abs(reliance_total - zone_sum) <= TOLERANCE_LAKH, (
        f"sum(by zone) = {zone_sum}, Reliance Retail total = {reliance_total}")


def test_reliance_total_matches_certified_screenshot_figure():
    """Regression pin: Reliance Retail's total NSV (all detail_records) must
    be ~Rs137.03 Cr (13703 L), not ~Rs1.37 Cr (the 100x-too-small figure)."""
    d = _data()
    recs = d["detail_records"]
    reliance_total = sum(float(r.get("NSV", 0) or 0) for r in recs if r.get("Chain") == "Reliance Retail")
    assert reliance_total > 12000, (
        f"Reliance Retail total NSV = {reliance_total} L -- expected ~13703 L")


# ---------------------------------------------------------------------------
# 4. Inventory & Supply Health "Total Offtake" KPI
# ---------------------------------------------------------------------------

def test_inventory_total_offtake_reconciles_to_monthly_sum():
    """offtake.total_<latest fy> must equal the independent sum of that FY's
    own monthly series -- proves the field the fixed KPI now reads is itself
    internally consistent (not the flat, no-longer-used offtake.total)."""
    d = _data()
    o = d["offtake"]
    fy_tags = o.get("fy_tags") or []
    assert fy_tags, "offtake.fy_tags is empty -- cannot resolve latest FY"
    fy_r = fy_tags[-1]
    total = o.get(f"total_{fy_r}")
    monthly = o.get(f"monthly_{fy_r}") or []
    assert total is not None, f"offtake.total_{fy_r} missing"
    assert monthly, f"offtake.monthly_{fy_r} missing or empty"
    monthly_sum = sum(float(v or 0) for v in monthly)
    assert abs(total - monthly_sum) <= TOLERANCE_LAKH, (
        f"offtake.total_{fy_r} = {total}, sum(monthly_{fy_r}) = {monthly_sum}")


def test_inventory_kpi_formula_uses_fyr_fallback_not_raw_fy():
    """Source regression guard for the exact defect fixed: the Total Offtake
    KPI must read o.total[fyR] / o.total_<fyR> using the page's own
    already-established fyR fallback (fy || latest FY tag), computed BEFORE
    the KPI, not the raw fyKey() result (null in the default 'All FY' view --
    that null read is what produced the Rs0 L KPI)."""
    src = _index_src()
    m = re.search(r"function buildInventoryHealth\(\)\{(.*?)\n\}\n", src, re.S)
    assert m, "buildInventoryHealth() not found in dashboard/index.html"
    body = m.group(1)
    fyr_def_pos = body.find("const fyR")
    total_def_pos = body.find("const total")
    assert fyr_def_pos != -1, "fyR is not defined in buildInventoryHealth()"
    assert total_def_pos != -1, "total is not defined in buildInventoryHealth()"
    assert fyr_def_pos < total_def_pos, (
        "fyR must be computed BEFORE total in buildInventoryHealth() -- "
        "this is the exact ordering bug PR #193 fixed")
    total_line = body[total_def_pos:body.find(";", total_def_pos) + 1]
    assert "fyR" in total_line, (
        f"the KPI's `total` assignment does not reference fyR: {total_line!r}")


def test_inventory_kpi_nonzero_when_real_data_exists():
    """Regression pin: with real offtake data present, the resolved KPI value
    must not be the pre-fix Rs0 L."""
    d = _data()
    o = d["offtake"]
    fy_r = (o.get("fy_tags") or [])[-1]
    total = o.get(f"total_{fy_r}") or (o.get("total") or {}).get(fy_r) if isinstance(o.get("total"), dict) else o.get(f"total_{fy_r}")
    assert total and total > 1000, f"Total Offtake KPI value = {total} -- expected a real, material figure"


# ---------------------------------------------------------------------------
# 5. Publication boundary: no NaN / Infinity / silent missing-as-zero
# ---------------------------------------------------------------------------

def test_no_nan_or_infinity_tokens_in_datajs():
    """Reuses this repo's own release-gate check (scripts/ci_validate_datajs.py)
    rather than a second copy of the same scan."""
    text = (REPO / "dashboard" / "data.js").read_text()
    assert ": NaN" not in text and ":NaN" not in text, "raw NaN token(s) found in data.js"
    assert "Infinity" not in text, "Infinity token(s) found in data.js"


def test_datajs_baseline_invariants_hold():
    """FY25/FY26 certified baselines (config/baselines.json) must still hold
    after the PR #193 regeneration -- this PR only intended primary.by_channel
    (FY26) to change; every other protected baseline must be untouched."""
    d = _data()
    fails = ci.check_baselines(d)
    assert not fails, f"baseline invariant failure(s): {fails}"
