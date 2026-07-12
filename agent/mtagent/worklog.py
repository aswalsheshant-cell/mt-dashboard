"""Work log — STEP 9 of the analyst charter: every CLI run is appended to
``agent/index/worklog.jsonl`` (gitignored) with command, args, timestamp,
exit status and any notes, so there is always an audit trail of what was
run against which data. ``python -m mtagent log`` shows the tail."""
from __future__ import annotations

import datetime
import json
from pathlib import Path

from .config import Config

LOG_NAME = "worklog.jsonl"


def _log_path(cfg: Config) -> Path:
    return cfg.path(cfg.index_path).parent / LOG_NAME


def log_run(cfg: Config, command: str, argv: list, status: int,
            notes: list | None = None) -> None:
    entry = {
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "command": command,
        "argv": argv,
        "status": status,
        "notes": notes or [],
    }
    try:
        p = _log_path(cfg)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError:
        pass   # logging must never break the actual work


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
