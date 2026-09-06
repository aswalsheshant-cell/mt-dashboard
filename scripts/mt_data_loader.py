"""
Modern Trade (MT) Data Loader Engine
Extracts, transforms, and validates commercial metrics from CSV exports or SQL databases
into the standard config schema consumed by build_mt_monthly_ppt.py and mt_analytics_engine.py.
"""

from typing import Dict, Any, List, Optional
import os
import csv
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class MTDataLoader:
    def __init__(self, fallback_config: Optional[Dict[str, Any]] = None):
        self.fallback_config = fallback_config or {}

    def load_from_json(self, json_path: str) -> Dict[str, Any]:
        """Loads a pre-aggregated monthly metrics payload from a JSON file."""
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON metrics file not found: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Successfully loaded metrics from JSON: %s", json_path)
        return self._merge_with_fallback(data)

    def load_from_csv_directory(self, csv_dir: str) -> Dict[str, Any]:
        """
        Loads metrics from standard tabular CSV exports:
        - zones.csv: zone_name, primary_nsv, offtake_nsv, conversion_pct, yoy_growth
        - chains.csv: chain_name, primary_cr, offtake_cr, conversion_pct, growth_yoy
        - categories.csv: category_name, share_pct, growth_yoy, hero_sku
        - offtake.csv: [OPTIONAL] chain_name, month, article, nsv_lakhs, qty, store_count
        """
        if not os.path.isdir(csv_dir):
            raise NotADirectoryError(f"CSV data directory not found: {csv_dir}")

        config_patch: Dict[str, Any] = {}

        # 1. Parse Zones
        zones_file = os.path.join(csv_dir, "zones.csv")
        if os.path.exists(zones_file):
            zones_detail = []
            with open(zones_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    zones_detail.append({
                        "name": str(row["zone_name"]).strip(),
                        "nsv": float(row.get("offtake_nsv", row.get("primary_nsv", 1.0))),
                        "conversion": float(row.get("conversion_pct", 50.0)),
                        "yoy_growth": float(row.get("yoy_growth", 0.0))
                    })
            config_patch["zones_detail"] = zones_detail
            logger.info("Ingested %d zone records from %s", len(zones_detail), zones_file)

        # 2. Parse Chains & Diagnostics
        chains_file = os.path.join(csv_dir, "chains.csv")
        if os.path.exists(chains_file):
            with open(chains_file, "r", encoding="utf-8-sig") as f:
                reader = list(csv.DictReader(f))
                if reader:
                    # Treat first or designated chain as the focus diagnostic chain
                    focus = reader[0]
                    config_patch["diagnostic_chain"] = {
                        "chain_name": str(focus.get("chain_name", "Reliance")).strip(),
                        "primary": float(focus.get("primary_cr", 2.40)),
                        "offtake": float(focus.get("offtake_cr", 1.25))
                    }
            logger.info("Ingested diagnostic chain data from %s", chains_file)

        # 3. Parse Categories
        categories_file = os.path.join(csv_dir, "categories.csv")
        if os.path.exists(categories_file):
            categories = []
            with open(categories_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    categories.append({
                        "name": str(row["category_name"]).strip(),
                        "share": float(row.get("share_pct", 0.0)),
                        "growth": float(row.get("growth_yoy", 0.0)),
                        "hero_sku": str(row.get("hero_sku", "")).strip()
                    })
            config_patch["categories"] = categories
            logger.info("Ingested %d category records from %s", len(categories), categories_file)

        # 4. Parse Offtake (Secondary POS Data) [NEW]
        offtake_file = os.path.join(csv_dir, "offtake.csv")
        if os.path.exists(offtake_file):
            offtake_by_chain = {}
            with open(offtake_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    chain = str(row.get("chain_name", "")).strip()
                    month = str(row.get("month", "")).strip()
                    article = str(row.get("article", "")).strip()
                    nsv = float(row.get("nsv_lakhs", 0.0))

                    if chain not in offtake_by_chain:
                        offtake_by_chain[chain] = {"monthly": {}, "total": 0.0}
                    if month not in offtake_by_chain[chain]["monthly"]:
                        offtake_by_chain[chain]["monthly"][month] = 0.0

                    offtake_by_chain[chain]["monthly"][month] += nsv
                    offtake_by_chain[chain]["total"] += nsv

            config_patch["by_chain_detail"] = offtake_by_chain
            logger.info("Ingested offtake data for %d chains from %s", len(offtake_by_chain), offtake_file)
        else:
            logger.info("No offtake.csv found (optional); using fallback aggregates")

        return self._merge_with_fallback(config_patch)

    def load_from_sql(self, connection_string: str, month: str, year: int) -> Dict[str, Any]:
        """
        Executes analytical aggregation queries against an active SQL warehouse connection
        (Snowflake, BigQuery, PostgreSQL, SQLite, etc.) via SQLAlchemy.
        """
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            raise ImportError("SQLAlchemy is required for SQL ingestion. Run: pip install sqlalchemy")

        engine = create_engine(connection_string)
        config_patch: Dict[str, Any] = {}

        zone_query = text("""
            SELECT
                zone_name,
                ROUND(SUM(offtake_val) / 10000000.0, 2) AS nsv_cr,
                ROUND(SUM(offtake_val) * 100.0 / NULLIF(SUM(primary_val), 0), 1) AS conversion_pct,
                ROUND(AVG(yoy_growth_pct), 1) AS yoy_growth
            FROM mt_monthly_sales_fact
            WHERE review_month = :month AND review_year = :year
            GROUP BY zone_name
            ORDER BY nsv_cr DESC;
        """)

        chain_query = text("""
            SELECT
                chain_name,
                ROUND(SUM(primary_val) / 10000000.0, 2) AS primary_cr,
                ROUND(SUM(offtake_val) / 10000000.0, 2) AS offtake_cr
            FROM mt_monthly_sales_fact
            WHERE review_month = :month AND review_year = :year
            GROUP BY chain_name
            ORDER BY primary_cr DESC
            LIMIT 1;
        """)

        with engine.connect() as conn:
            # Query zones
            z_rows = conn.execute(zone_query, {"month": month.lower(), "year": year}).fetchall()
            if z_rows:
                config_patch["zones_detail"] = [
                    {
                        "name": r[0],
                        "nsv": float(r[1] or 0.0),
                        "conversion": float(r[2] or 0.0),
                        "yoy_growth": float(r[3] or 0.0)
                    }
                    for r in z_rows
                ]

            # Query diagnostic chain
            c_row = conn.execute(chain_query, {"month": month.lower(), "year": year}).fetchone()
            if c_row:
                config_patch["diagnostic_chain"] = {
                    "chain_name": c_row[0],
                    "primary": float(c_row[1] or 0.0),
                    "offtake": float(c_row[2] or 0.0)
                }

        logger.info("Successfully fetched live SQL aggregates for %s %d", month, year)
        return self._merge_with_fallback(config_patch)

    def _merge_with_fallback(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        """Merges dynamically loaded fields on top of fallback defaults."""
        merged = self.fallback_config.copy()
        for key, value in patch.items():
            if value is not None:
                merged[key] = value
        return merged
