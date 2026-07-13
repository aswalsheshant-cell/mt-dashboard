"""mtagent CLI — run from the repo root (or anywhere inside it):

    python -m mtagent doctor
    python -m mtagent index [--rebuild]
    python -m mtagent ask "How is FY derived from a month label?"
    python -m mtagent meeting "Why is offtake down vs primary?"   # /meeting mode
    python -m mtagent check            # DAX + PQ + (if duckdb) data quality
    python -m mtagent qc               # /qc mode: full QC battery + coverage map
    python -m mtagent reconcile        # /reconcile: dashboard vs source CSVs
    python -m mtagent check-dax [--strict] [--json]
    python -m mtagent check-pq  [--strict] [--json]
    python -m mtagent db-build
    python -m mtagent sql list
    python -m mtagent sql run chain_ranking --param fy=FY26
    python -m mtagent sql exec "SELECT fy_from_label('Apr''25')"
    python -m mtagent catalog [--rebuild]      # categorize every repo file
    python -m mtagent find "chain master"      # where is ...?
    python -m mtagent place offtake_Jun_26.csv # where does this file go?
    python -m mtagent log [--tail N]           # work-log audit trail
    python -m mtagent eval
    python -m mtagent pbi list                 # Power BI workflow controller (Module 2)
    python -m mtagent pbi build-dataset
    python -m mtagent pbi generate-dax
    python -m mtagent pbi reconcile-model --source <csv> --build-dir <agent/pbi_build/...>
    python -m mtagent pbi status
    python -m mtagent pbi next-manual-step
    python -m mtagent pbi resume
    python -m mtagent pbi mark-complete --step-id <id> --evidence-kind screenshot --evidence <path>
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
    mode = getattr(args, "mode", "ask")
    extra = None
    if mode == "meeting" and getattr(args, "drilldown", False):
        mode = "drilldown"
        from .diffengine import analyze_offtake, format_drilldown_context
        report = analyze_offtake(cfg)
        if report:
            extra = format_drilldown_context(cfg, report)
        else:
            print("[note] drill-down tables unavailable: need at least two "
                  "months in Offtake_Monthly", file=sys.stderr)
    result = ask(cfg, args.question, k=args.k, mode=mode, extra_context=extra)
    if extra and not result["answer"]:
        print(extra + "\n")   # no local LLM — surface the computed tables raw
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


def cmd_qc(cfg: Config, args) -> int:
    """/qc mode: the full battery, then a coverage map against the analyst
    charter's QC checklist so it's explicit what ran and what needs Power
    BI Desktop (which a CLI can't reach)."""
    rc = cmd_check(cfg, args)
    inv = _inventory(cfg)
    covered = [
        ("DAX QC", "check-dax: balance, duplicates, table refs, DIVIDE, FY literals"),
        ("Power Query QC", "check-pq: let/in, step graph, paths, typing"),
        ("Business Rule QC", "ONE-FY-RULE lint (DAX005) + data_quality SQL FY check"),
        ("Duplicate QC", "DAX002 cross-file duplicates + data_quality row checks"),
        ("Mapping QC", "PQ006 repo-path existence + null-chain data checks"),
        ("Relationship QC", f"model inventory from {inv.source} "
                            f"({len(inv.tables)} tables) — drop model.bim in "
                            "agent/metadata for exact relationship coverage"),
        ("Refresh QC", "data.js vs source CSVs — run: python -m mtagent reconcile"),
    ]
    manual = [
        ("Excel QC", "workbook formulas can't be inspected offline here — open the "
                     "file, or export the sheet to CSV and use sql exec"),
        ("Formatting QC", "visual formatting lives in the .pbix — see "
                          "PowerBI/docs/ExportAndVisualSettings.md checklist"),
    ]
    print("\nQC coverage map:")
    for name, how in covered:
        print(f"  [auto]   {name}: {how}")
    for name, how in manual:
        print(f"  [manual] {name}: {how}")
    return rc


def cmd_reconcile(cfg: Config, args) -> int:
    from .reconcile import format_report, run_reconciliation
    result = run_reconciliation(cfg, tol_pct=args.tol)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_report(result))
    return 1 if any(r["status"] == "DIFF" for r in result["rows"]) else 0


def cmd_catalog(cfg: Config, args) -> int:
    from .catalog import build_catalog, load_catalog, summarize
    entries = build_catalog(cfg) if args.rebuild else load_catalog(cfg)
    print(summarize(entries))
    return 0


def cmd_find(cfg: Config, args) -> int:
    from .catalog import find
    hits = find(cfg, args.query)
    if not hits:
        print("no catalog match — try: python -m mtagent ask \"" + args.query + "\"")
        return 1
    for score, e in hits:
        tag = f"  [{e.fy} {e.month}]" if e.fy else ""
        print(f"{score:5.1f}  {e.path}{tag}\n       {e.category} — {e.purpose}")
    return 0


def cmd_place(cfg: Config, args) -> int:
    from .catalog import suggest_placement
    s = suggest_placement(args.filename)
    if not s["folder"]:
        print(f"no placement rule for {s['file']} — {s['then']}")
        return 1
    print(f"file:    {s['file']}\nfolder:  {s['folder']}\n"
          f"naming:  {s['naming']}\nthen:    {s['then']}")
    if s["reminder"]:
        print(f"note:    {s['reminder']}")
    # Proactive diff engine: newest month vs prior month of the target feed.
    if "Offtake_Monthly" in s["folder"]:
        from .diffengine import analyze_offtake, format_exception_report
        given = Path(args.filename)
        report = analyze_offtake(cfg, extra_file=given if given.exists() else None)
        if report:
            print(format_exception_report(report))
        else:
            print("\nProactive Exception Report: skipped — needs at least two "
                  "monthly files in Offtake_Monthly to compare.")
    else:
        print("\nProactive Exception Report: automated MoM comparison currently "
              "covers the offtake feed; for this feed run the matching SQL "
              "template after refresh (python -m mtagent sql list).")
    return 0


def cmd_log(cfg: Config, args) -> int:
    from .worklog import read_log
    entries = read_log(cfg, tail=args.tail)
    if not entries:
        print("work log is empty")
        return 0
    for e in entries:
        notes = f"  ({'; '.join(e['notes'])})" if e.get("notes") else ""
        argv = e.get("argv") or []
        if argv and argv[0] == e["command"]:
            argv = argv[1:]
        print(f"{e['ts']}  rc={e['status']}  {e['command']} "
              f"{' '.join(argv)}{notes}")
    return 0


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


def cmd_pbi(cfg: Config, args) -> int:
    from . import pbi_commands  # noqa: F401 -- import populates the registry
    from .pbi_registry import get_command, list_commands
    from .pbi_workflow import WorkflowController

    if args.pbi_cmd == "list":
        for c in list_commands():
            print(f"{c.name:20s} [{c.classification:9s}] {c.description}")
        return 0

    controller = WorkflowController(cfg)
    kwargs = {k: v for k, v in vars(args).items()
              if k not in ("cmd", "pbi_cmd", "json") and v is not None}
    try:
        spec = get_command(args.pbi_cmd)
        result = spec.handler(cfg, controller, **kwargs)
    except (KeyError, ValueError) as e:
        print(f"pbi {args.pbi_cmd}: {e}", file=sys.stderr)
        return 2

    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, default=str))
    else:
        for k, v in result.items():
            print(f"{k}: {v}")
    status = str(result.get("status", ""))
    return 1 if status in ("Failed", "Blocked") else 0


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
    p.set_defaults(mode="ask")

    p = sub.add_parser("meeting", help="/meeting mode: terse leadership answer "
                                       "(Answer / drivers / response / DQ / next action)")
    p.add_argument("question")
    p.add_argument("-k", type=int, default=None)
    p.add_argument("--json", action="store_true")
    p.add_argument("--drilldown", "--verbose", action="store_true",
                   dest="drilldown",
                   help="lift the 120-word limit: top underperforming outlets, "
                        "sub-category/pack mix deltas, GST/TOT confidence status")
    p.set_defaults(mode="meeting")

    for name in ("check-dax", "check-pq"):
        p = sub.add_parser(name, help=f"run the {name[6:].upper()} lint")
        p.add_argument("paths", nargs="*", help="files (default: whole PowerBI folder)")
        p.add_argument("--strict", action="store_true", help="warnings fail too")
        p.add_argument("--json", action="store_true")
        p.add_argument("--min-severity", choices=("error", "warn", "info"),
                       default="info", help="lowest severity to print")

    for name, hlp in (("check", "DAX + PQ lint + SQL data-quality sweep"),
                      ("qc", "/qc mode: full QC battery + coverage map")):
        p = sub.add_parser(name, help=hlp)
        p.add_argument("--strict", action="store_true")
        p.add_argument("--json", action="store_true")
        p.add_argument("--min-severity", choices=("error", "warn", "info"),
                       default="info")

    p = sub.add_parser("reconcile", help="/reconcile mode: dashboard data.js vs "
                                         "source CSVs vs internal consistency")
    p.add_argument("--tol", type=float, default=0.5,
                   help="tolerance %% for OK/DIFF (default 0.5)")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("catalog", help="categorize every repo file (writes "
                                       "agent/index/catalog.json)")
    p.add_argument("--rebuild", action="store_true")

    p = sub.add_parser("find", help="search the file catalog: where is ...?")
    p.add_argument("query")

    p = sub.add_parser("place", help="where does this new file belong?")
    p.add_argument("filename")

    p = sub.add_parser("log", help="show the work-log audit trail")
    p.add_argument("--tail", type=int, default=20)

    sub.add_parser("db-build", help="build the local DuckDB over the committed CSVs")

    p = sub.add_parser("sql", help="list/run SQL templates or exec raw SQL")
    p.add_argument("action", choices=("list", "run", "exec"))
    p.add_argument("name", nargs="?", help="template name (run) or raw SQL (exec)")
    p.add_argument("--param", action="append", metavar="k=v")
    p.add_argument("--json", action="store_true")
    p.add_argument("--show-sql", action="store_true")

    p = sub.add_parser("eval", help="golden-QA retrieval eval + validator self-checks")
    p.add_argument("--k", type=int, default=3, help="hit@k cutoff")

    p = sub.add_parser("pbi", help="Power BI workflow controller (Module 2)")
    pbi_sub = p.add_subparsers(dest="pbi_cmd", required=True)

    pbi_sub.add_parser("list", help="list every registered pbi command")

    pb = pbi_sub.add_parser("build-dataset", help="build the PBI-ready dataset from the latest offtake files")
    pb.add_argument("--raw-dir", help="override PowerBI/RawDataFolders/Offtake_Monthly")
    pb.add_argument("--masters-dir", help="override PowerBI/SeedData/Masters")
    pb.add_argument("--json", action="store_true")

    pd = pbi_sub.add_parser("generate-dax", help="audit PowerBI/DAX/ coverage + generate a gap library")
    pd.add_argument("--dax-dir", help="override PowerBI/DAX")
    pd.add_argument("--json", action="store_true")

    pr = pbi_sub.add_parser("reconcile-model", help="source-to-model reconciliation")
    pr.add_argument("--source", required=True, help="original offtake CSV")
    pr.add_argument("--build-dir", required=True, help="agent/pbi_build/<build_id> from build-dataset")
    pr.add_argument("--masters-dir", help="override PowerBI/SeedData/Masters")
    pr.add_argument("--json", action="store_true")

    for _name, _hlp in (
        ("generate-power-query", "[not yet implemented] step 5: generate Power Query scripts"),
        ("generate-page-blueprint", "[not yet implemented] step 7: generate the page-wise visual blueprint"),
        ("generate-theme", "[not yet implemented] step 8: generate the Power BI theme JSON"),
        ("generate-docs", "[not yet implemented] step 9: generate model documentation"),
        ("prepare-build-package", "[not yet implemented] step 10: prepare the Power BI build package"),
    ):
        _p = pbi_sub.add_parser(_name, help=_hlp)
        _p.add_argument("--json", action="store_true")

    pra = pbi_sub.add_parser("run-automated", help="run every automated step end to end, "
                                                    "stopping cleanly at the first manual/approval step")
    pra.add_argument("--raw-dir", help="override PowerBI/RawDataFolders/Offtake_Monthly")
    pra.add_argument("--masters-dir", help="override PowerBI/SeedData/Masters")
    pra.add_argument("--dax-dir", help="override PowerBI/DAX")
    pra.add_argument("--json", action="store_true")

    ps = pbi_sub.add_parser("status", help="show dashboard build status")
    ps.add_argument("--json", action="store_true")

    pcm = pbi_sub.add_parser("compile-model", help="compile the .pbip semantic model "
                                                    "(bindings + relationships + gated DAX) programmatically")
    pcm.add_argument("--build-dir", help="agent/pbi_build/<id> to bind (default: latest)")
    pcm.add_argument("--json", action="store_true")

    psm = pbi_sub.add_parser("start-manual-step", help="transition the next Ready manual step "
                                                        "to Manual Action Required with concrete instructions")
    psm.add_argument("--json", action="store_true")

    pn = pbi_sub.add_parser("next-manual-step", help="show only the next manual Power BI step")
    pn.add_argument("--json", action="store_true")

    pres = pbi_sub.add_parser("resume", help="resume from the last completed step")
    pres.add_argument("--json", action="store_true")

    pm = pbi_sub.add_parser("mark-complete", help="mark a step complete (requires evidence)")
    pm.add_argument("--step-id", required=True)
    pm.add_argument("--evidence-kind", required=True,
                     choices=("screenshot", "metadata_export", "query_output", "file_output", "user_confirmation"))
    pm.add_argument("--evidence", required=True)
    pm.add_argument("--json", action="store_true")

    return ap


def main(argv: list | None = None) -> int:
    import sys as _sys
    raw_argv = list(argv if argv is not None else _sys.argv[1:])
    args = build_parser().parse_args(argv)
    cfg = load_config(args.config)
    if args.cmd == "sql" and args.action in ("run", "exec") and not args.name:
        print("sql run/exec needs a template name or SQL string", file=sys.stderr)
        return 2
    handlers = {
        "doctor": cmd_doctor, "index": cmd_index,
        "ask": cmd_ask, "meeting": cmd_ask,
        "check-dax": cmd_check_dax, "check-pq": cmd_check_pq,
        "check": cmd_check, "qc": cmd_qc, "reconcile": cmd_reconcile,
        "catalog": cmd_catalog, "find": cmd_find, "place": cmd_place,
        "log": cmd_log, "db-build": cmd_db_build, "sql": cmd_sql,
        "eval": cmd_eval, "pbi": cmd_pbi,
    }
    notes: list[str] = []
    try:
        rc = handlers[args.cmd](cfg, args)
    except Exception as e:
        notes.append(f"{type(e).__name__}: {e}")
        rc = 1
        raise
    finally:
        # STEP 9 of the charter: log every run (except reading the log itself)
        if args.cmd != "log":
            from .worklog import log_run
            log_run(cfg, args.cmd, raw_argv, rc if notes == [] else 1, notes)
    return rc
