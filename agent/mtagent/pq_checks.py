"""Power Query (M) checks for the paste-in queries under ``PowerBI/PowerQuery/``.

Static lint — runs offline, no Power BI needed:

  PQ001 error  missing let/in structure (parameter queries are exempt)
  PQ002 error  unbalanced ( ) [ ] { } or unterminated string
  PQ003 error  the ``in`` result is not a defined step
  PQ004 warn   step defined but never referenced (dead step)
  PQ005 warn   hardcoded absolute path outside 00_Parameters — everything
               must flow through the pRootFolder parameter
  PQ006 warn   referenced RawDataFolders/SeedData path missing from the repo
               (repo mirrors the expected on-disk layout)
  PQ007 info   fact query (10_..19_) without Table.TransformColumnTypes —
               repo convention is to enforce types on every fact

M strings escape quotes by doubling (``""``); comments are ``//`` and
``/* */``. Step names are bare identifiers or ``#"quoted names"``.
"""
from __future__ import annotations

import re
from pathlib import Path

from .dax_validator import strip_comments_and_strings  # same lexical rules
from .report import Finding

_STEP_DEF_RE = re.compile(r'(#"[^"]+"|[A-Za-z_][A-Za-z0-9_.]*)\s*=(?!=)')
_ABS_PATH_RE = re.compile(r'^"(?:[A-Za-z]:\\|\\\\)')
_REPO_PATH_RE = re.compile(r'"\\((?:RawDataFolders|SeedData)\\[^"]*)"')
_BALANCE_PAIRS = {")": "(", "]": "[", "}": "{"}


def _is_parameter_query(text: str) -> bool:
    return "IsParameterQuery" in text


def check_balance(cleaned: str, fname: str) -> list:
    findings, stack, line = [], [], 1
    for ch in cleaned:
        if ch == "\n":
            line += 1
        elif ch in "([{":
            stack.append((ch, line))
        elif ch in ")]}":
            if not stack or stack[-1][0] != _BALANCE_PAIRS[ch]:
                findings.append(Finding(fname, line, "PQ002", "error",
                                        f"unbalanced '{ch}'"))
                return findings
            stack.pop()
    for ch, ln in stack:
        findings.append(Finding(fname, ln, "PQ002", "error", f"unclosed '{ch}'"))
    return findings


def _let_bindings(cleaned: str) -> tuple[list, str | None]:
    """Parse the top-level let block: [(name, line)], in-result name.
    Bindings are recognised at depth 0 relative to the let body (commas that
    separate steps), which skips nested record/function ``=`` signs."""
    m = re.search(r"\blet\b", cleaned)
    if not m:
        return [], None
    body_start = m.end()
    depth = 0
    steps, at_step_start = [], True
    i, n, line = body_start, len(cleaned), cleaned.count("\n", 0, body_start) + 1
    in_result = None
    while i < n:
        ch = cleaned[i]
        if ch == "\n":
            line += 1
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and ch == ",":
            at_step_start = True
            i += 1
            continue   # don't let the comma itself clear at_step_start below
        elif depth == 0 and cleaned.startswith("in", i) and \
                (i + 2 >= n or not (cleaned[i + 2].isalnum() or cleaned[i + 2] == "_")) and \
                not (i > 0 and (cleaned[i - 1].isalnum() or cleaned[i - 1] in '_"')):
            rest = cleaned[i + 2:].strip()
            dm = _STEP_DEF_RE.match(rest + " =")   # reuse ident pattern
            in_result = dm.group(1) if dm else (rest.split()[0] if rest else None)
            break
        if at_step_start and (ch.isalpha() or ch in '_#'):
            dm = _STEP_DEF_RE.match(cleaned, i)
            if dm:
                steps.append((dm.group(1), line))
                at_step_start = False
                i = dm.end()
                continue
            at_step_start = False
        elif at_step_start and not ch.isspace():
            at_step_start = False
        i += 1
    return steps, in_result


def validate_file(path: Path, repo_root: Path | None = None) -> list:
    fname = str(path)
    text = Path(path).read_text(encoding="utf-8-sig")
    cleaned, literals = strip_comments_and_strings(text, keep_hash_identifiers=True)
    findings = check_balance(cleaned, fname)
    is_param = _is_parameter_query(text)

    steps, in_result = _let_bindings(cleaned)
    if not re.search(r"\blet\b", cleaned) or not re.search(r"\bin\b", cleaned):
        if not is_param:
            findings.append(Finding(fname, 1, "PQ001", "error",
                                    "no let/in structure found"))
    else:
        step_names = [s for s, _ in steps]
        if in_result and in_result not in step_names and steps:
            findings.append(Finding(fname, 1, "PQ003", "error",
                                    f"'in {in_result}' is not a defined step"))
        # PQ004 — dead steps: defined, not the result, never referenced later
        for name, ln in steps:
            if name == in_result:
                continue
            token = re.escape(name)
            refs = len(re.findall(rf"(?<![\w#\"]){token}(?![\w])", cleaned)) \
                if not name.startswith('#') else cleaned.count(name)
            if refs <= 1:   # its own definition only
                findings.append(Finding(fname, ln, "PQ004", "warn",
                                        f"step {name} is never referenced"))

    # PQ005 — hardcoded absolute paths (parameter queries exempt)
    if not is_param:
        for ln, lit in literals:
            if _ABS_PATH_RE.match(lit):
                findings.append(Finding(fname, ln, "PQ005", "warn",
                                        f"hardcoded absolute path {lit} — "
                                        "route through pRootFolder"))

    # PQ006 — referenced repo paths must exist (repo mirrors deploy layout)
    if repo_root:
        base = Path(repo_root) / "PowerBI"
        for ln, lit in literals:
            m = _REPO_PATH_RE.match(lit)
            if m:
                rel = m.group(1).replace("\\", "/").strip("/")
                # heavy source workbooks are gitignored — only their folder
                # is expected to exist in the repo
                if rel.lower().endswith((".xlsx", ".xlsb", ".xlsm")):
                    rel = str(Path(rel).parent)
                if not (base / rel).exists():
                    findings.append(Finding(fname, ln, "PQ006", "warn",
                                            f"referenced path PowerBI/{rel} "
                                            "does not exist in the repo"))

    # PQ007 — fact queries should enforce column types
    if re.match(r"1\d_", Path(path).name) and \
            "Table.TransformColumnTypes" not in text and not is_param:
        findings.append(Finding(fname, 1, "PQ007", "info",
                                "fact query without Table.TransformColumnTypes — "
                                "repo convention is to type every fact column"))
    return findings


def validate_paths(paths: list, repo_root: Path | None = None) -> list:
    findings: list[Finding] = []
    for p in paths:
        findings.extend(validate_file(Path(p), repo_root))
    return findings
