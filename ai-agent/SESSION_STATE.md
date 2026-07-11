# Session state — offline AI data-analyst agent (resume point)

**Branch:** `claude/offline-ai-data-analyst-iiincp`  ·  **PR:** #14 (draft, CI green via Vercel)
**Last updated:** 2026-07-10

Pick up from here. Nothing below is finalized beyond what's committed to the branch.

---

## Delivered & pushed (all on PR #14)

| Item | Where | Tests |
|---|---|---|
| Design blueprint | `ai-agent/BLUEPRINT.md` | — |
| **P1** NL→SQL core + read-only sandbox + swappable LLM providers | `scripts/ai_analyst/{data_layer,nl2sql,llm_provider,agent,cli}.py` | ✅ |
| P1.5 live-LLM readiness (prompt tuning, `doctor`, integration test) | `llm_provider.py`, `tests/test_ollama_integration.py` | ✅ (skips w/o Ollama) |
| **P3** EDA profiling + cleaning suggestions; document ingest + summary | `profiler.py`, `documents.py` | ✅ |
| **P4** persistent learning (real hashing-TF embeddings + cosine retrieval) | `learning.py` | ✅ |
| **P5** report export md/html/csv (stdlib) + xlsx/pptx (pluggable) | `report.py` | ✅ |
| **P6** Template Fill Mode (registry, provenance, QC, audit, watermark) | `templates.py`, `template_fill.py`, `provenance.py`, `qc.py` | ✅ |
| **P7** stdlib `.xlsx` Workbook QC scanner (finds `METock`) → `QC_Check` | `xlsx_qc.py`, `tests/test_xlsx_qc.py` | ✅ |
| **Power BI kit hardening** (audit approved; negative NSV = valid, not error) | `PowerBI/PowerQuery/*.pq`, `PowerBI/DAX/*.dax`, `PowerBI/QuickSetup/*` | ✅ text-verified (no live PBI here) |

**Test status:** 95 tests pass, 2 skipped (live Ollama). Run: `python scripts/ai_analyst/run_tests.py`.
Latest commit at save time: `58eeef3` (Phase 7).

---

## Environment constraints (this remote container)
- **PyPI blocked (403)** → cannot install `duckdb`, `pandas`, `openpyxl`, `python-pptx`, `sentence-transformers`. Everything runs on the **standard library**; heavier backends are pluggable and used on the user's machine.
- **No Ollama** here → live-model path is code-complete but validated only on the user's machine (`ollama serve`; `cli.py ... doctor`).
- Real data available in-repo for tests: `PowerBI/SeedData/Masters/ArticleMaster.csv`, and `PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_{Apr,May}_26.csv`.

---

## Power BI kit hardening — DONE (approved, applied, pushed)

Commits: canonical PQ+DAX (`a338ea6`), QuickSetup sync (`4c36344`). Applied audit
fixes P1,P2,P3,P6 (Power Query) and D1,D2,S1,S2 (DAX) to the canonical files AND
the QuickSetup consolidated mirror. **Business rule locked: negative NSV = valid
returns/credit notes, NOT a data-quality error.** Not runnable in this env (no
Power BI) — verified by reading; user must run the audit §8 validation on refresh.

## NEXT ACTION (blocked on user) — deep workbook QC + HTML filter (still gated)

Remaining, gated on the user sending the `.xlsx`:
1. **Excel workbook deep-QC** — run `scripts/ai_analyst/xlsx_qc.py` on the file, deliver
   `QC_Check` + cell-by-cell fix list (stdlib scanner works here; openpyxl needed only to
   write the sheet back / apply fixes on the user's machine).
2. **HTML filter normalization** (`dashboard/index.html`) — still gated per user; mirror
   the P6 canonicalisation rule (trim/clean + Proper-case Zone/State so West/WEST collapse),
   add a "last updated" stamp. Preserve layout/logic.

### Blocker
The `.xlsx` workbook is **not in the repo** (gitignored) and was not attached yet.
"METock" exists only in that workbook — not anywhere in this repo.

**To resume:** user attaches the `.xlsx` to a message (lands in `/root/.claude/uploads/...`),
or force-adds it (`git add -f`). Then:

1. **Deep QC** across all tabs with `scripts/ai_analyst/xlsx_qc.py` (stdlib reader — works here):
   errors/`#REF!`, broken cross-tab links, chart ranges, hidden sheets, merged cells,
   duplicate keys (Store/Article/Chain-Article/Month), blank/duplicate/unmapped mappings
   (Chain/Account/Format/Brand/Category/Subcat/Range/PackSize/Article/EAN/Zone/State/City),
   date/month/year consistency, filter values (incl `METock`, `West`/`WEST`), totals reconcile.
   Command:
   ```
   python scripts/ai_analyst/cli.py qc-workbook --file <wb.xlsx> \
     --filter <Sheet> <ChannelCol> MT,GT,EB2B,SIS \
     --dup <Sheet> <KeyCol> --date <Sheet> <DateCol> \
     --out QC_Check.html
   ```
2. Deliver `QC_Check` + a prioritized, cell-by-cell **fix list**.
3. **Applying fixes:** cannot rewrite binary `.xlsx` here (no openpyxl). Deliver as
   (a) a remediation spec to apply in Excel, and/or (b) a small **openpyxl fixer script +
   corrected mapping CSVs / Power Query steps** the user runs locally (repeatable monthly).
4. Only after the workbook is QC-passed & verified → proceed to:
   - **DAX/PQ hardening**: audit `PowerBI/DAX/*.dax` (already `DIVIDE`-safe) + `PowerBI/PowerQuery/*.pq`
     — one consistent date table, blank/NA/Pending handling, clean helper columns, mapping usage.
   - **HTML filter normalization**: `dashboard/index.html` filter builder (~lines 1480–1560,
     `FILT=[...]`) — trim + case-dedupe filter values (fix `West`/`WEST`), add "last updated" stamp.
     Preserve layout/logic; only fix the label/dedup bug.

---

## PR watch
Subscribed to PR #14 activity. Only Vercel deploy events so far (all Building→Ready, CI green).
No review comments needing action. Subscription continues until PR merged/closed.
