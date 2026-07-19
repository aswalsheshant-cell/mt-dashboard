# mtagent Controller — `ask` / `run` / `chat` / `status` / `log`

The single entry point layer described in
`agent/AGENT_OPERATING_PRINCIPLES.md`. You talk to one of five commands;
`run`/`chat` route through `agent/mtagent/controller.py`, which turns your
instruction into a structured **Plan** (desired output, business rules,
success criteria, risks, approval boundary) and only then executes it
against the real `mtagent pbi` commands — never a fabricated one.

| Command | Role |
|---|---|
| `ask` | Knowledge Q&A only — unchanged, RAG-backed, has its own eval suite |
| `run` | Structured planning + controlled execution of one instruction |
| `chat` | Interactive session — instructions execute, questions get answered, `exit` to quit |
| `status` | Active workflow, blockers, next approval needed |
| `log` | Recent worklog audit trail (`--tail N`) |

## Setup — Windows PowerShell

Full dependency install detail is in `agent/README.md` §Setup — this is
the condensed path to running the controller specifically.

```powershell
# 1. Get the repo onto a fixed path (adjust to your machine)
cd C:\Users\<you>\Projects
git clone <repo-url> mt-dashboard
cd mt-dashboard

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies (all optional — the agent degrades gracefully
#    without them; DuckDB/Ollama add SQL/LLM features, not required for
#    the controller's build/reconcile/compile/status/apply-alias actions)
python -m pip install --upgrade pip
pip install -r agent\requirements.txt

# 4. Run from the agent/ folder
cd agent
python -m mtagent status
```

## Setup — VS Code Terminal

Same steps, run inside VS Code's integrated terminal (View → Terminal, or
`` Ctrl+` ``). If VS Code doesn't auto-activate the venv, select it via
`Ctrl+Shift+P` → **Python: Select Interpreter** → `.venv\Scripts\python.exe`,
then reopen the terminal so activation happens automatically on each new
terminal tab.

```powershell
cd C:\Users\<you>\Projects\mt-dashboard\agent
python -m mtagent status
```

## Start command

```powershell
python -m mtagent chat
```

or, for a single one-time instruction without staying in a session:

```powershell
python -m mtagent run "<instruction>"
```

## The standard response shape

Every `run`/`chat` action ends with this, whether it passed, failed, or
was blocked on approval:

```
Run status: PASS / FAIL / BLOCKED

Desired output:
<what this action was trying to achieve>

Completed stages:
- <stage name>: PASS/FAIL/BLOCKED (<detail if any>)

Key results:
- <k>: <v>

Files created:
- <path>

Approval required:
<question, or "None">
```

## Five realistic MT analyst examples

**1. Morning check — is the pipeline healthy?**
```powershell
python -m mtagent status
```
Shows completion %, current phase, blockers, warnings, and the last few
worklog entries. Read-only, no approval needed.

**2. Rebuild after a new offtake month lands**
```powershell
python -m mtagent run "rebuild the dataset"
```
Shows the plan (entry/exit conditions, expected output files), then runs
`build-dataset` for real. Generates gitignored build output — no approval
needed, but stops and reports plainly if `blocked_reason` comes back
non-empty (e.g. missing source columns).

**3. Confirm the build is trustworthy before touching Power BI**
```powershell
python -m mtagent run "check reconciliation"
```
BLOCKED if no build exists yet ("build_dataset must run first" — never
silently builds one for you). FAIL if variance exceeds tolerance — and a
FAIL here means `compile_model` should not be run next.

**4. Record a scoped chain alias, same shape as the June'26 mapping work**
```powershell
python -m mtagent run 'apply "Apollo Healthco" to "Apollo" for the secondary file only'
```
Refuses outright (never silently accepts) if the canonical target looks
like a raw store/ship-to code instead of a real chain name. If the
canonical isn't in `ChainMaster.csv` at all, it's still recorded but
explicitly flagged, never silently promoted to canonical.

**5. End-of-day: what happened, and is anything waiting on me?**
```powershell
python -m mtagent log --tail 10
python -m mtagent status
```
`log` shows the structured worklog entries (desired output, stage
results, reconciliation, files created, approval status) for everything
run today. `status` names the next manual/approval step if one is
pending.

## Approval boundary — the one rule that never bends

Read-only checks (`status`, `reconciliation` checks) and actions that
only produce gitignored build output (`build-dataset`, `compile-model`,
`apply-alias` records) run automatically. **Anything destructive —
commit, push, overwrite an approved file, publish, delete, or share
externally — always shows `BLOCKED` and the exact approval question
until you pass `--approve` on that specific invocation** (or type
`approve: <instruction>` in `chat`). The controller itself never calls
`git commit`/`git push` even when approved — that stays with the
orchestrating session, as a second, deliberate step.
