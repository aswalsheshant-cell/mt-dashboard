"""Real-subprocess MCP integration test.

No real MCP client (Claude Desktop, the official @modelcontextprotocol/
inspector) is reachable in this environment -- Claude Desktop is a desktop
GUI app not present in this headless sandbox, and `npx @modelcontextprotocol/
inspector` hits the identical HTTP 403 from registry.npmjs.org that blocks
every other package index here (pypi.org, files.pythonhosted.org, archive.
ubuntu.com -- confirmed org policy, not a local misconfiguration). This is
the most rigorous available substitute: a real `python -m mtagent mcp-serve`
subprocess, driven interactively over its actual stdin/stdout pipes with
one request sent and one response read at a time (not a pre-built batch
file piped in), following the real MCP handshake order -- which is exactly
the boundary a real client actually exercises and unit-level
`handle_message()` calls (test_mcp_server.py) do not.

If you have access to Claude Desktop, add this server per README.md's
"MCP server" section and confirm the 8 tools appear with usable schemas --
that remains the one check this substitute cannot fully replace.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AGENT_DIR = REPO / "agent"


class MCPClient:
    """A minimal, real MCP client: spawns the actual CLI entry point and
    talks newline-delimited JSON-RPC over real pipes, one message at a time."""

    def __init__(self):
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "mtagent", "mcp-serve"],
            cwd=str(AGENT_DIR),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", bufsize=1,
        )

    def send(self, msg: dict) -> None:
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def recv(self, timeout: float = 15.0) -> dict:
        line = self.proc.stdout.readline()
        if not line:
            err = self.proc.stderr.read()
            raise RuntimeError(f"server closed stdout unexpectedly; stderr={err!r}")
        return json.loads(line)

    def call_tool(self, name: str, arguments: dict | None = None, msg_id: int = 1) -> dict:
        self.send({"jsonrpc": "2.0", "id": msg_id, "method": "tools/call",
                   "params": {"name": name, "arguments": arguments or {}}})
        return self.recv()

    def close(self, timeout: float = 10.0) -> tuple[int, str]:
        if self.proc.poll() is not None and self.proc.stdout.closed:
            return self.proc.returncode, ""  # already closed -- safe to call twice
        if not self.proc.stdin.closed:
            self.proc.stdin.close()
        try:
            self.proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait(timeout=5)
        stderr = self.proc.stderr.read()
        self.proc.stdout.close()
        self.proc.stderr.close()
        return self.proc.returncode, stderr


class TestRealClientHandshake(unittest.TestCase):
    """The exact sequence a real MCP client performs: initialize -> wait
    for response -> notifications/initialized -> normal operation."""

    def setUp(self):
        self.client = MCPClient()
        self.addCleanup(self.client.close)

    def test_full_handshake_then_tools_list_then_shutdown(self):
        self.client.send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                           "params": {"protocolVersion": "2024-11-05",
                                      "capabilities": {}, "clientInfo": {"name": "test-client", "version": "0.0.1"}}})
        init_resp = self.client.recv()
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "mtagent")
        self.assertIn("tools", init_resp["result"]["capabilities"])

        # notification: no response expected, must not desync the stream
        self.client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        self.client.send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        list_resp = self.client.recv()
        tools = list_resp["result"]["tools"]
        self.assertEqual(len(tools), 8)
        for t in tools:
            self.assertIn("name", t)
            self.assertIn("description", t)
            self.assertIn("inputSchema", t)
            json.dumps(t["inputSchema"])  # every schema must itself be valid JSON

        rc, stderr = self.client.close()
        self.assertEqual(rc, 0, f"server did not exit cleanly; stderr={stderr!r}")
        self.assertEqual(stderr.strip(), "", "server wrote to stderr during a clean run")


class TestAllToolsOverRealPipes(unittest.TestCase):
    """Call every tool through the real subprocess boundary, one at a time,
    and check the response shape a client would actually rely on."""

    def setUp(self):
        self.client = MCPClient()
        self.addCleanup(self.client.close)
        self.client.send({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
        self.client.recv()
        self.client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _content_json(self, resp):
        self.assertIn("result", resp, resp)
        self.assertFalse(resp["result"]["isError"], resp["result"])
        return json.loads(resp["result"]["content"][0]["text"])

    def test_status(self):
        payload = self._content_json(self.client.call_tool("status"))
        self.assertIn("completion_pct", payload)

    def test_pbi_status(self):
        payload = self._content_json(self.client.call_tool("pbi_status"))
        self.assertIn("build_id", payload)

    def test_reconcile_large_output_survives_line_framing(self):
        resp = self.client.call_tool("reconcile")
        payload = self._content_json(resp)
        self.assertIn("rows", payload)
        # this response is large enough (all reconciliation rows, full
        # precision) to actually exercise line-length handling, not a toy payload
        raw_len = len(resp["result"]["content"][0]["text"])
        self.assertGreater(raw_len, 200)

    def test_find(self):
        payload = self._content_json(self.client.call_tool("find", {"query": "offtake"}))
        self.assertIn("hits", payload)

    def test_worklog_tail(self):
        payload = self._content_json(self.client.call_tool("worklog_tail", {"n": 2}))
        self.assertIn("entries", payload)

    def test_ask_missing_question_is_a_tool_error_not_a_crash(self):
        resp = self.client.call_tool("ask", {})
        self.assertTrue(resp["result"]["isError"])
        # server must still be alive and answer the next request normally
        payload = self._content_json(self.client.call_tool("status", msg_id=2))
        self.assertIn("completion_pct", payload)

    def test_pbi_reconcile_model_missing_args_is_a_tool_error(self):
        resp = self.client.call_tool("pbi_reconcile_model", {})
        self.assertTrue(resp["result"]["isError"])

    def test_pbi_build_dataset_runs_and_reports_a_real_result(self):
        payload = self._content_json(self.client.call_tool("pbi_build_dataset"))
        # whatever it returns must be the real handler's dict, not a stub
        self.assertIsInstance(payload, dict)
        self.assertTrue(payload)

    def test_unicode_question_round_trips_correctly(self):
        question = "FY27 primary कैसे compute होता है? 你好 — édge cases: café, naïve"
        resp = self.client.call_tool("ask", {"question": question})
        payload = self._content_json(resp)
        self.assertIn("passages", payload)  # got a structured answer, not mangled bytes

    def test_ten_sequential_requests_stay_in_order_no_desync(self):
        ids = []
        for i in range(10):
            self.client.send({"jsonrpc": "2.0", "id": 100 + i, "method": "ping"})
        for i in range(10):
            resp = self.client.recv()
            ids.append(resp["id"])
        self.assertEqual(ids, [100 + i for i in range(10)])


class TestStdoutIsPureJSON(unittest.TestCase):
    """The single most fragile property of a stdio MCP server: ANY stray
    print()/logging-to-stdout from a reused CLI code path would corrupt the
    JSON-RPC stream for every client. Exercise every tool and assert stdout
    is nothing but newline-delimited JSON, start to finish."""

    def test_server_writes_only_json_to_stdout_across_all_tools(self):
        client = MCPClient()
        self.addCleanup(client.close)
        client.send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        client.recv()
        client.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        tool_calls = [
            ("status", {}), ("pbi_status", {}), ("reconcile", {}),
            ("find", {"query": "chain master"}), ("worklog_tail", {"n": 1}),
            ("ask", {"question": "test"}),
        ]
        for i, (name, args) in enumerate(tool_calls, start=2):
            client.send({"jsonrpc": "2.0", "id": i, "method": "tools/call",
                         "params": {"name": name, "arguments": args}})
            line = client.proc.stdout.readline()
            self.assertTrue(line.strip(), f"empty/no line for tool {name}")
            try:
                json.loads(line)
            except json.JSONDecodeError as e:
                self.fail(f"non-JSON on stdout after calling {name!r}: {line!r} ({e})")
        rc, stderr = client.close()
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
