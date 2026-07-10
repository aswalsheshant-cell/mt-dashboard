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
  Supports a classification banner and green/red growth columns.
- `templates.py` / `template_fill.py` / `provenance.py` / `qc.py` — **Phase 6**:
  **Template Fill Mode**. A registry of leadership formats (MT Monthly Offtake, QBR,
  Nielsen deep dive, …) filled ONLY from user-supplied source files, with an audit
  (Considered/Not Considered) sheet, per-number source provenance, and a pre-export QC
  report. Missing sources become "Source data required" — never invented numbers.
- `xlsx_qc.py` — **Phase 7**: stdlib **Workbook QC scanner** for `.xlsx`. Detects formula/
  `#REF!` errors, hidden sheets, merged cells in data sheets, duplicate keys, blank
  mappings, mixed date formats, and anomalous/near-duplicate filter labels (e.g. a stray
  `METock`, or `West`/`WEST`). Emits a `QC_Check` table (Check/Tool/Tab/Source/Status/
  Remarks/Action); writes it back as a sheet via openpyxl, or renders md/html/csv offline.
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

# template fill mode (Phase 6): fill a leadership format from source files only
python scripts/ai_analyst/cli.py templates                       # list formats
python scripts/ai_analyst/cli.py template --format "MT Monthly Offtake Report" \
    --period "May'26" --compare "Apr'26" \
    --source offtake "May'26" .../offtake_store_article_May_26.csv \
    --source offtake "Apr'26" .../offtake_store_article_Apr_26.csv \
    --out report.html --out working.xlsx --out deck.pptx

# workbook QC (Phase 7): scan an .xlsx and emit a QC_Check (finds 'METock' etc.)
python scripts/ai_analyst/cli.py qc-workbook --file dashboard.xlsx \
    --dup Raw_Data StoreKey --date Raw_Data MonthDate \
    --filter Raw_Data Channel MT,GT,EB2B,SIS \
    --out QC_Check.html --write-sheet
```

### Template Fill Mode guarantees
- **Numbers only from sources.** Missing dataset/period → `Source data required`, never a guess.
- **Audit sheet** — every file/sheet/rows/columns/filter Considered or Not Considered, with reasons.
- **Source provenance** for each key number (file, column, filter, calculation).
- **QC before export** — total, MoM, YoY, contribution %, missing-mapping, duplicate,
  unmapped chain/article, and MT-vs-GT checks (NA when a source is absent).
- **'Others' hidden** from visible tables but **included in totals**; growth shown green/red;
  classification banner (e.g. "Confidential - MT Internal"); fully offline, no external transfer.

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
**Done — Phase 6:** Template Fill Mode — leadership formats filled only from source files,
with audit, provenance, QC, 'Others' handling, growth colouring and a classification banner.

**Remaining:** the in-dashboard AI panel (P2, needs a live local model to be useful), an
optional FAISS + sentence-transformers upgrade at scale, and a later local scheduler.

The offline provider is a deterministic fallback, **not** a substitute for the local
model — point it at Ollama for real language understanding. PDF/XLSX ingest needs a
backend on your machine (`pip install pdfplumber openpyxl`); text/markdown work with no
dependencies.
