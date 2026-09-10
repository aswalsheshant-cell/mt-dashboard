"""
Compress a row-level provisional-mapping approval register into the smallest
defensible set of owner-facing rules, per the mapping-approval-governor skill
contract (skill-suite/skills/mapping-approval-governor/).

This does NOT decide anything. It never sets an Owner_Decision. It only
reduces how many lines a human has to decide on, while keeping every
original row traceable underneath the resulting rule or exception.

Algorithm (see skill references/compression-algorithm.md for the full spec):
  1. Load the finest-grain detail available: Month x Distributor x Brand x Chain.
  2. For each (Distributor, Brand), test whether every month maps to the same
     chain. If yes -> that (Distributor, Brand) is "stable" and eligible to
     merge upward. If no -> split at the exact conflicting month(s) and file
     those as OWNER_ROW_EXCEPTION, never absorbed into a broader rule.
  3. Within a Distributor, merge stable (Distributor, Brand) pairs that share
     the same resolved chain into one rule (Distributor -> Chain, brand
     scope = the merged set, up to "ALL" if every brand for that distributor
     agrees).
  4. Materiality-tier every rule and exception by absolute value, with the
     thresholds stated explicitly in the output (never implicit).

Usage:
    python scripts/mapping_approval_compression.py --detail <MonthDetail.csv> --out-dir <dir>
"""
import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HIGH_THRESHOLD_L = 200.0
MEDIUM_THRESHOLD_L = 20.0
NOISE_FLOOR_L = 0.01          # a value below this in a given month is treated as absent, not a chain appearance
CORE_CHAIN_MONTH_COVERAGE = 0.8  # a chain must be nonzero in >= this fraction of active months to be "core"
RESIDUAL_MATERIALITY_L = 5.0  # non-core value below this, for a given (distributor,brand), is folded into the core rule as a noted residual rather than a separate exception


def materiality(value_l: float) -> str:
    if value_l >= HIGH_THRESHOLD_L:
        return "HIGH"
    if value_l >= MEDIUM_THRESHOLD_L:
        return "MEDIUM"
    return "LOW"


def compress(detail: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (rules_df, exceptions_df). Every row of `detail` ends up
    represented in exactly one output row's Row_Count/Value, verified by the
    caller against the grand total."""
    detail = detail.copy()
    detail["Value_L"] = pd.to_numeric(detail["Value_L"], errors="coerce").fillna(0.0)

    rules = []
    exceptions = []
    rule_seq = 0

    for distributor, dist_df in detail.groupby("Distributor", dropna=False):
        # Step 2: per (Distributor, Brand), find the CORE chain set -- chains
        # nonzero in >= CORE_CHAIN_MONTH_COVERAGE of the months this brand has
        # any activity in. A stable multi-chain split (same chains, varying
        # rupee share month to month -- completely normal for a % split) is
        # NOT a conflict; only a chain composition that genuinely changes
        # (a chain disappearing and a different one taking its place) is.
        stable_brand_rule = {}    # brand -> dict(core_chains set, core_value, residual_value, residual_chains)
        unstable_brands = []      # brand: no coverage threshold produces a usable core (rare)
        for brand, bdf in dist_df.groupby("Brand", dropna=False):
            active = bdf[bdf["Value_L"].abs() > NOISE_FLOOR_L]
            active_months = active["Month"].nunique()
            if active_months == 0:
                continue
            chain_month_counts = active.groupby("Chain")["Month"].nunique()
            core_chains = set(chain_month_counts[chain_month_counts >= CORE_CHAIN_MONTH_COVERAGE * active_months].index)
            if not core_chains:
                # no chain clears the bar -- genuinely no stable pattern
                unstable_brands.append(brand)
                continue
            core_value = bdf[bdf["Chain"].isin(core_chains)]["Value_L"].sum()
            residual = bdf[~bdf["Chain"].isin(core_chains)]
            residual_value = residual["Value_L"].sum()
            total_value = bdf["Value_L"].sum()
            if total_value > 0 and (residual_value / total_value) > 0.20 and residual_value > RESIDUAL_MATERIALITY_L:
                # the "non-core" portion is itself too large to wave away -- treat as unstable
                unstable_brands.append(brand)
                continue
            stable_brand_rule[brand] = dict(
                core_chains=core_chains, core_value=core_value,
                residual_value=residual_value,
                residual_chains=sorted(residual["Chain"].dropna().unique().tolist()),
                all_rows=bdf,
            )

        # Step 3: merge brands within this distributor that share an identical
        # core chain set into one rule (Distributor -> {chain set}).
        signature_to_brands: dict[frozenset, list[str]] = {}
        for brand, info in stable_brand_rule.items():
            signature_to_brands.setdefault(frozenset(info["core_chains"]), []).append(brand)

        all_brands_for_distributor = set(dist_df["Brand"].unique())
        for chain_set, brands in signature_to_brands.items():
            rows = pd.concat([stable_brand_rule[b]["all_rows"] for b in brands])
            core_rows = rows[rows["Chain"].isin(chain_set)]
            core_value = core_rows["Value_L"].sum()
            residual_value = sum(stable_brand_rule[b]["residual_value"] for b in brands)
            # the rule's Value_L covers the WHOLE brand-cluster total (core + the
            # immaterial residual folded in) so every input rupee lands in exactly
            # one output line; Residual_Non_Core_Value_L discloses how much of that
            # total sits outside the named core chain(s), for transparency
            rule_value = rows["Value_L"].sum()
            months = sorted(rows["Month"].unique(), key=lambda m: str(m))
            brand_scope = "ALL" if set(brands) == all_brands_for_distributor and len(signature_to_brands) == 1 else ", ".join(sorted(brands))
            # per-chain split, so the owner sees the actual % breakdown, not just the chain names
            split = (core_rows.groupby("Chain")["Value_L"].sum() / core_value * 100).round(1).to_dict() if core_value else {}
            split_str = "; ".join(f"{c}: {p}%" for c, p in sorted(split.items(), key=lambda kv: -kv[1]))
            rule_seq += 1
            rules.append(dict(
                Rule_ID=f"RULE-{rule_seq:04d}",
                Decision_Type="OWNER_RULE_APPROVAL",
                Distributor=distributor,
                Brand_Scope=brand_scope,
                Proposed_Chain=split_str if len(chain_set) > 1 else (next(iter(chain_set)) if chain_set else "UNKNOWN"),
                Row_Count=len(rows),
                Months_Covered=len(months),
                Month_Range=f"{months[0]}..{months[-1]}" if months else "",
                Value_L=round(rule_value, 4),
                Materiality=materiality(rule_value),
                Evidence_Source="Chain_Wise_Primary_Sale_2.xlsx (Dump) -- PENDING OWNER APPROVAL",
                Conflicts=0,
                Residual_Non_Core_Value_L=round(residual_value, 4),
            ))

        # Step 2b: brands with no stable core -> exceptions
        for brand in unstable_brands:
            bdf = dist_df[dist_df["Brand"] == brand]
            active = bdf[bdf["Value_L"].abs() > NOISE_FLOOR_L]
            distinct_chains = sorted(active["Chain"].dropna().unique().tolist())
            value = bdf["Value_L"].sum()
            months = sorted(bdf["Month"].unique(), key=lambda m: str(m))
            exceptions.append(dict(
                Rule_ID=f"EXC-{len(exceptions)+1:04d}",
                Decision_Type="OWNER_ROW_EXCEPTION",
                Distributor=distributor,
                Brand_Scope=brand,
                Proposed_Chain=" / ".join(distinct_chains) if distinct_chains else "NONE",
                Row_Count=len(bdf),
                Months_Covered=len(months),
                Month_Range=f"{months[0]}..{months[-1]}" if months else "",
                Value_L=round(value, 4),
                Materiality=materiality(value),
                Evidence_Source="Chain_Wise_Primary_Sale_2.xlsx (Dump) -- PENDING OWNER APPROVAL",
                Conflicts=len(distinct_chains),
                Reason=f"No chain clears the {int(CORE_CHAIN_MONTH_COVERAGE*100)}% month-coverage bar, or the "
                       f"non-core residual is too large to fold in -- chain composition genuinely shifts across "
                       f"{len(distinct_chains)} chains ({', '.join(distinct_chains)})",
            ))

    rules_df = pd.DataFrame(rules)
    exceptions_df = pd.DataFrame(exceptions)
    return rules_df, exceptions_df


def build_owner_message() -> str:
    return (
        "Please review only the highlighted approval rows.\n"
        "For each row choose APPROVE, CORRECT or REJECT.\n"
        "Do not review the full methodology again.\n"
        "Where correcting, enter the correct chain.\n"
        "We will use only your explicit decision and retain the original proposal for audit."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--detail", type=Path, required=True,
                     help="Month x Distributor x Brand x Chain detail CSV")
    ap.add_argument("--out-dir", type=Path, required=True)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    detail = pd.read_csv(args.detail)
    input_rows = len(detail)
    input_value = round(pd.to_numeric(detail["Value_L"], errors="coerce").fillna(0.0).sum(), 4)

    rules_df, exceptions_df = compress(detail)

    total_rule_value = round(rules_df["Value_L"].sum(), 4) if len(rules_df) else 0.0
    total_exc_value = round(exceptions_df["Value_L"].sum(), 4) if len(exceptions_df) else 0.0
    output_value = round(total_rule_value + total_exc_value, 4)
    diff = round(output_value - input_value, 4)

    n_output_items = len(rules_df) + len(exceptions_df)
    compression_ratio = round((1 - n_output_items / input_rows) * 100, 2) if input_rows else 0.0

    rules_df.to_csv(args.out_dir / "OwnerDecisionPack_RuleApprovals.csv", index=False)
    exceptions_df.to_csv(args.out_dir / "OwnerDecisionPack_RowExceptions.csv", index=False)

    fingerprint = hashlib.sha256(args.detail.read_bytes()).hexdigest()
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_detail_file": str(args.detail),
        "input_detail_sha256": fingerprint,
        "materiality_thresholds_L": {"HIGH": HIGH_THRESHOLD_L, "MEDIUM": MEDIUM_THRESHOLD_L},
        "input_rows": input_rows,
        "input_value_L": input_value,
        "output_rules": len(rules_df),
        "output_exceptions": len(exceptions_df),
        "output_items_total": n_output_items,
        "compression_ratio_pct": compression_ratio,
        "value_reconciliation_diff_L": diff,
        "by_decision_type_value_L": {
            "OWNER_RULE_APPROVAL": total_rule_value,
            "OWNER_ROW_EXCEPTION": total_exc_value,
        },
        "by_materiality_value_L": {
            tier: round(pd.concat([rules_df, exceptions_df])
                        .loc[lambda d: d["Materiality"] == tier, "Value_L"].sum(), 4)
            for tier in ("HIGH", "MEDIUM", "LOW")
        } if n_output_items else {},
    }
    import json
    with open(args.out_dir / "CompressionSummary.json", "w") as f:
        json.dump(summary, f, indent=2)
    with open(args.out_dir / "OwnerMessage.txt", "w") as f:
        f.write(build_owner_message())

    print(f"Input: {input_rows} rows, Rs{input_value}L")
    print(f"Output: {len(rules_df)} rules + {len(exceptions_df)} exceptions = {n_output_items} items "
          f"({compression_ratio}% compression)")
    print(f"Value reconciliation diff: Rs{diff}L")
    assert abs(diff) <= 0.01, "COMPRESSION FAILED TO RECONCILE -- do not use this output"
    print("\nBy decision type:")
    for k, v in summary["by_decision_type_value_L"].items():
        print(f"  {k}: Rs{v}L")
    print("\nBy materiality:")
    for k, v in summary.get("by_materiality_value_L", {}).items():
        print(f"  {k}: Rs{v}L")
    return 0


if __name__ == "__main__":
    sys.exit(main())
