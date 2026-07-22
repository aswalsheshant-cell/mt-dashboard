# mtagent — Local Offline Analytics Agent

A fully local assistant for the Honasa/Mamaearth **Modern Trade** repo. It
runs on the analyst's machine with **no network access required**: local LLM
via [Ollama](https://ollama.com), local SQL via DuckDB, a file-based vector
index, and pure-Python validators for the Power BI build kit.

```
        ┌────────────────────────── your machine ──────────────────────────┐
        │                                                                  │
question ─→ vector index ─→ top-k passages ─→ Ollama (llama3.1) ─→ answer  │
        │      ▲                                    ▲                      │
        │      │ index                              │ (optional — falls    │
        │  docs / DAX / PQ / CSV shapes /           │  back to showing     │
        │  PDFs / model.bim metadata exports        │  passages)           │
        │                                                                  │
 sql ────→ DuckDB ←─ committed CSVs (RawDataFolders + SeedData)            │
 check ──→ DAX validator + Power Query lint + SQL data-quality sweep       │
        └──────────────────────────────────────────────────────────────────┘
```

Everything degrades gracefully: **no Ollama** → hashed-TF-IDF retrieval and
passage output instead of generated answers; **no duckdb** → SQL commands
explain what to install, everything else still works. The core needs only
Python 3.10+ stdlib.

## Setup (local machine SOP)

Python 3.10+ required. All pip dependencies are **optional** — the agent
runs stdlib-only with graceful fallbacks — but for the full experience
(DuckDB SQL, PDF ingestion, LLM answers) follow all three steps.

### 1. Python dependencies in a virtual environment

**Windows (PowerShell):**

```powershell
cd <repo-root>
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r agent\requirements.txt
```

**macOS / Linux:**

```bash
cd <repo-root>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r agent/requirements.txt
```

If PyPI is blocked by the corporate network, use an approved internal
package mirror:

```bash
pip install --index-url https://<internal-pypi-mirror>/simple -r agent/requirements.txt
```

Alternatively, download wheels on an internet-connected machine and
transfer them across:

```bash
pip download -r agent/requirements.txt -d wheels
pip install --no-index --find-links wheels -r agent/requirements.txt
```

### 2. Ollama (local LLM — optional)

Install Ollama from your approved software channel, then fetch the models:

```bash
ollama pull llama3.1:8b        # chat model
ollama pull nomic-embed-text   # embedding model
ollama serve                   # only if no Ollama service is already running
                               # (the Windows/macOS desktop app serves automatically)
```

Verify:

```bash
ollama list
```

### 3. Verify and run the tests inside the activated venv

```bash
cd agent
python -m mtagent doctor                  # every line should read [ok]
python -m unittest discover -s tests      # 63 tests; with duckdb installed the
                                          # 3 DuckDB-execution tests run instead of skipping
python -m mtagent eval                    # retrieval bar + validators + all 8 SQL
                                          # templates now EXECUTE against DuckDB
python -m mtagent check                   # lint + live data-quality sweep
```

> All commands are `python -m mtagent …` run from `agent/` (or add `agent/`
> to `PYTHONPATH`). Config defaults live in `mtagent/config.py`; copy
> `agent/config.example.json` to `agent/config.json` to override (models,
> Ollama URL, top-k, paths). `OLLAMA_HOST` is honoured.
>
> **Cloud (Claude Code on the web) note:** whether `pip`/`ollama` work in a
> remote session is governed by the environment's network policy — if
> `pypi.org` / `files.pythonhosted.org` are denied (HTTP 403), the agent
> still runs with its stdlib fallbacks; allow those hosts in the
> environment settings to run the full-dependency suite there.

## Commands

| Command | What it does |
|---|---|
| `doctor` | report which optional deps / Ollama models / artifacts are present |
| `index [--rebuild]` | build the local vector index over docs, DAX, Power Query, CSV shapes, PDFs, and Power BI metadata exports |
| `ask "…"` | retrieval-augmented answer from the local model (analyst persona, sources cited); without Ollama it prints the retrieved passages |
| `meeting "…"` | **/meeting mode**: terse leadership shape — Answer / Top 3 drivers / Recommended response / Data quality / Next action |
| `meeting "…" --drilldown` (or `--verbose`) | lifts the brevity limit and injects **computed** tables: top-N underperforming outlets (MoM NSV), sub-category & pack-size mix deltas, and GST/TOT row confidence (Finance signed-off vs Pending). Without Ollama the computed tables print raw |
| `check-dax [--strict]` | lint `PowerBI/DAX/*.dax` (see codes below) |
| `check-pq [--strict]` | lint `PowerBI/PowerQuery/*.pq` |
| `check` | both lints + the DuckDB data-quality sweep; non-zero exit on errors |
| `qc` | **/qc mode**: everything `check` does + a coverage map against the analyst QC charter (what ran automatically, what needs Power BI Desktop) |
| `reconcile [--tol 0.5]` | **/reconcile mode**: dashboard `data.js` vs the committed source CSVs vs itself — internal totals, article-level blocks (FY27+ primary & offtake, per month), and preagg-vs-article INFO rows; exit 1 on any DIFF |
| `db-build` | (re)build `agent/index/mt.duckdb` views over the committed CSVs |
| `sql list` / `sql run <name> --param k=v` / `sql exec "…"` | run the SQL templates in `agent/sql/` or ad-hoc SQL |
| `catalog [--rebuild]` | categorize every tracked file into business categories with purposes (writes `agent/index/catalog.json`) |
| `find "…"` | search the catalog: *where is the chain master? where do GST rates live?* |
| `place <filename>` | *where does this new file go?* — target folder, naming rule, the exact refresh command, **plus the Proactive Exception Report**: newest vs prior offtake month — (1) Zone/Chain-DC NSV drops beyond the threshold (default 10% MoM, `mom_drop_threshold_pct`), (2) NPI zero-sales / zero-store-availability tracking (drop `PowerBI/SeedData/Masters/NPI_List.csv` for the real list; a labelled prior-month proxy is used otherwise), (3) operational gaps — stores that billed last cycle but have zero records now, with NSV at risk |
| `log [--tail N]` | audit trail: every command run is logged to `agent/index/worklog.jsonl` (timestamp, args, exit status) |
| `eval` | golden-QA retrieval eval + validator regression checks + template execution |
| `pbi <command>` | **Power BI Workflow Controller** (Module 2) — stateful, resumable dashboard-build pipeline. See [`agent/PBI_WORKFLOW.md`](PBI_WORKFLOW.md) for the full command reference, sample config/output, and what remains manual inside Power BI Desktop |
| `mcp-serve` | run mtagent as an **MCP server** over stdio, for any MCP client (Claude Desktop, Claude Code, etc.) — see below |

### MCP server

`python -m mtagent mcp-serve` exposes a curated set of mtagent commands as
MCP tools over stdio (`mtagent/mcp_server.py`). No `mcp` SDK dependency —
it implements the stdio JSON-RPC 2.0 transport directly in stdlib, the same
"eliminate the dependency" approach used elsewhere in this agent, since
`pip install mcp` is not obtainable in every environment this runs in.

Tools exposed (v1), each checked against its real code path and classified
before any mutating tool gets added:

| Tool | Category | Side effects |
|---|---|---|
| `ask` | read_only | may lazily build/cache `agent/index/index.json` on first use |
| `status` | read_only | none |
| `reconcile` | read_only | none |
| `find` | read_only | may lazily build/cache `agent/index/catalog.json` on first use |
| `worklog_tail` | read_only | none |
| `pbi_status` | read_only | none |
| `pbi_build_dataset` | local_file_write | writes `agent/pbi_build/<build_id>/*.csv` + workflow state; never git |
| `pbi_reconcile_model` | local_file_write | writes a reconciliation report + workflow state; never git |

Every tool also carries the MCP-native `annotations` (`readOnlyHint`,
`destructiveHint`, `idempotentHint`, `openWorldHint`) in `tools/list`, so a
client can reason about safety without reading this table. No tool is
`destructiveHint: true` — the two `local_file_write` tools only add/overwrite
their own generated output, never touch source data or git. Nothing in the
`state_mutation` or `high_impact_mutation` tiers (`apply-alias`,
`mark-complete`, `compile-model`, any git operation) is exposed yet, and a
test (`TestSafetyClassification.test_no_state_mutation_or_high_impact_tools_
exist_yet`) pins that boundary so adding one is a deliberate, visible change.

Each tool is a thin wrapper around the exact function its CLI equivalent
calls — no duplicated logic, so a fix to one path fixes both.

**Validation:** `tests/test_mcp_server.py` (unit-level, protocol edge cases:
malformed/empty lines, unusual request IDs, non-serializable tool results,
broken-pipe handling) and `tests/test_mcp_server_integration.py` (a real
`mcp-serve` subprocess driven over actual stdin/stdout pipes — full
handshake, all 8 tools, unicode, large-output framing, 10 sequential
requests, clean shutdown, and a check that stdout carries nothing but
valid JSON across every tool call). No real MCP client (Claude Desktop,
the official `@modelcontextprotocol/inspector`) is reachable from this
environment — Claude Desktop is a desktop GUI app not present in this
sandbox, and `npx @modelcontextprotocol/inspector` hits the same
`registry.npmjs.org` 403 that blocks every other package index here. The
real-subprocess integration suite is the closest available substitute; if
you have Claude Desktop, adding this server per the config below and
confirming the 8 tools list/call correctly is the one check that
substitute can't fully replace.

To add this server to an MCP client config (e.g. Claude Desktop's
`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mtagent": {
      "command": "python3",
      "args": ["-m", "mtagent", "mcp-serve"],
      "cwd": "/path/to/mt-dashboard/agent"
    }
  }
}
```

Mutating commands beyond the two above (`derive-article-master`,
`apply-alias`, `compile-model`, `mark-complete`, ...) are not exposed yet —
add them to `TOOLS` in `mcp_server.py` the same way if/when needed.

### Analyst persona & business rules

`ask`/`meeting` answers are governed by `mtagent/persona.py` — the MT
Channel Analyst charter (workflow: intent → datasets → data readiness →
business rules → analysis → QC → insight) plus the approved business rules:
Apr–Mar FY via THE ONE FY RULE, NSV in Lakh (×100000 = ₹, ÷100 = Cr), NSV
net of tax vs MRP incl. tax (never compare silently), Others included in
totals, **Pending ≠ Zero**, the FY27 coverage split, Cont% distributor
allocation, and the GST 2.0 cutover for TOT%. Edit that file to evolve the
charter; `tests/test_catalog_reconcile.py::TestPersona` pins the
load-bearing rules.

### Data contract (ingestion robustness)

Applied consistently in the DuckDB views, the diff engine, and the FY rules:

- **String standardization** — lookup dimensions (Chain Name, Site/Store
  Name, DC Code, Ship-To, descriptions) are TRIM+UPPER-normalized at load,
  so casing/trailing-space variants can never split one chain into two.
- **Date normalization** — month labels of **any** source style parse
  everywhere: `Apr-26`, `Apr'26`, `Apr 2026`, and raw Excel date serials
  incl. floating points (`46113.0`/`46113.5` = Apr-2026, Excel 1900 date
  system, epoch 1899-12-30 — verified against this repo's own offtake data,
  where 32k+ real rows carry serials).
- **Missing-mapping guard** — `db-build` never drops an unmapped row:
  every Chain/Store/Article value absent from the active masters is
  quarantined into the **`unmapped_staging`** table (entity, row count, NSV
  impact) with a `STRUCTURAL WARNING` in the build log, and surfaces in the
  `data_quality` template. Store/Article guards engage once the
  corresponding master is real (≥100 rows) — the committed seeds are small
  samples.

### DAX validator codes

| Code | Severity | Meaning |
|---|---|---|
| DAX001 | error | unbalanced `( ) [ ]` / unterminated string |
| DAX002 | error | duplicate definition name across files (collides when pasted into one model) |
| DAX003 | warn | reference to a table missing from the model inventory |
| DAX004 | info | raw `/` division (repo convention: `DIVIDE()`) |
| DAX005 | info | hardcoded FY / `DATE(20xx,…)` literal — see THE ONE FY RULE in `CLAUDE.md` |
| DAX006 | warn | `[ref]` that is no known measure/column (only with a real metadata export) |

### Power Query codes

| Code | Severity | Meaning |
|---|---|---|
| PQ001 | error | missing `let/in` (parameter queries exempt) |
| PQ002 | error | unbalanced `( ) [ ] { }` / unterminated string |
| PQ003 | error | `in` result is not a defined step |
| PQ004 | warn | dead step (defined, never referenced) |
| PQ005 | warn | hardcoded absolute path — must flow through `pRootFolder` |
| PQ006 | warn | referenced `RawDataFolders`/`SeedData` path missing from the repo |
| PQ007 | info | fact query without `Table.TransformColumnTypes` |

The model inventory for DAX003/DAX006 comes from **`agent/metadata/`**
(`model.bim` from Tabular Editor, or DAX Studio `INFO.*()` CSV exports — see
`agent/metadata/README.md`); with no export it falls back to parsing
`PowerBI/docs/DataModel.md`.

### SQL templates

Templates live in `agent/sql/*.sql` with a small comment header
(`-- name:` / `-- description:` / `-- param: x default=y`); placeholders are
`{{param}}`. The DuckDB layer defines **THE ONE FY RULE as SQL macros**
(`fy_from_ym`, `fy_from_label`, `fy_quarter`) and a unit test pins them to
the Python helpers, so every query derives FY from month+year — never from a
column position. Views: `v_primary_article`, `v_offtake`,
`v_primary_shipto`, plus one `m_*` view per SeedData master.

```bash
python -m mtagent sql run chain_ranking --param fy=FY26
python -m mtagent sql run data_quality          # every row should be 0
python -m mtagent sql exec "SELECT fy_from_label('Apr''26')"   # FY27
```

To add a template: drop a new `.sql` in `agent/sql/` with the header — it
shows up in `sql list` and gets executed by `eval` automatically.

## Evaluation

Two layers, both offline:

1. **`python -m mtagent eval`** — retrieval hit@3 over
   `agent/evals/golden_qa.jsonl` (bar: 70%, must pass even on the
   zero-dependency fallback embedder), validator regression over the repo's
   real DAX/PQ corpus (one *known* pre-existing defect is allowlisted:
   `QC Mapping Coverage %` is defined with different formulas in
   `08_ForecastQC_Measures.dax` and `09_ArticleAllocation_Eligibility.dax`),
   and render/execute of every SQL template.
2. **`python -m unittest discover -s agent/tests`** (or `pytest agent/tests`)
   — 146 unit + integration tests: FY-rule pinning (incl. Python↔SQL-macro
   parity), lexer/balance/definition extraction, each lint code
   positive+negative, metadata parsers, chunker regressions, index
   round-trip, golden retrieval bar, and the Power BI Workflow Controller
   (state machine, evidence validation, dataset build against both
   synthetic fixtures and the real committed offtake CSV, DAX gap
   coverage, source-to-model reconciliation, full CLI wiring — see
   [`agent/PBI_WORKFLOW.md`](PBI_WORKFLOW.md)). DuckDB-execution tests
   self-skip where duckdb isn't installed.

## Repo etiquette

Generated artifacts (`agent/index/`, `*.duckdb`, dropped metadata exports)
are gitignored — only code, templates, tests, seeds and docs are tracked.
The agent never fabricates numbers: every figure comes from the committed
CSVs via DuckDB, and `ask` answers only from retrieved repo passages.
