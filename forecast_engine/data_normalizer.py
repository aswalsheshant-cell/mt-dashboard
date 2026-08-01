# -*- coding: utf-8 -*-
"""Data schema normalization layer for heterogeneous input sources."""
import pandas as pd
from typing import Dict, List, Optional, Tuple


class DataNormalizer:
    """Standardizes input data from multiple sources (Margin Repo, Primary, Offtake) to consistent schema."""

    # Canonical column mappings: what we expect after normalization
    MARGIN_COLUMNS = {
        "ean", "chain", "brand", "category", "article",
        "mrp", "final_effective_margin_pct", "distribution_pct",
        "record_status", "qc_severity", "zone", "state"
    }

    PRIMARY_COLUMNS = {
        "ean", "chain", "brand", "category", "article",
        "date", "quantity", "primary_qty", "chain_name",
        "zone", "state"
    }

    OFFTAKE_COLUMNS = {
        "ean", "chain", "brand", "category", "article",
        "date", "quantity", "offtake_qty", "chain_name",
        "zone", "state"
    }

    # Case-insensitive column mapping: (lowercase canonical, [possible variations])
    COLUMN_ALIASES = {
        "ean": {"ean", "EAN", "Ean"},
        "chain": {"chain", "CHAIN", "chain_id", "Chain ID"},
        "chain_name": {"chain_name", "Chain Name", "chain name", "Chain"},
        "brand": {"brand", "Brand", "BRAND"},
        "category": {"category", "Category", "CATEGORY"},
        "article": {"article", "Article", "ARTICLE", "sku", "SKU"},
        "date": {"date", "Date", "DATE", "month", "Month"},
        "quantity": {"quantity", "Quantity", "QUANTITY", "qty", "Qty"},
        "primary_qty": {"primary_qty", "Primary_Qty", "primary quantity", "Primary Quantity"},
        "offtake_qty": {"offtake_qty", "Offtake_Qty", "offtake quantity", "Offtake Quantity"},
        "mrp": {"mrp", "MRP", "Mrp"},
        "final_effective_margin_pct": {"final_effective_margin_pct", "Final_Effective_Margin_Pct", "margin_pct", "Margin_Pct"},
        "distribution_pct": {"distribution_pct", "Distribution_Pct", "distribution", "Distribution"},
        "record_status": {"record_status", "Record_Status", "status", "Status"},
        "qc_severity": {"qc_severity", "QC_Severity", "qc severity"},
        "zone": {"zone", "Zone", "ZONE"},
        "state": {"state", "State", "STATE"},
    }

    @classmethod
    def normalize_columns(cls, df: pd.DataFrame, source_type: str = "auto") -> pd.DataFrame:
        """
        Normalize DataFrame columns to lowercase canonical names.

        Args:
            df: Input DataFrame with potentially mixed-case column names
            source_type: "margin", "primary", "offtake", or "auto" (infer from columns)

        Returns:
            DataFrame with standardized lowercase column names
        """
        if df.empty:
            return df

        normalized = df.copy()

        # Build reverse mapping: actual column → canonical lowercase
        reverse_map = {}
        for canonical, aliases in cls.COLUMN_ALIASES.items():
            for alias in aliases:
                reverse_map[alias] = canonical

        # Rename columns using case-insensitive matching
        rename_dict = {}
        for col in normalized.columns:
            # Try exact match first in reverse map
            if col in reverse_map:
                rename_dict[col] = reverse_map[col]
            # Try case-insensitive match
            else:
                lower_col = col.lower()
                if lower_col in reverse_map:
                    rename_dict[col] = reverse_map[lower_col]
                # Try removing spaces and matching
                elif lower_col.replace(" ", "_") in reverse_map:
                    rename_dict[col] = reverse_map[lower_col.replace(" ", "_")]
                elif lower_col.replace("_", " ") in reverse_map:
                    rename_dict[col] = reverse_map[lower_col.replace("_", " ")]

        if rename_dict:
            normalized = normalized.rename(columns=rename_dict)

        return normalized

    @classmethod
    def normalize_data_types(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to appropriate types (numeric, datetime, string)."""
        normalized = df.copy()

        # Numeric columns — always convert to float64 for calculations
        numeric_cols = {
            "quantity", "primary_qty", "offtake_qty", "mrp",
            "final_effective_margin_pct", "distribution_pct"
        }
        for col in numeric_cols:
            if col in normalized.columns:
                normalized[col] = pd.to_numeric(normalized[col], errors="coerce").astype("float64")

        # DateTime columns
        datetime_cols = {"date"}
        for col in datetime_cols:
            if col in normalized.columns:
                normalized[col] = pd.to_datetime(normalized[col], errors="coerce")

        # String columns (strip whitespace)
        string_cols = {"ean", "chain", "chain_name", "brand", "category", "article", "zone", "state", "record_status", "qc_severity"}
        for col in string_cols:
            if col in normalized.columns and normalized[col].dtype == "object":
                normalized[col] = normalized[col].astype(str).str.strip()

        return normalized

    @classmethod
    def normalize(cls, df: pd.DataFrame, source_type: str = "auto") -> pd.DataFrame:
        """
        Full normalization: column names + data types.

        Args:
            df: Input DataFrame
            source_type: "margin", "primary", "offtake", or "auto"

        Returns:
            Normalized DataFrame
        """
        if df.empty:
            return df

        # Step 1: Normalize column names to lowercase
        normalized = cls.normalize_columns(df, source_type=source_type)

        # Step 2: Normalize data types
        normalized = cls.normalize_data_types(normalized)

        return normalized

    @classmethod
    def validate_normalized(cls, df: pd.DataFrame, required_cols: set) -> Tuple[bool, List[str]]:
        """
        Validate that normalized DataFrame has required columns.

        Returns:
            (is_valid, list_of_missing_columns)
        """
        missing = required_cols - set(df.columns)
        return len(missing) == 0, list(missing)
