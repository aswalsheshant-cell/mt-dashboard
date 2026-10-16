# Finance issue register

Source of truth for what Finance owns in this project. Add a row here when a new
finance item appears; do not keep a second list. Values are as last checked, re-run the
check command before quoting them.

| ID | Item | Check command / file | Owner | What Finance must give |
|---|---|---|---|---|
| F-01 | AssumptionTable missing Jun-Sep'26 | `python scripts/check_assumption_coverage.py` | Finance | GM %, Trade Spend %, visibility, scheme, other spend per month, with `Approved: <ref>` in Remarks |
| F-02 | AssumptionTable Apr/May'26 unapproved | same | Finance | Approval reference for the existing rows (they are "Default portfolio assumption") |
| F-03 | 7 distributor claim aliases pending | `PowerBI/SeedData/Mapping/ClaimDriver_Alias_Decisions_Q1_FY27.csv` | Finance (confirm) | Owner_Decision, Approver, Approval_Date, Approval_Reference per alias |
| F-04 | Claims are ALLOCATED_PROVISIONAL, no formal approval reference | `build_distributor_claim_monthly_allocation.py --check` | Finance | Reference for A1 (additive to Direct DN) and A2 (monthly + quarterly CM2) |
| F-05 | Ratnadeep claim amount with no month | claim allocation output | Finance | Month, or confirm it stays quarterly only |
| F-06 | Spar negative claim (about -0.02 L) | claim allocation output | Finance | Credit note or error: keep, reverse or ignore |
| F-07 | 24 chains with no cost (about 7.7% of NSV) | claim / DN coverage in CM2 panel | Finance | DN and claim files, or a written nil confirmation per chain |
| F-08 | Brand / category CM2 claims not included | CM2 panel note | Finance | Brand or category split of claims, or approval to keep chain-level only |
| F-09 | Returns above sales (about -5.18 L) | CM2 panel | Finance | Confirm treatment of the credit |
| F-10 | Provisional COGS total (4,411.21 L) vs its months (3,411.21 L) | `config/pending_inputs.yml`, `docs/evidence/INPUT_AVAILABILITY_REGISTER.md` | Finance | Confirm the GMV / MRP basis |
| F-11 | Rate card / COGS basis (BL-16) | `docs/FAILURE_MODE_REGISTER.md` | Finance | Effective-dated rate card |
| F-13 | Latest month Primary file not loaded (Sep'26) | `python scripts/finance_input_readiness.py` | MT Analyst Lead (SAP billing pull) | primary_article_Sep_26.csv, see playbook B |
| F-12 | Promo funding share (break-even KPI) | `docs/prompts/FMCG_SALES_JOURNEY_TRACKER.md` | Finance + Trade Marketing | Company funding % per scheme |

Cross-check before summing any claim, provision or trade-spend source: FM-14 in
`docs/FAILURE_MODE_REGISTER.md` (provision, claim and settlement can describe one event).
