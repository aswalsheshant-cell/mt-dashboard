"""Minimal stdlib-only MCP (Model Context Protocol) server for mtagent.

No ``mcp`` SDK dependency -- confirmed unavailable in this environment
(pip and apt both return 403 under org policy for every package tried this
project, not just this one). Implements exactly the stdio transport +
JSON-RPC 2.0 methods a tool-only MCP server needs: ``initialize``,
``notifications/initialized``, ``tools/list``, ``tools/call``, ``ping``.
See https://modelcontextprotocol.io/specification -- stdio transport is
newline-delimited JSON-RPC messages on stdin/stdout, no HTTP framing.

Every tool below is a thin wrapper that calls the SAME function the CLI
command already calls (``rag.ask``, ``WorkflowController.status_summary``,
``reconcile.run_reconciliation``, ``catalog.find``, ``worklog.read_log``,
and the ``build-dataset``/``reconcile-model`` PBI commands via the existing
registry) -- no duplicated business logic, so a fix to one path fixes both.

Scope, deliberately: this first pass exposes read/analysis tools plus the
two PBI pipeline steps that are already safe to run freely per
``pbi-workflow.md`` (build-dataset, reconcile-model -- local file output
only, no git commit/push). Mutating commands beyond that (derive-article-
master, apply-alias, compile-model, mark-complete) are not exposed yet;
add them the same way if/when needed.

Run with:
    python -m mtagent mcp-serve
"""
from __future__ import annotations

import json
import sys
import traceback

from .config import Config

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "mtagent"
SERVER_VERSION = "0.1.0"


# --------------------------------------------------------------------------
# Tool handlers -- each returns a JSON-serializable dict, reusing the exact
# function the equivalent CLI command calls.
# --------------------------------------------------------------------------
def _tool_ask(cfg: Config, args: dict) -> dict:
    from .rag import ask
    if "question" not in args:
        raise ValueError("ask requires 'question'")
    return ask(cfg, args["question"], k=args.get("k"), mode=args.get("mode", "ask"))


def _tool_status(cfg: Config, args: dict) -> dict:
    from .pbi_workflow import WorkflowController
    return WorkflowController(cfg).status_summary()


def _tool_reconcile(cfg: Config, args: dict) -> dict:
    from .reconcile import run_reconciliation
    return run_reconciliation(cfg, tol_pct=args.get("tol_pct", 0.5))


def _tool_find(cfg: Config, args: dict) -> dict:
    from .catalog import find
    if "query" not in args:
        raise ValueError("find requires 'query'")
    hits = find(cfg, args["query"], limit=args.get("limit", 10))
    return {"hits": [
        {"score": score, "path": e.path, "category": e.category,
         "purpose": e.purpose, "fy": e.fy, "month": e.month}
        for score, e in hits
    ]}


def _tool_worklog_tail(cfg: Config, args: dict) -> dict:
    from .worklog import read_log
    return {"entries": read_log(cfg, tail=args.get("n", 10))}


def _pbi_controller(cfg: Config):
    from . import pbi_commands  # noqa: F401 -- import populates the registry
    from .pbi_registry import get_command
    from .pbi_workflow import WorkflowController
    return get_command, WorkflowController(cfg)


def _tool_pbi_status(cfg: Config, args: dict) -> dict:
    get_command, controller = _pbi_controller(cfg)
    return get_command("status").handler(cfg, controller)


def _tool_pbi_build_dataset(cfg: Config, args: dict) -> dict:
    get_command, controller = _pbi_controller(cfg)
    return get_command("build-dataset").handler(
        cfg, controller, raw_dir=args.get("raw_dir"), masters_dir=args.get("masters_dir"))


def _tool_pbi_reconcile_model(cfg: Config, args: dict) -> dict:
    get_command, controller = _pbi_controller(cfg)
    if "source" not in args or "build_dir" not in args:
        raise ValueError("pbi_reconcile_model requires 'source' and 'build_dir'")
    return get_command("reconcile-model").handler(
        cfg, controller, source=args["source"], build_dir=args["build_dir"],
        masters_dir=args.get("masters_dir"))


TOOLS = {
    "ask": {
        "description": (
            "Ask the offline MT analyst agent a question over its local knowledge base "
            "(repo docs, masters, DAX/PQ files). Retrieval-augmented; uses local Ollama "
            "if available, otherwise returns the raw retrieved passages."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The question to ask"},
                "k": {"type": "integer", "description": "Passages to retrieve (default: config top_k)"},
                "mode": {"type": "string", "enum": ["ask", "meeting"],
                         "description": "ask = normal, meeting = terse leadership-brief answer"},
            },
            "required": ["question"],
        },
        "handler": _tool_ask,
    },
    "status": {
        "description": ("Top-level mtagent/PBI workflow status: current phase, completion %, "
                         "blockers, warnings, next manual step."),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_status,
    },
    "reconcile": {
        "description": ("Reconcile dashboard/data.js against the committed source CSVs "
                         "(Primary_Article_Monthly, Offtake_Monthly). Read-only cross-check, "
                         "does not modify any file."),
        "inputSchema": {
            "type": "object",
            "properties": {"tol_pct": {"type": "number",
                                        "description": "Tolerance %% for PASS/DIFF (default 0.5)"}},
        },
        "handler": _tool_reconcile,
    },
    "find": {
        "description": "Locate where a concept/file lives in the repo (e.g. 'chain master', 'offtake June').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
        "handler": _tool_find,
    },
    "worklog_tail": {
        "description": "Read the most recent mtagent worklog entries (audit trail of commands run).",
        "inputSchema": {
            "type": "object",
            "properties": {"n": {"type": "integer", "description": "Number of entries (default 10)"}},
        },
        "handler": _tool_worklog_tail,
    },
    "pbi_status": {
        "description": ("Power BI workflow controller status: build_id, completion %, "
                         "completed/pending phases, blockers, warnings, latest outputs."),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_pbi_status,
    },
    "pbi_build_dataset": {
        "description": ("Run the PBI build-dataset step (ingest PowerBI/RawDataFolders/"
                         "Offtake_Monthly into dimension/fact tables under agent/pbi_build/"
                         "<build_id>/). Writes local build output files only -- never commits "
                         "or pushes."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "raw_dir": {"type": "string", "description": "Override Offtake_Monthly dir (optional)"},
                "masters_dir": {"type": "string", "description": "Override masters dir (optional)"},
            },
        },
        "handler": _tool_pbi_build_dataset,
    },
    "pbi_reconcile_model": {
        "description": ("Run source-to-model reconciliation for a specific PBI build (compares "
                         "a source offtake CSV against a build directory's Fact tables). "
                         "Read-only report."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {"type": "string",
                           "description": "Source offtake CSV, e.g. PowerBI/RawDataFolders/"
                                          "Offtake_Monthly/offtake_store_article_May_26.csv"},
                "build_dir": {"type": "string",
                              "description": "Build directory, e.g. agent/pbi_build/FY27_May26"},
                "masters_dir": {"type": "string", "description": "Override masters dir (optional)"},
            },
            "required": ["source", "build_dir"],
        },
        "handler": _tool_pbi_reconcile_model,
    },
}


# --------------------------------------------------------------------------
# JSON-RPC 2.0 / stdio transport
# --------------------------------------------------------------------------
def _error_response(msg_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _handle_initialize(msg: dict) -> dict:
    return {
        "jsonrpc": "2.0", "id": msg["id"],
        "result": {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        },
    }


def _handle_tools_list(msg: dict) -> dict:
    tools = [{"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"]}
             for name, spec in TOOLS.items()]
    return {"jsonrpc": "2.0", "id": msg["id"], "result": {"tools": tools}}


def _handle_tools_call(msg: dict, cfg: Config) -> dict:
    params = msg.get("params") or {}
    name = params.get("name")
    args = params.get("arguments") or {}
    spec = TOOLS.get(name)
    if spec is None:
        return _error_response(msg["id"], -32602, f"Unknown tool: {name}")
    try:
        result = spec["handler"](cfg, args)
        text = json.dumps(result, indent=2, default=str)
        return {"jsonrpc": "2.0", "id": msg["id"],
                "result": {"content": [{"type": "text", "text": text}], "isError": False}}
    except Exception as e:
        # A tool-level failure is reported IN the result (isError=True), per
        # spec, so the client sees it as a tool outcome, not a transport error.
        text = f"{type(e).__name__}: {e}"
        return {"jsonrpc": "2.0", "id": msg["id"],
                "result": {"content": [{"type": "text", "text": text}], "isError": True}}


def handle_message(msg: dict, cfg: Config) -> dict | None:
    """Dispatch one parsed JSON-RPC message. Returns the response dict, or
    None for notifications (no 'id' -- no response expected, per spec)."""
    method = msg.get("method")
    msg_id = msg.get("id")
    if method == "initialize":
        return _handle_initialize(msg)
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return _handle_tools_list(msg)
    if method == "tools/call":
        return _handle_tools_call(msg, cfg)
    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}
    if msg_id is None:
        return None  # unrecognised notification -- never error on a notification
    return _error_response(msg_id, -32601, f"Method not found: {method}")


def serve(cfg: Config, in_stream=None, out_stream=None) -> None:
    """Blocking stdio loop: one JSON-RPC message per line in, one per line
    out. A malformed line is reported as a JSON-RPC parse error and the
    loop continues -- never crashes the server on bad input."""
    in_stream = in_stream if in_stream is not None else sys.stdin
    out_stream = out_stream if out_stream is not None else sys.stdout
    for line in in_stream:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            out_stream.write(json.dumps(_error_response(None, -32700, f"Parse error: {e}")) + "\n")
            out_stream.flush()
            continue
        try:
            resp = handle_message(msg, cfg)
        except Exception as e:
            resp = _error_response(msg.get("id") if isinstance(msg, dict) else None,
                                    -32603, f"Internal error: {e}\n{traceback.format_exc()}")
        if resp is not None:
            out_stream.write(json.dumps(resp, default=str) + "\n")
            out_stream.flush()
