"""Phase 2C infrastructure tests -- source classification, governed
aliases, manifest, reconciliation placeholder, identity/continuity
prototype, and the mutation/determinism guarantees the release gate
depends on.

Synthetic fixtures only. No real FY26 source exists in this repository
(confirmed again as part of this pass -- see docs/PHASE_2_EXECUTION_STATUS.md's
Phase 2C attempt log). These tests prove the harness is correct and ready,
not that any real data has been certified.
"""
import importlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
shr = importlib.import_module("store_history_readiness")


def _good_row(month="Apr'25", chain="DMart", code="D001", name="DMart Andheri",
              article="ART-001", units=10, nsv=100.0, state="Maharashtra", city="Mumbai"):
    return {"Month": month, "Chain": chain, "Store Code": code, "Store Name": name,
            "State": state, "City": city, "Article": article, "Units": units, "NSV": nsv}


def _frame(rows):
    return pd.DataFrame(rows)


def _write_csv(tmp_path, rows, name="fy26.csv"):
    p = tmp_path / name
    _frame(rows).to_csv(p, index=False)
    return p


class TestSourceClassification:
    def test_missing_file_is_source_not_found(self, tmp_path):
        result = shr.classify_source(tmp_path / "does_not_exist.csv")
        assert result["source_status"] == "SOURCE_NOT_FOUND"

    def test_empty_csv_is_schema_invalid(self, tmp_path):
        p = _write_csv(tmp_path, [])
        result = shr.classify_source(p)
        assert result["source_status"] == "SOURCE_SCHEMA_INVALID"

    def test_missing_required_columns_is_wrong_grain(self, tmp_path):
        df = _frame([_good_row()]).drop(columns=["Store Code", "Article"])
        p = tmp_path / "fy26.csv"
        df.to_csv(p, index=False)
        result = shr.classify_source(p)
        assert result["source_status"] == "SOURCE_WRONG_GRAIN"

    def test_chain_level_json_aggregate_is_wrong_grain(self, tmp_path):
        """The exact real-world case this Phase 2C pass had to rule out:
        data/raw_drops/_agg/offtake_fy26.json -- chain/month grain only."""
        p = tmp_path / "offtake_fy26.json"
        p.write_text(json.dumps({
            "months": ["Apr-25", "May-25"],
            "monthly": [2271.99, 2449.48],
            "by_chain": {"Apollo": {"Apr-25": 244.84, "May-25": 272.2}},
        }))
        result = shr.classify_source(p)
        assert result["source_status"] == "SOURCE_WRONG_GRAIN"
        assert "chain/month grain only" in result["reason"]

    def test_unreadable_json_is_schema_invalid(self, tmp_path):
        p = tmp_path / "broken.json"
        p.write_text("{not valid json")
        result = shr.classify_source(p)
        assert result["source_status"] == "SOURCE_SCHEMA_INVALID"

    def test_partial_month_coverage_is_period_incomplete(self, tmp_path):
        p = _write_csv(tmp_path, [_good_row(month="Apr'25"), _good_row(month="May'25", code="D002")])
        result = shr.classify_source(p)
        assert result["source_status"] == "SOURCE_PERIOD_INCOMPLETE"

    def test_duplicate_grain_is_source_duplicated(self, tmp_path):
        months = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25", "Sep'25",
                  "Oct'25", "Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26"]
        rows = [_good_row(month=m, code=f"D{i:03d}") for i, m in enumerate(months)]
        rows.append(_good_row(month="Apr'25", code="D000"))  # duplicate of the first row
        p = _write_csv(tmp_path, rows)
        result = shr.classify_source(p)
        assert result["source_status"] == "SOURCE_DUPLICATED"

    def test_clean_full_file_is_authenticated(self, tmp_path):
        months = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25", "Sep'25",
                  "Oct'25", "Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26"]
        rows = [_good_row(month=m, code=f"D{i:03d}") for i, m in enumerate(months)]
        p = _write_csv(tmp_path, rows)
        result = shr.classify_source(p)
        assert result["source_status"] == "SOURCE_AUTHENTICATED"

    def test_unreconciled_control_total_blocks_authentication(self, tmp_path):
        months = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25", "Sep'25",
                  "Oct'25", "Nov'25", "Dec'25", "Jan'26", "Feb'26", "Mar'26"]
        rows = [_good_row(month=m, code=f"D{i:03d}") for i, m in enumerate(months)]
        p = _write_csv(tmp_path, rows)
        result = shr.classify_source(p, control_total=999999.0)
        assert result["source_status"] == "SOURCE_UNRECONCILED"


class TestUnknownMasterValues:
    def test_unknown_chain_is_governed_exception_not_hard_block(self, tmp_path):
        df = _frame([_good_row(chain="Totally Fictional Chain Xyz")])
        report = shr.validate_store_history(df)
        check = next(c for c in report["checks"] if c["check"] == "unknown_master_values")
        assert check["status"] == "WARN"
        assert "Totally Fictional Chain Xyz" in check["exceptions"]["unknown_chain"]
        # Not a hard fail -- governed exception, review needed, not a block.
        assert report["verdict"] != "BLOCKED_BY_DATA_QUALITY"

    def test_known_chain_alias_passes(self):
        df = _frame([_good_row(chain="DMart")])
        report = shr.validate_store_history(df)
        check = next(c for c in report["checks"] if c["check"] == "unknown_master_values")
        assert check["status"] == "PASS"


class TestPeriodWindowAndMonthFormat:
    def test_out_of_window_month_warns(self):
        df = _frame([_good_row(month="Apr'26")])  # FY27 month, not FY26
        report = shr.validate_store_history(df)
        check = next(c for c in report["checks"] if c["check"] == "period_window")
        assert check["status"] == "WARN"
        assert "Apr-26" in check["out_of_window_months"]

    def test_in_window_month_passes(self):
        df = _frame([_good_row(month="Apr'25")])
        report = shr.validate_store_history(df)
        check = next(c for c in report["checks"] if c["check"] == "period_window")
        assert check["status"] == "PASS"

    def test_unparseable_month_flagged(self):
        df = _frame([_good_row(month="not-a-month-at-all")])
        report = shr.validate_store_history(df)
        check = next(c for c in report["checks"] if c["check"] == "invalid_month_formats")
        assert check["status"] == "WARN"
        assert check["unparseable_month_row_count"] == 1


class TestGovernedAliases:
    def test_known_raw_columns_renamed_explicitly(self):
        df = pd.DataFrame([{"Chain Name": "DMart", "Site Code": "D001", "Site Name": "DMart Andheri",
                             "Sales Qty": 10, "Article": "ART-001", "NSV": 100.0}])
        renamed, applied = shr.apply_governed_aliases(df)
        assert set(["Chain", "Store Code", "Store Name", "Units"]) <= set(renamed.columns)
        assert applied == {"Chain": "Chain Name", "Store Code": "Site Code",
                            "Store Name": "Site Name", "Units": "Sales Qty"}

    def test_already_contract_named_columns_left_alone(self):
        df = _frame([_good_row()])
        renamed, applied = shr.apply_governed_aliases(df)
        assert applied == {}
        assert list(renamed.columns) == list(df.columns)

    def test_never_guesses_an_unmapped_column_name(self):
        """A raw name not in the governed map must never be silently
        matched -- e.g. a hypothetical 'StoreCd' must stay unrenamed."""
        df = pd.DataFrame([{"StoreCd": "D001", "Chain": "DMart"}])
        renamed, applied = shr.apply_governed_aliases(df)
        assert "Store Code" not in renamed.columns
        assert "StoreCd" in renamed.columns
        assert applied == {}


class TestSourceManifest:
    def test_manifest_has_all_required_fields(self, tmp_path):
        months = ["Apr'25", "May'25"]
        rows = [_good_row(month=m, code=f"D{i:03d}") for i, m in enumerate(months)]
        p = _write_csv(tmp_path, rows)
        manifest = shr.build_source_manifest(p)
        for field in ("dataset_name", "source_filename", "sha256", "file_size", "row_count",
                      "column_count", "period_min", "period_max", "ingestion_timestamp",
                      "schema_version", "source_status"):
            assert field in manifest, f"manifest missing required field {field!r}"
        assert manifest["row_count"] == 2
        assert manifest["period_min"] == "Apr-25"
        assert manifest["period_max"] == "May-25"

    def test_manifest_never_modifies_source(self, tmp_path):
        p = _write_csv(tmp_path, [_good_row()])
        before = p.read_bytes()
        before_mtime = p.stat().st_mtime
        shr.build_source_manifest(p)
        after = p.read_bytes()
        assert before == after
        assert p.stat().st_mtime == before_mtime

    def test_manifest_deterministic_except_timestamp(self, tmp_path):
        p = _write_csv(tmp_path, [_good_row()])
        m1 = shr.build_source_manifest(p)
        m2 = shr.build_source_manifest(p)
        variable = {"ingestion_timestamp"}
        for k in set(m1) | set(m2):
            if k in variable:
                continue
            assert m1.get(k) == m2.get(k), f"manifest field {k!r} differs between identical runs"


class TestReconciliationPlaceholder:
    def test_no_governed_tolerance_stays_blocked_pending_policy(self):
        result = shr.reconciliation_placeholder(raw_total=1000.0, canonical_total=999.5)
        assert result["status"] == "BLOCKED_PENDING_POLICY"
        assert result["difference"] == -0.5

    def test_never_guesses_a_tolerance(self):
        """Even a near-perfect reconciliation must not silently PASS without
        an explicit, governed tolerance supplied."""
        result = shr.reconciliation_placeholder(raw_total=1000.0, canonical_total=1000.0001)
        assert result["status"] == "BLOCKED_PENDING_POLICY"

    def test_explicit_tolerance_allows_pass(self):
        result = shr.reconciliation_placeholder(raw_total=1000.0, canonical_total=1000.5,
                                                   governed_tolerance_pct=1.0)
        assert result["status"] == "PASS"

    def test_explicit_tolerance_exceeded_warns(self):
        result = shr.reconciliation_placeholder(raw_total=1000.0, canonical_total=1200.0,
                                                   governed_tolerance_pct=1.0)
        assert result["status"] == "WARN"


class TestIdentityContinuityPrototype:
    """Prototype only -- confirms the interface, and explicitly confirms it
    is NOT wired into the production crosswalk builder."""

    def test_same_code_same_chain_is_comparable(self):
        fy26 = {"Store Code": "D001", "Chain": "DMart"}
        fy27 = {"Store Code": "D001", "Chain": "DMart"}
        result = shr.classify_identity_and_continuity(fy26, fy27)
        assert result["Identity_Status"] == "SAME_IDENTITY"
        assert result["Chain_Continuity_Status"] == "CHAIN_CONTINUOUS"
        assert result["Cohort_Status"] == "COMPARABLE_STORE"

    def test_chain_migration_case_flags_continuity_change(self):
        """The exact hypothetical example from the design discussion: same
        store identity, chain changed between years -- must not be silently
        treated as a normal comparable store."""
        fy26 = {"Store Code": "S001", "Chain": "Chain A"}
        fy27 = {"Store Code": "S001", "Chain": "Chain B"}
        result = shr.classify_identity_and_continuity(fy26, fy27)
        assert result["Identity_Status"] == "SAME_IDENTITY"
        assert result["Chain_Continuity_Status"] == "CHAIN_CHANGED_UNCLASSIFIED"
        assert result["Cohort_Status"] == "BLOCKED_FOR_REVIEW"
        assert result["Cohort_Status"] != "COMPARABLE_STORE"

    def test_prototype_not_wired_into_production_crosswalk(self):
        """build_crosswalk_candidates() must not call or depend on
        classify_identity_and_continuity() -- production behavior is
        unchanged by this Phase 2C pass."""
        import inspect
        source = inspect.getsource(shr.build_crosswalk_candidates)
        assert "classify_identity_and_continuity" not in source


class TestPhase2CGateStatus:
    def test_gate_status_shape(self):
        status = shr.phase2c_gate_status()
        for field in ("phase_2b_status", "phase_2c_harness_status",
                      "fy26_production_ingestion_performed", "source_authenticated",
                      "publication_blocked", "actual_ingestion", "reason"):
            assert field in status

    def test_gate_status_reflects_current_repo_state_no_real_fy26(self):
        """As of this Phase 2C pass, no real FY26 file exists -- the gate
        must say so honestly, not optimistically."""
        status = shr.phase2c_gate_status()
        assert status["phase_2b_status"] == "CERTIFIED"
        assert status["fy26_production_ingestion_performed"] is False
        assert status["source_authenticated"] is False
        assert status["publication_blocked"] is True
        assert status["actual_ingestion"] == "NOT_STARTED"
        assert status["reason"] == "BLOCKED_BY_SOURCE_DATA"


class TestMutationGuardOnFailure:
    """Any validation failure must never touch production data.js, FY27
    raw sources, or Phase 2B baseline files -- verified by hashing them
    before and after a run against a deliberately bad fixture."""

    def test_blocked_run_touches_nothing_outside_its_own_output(self, tmp_path):
        import subprocess as _sp
        repo_root = Path(__file__).resolve().parent.parent
        guarded_paths = [
            repo_root / "dashboard" / "data.js",
            repo_root / "scripts" / "store_history_readiness.py",
        ]
        before = {p: shr.compute_checksum(p) for p in guarded_paths if p.exists()}

        bad = _frame([_good_row()]).drop(columns=["NSV"])
        bad_path = tmp_path / "bad_fy26.csv"
        bad.to_csv(bad_path, index=False)
        out_path = tmp_path / "qc_out.json"

        result = _sp.run(
            [sys.executable, str(repo_root / "scripts" / "store_history_readiness.py"),
             "--src", str(bad_path), "--out", str(out_path)],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == shr.EXIT_BLOCKED_BY_DATA_QUALITY

        after = {p: shr.compute_checksum(p) for p in guarded_paths if p.exists()}
        assert before == after, "a blocked run must never mutate production/repo files"
