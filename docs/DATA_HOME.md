# One data home for the HTML and the Power BI dashboard

**Rule.** Every input file lives in one place under `PowerBI/`. Both dashboards read from it. Nothing under `dashboard/` is a source: those files are generated.

| Folder | What goes in it | Git |
|---|---|---|
| `PowerBI/SeedData/` | approved masters, mappings, aggregates, forecast and fill-rate seeds | tracked |
| `PowerBI/RawDataFolders/<watch>/` | monthly drops the Power Query folder queries read | new raw drops are ignored (`.gitignore`); files already tracked stay tracked (owner decision I-2) |
| `PowerBI/Reference/` | references, decision registers, trackers and templates that are NOT approved inputs | tracked |
| `PowerBI/templates/` | blank input templates (layout only) | tracked |
| `dashboard/*.js`, `dashboard/*.json` | **generated** for the HTML dashboard by the script named below | tracked, never hand-edited |

## Generated HTML files and what writes them

| HTML file | Generator | Reads |
|---|---|---|
| `data.js` | `scripts/build_dashboard_data.py` (`--offtake-patch`, `--primary-only`, `--detail-only`) | `PowerBI/RawDataFolders/*`, `PowerBI/SeedData/*` |
| `tdp.js` | `scripts/build_tdp.py` | `PowerBI/RawDataFolders/TDP_Monthly` (none supplied yet) |
| `tdp_inhouse.js` | `scripts/build_tdp_inhouse.py` | offtake files and `Store_City_Master.csv` |
| `tdp_focus.js` | `scripts/build_tdp_focus_articles.py` | offtake and primary article files |
| `store_cuts.js`, `store_universe.js`, `nielsen.js` | `build_store_cuts.py`, `build_store_universe.py`, `build_nielsen_dashboard.py` | `PowerBI/SeedData/Store_Cuts`, `Nielsen`, `Masters` |
| `claim_data.json`, `claim_reconciliation_matrix.json` | `process_claim_master.py`, `reconcile_claim_exceptions.py` | `PowerBI/RawDataFolders/ClaimMaster_Quarterly` |
| `po_sla_alerts.json` | `generate_po_alerts.py` | see script |

## How to check you are not creating a second copy
- `python scripts/audit_data_source_map.py` lists every file the Power Query, the HTML build and the registry read, with its column layout. `docs/evidence/DATA_SOURCE_MAP.md` is the result.
- `config/data_source_registry.yml` has one entry per dataset: path, grain, dates, owner, status.
- `PowerBI/Reference/PR_INPUTS_MANIFEST.csv` lists the files landed from PRs, with SHA-256 and their PR.
- `tests/test_data_home.py` fails if two tracked files under `PowerBI/` have the same name and different content in the same folder family, or if a landed file is not in the manifest.

## Files that were only in PRs or branches
Landed (reference or seed, not wired, not approved): see `PR_INPUTS_MANIFEST.csv`. Everything else (restricted raw extracts, synthetic data, release packages) stays out of Git; `docs/evidence/INPUT_AVAILABILITY_REGISTER.md` lists each with the reason, and `scripts/restore_branch_files.py` copies one to your local folder.
