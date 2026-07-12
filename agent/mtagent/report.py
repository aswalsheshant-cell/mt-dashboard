"""Shared finding type + console/JSON formatting for the validators."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass

SEVERITIES = ("error", "warn", "info")


@dataclass
class Finding:
    file: str
    line: int
    code: str
    severity: str          # error | warn | info
    message: str

    def format(self) -> str:
        return f"{self.file}:{self.line}: {self.severity.upper()} {self.code} {self.message}"


def summarize(findings: list) -> dict:
    out = {s: 0 for s in SEVERITIES}
    for f in findings:
        out[f.severity] = out.get(f.severity, 0) + 1
    return out


def print_findings(findings: list, as_json: bool = False,
                   min_severity: str = "info") -> None:
    keep = SEVERITIES[: SEVERITIES.index(min_severity) + 1]
    shown = [f for f in findings if f.severity in keep]
    if as_json:
        print(json.dumps([asdict(f) for f in shown], indent=2))
        return
    for f in shown:
        print(f.format())
    s = summarize(findings)
    print(f"-- {s['error']} error(s), {s['warn']} warning(s), {s['info']} info note(s)")


def exit_code(findings: list, strict: bool = False) -> int:
    s = summarize(findings)
    if s["error"]:
        return 1
    if strict and s["warn"]:
        return 1
    return 0
