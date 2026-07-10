# ai_analyst — offline AI data-analyst agent (Phase 1)

Phase 1 of the blueprint (`ai-agent/BLUEPRINT.md`): a **natural-language → SQL**
engine that runs on your **real** export files, fully offline, with the LLM
interaction cleanly separated so it works **with no model installed**.

## Why it runs anywhere

| Concern | Choice |
|---|---|
| SQL engine | **DuckDB** when the `duckdb` package is present (fast, Parquet-ready); **stdlib `sqlite3`** fallback otherwise — no install, works air-gapped |
| Model | Local **Ollama** if reachable; otherwise a transparent **offline deterministic** translator — so the pipeline (and its tests) never require a model |
| Data egress | None by default. The remote provider is inert unless you pass `allow_data_egress=True` |
| Safety | Every generated query is validated to a **single read-only SELECT/WITH** before it touches the DB |

## Modules

- `data_layer.py` — **Module 1**: load CSV (and in-memory `window.DASH` rows) into the
  engine, sanitize/dedupe messy headers, expose schema, run read-only SQL.
- `nl2sql.py` — **Module 2**: question → validated SQL → results. Contains the
  read-only sandbox (`validate_sql`).
- `llm_provider.py` — **Module 3**: swappable backends behind one interface —
  `OfflineDeterministicProvider`, `OllamaProvider` (local), `RemoteOptInProvider` (gated).
- `profiler.py` — **Phase 3**: EDA profiling + cleaning suggestions over any loaded table
  (nulls, distincts, numeric stats, top categoricals, duplicates) — pure stdlib via the engine.
- `documents.py` — **Phase 3**: document ingest (text/markdown stdlib; PDF/XLSX via a
  pluggable backend) + deterministic offline extractive summarisation.
- `learning.py` — **Phase 4**: persistent learning — store corrections with a **real**
  embedding (stdlib hashing-TF; sentence-transformers optional) and retrieve by cosine
  similarity to reuse/inject them. SQLite-backed, per-machine, gitignored.
- `report.py` — **Phase 5**: assemble findings (text, KPIs, tables, EDA profiles, query
  results) and export to **Markdown/HTML/CSV** (stdlib) or **XLSX/PPTX** (pluggable:
  openpyxl / python-pptx). HTML is self-contained and matches the dashboard palette.
- `agent.py` — orchestrator (`Analyst`).
- `cli.py` — command line.

## CLI

```bash
# schema of a real seed file
python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters/ArticleMaster.csv schema

# translate only
python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters/ArticleMaster.csv \
    sql "how many articles by category"

# translate + run on the real data
python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters/ArticleMaster.csv \
    ask "distinct brand"

# load a whole folder; force backends
python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters \
    --provider offline --engine sqlite ask "articles by sub category"

# EDA profile + cleaning suggestions for a table (Phase 3)
python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters/ArticleMaster.csv \
    profile --table articlemaster

# summarise a document — text/markdown now; .pdf/.xlsx with a backend installed (Phase 3)
python scripts/ai_analyst/cli.py summarize path/to/report.txt --sentences 3

# readiness check (engine, provider, live LLM if present)
python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters doctor

# persistent learning (Phase 4): teach a correction, then it's reused
python scripts/ai_analyst/cli.py --data <csv> --learn \
    learn --question "revenue by category" --sql 'SELECT "category", ... '
python scripts/ai_analyst/cli.py --data <csv> --learn ask "revenue by category"   # -> (via learned)
python scripts/ai_analyst/cli.py --learn lessons                                    # store stats

# report export (Phase 5): profile + questions -> .html/.md/.csv/.xlsx/.pptx
python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters/ArticleMaster.csv \
    report --out report.html --title "MT Analysis" --table articlemaster \
    --ask "how many articles by category" --ask "distinct brand"
```

`--data` is repeatable (`--data fileA --data dirB`). `--provider` ∈
`auto|offline|ollama|remote`; `--engine` ∈ `auto|sqlite|duckdb`.

### Verified output (real `ArticleMaster.csv`, offline provider + sqlite)

```
ask "how many articles by category"
  SELECT "category", COUNT(*) AS n FROM "articlemaster" GROUP BY "category" ORDER BY n DESC
  Face Care | 7
  Sun Care  | 4
  Hair Care | 2
```

## Library

```python
from ai_analyst import Analyst
a = Analyst(provider="auto", engine="auto")   # local model+duckdb if present
a.load_dir("PowerBI/SeedData/Masters")
res = a.ask("how many articles by category")
print(res.sql, res.rows)                       # QueryResult(sql, columns, rows, ...)
```

## Using a local model (on your machine)

```bash
# install Ollama, then:
ollama pull mistral
ollama serve            # http://localhost:11434
# provider=auto now uses it automatically; no data leaves the machine
```

## Tests

Stdlib `unittest`, no dependencies. They load the **real** committed seed CSVs and
assert grounded results (e.g. group-by counts sum to the true row count) plus the
read-only sandbox (DROP/DELETE/PRAGMA/statement-stacking are rejected).

```bash
python scripts/ai_analyst/run_tests.py     # 30 tests
```

## Status

**Done — Phase 1:** offline NL→SQL core with a clean model boundary and read-only sandbox.
**Done — Phase 3:** EDA profiling + cleaning suggestions, and document ingest + offline
summarisation. Both run and are tested on the real seed files today.
**Done — Phase 4:** persistent learning — corrections stored with real embeddings and
reused via cosine similarity (offline path reuses verbatim; a model gets them as few-shot).
**Done — Phase 5:** offline report export to Markdown/HTML/CSV (stdlib) and XLSX/PPTX
(pluggable), assembled from EDA profiles and query results.

**Remaining:** the in-dashboard AI panel (P2, needs a live local model to be useful) and
an optional FAISS + sentence-transformers upgrade for the learning store at scale.

The offline provider is a deterministic fallback, **not** a substitute for the local
model — point it at Ollama for real language understanding. PDF/XLSX ingest needs a
backend on your machine (`pip install pdfplumber openpyxl`); text/markdown work with no
dependencies.
