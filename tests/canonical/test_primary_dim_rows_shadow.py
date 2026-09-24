"""Makes scripts/canonical/primary_dim_rows_shadow.py's shadow comparison a
durable, re-runnable regression check (Phase 2B-B, item 1) rather than a
one-off script output reported only in prose.

Proves, against real data (detail_records, the certified article-level
Primary source -- see that module's docstring for why the actual
gitignored primary.xlsx workbook isn't available in this environment):
every (chain, FY) cell that differs between the pre-fix and post-fix
dim_rows() behavior is EXACTLY the intended effect (a fabricated 0 becoming
None), never an unexpected divergence, and no real (non-fabricated) value
is ever disturbed."""
from canonical import facts
from canonical.primary_dim_rows_shadow import build_report


def test_shadow_comparison_has_zero_unexpected_divergence(data):
    _, _, diffs = build_report(data)
    unexpected = [d for d in diffs if "UNEXPECTED" in d["classification"]]
    assert unexpected == [], f"unexpected divergence(s): {unexpected}"


def test_shadow_comparison_only_changes_fabricated_zeros_to_none(data):
    _, _, diffs = build_report(data)
    assert diffs, "expected at least the known fabricated-zero cases to show up as diffs"
    for d in diffs:
        assert d["old"] == 0, f"expected every diff's old value to be the fabricated 0, got {d}"
        assert d["new"] is None, f"expected every diff's new value to be None, got {d}"


def test_shadow_comparison_includes_the_two_empirically_confirmed_chains(data):
    """Dabur New U and Medanta were found by direct inspection of the real
    certified data.js (fy26: 0 despite no real FY26 rows) before this fix --
    pin them so this test fails loudly if a future data.js rebuild makes
    them no longer exercise the fix (in which case this pin should be
    revisited, not silently left passing on stale reasoning)."""
    _, _, diffs = build_report(data)
    diffed_chains = {d["chain"] for d in diffs}
    assert {"Dabur New U", "Medanta"}.issubset(diffed_chains)


def test_no_real_nonzero_value_is_ever_disturbed(data):
    old_rows, new_rows, _ = build_report(data)
    for name in set(old_rows) | set(new_rows):
        old_r, new_r = old_rows.get(name, {}), new_rows.get(name, {})
        for k in set(old_r) | set(new_r):
            if k in ("name", "yoy"):
                continue
            ov, nv = old_r.get(k), new_r.get(k)
            if ov not in (None, 0) and nv not in (None, 0):
                assert ov == nv, f"{name}/{k}: real value changed {ov} -> {nv}"
