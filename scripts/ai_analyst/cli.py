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
    ap.add_argument("--json", action="store_true", help="emit JSON")

    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("schema", help="print the loaded schema")
    p_sql = sub.add_parser("sql", help="translate a question to SQL (no execution)")
    p_sql.add_argument("question")
    p_ask = sub.add_parser("ask", help="translate and run a question")
    p_ask.add_argument("question")

    args = ap.parse_args(argv)

    pkw = {"model": args.model} if args.provider in ("auto", "ollama") else {}
    analyst = Analyst(provider=args.provider, engine=args.engine, provider_kwargs=pkw)
    _load(analyst, args.data)

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

    if args.cmd == "ask":
        res = analyst.ask(args.question)
        if args.json:
            print(json.dumps(res.to_dict(), indent=2, default=str))
            return 0 if res.ok else 1
        print(f"SQL: {res.sql}")
        if not res.ok:
            print(f"error: {res.error}", file=sys.stderr)
            return 1
        print(f"({len(res.rows)} rows) columns: {', '.join(res.columns)}")
        for row in res.rows[:50]:
            print("  " + " | ".join("" if v is None else str(v) for v in row))
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
