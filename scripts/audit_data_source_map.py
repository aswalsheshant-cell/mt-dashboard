"""One map of every data file the HTML dashboard and the Power BI model depend on.

It answers, from the repo itself:
  * Which files does each Power Query read, and do they exist?
  * Which files does dashboard/index.html load (script tags and fetch calls), and do they exist?
  * Which paths does config/data_source_registry.yml point to, and do they exist?
  * For each file: is it tracked in Git, which restricted class does the firewall give it,
    which dashboard or query uses it, and what are its columns?
  * Do the files in one watch folder agree on their column names? (the Primary Article
    "Chain name" / "MRP Rate" problem was exactly this kind of drift)

Outputs (rebuilt every run):
  PowerBI/data_source_map.json        machine-readable map
  docs/evidence/DATA_SOURCE_MAP.md    the same, readable

Header pins (config/data_header_pins.json) record the column layouts accepted today. A new file
whose layout is not pinned fails tests/test_data_source_map.py until someone reviews it and
runs --update-pins. That is what stops a silent header change from reaching a refresh.

Preflight on any machine that holds the real data (no Git needed):
  python scripts/audit_data_source_map.py --preflight "C:\\path\\to\\mt-dashboard\\PowerBI"
lists every file the queries need that is missing there, and every file whose columns are not pinned.

Usage:
  python scripts/audit_data_source_map.py
  python scripts/audit_data_source_map.py --update-pins
  python scripts/audit_data_source_map.py --preflight <PowerBI folder>
  python scripts/audit_data_source_map.py --with-branches     # also list data files that exist only on unmerged branches
"""

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import powerbi_full_sources as pfs  # noqa: E402
import restricted_source_firewall as fw  # noqa: E402

PBI = ROOT / "PowerBI"
OUT_JSON = PBI / "data_source_map.json"
OUT_MD = ROOT / "docs" / "evidence" / "DATA_SOURCE_MAP.md"
PINS = ROOT / "config" / "data_header_pins.json"
REGISTRY = ROOT / "config" / "data_source_registry.yml"
DASH = ROOT / "dashboard"

# Watch folders that are meant to be empty until a file arrives.
EXPECTED_EMPTY = {"RawDataFolders\\Primary_Weekly", "RawDataFolders\\TDP_Monthly"}
HEADER_FOLDERS = ("PowerBI/RawDataFolders", "PowerBI/SeedData")


def norm_header(h):
    return [" ".join(c.replace("\n", " ").replace("\r", " ").split()) for c in h if c is not None]


def read_header(path):
    try:
        with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
            return norm_header(next(csv.reader(fh), []))
    except OSError:
        return []


def sig(cols):
    return hashlib.sha1("|".join(cols).encode()).hexdigest()[:10]


def git_lines(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.splitlines()


def tracked_set():
    return set(fw.tracked_files())


def ignored(path):
    return subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0


# ---------- references ----------

def powerbi_references(model):
    refs = []
    for t in model["model"]["tables"]:
        r, hard, derived = pfs.table_refs(t)
        for ref in sorted(set(r) | set(hard)):
            res = pfs.resolve(ref)
            refs.append({
                "used_by": "Power Query: " + t["name"],
                "ref": ref,
                "kind": res["kind"],
                "exists": res["exists"],
                "files": [f.relative_to(ROOT).as_posix() for f in res["files"]],
                "expected_empty": ref in EXPECTED_EMPTY,
                "hard_coded_path": ref in hard,
            })
    return refs


DASH_FILE = re.compile(r"""['"]([\w./\-]+\.(?:json|js|csv))(?:\?[^'"]*)?['"]""")


def dashboard_references():
    refs = {}
    for f in [DASH / "index.html", *sorted(DASH.glob("*.js"))]:
        if f.name in ("data.js",) or f.name.endswith(".min.js") or f.name.startswith(("chart", "jspdf", "html2canvas", "xlsx")):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"(?:fetch\(|<script[^>]*src=)\s*['\"]([^'\"?]+)", text):
            name = m.group(1)
            if name.startswith(("http", "//")):
                continue
            refs.setdefault(name, set()).add(f.name)
    out = []
    for name, users in sorted(refs.items()):
        p = DASH / name
        out.append({"used_by": "HTML dashboard: " + ", ".join(sorted(users)), "ref": "dashboard/" + name,
                    "exists": p.exists(), "files": ["dashboard/" + name] if p.exists() else []})
    return out


def registry_references():
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    out = []
    for key, d in (data.get("datasets") or {}).items():
        sp = d.get("source_path")
        if not sp:
            continue
        for tok in re.findall(r"((?:PowerBI|data|dashboard|config|scripts)/[\w./\-*]+)", str(sp)):
            tok = tok.rstrip(".,;)")
            local_only = False
            if tok.endswith("/"):
                exists = (ROOT / tok).is_dir()
            elif tok.endswith(("_", "-")):  # a file-name pattern such as offtake_store_article_<Mon>_<YY>.csv
                parent = (ROOT / tok).parent
                exists = parent.is_dir() and any(f.name.startswith(Path(tok).name) for f in parent.iterdir())
            elif "*" in tok:
                exists = bool(list(ROOT.glob(tok)))
            else:
                exists = (ROOT / tok).exists()
            if not exists and ignored(tok.rstrip("/") + ("/x" if tok.endswith("/") else "")):
                local_only = True  # kept out of Git on purpose; must exist on the machine that builds the data
            waiting = any(e.replace("\\", "/") in tok for e in EXPECTED_EMPTY)  # folder is meant to be empty until a file arrives
            out.append({"used_by": "Registry: " + key, "ref": tok, "exists": exists, "local_only": local_only, "expected_empty": waiting,
                        "status": d.get("validation_status")})
    return out


# ---------- folder drift ----------

def header_groups(tracked):
    groups = {}
    for base in HEADER_FOLDERS:
        for folder in sorted(p for p in (ROOT / base).rglob("*") if p.is_dir()):
            files = sorted(f for f in folder.glob("*.csv") if not f.name.startswith("_"))
            if len(files) < 1:
                continue
            by = defaultdict(list)
            for f in files:
                cols = read_header(f)
                by[sig(cols)].append((f.name, cols))
            rel = folder.relative_to(ROOT).as_posix()
            groups[rel] = {s: {"columns": v[0][1], "files": [n for n, _ in v]} for s, v in sorted(by.items())}
    return groups


def pins_diff(groups, pins):
    new = []
    for folder, sigs in groups.items():
        pinned = set(pins.get(folder, {}))
        for s, info in sigs.items():
            if s not in pinned:
                new.append((folder, s, info["files"]))
    return new


# ---------- git (optional) ----------

def branch_only_files():
    def tree(ref):
        out = subprocess.run(["git", "ls-tree", "-r", "-z", ref, "--", "PowerBI/RawDataFolders", "PowerBI/SeedData", "data", "dashboard"],
                             cwd=ROOT, capture_output=True, text=True).stdout
        d = {}
        for l in out.split("\0"):
            if l:
                meta, path = l.split("\t", 1)
                d[path] = meta.split()[2]
        return d
    head = tree("HEAD")
    ext = (".csv", ".json", ".js", ".xlsx", ".xlsb", ".zip", ".gz")
    res = {}
    for b in git_lines("branch", "-r"):
        b = b.strip()
        if "HEAD" in b or b.endswith(("origin/main", "origin/gh-pages")):
            continue
        only = [p for p in tree(b) if p.endswith(ext) and p not in head and "PBIR_Generated" not in p and "node_modules" not in p]
        if only:
            res[b.replace("origin/", "")] = sorted(only)
    return res


# ---------- build ----------

def build(with_branches=False):
    model = json.loads((PBI / "model.bim").read_text(encoding="utf-8"))
    policy = fw.load_policy()
    tracked = tracked_set()
    refs = powerbi_references(model) + dashboard_references() + registry_references()

    used_by = defaultdict(set)
    for r in refs:
        for f in r.get("files", []):
            used_by[f].add(r["used_by"])
        if r.get("exists") and not r.get("files") and r["ref"] not in used_by:
            used_by[r["ref"]].add(r["used_by"])

    files = []
    for f in sorted(used_by):
        p = ROOT / f
        if not p.is_file():
            continue
        hdr = read_header(p) if f.lower().endswith(".csv") else []
        cls = fw.classify(f, ",".join(hdr) if hdr else "", policy)
        files.append({"path": f, "tracked": f in tracked, "ignored": ignored(f), "restricted_class": cls,
                      "used_by": sorted(used_by[f]), "columns": len(hdr), "header_sig": sig(hdr) if hdr else None})

    missing = [r for r in refs if not r.get("exists") and not r.get("expected_empty") and not r.get("local_only")]
    local_only = [{"used_by": r["used_by"], "ref": r["ref"]} for r in refs if r.get("local_only") and not r.get("exists")]
    groups = header_groups(tracked)
    pins = json.loads(PINS.read_text(encoding="utf-8")) if PINS.exists() else {}
    unpinned = pins_diff(groups, pins)

    referenced = set(used_by)
    orphans = []
    for base in ("PowerBI/RawDataFolders", "PowerBI/SeedData"):
        for f in sorted((ROOT / base).rglob("*")):
            rel = f.relative_to(ROOT).as_posix()
            if f.is_file() and f.suffix.lower() in (".csv", ".json") and not f.name.startswith("_") and rel not in referenced:
                orphans.append(rel)

    doc = {
        "generated": date.today().isoformat(),
        "basis": "Static map from the repo (model.bim, dashboard/*.html|js, config/data_source_registry.yml, Git, restricted_source_policy.yml).",
        "counts": {"references": len(refs), "missing_references": len(missing), "files_in_use": len(files),
                   "unpinned_header_layouts": len(unpinned), "orphan_files": len(orphans)},
        "missing_references": missing,
        "local_only_references": local_only,
        "references": refs,
        "files_in_use": files,
        "header_layouts": {k: v for k, v in groups.items() if len(v) > 1},
        "unpinned_header_layouts": [{"folder": a, "sig": b, "files": c} for a, b, c in unpinned],
        "orphan_files": orphans,
    }
    if with_branches:
        doc["branch_only_files"] = branch_only_files()
    return doc, groups


def write_md(doc):
    c = doc["counts"]
    L = ["# Data source map", "",
         "Rebuilt by `scripts/audit_data_source_map.py`. %s" % doc["basis"], "",
         "Generated %s. References: %d. Missing: %d. Files in use: %d. Folders with more than one column layout: %d. Unpinned layouts: %d. Unreferenced files: %d." % (
             doc["generated"], c["references"], c["missing_references"], c["files_in_use"], len(doc["header_layouts"]), c["unpinned_header_layouts"], c["orphan_files"]), "",
         "## Missing references", ""]
    if doc["missing_references"]:
        L += ["| Used by | Path | Note |", "|---|---|---|"]
        for r in doc["missing_references"]:
            note = "hard-coded path" if r.get("hard_coded_path") else ""
            L.append("| %s | `%s` | %s |" % (r["used_by"], r["ref"], note))
    else:
        L.append("None. Every path a query, the HTML dashboard or the registry names exists. Folders that are meant to be empty until a file arrives (Primary_Weekly, TDP_Monthly) are not counted.")
    L += ["", "## Kept out of Git on purpose (must exist on the machine that builds the data)", ""]
    L += ["- `%s` (%s)" % (r["ref"], r["used_by"]) for r in doc["local_only_references"]] or ["None."]
    L += ["", "## Folders whose files do not share one column layout", "",
          "Each layout below is accepted and pinned in `config/data_header_pins.json`. A file with a layout that is not pinned fails `tests/test_data_source_map.py`.", ""]
    for folder, sigs in sorted(doc["header_layouts"].items()):
        L.append("### `%s`" % folder)
        for s, info in sigs.items():
            L.append("- layout `%s` (%d columns): %s" % (s, len(info["columns"]), ", ".join("`%s`" % f for f in info["files"][:6]) + (" ..." if len(info["files"]) > 6 else "")))
        cols = [set(i["columns"]) for i in sigs.values()]
        common = set.intersection(*cols)
        for s, info in sigs.items():
            extra = [x for x in info["columns"] if x not in common]
            if extra:
                L.append("  - only in `%s`: %s" % (s, ", ".join("`%s`" % x for x in extra[:10])))
        L.append("")
    L += ["## Files the queries and dashboards use", "",
          "| File | In Git | Restricted class | Used by |", "|---|---|---|---|"]
    for f in doc["files_in_use"]:
        L.append("| `%s` | %s | %s | %s |" % (f["path"], "yes" if f["tracked"] else "no", f["restricted_class"] or "-", "; ".join(f["used_by"][:3]) + (" ..." if len(f["used_by"]) > 3 else "")))
    L += ["", "## Files in the data folders that no query, dashboard or registry entry names", ""]
    L += ["- `%s`" % o for o in doc["orphan_files"]] or ["None."]
    if "branch_only_files" in doc:
        L += ["", "## Data files that exist only on unmerged branches (snapshot %s)" % doc["generated"], ""]
        for b, fs in sorted(doc["branch_only_files"].items()):
            L.append("- `%s`: %s" % (b, ", ".join("`%s`" % x.rsplit("/", 1)[-1] for x in fs[:6]) + (" ... (+%d)" % (len(fs) - 6) if len(fs) > 6 else "")))
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")


def preflight(folder):
    base = Path(folder)
    if not (base / "PowerQuery").exists():
        sys.exit("%s does not look like the PowerBI folder (no PowerQuery subfolder)." % folder)
    pins = json.loads(PINS.read_text(encoding="utf-8")) if PINS.exists() else {}
    model = json.loads((base / "model.bim").read_text(encoding="utf-8"))
    problems = 0
    for t in model["model"]["tables"]:
        r, hard, _ = pfs.table_refs(t)
        for ref in sorted(set(r) | set(hard)):
            p = base / ref.replace("\\", "/")
            files = []
            if p.is_dir():
                files = [f for f in p.iterdir() if f.suffix.lower() == ".csv" and not f.name.startswith("_")]
                if not files and ref not in EXPECTED_EMPTY:
                    print("MISSING  %-34s no data files in %s" % (t["name"], ref)); problems += 1
            elif p.is_file():
                files = [p]
            else:
                print("MISSING  %-34s %s" % (t["name"], ref)); problems += 1
            for f in files:
                rel_folder = "PowerBI/" + f.parent.relative_to(base).as_posix()
                cols = read_header(f)
                if rel_folder in pins and sig(cols) not in pins[rel_folder]:
                    print("NEW LAYOUT %-30s %s has columns not seen before (%d)" % (t["name"], f.name, len(cols))); problems += 1
    print("preflight: %s" % ("%d problem(s)" % problems if problems else "all required files present; no unpinned column layouts"))
    return 1 if problems else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--update-pins", action="store_true", help="accept today's column layouts as the pinned set")
    ap.add_argument("--preflight", metavar="POWERBI_FOLDER")
    ap.add_argument("--with-branches", action="store_true")
    args = ap.parse_args()
    if args.preflight:
        sys.exit(preflight(args.preflight))
    doc, groups = build(args.with_branches)
    if args.update_pins:
        pins = {folder: {s: {"columns": len(i["columns"]), "example": i["files"][0]} for s, i in sigs.items()} for folder, sigs in groups.items()}
        PINS.write_text(json.dumps(pins, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        doc, groups = build(args.with_branches)
    OUT_JSON.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    write_md(doc)
    c = doc["counts"]
    print("references %d | missing %d | files in use %d | multi-layout folders %d | unpinned %d | orphans %d" % (
        c["references"], c["missing_references"], c["files_in_use"], len(doc["header_layouts"]), c["unpinned_header_layouts"], c["orphan_files"]))
    for r in doc["missing_references"]:
        print("  MISSING", r["used_by"], r["ref"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
