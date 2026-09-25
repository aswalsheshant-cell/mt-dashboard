#!/usr/bin/env python3
"""
Promo Depth vs. Offtake Uplift Correlation Engine

Models the commercial impact of promotional discount depth on secondary sales (offtake).
Calculates price elasticity of demand by discount tier and identifies ROI-optimal ranges.

No external dependencies required (numpy optional for advanced statistics).
"""

import json
import sys
from collections import defaultdict
from statistics import median, stdev


class CorrelationAnalyzer:
    """Compute elasticity metrics between promo depth and offtake volume."""

    def __init__(self, tolerance=1e-6):
        self.tolerance = tolerance

    def compute_baseline_offtake(self, offtake_data, chain_name, window=3):
        """
        Compute rolling N-month median offtake per chain (excludes spike months).

        Args:
            offtake_data: dict of monthly offtake metrics
            chain_name: string chain identifier
            window: rolling window size (default 3 months)

        Returns:
            dict: {month: baseline_value} for chain
        """
        if not offtake_data or chain_name not in offtake_data.get('by_chain_detail', {}):
            return {}

        chain_detail = offtake_data['by_chain_detail'][chain_name]
        monthly_volumes = chain_detail.get('monthly', {})

        if not monthly_volumes:
            return {}

        baselines = {}
        sorted_months = sorted(monthly_volumes.keys())

        for i, month in enumerate(sorted_months):
            # Use window of months around current month (excluding current for prediction)
            window_months = []
            for j in range(max(0, i - window), i):
                if j < len(sorted_months):
                    vol = monthly_volumes[sorted_months[j]]
                    if isinstance(vol, (int, float)) and vol > 0:
                        window_months.append(vol)

            if window_months:
                baselines[month] = median(window_months)

        return baselines

    def segment_by_discount_tier(self, depth_percent):
        """
        Classify discount depth into tier.

        Args:
            depth_percent: float discount depth (0-100)

        Returns:
            str: 'tier_1', 'tier_2', 'tier_3', or 'unknown'
        """
        if depth_percent < 0 or depth_percent > 100:
            return 'unknown'
        elif depth_percent < 30:
            return 'tier_0'  # Low depth, minimal promo
        elif depth_percent < 50:
            return 'tier_1'  # 30–50%
        elif depth_percent < 70:
            return 'tier_2'  # 50–70%
        else:
            return 'tier_3'  # 70%+

    def calculate_elasticity(self, promo_data, offtake_data):
        """
        Compute price elasticity coefficient: lift_pct / discount_pct.

        Args:
            promo_data: dict with promo metrics by chain/month
            offtake_data: dict with offtake metrics by chain/month

        Returns:
            dict: {chain: {tier: {metrics}}}
        """
        result = defaultdict(lambda: defaultdict(lambda: {
            'avg_lift': 0,
            'std_dev': 0,
            'min_lift': 0,
            'max_lift': 0,
            'count': 0,
            'elasticity': 0
        }))

        chains_in_promo = {c['name']: c for c in promo_data.get('by_chain', [])}

        for chain_name, chain_promo in chains_in_promo.items():
            baselines = self.compute_baseline_offtake(offtake_data, chain_name)

            if not baselines:
                continue

            # Group by tier
            tiers = defaultdict(list)
            for month, discount_depth in chain_promo.get('monthly_depth', {}).items():
                if month not in baselines:
                    continue

                baseline = baselines[month]
                if baseline <= 0:
                    continue

                # Get actual offtake for this month
                offtake_actual = None
                if 'by_chain_detail' in offtake_data:
                    chain_detail = offtake_data['by_chain_detail'].get(chain_name, {})
                    monthly = chain_detail.get('monthly', {})
                    offtake_actual = monthly.get(month)

                if offtake_actual is None or offtake_actual <= 0:
                    continue

                # Calculate uplift
                uplift_pct = ((offtake_actual - baseline) / baseline) * 100

                # Classify and aggregate
                tier = self.segment_by_discount_tier(discount_depth)
                if tier != 'unknown':
                    tiers[tier].append({
                        'lift': uplift_pct,
                        'discount': discount_depth,
                        'baseline': baseline,
                        'actual': offtake_actual,
                        'month': month
                    })

            # Aggregate by tier
            for tier, instances in tiers.items():
                if instances:
                    lifts = [i['lift'] for i in instances]
                    discounts = [i['discount'] for i in instances]

                    avg_lift = sum(lifts) / len(lifts)
                    avg_discount = sum(discounts) / len(discounts)

                    # Calculate elasticity (lift % per 1% discount)
                    elasticity = avg_lift / avg_discount if avg_discount > 0 else 0

                    # Standard deviation
                    std_dev = stdev(lifts) if len(lifts) > 1 else 0

                    result[chain_name][tier] = {
                        'avg_lift': round(avg_lift, 2),
                        'std_dev': round(std_dev, 2),
                        'min_lift': round(min(lifts), 2),
                        'max_lift': round(max(lifts), 2),
                        'count': len(instances),
                        'elasticity': round(elasticity, 3),
                        'avg_discount': round(avg_discount, 2)
                    }

        return dict(result)

    def detect_anomalies(self, promo_data, offtake_data, elasticity_data):
        """
        Flag anomalous patterns: dilution risk, exceptional uplift.

        Args:
            promo_data: dict with promo metrics
            offtake_data: dict with offtake metrics
            elasticity_data: computed elasticity from calculate_elasticity()

        Returns:
            list: [flags with severity, chain, month, metrics]
        """
        flags = []

        chains_in_promo = {c['name']: c for c in promo_data.get('by_chain', [])}

        for chain_name, chain_promo in chains_in_promo.items():
            baselines = self.compute_baseline_offtake(offtake_data, chain_name)

            for month, discount_depth in chain_promo.get('monthly_depth', {}).items():
                if month not in baselines:
                    continue

                baseline = baselines[month]
                if baseline <= 0:
                    continue

                # Get actual offtake
                offtake_actual = None
                if 'by_chain_detail' in offtake_data:
                    chain_detail = offtake_data['by_chain_detail'].get(chain_name, {})
                    monthly = chain_detail.get('monthly', {})
                    offtake_actual = monthly.get(month)

                if offtake_actual is None or offtake_actual <= 0:
                    continue

                uplift_pct = ((offtake_actual - baseline) / baseline) * 100

                # Dilution risk: high discount with low/negative uplift
                if discount_depth > 70 and uplift_pct < 15:
                    flags.append({
                        'chain': chain_name,
                        'month': month,
                        'discount_depth': round(discount_depth, 1),
                        'offtake_lift': round(uplift_pct, 1),
                        'baseline': round(baseline, 0),
                        'actual': round(offtake_actual, 0),
                        'flag': 'dilution_risk',
                        'severity': 'high' if uplift_pct < 5 else 'medium'
                    })

                # Exceptional uplift: very high lift
                if uplift_pct > 50:
                    flags.append({
                        'chain': chain_name,
                        'month': month,
                        'discount_depth': round(discount_depth, 1),
                        'offtake_lift': round(uplift_pct, 1),
                        'baseline': round(baseline, 0),
                        'actual': round(offtake_actual, 0),
                        'flag': 'exceptional_uplift',
                        'severity': 'high'
                    })

                # Elasticity anomaly: over-elastic (>1.0) or inelastic (<0.1) tier
                tier = self.segment_by_discount_tier(discount_depth)
                if chain_name in elasticity_data and tier in elasticity_data[chain_name]:
                    elasticity = elasticity_data[chain_name][tier].get('elasticity', 0)
                    if elasticity > 1.0:
                        flags.append({
                            'chain': chain_name,
                            'month': month,
                            'discount_depth': round(discount_depth, 1),
                            'elasticity': round(elasticity, 3),
                            'flag': 'super_elastic',
                            'severity': 'medium',
                            'note': 'Uplift > 1x discount increase (market saturation?)'
                        })

        return flags

    def summarize_insights(self, elasticity_data):
        """
        Generate summary insights for optimal discount range.

        Args:
            elasticity_data: computed elasticity metrics

        Returns:
            dict: {optimal_tier, highest_roi_chains, dilution_risk_chains}
        """
        tier_elasticities = defaultdict(list)

        for chain, tiers in elasticity_data.items():
            for tier, metrics in tiers.items():
                if metrics.get('count', 0) > 0:
                    tier_elasticities[tier].append({
                        'chain': chain,
                        'elasticity': metrics['elasticity'],
                        'avg_lift': metrics['avg_lift']
                    })

        # Find highest-ROI tier (best elasticity)
        best_tier = None
        best_elasticity = -1
        for tier, instances in tier_elasticities.items():
            if instances:
                avg_elast = sum(i['elasticity'] for i in instances) / len(instances)
                if avg_elast > best_elasticity:
                    best_elasticity = avg_elast
                    best_tier = tier

        # High-ROI chains (elasticity > 0.3)
        high_roi = []
        dilution_risk = []
        for chain, tiers in elasticity_data.items():
            for tier, metrics in tiers.items():
                if metrics.get('elasticity', 0) > 0.3:
                    high_roi.append(chain)
                elif tier in ['tier_2', 'tier_3'] and metrics.get('elasticity', 0) < 0.1:
                    dilution_risk.append(chain)

        return {
            'highest_roi_tier': best_tier or 'tier_2',
            'avg_elasticity_by_tier': {
                tier: round(sum(i['elasticity'] for i in instances) / len(instances), 3)
                for tier, instances in tier_elasticities.items()
                if instances
            },
            'high_roi_chains': list(set(high_roi)),
            'dilution_risk_chains': list(set(dilution_risk)),
            'optimal_depth_range': '45–55%' if best_tier == 'tier_2' else '30–50%'
        }


def generate_correlations_block(data_master_path_or_dict):
    """
    Compute correlations from data_master.json or dict.

    Extracts monthly promo data and correlates with available offtake metrics.
    Monthly offtake data integration pending; uses FY-level aggregates as baseline.

    Args:
        data_master_path_or_dict: path to data_master.json or dict of loaded data

    Returns:
        dict: {correlations: {by_chain, anomaly_flags, summary}}
    """
    # Load data from path or use dict directly
    if isinstance(data_master_path_or_dict, dict):
        data = data_master_path_or_dict
    else:
        try:
            with open(data_master_path_or_dict, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"ERROR: Could not load data_master.json: {e}")
            return {}

    promo = data.get('promo', {})
    by_chain_offtake = data.get('by_chain_offtake', {})

    if not promo:
        print("WARNING: Missing promo data")
        return {}

    # Prepare offtake data structure for analysis
    # Note: by_chain_offtake is organized by FY, extract monthly data from promo
    monthly_promo = promo.get('monthly', {})

    if not monthly_promo:
        print("WARNING: No monthly promo data available for correlation analysis")
        return {}

    # Build correlation summary from monthly promo data
    analyzer = CorrelationAnalyzer()
    by_chain_summary = defaultdict(lambda: {'tiers': defaultdict(list)})

    # Extract monthly chain data
    for month, month_data in monthly_promo.items():
        for chain_entry in month_data.get('by_chain', []):
            chain_name = chain_entry.get('name')
            discount_depth = chain_entry.get('avg_offer_pct')
            skus = chain_entry.get('skus', 0)

            if chain_name and discount_depth is not None and discount_depth > 0:
                tier = analyzer.segment_by_discount_tier(discount_depth)
                by_chain_summary[chain_name]['tiers'][tier].append({
                    'month': month,
                    'discount': discount_depth,
                    'skus': skus,
                    'brands': chain_entry.get('brands', 0)
                })

    # Compute elasticity tiers from collected data
    elasticity = {}
    for chain_name, data_summary in by_chain_summary.items():
        elasticity[chain_name] = {}
        for tier, instances in data_summary['tiers'].items():
            if instances:
                discounts = [i['discount'] for i in instances]
                avg_discount = sum(discounts) / len(discounts)

                # F15 (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md follow-up
                # sweep, 2026-09-25): this used to hardcode avg_lift=0 (a
                # placeholder presented as a real observation) and compute
                # 'elasticity' as avg_discount/100 -- not lift/discount, the
                # actual elasticity formula this file's own docstring and
                # CorrelationAnalyzer.calculate_elasticity() define, just
                # above, unused here for lack of a monthly offtake-by-chain
                # source to compute a real lift against. avg_discount/count
                # are real, observed values (kept); lift/elasticity/roc_index
                # are not computable without that source, so they stay None,
                # never a fabricated number that could reach an executive
                # brief looking legitimate.
                elasticity[chain_name][tier] = {
                    'avg_discount': round(avg_discount, 2),
                    'count': len(instances),
                    'elasticity': None,
                    'avg_lift': None,
                    'std_dev': None,
                    'min_lift': None,
                    'max_lift': None,
                    'status': 'NOT_AVAILABLE_UNTIL_VALIDATED_LIFT_SOURCE'
                }

    # Detect anomalies from available data
    anomalies = []
    for chain_name, data_summary in by_chain_summary.items():
        for tier, instances in data_summary['tiers'].items():
            for instance in instances:
                # Flag excessively deep discounts
                if instance['discount'] > 70:
                    anomalies.append({
                        'chain': chain_name,
                        'month': instance['month'],
                        'discount_depth': round(instance['discount'], 1),
                        'flag': 'excessive_discount',
                        'severity': 'medium',
                        'note': 'Discount depth >70% (monitor ROI closely)'
                    })

    # F15: highest_roi_tier/optimal_depth_range/avg_discount_tier_N were
    # hardcoded literals (never actually derived from `elasticity` above) --
    # the same fabrication pattern as avg_lift, just one level up. None of
    # these are computable without a real, validated elasticity source.
    summary = {
        'highest_roi_tier': None,
        'optimal_depth_range': None,
        'avg_discount_tier_1': None,
        'avg_discount_tier_2': None,
        'avg_discount_tier_3': None,
        'total_chains_analyzed': len(elasticity),
        'data_availability': ('Monthly promo discount depth available (real); monthly '
                               'offtake-by-chain data required to compute real lift/'
                               'elasticity does not exist yet'),
        'status': 'NOT_AVAILABLE_UNTIL_VALIDATED_LIFT_SOURCE',
        'methodology_validated': False,
        'reason': ('Elasticity/lift figures require monthly offtake matched to promo '
                   'periods (CorrelationAnalyzer.calculate_elasticity(), unused here '
                   'for lack of that source) plus a reviewed methodology sign-off -- '
                   'neither exists yet. Do not use avg_lift/elasticity/roc_index/'
                   'highest_roi_tier/optimal_depth_range until methodology_validated '
                   'is true.')
    }

    # Build output structure. roc_index ("return on chain") is derived from
    # elasticity, which has no real source yet -- stays None, not a sum over
    # None values (which would raise) or a silent 0 (which would look real).
    by_chain = []
    for chain_name, tiers in elasticity.items():
        by_chain.append({
            'name': chain_name,
            'elasticity_tiers': dict(tiers),
            'roc_index': None
        })

    return {
        'correlations': {
            'by_chain': by_chain,
            'anomaly_flags': anomalies,
            'summary': summary,
            'version': '1.0',
            'generated_at': None,  # Will be set by sync script
            'status': 'NOT_AVAILABLE_UNTIL_VALIDATED_LIFT_SOURCE',
            'methodology_validated': False
        }
    }


def main():
    """CLI interface for correlation analysis."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Compute promo depth vs. offtake uplift correlations'
    )
    parser.add_argument(
        '--data-master',
        type=str,
        default='data_master.json',
        help='Path to data_master.json'
    )
    parser.add_argument(
        '--output-json',
        type=str,
        help='Output correlations to JSON file (optional)'
    )
    parser.add_argument(
        '--summary-only',
        action='store_true',
        help='Print summary insights only'
    )

    args = parser.parse_args()

    correlations = generate_correlations_block(args.data_master)

    if not correlations:
        print("FAILED: Could not generate correlations")
        return 1

    if args.summary_only:
        summary = correlations['correlations']['summary']
        print("=" * 60)
        print("PROMO ELASTICITY SUMMARY")
        print("=" * 60)
        print(f"Optimal Tier: {summary.get('highest_roi_tier')}")
        print(f"Optimal Depth Range: {summary.get('optimal_depth_range')}")
        print(f"High-ROI Chains: {len(summary.get('high_roi_chains', []))}")
        print(f"Dilution Risk Chains: {len(summary.get('dilution_risk_chains', []))}")
        print(f"Anomaly Flags: {len(correlations['correlations']['anomaly_flags'])}")
    else:
        print(json.dumps(correlations, indent=2))

    if args.output_json:
        with open(args.output_json, 'w') as f:
            json.dump(correlations, f, indent=2)
        print(f"✓ Correlations saved to {args.output_json}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
