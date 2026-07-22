import io
import json
import unittest
from pathlib import Path

from mtagent.config import Config
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


class TestUnknownMethod(unittest.TestCase):
    def test_unknown_method_with_id_returns_method_not_found(self):
        resp = handle_message({"jsonrpc": "2.0", "id": 3, "method": "resources/list"}, _cfg())
        self.assertEqual(resp["error"]["code"], -32601)

    def test_unknown_notification_without_id_returns_nothing(self):
        resp = handle_message({"jsonrpc": "2.0", "method": "some/unknown/notification"}, _cfg())
        self.assertIsNone(resp)


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
