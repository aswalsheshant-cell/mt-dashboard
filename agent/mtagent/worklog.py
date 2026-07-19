"""Work log — STEP 9 of the analyst charter: every CLI run is appended to
``agent/index/worklog.jsonl`` (gitignored) with command, args, timestamp,
exit status and any notes, so there is always an audit trail of what was
run against which data. ``python -m mtagent log`` shows the tail.

Schema v2 (see ``agent/AGENT_OPERATING_PRINCIPLES.md`` "Worklog schema"):
adds ``desired_output``/``success_criteria``/``input_hashes``/
``stage_results``/``reconciliation``/``exceptions``/``decision_required``/
``output_hashes``/``approved_by`` so a log entry can prove a run produced
the *correct business result*, not just that a command executed. Every
new field is optional and additive — a v1 entry (just
ts/command/argv/status/notes) still round-trips through ``read_log``
unchanged; old callers of ``log_run`` with only the original four
positional args keep working with the new fields simply absent.
"""
from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

from .config import Config

LOG_NAME = "worklog.jsonl"
SCHEMA_VERSION = 2


def _log_path(cfg: Config) -> Path:
    return cfg.path(cfg.index_path).parent / LOG_NAME


def hash_file(path: str | Path) -> str:
    """SHA-256 of a file's bytes, for input/output integrity evidence."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hash_files(paths: list) -> dict:
    """{relative-or-given path string: sha256} for a list of file paths."""
    return {str(p): hash_file(p) for p in paths}


def log_run(cfg: Config, command: str, argv: list, status: int,
            notes: list | None = None, *,
            run_id: str | None = None,
            desired_output: str | None = None,
            success_criteria: list | None = None,
            input_files: list | None = None,
            input_hashes: dict | None = None,
            stage_results: dict | None = None,
            reconciliation: dict | None = None,
            exceptions: list | None = None,
            decision_required: list | None = None,
            output_files: list | None = None,
            output_hashes: dict | None = None,
            approved_by: str | None = None) -> None:
    """Append one worklog entry. Only ``cfg``/``command``/``argv``/``status``
    are required — every schema-v2 field is optional so existing call
    sites (e.g. the CLI's own per-command logging) are unaffected. Pass
    the v2 fields explicitly when a run should carry feedback-loop
    evidence (see AGENT_OPERATING_PRINCIPLES.md principle #7 and #10).
    """
    entry = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "command": command,
        "argv": argv,
        "status": status,
        "notes": notes or [],
    }
    # A plain v1-style call (no v2 kwarg supplied) writes a plain v1-shaped
    # line. The moment the caller opts in by supplying ANY v2 field, write
    # the COMPLETE v2 shape (unset list/dict fields default to []/{}, unset
    # scalars stay None) -- a partial v2 entry would be as misleading as a
    # v1 entry claiming to have feedback-loop evidence it doesn't carry.
    raw_v2 = {
        "run_id": run_id, "desired_output": desired_output,
        "success_criteria": success_criteria, "input_files": input_files,
        "input_hashes": input_hashes, "stage_results": stage_results,
        "reconciliation": reconciliation, "exceptions": exceptions,
        "decision_required": decision_required, "output_files": output_files,
        "output_hashes": output_hashes, "approved_by": approved_by,
    }
    if any(v is not None for v in raw_v2.values()):
        list_fields = {"success_criteria", "input_files", "exceptions",
                        "decision_required", "output_files"}
        dict_fields = {"input_hashes", "stage_results", "reconciliation", "output_hashes"}
        entry["schema_version"] = SCHEMA_VERSION
        for k, v in raw_v2.items():
            if v is None and k in list_fields:
                v = []
            elif v is None and k in dict_fields:
                v = {}
            entry[k] = v
    try:
        p = _log_path(cfg)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except (OSError, ValueError):
        pass   # logging must never break the actual work -- ValueError catches
                # things like an embedded-null path that OSError alone would miss


def read_log(cfg: Config, tail: int = 20) -> list[dict]:
    p = _log_path(cfg)
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    out = []
    for line in lines[-tail:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
