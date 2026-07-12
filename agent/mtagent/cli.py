"""mtagent CLI — run from the repo root (or anywhere inside it):

    python -m mtagent doctor
    python -m mtagent index [--rebuild]
    python -m mtagent ask "How is FY derived from a month label?"
    python -m mtagent check            # DAX + PQ + (if duckdb) data quality
    python -m mtagent check-dax [--strict] [--json]
    python -m mtagent check-pq  [--strict] [--json]
    python -m mtagent db-build
    python -m mtagent sql list
    python -m mtagent sql run chain_ranking --param fy=FY26
    python -m mtagent sql exec "SELECT fy_from_label('Apr''25')"
    python -m mtagent eval
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import Config, load_config
from .report import exit_code, print_findings


def _dax_paths(cfg: Config, args_paths: list) -> list:
    if args_paths:
        return [Path(p) for p in args_paths]
    return sorted((cfg.root() / "PowerBI" / "DAX").glob("*.dax"))


def _pq_paths(cfg: Config, args_paths: list) -> list:
    if args_paths:
        return [Path(p) for p in args_paths]
    return sorted((cfg.root() / "PowerBI" / "PowerQuery").glob("*.pq"))


def _inventory(cfg: Config):
    from .metadata import load_inventory
    return load_inventory(cfg.path(cfg.metadata_dir), cfg.root())


# ---------------------------------------------------------------- commands

def cmd_doctor(cfg: Config, args) -> int:
    from .llm import Ollama
    root = cfg.root()
    print(f"mtagent {__version__} — repo root: {root}")
    for mod in ("duckdb", "pandas", "openpyxl", "pypdf"):
        try:
            __import__(mod)
            print(f"  [ok]      {mod}")
        except ImportError:
            print(f"  [missing] {mod}  (optional — pip install {mod})")
    client = Ollama(cfg)
    if client.available():
        models = client.models()
        print(f"  [ok]      Ollama at {cfg.ollama_url} — models: "
              f"{', '.join(models) or '(none pulled)'}")
        for want, role in ((cfg.chat_model, "chat"), (cfg.embed_model, "embed")):
            if not any(m.split(":")[0] == want.split(":")[0] for m in models):
                print(f"  [note]    {role} model '{want}' not pulled — "
                      f"run: ollama pull {want}")
    else:
        print(f"  [missing] Ollama at {cfg.ollama_url} — 'ask' falls back to "
              "passage retrieval; the index falls back to hashed TF-IDF")
    idx = cfg.path(cfg.index_path)
    print(f"  [{'ok' if idx.exists() else 'missing'}]{' ' * (5 if idx.exists() else 0)} "
          f"vector index {idx}" + ("" if idx.exists() else "  (run: python -m mtagent index)"))
    db = cfg.path(cfg.db_path)
    print(f"  [{'ok' if db.exists() else 'missing'}]{' ' * (5 if db.exists() else 0)} "
          f"duckdb file {db}" + ("" if db.exists() else "  (run: python -m mtagent db-build)"))
    inv = _inventory(cfg)
    print(f"  [info]    model inventory from {inv.source}: {len(inv.tables)} tables, "
          f"{len(inv.measures)} measures "
          f"(drop model.bim / INFO.*.csv into {cfg.metadata_dir} for exact checks)")
    return 0


def cmd_index(cfg: Config, args) -> int:
    from .rag import ensure_index
    _, notices = ensure_index(cfg, rebuild=True)
    for n in notices:
        print(n)
    return 0


def cmd_ask(cfg: Config, args) -> int:
    from .rag import ask
    result = ask(cfg, args.question, k=args.k)
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    for n in result["notices"]:
        print(f"[note] {n}", file=sys.stderr)
    if result["answer"]:
        print(result["answer"])
        print("\nSources considered:")
    else:
        print("Top passages (no local LLM available):\n")
    for p in result["passages"]:
        print(f"  {p['score']:6.3f}  {p['source']} :: {p['section']}")
        if not result["answer"]:
            text = p["text"]
            print("    " + text[:500].replace("\n", "\n    ")
                  + ("…" if len(text) > 500 else "") + "\n")
    return 0


def cmd_check_dax(cfg: Config, args) -> int:
    from .dax_validator import validate_paths
    findings = validate_paths(_dax_paths(cfg, args.paths), _inventory(cfg))
    print_findings(findings, as_json=args.json, min_severity=args.min_severity)
    return exit_code(findings, strict=args.strict)


def cmd_check_pq(cfg: Config, args) -> int:
    from .pq_checks import validate_paths
    findings = validate_paths(_pq_paths(cfg, args.paths), cfg.root())
    print_findings(findings, as_json=args.json, min_severity=args.min_severity)
    return exit_code(findings, strict=args.strict)


def cmd_check(cfg: Config, args) -> int:
    from .dax_validator import validate_paths as vdax
    from .pq_checks import validate_paths as vpq
    findings = vdax(_dax_paths(cfg, []), _inventory(cfg))
    findings += vpq(_pq_paths(cfg, []), cfg.root())
    print_findings(findings, as_json=args.json, min_severity=args.min_severity)
    rc = exit_code(findings, strict=args.strict)
    try:
        from .duck import run_sql
        from .sql_templates import get_template, render
        if not cfg.path(cfg.db_path).exists():
            from .duck import build_db
            build_db(cfg)
        cols, rows = run_sql(cfg, render(get_template(cfg, "data_quality")))
        bad = [r for r in rows if r[-1]]
        print(f"\ndata quality ({len(rows)} checks): "
              + ("all clean" if not bad else f"{len(bad)} non-zero:"))
        for r in bad:
            print(f"  {r[0]}: {r[-1]} row(s)")
            rc = rc or 1
    except Exception as e:   # duckdb missing or CSVs absent — still a valid run
        print(f"\n[note] data-quality SQL sweep skipped: {e}")
    return rc


def cmd_db_build(cfg: Config, args) -> int:
    from .duck import build_db
    for line in build_db(cfg):
        print(line)
    return 0


def cmd_sql(cfg: Config, args) -> int:
    from .duck import format_table, run_sql
    from .sql_templates import get_template, list_templates, render
    if args.action == "list":
        for t in list_templates(cfg):
            ps = ", ".join(f"{k}={v or '<required>'}" for k, v in t.params.items())
            print(f"{t.name:22s} {t.description}" + (f"  [params: {ps}]" if ps else ""))
        return 0
    if not cfg.path(cfg.db_path).exists():
        from .duck import build_db
        for line in build_db(cfg):
            print(line, file=sys.stderr)
    if args.action == "run":
        params = dict(p.split("=", 1) for p in (args.param or []))
        sql = render(get_template(cfg, args.name), params)
        if args.show_sql:
            print(sql, file=sys.stderr)
    else:   # exec
        sql = args.name
    cols, rows = run_sql(cfg, sql)
    if args.json:
        print(json.dumps([dict(zip(cols, r)) for r in rows], indent=2, default=str))
    else:
        print(format_table(cols, rows))
    return 0


def cmd_eval(cfg: Config, args) -> int:
    from .evalrun import run_eval
    return run_eval(cfg, k=args.k)


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="mtagent", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="path to a config JSON (default: agent/config.json)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="show what is installed / reachable")
    sub.add_parser("index", help="(re)build the local vector index")

    p = sub.add_parser("ask", help="ask a question over the local knowledge base")
    p.add_argument("question")
    p.add_argument("-k", type=int, default=None, help="passages to retrieve")
    p.add_argument("--json", action="store_true")

    for name in ("check-dax", "check-pq"):
        p = sub.add_parser(name, help=f"run the {name[6:].upper()} lint")
        p.add_argument("paths", nargs="*", help="files (default: whole PowerBI folder)")
        p.add_argument("--strict", action="store_true", help="warnings fail too")
        p.add_argument("--json", action="store_true")
        p.add_argument("--min-severity", choices=("error", "warn", "info"),
                       default="info", help="lowest severity to print")

    p = sub.add_parser("check", help="DAX + PQ lint + SQL data-quality sweep")
    p.add_argument("--strict", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--min-severity", choices=("error", "warn", "info"), default="info")

    sub.add_parser("db-build", help="build the local DuckDB over the committed CSVs")

    p = sub.add_parser("sql", help="list/run SQL templates or exec raw SQL")
    p.add_argument("action", choices=("list", "run", "exec"))
    p.add_argument("name", nargs="?", help="template name (run) or raw SQL (exec)")
    p.add_argument("--param", action="append", metavar="k=v")
    p.add_argument("--json", action="store_true")
    p.add_argument("--show-sql", action="store_true")

    p = sub.add_parser("eval", help="golden-QA retrieval eval + validator self-checks")
    p.add_argument("--k", type=int, default=3, help="hit@k cutoff")
    return ap


def main(argv: list | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    if args.cmd == "sql" and args.action in ("run", "exec") and not args.name:
        print("sql run/exec needs a template name or SQL string", file=sys.stderr)
        return 2
    handlers = {
        "doctor": cmd_doctor, "index": cmd_index, "ask": cmd_ask,
        "check-dax": cmd_check_dax, "check-pq": cmd_check_pq, "check": cmd_check,
        "db-build": cmd_db_build, "sql": cmd_sql, "eval": cmd_eval,
    }
    return handlers[args.cmd](cfg, args)
