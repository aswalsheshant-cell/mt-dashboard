#!/usr/bin/env python3
"""
NPI Master Loader — Load and validate article-level NPI metadata.

Reads NPI_Master.csv and produces a validated dict structure for use in
build_dashboard_data.py. Handles missing optional fields gracefully.

NPI Master required columns:
  article_id, article_name, brand, category, pack_size, launch_date, launch_fy, npi_flag

Optional columns:
  sub_brand, sub_category, price_band, launch_month, launch_quarter, npi_type,
  comparable_article_id, comparable_category, comparable_price_band, target_chain,
  target_zone, target_store_count, target_distribution_pct, launch_wave,
  seasonality_profile, weather_sensitivity, price_sensitivity, expected_ramp_months
"""
from __future__ import annotations
import csv, json, math
from pathlib import Path
from datetime import datetime
import pandas as pd

# ---- FY Helpers (match build_dashboard_data.py) ----
_MON3_NUM = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,
             "Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}

def fy_tag_from_ym(year, month):
    """(year, month) -> 'FY27'. Apr-2026 -> FY27; Mar-2026 -> FY26."""
    return f"FY{(year + 1 if month >= 4 else year) % 100:02d}"

def fy_start_year(tag):
    """'FY27' -> 2026."""
    return 2000 + int(str(tag).strip()[2:]) - 1

# ---- NPI Master Loader ----
class NPIMasterLoader:
    """Load, validate, and transform NPI Master CSV into data.js structure."""

    REQUIRED_COLS = {
        "article_id", "article_name", "brand", "category", "pack_size",
        "launch_date", "launch_fy", "npi_flag"
    }

    OPTIONAL_COLS = {
        "sub_brand", "sub_category", "price_band", "launch_month",
        "launch_quarter", "npi_type", "comparable_article_id",
        "comparable_category", "comparable_price_band", "target_chain",
        "target_zone", "target_store_count", "target_distribution_pct",
        "launch_wave", "seasonality_profile", "weather_sensitivity",
        "price_sensitivity", "expected_ramp_months"
    }

    VALID_NPI_TYPES = {"New Brand", "New Variant", "New Pack", "New Price Point",
                       "Reformulation", "Relaunch"}
    VALID_MATURITY_STATUSES = {"LAUNCH", "BUILD", "SCALE", "STABILISE", "MATURE"}

    def __init__(self, csv_path):
        self.csv_path = Path(csv_path)
        self.data = []
        self.errors = []
        self.warnings = []

    def load(self) -> bool:
        """Load and validate NPI Master CSV. Returns True if no critical errors."""
        if not self.csv_path.exists():
            self.errors.append(f"NPI Master file not found: {self.csv_path}")
            return False

        try:
            df = pd.read_csv(self.csv_path, dtype=str, keep_default_na=False)
        except Exception as e:
            self.errors.append(f"Failed to read CSV: {e}")
            return False

        # Validate schema
        missing = self.REQUIRED_COLS - set(df.columns)
        if missing:
            self.errors.append(f"Missing required columns: {missing}")
            return False

        self.data = []
        for idx, row in df.iterrows():
            article = self._parse_row(row, idx + 2)  # +2 for header + 1-indexing
            if article:
                self.data.append(article)

        if not self.data and self.errors:
            return False

        return True

    def _parse_row(self, row, row_num) -> dict | None:
        """Parse a single NPI Master row. Returns None if critical errors."""
        article_id = row.get("article_id", "").strip()
        if not article_id:
            self.errors.append(f"Row {row_num}: article_id is required")
            return None

        # Parse launch date
        launch_date = row.get("launch_date", "").strip()
        if not launch_date:
            self.errors.append(f"Row {row_num} ({article_id}): launch_date is required")
            return None

        try:
            dt = pd.to_datetime(launch_date, errors="coerce")
            if pd.isna(dt):
                raise ValueError("Could not parse date")
            launch_day = dt
            launch_month_num = dt.month
            launch_year = dt.year
        except Exception as e:
            self.errors.append(f"Row {row_num} ({article_id}): Invalid launch_date '{launch_date}': {e}")
            return None

        # Derive FY if not provided
        launch_fy = row.get("launch_fy", "").strip()
        if not launch_fy:
            launch_fy = fy_tag_from_ym(launch_year, launch_month_num)

        # Validate NPI flag
        npi_flag_str = row.get("npi_flag", "").strip().lower()
        npi_flag = npi_flag_str in ("true", "yes", "1", "y")

        # NPI type (optional, but validate if provided)
        npi_type = row.get("npi_type", "").strip() or None
        if npi_type and npi_type not in self.VALID_NPI_TYPES:
            self.warnings.append(
                f"Row {row_num} ({article_id}): npi_type '{npi_type}' not in "
                f"{self.VALID_NPI_TYPES}; using as-is")

        # Parse numeric fields
        target_store_count = self._parse_int(row.get("target_store_count", ""))
        target_distribution_pct = self._parse_float(row.get("target_distribution_pct", ""))
        expected_ramp_months = self._parse_int(row.get("expected_ramp_months", ""))

        # Derive launch month if not provided
        launch_month = row.get("launch_month", "").strip() or None
        if not launch_month:
            mon3 = {v: k for k, v in _MON3_NUM.items()}
            launch_month = mon3.get(launch_month_num)

        # Derive launch quarter if not provided
        launch_quarter = row.get("launch_quarter", "").strip() or None
        if not launch_quarter:
            quarter_map = {
                4: "Q1", 5: "Q1", 6: "Q1",
                7: "Q2", 8: "Q2", 9: "Q2",
                10: "Q3", 11: "Q3", 12: "Q3",
                1: "Q4", 2: "Q4", 3: "Q4"
            }
            q = quarter_map.get(launch_month_num)
            launch_quarter = f"{q}-{launch_year % 100:02d}" if q else None

        # Parse target_chain and target_zone (may be comma-separated or pipe-separated)
        target_chain = self._parse_list(row.get("target_chain", ""))
        target_zone = self._parse_list(row.get("target_zone", ""))

        article = {
            "article_id": article_id,
            "article_name": row.get("article_name", "").strip() or article_id,
            "brand": row.get("brand", "").strip() or None,
            "sub_brand": row.get("sub_brand", "").strip() or None,
            "category": row.get("category", "").strip() or None,
            "sub_category": row.get("sub_category", "").strip() or None,
            "pack_size": row.get("pack_size", "").strip() or None,
            "price_band": row.get("price_band", "").strip() or None,
            "launch_date": launch_day.isoformat() if pd.notna(launch_day) else None,
            "launch_fy": launch_fy,
            "launch_month": launch_month,
            "launch_quarter": launch_quarter,
            "npi_flag": npi_flag,
            "npi_type": npi_type,
            "comparable_article_id": row.get("comparable_article_id", "").strip() or None,
            "comparable_category": row.get("comparable_category", "").strip() or None,
            "comparable_price_band": row.get("comparable_price_band", "").strip() or None,
            "target_chain": target_chain,
            "target_zone": target_zone,
            "target_store_count": target_store_count,
            "target_distribution_pct": target_distribution_pct,
            "launch_wave": row.get("launch_wave", "").strip() or None,
            "seasonality_profile": row.get("seasonality_profile", "").strip() or None,
            "weather_sensitivity": row.get("weather_sensitivity", "").strip() or None,
            "price_sensitivity": row.get("price_sensitivity", "").strip() or None,
            "expected_ramp_months": expected_ramp_months,
        }

        return article

    @staticmethod
    def _parse_int(val):
        """Parse integer, return None if invalid/blank."""
        if not val or (isinstance(val, float) and math.isnan(val)):
            return None
        try:
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_float(val):
        """Parse float, return None if invalid/blank."""
        if not val or (isinstance(val, float) and math.isnan(val)):
            return None
        try:
            return round(float(str(val).strip()), 2)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_list(val):
        """Parse comma/pipe-separated list, return [] if blank."""
        if not val or (isinstance(val, float) and math.isnan(val)):
            return []
        s = str(val).strip()
        if not s:
            return []
        # Try both comma and pipe separators
        if ',' in s:
            return [x.strip() for x in s.split(',') if x.strip()]
        elif '|' in s:
            return [x.strip() for x in s.split('|') if x.strip()]
        else:
            return [s] if s else []

    def to_dict(self) -> dict:
        """Return data.js-ready NPI master structure."""
        return {
            "npi_articles": self.data,
            "n_npi_articles": len([a for a in self.data if a.get("npi_flag")]),
            "n_total_articles": len(self.data),
            "load_status": "ok" if not self.errors else "error",
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def report(self):
        """Print load summary."""
        print(f"\n{'='*80}")
        print("NPI MASTER LOADER REPORT")
        print(f"{'='*80}")
        print(f"File: {self.csv_path}")
        print(f"Articles loaded: {len(self.data)}")
        print(f"NPI articles (npi_flag=true): {len([a for a in self.data if a.get('npi_flag')])}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for e in self.errors:
                print(f"  {e}")
        else:
            print("\n✓ No errors")

        if self.warnings:
            print(f"\n⚠ WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                print(f"  {w}")

        print(f"\n{'='*80}\n")


def load_npi_master(csv_path: str | Path) -> dict:
    """Load NPI Master CSV and return data.js-ready dict."""
    loader = NPIMasterLoader(csv_path)
    if loader.load():
        loader.report()
        return loader.to_dict()
    else:
        loader.report()
        return {
            "npi_articles": [],
            "n_npi_articles": 0,
            "n_total_articles": 0,
            "load_status": "error",
            "errors": loader.errors,
            "warnings": loader.warnings,
        }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python npi_master_loader.py <path/to/NPI_Master.csv>")
        sys.exit(1)

    csv_path = sys.argv[1]
    result = load_npi_master(csv_path)
    print(json.dumps(result, indent=2))
