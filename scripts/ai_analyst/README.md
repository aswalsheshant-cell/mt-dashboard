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

## What Phase 1 is / isn't

**Is:** a working, tested, offline NL→SQL core with a clean model boundary and a
safety sandbox, runnable on your real files today.

**Isn't (next phases):** the in-dashboard AI panel (P2), PDF/EDA ingest (P3), the
sentence-transformers + FAISS learning loop (P4), and report export (P5). The
offline provider is a deterministic fallback, **not** a substitute for the local
model — point it at Ollama for real language understanding.
