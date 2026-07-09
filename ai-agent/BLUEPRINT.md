# Offline AI Data-Analyst Agent — Build Blueprint

**Project:** Honasa / Mamaearth — Modern Trade (MT) Leadership Analytics
**Goal:** An offline-first AI agent that works like a data analyst — cleaning, analysing,
querying, visualising, forecasting, and reporting — **without any data leaving the machine**,
while **continuously learning** from the user's corrections.

This document is the single source of truth for the design. It folds together three inputs:
1. The multi-tool analyst workflow (SQL · Python · Excel · Power BI · PDF).
2. The offline-agent requirements (hardware, software, capabilities, security, skills).
3. The architecture that actually fits **this** repo (Python pipeline + offline HTML dashboard).

> **Runtime note.** This repo is **Python** (`scripts/*.py`) + a **vendored, double-click-to-open
> HTML dashboard** (`dashboard/index.html`). The reference implementation below is therefore
> **Python + browser-JS calling a local model** — deliberately *not* a new Node.js service, so it
> stays offline, reuses `window.DASH` and pandas, and needs no build step.

---

## 1. What "good" looks like (objectives & KPIs)

| Objective | Concrete deliverable | Success metric |
|---|---|---|
| Offline operation | Runs with network cable unplugged | 100% of core tasks work air-gapped |
| No data leakage | Raw data never sent to any cloud endpoint by default | 0 outbound calls with data unless user opts in per-request |
| Document analysis | PDF/Excel → structured summary + Q&A | Extracts + answers on the attached-style reports |
| SQL / NL querying | Plain English → SQL/pandas grounded in real schema | Query runs against real `data.js` / CSVs, no invented tables |
| Dashboard insights | Narrative insight cards from real `window.DASH` numbers | Insights cite actual FY25/FY26/FY27 figures |
| Continuous learning | Corrections improve later answers | Measurable retrieval hit on repeated question types |
| Reporting | One-click PDF / Excel / PPT summary | Matches existing dashboard export look |

---

## 2. Architecture (fits this repo)

```
┌──────────────────────────────────────────────────────────────────────┐
│                    OFFLINE AI DATA-ANALYST AGENT                       │
│                                                                        │
│  ┌───────────────────────────┐      ┌──────────────────────────────┐  │
│  │  ① In-dashboard AI panel  │      │  ② Python companion CLI       │  │
│  │  (new tab in index.html)  │      │  (scripts/ai_analyst/)        │  │
│  │  • grounded in window.DASH│      │  • PDF / Excel / CSV ingest   │  │
│  │  • insight cards, NL Q&A  │      │  • pandas EDA + profiling     │  │
│  │  • localStorage feedback  │      │  • SQL/pandas drafting        │  │
│  │  • fetch → localhost LLM  │      │  • report gen (PDF/XLSX/PPTX) │  │
│  └────────────┬──────────────┘      └───────────────┬──────────────┘  │
│               │                                      │                 │
│               └──────────────┬───────────────────────┘                 │
│                              ▼                                          │
│              ┌───────────────────────────────┐                         │
│              │  Local model server (Ollama /  │  http://localhost:11434 │
│              │  LM Studio)  Mistral / Llama    │  ← never leaves machine │
│              └───────────────┬───────────────┘                         │
│                              ▼                                          │
│   ┌───────────────┐  ┌────────────────┐  ┌───────────────────────────┐ │
│   │ Local vector  │  │ Learning store │  │ Sandboxed code executor   │ │
│   │ index (RAG)   │  │ SQLite/DuckDB   │  │ (subprocess, no network)  │ │
│   │ real embeds   │  │ + encryption   │  │ runs generated pandas/SQL │ │
│   └───────────────┘  └────────────────┘  └───────────────────────────┘ │
│                                                                        │
│   ── Data-security layer: local-only I/O · encryption at rest ──       │
│   ── · per-request cloud opt-in with an audit log ──                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Why two front-ends, one brain:** the dashboard panel is for *reading* the already-built
`window.DASH` insights; the Python CLI is for *doing* heavy analyst work on new files. Both call
the same local model and share the same learning store, so a correction taught in one shows up in
the other.

---

## 3. Hardware requirements (right-sized, not maxed)

| Tier | CPU / GPU | RAM | Storage | Runs |
|---|---|---|---|---|
| **Minimum** | Modern 4-core CPU | 16 GB | 20 GB free SSD | 7B model (Q4) CPU-only, pandas EDA |
| **Recommended** | 8-core CPU **or** any 8 GB+ GPU / Apple M-series | 32 GB | 1 TB SSD | 7–13B model at speed, larger datasets in-memory |
| **Advanced** | NVIDIA 16 GB+ GPU | 64 GB | 1 TB+ NVMe | Local fine-tuning, 30B+ models, batch inference |

> Quantised 7B models (Mistral, Llama 3 8B) run acceptably CPU-only at 16 GB — GPU mainly buys
> speed and lets you fine-tune. Match the model size to the machine; don't over-buy.

---

## 4. Software stack (all offline-capable)

| Layer | Tools | Role |
|---|---|---|
| **Local LLM serving** | **Ollama** (recommended) or LM Studio | Run/serve Mistral·Llama fully offline via localhost |
| **ML / DL frameworks** | PyTorch · scikit-learn · ONNX Runtime | Predictive models, embeddings, optional fine-tune |
| **Data processing** | **pandas** · NumPy · **Polars** · **DuckDB** · SQLite | Wrangle, ETL, in-process SQL over files |
| **Visualisation** | Matplotlib · Seaborn · Plotly · Chart.js (already vendored) | Charts in reports + dashboard |
| **Document I/O** | pdfplumber / PyMuPDF · openpyxl · python-pptx | PDF/Excel/PPT read + write |
| **Embeddings / RAG** | sentence-transformers (local) · FAISS / Chroma | **Real** semantic retrieval for learning |
| **Orchestration** | Plain Python (stdlib) + a thin agent loop | Tool routing; no heavy framework needed |

> **DuckDB is the quiet hero here:** it runs real SQL directly over your CSV/Parquet/Excel exports
> with zero server setup — so "natural language → SQL" executes against *actual* files, not a
> fabricated schema.

---

## 5. Agent capabilities (the analyst skill set)

Each capability = one tool the agent can call. All run locally.

1. **Data cleaning & preprocessing** — missing-value report, dedupe, type coercion, outlier flags
   (IQR / z-score) via pandas. Suggestions are grounded in the *actual* profile of the loaded file.
2. **Descriptive analysis / EDA** — `df.describe()`-style stats, distributions, correlations,
   auto-generated summary written in plain English by the local LLM.
3. **Natural-language querying** — English → SQL (executed by DuckDB) **or** English → pandas.
   The schema is read from the real file, so no invented tables.
4. **Predictive modelling** — scikit-learn baselines (regression / classification / simple
   time-series) with an explanation of *why* a model under/over-fits.
5. **Visualisation generator** — chart specs from data; renders to PNG (reports) and Chart.js
   (dashboard), reusing the dashboard's existing palette.
6. **Automated report generation** — assemble findings into **PDF / Excel / PPTX** offline
   (python-pptx already used by `scripts/rebuild_mt_offtake_ppt.py` — reuse it).
7. **Dashboard insight cards** — read `window.DASH`, produce risk/win/watch narrative cards in the
   existing `.icard` style.

---

## 6. Continuous learning — done honestly

The learning loop must be **real**, not a placeholder. Design:

```
user asks ──► agent answers ──► user rates / corrects ──►
   store {question, answer, correction, domain} + REAL embedding ──►
   next similar question ──► retrieve top-k corrections ──►
   inject as few-shot context ──► better answer
```

- **Embeddings:** `sentence-transformers` (e.g. `all-MiniLM-L6-v2`, ~80 MB, runs offline).
  Real vectors → real cosine similarity. *(The earlier JS prototype faked this with
  `Math.random()` — that is explicitly replaced here.)*
- **Store:** SQLite or DuckDB table `feedback(question, answer, correction, domain, vector)`.
- **Retrieval:** FAISS or Chroma index for top-k nearest corrections, fed back as few-shot examples.
- **Escalation path (optional):** once you have hundreds of high-quality corrections in a domain,
  export them as an instruction/QLoRA dataset to fine-tune the local model — but retrieval-augmentation
  gets you 80% of the value with none of the training cost, so start there.

---

## 7. Security & data-leakage prevention

| Control | Implementation |
|---|---|
| **Local-only by default** | All inference via `localhost:11434`; no external hosts in the default path |
| **Per-request cloud opt-in** | Cloud model is a deliberate, logged choice showing exactly what would be sent |
| **Encryption at rest** | Learning store + cached extracts encrypted with a **user-supplied / OS-keychain** key — never a hardcoded key |
| **No raw-data logging** | Logs record query type, timing, schema shape — never cell values |
| **Sandboxed execution** | Generated pandas/SQL runs in a subprocess with **no network** and a timeout |
| **Audit trail** | Every cloud call appended to `ai-agent/data/audit.log` for review |
| **Reset / right-to-delete** | One command wipes the learning store and any cached extracts |

> ⚠️ The earlier JS prototype derived its AES key from a hardcoded string+salt — that is *not*
> secure and is replaced by an OS-keychain / user-passphrase key in this design.

---

## 8. Skills to build/operate this

- **Python:** pandas, scikit-learn, matplotlib (core).
- **SQL:** joins, window functions, CTEs — plus DuckDB for file-based SQL.
- **Local LLM deployment:** installing Ollama, pulling Mistral/Llama, prompt design, quantisation basics.
- **A little JS:** to wire the dashboard panel's `fetch` call (kept minimal, single `<script>` block).

---

## 9. Optional advanced features (later)

- **Voice querying** — offline speech-to-text (e.g. `whisper.cpp`) → same NL-query pipeline.
- **Local GUI** — the dashboard panel already serves as a no-code interface; can grow into a full app.
- **Automated alerting** — scheduled anomaly detection over new monthly drops, offline.

---

## 10. Phased roadmap

| Phase | Scope | Output |
|---|---|---|
| **P1 — Foundation** | Ollama + local model; Python `ai_analyst/` skeleton; DuckDB over existing CSV exports | NL→SQL that *runs* on real files |
| **P2 — Dashboard panel** | New "AI Analyst" tab in `index.html`; `fetch`→localhost; insight cards from `window.DASH` | In-dashboard Q&A + insights, offline |
| **P3 — Documents & EDA** | PDF/Excel ingest; pandas profiling; plain-English EDA summary | Analyse the attached-style reports |
| **P4 — Learning** | sentence-transformers embeddings + FAISS; feedback capture in both front-ends | Corrections measurably improve later answers |
| **P5 — Reporting & security** | PDF/XLSX/PPTX export (reuse python-pptx); encryption, sandbox, audit log | One-click reports + hardened security |

---

## 11. What already exists in this repo (reuse, don't rebuild)

- `scripts/build_dashboard_data.py` — the data model + FY logic. The agent should read its output
  (`window.DASH`), not re-derive it.
- `scripts/rebuild_mt_offtake_ppt.py`, `build_*_slide.py` — **python-pptx report generation** to reuse
  for the agent's PPT export.
- `dashboard/index.html` — 12-tab shell, filter bar, `.icard` insight styling, Chart.js — the AI
  panel plugs in as a 13th tab and reuses these styles.
- `dashboard/xlsx.core.min.js`, `chart.umd.js`, `jspdf.umd.min.js` — already-vendored libs for
  offline Excel/chart/PDF work in the browser.

---

### Status of the earlier prototype
The initial `ai-agent/*.js` (Node) files were a false start: fake embeddings, fabricated SQL against
a non-existent `sales` table, and a hardcoded encryption key. They are **superseded by this blueprint**
and should be removed before any Python implementation begins.
