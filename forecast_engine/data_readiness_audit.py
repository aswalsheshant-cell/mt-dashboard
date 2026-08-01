# -*- coding: utf-8 -*-
"""Phase A data readiness audit.

Validates input data quality before forecast pipeline execution.
Enforces strict BLOCKED/FAIL/WARNING/PASS classification.
No silent resolution; all issues assigned to owner with recommended action.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import datetime as dt
import json


EXCLUDED_BRANDS = {"Pure Origin", "Lumineve", "Staze"}

REQUIRED_COLUMNS = {
    "primary_history": {
        "month", "chain_name", "zone", "state", "brand", "category",
        "article", "ean", "primary_qty", "primary_nsv", "distributor", "warehouse"
    },
    "offtake_history": {
        "month", "chain_name", "zone", "state", "brand", "category",
        "article", "ean", "offtake_qty", "offtake_nsv", "store_count"
    },
    "fact_margin": {
        "month", "chain_name", "brand", "article", "ean",
        "margin_pct", "tot_pct", "gst_pct", "cm2_pct", "quality_status"
    },
    "article_master": {"ean", "article", "brand", "category"},
    "chain_master": {"chain_name", "zone", "state"},
    "warehouse_mapping": {"chain_name", "zone", "state", "warehouse"},
}

VALID_MONTHS = [f"{y}-{m:02d}" for y in range(2024, 2027) for m in range(1, 13)]


class DataReadinessAudit:
    """Phase A data quality and readiness validation."""

    def __init__(self, input_dir: str, output_dir: str):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.audit_results = {}
        self.issues = []
        self.summary = {
            "PASS": 0,
            "WARNING": 0,
            "FAIL": 0,
            "BLOCKED": 0,
        }

    def log_issue(
        self,
        issue_type: str,
        severity: str,
        count: int,
        owner: str,
        action: str,
        details: Optional[str] = None,
    ):
        """Record an audit issue."""
        self.issues.append({
            "type": issue_type,
            "severity": severity,
            "count": count,
            "owner": owner,
            "action": action,
            "details": details,
        })
        self.summary[severity] += 1

    def audit_columns(self, df: pd.DataFrame, expected_cols: set, file_type: str):
        """Check required columns exist."""
        missing = expected_cols - set(df.columns)
        if missing:
            self.log_issue(
                issue_type=f"Missing columns in {file_type}",
                severity="BLOCKED",
                count=len(missing),
                owner="Data Ops",
                action=f"Add missing columns: {missing}",
                details=f"Expected: {expected_cols}, Got: {set(df.columns)}",
            )
            return False
        return True

    def audit_blank_values(self, df: pd.DataFrame, required_cols: set, file_type: str):
        """Check for blank/missing values in required columns."""
        for col in required_cols:
            if col not in df.columns:
                continue
            blank_count = df[col].isna().sum() + (df[col] == "").sum()
            if blank_count > 0:
                self.log_issue(
                    issue_type=f"Blank values in {file_type}.{col}",
                    severity="FAIL" if blank_count > len(df) * 0.01 else "WARNING",
                    count=blank_count,
                    owner="Data Owner",
                    action=f"Investigate and fill {blank_count} blank values in {col}",
                    details=f"{blank_count} of {len(df)} rows ({100*blank_count/len(df):.1f}%)",
                )

    def audit_duplicates(self, df: pd.DataFrame, key_cols: List[str], file_type: str):
        """Check for duplicate records by key columns."""
        if not all(col in df.columns for col in key_cols):
            return
        dup_mask = df.duplicated(subset=key_cols, keep=False)
        dup_count = dup_mask.sum()
        if dup_count > 0:
            self.log_issue(
                issue_type=f"Duplicate records in {file_type}",
                severity="BLOCKED",
                count=dup_count // 2,  # Report as duplicate pairs
                owner="Data Ops",
                action=f"Identify and merge or remove {dup_count} duplicate rows",
                details=f"Key columns: {key_cols}",
            )

    def audit_numeric_format(self, df: pd.DataFrame, numeric_cols: set, file_type: str):
        """Check numeric columns are valid numbers, not text."""
        for col in numeric_cols:
            if col not in df.columns:
                continue
            # Try to convert; count failures
            try:
                pd.to_numeric(df[col], errors="coerce")
            except Exception as e:
                self.log_issue(
                    issue_type=f"Non-numeric values in {file_type}.{col}",
                    severity="FAIL",
                    count=1,
                    owner="Data Ops",
                    action=f"Convert {col} to numeric or fill with 0",
                )
                return

            non_numeric_count = pd.to_numeric(df[col], errors="coerce").isna().sum()
            if non_numeric_count > 0:
                self.log_issue(
                    issue_type=f"Non-numeric values in {file_type}.{col}",
                    severity="FAIL" if non_numeric_count > 5 else "WARNING",
                    count=non_numeric_count,
                    owner="Data Ops",
                    action=f"Fix or remove {non_numeric_count} non-numeric values",
                )

    def audit_negative_quantities(self, df: pd.DataFrame, qty_cols: set, file_type: str):
        """Flag negative sales quantities (may be returns, but need clarification)."""
        for col in qty_cols:
            if col not in df.columns:
                continue
            neg_mask = pd.to_numeric(df[col], errors="coerce") < 0
            neg_count = neg_mask.sum()
            if neg_count > 0:
                self.log_issue(
                    issue_type=f"Negative quantities in {file_type}.{col}",
                    severity="WARNING",
                    count=neg_count,
                    owner="Business Sponsor",
                    action=f"Confirm treatment of {neg_count} negative values (returns vs. data errors)",
                )

    def audit_months(self, df: pd.DataFrame, file_type: str):
        """Check month column format and coverage."""
        if "month" not in df.columns:
            return
        invalid_months = df[~df["month"].isin(VALID_MONTHS)]
        if len(invalid_months) > 0:
            self.log_issue(
                issue_type=f"Invalid month format in {file_type}",
                severity="BLOCKED",
                count=len(invalid_months),
                owner="Data Ops",
                action="Fix month format to YYYY-MM",
                details=f"Invalid values: {invalid_months['month'].unique()}",
            )

        # Check coverage: should be Apr 2025 through Jun 2026 minimum
        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        min_month = df["month"].min()
        max_month = df["month"].max()
        expected_start = pd.Timestamp("2025-04-01")
        expected_end = pd.Timestamp("2026-06-30")

        if min_month > expected_start:
            self.log_issue(
                issue_type=f"Insufficient historical depth in {file_type}",
                severity="WARNING",
                count=1,
                owner="Data Ops",
                action="Add historical data prior to April 2025",
                details=f"Data starts at {min_month}, expected April 2025",
            )

    def audit_article_history(self, df: pd.DataFrame, min_months: int = 6):
        """Check articles have sufficient historical depth."""
        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        article_months = df.groupby("ean")["month"].nunique()
        insufficient = article_months[article_months < min_months]

        if len(insufficient) > 0:
            self.log_issue(
                issue_type=f"Articles with insufficient history (<{min_months} months)",
                severity="WARNING",
                count=len(insufficient),
                owner="KAM / Category",
                action=f"Review {len(insufficient)} articles with <{min_months} months data (may be NPI or new listings)",
                details=f"Range: {insufficient.min()}-{insufficient.max()} months",
            )

    def audit_master_mapping(self, primary_df: pd.DataFrame, margin_df: pd.DataFrame):
        """Check all demand articles exist in margin master."""
        demand_eans = set(primary_df["ean"].unique())
        margin_eans = set(margin_df["ean"].unique())
        unmapped = demand_eans - margin_eans

        if unmapped:
            self.log_issue(
                issue_type="Unmapped EANs (demand without margin)",
                severity="FAIL" if len(unmapped) > 10 else "WARNING",
                count=len(unmapped),
                owner="Margin Owner",
                action=f"Map or exclude {len(unmapped)} EANs in margin master",
                details=f"Sample unmapped: {list(unmapped)[:5]}",
            )

    def audit_warehouse_mapping(self, primary_df: pd.DataFrame, warehouse_df: pd.DataFrame):
        """Check all chains are mapped to warehouses."""
        demand_chains = set(primary_df["chain_name"].unique())
        mapped_chains = set(warehouse_df["chain_name"].unique())
        unmapped = demand_chains - mapped_chains

        if unmapped:
            self.log_issue(
                issue_type="Unmapped chains (missing warehouse allocation)",
                severity="FAIL" if len(unmapped) > 0 else "WARNING",
                count=len(unmapped),
                owner="Supply Chain",
                action=f"Add warehouse mappings for {unmapped}",
            )

    def audit_excluded_brands(self, df: pd.DataFrame, file_type: str):
        """Check for excluded brands in data."""
        if "brand" not in df.columns:
            return
        excluded_in_data = df[df["brand"].isin(EXCLUDED_BRANDS)]
        if len(excluded_in_data) > 0:
            self.log_issue(
                issue_type=f"Excluded brands in {file_type}",
                severity="WARNING",
                count=len(excluded_in_data),
                owner="Data Ops",
                action="Remove records for excluded brands (Pure Origin, Lumineve, Staze)",
                details=f"Brands found: {excluded_in_data['brand'].unique()}",
            )

    def audit_partial_months(self, df: pd.DataFrame, file_type: str):
        """Flag partial-month data that may skew model."""
        if "month" not in df.columns:
            return

        # Check if latest month is current month (Aug 2026)
        df["month"] = pd.to_datetime(df["month"], errors="coerce")
        max_month = df["month"].max()

        if max_month.month == dt.datetime.now().month and max_month.year == dt.datetime.now().year:
            self.log_issue(
                issue_type=f"Partial-month data in {file_type}",
                severity="WARNING",
                count=1,
                owner="Business Sponsor",
                action="Decide: exclude current month or apply run-rate logic",
                details=f"Latest month is {max_month.strftime('%Y-%m')} (current month)",
            )

    def run_audit(self) -> Dict:
        """Execute full audit suite."""
        print("=" * 70)
        print("PHASE A DATA READINESS AUDIT")
        print("=" * 70)

        files_found = {}
        for file_type in REQUIRED_COLUMNS.keys():
            file_path = self.input_dir / f"{file_type}.csv"
            if file_path.exists():
                files_found[file_type] = pd.read_csv(file_path, dtype=str)
                print(f"✓ Loaded {file_type}: {len(files_found[file_type])} rows")
            else:
                self.log_issue(
                    issue_type=f"Missing file: {file_type}.csv",
                    severity="BLOCKED",
                    count=1,
                    owner="Data Ops",
                    action=f"Provide {file_type}.csv in {self.input_dir}",
                )
                print(f"✗ Missing {file_type}.csv")

        print("\n" + "-" * 70)
        print("AUDIT CHECKS")
        print("-" * 70)

        # Audit each file
        for file_type, df in files_found.items():
            print(f"\nAuditing {file_type}...")

            # Column audit
            if not self.audit_columns(df, REQUIRED_COLUMNS[file_type], file_type):
                continue

            # Blank value audit
            self.audit_blank_values(df, REQUIRED_COLUMNS[file_type], file_type)

            # Duplicate audit
            if file_type == "primary_history":
                self.audit_duplicates(df, ["month", "chain_name", "ean"], file_type)
            elif file_type == "offtake_history":
                self.audit_duplicates(df, ["month", "chain_name", "ean"], file_type)
            elif file_type == "fact_margin":
                self.audit_duplicates(df, ["month", "chain_name", "ean"], file_type)

            # Numeric audit
            numeric_cols = {c for c in df.columns if any(q in c.lower() for q in ["qty", "nsv", "pct"])}
            if numeric_cols:
                self.audit_numeric_format(df, numeric_cols, file_type)

            # Negative quantity audit
            qty_cols = {c for c in df.columns if "qty" in c.lower()}
            if qty_cols:
                self.audit_negative_quantities(df, qty_cols, file_type)

            # Month audit
            if "month" in df.columns:
                self.audit_months(df, file_type)

            # History depth audit
            if file_type in ["primary_history", "offtake_history"]:
                self.audit_article_history(df, min_months=6)

            # Brand exclusion audit
            if "brand" in df.columns:
                self.audit_excluded_brands(df, file_type)

            # Partial month audit
            if file_type in ["primary_history", "offtake_history"]:
                self.audit_partial_months(df, file_type)

        # Cross-file audits
        if "primary_history" in files_found and "fact_margin" in files_found:
            print("\nAuditing master mapping...")
            self.audit_master_mapping(files_found["primary_history"], files_found["fact_margin"])

        if "primary_history" in files_found and "warehouse_mapping" in files_found:
            print("Auditing warehouse allocation...")
            self.audit_warehouse_mapping(files_found["primary_history"], files_found["warehouse_mapping"])

        # Generate report
        self._write_reports()

        return self._summary_dict()

    def _write_reports(self):
        """Write audit results to files."""
        # CSV issues
        issues_df = pd.DataFrame(self.issues)
        issues_df.to_csv(self.output_dir / "audit_issues.csv", index=False)

        # JSON summary
        summary = self._summary_dict()
        with open(self.output_dir / "audit_summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        # Excel workbook
        try:
            with pd.ExcelWriter(self.output_dir / "Data_Readiness_Audit.xlsx", engine="openpyxl") as writer:
                issues_df.to_excel(writer, sheet_name="Issues", index=False)

                summary_df = pd.DataFrame([
                    {"Status": k, "Count": v} for k, v in self.summary.items()
                ])
                summary_df.to_excel(writer, sheet_name="Summary", index=False)
        except Exception as e:
            print(f"Note: Could not create Excel file ({e})")

        print(f"\n✓ Audit reports written to {self.output_dir}")

    def _summary_dict(self) -> Dict:
        """Return audit summary."""
        return {
            "timestamp": dt.datetime.now().isoformat(timespec="seconds"),
            "total_issues": sum(self.summary.values()),
            "summary": self.summary,
            "blocked_count": self.summary["BLOCKED"],
            "gate_status": "FAIL" if self.summary["BLOCKED"] > 0 else "PASS",
            "issues": self.issues,
        }


def run_data_readiness_audit(input_dir: str = "Phase_A_Input", output_dir: str = "audit_output"):
    """Run data readiness audit."""
    audit = DataReadinessAudit(input_dir, output_dir)
    result = audit.run_audit()

    print("\n" + "=" * 70)
    print("AUDIT SUMMARY")
    print("=" * 70)
    print(f"PASS:     {result['summary']['PASS']}")
    print(f"WARNING:  {result['summary']['WARNING']}")
    print(f"FAIL:     {result['summary']['FAIL']}")
    print(f"BLOCKED:  {result['summary']['BLOCKED']}")
    print(f"\nGate Status: {result['gate_status'].upper()}")

    if result['gate_status'] == "FAIL":
        print("\n❌ FORECAST PIPELINE BLOCKED")
        print(f"   {result['blocked_count']} blocking issue(s) must be resolved before forecast runs")
    else:
        print("\n✅ DATA READY FOR FORECAST")

    print("=" * 70)

    return result


if __name__ == "__main__":
    import sys
    input_dir = sys.argv[1] if len(sys.argv) > 1 else "Phase_A_Input"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "audit_output"
    run_data_readiness_audit(input_dir, output_dir)
