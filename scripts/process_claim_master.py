#!/usr/bin/env python3
"""
Process Distributor × Chain Claim Master for CM2 calculation and Dist ROI analysis.

Integrates claim data (Apr-Jun 2026) into dashboard for:
- Chain-level CM2 expense tracking
- Distributor ROI calculations
- Claim category breakdown by chain/distributor
- QA flags and exceptions management

Usage:
    python scripts/process_claim_master.py \
        --claim-excel <path-to-claim-master.xlsx> \
        --output <output-json-file>
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Any
import pandas as pd

class ClaimMasterProcessor:
    """Process distributor chain claims for CM2 and ROI calculations."""

    EXPENSE_CATEGORIES = [
        'Chain Promo (On Invoice)',
        'Extra Margin / Rate Difference',
        'Visibility',
        'Off Invoice / Debit Note Promo',
        'Freight / Transportation',
        'Other Claims',
        'Incentive'
    ]

    def __init__(self, claim_excel_path: str):
        """Initialize processor with claim master Excel file."""
        self.file_path = Path(claim_excel_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Claim master file not found: {claim_excel_path}")

        self.data = {}
        self.load_sheets()

    def _extract_data_with_headers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract data from DataFrame by finding header row."""
        for idx, row in df.iterrows():
            # Look for a row with meaningful headers
            if not row.isna().all() and len(str(row.iloc[0])) > 2:
                # This looks like a header row
                df.columns = row.values
                return df[idx+1:].reset_index(drop=True)
        return df

    def load_sheets(self):
        """Load all relevant sheets from Excel."""
        print(f"📖 Loading claim master from: {self.file_path.name}")

        # Load Claim Master (core data)
        try:
            claim_df = pd.read_excel(self.file_path, sheet_name='Claim Master', header=1)
            self.data['claim_master'] = claim_df
            print(f"   ✓ Claim Master: {len(claim_df)} rows")
        except Exception as e:
            print(f"   ✗ Error loading Claim Master: {e}")

        # Load Chain Summary
        try:
            chain_df = pd.read_excel(self.file_path, sheet_name='Chain Summary')
            chain_df = self._extract_data_with_headers(chain_df)
            self.data['chain_summary'] = chain_df
            print(f"   ✓ Chain Summary: {len(chain_df)} rows")
        except Exception as e:
            print(f"   ✗ Error loading Chain Summary: {e}")

        # Load Distributor Summary
        try:
            dist_df = pd.read_excel(self.file_path, sheet_name='Distributor Summary')
            dist_df = self._extract_data_with_headers(dist_df)
            self.data['distributor_summary'] = dist_df
            print(f"   ✓ Distributor Summary: {len(dist_df)} rows")
        except Exception as e:
            print(f"   ✗ Error loading Distributor Summary: {e}")

        # Load Exceptions
        try:
            exc_df = pd.read_excel(self.file_path, sheet_name='Exceptions')
            exc_df = self._extract_data_with_headers(exc_df)
            self.data['exceptions'] = exc_df
            print(f"   ✓ Exceptions: {len(exc_df)} rows")
        except Exception as e:
            print(f"   ✗ Error loading Exceptions: {e}")

    def build_claim_by_chain(self) -> Dict[str, Dict[str, Any]]:
        """Build chain-level claim expense breakdown."""
        claims_by_chain = {}

        if 'chain_summary' not in self.data:
            return claims_by_chain

        df = self.data['chain_summary']

        # Get first column name (should be 'Chain')
        first_col = df.columns[0]

        for _, row in df.iterrows():
            chain_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
            if not chain_name or chain_name in ['Chain', 'nan', '']:
                continue

            total = 0
            expenses = {}

            # Sum all numeric columns (skip first column which is chain name)
            for col in df.columns[1:]:
                if col and isinstance(col, str) and not pd.isna(row[col]):
                    try:
                        value = float(row[col]) if row[col] != 0 else 0
                        if value != 0:
                            expenses[str(col).strip()] = value
                            total += value
                    except (ValueError, TypeError):
                        pass

            if total > 0 or expenses:
                claims_by_chain[chain_name] = {
                    'total_claim_lakh': round(total, 2),
                    'by_category': {k: round(v, 2) for k, v in expenses.items() if v != 0},
                    'row_count': 0
                }

        print(f"\n📊 CHAIN-LEVEL CLAIMS:")
        print(f"   Total chains: {len(claims_by_chain)}")
        if claims_by_chain:
            print(f"   Total claim value: ₹{sum(c['total_claim_lakh'] for c in claims_by_chain.values()):,.2f} L")

        return claims_by_chain

    def build_distributor_summary(self) -> Dict[str, Dict[str, Any]]:
        """Build distributor-level claim summary with ROI metrics."""
        dist_claims = {}

        if 'distributor_summary' not in self.data:
            return dist_claims

        df = self.data['distributor_summary']

        for _, row in df.iterrows():
            dist_name = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else None
            if not dist_name or dist_name in ['Distributor', 'nan', '']:
                continue

            # Try to extract monthly values from columns (Apr-2026, May-2026, Jun-2026)
            apr = 0
            may = 0
            jun = 0

            for col in df.columns:
                if pd.notna(col):
                    col_str = str(col).lower()
                    if 'apr' in col_str:
                        try:
                            apr = float(row[col]) if pd.notna(row[col]) else 0
                        except (ValueError, TypeError):
                            pass
                    elif 'may' in col_str:
                        try:
                            may = float(row[col]) if pd.notna(row[col]) else 0
                        except (ValueError, TypeError):
                            pass
                    elif 'jun' in col_str:
                        try:
                            jun = float(row[col]) if pd.notna(row[col]) else 0
                        except (ValueError, TypeError):
                            pass

            total = apr + may + jun
            if total > 0:
                dist_claims[dist_name] = {
                    'total_claim_lakh': round(total, 2),
                    'apr_lakh': round(apr, 2),
                    'may_lakh': round(may, 2),
                    'jun_lakh': round(jun, 2),
                    'avg_monthly': round(total / 3, 2) if total > 0 else 0,
                }

        print(f"\n💼 DISTRIBUTOR-LEVEL CLAIMS:")
        print(f"   Total distributors: {len(dist_claims)}")
        if dist_claims:
            print(f"   Total claim value: ₹{sum(d['total_claim_lakh'] for d in dist_claims.values()):,.2f} L")

        return dist_claims

    def build_claim_quality_summary(self) -> Dict[str, Any]:
        """Build data quality and review status summary."""
        quality = {
            'total_records': 0,
            'exceptions_count': 0,
        }

        if 'claim_master' in self.data:
            df = self.data['claim_master']
            quality['total_records'] = len(df)

        if 'exceptions' in self.data:
            df = self.data['exceptions']
            quality['exceptions_count'] = len(df)

        print(f"\n✅ DATA QUALITY:")
        print(f"   Total records: {quality['total_records']}")
        print(f"   Exceptions: {quality['exceptions_count']}")

        return quality

    def build_output(self) -> Dict[str, Any]:
        """Build complete output structure for dashboard integration."""
        output = {
            'metadata': {
                'source': 'Distributor_Chain_Claim_Master_AprJun_2026.xlsx',
                'months': ['Apr-2026', 'May-2026', 'Jun-2026'],
                'period': 'Q1 FY27',
                'generated_at': pd.Timestamp.now().isoformat()
            },
            'claims': {
                'by_chain': self.build_claim_by_chain(),
                'by_distributor': self.build_distributor_summary(),
                'quality_summary': self.build_claim_quality_summary()
            }
        }

        return output

    def process(self) -> Dict[str, Any]:
        """Process all claim data and return structured output."""
        print("\n🔄 PROCESSING CLAIM MASTER DATA...")
        print("=" * 70)

        return self.build_output()


def main():
    ap = argparse.ArgumentParser(
        description='Process Distributor x Chain Claim Master for CM2 and Dist ROI'
    )
    ap.add_argument('--claim-excel', required=True,
                    help='Path to Distributor_Chain_Claim_Master Excel file')
    ap.add_argument('--output', default='dashboard/claim_data.json',
                    help='Output JSON file for dashboard integration')

    args = ap.parse_args()

    # Process claim master
    processor = ClaimMasterProcessor(args.claim_excel)
    output = processor.process()

    # Write output
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n💾 Output saved to: {out_path}")
    print(f"   File size: {out_path.stat().st_size / 1024:.1f} KB")

    return 0


if __name__ == '__main__':
    exit(main())
