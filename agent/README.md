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

## Setup

```bash
cd <repo-root>

# 1. optional deps (see agent/requirements.txt for offline-install steps)
pip install -r agent/requirements.txt

# 2. optional local LLM
ollama pull llama3.1:8b        # chat
ollama pull nomic-embed-text   # embeddings

# 3. see what you have
python -m mtagent doctor       # run from repo root, or: PYTHONPATH=agent
```

> All commands are `python -m mtagent …` run from `agent/` (or add `agent/`
> to `PYTHONPATH`). Config defaults live in `mtagent/config.py`; copy
> `agent/config.example.json` to `agent/config.json` to override (models,
> Ollama URL, top-k, paths). `OLLAMA_HOST` is honoured.

## Commands

| Command | What it does |
|---|---|
| `doctor` | report which optional deps / Ollama models / artifacts are present |
| `index [--rebuild]` | build the local vector index over docs, DAX, Power Query, CSV shapes, PDFs, and Power BI metadata exports |
| `ask "…"` | retrieval-augmented answer from the local model, with sources; without Ollama it prints the retrieved passages |
| `check-dax [--strict]` | lint `PowerBI/DAX/*.dax` (see codes below) |
| `check-pq [--strict]` | lint `PowerBI/PowerQuery/*.pq` |
| `check` | both lints + the DuckDB data-quality sweep; non-zero exit on errors |
| `db-build` | (re)build `agent/index/mt.duckdb` views over the committed CSVs |
| `sql list` / `sql run <name> --param k=v` / `sql exec "…"` | run the SQL templates in `agent/sql/` or ad-hoc SQL |
| `eval` | golden-QA retrieval eval + validator regression checks + template execution |

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
   — 63 unit tests: FY-rule pinning (incl. Python↔SQL-macro parity),
   lexer/balance/definition extraction, each lint code positive+negative,
   metadata parsers, chunker regressions, index round-trip, golden retrieval
   bar. DuckDB-execution tests self-skip where duckdb isn't installed.

## Repo etiquette

Generated artifacts (`agent/index/`, `*.duckdb`, dropped metadata exports)
are gitignored — only code, templates, tests, seeds and docs are tracked.
The agent never fabricates numbers: every figure comes from the committed
CSVs via DuckDB, and `ask` answers only from retrieved repo passages.
