"""
Regression test for FM-23 (FY12 -- month/FY key mismatch): targets_block()
is called with target_rows from EITHER load_targets_csv() -- which returns
(fy_tag_string, 'Mon-YY' label, value) e.g. ("FY27", "Apr-26", ...) -- OR
load_ty_target() -- which returns (date, 'Mon-YY' label, value) e.g.
(datetime.date(2026, 4, 1), "Apr-26", ...), because its OTHER caller,
forecast_block_ty(), needs the real date object (calls .year/.month on it
directly) and can't be changed without breaking that caller.

Before the fix, targets_block() did `fy = target_rows[0][0]` then
`{lbl: v for tag, lbl, v in target_rows if tag == fy}` -- comparing tag to
fy works fine for string tags (every row in a 12-month FY shares the same
tag) but silently collapses to just the FIRST row when tag is a date
object (12 distinct dates, only the first equals itself). This understated
fy_target by ~92% (11 of 12 months dropped), rendered fy_tag as a raw
Python date object instead of a string like "FY27", and silently dropped
all but the first month of any actuals period-to-date comparison.

This is dormant in the current committed dashboard/data.js (which used the
load_targets_csv() fallback -- confirmed via its own "source" field), so it
has never yet corrupted a real build, but would corrupt the very next
build that supplies the real, gitignored
FY2627_TGT_and_sales_team_mapping.xlsb file to --src.
"""
import datetime
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import build_dashboard_data as bdd  # noqa: E402


def _csv_shaped_rows():
    """Matches load_targets_csv()'s real return shape: (fy_tag, label, value)."""
    months = [("Apr", 2026), ("May", 2026), ("Jun", 2026), ("Jul", 2026), ("Aug", 2026),
              ("Sep", 2026), ("Oct", 2026), ("Nov", 2026), ("Dec", 2026),
              ("Jan", 2027), ("Feb", 2027), ("Mar", 2027)]
    return [("FY27", f"{m}-{y % 100:02d}", 1000.0) for m, y in months]


def _date_shaped_rows():
    """Matches load_ty_target()'s real return shape: (date, label, value)."""
    month_nums = {"Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9,
                  "Oct": 10, "Nov": 11, "Dec": 12, "Jan": 1, "Feb": 2, "Mar": 3}
    months = [("Apr", 2026), ("May", 2026), ("Jun", 2026), ("Jul", 2026), ("Aug", 2026),
              ("Sep", 2026), ("Oct", 2026), ("Nov", 2026), ("Dec", 2026),
              ("Jan", 2027), ("Feb", 2027), ("Mar", 2027)]
    rows = []
    for m, y in months:
        d = datetime.date(y, month_nums[m], 1)
        rows.append((d, d.strftime("%b-%y"), 1000.0))
    rows.sort(key=lambda x: x[0])
    return rows


def test_date_shaped_rows_produce_full_fy_target_not_one_month():
    """The exact failure this bug caused: fy_target collapsed to 1000
    (one month) instead of 12000 (the full FY) when fed date-shaped rows."""
    tb = bdd.targets_block(_date_shaped_rows(), {}, same_period=None)
    assert tb["fy_target"] == 12000.0, (
        f"fy_target={tb['fy_target']} -- expected 12000.0 (12 months x 1000), "
        f"got a value consistent with only 1 month surviving the (broken) tag filter"
    )
    assert tb["months_in_fy"] == 12, f"months_in_fy={tb['months_in_fy']}, expected 12"


def test_date_shaped_rows_produce_string_fy_tag_not_a_date_object():
    tb = bdd.targets_block(_date_shaped_rows(), {}, same_period=None)
    assert isinstance(tb["fy_tag"], str), (
        f"fy_tag is {type(tb['fy_tag'])} ({tb['fy_tag']!r}) -- expected a string like 'FY27', "
        f"not a raw datetime.date (which would render nonsensically in the dashboard UI)"
    )
    assert tb["fy_tag"] == "FY27"


def test_date_shaped_rows_period_to_date_actuals_keep_all_matching_months():
    """The full failure chain: with the bug, actuals with 3 real months of
    data would only ever compare against the 1 surviving target month."""
    actuals = {"offtake": {"Apr-26": 800.0, "May-26": 800.0, "Jun-26": 800.0}}
    tb = bdd.targets_block(_date_shaped_rows(), actuals, same_period=None)
    m = tb["measures"]["offtake"]
    assert m["months"] == ["Apr-26", "May-26", "Jun-26"], m["months"]
    assert m["target"] == 3000.0, m["target"]
    assert m["actual"] == 2400.0, m["actual"]


def test_csv_shaped_rows_unaffected_by_the_normalization():
    """The currently-live path (string fy_tag already) must produce
    identical results before and after the fix -- this is a normalization
    for the OTHER shape, not a behavior change for the working one."""
    tb = bdd.targets_block(_csv_shaped_rows(), {}, same_period=None)
    assert tb["fy_tag"] == "FY27"
    assert tb["fy_target"] == 12000.0
    assert tb["months_in_fy"] == 12


def test_both_shapes_produce_identical_output_for_the_same_calendar_data():
    """The real proof of correctness: feeding targets_block() the SAME
    underlying FY27 target data in both shapes must produce the same
    fy_target/fy_tag/months_in_fy -- the shape is an accident of which
    loader produced it, not a real difference in the data."""
    tb_date = bdd.targets_block(_date_shaped_rows(), {}, same_period=None)
    tb_csv = bdd.targets_block(_csv_shaped_rows(), {}, same_period=None)
    assert tb_date["fy_tag"] == tb_csv["fy_tag"]
    assert tb_date["fy_target"] == tb_csv["fy_target"]
    assert tb_date["months_in_fy"] == tb_csv["months_in_fy"]
