import io
import json
import unittest
from pathlib import Path

from mtagent.config import Config
from mtagent import mcp_server
from mtagent.mcp_server import TOOLS, handle_message, serve

REPO = Path(__file__).resolve().parents[2]


def _cfg(**kw) -> Config:
    return Config(repo_root=str(REPO), **kw)


class TestInitialize(unittest.TestCase):
    def test_initialize_returns_protocol_and_capabilities(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                "params": {}}, _cfg())
        self.assertEqual(resp["id"], 1)
        self.assertEqual(resp["result"]["protocolVersion"], "2024-11-05")
        self.assertIn("tools", resp["result"]["capabilities"])
        self.assertEqual(resp["result"]["serverInfo"]["name"], "mtagent")

    def test_initialized_notification_has_no_response(self):
        resp = handle_message({"jsonrpc": "2.0", "method": "notifications/initialized"}, _cfg())
        self.assertIsNone(resp)

    def test_ping(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 5, "method": "ping"}, _cfg())
        self.assertEqual(resp, {"jsonrpc": "2.0", "id": 5, "result": {}})


class TestToolsList(unittest.TestCase):
    def test_lists_every_registered_tool_with_valid_schema(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, _cfg())
        names = {t["name"] for t in resp["result"]["tools"]}
        self.assertEqual(names, set(TOOLS.keys()))
        for t in resp["result"]["tools"]:
            self.assertTrue(t["description"])
            self.assertEqual(t["inputSchema"]["type"], "object")
            self.assertIn("readOnlyHint", t["annotations"])

    def test_expected_tools_present(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}, _cfg())
        names = {t["name"] for t in resp["result"]["tools"]}
        for expected in ("ask", "status", "reconcile", "find", "worklog_tail",
                          "pbi_status", "pbi_build_dataset", "pbi_reconcile_model"):
            self.assertIn(expected, names)


class TestToolsCall(unittest.TestCase):
    def _call(self, name, arguments=None):
        return handle_message({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                                "params": {"name": name, "arguments": arguments or {}}}, _cfg())

    def test_unknown_tool_is_a_protocol_error(self):
        resp = self._call("does_not_exist")
        self.assertIn("error", resp)
        self.assertEqual(resp["error"]["code"], -32602)

    def test_find_real_repo_returns_hits(self):
        resp = self._call("find", {"query": "chain master"})
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("hits", payload)
        self.assertGreater(len(payload["hits"]), 0)
        self.assertIn("path", payload["hits"][0])

    def test_find_missing_required_arg_is_tool_error_not_crash(self):
        resp = self._call("find", {})
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("query", resp["result"]["content"][0]["text"])

    def test_status_returns_real_workflow_summary(self):
        resp = self._call("status")
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("completion_pct", payload)
        self.assertIn("current_phase", payload)

    def test_pbi_status_returns_real_build_status(self):
        resp = self._call("pbi_status")
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("build_id", payload)
        self.assertIn("completion_pct", payload)

    def test_pbi_build_dataset_validation_result_is_structured_not_a_json_string(self):
        # pbi_dataset.py stores validation_result as json.dumps(build_log)
        # (correct for WorkflowController's uniform str-typed field) -- the
        # MCP tool must present it as a real nested object, not JSON-inside-JSON.
        resp = self._call("pbi_build_dataset")
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIsInstance(payload["validation_result"], dict)
        self.assertIn("source_row_count", payload["validation_result"])

    def test_pbi_reconcile_model_validation_result_stays_plain_text(self):
        # This one really is a one-line human summary, not JSON -- must be
        # left alone (the normalizer only touches strings that look like JSON).
        resp = self._call("pbi_reconcile_model",
                           {"source": "PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_May_26.csv",
                            "build_dir": "agent/pbi_build/FY27_May26"})
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIsInstance(payload["validation_result"], str)

    def test_reconcile_runs_against_real_repo(self):
        resp = self._call("reconcile")
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("rows", payload)
        self.assertGreater(len(payload["rows"]), 0)

    def test_worklog_tail_returns_entries_list(self):
        resp = self._call("worklog_tail", {"n": 3})
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("entries", payload)

    def test_pbi_reconcile_model_missing_required_args_is_tool_error(self):
        resp = self._call("pbi_reconcile_model", {})
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("source", resp["result"]["content"][0]["text"])


class TestSafetyClassification(unittest.TestCase):
    """Every tool must be classified before a mutating tool is ever added --
    this pins the classification so a future addition can't silently skip it."""

    EXPECTED_CATEGORY = {
        "ask": "read_only", "status": "read_only", "reconcile": "read_only",
        "find": "read_only", "worklog_tail": "read_only", "pbi_status": "read_only",
        "pbi_build_dataset": "local_file_write", "pbi_reconcile_model": "local_file_write",
    }

    def test_every_tool_has_a_category_and_it_matches_expectation(self):
        for name, spec in TOOLS.items():
            self.assertIn("category", spec, name)
            self.assertEqual(spec["category"], self.EXPECTED_CATEGORY[name], name)

    def test_every_tool_has_side_effects_documented(self):
        for name, spec in TOOLS.items():
            self.assertIn("side_effects", spec, name)
            self.assertTrue(spec["side_effects"].strip(), name)

    def test_read_only_tools_have_readonly_annotation_true(self):
        for name, spec in TOOLS.items():
            if spec["category"] == "read_only":
                self.assertTrue(spec["annotations"]["readOnlyHint"], name)

    def test_local_file_write_tools_have_readonly_annotation_false(self):
        for name, spec in TOOLS.items():
            if spec["category"] == "local_file_write":
                self.assertFalse(spec["annotations"]["readOnlyHint"], name)

    def test_no_tool_is_marked_destructive(self):
        # None of the 8 current tools delete or irreversibly change anything
        # -- both categories add/overwrite their own generated output only.
        for name, spec in TOOLS.items():
            self.assertFalse(spec["annotations"]["destructiveHint"], name)

    def test_no_state_mutation_or_high_impact_tools_exist_yet(self):
        # This is the explicit scope boundary: no apply-alias, mark-complete,
        # compile-model, or git operation is exposed. If this test needs
        # updating, that's a deliberate scope expansion, not an accident.
        categories = {spec["category"] for spec in TOOLS.values()}
        self.assertEqual(categories, {"read_only", "local_file_write"})


class TestUnknownMethod(unittest.TestCase):
    def test_unknown_method_with_id_returns_method_not_found(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 3, "method": "resources/list"}, _cfg())
        self.assertEqual(resp["error"]["code"], -32601)

    def test_unknown_notification_without_id_returns_nothing(self):
        resp = handle_message({"jsonrpc": "2.0", "method": "some/unknown/notification"}, _cfg())
        self.assertIsNone(resp)

    def test_message_with_no_method_key_at_all_is_a_clean_error(self):
        # A request that's missing 'method' entirely -- msg.get('method') is
        # None, must not raise, must round-trip the id it did carry.
        resp = handle_message({"jsonrpc": "2.0", "id": 7}, _cfg())
        self.assertEqual(resp["error"]["code"], -32601)
        self.assertEqual(resp["id"], 7)


class TestUnusualRequestIds(unittest.TestCase):
    """JSON-RPC allows id to be a string, a number, or null -- never assume
    it's always an int."""

    def test_string_id_is_echoed_back_exactly(self):
        resp = handle_message({"jsonrpc": "2.0", "id": "req-abc-123", "method": "ping"}, _cfg())
        self.assertEqual(resp["id"], "req-abc-123")

    def test_float_id_is_echoed_back_exactly(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 3.14, "method": "ping"}, _cfg())
        self.assertEqual(resp["id"], 3.14)

    def test_explicit_null_id_still_gets_a_response_unlike_a_true_notification(self):
        # 'id': null (key PRESENT, value null) is a request, not a
        # notification -- must NOT be silently swallowed like a message
        # with the 'id' key absent entirely.
        resp = handle_message({"jsonrpc": "2.0", "id": None, "method": "unknown/thing"}, _cfg())
        self.assertIsNotNone(resp)
        self.assertIn("error", resp)
        self.assertIsNone(resp["id"])

    def test_true_notification_with_no_id_key_gets_no_response(self):
        resp = handle_message({"jsonrpc": "2.0", "method": "unknown/thing"}, _cfg())
        self.assertIsNone(resp)

    def test_non_dict_top_level_message_does_not_crash_the_server(self):
        # A syntactically valid JSON line that isn't a JSON-RPC object at all
        # (e.g. a bare array) must degrade to an internal-error response
        # inside serve(), never propagate an unhandled exception.
        inp = io.StringIO("[1, 2, 3]\n")
        out = io.StringIO()
        serve(_cfg(), in_stream=inp, out_stream=out)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        resp = json.loads(lines[0])
        self.assertIn("error", resp)
        self.assertIsNone(resp["id"])


class TestNonSerializableToolResults(unittest.TestCase):
    """A tool handler can return values json.dumps can't handle directly
    (Path objects, sets, ...) -- default=str must absorb them without
    crashing the response path, and the genuinely-unstringifiable case must
    degrade to isError, never an unhandled exception."""

    def setUp(self):
        self._orig_tools = dict(TOOLS)
        self.addCleanup(lambda: TOOLS.clear() or TOOLS.update(self._orig_tools))

    def test_path_and_set_values_are_stringified_not_crashing(self):
        TOOLS["_test_odd_values"] = {
            "description": "test", "inputSchema": {"type": "object", "properties": {}},
            "handler": lambda cfg, args: {"path": Path("/tmp/x"), "tags": {"a", "b"}},
        }
        resp = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {"name": "_test_odd_values", "arguments": {}}}, _cfg())
        self.assertFalse(resp["result"]["isError"])
        payload = json.loads(resp["result"]["content"][0]["text"])
        self.assertIn("/tmp/x", payload["path"])

    def test_truly_unstringifiable_result_becomes_isError_not_a_crash(self):
        class Cursed:
            def __str__(self):
                raise RuntimeError("cannot stringify me")

        TOOLS["_test_cursed"] = {
            "description": "test", "inputSchema": {"type": "object", "properties": {}},
            "handler": lambda cfg, args: {"bad": Cursed()},
        }
        resp = handle_message({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {"name": "_test_cursed", "arguments": {}}}, _cfg())
        self.assertTrue(resp["result"]["isError"])
        self.assertIn("RuntimeError", resp["result"]["content"][0]["text"])


class TestBrokenPipe(unittest.TestCase):
    """If the client disconnects mid-response (broken pipe / closed stdout),
    the server must exit the loop quietly, not raise an unhandled exception
    that would print a Python traceback to stderr."""

    class _DyingStream:
        def write(self, _data):
            raise BrokenPipeError("client hung up")

        def flush(self):
            pass

    def test_broken_pipe_on_write_stops_the_loop_without_raising(self):
        inp = io.StringIO(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
                           + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}) + "\n")
        try:
            serve(_cfg(), in_stream=inp, out_stream=self._DyingStream())
        except BrokenPipeError:
            self.fail("serve() must absorb a broken pipe, not propagate it")

    def test_write_line_helper_returns_false_instead_of_raising(self):
        ok = mcp_server._write_line(self._DyingStream(), {"jsonrpc": "2.0", "id": 1, "result": {}})
        self.assertFalse(ok)


class TestServeLoop(unittest.TestCase):
    def test_malformed_line_yields_parse_error_and_loop_continues(self):
        inp = io.StringIO("not json at all\n"
                           + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n")
        out = io.StringIO()
        serve(_cfg(), in_stream=inp, out_stream=out)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        first = json.loads(lines[0])
        self.assertEqual(first["error"]["code"], -32700)
        second = json.loads(lines[1])
        self.assertEqual(second["result"], {})

    def test_blank_lines_are_skipped(self):
        inp = io.StringIO("\n\n" + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n\n")
        out = io.StringIO()
        serve(_cfg(), in_stream=inp, out_stream=out)
        lines = [l for l in out.getvalue().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)

    def test_notification_produces_no_output_line(self):
        inp = io.StringIO(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        out = io.StringIO()
        serve(_cfg(), in_stream=inp, out_stream=out)
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
