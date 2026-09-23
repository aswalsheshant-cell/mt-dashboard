# Data Security & Sensitivity Classification

**Created:** 2026-09-23, Phase 17.5 of "Production Acceptance & Certified Baseline
Lock." **This extends, not replaces,** the already-existing, already-enforced
governance in `docs/knowledge/KA-10-sensitive-data-boundary.md` (business-approved,
`Internal_Approval_Required: No — this boundary is not negotiable`, enforced today by
`tests/test_published_assets_privacy.py`, confirmed passing on the certified baseline:
2 passed, 1 skipped). Nothing here overrides or loosens KA-10.

## Classification matrix

| Data class | Sensitivity | Approved storage | Approved processing | External AI allowed? | GitHub allowed? | Power BI allowed? | Export restrictions | Retention |
|---|---|---|---|---|---|---|---|---|
| Raw customer/chain sales (Primary/Offtake extracts) | CONFIDENTIAL | `PowerBI/RawDataFolders/` (gitignored, never committed) | `scripts/build_dashboard_data.py` locally; never leaves the build environment as raw rows | **No** — never sent to an external LLM as raw rows; only already-published aggregate KPIs (via this session, reading `data.js`) are in scope for AI processing | **No** — raw files are explicitly `.gitignore`d, confirmed by CLAUDE.md's own "Source .xlsb/.xlsx files are gitignored" | Yes — this is Power BI's intended input, via the documented gateway/folder connection (not yet live, see `docs/PBIP_PRODUCTION_ACCEPTANCE.md`) | Never exported to a personal device or non-approved cloud storage | REQUIRES_SECURITY_OWNER_DECISION — no retention policy is documented anywhere in this repo |
| Store-level sales (chain × store × article grain) | CONFIDENTIAL | Same as above, folded into `dashboard/data.js` only as aggregates (chain/zone/brand rollups, never raw per-store-per-transaction rows) | Same | No (aggregate-only, as published) | Aggregates only, via `dashboard/data.js` (public GitHub Pages artifact — see KA-10) | Yes, at source grain inside the semantic model (not yet live) | Same | REQUIRES_SECURITY_OWNER_DECISION |
| Financial NSV/CM2/margin figures | CONFIDENTIAL (source), publishable as aggregate | `dashboard/data.js` (aggregate), source workbooks gitignored | `cm2_block()`, `tot_block()`, etc. | Aggregate figures only (already the case for every number this session read and discussed) | Aggregate figures already published to GitHub Pages by design (this is the dashboard's whole purpose) | Yes | Do not export row-level P&L/expense data (`PL_Expense_Input.csv` and similar stay gitignored per FM-01's own history) | REQUIRES_SECURITY_OWNER_DECISION |
| Employee/BA (Brand Ambassador) data — names, IDs, grades, individual targets/payouts | **RESTRICTED** | `incentive_working/` (gitignored, per session-resume banner: "18 file(s), gitignored") | Incentive-scope scripts only, never the dashboard-publishing pipeline | **No, never** | **No, never** — this is exactly what `tests/test_published_assets_privacy.py` exists to block (`HCPL\d+` employee IDs, `Employee Name`, `Annual Eligibility`, `Payout Amount`, `Incentive_Grade` patterns) | **No** — KA-10: "DMS/Massit is incentive-scope only and is absent from the commercial payload" | Never, under any circumstance, per KA-10's "not negotiable" status | REQUIRES_SECURITY_OWNER_DECISION, though KA-10 already establishes the publish-side rule independent of a formal retention schedule |
| Aggregated dashboard output (`dashboard/data.js`, `dashboard/index.html`) | INTERNAL (business-sensitive but intentionally published) | GitHub Pages (public URL, regardless of repo visibility — KA-10's own first principle) | `build_dashboard_data.py` full pipeline | Yes — this is the layer this session (and any future AI session) actually reads and reasons about | Yes — this is the committed, published artifact | N/A (this is the dashboard, not the Power BI side) | Public by design once deployed; the privacy test is the only gate before that happens | N/A — versioned in Git history |
| Synthetic/test/demo data | SYNTHETIC ONLY | Anywhere, including public demos | Anywhere | Yes | Yes | Yes | None | N/A |
| DMS/Massit consolidated block (`sales_actuals`) | RESTRICTED (incentive-scope) | Never in `dashboard/data.js` | Incentive pipeline only | No | No | No | KA-10 + `test_dms_block_absent_from_published_payload` enforce this at the schema level (`"sales_actuals" not in d`) | REQUIRES_SECURITY_OWNER_DECISION |

## What this document does NOT invent

Per this phase's own instruction — **"Do not invent company policy. If company
policy is unavailable, mark REQUIRES_SECURITY_OWNER_DECISION rather than
assuming"** — the following are explicitly left open, not guessed at:

- **Formal data retention periods** for any class above. No retention schedule exists
  anywhere in this repository's docs. Every "REQUIRES_SECURITY_OWNER_DECISION" cell
  in the Retention column reflects a genuine absence, not an oversight in this audit.
- **A named Security Owner.** `KA-10`'s enforcement (the privacy test) is real and
  effective, but no individual or role is named anywhere in this repo as the
  accountable Security Owner for data classification decisions. This audit does not
  invent one.
- **Microsoft Purview sensitivity labels.** The mega-prompt that requested this phase
  cites Purview's support for labeling Power BI reports/semantic models/dashboards.
  This repo has **no evidence any Purview label has ever been applied** — no live
  Power BI Service tenant exists yet (`docs/PBIP_PRODUCTION_ACCEPTANCE.md`), so
  Purview labeling is not yet actionable. Recorded here as a **future action once a
  live workspace exists**, not claimed as done.

## AI agent obligations (binding on this session and any future one working in this repo)

Restating the mega-prompt's own list, cross-checked against what this repo already
enforces vs. what remains a stated intention only:

| Rule | Enforced how, today | Status |
|---|---|---|
| No raw company data → external AI | This session never read raw `.xlsb`/`.xlsx` files (they're gitignored and physically absent from the checkout in normal operation) | **Enforced by absence** — not a policy control, a structural one (the files simply aren't there to leak) |
| No credentials → repo | `.gitignore` patterns; no credential was read, printed, or committed by this session at any point in this entire certification pass | **Observed, consistent with practice** |
| No customer-level exports → uncontrolled systems | Not applicable this pass — no export was performed | **N/A this pass** |
| No employee data → external system | `tests/test_published_assets_privacy.py` (KA-10) | **Enforced, tested, passing** |
| Synthetic/test data only → public demos | `pipeline_generate_sidecars.py`'s fail-closed guard (PR #157/#177, this session's own certification pass) — requires an explicit `--i-understand-this-is-mock-data` flag and stamps `is_synthetic=true` before any synthetic value reaches a live path | **Enforced, tested, passing** |

## Verdict for this sub-phase

**PARTIAL — the one rule that matters most (employee/incentive data never reaching a
public artifact) is real, tested, and passing today (KA-10).** Retention policy and a
named Security Owner are genuine, undecided gaps — correctly marked
REQUIRES_SECURITY_OWNER_DECISION rather than filled in by this session. Purview
labeling is a real future action, blocked only on a live Power BI workspace existing
first (same blocker as Phase 17.4).
