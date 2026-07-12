"""Evaluation runner: retrieval quality + validator self-checks.

Retrieval: agent/evals/golden_qa.jsonl holds question -> acceptable source
paths; a question passes when any expected path appears in the top-k
retrieved chunks (hit@k). The bar is deliberately modest (>= 70%) because
the zero-dependency hashed-TF-IDF fallback must pass it too; with Ollama
embeddings the same set should score higher, never lower.

Validators: the repo's own DAX/PQ files are the fixture — they must lint
without NEW errors (the known pre-existing duplicate-measure defect is
allowlisted so the eval pins today's baseline and catches regressions).
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import Config

PASS_BAR = 0.70
# Pre-existing, genuine defect in the repo the validator is EXPECTED to find:
# 'QC Mapping Coverage %' defined with different formulas in 08_ and 09_.
KNOWN_DAX_ERRORS = {("DAX002", "QC Mapping Coverage %")}


def _allowlisted(finding) -> bool:
    return any(code == finding.code and token in finding.message
               for code, token in KNOWN_DAX_ERRORS)


def run_eval(cfg: Config, k: int = 3) -> int:
    from .dax_validator import validate_paths as vdax
    from .metadata import load_inventory
    from .pq_checks import validate_paths as vpq
    from .rag import ensure_index

    root = cfg.root()
    failures = 0

    # ---- 1. retrieval hit@k over the golden set ----
    golden = cfg.path("agent/evals/golden_qa.jsonl")
    cases = [json.loads(line) for line in
             golden.read_text(encoding="utf-8").splitlines() if line.strip()]
    idx, _ = ensure_index(cfg)
    hits = 0
    print(f"retrieval eval (hit@{k}, embedder={idx.embedder}):")
    for case in cases:
        got = idx.search(cfg, case["q"], k)
        ok = any(exp in p["source"] for exp in case["expect_any"] for p in got)
        hits += ok
        print(f"  [{'PASS' if ok else 'MISS'}] {case['q']}")
        if not ok:
            for p in got:
                print(f"         got {p['source']} :: {p['section']}")
    score = hits / len(cases) if cases else 0.0
    print(f"  score: {hits}/{len(cases)} = {score:.0%} (bar {PASS_BAR:.0%})")
    if score < PASS_BAR:
        failures += 1

    # ---- 2. validators over the real repo files ----
    inv = load_inventory(cfg.path(cfg.metadata_dir), root)
    dax = vdax(sorted((root / "PowerBI" / "DAX").glob("*.dax")), inv)
    new_dax_errors = [f for f in dax if f.severity == "error" and not _allowlisted(f)]
    known = [f for f in dax if f.severity == "error" and _allowlisted(f)]
    print(f"\nDAX validator over PowerBI/DAX: {len(dax)} finding(s), "
          f"{len(known)} known pre-existing error(s), "
          f"{len(new_dax_errors)} NEW error(s)")
    for f in new_dax_errors:
        print("  " + f.format())
    if new_dax_errors:
        failures += 1

    pq = vpq(sorted((root / "PowerBI" / "PowerQuery").glob("*.pq")), root)
    pq_errors = [f for f in pq if f.severity == "error"]
    print(f"PQ checks over PowerBI/PowerQuery: {len(pq)} finding(s), "
          f"{len(pq_errors)} error(s)")
    for f in pq_errors:
        print("  " + f.format())
    if pq_errors:
        failures += 1

    # ---- 3. SQL templates render + (if duckdb) execute ----
    from .sql_templates import list_templates, render
    templates = list_templates(cfg)
    rendered = []
    for t in templates:
        try:
            rendered.append((t.name, render(t)))
        except ValueError as e:
            print(f"  template {t.name}: FAILED to render: {e}")
            failures += 1
    print(f"\nSQL templates: {len(rendered)}/{len(templates)} render cleanly")
    try:
        from .duck import build_db, run_sql
        build_db(cfg)
        ran = 0
        for name, sql in rendered:
            try:
                run_sql(cfg, sql)
                ran += 1
            except Exception as e:
                print(f"  template {name}: FAILED to execute: {e}")
                failures += 1
        print(f"SQL templates executed on DuckDB: {ran}/{len(rendered)}")
    except Exception as e:
        print(f"SQL execution skipped (no duckdb here): {e}")

    print(f"\neval result: {'PASS' if failures == 0 else f'FAIL ({failures} section(s))'}")
    return 0 if failures == 0 else 1
