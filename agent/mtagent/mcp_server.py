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


def _normalize_validation_result(result: dict) -> dict:
    """Thin, MCP-only presentation fix -- not a change to the underlying
    pipeline. WorkflowController's `validation_result` field is typed str
    for every step (agent/mtagent/pbi_workflow.py), so build-dataset stores
    its rich per-run detail as a JSON-dumped STRING inside that string field
    (agent/mtagent/pbi_dataset.py: "validation_result": json.dumps(build_log)).
    That's the right call for the workflow state machine (uniform field
    type across every step, some of which are one-line text summaries, not
    JSON), but an MCP client sees a JSON string double-encoded inside JSON,
    which is exactly the kind of "long text blob instead of structured
    data" a tool result should avoid. Parse it back into a real nested
    object where it decodes as JSON; leave genuinely plain-text summaries
    (e.g. reconcile-model's "37 metrics compared, 0 FAIL...") untouched."""
    vr = result.get("validation_result")
    if isinstance(vr, str) and vr.strip().startswith("{"):
        try:
            result = {**result, "validation_result": json.loads(vr)}
        except json.JSONDecodeError:
            pass  # not actually JSON -- leave the original string as-is
    return result


def _tool_pbi_status(cfg: Config, args: dict) -> dict:
    get_command, controller = _pbi_controller(cfg)
    return get_command("status").handler(cfg, controller)


def _tool_pbi_build_dataset(cfg: Config, args: dict) -> dict:
    get_command, controller = _pbi_controller(cfg)
    result = get_command("build-dataset").handler(
        cfg, controller, raw_dir=args.get("raw_dir"), masters_dir=args.get("masters_dir"))
    return _normalize_validation_result(result)


def _tool_pbi_reconcile_model(cfg: Config, args: dict) -> dict:
    get_command, controller = _pbi_controller(cfg)
    if "source" not in args or "build_dir" not in args:
        raise ValueError("pbi_reconcile_model requires 'source' and 'build_dir'")
    return get_command("reconcile-model").handler(
        cfg, controller, source=args["source"], build_dir=args["build_dir"],
        masters_dir=args.get("masters_dir"))


# --------------------------------------------------------------------------
# Safety classification -- checked directly against each handler's real
# code path (not assumed), per this project's own "trust nothing you
# haven't checked against real behaviour" discipline. Two layers:
#   annotations: the MCP-spec-native tool-annotation fields (readOnlyHint,
#     destructiveHint, idempotentHint, openWorldHint) -- additive JSON, safe
#     for any client to ignore if it predates them.
#   category: plain-language classification for humans reading tools/list
#     or this file -- "read_only" | "local_file_write". No "state_mutation"
#     or "high_impact_mutation" tools exist yet; that tier starts the first
#     time a genuinely mutating command (apply-alias, mark-complete,
#     compile-model, ...) is added -- not before.
# --------------------------------------------------------------------------
_READ_ONLY = {"readOnlyHint": True, "destructiveHint": False,
              "idempotentHint": True, "openWorldHint": False}
_LOCAL_FILE_WRITE = {"readOnlyHint": False, "destructiveHint": False,
                     "idempotentHint": True, "openWorldHint": False}

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
        "category": "read_only",
        "annotations": _READ_ONLY,
        "side_effects": "May lazily build/cache agent/index/index.json on first use if it "
                         "doesn't exist yet (rag.ensure_index) -- a local cache write, not a "
                         "content mutation; every call after the first is pure read.",
    },
    "status": {
        "description": ("Top-level mtagent/PBI workflow status: current phase, completion %, "
                         "blockers, warnings, next manual step."),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_status,
        "category": "read_only",
        "annotations": _READ_ONLY,
        "side_effects": "None.",
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
        "category": "read_only",
        "annotations": _READ_ONLY,
        "side_effects": "None.",
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
        "category": "read_only",
        "annotations": _READ_ONLY,
        "side_effects": "May lazily build/cache agent/index/catalog.json on first use if it "
                         "doesn't exist yet (catalog.load_catalog) -- same local-cache-only "
                         "caveat as ask.",
    },
    "worklog_tail": {
        "description": "Read the most recent mtagent worklog entries (audit trail of commands run).",
        "inputSchema": {
            "type": "object",
            "properties": {"n": {"type": "integer", "description": "Number of entries (default 10)"}},
        },
        "handler": _tool_worklog_tail,
        "category": "read_only",
        "annotations": _READ_ONLY,
        "side_effects": "None.",
    },
    "pbi_status": {
        "description": ("Power BI workflow controller status: build_id, completion %, "
                         "completed/pending phases, blockers, warnings, latest outputs."),
        "inputSchema": {"type": "object", "properties": {}},
        "handler": _tool_pbi_status,
        "category": "read_only",
        "annotations": _READ_ONLY,
        "side_effects": "None.",
    },
    "pbi_build_dataset": {
        "description": ("Run the PBI build-dataset step (ingest PowerBI/RawDataFolders/"
                         "Offtake_Monthly into dimension/fact tables under agent/pbi_build/"
                         "<build_id>/). Writes local build output files and updates the "
                         "workflow state file -- never touches git (no commit/push)."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "raw_dir": {"type": "string", "description": "Override Offtake_Monthly dir (optional)"},
                "masters_dir": {"type": "string", "description": "Override masters dir (optional)"},
            },
        },
        "handler": _tool_pbi_build_dataset,
        "category": "local_file_write",
        "annotations": _LOCAL_FILE_WRITE,
        "side_effects": "Writes agent/pbi_build/<build_id>/*.csv (Dim/Fact tables, Data_Quality_"
                         "Report.csv, Outlier_Report.csv, ...) and updates the PBI workflow's "
                         "persisted state file (step statuses). Reversible: re-running overwrites "
                         "the same build_id deterministically from source CSVs; nothing outside "
                         "agent/pbi_build/ or the workflow state file is touched. No dry-run mode.",
    },
    "pbi_reconcile_model": {
        "description": ("Run source-to-model reconciliation for a specific PBI build (compares "
                         "a source offtake CSV against a build directory's Fact tables). Writes "
                         "a reconciliation report file and updates the workflow state file -- "
                         "not read-only despite being a checking/reporting step."),
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
        "category": "local_file_write",
        "annotations": _LOCAL_FILE_WRITE,
        "side_effects": "Writes <build_dir>/Source_To_Model_Reconciliation_Report.csv and updates "
                         "the PBI workflow's persisted state file. Reversible: re-running "
                         "overwrites the same report file deterministically. No dry-run mode.",
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
    tools = [{"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"],
              "annotations": spec["annotations"]}
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
    None for notifications. Per spec, a notification is identified by the
    'id' KEY being absent -- not by its value being null. A request with an
    explicit `"id": null` is unusual but valid and still gets a response;
    conflating the two (checking only `.get('id') is None`) would silently
    swallow a response a client is waiting for."""
    method = msg.get("method")
    has_id = "id" in msg
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
    if not has_id:
        return None  # true notification -- 'id' key absent entirely
    return _error_response(msg_id, -32601, f"Method not found: {method}")


def _write_line(out_stream, obj: dict) -> bool:
    """Write one JSON-RPC response line. Returns False (instead of raising)
    if the pipe/stream is gone -- a client that vanished mid-response is
    normal for a stdio subprocess, not a crash-worthy condition."""
    try:
        out_stream.write(json.dumps(obj, default=str) + "\n")
        out_stream.flush()
        return True
    except (BrokenPipeError, OSError, ValueError):
        return False


def serve(cfg: Config, in_stream=None, out_stream=None) -> None:
    """Blocking stdio loop: one JSON-RPC message per line in, one per line
    out. A malformed line is reported as a JSON-RPC parse error and the
    loop continues -- never crashes the server on bad input. Exits quietly
    (no traceback) the moment the client disconnects (broken pipe) or
    closes stdin (falls out of the for-loop naturally)."""
    in_stream = in_stream if in_stream is not None else sys.stdin
    out_stream = out_stream if out_stream is not None else sys.stdout
    for line in in_stream:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            if not _write_line(out_stream, _error_response(None, -32700, f"Parse error: {e}")):
                return
            continue
        try:
            resp = handle_message(msg, cfg)
        except Exception as e:
            resp = _error_response(msg.get("id") if isinstance(msg, dict) else None,
                                    -32603, f"Internal error: {e}\n{traceback.format_exc()}")
        if resp is not None:
            if not _write_line(out_stream, resp):
                return
