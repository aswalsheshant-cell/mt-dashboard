#!/usr/bin/env python3
"""
Thin CLI for the offline AI data-analyst agent (Phase 1).

Examples:
    # show the schema loaded from real seed files
    python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters schema

    # translate only (no execution)
    python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters sql "how many articles by category"

    # translate + run
    python scripts/ai_analyst/cli.py --data PowerBI/SeedData/Masters ask "distinct brand"

    # force a backend
    python scripts/ai_analyst/cli.py --provider offline --engine sqlite --data <dir> ask "..."

By default the provider is 'auto' (local Ollama if reachable, else the offline
deterministic translator) and the engine is 'auto' (DuckDB if installed, else
stdlib sqlite3). Nothing leaves the machine.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# allow running as a plain script: put scripts/ on the path so `ai_analyst` imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_analyst.agent import Analyst  # noqa: E402


def _load(analyst: Analyst, data_args):
    for d in data_args:
        p = Path(d)
        if p.is_dir():
            analyst.load_dir(p)
        elif p.is_file():
            analyst.load_csv(p)
        else:
            print(f"warning: {d} not found", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Offline AI data-analyst agent (Phase 1).")
    ap.add_argument("--data", action="append", default=[], metavar="PATH",
                    help="CSV file or directory to load (repeatable: --data a --data b)")
    ap.add_argument("--provider", default="auto", choices=["auto", "offline", "ollama", "remote"])
    ap.add_argument("--engine", default="auto", choices=["auto", "sqlite", "duckdb"])
    ap.add_argument("--model", default="mistral", help="model name for the ollama provider")
    ap.add_argument("--learn", action="store_true", help="enable persistent learning store")
    ap.add_argument("--learning-db", default="scripts/ai_analyst/data/learning.db",
                    help="path to the learning store (implies --learn)")
    ap.add_argument("--domain", default="general", help="domain tag for learning")
    ap.add_argument("--json", action="store_true", help="emit JSON")

    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("schema", help="print the loaded schema")
    sub.add_parser("doctor", help="report engine + provider readiness (and a live LLM check)")
    p_sql = sub.add_parser("sql", help="translate a question to SQL (no execution)")
    p_sql.add_argument("question")
    p_ask = sub.add_parser("ask", help="translate and run a question")
    p_ask.add_argument("question")
    p_prof = sub.add_parser("profile", help="EDA profile + cleaning suggestions for a table")
    p_prof.add_argument("--table", default=None, help="table name (default: first loaded)")
    p_prof.add_argument("--sample", type=int, default=5000, help="max rows to profile")
    p_sum = sub.add_parser("summarize", help="read a document and summarise it")
    p_sum.add_argument("doc", help="path to a .txt/.md/.pdf/.xlsx document")
    p_sum.add_argument("--sentences", type=int, default=5, help="summary length")
    p_learn = sub.add_parser("learn", help="teach the correct SQL for a question (implies --learn)")
    p_learn.add_argument("--question", required=True)
    p_learn.add_argument("--sql", required=True)
    p_learn.add_argument("--rating", type=int, default=None)
    sub.add_parser("lessons", help="show learning-store stats (implies --learn)")

    args = ap.parse_args(argv)

    learning_on = args.learn or args.cmd in ("learn", "lessons") \
        or args.learning_db != "scripts/ai_analyst/data/learning.db"
    pkw = {"model": args.model} if args.provider in ("auto", "ollama") else {}
    analyst = Analyst(provider=args.provider, engine=args.engine, provider_kwargs=pkw,
                      learning=learning_on, learning_path=args.learning_db)
    _load(analyst, args.data)

    if args.cmd == "doctor":
        from ai_analyst.llm_provider import OllamaProvider
        print(f"engine (selected):   {analyst.data.engine}")
        try:
            import duckdb  # noqa: F401
            print("duckdb installed:    yes")
        except Exception:
            print("duckdb installed:    no (using stdlib sqlite3)")
        print(f"provider (selected): {analyst.provider.name}")
        oll = OllamaProvider(model=args.model)
        up = oll.is_available()
        print(f"ollama reachable:    {'yes' if up else 'no'} ({oll.endpoint}, model={args.model})")
        print(f"tables loaded:       {len(analyst.schema())}")
        if up and analyst.schema():
            print("\nlive LLM check:")
            q = "how many rows in the first table"
            res = analyst.ask(q)
            print(f"  Q: {q}\n  SQL: {res.sql}\n  ok: {res.ok} rows: {len(res.rows)}"
                  + ("" if res.ok else f"\n  error: {res.error}"))
        elif not up:
            print("\nTo enable a local model:  ollama pull mistral && ollama serve")
        return 0

    if args.cmd == "schema":
        sch = analyst.schema()
        if args.json:
            print(json.dumps(sch, indent=2))
        else:
            if not sch:
                print("(no tables loaded — pass --data)")
            for t, cols in sch.items():
                print(f"{t} ({len(cols)} cols): {', '.join(cols)}")
        print(f"\nengine={analyst.data.engine} provider={analyst.provider.name}", file=sys.stderr)
        return 0

    if args.cmd == "sql":
        try:
            print(analyst.to_sql(args.question))
            return 0
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "learn":
        rid = analyst.learn(args.question, args.sql, rating=args.rating, domain=args.domain)
        print(f"learned #{rid}: {args.question!r} -> {args.sql}")
        print(f"store: {analyst.learning_stats()}", file=sys.stderr)
        return 0

    if args.cmd == "lessons":
        print(json.dumps(analyst.learning_stats(), indent=2, default=str))
        return 0

    if args.cmd == "ask":
        res = analyst.ask(args.question, domain=args.domain)
        if args.json:
            print(json.dumps(res.to_dict(), indent=2, default=str))
            return 0 if res.ok else 1
        via = f"  (via {res.provider})" if res.provider else ""
        print(f"SQL: {res.sql}{via}")
        if not res.ok:
            print(f"error: {res.error}", file=sys.stderr)
            return 1
        print(f"({len(res.rows)} rows) columns: {', '.join(res.columns)}")
        for row in res.rows[:50]:
            print("  " + " | ".join("" if v is None else str(v) for v in row))
        return 0

    if args.cmd == "profile":
        from ai_analyst.profiler import profile_report
        try:
            prof = analyst.profile(table=args.table, sample=args.sample)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            from dataclasses import asdict
            print(json.dumps(asdict(prof), indent=2, default=str))
        else:
            print(profile_report(prof))
        return 0

    if args.cmd == "summarize":
        try:
            info = analyst.summarize_document(args.doc, max_sentences=args.sentences)
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(info, indent=2, default=str))
        else:
            s = info["stats"]
            pg = f", {info['n_pages']} pages" if info.get("n_pages") else ""
            print(f"{info['path']}  ({info['kind']}{pg})")
            print(f"  {s['words']} words, {s['sentences']} sentences, {s['unique_words']} unique words")
            print(f"\nSummary:\n{info['summary']}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
