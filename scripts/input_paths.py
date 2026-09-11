"""Resolve a script's input file without depending on an ephemeral session path.

Several scripts used to hardcode an absolute path into
/root/.claude/uploads/<session-uuid>/. That directory belongs to one Claude
session: the moment the container is replaced the path is gone, and the script
cannot run. Every such path in this repo was already dead.

The replacement is an explicit input contract, in this order:

  1. a CLI flag           --src / --input (whatever the script declares)
  2. an environment var   e.g. MT_UNIVERSE_FILE
  3. a repo-relative path when a canonical in-repo copy genuinely exists

There is deliberately no fourth step. No globbing, no "newest file in the
folder", no guessing -- picking the wrong month's workbook silently is worse
than stopping. When nothing resolves, the script exits naming the exact file it
needs, which is what CLAUDE.md's "No dummy data" rule requires.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def resolve_input(*, flag: str, env: str, describe: str, repo_default: str | None = None,
                  argv: list[str] | None = None) -> Path:
    """Return the input file, or exit with a message naming what is missing.

    flag         CLI flag to read, e.g. "--src"
    env          environment variable to fall back to, e.g. "MT_NPI_FILE"
    describe     what the file is, in words, for the error message
    repo_default repo-relative path to use when the file is tracked in-repo
    """
    args = list(sys.argv[1:] if argv is None else argv)
    chosen = None
    source = ""

    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            chosen, source = args[i + 1], f"{flag} argument"
    for a in args:                                   # also accept --src=PATH
        if a.startswith(flag + "="):
            chosen, source = a.split("=", 1)[1], f"{flag}= argument"

    if chosen is None and os.environ.get(env):
        chosen, source = os.environ[env], f"${env}"

    if chosen is None and repo_default and (REPO / repo_default).exists():
        chosen, source = str(REPO / repo_default), "repo default"

    if chosen is None:
        sys.exit(
            f"\nMissing input: {describe}\n"
            f"  Pass it with:  {flag} /path/to/file\n"
            f"  or set:        {env}=/path/to/file\n"
            + (f"  or place it at: {repo_default}\n" if repo_default else "")
            + "\nThis script previously hardcoded a path inside a Claude session's\n"
              "upload directory, which does not survive a new container. Nothing is\n"
              "guessed in its place -- supply the file explicitly.\n")

    p = Path(chosen).expanduser()
    if not p.exists():
        sys.exit(f"\nInput not found: {p}\n  ({describe}, given via {source})\n")
    return p
