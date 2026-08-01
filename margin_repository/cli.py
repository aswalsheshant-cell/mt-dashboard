# -*- coding: utf-8 -*-
"""CLI runner: import → validate → version → change-log → impact → outputs.

Usage:
    python cli.py import <source.xlsx> [--repo-root ./repo_data] [--out outputs.xlsx]
    python cli.py pipeline <dms.xlsx> [--repo-root ./repo] [--out ./out]
                          [--responses ./Action_Files_2026_08_01]
    python cli.py search <query> [--repo-root ./repo_data]
    python cli.py versions [--repo-root ./repo_data]
    python cli.py rollback <batch_id> [--repo-root ./repo_data]
    python cli.py template [--out template.xlsx]
    python cli.py import-template [--out import_template.xlsx]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from repository import MarginRepository
from ingest import normalize_file
from impact import impact_from_changelog
from outputs import build_outputs, build_repository_template, build_import_template
from search import search


def cmd_import(args):
    repo = MarginRepository(args.repo_root)
    df, meta = normalize_file(args.source, sheet=args.sheet)
    print("Normalized %d rows from '%s' (header row %s, %d columns mapped)" %
          (meta["rows"], args.source, meta["header_row"], meta["mapped"]))
    if meta.get("unmapped_cols"):
        print("  Unmapped columns preserved: %s" % ", ".join(meta["unmapped_cols"]))

    summary, changelog, removed = repo.import_frame(df, source_file=os.path.basename(args.source))
    print("\nImport summary:")
    for k, v in summary.items():
        print("  %-28s %s" % (k, v))

    impact = impact_from_changelog(changelog)
    out_path = args.out or os.path.join(args.repo_root, "margin_outputs.xlsx")
    build_outputs(repo, out_path, changelog=changelog, removed=removed, impact=impact)
    print("\nOutputs written to: %s" % out_path)
    print("Repository root:    %s" % args.repo_root)


def cmd_search(args):
    repo = MarginRepository(args.repo_root)
    cur = repo.current(include_held=True)
    result = search(cur, args.query)
    if result.empty:
        print("No results for: %s" % args.query)
        return
    display = ["Chain", "Brand", "Article", "EAN", "Trade Margin %",
               "Final Effective Margin %", "QC_Severity"]
    cols = [c for c in display if c in result.columns]
    print(result[cols].to_string(index=False))
    print("\n%d article(s) found." % len(result))


def cmd_versions(args):
    repo = MarginRepository(args.repo_root)
    versions = repo.list_versions()
    if not versions:
        print("No snapshots yet.")
        return
    for v in versions:
        print("  " + v)
    print("\n%d snapshot(s)." % len(versions))


def cmd_rollback(args):
    repo = MarginRepository(args.repo_root)
    n = repo.rollback(args.batch_id)
    print("Rolled back to batch %s (%d records restored)." % (args.batch_id, n))


def cmd_template(args):
    path = args.out or "margin_repository_template.xlsx"
    build_repository_template(path)
    print("Repository template written to: %s" % path)


def cmd_import_template(args):
    path = args.out or "margin_import_template.xlsx"
    build_import_template(path)
    print("Import template written to: %s" % path)


def cmd_pipeline(args):
    from pipeline import run
    run(dms_path=args.source, repo_root=args.repo_root, out_dir=args.out,
        action_dir=args.action_dir, masters_dir=args.masters_dir,
        merge_responses_from=args.responses, verbose=True)


def main():
    p = argparse.ArgumentParser(description="Chain x Article Margin Repository CLI")
    sub = p.add_subparsers(dest="command")

    imp = sub.add_parser("import", help="Import a commercial source file")
    imp.add_argument("source", help="Path to source file (.xlsx/.xlsb/.csv)")
    imp.add_argument("--repo-root", default="./repo_data")
    imp.add_argument("--out", default=None)
    imp.add_argument("--sheet", default=0, type=int)

    srch = sub.add_parser("search", help="Search the repository")
    srch.add_argument("query", help="Natural language query")
    srch.add_argument("--repo-root", default="./repo_data")

    sub.add_parser("versions", help="List snapshots").add_argument("--repo-root", default="./repo_data")

    rb = sub.add_parser("rollback", help="Rollback to a prior snapshot")
    rb.add_argument("batch_id", help="Batch / snapshot ID")
    rb.add_argument("--repo-root", default="./repo_data")

    tmpl = sub.add_parser("template", help="Generate blank repository template")
    tmpl.add_argument("--out", default=None)

    itm = sub.add_parser("import-template", help="Generate blank import template")
    itm.add_argument("--out", default=None)

    pl = sub.add_parser("pipeline", help="One-click end-to-end refresh")
    pl.add_argument("source", help="DMS file path (.xlsx)")
    pl.add_argument("--repo-root", default="./repo_data")
    pl.add_argument("--out", default="./pipeline_out")
    pl.add_argument("--responses", default=None,
                    help="Directory containing completed action files to merge")
    pl.add_argument("--action-dir", default=None,
                    help="Where to write new action files (defaults to <out>/Action_Files)")
    pl.add_argument("--masters-dir", default=None,
                    help="Persistent master files directory")

    args = p.parse_args()
    if args.command is None:
        p.print_help()
        return

    cmds = {"import": cmd_import, "search": cmd_search, "versions": cmd_versions,
            "rollback": cmd_rollback, "template": cmd_template,
            "import-template": cmd_import_template, "pipeline": cmd_pipeline}
    cmds[args.command](args)


if __name__ == "__main__":
    main()
