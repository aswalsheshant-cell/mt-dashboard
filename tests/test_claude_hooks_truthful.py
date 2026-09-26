"""Claude Code hooks in .claude/ must run and must not claim checks that never ran.

Found 2026-09-26 on main (old PR #133 rebuilt on current main):
  * the PostToolUse(Write) PPTX hook read `$1`, but a hook receives its payload
    as JSON on stdin (https://code.claude.com/docs/en/hooks), so it never fired;
    it also carried a non-standard "args" key, and its message claimed
    "Pattern Matcher Router validation applied ... Deck is presentation-ready"
    although no validation exists anywhere;
  * session-start.sh printed "=== Environment ready ===" whatever the health
    check reported (its output was discarded with `|| true`).
"""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / ".claude" / "settings.json"
SESSION = ROOT / ".claude" / "hooks" / "session-start.sh"
HOOK_KEYS = {"type", "command", "timeout"}


def _hooks():
    cfg = json.loads(SETTINGS.read_text(encoding="utf-8"))
    for event, groups in cfg.get("hooks", {}).items():
        for g in groups:
            for h in g.get("hooks", []):
                yield event, h


def test_hook_entries_use_only_documented_keys():
    bad = [(e, sorted(set(h) - HOOK_KEYS)) for e, h in _hooks() if set(h) - HOOK_KEYS]
    assert bad == [], f"undocumented hook keys: {bad}"


def test_no_hook_reads_positional_args():
    bad = [e for e, h in _hooks() if "$1" in h.get("command", "")]
    assert bad == [], "hooks get JSON on stdin, never $1"


def test_no_hook_claims_validation_it_does_not_run():
    text = SETTINGS.read_text(encoding="utf-8").lower()
    for scripted in (ROOT / ".claude" / "hooks").glob("*.sh"):
        # executable lines only -- a comment warning against the claim is fine
        text += "\n".join(ln for ln in scripted.read_text(encoding="utf-8").lower().splitlines()
                           if not ln.lstrip().startswith("#"))
    for claim in ("presentation-ready", "validation applied", "and validated"):
        assert claim not in text, f"hook text claims '{claim}' but no such check runs"


def _pptx_hook():
    cmds = [h["command"] for e, h in _hooks() if e == "PostToolUse"]
    assert len(cmds) == 1
    return cmds[0].replace("$CLAUDE_PROJECT_DIR", str(ROOT))


def _run_pptx_hook(payload):
    return subprocess.run(["bash", "-c", _pptx_hook()], input=payload, capture_output=True, text=True, timeout=20)


def test_pptx_hook_fires_on_pptx_and_says_what_it_checked():
    r = _run_pptx_hook(json.dumps({"tool_name": "Write", "tool_input": {"file_path": "/tmp/deck.pptx"}}))
    assert r.returncode == 0
    msg = json.loads(r.stdout)["systemMessage"]
    assert "/tmp/deck.pptx" in msg and "no content validation" in msg


def test_pptx_hook_silent_on_other_files_and_bad_payload():
    for payload in (json.dumps({"tool_input": {"file_path": "/tmp/notes.md"}}), "not json", ""):
        r = _run_pptx_hook(payload)
        assert r.returncode == 0 and r.stdout.strip() == "", payload


def _session_banner(tmp_path, health_lines):
    """Run the real session-start.sh against a tmp project whose health check
    prints `health_lines` (no package.json, so it goes straight to finish())."""
    (tmp_path / "scripts").mkdir()
    hc = tmp_path / "scripts" / "environment_health_check.sh"
    hc.write_text("#!/bin/bash\n" + "".join(f"echo '{ln}'\n" for ln in health_lines) + "exit 0\n")
    hc.chmod(0o755)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(tmp_path))
    r = subprocess.run(["bash", str(SESSION)], input="", capture_output=True, text=True, env=env, timeout=30)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip().splitlines()[-1]


def test_session_banner_ready_only_when_environment_is_clean(tmp_path):
    clean = ["  memory                 15000 MB free of 16000 MB",
             "  DMS extracts staged    0 file(s) — incentive ingest BLOCKED until re-supplied",
             "  incentive working      absent — regenerate from source when needed"]
    assert _session_banner(tmp_path, clean) == "=== Environment ready ==="


def test_session_banner_flags_environment_problems(tmp_path):
    for problem in ("  ** LOW DISK — clear build artifacts before writing data.js",
                    "  dashboard/data.js      MISSING",
                    "  python deps            missing: pandas — run ./scripts/setup_environment.sh",
                    "  chromium               absent",
                    "  test server :8899      STILL RUNNING — stop it before re-running the sweep"):
        d = tmp_path / str(abs(hash(problem)))
        d.mkdir()
        banner = _session_banner(d, [problem])
        assert banner != "=== Environment ready ===" and "see" in banner.lower(), (problem, banner)
