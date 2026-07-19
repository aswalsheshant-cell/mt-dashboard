"""The 16 June'26 rules from the Master Prompt, evaluated against REAL
repo evidence gathered by direct inspection of PowerBI/SeedData/ and
agent/tests/ -- not asserted, not fabricated. Several rows below are
PARTIAL or NOT_EVALUATED on purpose: that is the honest result, not a
placeholder to fill in later.
"""
from __future__ import annotations

from .traceability import TraceabilityRow, PASS, FAIL, PARTIAL, NOT_EVALUATED


def build_june26_traceability() -> list:
    return [
        TraceabilityRow(
            rule_id="R1", business_rule="Source row count preservation",
            risk_controlled="Silent row drops or duplication during transformation",
            implementation_file="agent/mtagent/validators/business_validation.py",
            function_or_module="reconcile_counts()",
            test_file="agent/tests/test_business_validation.py",
            test_name="TestRowCountAndMapping.test_row_count_mismatch_fails",
            expected_behavior="source_n != output_n fails the check by name",
            actual_result=PASS,
            evidence_location="run for real 2026-07-19 against MTD_Primary_Jun_26.csv (23,193 rows): "
                               "21,283 Direct + 1,907 Distributor-split + 2 no-Cont%-exception + 1 blank-ShipTo "
                               "= 23,193 accounted for, 0 silently dropped. See "
                               "agent/pbi_build/FY27_Jun26/Reconciliation_Report_Jun26.md",
        ),
        TraceabilityRow(
            rule_id="R2", business_rule="NSV reconciliation",
            risk_controlled="Reporting a build whose NSV doesn't match source",
            implementation_file="agent/mtagent/validators/business_validation.py",
            function_or_module="reconcile_metric()",
            test_file="agent/tests/test_business_validation.py",
            test_name="TestActivityCannotEqualSuccess.test_nsv_mismatch_fails_even_though_activity_completed",
            expected_behavior="a diff outside tolerance fails, even if the run technically completed",
            actual_result=PASS,
            evidence_location="run for real 2026-07-19: raw primary NSV Rs 41,67,37,933.62 vs allocated "
                               "(Rs 41,67,22,597.99) + disclosed exceptions (Rs 15,335.63) = Rs 41,67,37,933.62, "
                               "diff Rs 0.00 at full float precision. See "
                               "agent/pbi_build/FY27_Jun26/Reconciliation_Report_Jun26.md",
        ),
        TraceabilityRow(
            rule_id="R3", business_rule="Qty reconciliation",
            risk_controlled="Reporting a build whose Qty doesn't match source",
            implementation_file="agent/mtagent/validators/business_validation.py",
            function_or_module="reconcile_metric() (same function, applied to Qty)",
            test_file="agent/tests/test_business_validation.py",
            test_name="TestActivityCannotEqualSuccess.test_exact_match_within_tolerance_passes",
            expected_behavior="Qty diff within tolerance passes; outside tolerance fails",
            actual_result=PASS,
            evidence_location="run for real 2026-07-19: raw primary Qty 2,345,731 vs allocated (2,345,665.00) "
                               "+ disclosed exceptions (66.00) = 2,345,731.00, diff 0.00. See "
                               "agent/pbi_build/FY27_Jun26/Reconciliation_Report_Jun26.md",
        ),
        TraceabilityRow(
            rule_id="R4", business_rule="Canonical chain validation",
            risk_controlled="A mapping target that isn't an approved chain being silently accepted",
            implementation_file="agent/mtagent/validators/business_validation.py",
            function_or_module="mapping_validation_check()",
            test_file="agent/tests/test_business_validation.py",
            test_name="TestRowCountAndMapping.test_mapping_not_in_known_canonicals_fails_but_is_named",
            expected_behavior="unknown canonical is flagged by name, never silently accepted",
            actual_result=PASS,
            evidence_location="agent/tests/test_business_validation.py::TestRowCountAndMapping (2 tests, both pass)",
        ),
        TraceabilityRow(
            rule_id="R5", business_rule="Prevention of store-level chain explosion",
            risk_controlled="The real Reliance bug: a lookup exploding one chain into ~130 fake per-store chains",
            implementation_file="agent/mtagent/controller.py; agent/mtagent/validators/business_validation.py",
            function_or_module="_STORE_CODE_SHAPE regex (controller.py); distinct_value_check()",
            test_file="agent/tests/test_controller.py; agent/tests/test_business_validation.py",
            test_name="TestStoreNamesCannotBecomeChains (4 tests); TestDistinctValueExplosion (3 tests)",
            expected_behavior="a store/ship-to-shaped canonical target is refused at interpret time; "
                               "a 45->130 count jump fails distinct_value_check",
            actual_result=PASS,
            evidence_location="agent/tests/test_controller.py::TestStoreNamesCannotBecomeChains -- includes "
                               "'Reliance Retail Limited_FRDI' and 'V-Mart Retail Limited-148-BIRSA' as real "
                               "regression cases matching the actual incident shape",
        ),
        TraceabilityRow(
            rule_id="R6", business_rule="Approved alias scope (e.g. secondary-file-only)",
            risk_controlled="An alias intended for one file silently applying pipeline-wide",
            implementation_file="agent/mtagent/controller.py",
            function_or_module="_apply_alias()",
            test_file="agent/tests/test_controller.py",
            test_name="TestStoreNamesCannotBecomeChains.test_apply_alias_to_a_real_chain_is_recorded_cleanly",
            expected_behavior="Scope column recorded exactly as stated in the instruction",
            actual_result=PASS,
            evidence_location="ControllerAlias_<scope>.csv Scope column, verified by the cited test",
        ),
        TraceabilityRow(
            rule_id="R7", business_rule="Sancus -> RMT Sancus",
            risk_controlled="A distributor-routed chain left unmapped or wrongly named",
            implementation_file="PowerBI/SeedData/Masters/ChainMaster.csv; ChainAliases.csv",
            function_or_module="n/a (master data, not code)",
            test_file="n/a", test_name="n/a",
            expected_behavior="a canonical Sancus entry exists and distributor rows resolve to it",
            actual_result=PASS,
            evidence_location="ChainMaster.csv row: 'RMT-Sancus,Sancus,Distributor-MT,South-1,Yes,Yes'; "
                               "ChainAliases.csv: 'Sancus(Rmt) -> RMT-Sancus, business-confirmed 2026-07-13'. "
                               "RESOLVED (analyst review): 'RMT-Sancus' (hyphen) is the master file's spelling "
                               "and is used consistently across ChainMaster.csv/ChainAliases.csv/"
                               "ChannelMap_Chain.csv -- the earlier decision text ('RMT Sancus', with a space) "
                               "was informal phrasing of the same confirmed decision, not a separate unresolved "
                               "spelling. Treated as canonical; no data change made. UPDATE 2026-07-19: the "
                               "distributor-level split question (previously the open part of this rule) is now "
                               "answered for June'26 specifically, from real data: "
                               "secondary_distributor_chain_Jun_26.csv's 'Sancus Networks Private Limited-RMT' "
                               "rows give RMT-Sancus 78.3%, More Retail 12.5%, Vishal Mega Mart 9.2% (no Deal "
                               "Share/Medanta activity this specific month -- plausible, not an error). The older "
                               "9 rows in ChainAccount_Mapping_NeedsReview.csv covering Mar'25-May'26 remain "
                               "'Pending' and are a separate, multi-month question this doesn't resolve.",
        ),
        TraceabilityRow(
            rule_id="R8", business_rule="Apollo Healthco -> Apollo",
            risk_controlled="A direct-ship account fragmenting into a separate chain from its parent",
            implementation_file="PowerBI/SeedData/Mapping/ChainAccount_Mapping_Inferred.csv; "
                                 "PowerBI/SeedData/Masters/ChainMaster.csv",
            function_or_module="n/a (master data, not code)",
            test_file="n/a", test_name="n/a",
            expected_behavior="Apollo Healthco rows resolve to canonical chain 'Apollo'",
            actual_result=PASS,
            evidence_location="ChainAccount_Mapping_Inferred.csv: 'Apollo,APOLLO HEALTHCO LIMITED-WB,...,"
                               "Validated (Cross-Ref),Apollo Healthco,Apollo Healthco,Merge,exact match on "
                               "Ship-To Name against Confirmed row in CustomerCode_Zone_State_Mapping.csv "
                               "(Customer Code 1102407),...,2026-07-14'; ChainMaster.csv confirms canonical "
                               "'Apollo' exists",
        ),
        TraceabilityRow(
            rule_id="R9", business_rule="Sasta Sunder -> Sasta Sundar",
            risk_controlled="A misspelled raw label failing to roll up to its chain",
            implementation_file="PowerBI/SeedData/Masters/ChainMaster.csv",
            function_or_module="n/a (master data, not code)",
            test_file="n/a", test_name="n/a",
            expected_behavior="a canonical Sasta Sundar entry exists",
            actual_result=PASS,
            evidence_location="ChainMaster.csv row: 'SastaSundar,SastaSundar,Pharmacy,East,Yes,Yes'; also present "
                               "consistently in ChannelMap_Chain.csv and ShipToMaster.csv's distributor routing "
                               "list. RESOLVED (analyst review): 'SastaSundar' (one token, no space) is the "
                               "master file's spelling, used consistently across all 3 files that reference it -- "
                               "the earlier decision text ('Sasta Sundar', with a space) was informal phrasing of "
                               "the same confirmed decision. Treated as canonical; no data change made.",
        ),
        TraceabilityRow(
            rule_id="R10", business_rule="Reliance Retail-(Azorte) -> Reliance Azorte",
            risk_controlled="A distinct beauty-retail banner being silently merged into Reliance Retail",
            implementation_file="PowerBI/SeedData/Masters/ChainMaster.csv",
            function_or_module="n/a (master data, not code)",
            test_file="n/a", test_name="n/a",
            expected_behavior="a canonical Azorte entry exists, parent Reliance, separate from Reliance Retail",
            actual_result=PASS,
            evidence_location="ChainMaster.csv row: 'Azorte,Reliance,Beauty Retail,Pan India,Yes,'. RESOLVED "
                               "(analyst review): 'Azorte' (chain) / 'Reliance' (account) is the master file's "
                               "naming, and it is what PowerBI/docs/SIS_Reconciliation.md itself uses when citing "
                               "the same chain ('Azorte (Rs68.09 L) is a Reliance-owned beauty retail format') -- "
                               "the earlier decision text ('Reliance Azorte'/'Reliance Retail') described the same "
                               "chain informally, not a separate required rename. The core requirement -- Azorte "
                               "kept as its own row, never merged into Reliance Retail -- IS satisfied. Treated as "
                               "canonical; no data change made.",
        ),
        TraceabilityRow(
            rule_id="R11", business_rule="Reliance Azorte retained as separate SIS banner",
            risk_controlled="Azorte's SIS reporting treatment being silently dropped or mis-tagged",
            implementation_file="PowerBI/SeedData/Masters/ChannelMap_Chain.csv; "
                                 "PowerBI/docs/SIS_Reconciliation.md",
            function_or_module="n/a (master data, not code)",
            test_file="n/a", test_name="n/a",
            expected_behavior="Azorte's SIS treatment is confirmed and consistently applied",
            actual_result=PARTIAL,
            evidence_location="CORRECTED FINDING (analyst re-review -- an earlier pass on this row was WRONG and "
                               "is superseded here): ChannelMap_Chain.csv row 'Azorte,MT,default channel — edit "
                               "if chain is SIS/EB2B' looked like a forgotten edit at first glance, but "
                               "'SIS' has NEVER appeared as a Channel value anywhere in that file (only 'MT' and "
                               "'EB2B' exist) -- writing 'SIS' in would introduce a brand-new category with no "
                               "confirmed downstream handling. More importantly, PowerBI/docs/SIS_Reconciliation.md "
                               "(the actual primary-side SIS investigation, RESOLVED 2026-07-03 at Rs250.17 L) "
                               "explicitly lists Azorte's channel as an OPEN, WEAKER hypothesis, not a settled "
                               "fact: 'Azorte (Rs68.09 L) is a Reliance-owned beauty retail format that could "
                               "arguably be EB2B depending on the business's channel definition.' Primary-side SIS "
                               "is computed directly from primary_article.xlsb's own Channel column, NOT from "
                               "ChannelMap_Chain.csv, which is a separate, offtake-side mechanism. Conclusion: "
                               "this is not an unapplied edit, it is a genuinely open channel-classification "
                               "question the business has not closed -- I did NOT edit ChannelMap_Chain.csv, "
                               "since doing so would be an uninformed guess on a question already flagged as "
                               "unresolved elsewhere in the repo.",
        ),
        TraceabilityRow(
            rule_id="R12", business_rule="June'26 partial-month handling",
            risk_controlled="A provisional month being silently presented as closed",
            implementation_file="agent/mtagent/validators/business_validation.py",
            function_or_module="period_completeness_check()",
            test_file="agent/tests/test_business_validation.py",
            test_name="TestPeriodCompleteness (3 tests)",
            expected_behavior="is_partial_period=True + treated_as_closed=True fails by name",
            actual_result=PASS,
            evidence_location="applied for real 2026-07-19 to the June'26 allocation run: "
                               "period_completeness_check('june26', is_partial_period=True, "
                               "treated_as_closed=False) -> passed=True. Recorded explicitly in "
                               "agent/pbi_build/FY27_Jun26/Reconciliation_Report_Jun26.md as Partial/Provisional, "
                               "not closed-month performance.",
        ),
        TraceabilityRow(
            rule_id="R13", business_rule="No automatic commit or push",
            risk_controlled="An agent silently altering shared git history",
            implementation_file="agent/mtagent/controller.py",
            function_or_module="execute() -- commit/push branch",
            test_file="agent/tests/test_controller.py",
            test_name="TestNoCommitOrPushWithoutApproval (3 tests)",
            expected_behavior="commit/push always BLOCKED without approved=True; never executes git even when approved",
            actual_result=PASS,
            evidence_location="agent/tests/test_controller.py::TestNoCommitOrPushWithoutApproval -- includes "
                               "explicit assertion that no .git operation occurs even with approved=True",
        ),
        TraceabilityRow(
            rule_id="R14", business_rule="No release when critical checks fail",
            risk_controlled="An unreconciled or unvalidated output reaching APPROVED_FOR_SHARING",
            implementation_file="agent/mtagent/validators/release_gate.py",
            function_or_module="evaluate_release()",
            test_file="agent/tests/test_release_gate.py",
            test_name="TestUnreconciledFileCannotBeShared; TestPartialMonthCannotBeClosed; "
                       "TestVisuallyBrokenButNumericallyCorrectStaysDraft",
            expected_behavior="any failing checklist item forces DRAFT, even with human_approved=True",
            actual_result=PASS,
            evidence_location="agent/tests/test_release_gate.py -- 5 tests across 3 classes, all passing",
        ),
        TraceabilityRow(
            rule_id="R15", business_rule="Hidden-sheet redaction check",
            risk_controlled="A confidential hidden sheet or comment reaching an external share",
            implementation_file="agent/mtagent/validators/release_gate.py",
            function_or_module="redaction_scan()",
            test_file="agent/tests/test_release_gate.py",
            test_name="TestConfidentialHiddenSheetBlocksSharing (2 tests)",
            expected_behavior="a hidden sheet with confidential content is named in the scan's issues list",
            actual_result=NOT_EVALUATED,
            evidence_location="tests exist and are real (not stubs), but SKIPPED in this environment because "
                               "openpyxl is not installed and this sandbox has no network access to install it "
                               "(see ENV-1 in the backlog table). The no-openpyxl degrade path itself IS proven: "
                               "TestRedactionScanDegradesGracefullyWithoutOpenpyxl passes",
        ),
        TraceabilityRow(
            rule_id="R16", business_rule="Output version and lineage requirement",
            risk_controlled="An approved file with no way to tell which run produced it",
            implementation_file="agent/mtagent/validators/release_gate.py",
            function_or_module="evaluate_release() (version_and_timestamp_added); build_version_filename()",
            test_file="agent/tests/test_release_gate.py",
            test_name="TestNoVersionCannotBeApproved (2 tests)",
            expected_behavior="missing version/timestamp blocks APPROVED_FOR_SHARING; filename avoids "
                               "'final_final' style naming",
            actual_result=PASS,
            evidence_location="agent/tests/test_release_gate.py::TestNoVersionCannotBeApproved -- both tests pass "
                               "(corrected in this session: these were previously mis-gated behind an "
                               "unnecessary openpyxl skip that has now been removed, since neither test needs it)",
        ),
    ]
