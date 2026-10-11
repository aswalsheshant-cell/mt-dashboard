"""b5_execute_queries.py with a fake HTTP layer: no network, no token, no workspace."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))
import b5_evidence as b5  # noqa: E402
import b5_execute_queries as ex  # noqa: E402
from test_b5_evidence import good_results  # noqa: E402

A = SimpleNamespace(workspace_id="ws-1", dataset_id="ds-1", published_from_sha="abc1234", model_file="")


def _rest(tbl):
    """Engine table -> ExecuteQueries response (rows are dicts keyed '[Col]')."""
    rows = [{"[%s]" % c: v for c, v in zip(tbl["columns"], r)} for r in tbl["rows"]]
    return {"results": [{"tables": [{"rows": rows}]}]}


def fake_send(refresh_status="Completed", fail_key=None):
    by_query = {b5._norm_q(q): k for k, q in b5.collect_queries().items()}
    good = good_results()

    def send(method, url, token, body=None):
        assert token == "tok"
        if method == "GET" and url.endswith("/datasets/ds-1"):
            return 200, {"name": "ModernTrade_Model"}, {}
        if method == "GET" and "/refreshes" in url:
            return 200, {"value": [{"status": refresh_status, "endTime": "2026-10-11T08:00:00Z"}]}, {}
        key = by_query[b5._norm_q(body["queries"][0]["query"])]
        if key == fail_key:
            return 400, {"error": {"code": "BadRequest"}}, {}
        return 200, _rest(good[key]), {}
    return send


def doc(**kw):
    return ex.build_doc("tok", A, send=fake_send(**kw), sleep=lambda s: None, git=lambda: ("abc1234", False))


def test_service_run_passes_every_required_row(tmp_path):
    d = doc()
    p = b5.write_evidence(d, raw_sha256="0" * 64, evidence_dir=tmp_path, run_by="t", refreshed=True,
                          fy_parser_failures=0, attested_by="t")
    text = p.read_text(encoding="utf-8")
    assert "Power BI Service" in text and "LIVE SERVICE" in text and "no Desktop" in text
    rows = b5.evaluate_all(d, manual_fy_failures=0, attested_by="t")
    assert all(rows[r].status == "PASS" for r in b5.REQUIRED_PASS)


def test_only_governed_queries_are_sent():
    d = doc()
    assert d["queries"] == b5.collect_queries() and set(d["cases"]) == set(d["queries"])


def test_unfinished_refresh_is_refused(tmp_path):
    with pytest.raises(b5.EvidenceRefused, match="refresh"):
        b5.write_evidence(doc(refresh_status="Failed"), raw_sha256="0" * 64, evidence_dir=tmp_path)


def test_model_built_from_another_sha_is_refused(tmp_path):
    d = doc()
    d["meta"]["published_from_sha"] = "ffffff0"
    with pytest.raises(b5.EvidenceRefused, match="republish"):
        b5.write_evidence(d, raw_sha256="0" * 64, evidence_dir=tmp_path)


def test_a_failed_query_reads_not_run_never_pass():
    d = doc(fail_key="cm2:5:2")
    assert "cm2:5:2" in d["errors"]
    assert b5.evaluate_all(d, manual_fy_failures=0, attested_by="t")["5"].status != "PASS"


def test_service_meta_cannot_skip_required_fields(tmp_path):
    d = doc()
    del d["meta"]["workspace_id"]
    with pytest.raises(b5.EvidenceRefused):
        b5.write_evidence(d, raw_sha256="0" * 64, evidence_dir=tmp_path)


def test_dax_error_in_a_200_response_is_raised():
    send = lambda m, u, t, b=None: (200, {"results": [{"error": {"code": "x"}}]}, {})  # noqa: E731
    with pytest.raises(RuntimeError):
        ex.run_query("tok", "w", "d", "EVALUATE ROW(\"a\",1)", send, lambda s: None)


def test_throttling_is_retried():
    calls = []

    def send(m, u, t, b=None):
        calls.append(1)
        return (429, None, {"Retry-After": "1"}) if len(calls) < 3 else (200, _rest({"columns": ["a"], "rows": [[1]]}), {})
    assert ex.run_query("tok", "w", "d", "q", send, lambda s: None)["rows"] == [{"[a]": 1}] and len(calls) == 3


def test_token_is_never_written_to_results(tmp_path):
    assert "tok" not in json.dumps(doc(), default=str)


def test_missing_token_stops(monkeypatch, capsys):
    monkeypatch.delenv("PBI_ACCESS_TOKEN", raising=False)
    assert ex.main(["--workspace-id", "w", "--dataset-id", "d", "--published-from-sha", "x"]) == 2
