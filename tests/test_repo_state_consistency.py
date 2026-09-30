"""repo_state_consistency: the state docs must agree with config/project_state.yml.

Found 2026-09-30: docs/PROJECT_STATE.md said "Open PRs now: #119 ... and #229
(HOLD)" three days after #229 merged, and the blocker pack still titled B3
"#229 ... (HOLD)" while the remaining work had moved to #252. Every test was
green; only the documents described yesterday's repository.

This test cannot call GitHub. It pins the documents to one machine-readable
file, and that file is checked against GitHub by a person at each merge.
"""
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STATE = yaml.safe_load((ROOT / "config/project_state.yml").read_text(encoding="utf-8"))
PS = (ROOT / "docs/PROJECT_STATE.md").read_text(encoding="utf-8")
PACK = (ROOT / "docs/COMPLETION_BLOCKER_PACK.md").read_text(encoding="utf-8")

TERMINAL = {"RESOLVED_AND_VALIDATED", "BLOCKED_EXTERNAL_EVIDENCE", "BLOCKED_OWNER_DECISION",
            "BLOCKED_ENVIRONMENT", "DEFERRED_NON_BLOCKING_WITH_OWNER"}


def _section(text, heading):
    start = text.index(heading)
    nxt = text.find("\n## ", start + 1)
    return text[start:nxt if nxt != -1 else len(text)]


def _pr_numbers(line):
    return {int(n) for n in re.findall(r"#(\d+)", line)}


def test_registry_shape():
    open_nums = {p["number"] for p in STATE["open_prs"]}
    assert not open_nums & set(STATE["merged_prs"]), "a PR cannot be both open and merged"
    for p in STATE["open_prs"]:
        assert p["status"] in {"HOLD", "FROZEN_EVIDENCE", "READY", "BLOCKED"}, p
        assert p.get("blocker") and p.get("reason"), f"#{p['number']} needs a blocker and a reason"
        if p.get("stacked_on_merged"):
            assert p["stacked_on_merged"] in STATE["merged_prs"]
            assert "rebuild" in p["reason"].lower(), f"#{p['number']} is stacked on a merged PR; record the rebuild plan"
    assert set(STATE["blockers"]) == {"B1", "B2", "B3", "B4", "B5", "B6"}
    for bid, b in STATE["blockers"].items():
        assert b["state"] in TERMINAL, f"{bid}: {b['state']} is not a terminal state"
        assert b.get("owner") and b.get("needs"), f"{bid} needs an owner and the exact input"


def test_next_approved_task_lists_exactly_the_open_prs():
    nat = _section(PS, "## Next Approved Task")
    line = next(l for l in nat.splitlines() if l.startswith("Open PRs held on blockers:"))
    # each open PR is written "#NNN (status...)"; other #refs on the line are context
    listed = {int(n) for n in re.findall(r"#(\d+) \(", line.split("Open issues")[0])}
    assert listed == {p["number"] for p in STATE["open_prs"]}, f"PROJECT_STATE lists {sorted(listed)}"
    issues = _pr_numbers(line.split("Open issues")[1]) if "Open issues" in line else set()
    assert issues == {i["number"] for i in STATE["open_issues"]}


def test_merged_prs_never_called_open_or_hold_in_current_text():
    current = _section(PS, "## Next Approved Task") + _section(PACK, "## Summary")
    for n in STATE["merged_prs"]:
        for bad in (rf"#{n}\s*\(HOLD\)", rf"#{n}\s*—[^|\n]*\(HOLD\)", rf"#{n}\s+HOLD"):
            assert not re.search(bad, current), f"#{n} is merged but current-state text calls it HOLD"


def test_blocker_pack_rows_match_registry():
    rows = {l.split("|")[1].strip(): l for l in PACK.splitlines() if re.match(r"\| B[1-6] \|", l)}
    assert set(rows) == set(STATE["blockers"])
    assert STATE["blockers"]["B5"]["doc_status"] in rows["B5"]
    for p in STATE["open_prs"]:
        assert f"#{p['number']}" in rows[p["blocker"]], f"#{p['number']} not named on blocker {p['blocker']}"


def test_dated_history_sections_are_marked_historical():
    for h in ("### Production certification — 2026-09-25", "### Closeout — 2026-09-26",
              "### Final certification — 2026-09-26"):
        sec = PS[PS.index(h):PS.index(h) + 400]
        assert "Historical record" in sec, f"{h} lists PR states; it must be marked as history"
