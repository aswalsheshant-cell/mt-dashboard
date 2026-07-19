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
            actual_result=PARTIAL,
            evidence_location="mechanism implemented and unit-tested; NOT yet run against real June'26 "
                               "source data -- no June'26 (2026) source files exist in this environment "
                               "(see JUN26-V3 in the backlog table)",
        ),
        TraceabilityRow(
            rule_id="R2", business_rule="NSV reconciliation",
            risk_controlled="Reporting a build whose NSV doesn't match source",
            implementation_file="agent/mtagent/validators/business_validation.py",
            function_or_module="reconcile_metric()",
            test_file="agent/tests/test_business_validation.py",
            test_name="TestActivityCannotEqualSuccess.test_nsv_mismatch_fails_even_though_activity_completed",
            expected_behavior="a diff outside tolerance fails, even if the run technically completed",
            actual_result=PARTIAL,
            evidence_location="mechanism implemented and unit-tested; not yet applied to real June'26 NSV totals "
                               "(no June'26 source data present)",
        ),
        TraceabilityRow(
            rule_id="R3", business_rule="Qty reconciliation",
            risk_controlled="Reporting a build whose Qty doesn't match source",
            implementation_file="agent/mtagent/validators/business_validation.py",
            function_or_module="reconcile_metric() (same function, applied to Qty)",
            test_file="agent/tests/test_business_validation.py",
            test_name="TestActivityCannotEqualSuccess.test_exact_match_within_tolerance_passes",
            expected_behavior="Qty diff within tolerance passes; outside tolerance fails",
            actual_result=PARTIAL,
            evidence_location="mechanism implemented and unit-tested; not yet applied to real June'26 Qty totals",
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
            expected_behavior="canonical entry 'RMT Sancus' exists and distributor rows resolve to it",
            actual_result=PARTIAL,
            evidence_location="ChainMaster.csv row: 'RMT-Sancus,Sancus,Distributor-MT,South-1,Yes,Yes' -- NOTE: "
                               "canonical spelling is 'RMT-Sancus' (hyphen), not 'RMT Sancus' (space) as the "
                               "business decision was recorded; ChainAliases.csv confirms "
                               "'Sancus(Rmt) -> RMT-Sancus, business-confirmed 2026-07-13'. HOWEVER "
                               "ChainAccount_Mapping_NeedsReview.csv still has 9 rows for 'Sancus Networks "
                               "Private Limited-RMT' marked Validation Status 'Pending' / 'Needs Check' -- the "
                               "canonical master entry exists but distributor-level resolution is not fully closed",
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
            expected_behavior="canonical entry 'Sasta Sundar' exists",
            actual_result=PARTIAL,
            evidence_location="ChainMaster.csv row: 'SastaSundar,SastaSundar,Pharmacy,East,Yes,Yes' -- NOTE: "
                               "actual canonical spelling is 'SastaSundar' (no space, one token), not "
                               "'Sasta Sundar' (with a space) as the business decision was recorded. Also present "
                               "in ShipToMaster.csv distributor routing list. The chain exists and is active; "
                               "only the exact spelling differs from what was decided -- flagged for confirmation, "
                               "not treated as resolved as originally worded",
        ),
        TraceabilityRow(
            rule_id="R10", business_rule="Reliance Retail-(Azorte) -> Reliance Azorte",
            risk_controlled="A distinct beauty-retail banner being silently merged into Reliance Retail",
            implementation_file="PowerBI/SeedData/Masters/ChainMaster.csv",
            function_or_module="n/a (master data, not code)",
            test_file="n/a", test_name="n/a",
            expected_behavior="canonical entry 'Reliance Azorte' exists, parent Reliance Retail, separate from it",
            actual_result=PARTIAL,
            evidence_location="ChainMaster.csv row: 'Azorte,Reliance,Beauty Retail,Pan India,Yes,' -- NOTE: "
                               "actual canonical chain name is 'Azorte' (not 'Reliance Azorte'), and the Account "
                               "column reads 'Reliance' (not 'Reliance Retail'). The chain IS kept distinct from "
                               "'Reliance Retail' as a separate row, which satisfies the core decision, but the "
                               "exact naming differs from how the decision was recorded -- flagged for confirmation",
        ),
        TraceabilityRow(
            rule_id="R11", business_rule="Reliance Azorte retained as separate SIS banner",
            risk_controlled="Azorte's SIS reporting treatment being silently dropped",
            implementation_file="PowerBI/SeedData/Masters/ChannelMap_Chain.csv",
            function_or_module="n/a (master data, not code)",
            test_file="n/a", test_name="n/a",
            expected_behavior="Azorte's channel is tagged SIS in ChannelMap_Chain.csv",
            actual_result=FAIL,
            evidence_location="ChannelMap_Chain.csv row: 'Azorte,MT,default channel — edit if chain is SIS/EB2B' "
                               "-- the row is still on the DEFAULT channel; nobody has actually edited it to SIS "
                               "despite the decision that Azorte's Business Format is SIS. This is a real, "
                               "concrete gap between the recorded decision and the master data, found by this "
                               "traceability check, not by assumption",
        ),
        TraceabilityRow(
            rule_id="R12", business_rule="June'26 partial-month handling",
            risk_controlled="A provisional month being silently presented as closed",
            implementation_file="agent/mtagent/validators/business_validation.py",
            function_or_module="period_completeness_check()",
            test_file="agent/tests/test_business_validation.py",
            test_name="TestPeriodCompleteness (3 tests)",
            expected_behavior="is_partial_period=True + treated_as_closed=True fails by name",
            actual_result=PARTIAL,
            evidence_location="mechanism implemented and unit-tested; not yet applied to real June'26 data "
                               "since no June'26 build exists",
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
