# Dashboard source-unit audit

This read-only audit records SHA-256, byte size, row count, signed NSV total,
month counts, and NSV/MRP ratios for the committed Offtake, Primary Article,
and Primary ShipTo CSVs. It reports both rupee and lakh interpretations; it
does **not** choose a source unit or change a number. The private, branch-scoped
GitHub Actions job stores the aggregate JSON for seven days.

Run locally from the repository root with:

    python scripts/audit_dashboard_units.py --repo-root . --out ../dashboard-unit-audit.json

Keep the output outside published `dashboard/` assets. Verify source units
against source documentation and same-basis monthly HTML totals before changing
Power Query. Primary and Offtake are different measures. A missing or mismatched
period is not zero. Preserve raw files, row counts, and hashes.

The ratio sample is deterministic (every 50th row with positive NSV and MRP).
It supports a unit hypothesis but is not proof by itself. The full signed
amount total includes returns and negative rows.

