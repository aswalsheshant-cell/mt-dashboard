#!/usr/bin/env python3
"""
NPI Performance Facts & Aggregation — Derive article-level sales metrics linked to NPI articles.

For each NPI article × month × chain × zone, computes:
  - Distribution achievement (% target stores stocking)
  - Sales productivity (₹ NSV per stocking store)
  - Offtake velocity (units/month vs lifecycle ramp expectation)
  - Availability metrics (OOS % if available from source)
  - Conversion gap (primary vs offtake ratio)

Grain: article × month × chain (with optional zone/store drill-down).
Built from:
  - npi_master: article metadata (targets, launch dates, comparable articles)
  - detail_meta.fyx_primary: article-level primary sales by month/chain
  - offtake store×article: article-level sell-out by store/chain
  - universe: store footprint by chain/zone
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
import math
import pandas as pd


class NPIPerformanceCalculator:
    """Calculate article-level sales performance facts for NPI articles."""

    def __init__(self,
                 npi_master: dict,
                 detail_meta: dict | None = None,
                 universe_df: pd.DataFrame | None = None,
                 reference_date: str | None = None):
        """
        Args:
            npi_master: Dict from NPIMasterLoader.to_dict() with npi_articles list.
            detail_meta: Dict with fyx_primary block (article-level sales by month/chain).
            universe_df: Store universe DataFrame with Chain, Zone, Store columns.
            reference_date: Reference date for age/ramp calculation (default: today).
        """
        self.npi_master = npi_master
        self.detail_meta = detail_meta or {}
        self.universe_df = universe_df
        self.reference_date = reference_date or datetime.now().date().isoformat()

        # Build lookup: article_id -> npi_article
        self.npi_by_article_id = {}
        for article in npi_master.get("npi_articles", []):
            if article.get("npi_flag"):
                self.npi_by_article_id[article["article_id"]] = article

        # Build store counts by chain/zone from universe
        self.stores_by_chain_zone = {}
        self.stores_by_chain = {}
        if universe_df is not None:
            for (chain, zone), group in universe_df.groupby(["Chain Name", "Zone"]):
                self.stores_by_chain_zone[(chain, zone)] = len(group)
            for chain, group in universe_df.groupby("Chain Name"):
                self.stores_by_chain[chain] = len(group)

    def derive_performance_facts(self,
                                  article_id: str,
                                  article_name: str,
                                  chain: str,
                                  month_label: str,
                                  primary_nsv_lakhs: float | None,
                                  offtake_units: int | None = None,
                                  stocking_stores: int | None = None) -> dict:
        """
        Derive NPI performance fact for one article × month × chain combination.

        Args:
            article_id: Article ID matching npi_master
            article_name: Display name
            chain: Chain name
            month_label: Month in 'Mon-YY' format (e.g. 'Jun-26')
            primary_nsv_lakhs: Primary sales in ₹ Lakh
            offtake_units: Offtake volume in units
            stocking_stores: Number of stores stocking article

        Returns:
            {
                "article_id": "AQ_FW_50ML",
                "article_name": "Aqualogica Face Wash 50ml",
                "chain": "Reliance",
                "month_label": "Jun-26",
                "launch_age_months": 3,
                "maturity_status": "SCALE",
                "target_distribution_pct": 80,
                "actual_distribution_stores": 45,
                "total_universe_stores": 50,
                "distribution_achievement_pct": 90.0,
                "expected_ramp_pct": 0.45,
                "primary_nsv_lakhs": 12.5,
                "offtake_units": 8500,
                "per_store_productivity_nsv": 0.278,
                "conversion_gap_pct": 2.5,
                "status": "GREEN" / "YELLOW" / "RED"
            }
        """
        fact = {
            "article_id": article_id,
            "article_name": article_name,
            "chain": chain,
            "month_label": month_label,
        }

        # Look up NPI article metadata
        npi_article = self.npi_by_article_id.get(article_id)
        if not npi_article:
            fact["status"] = "ARTICLE_NOT_IN_NPI"
            return fact

        # Add lifecycle information
        fact["launch_date"] = npi_article.get("launch_date")
        fact["launch_age_months"] = npi_article.get("launch_age_months")
        fact["maturity_status"] = npi_article.get("maturity_status")
        fact["expected_ramp_pct"] = npi_article.get("expected_ramp_pct")

        # Distribution target and achievement
        target_dist_pct = npi_article.get("target_distribution_pct") or 80
        target_chains = npi_article.get("target_chain") or []

        fact["target_distribution_pct"] = target_dist_pct

        # If chain is in target list, calculate distribution achievement
        is_target_chain = chain in target_chains if target_chains else True
        if is_target_chain and stocking_stores is not None:
            total_stores = self.stores_by_chain.get(chain)
            if total_stores and total_stores > 0:
                actual_dist_pct = 100 * stocking_stores / total_stores
                fact["actual_distribution_stores"] = stocking_stores
                fact["total_universe_stores"] = total_stores
                fact["distribution_achievement_pct"] = round(actual_dist_pct, 1)
            else:
                fact["status"] = "CHAIN_NOT_IN_UNIVERSE"
                return fact
        else:
            fact["actual_distribution_stores"] = None
            fact["total_universe_stores"] = None
            fact["distribution_achievement_pct"] = None

        # Sales metrics
        fact["primary_nsv_lakhs"] = round(primary_nsv_lakhs, 2) if primary_nsv_lakhs else None
        fact["offtake_units"] = offtake_units

        # Per-store productivity
        if primary_nsv_lakhs and stocking_stores and stocking_stores > 0:
            per_store_nsv = primary_nsv_lakhs / stocking_stores
            fact["per_store_productivity_nsv"] = round(per_store_nsv, 3)
        else:
            fact["per_store_productivity_nsv"] = None

        # Conversion gap (primary NSV vs offtake NSV proxy)
        # Placeholder: would need offtake value in ₹ for proper calculation
        # For now, mark as pending if both metrics available
        if primary_nsv_lakhs and offtake_units:
            fact["conversion_gap_pct"] = None  # Requires offtake pricing data
        else:
            fact["conversion_gap_pct"] = None

        # Performance status (GREEN/YELLOW/RED based on distribution achievement)
        if fact["distribution_achievement_pct"] is not None:
            dist_ach = fact["distribution_achievement_pct"]
            target = target_dist_pct
            variance = abs(dist_ach - target)

            if variance <= 4:
                fact["status"] = "GREEN"
            elif variance <= 10:
                fact["status"] = "YELLOW"
            else:
                fact["status"] = "RED"
        else:
            fact["status"] = "INSUFFICIENT_DATA"

        return fact

    def aggregate_by_article_month_chain(self,
                                          performance_facts: list[dict]) -> dict:
        """
        Aggregate performance facts into a pivot structure:
        npi_performance[article_id][month][chain] = fact

        Args:
            performance_facts: List of facts from derive_performance_facts()

        Returns:
            {
                "AQ_FW_50ML": {
                    "2026-06": {  # Month key
                        "Reliance": {...fact...},
                        "DMart": {...fact...}
                    },
                    ...
                },
                ...
            }
        """
        pivot = {}
        for fact in performance_facts:
            article_id = fact.get("article_id")
            month_label = fact.get("month_label")

            # Convert month label to month key (e.g., 'Jun-26' -> '2026-06')
            # For now, use month_label as-is
            month_key = month_label

            if article_id not in pivot:
                pivot[article_id] = {}
            if month_key not in pivot[article_id]:
                pivot[article_id][month_key] = {}

            chain = fact.get("chain")
            pivot[article_id][month_key][chain] = fact

        return pivot

    def compute_article_performance_summary(self, article_id: str) -> dict:
        """
        Compute summary metrics for an NPI article across all chains/months.

        Returns:
            {
                "article_id": "AQ_FW_50ML",
                "article_name": "Aqualogica Face Wash 50ml",
                "status_distribution": {
                    "GREEN": 5,
                    "YELLOW": 2,
                    "RED": 1,
                    "INSUFFICIENT_DATA": 0
                },
                "avg_distribution_achievement_pct": 85.2,
                "avg_per_store_productivity": 0.312,
                "n_chain_months_tracked": 8
            }
        """
        npi_article = self.npi_by_article_id.get(article_id)
        if not npi_article:
            return {"article_id": article_id, "error": "Article not in NPI master"}

        summary = {
            "article_id": article_id,
            "article_name": npi_article.get("article_name"),
            "status_distribution": {
                "GREEN": 0,
                "YELLOW": 0,
                "RED": 0,
                "INSUFFICIENT_DATA": 0,
            },
            "dist_achievements": [],
            "per_store_productivities": [],
        }

        # Placeholder: would be populated from performance_facts pivot
        summary["n_chain_months_tracked"] = 0
        summary["avg_distribution_achievement_pct"] = None
        summary["avg_per_store_productivity"] = None

        return summary


def build_npi_performance_block(npi_master: dict,
                                 detail_meta: dict | None = None,
                                 primary_sales: pd.DataFrame | None = None,
                                 offtake_sales: pd.DataFrame | None = None,
                                 universe_df: pd.DataFrame | None = None,
                                 reference_date: str | None = None) -> dict:
    """
    Build npi_performance block for data.js.

    Args:
        npi_master: Enriched NPI master dict
        detail_meta: Unused (kept for backward compat)
        primary_sales: Article-level primary sales DataFrame (from load_article_primary_sales)
        offtake_sales: Article-level offtake sales DataFrame (from load_article_offtake_sales)
        universe_df: Store universe DataFrame (for distribution % calc)
        reference_date: Reference date for lifecycle (default: today)

    Returns:
        {
            "npi_performance": {
                "n_facts": 150,
                "articles": [...],
                "by_article": {
                    "AQ_FW_50ML": {
                        "article_name": "...",
                        "by_month_chain": {...}
                    },
                    ...
                }
            }
        }
    """
    # Import loaders here to avoid circular dependency
    from npi_sales_loaders import compute_npi_performance_facts

    calc = NPIPerformanceCalculator(npi_master, detail_meta, universe_df, reference_date)

    # Compute performance facts from sales data
    if primary_sales is not None or offtake_sales is not None:
        primary_sales = primary_sales if primary_sales is not None else pd.DataFrame()
        offtake_sales = offtake_sales if offtake_sales is not None else pd.DataFrame()

        performance_facts = compute_npi_performance_facts(
            primary_sales=primary_sales,
            offtake_sales=offtake_sales,
            npi_master=npi_master,
            universe_df=universe_df,
            reference_date=reference_date
        )
    else:
        # No sales data provided: return empty structure
        performance_facts = []

    # Aggregate into pivot structure
    pivot = calc.aggregate_by_article_month_chain(performance_facts)

    articles_list = npi_master.get("npi_articles", [])
    n_npi = len([a for a in articles_list if a.get("npi_flag")])

    block = {
        "npi_performance": {
            "n_facts": len(performance_facts),
            "n_npi_articles": n_npi,
            "reference_date": reference_date or datetime.now().date().isoformat(),
            "by_article": pivot,
            "load_status": "ok" if len(performance_facts) > 0 or n_npi == 0 else "no_sales_data",
            "notes": {
                "grain": "article × month × chain",
                "metrics": [
                    "distribution_achievement_pct",
                    "per_store_productivity_nsv",
                    "expected_ramp_pct",
                    "maturity_status"
                ],
                "status_mapping": {
                    "GREEN": "within 4% of distribution target",
                    "YELLOW": "5–10% variance from target",
                    "RED": ">10% variance from target",
                    "INSUFFICIENT_DATA": "sales or distribution data missing"
                }
            }
        }
    }

    return block


if __name__ == "__main__":
    import json, sys

    # Example: create a performance fact for a single article
    # (Demonstrate the API; real usage loads from sales data)
    npi_master_example = {
        "npi_articles": [
            {
                "article_id": "AQ_FW_50ML",
                "article_name": "Aqualogica Face Wash 50ml",
                "launch_date": "2025-06-15",
                "launch_age_months": 3,
                "maturity_status": "SCALE",
                "expected_ramp_pct": 0.45,
                "target_distribution_pct": 80,
                "target_chain": ["Reliance", "DMart"],
                "npi_flag": True,
            }
        ]
    }

    # Build empty block
    block = build_npi_performance_block(npi_master_example)
    print(json.dumps(block, indent=2))
