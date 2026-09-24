"""Shadow comparison for the primary_block()'s dim_rows() fix (Phase 2B-B,
item 1 -- docs/SOURCE_MISSINGNESS_LINEAGE.md's F14 remediation proposal).

Compares the OLD behavior (pivot_table(...).fillna(0), unconditional zero
for any chain/zone/brand missing a given FY) against the NEW behavior
(zero_fill=False: a missing chain/zone/brand-FY combination is published as
None/NOT_AVAILABLE, never a fabricated 0) -- on REAL data.

Caveat, stated plainly: this repo's actual pre-aggregated Primary workbook
(primary.xlsx, read by load_primary()/load_primary_v2()) is a gitignored
--src input, not present in this environment. This script instead
reconstructs an equivalent DataFrame from `detail_records` -- the real,
certified, article-level Primary source already inside dashboard/data.js
(FY/Month/Chain/Brand/Zone/Channel/NSV/MRP, per detail_records_real()) --
mapped onto exactly the column names/casing primary_block() expects
(chain/brand/zone/channel lowercase, "MRP value"). This is real production
data, not synthetic fixtures, but it is a DIFFERENT source file than the
one that actually produced the certified primary.by_chain block, so this
proves the FIX's *behavior* (which cells change, and that no real value is
disturbed) on real data -- it does not itself regenerate the certified
data.js. Regenerating data.js from the real primary.xlsx requires the
actual --src drop, which only the repo owner running --primary-only
locally has.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from canonical import facts
import build_dashboard_data as bdd


def _reconstruct_primary_df(data):
    """detail_records -> a DataFrame matching primary_block()'s expected
    schema (FY, Month, NSV, "MRP value", chain, brand, zone, channel)."""
    rows = facts.primary_fact_rows(data)
    df = pd.DataFrame(rows)
    df = df.rename(columns={
        "Chain": "chain", "Brand": "brand", "Zone": "zone", "Channel": "channel",
        "MRP": "MRP value",
    })
    df["NSV"] = pd.to_numeric(df["NSV"], errors="coerce").fillna(0.0)
    df["MRP value"] = pd.to_numeric(df["MRP value"], errors="coerce").fillna(0.0)
    return df


def _old_dim_rows(df, tags, keys_of, index_col, keep_blank=False, sort=True):
    """Exact replica of the PRE-FIX dim_rows() body (pivot_table(...).fillna(0)),
    kept here only for shadow comparison -- not used by the production pipeline."""
    def fy_get(series, t):
        return float(sum(series.get(k, 0) or 0 for k in keys_of[t]))

    pv = df.pivot_table(index=index_col, columns="FY", values="NSV", aggfunc="sum").fillna(0)
    rows = []
    for k in pv.index:
        if not k and not keep_blank:
            continue
        row = {"name": k}
        for t in tags:
            row[t.lower()] = bdd.r2(fy_get(pv.loc[k], t))
        rows.append(row)
    return rows


def build_report(data):
    """Returns (old_by_chain, new_by_chain, comparison_rows) where
    comparison_rows lists every (chain, fy) cell whose value differs
    between old and new, with a classification of why."""
    df = _reconstruct_primary_df(data)
    src_fys = [k for k in df["FY"].dropna().unique()]
    tag_of = {k: bdd._fylabel(k) for k in src_fys}
    _all_tags = sorted({t for t in tag_of.values() if t}, key=bdd.fy_start_year)
    # Match primary_block()'s own COVERAGE GATE exactly (build_dashboard_data.py
    # :712-724): the pre-aggregated Primary workbook this function is designed
    # for ends Mar'26, so it only ever publishes tags in PREAGG_FY_TAGS -- a
    # pre-existing, documented, unrelated-to-this-fix restriction. Because this
    # shadow script substitutes detail_records (which DOES have real FY27 rows)
    # for the unavailable raw workbook, skipping this gate would make FY27
    # spuriously "differ" between old/new for every chain -- not because of the
    # fillna(0) fix, but because of a shadow-script-only source mismatch. Both
    # the old and new replicas below must apply the same gate to isolate the
    # fillna(0)-vs-None question this comparison actually exists to answer.
    tags = [t for t in _all_tags if t in bdd.PREAGG_FY_TAGS]
    keys_of = {t: [k for k, tt in tag_of.items() if tt == t] for t in tags}

    old_rows = {r["name"]: r for r in _old_dim_rows(df, tags, keys_of, "chain")}

    _, primary_out = bdd.primary_block(df)
    new_rows = {r["name"]: r for r in primary_out["by_chain"]}

    all_names = sorted(set(old_rows) | set(new_rows))
    diffs = []
    for name in all_names:
        old_r = old_rows.get(name, {})
        new_r = new_rows.get(name, {})
        for t in tags:
            lo = t.lower()
            old_v = old_r.get(lo)
            new_v = new_r.get(lo)
            if old_v != new_v:
                classification = (
                    "MISSING_TO_NOT_AVAILABLE (fix working as intended)"
                    if (old_v == 0 and new_v is None)
                    else "UNEXPECTED_DIVERGENCE -- investigate"
                )
                diffs.append({
                    "chain": name, "fy": t, "old": old_v, "new": new_v,
                    "classification": classification,
                })
    return old_rows, new_rows, diffs


def main():
    data = facts.load_datajs()
    old_rows, new_rows, diffs = build_report(data)

    unexpected = [d for d in diffs if "UNEXPECTED" in d["classification"]]
    expected = [d for d in diffs if "UNEXPECTED" not in d["classification"]]

    print(f"Total chains compared: {len(set(old_rows) | set(new_rows))}")
    print(f"Total (chain, FY) cells differing: {len(diffs)}")
    print(f"  Expected (missing -> NOT_AVAILABLE): {len(expected)}")
    print(f"  UNEXPECTED divergence: {len(unexpected)}")
    print()
    print("Expected diffs (the fix's intended effect):")
    for d in expected:
        print(f"  {d['chain']!r}, {d['fy']}: {d['old']} -> {d['new']}")
    if unexpected:
        print()
        print("UNEXPECTED diffs (investigate before shipping):")
        for d in unexpected:
            print(f"  {d['chain']!r}, {d['fy']}: {d['old']} -> {d['new']}")

    # Conservation check: every real (non-fabricated) value must be IDENTICAL
    # between old and new -- the fix must only ever change a fabricated 0
    # into None, never touch a genuinely real number.
    real_value_mismatches = []
    for name in set(old_rows) | set(new_rows):
        old_r, new_r = old_rows.get(name, {}), new_rows.get(name, {})
        for k in set(old_r) | set(new_r):
            if k in ("name", "yoy"):
                continue
            ov, nv = old_r.get(k), new_r.get(k)
            if ov not in (None, 0) and nv not in (None, 0) and ov != nv:
                real_value_mismatches.append((name, k, ov, nv))
    print()
    print(f"Real-value mismatches (should be 0): {len(real_value_mismatches)}")
    for m in real_value_mismatches:
        print(" ", m)

    return 0 if not unexpected and not real_value_mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
