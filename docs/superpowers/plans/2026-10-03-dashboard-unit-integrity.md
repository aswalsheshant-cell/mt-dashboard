# Dashboard Unit Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Prove and, only where proven, correct unit mismatches so HTML and Power BI agree for the same metric, period, source rows, and channel scope.

**Architecture:** A read-only audit records source units, totals, row counts, hashes, and same-basis comparisons. A focused Power Query change normalizes proven lakh-valued input to the model's rupee contract; dependent measures and QuickSetup follow the source change. The HTML lakh contract remains unless its own audit fails.

**Tech Stack:** Python, CSV, Power Query M, DAX, JavaScript, GitHub Actions, Power BI Desktop.

**Spec:** docs/superpowers/specs/2026-10-03-dashboard-unit-handoff-design.md

## Global Constraints

- Never remove or rewrite a source row, raw CSV, historical mapping, approved value, or frozen evidence to make a check pass.
- Compare Primary with Primary and Offtake with Offtake at the same FY/month/channel and reporting unit. Primary and Offtake are distinct measures.
- Keep the Reliance Brand Counter exclusion on Offtake only.
- Report unexplained deltas as unresolved. A corrected displayed number requires source-to-output explanation.
- B5 remains BLOCKED_PENDING_DESKTOP_EVIDENCE until governed live evidence and human review.
- Keep PR #119 frozen and PR #267 on HOLD. Do not put this work on #291 or the Claude FY branch.
- Use a fresh branch from current main; open a draft correctness-fix PR and do not merge without owner instruction.

## Review Focus

- A source file already in rupees must not be multiplied by 100,000.
- Missing month or incompatible channel scope must read NOT_COMPARABLE, not zero.
- Returns and negative NSV must retain their sign in totals.
- Reliance Brand Counter must stay excluded from Offtake MT totals and included in gross Primary.
- A ratio must use operands with the same unit and preserve BLANK/null behavior for zero denominators.

---

### Task 1: Read-only unit proof

**Files:**
- Create: scripts/audit_dashboard_units.py
- Create: tests/test_dashboard_unit_audit.py
- Create: docs/evidence/dashboard_unit_audit_README.md
- Create: .github/workflows/dashboard-unit-audit.yml (temporary, branch-scoped aggregate artifact runner)

**Interfaces:**
- CLI: python scripts/audit_dashboard_units.py --repo-root PATH --out PATH
- Output: JSON with source path, SHA-256, row count, raw sum, declared unit, normalized rupee sum, FY/month/channel scope, and comparison status.

- [ ] Write fixture tests for lakh and rupee sources, negative returns, absent months, missing columns, and differing scopes. Assert no source file is written.
- [ ] Run python -m pytest tests/test_dashboard_unit_audit.py -q and confirm the tests fail before implementation.
- [ ] Implement the read-only CLI. Read only required CSV columns; stream large monthly files. Use existing FY and RBC rules rather than creating new ones.
- [ ] Run the tests and confirm PASS.
- [ ] Run the audit on an authenticated checkout. If local Git authentication is unavailable, use the branch-scoped dashboard-unit-audit workflow on push: run the script against committed inputs, write aggregate JSON under the runner temporary directory, and upload only that JSON as a short-lived private artifact. Keep row-level data out of logs and published dashboard assets. Retrieve and review the artifact before any model edit.
- [ ] Review source hashes, row counts, monthly totals, and the attachment's sampled NSV-to-MRP ratio. Record which inputs are conclusively lakh, rupee, or unresolved. Commit the script and tests; do not change model calculations yet.

### Task 2: Power BI import normalization

**Files:**
- Modify after Task 1 proof: PowerBI/PowerQuery/11_Fact_OfftakeSales.pq
- Review, modify only if proof requires: PowerBI/PowerQuery/15_Fact_PrimaryShipTo.pq and PowerBI/PowerQuery/16_Fact_PrimaryArticle.pq
- Test: tests/test_powerbi_unit_contract.py

**Interfaces:**
- Fact Offtake Sales[Offtake NSV] and other model currency columns retain the DataDictionary contract of absolute rupees.
- A source-format or unit ambiguity fails clearly rather than silently scaling.

- [ ] Write tests pinning the exact proven source-to-model conversion, including a rupee-valued input that must not be scaled and negative NSV that must retain its sign.
- [ ] Run the targeted test and confirm FAIL against the current query.
- [ ] Add the minimal explicit conversion at the Power Query import boundary. Do not modify source CSVs or data.js.
- [ ] Run the targeted test and confirm PASS; regenerate PowerBI/QuickSetup/AllPowerQuery_Consolidated.txt through the existing generator.
- [ ] Compare raw-source hashes and row counts to Task 1; require no change. Commit only the proven import and generated-reference changes.

### Task 3: Same-unit measures and dependent outputs

**Files:**
- Review and modify where needed: PowerBI/PowerQuery/43_SecondarySalesEfficiency.pq
- Review and modify where needed: PowerBI/DAX/14_SecondarySales_Measures.dax and PowerBI/DAX/01_CoreMeasures.dax
- Regenerate if source DAX changes: PowerBI/QuickSetup/AllDAX_Consolidated.txt
- Test: tests/test_powerbi_unit_contract.py

**Interfaces:**
- Every sell-through or gap numerator and denominator declares one common unit before division.
- Display conversions divide rupees by 100,000 for lakh and 10,000,000 for crore.

- [ ] Write failing checks for the identified mixed-unit ratios, zero-denominator BLANK/null handling, and RBC scope.
- [ ] Run the targeted checks and confirm FAIL on the existing unit mismatch.
- [ ] Correct only measures whose operands the audit proves mismatched; repair misleading unit labels.
- [ ] Run targeted checks, regenerate QuickSetup, and confirm generated content matches source.
- [ ] Commit the focused changes with a before/after unit table and unchanged source hashes.

### Task 4: Same-basis dashboard reconciliation and live verification

**Files:**
- Create: docs/evidence/dashboard_unit_reconciliation_<date>.md
- Modify only if a separate HTML defect is proved: dashboard/index.html or scripts/build_dashboard_data.py
- Test: existing HTML/FY, data.js, financial reconciliation, and Power BI structural suites.

**Interfaces:**
- Evidence rows identify metric, source, FY/month, channel, HTML value in lakh, Power BI value in rupees and lakh, difference, and status.

- [ ] Generate same-basis comparison rows for overlapping months. Require differences within 0.01 lakh at reporting precision or list them as unresolved with lineage.
- [ ] Run existing data.js validation, FY/month tests, browser regression, Power BI structure tests, and the full affected Python suite. Record exact commands and results.
- [ ] If HTML differs independently, add a failing regression and make a separate focused fix; do not use an HTML change to hide a Power BI discrepancy.
- [ ] Refresh the resulting model in Power BI Desktop and capture governed B5 cases, raw results, exact SHA, version, and screenshots. Leave B5 OPEN until its documented human exit decision.
- [ ] Open a draft correctness-fix PR with the reconciliation, no-deletion report, remaining limitations, and rollback instructions. Do not merge.

### Task 5: Review the unfinished Claude FY branch

**Files:** No automatic code movement.

**Interfaces:** A review record of four commits from main 84864ce to branch head 853e01d, with an adopt/revise/hold decision per change.

- [ ] Compare each commit and generated QuickSetup reference against the corrected unit contract and current main.
- [ ] Verify FY month parsing, null/orphan month handling, cross-FY comparisons, and HTML filter tests.
- [ ] Record findings in the unit-fix PR. Port only independently validated changes through a separate reviewed PR if still needed; never merge the branch wholesale.
