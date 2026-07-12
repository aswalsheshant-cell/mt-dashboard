"""SQL template loader/renderer for the files in ``agent/sql/``.

Template header convention (comment lines at the top of each .sql):

    -- name: chain_ranking
    -- description: ... (may continue on indented -- lines)
    -- param: fy default=FY26

Placeholders in the body are ``{{param}}``. Values are sanitized to a strict
character allowlist before substitution — these templates are convenience
queries, not an injection surface, but the agent still refuses quotes,
semicolons and comment tokens in parameter values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config

SQL_DIR_NAME = "agent/sql"
_PARAM_RE = re.compile(r"^--\s*param:\s*(\w+)(?:\s+default=(.*))?$")
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")
_SAFE_VALUE_RE = re.compile(r"^[A-Za-z0-9 _%.,&()/+*=<>!-]*$")


@dataclass
class Template:
    name: str
    path: Path
    description: str = ""
    params: dict = field(default_factory=dict)   # name -> default (or None)
    body: str = ""


def _parse(path: Path) -> Template:
    t = Template(name=path.stem, path=path)
    lines = path.read_text(encoding="utf-8").splitlines()
    body_lines, in_header = [], True
    for line in lines:
        s = line.strip()
        if in_header and s.startswith("--"):
            if m := re.match(r"^--\s*name:\s*(.+)$", s):
                t.name = m.group(1).strip()
            elif m := re.match(r"^--\s*description:\s*(.+)$", s):
                t.description = m.group(1).strip()
            elif m := _PARAM_RE.match(s):
                t.params[m.group(1)] = (m.group(2) or "").strip() or None
            elif t.description and not s.startswith("-- "):
                pass
            elif t.description:
                t.description += " " + s.lstrip("- ").strip()
            continue
        in_header = False
        body_lines.append(line)
    t.body = "\n".join(body_lines).strip()
    return t


def list_templates(cfg: Config) -> list[Template]:
    d = cfg.path(SQL_DIR_NAME)
    return [_parse(p) for p in sorted(d.glob("*.sql"))]


def get_template(cfg: Config, name: str) -> Template:
    for t in list_templates(cfg):
        if t.name == name:
            return t
    known = ", ".join(t.name for t in list_templates(cfg))
    raise KeyError(f"no SQL template '{name}' — available: {known}")


def render(t: Template, params: dict | None = None) -> str:
    params = dict(params or {})
    values = {}
    for pname, default in t.params.items():
        v = params.pop(pname, default)
        if v is None:
            raise ValueError(f"template '{t.name}' needs --param {pname}=<value>")
        values[pname] = str(v)
    if params:
        raise ValueError(f"unknown param(s) for '{t.name}': {', '.join(params)}")
    for pname, v in values.items():
        if not _SAFE_VALUE_RE.match(v):
            raise ValueError(f"unsafe characters in param {pname}={v!r}")

    def sub(m: re.Match) -> str:
        name = m.group(1)
        if name not in values:
            raise ValueError(f"template '{t.name}' uses undeclared param "
                             f"{{{{{name}}}}} — add a '-- param:' header line")
        return values[name]

    return _PLACEHOLDER_RE.sub(sub, t.body)
