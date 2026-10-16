# Add a new month to the HTML dashboard and Power BI

Worked example: Sep'26 (Primary workbook "MTD-Primary-Sept'26", Offtake monthly file).

1. **Check coverage first**: `config/data_source_registry.yml`, `docs/DATA_AVAILABILITY_MATRIX.md`. FY tag
   follows THE ONE FY RULE (Sep'26 = FY27).
2. **Primary**: `python scripts/ingest_primary_month_xlsx.py --src "<workbook>.xlsx" --month Sep_26`.
   Output `PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Sep_26.csv` (local only, restricted).
   It checks columns, a single month, invoice dates inside the month, rows and NSV preserved, and ties to the
   workbook's Summary pivot. All rows stay (returns and cancellations are signed), nothing deduplicated.
   Chain = "Customer master 2"; Zone/State = the lowercase `zone`/`state` columns; pack size, sub-category and
   range come from earlier months by EAN, and unseen EANs stay blank (list them to the owner).
3. **Offtake**: put the month file(s) in `PowerBI/RawDataFolders/Offtake_Monthly/`, then
   `python scripts/build_dashboard_data.py --offtake-patch --src PowerBI/RawDataFolders/Offtake_Monthly --out dashboard/data.js`.
   Chains with no rows yet appear only as an exploratory L3M estimate, never added to totals
   (the chain tracker config records who is received).
4. **Primary block**: `python scripts/build_dashboard_data.py --detail-only --detail-max-rows 0 --src <empty dir> --out dashboard/data.js`
   (uncapped on purpose; the default cap silently drops detail coverage).
5. **Prove**: `python -m py_compile scripts/build_dashboard_data.py`, `scripts/ci_validate_datajs.py`,
   44-state sweep (`tests/dashboard_sweep.js`), diff FY25/FY26 and the `primary` / `offtake` blocks (unchanged).
6. **Power BI**: DAX and Power Query have no hard-coded months, so the files in the watch folders are enough.
   Regenerate `PowerBI/reconciliation_expected.json` with `python scripts/reconcile_powerbi_full.py` and check
   FY27 Primary and Offtake match the dashboard. On the user's machine: drop the same CSVs in the watch
   folders, refresh, compare with the expected values. Desktop run (B5) is still the user's.
7. **Tests**: re-pin only numbers that include the new month (FY27 totals, quarter completeness, chain pins).
   Regenerate `PowerBI/data_source_map.json` and `docs/evidence/DATA_SOURCE_MAP.md` from a clean worktree so
   local-only CSVs do not change the committed counts.
8. **Restricted files**: raw store-level or employee-coded CSVs stay out of Git (`config/restricted_source_policy.yml`).
   Only `data.js` and small seeds are committed.
9. **Register**: add the month to the matrix and registry; open a draft PR; do not merge without the owner.
