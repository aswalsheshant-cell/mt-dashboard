"""Static refresh-risk check for the Power Query files (no Power BI needed).

Power Query only fails at refresh. This script reads each query under
PowerBI/PowerQuery, follows the simple table steps (select, rename, remove, add,
retype), starts from the real CSV headers, and reports the failures Desktop would
raise:

  MISSING_COLUMN   a step names a column the table does not have at that point
  DUPLICATE_COLUMN a step makes two columns with one name
  BAD_VALUE        a column typed number/date has values that will not convert
  UNKNOWN_QUERY    a step refers to a query that does not exist
  PARTIAL_COLUMN   a column a step selects exists in some source files but not others,
                   so UseNull would leave it blank for those files
  NO_SOURCE_FILE   File.Contents / Folder.Files points at nothing

It stops following a query when it reaches a step it cannot model (joins, expands,
custom functions), so a clean result is not proof of a clean refresh. A finding is a
real defect unless noted. Output is read-only.

Usage:
  python scripts/check_pq_refresh_risks.py
  python scripts/check_pq_refresh_risks.py --only 16_Fact_PrimaryArticle
"""

import argparse
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBI = ROOT / "PowerBI"
PQ = PBI / "PowerQuery"
SKIP = ("_readme", "_template")
MAX_ROWS = 300000

# Gaps in the source files themselves. The query is fine; the data lacks the column.
ACCEPTED_SOURCE_GAPS = {
    ("11_Fact_OfftakeSales / Picked", "DC Name"): "offtake_store_article_Apr_26.csv has no DC Name column",
    ("11_Fact_OfftakeSales / Picked", "SO/ASE Name"): "offtake_store_article_Apr_26.csv has no SO/ASE Name column",
}


# ---------- tiny M reader ----------

def strip_comments(text):
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == '"':
                if i + 1 < n and text[i + 1] == '"':
                    out.append('"')
                    i += 1
                else:
                    in_str = False
        elif c == '"':
            in_str = True
            out.append(c)
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
            continue
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 1
        else:
            out.append(c)
        i += 1
    return "".join(out)


def split_top(text, sep=","):
    parts, depth, cur, in_str, i = [], 0, [], False, 0
    while i < len(text):
        c = text[i]
        if in_str:
            cur.append(c)
            if c == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    cur.append('"')
                    i += 1
                else:
                    in_str = False
        elif c == '"':
            in_str = True
            cur.append(c)
        elif c in "([{":
            depth += 1
            cur.append(c)
        elif c in ")]}":
            depth -= 1
            cur.append(c)
        elif c == sep and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(c)
        i += 1
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


def strings(text):
    return [s.replace('""', '"') for s in re.findall(r'"((?:[^"]|"")*)"', text)]


def query_blocks(path):
    """Yield (query name, let-body text) for each let ... in ... block in a file."""
    text = strip_comments(path.read_text(encoding="utf-8"))
    for m in re.finditer(r"(?m)^let\b", text):
        start = m.end()
        depth, i, n = 0, start, len(text)
        in_str = False
        end = None
        while i < n:
            c = text[i]
            if in_str:
                if c == '"':
                    if i + 1 < n and text[i + 1] == '"':
                        i += 1
                    else:
                        in_str = False
            elif c == '"':
                in_str = True
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
            elif depth == 0 and re.match(r"\bin\b", text[i:i + 3]) and not re.match(r"\w", text[i - 1:i]):
                end = i
                break
            i += 1
        if end is not None:
            yield text[start:end]


def steps_of(body):
    steps = []
    for part in split_top(body):
        m = re.match(r'^(#"(?:[^"]|"")*"|[A-Za-z_]\w*)\s*=\s*(.*)$', part, re.S)
        if m:
            name = m.group(1)
            name = name[2:-1] if name.startswith('#"') else name
            steps.append((name, m.group(2).strip()))
    return steps


# ---------- sources ----------

def read_headers(path):
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        return next(csv.reader(fh), [])


def resolve_path(expr):
    m = re.search(r'pRootFolder\s*&\s*"([^"]*)"', expr)
    if m:
        return PBI / m.group(1).replace("\\", "/").lstrip("/")
    m = re.search(r'"((?:PowerBI[\\/])?(?:RawDataFolders|SeedData)[^"]*)"', expr)
    if m:
        p = m.group(1).replace("\\", "/")
        return ROOT / p if p.startswith("PowerBI") else PBI / p
    return None


def data_files(p):
    if p is None:
        return []
    if p.is_dir():
        return sorted(f for f in p.iterdir() if f.suffix.lower() == ".csv" and not f.name.lower().startswith(SKIP) and not f.name.startswith("_"))
    return [p] if p.exists() else []


def normalise_name(h):
    return " ".join(h.replace("\n", " ").replace("\r", " ").split())


# ---------- value checks ----------

NUM = re.compile(r"^[-+]?(\d{1,3}(,\d{3})+|\d+)?(\.\d+)?([eE][-+]?\d+)?%?$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}([ T].*)?$")


def check_values(files, typed, headers_fix=False):
    """typed: {column: 'number'|'date'|'int'}. Returns list of (column, file, sample bad value, count)."""
    bad = {}
    for f in files:
        try:
            with open(f, newline="", encoding="utf-8-sig", errors="replace") as fh:
                rd = csv.DictReader(fh)
                if headers_fix:
                    rd.fieldnames = [normalise_name(h) for h in rd.fieldnames or []]
                for i, row in enumerate(rd):
                    if i >= MAX_ROWS:
                        break
                    for col, kind in typed.items():
                        v = (row.get(col) or "").strip()
                        if v == "" or v.lower() in ("null",):
                            continue
                        ok = bool(DATE.match(v)) if kind == "date" else bool(NUM.match(v))
                        if kind == "int" and ok:
                            ok = re.fullmatch(r"[-+]?\d+(\.0+)?", v.replace(",", "")) is not None
                        if not ok:
                            key = (col, f.name)
                            if key not in bad:
                                bad[key] = [v, 0]
                            bad[key][1] += 1
        except OSError:
            pass
    return [(c, fn, v[0], v[1]) for (c, fn), v in bad.items()]


def type_kind(t):
    t = t.strip()
    if t in ("type number", "Number.Type", "Int64.Type", "type currency", "Currency.Type", "Percentage.Type"):
        return "int" if t == "Int64.Type" else "number"
    if t in ("type date", "Date.Type"):
        return "date"
    return None


# ---------- query follower ----------

def follow(name, body, all_queries, findings):
    steps = steps_of(body)
    cols = None  # set of column names, or None when unknown
    files = []
    file_hdrs = []
    fixed = False
    aliased = False
    known = {n for n, _ in steps}
    for sname, expr in steps:
        head = expr.split("(", 1)[0].strip()
        loc = "%s / %s" % (name, sname)

        def need(columns, what):
            if cols is None:
                return
            for c in columns:
                if c not in cols:
                    findings.append(("MISSING_COLUMN", loc, "%s uses '%s' but the table has: %s" % (what, c, ", ".join(sorted(cols)[:12]) + (" ..." if len(cols) > 12 else ""))))

        # query references
        for ref in re.findall(r'(?<!\[)#"((?:[^"]|"")*)"(?!\s*=)', expr):
            if ref not in all_queries and ref not in known and not ref.startswith("Removed") and " " in ref and ref[0].isupper():
                findings.append(("UNKNOWN_QUERY", loc, "refers to #\"%s\", no query with that name" % ref))

        if head in ("Csv.Document", "Folder.Files", "fnCombineFolder", "Table.PromoteHeaders") and cols is None and not files:
            p = resolve_path(expr)
            if head == "Table.PromoteHeaders":
                continue
            if p is not None:
                fl = data_files(p)
                if not fl and head == "fnCombineFolder":
                    third = split_top(expr[len(head) + 1: expr.rfind(")")])
                    if len(third) >= 3 and third[2].startswith("{"):
                        cols = set(strings(third[2])) | {"Data Source File", "Refresh Date"}  # empty folder keeps these
                        continue
                if not fl:
                    findings.append(("NO_SOURCE_FILE", loc, "%s has no data files" % p.relative_to(PBI)))
                    return
                files = fl
        if head == "fnCombineFolder" and files:
            file_hdrs = [set(read_headers(f)) for f in files]
            hs = set()
            for f in files:
                hs.update(read_headers(f))
            cols = set(hs) | {"Data Source File", "Refresh Date"}
            continue
        if head == "Table.PromoteHeaders" and files and cols is None:
            hs = set()
            for f in files:
                hs.update(read_headers(f))
            cols = set(hs)
            continue
        if "fnAlias" in expr or "Table.RenameColumns" in expr and sname.startswith("Alias"):
            aliased = True
        if head == "Table.TransformColumnNames":
            fixed = True
            if cols is not None:
                cols = {normalise_name(c) for c in cols}
            continue

        args = expr[len(head) + 1:]
        args = args[: args.rfind(")")] if ")" in args else args
        parts = split_top(args)

        if head == "Table.SelectColumns" and len(parts) >= 2:
            if file_hdrs and len(file_hdrs) > 1 and not aliased:
                norm = [{normalise_name(h) if fixed else h for h in hs_} for hs_ in file_hdrs]
                for col in strings(parts[1]):
                    have = sum(col in h for h in norm)
                    if 0 < have < len(norm) and (loc, col) in ACCEPTED_SOURCE_GAPS:
                        continue
                    if 0 < have < len(norm):
                        findings.append(("PARTIAL_COLUMN", loc, "'%s' is in %d of %d source files; the others get blanks" % (col, have, len(norm))))
                    elif have == 0 and len(parts) >= 3 and "UseNull" in parts[2]:
                        findings.append(("PARTIAL_COLUMN", loc, "'%s' is in none of the %d source files; it will be all blanks" % (col, len(norm))))
            if not (len(parts) >= 3 and "MissingField" in parts[2]):
                need(strings(parts[1]), "Table.SelectColumns")
            elif cols is not None and "UseNull" in parts[2]:
                pass
            if cols is not None:
                cols = set(strings(parts[1]))
        elif head == "Table.RenameColumns" and len(parts) >= 2:
            pairs = re.findall(r'\{\s*"((?:[^"]|"")*)"\s*,\s*"((?:[^"]|"")*)"\s*\}', parts[1])
            lenient = len(parts) >= 3 and "MissingField" in parts[2]
            if not lenient:
                need([a for a, _ in pairs], "Table.RenameColumns")
            if cols is not None:
                for a, b in pairs:
                    if a in cols:
                        cols.discard(a)
                        if b in cols:
                            findings.append(("DUPLICATE_COLUMN", loc, "rename '%s' to '%s' collides with an existing column" % (a, b)))
                        cols.add(b)
        elif head == "Table.RemoveColumns" and len(parts) >= 2:
            lenient = len(parts) >= 3 and "MissingField" in parts[2]
            if not lenient:
                need(strings(parts[1]), "Table.RemoveColumns")
            if cols is not None:
                cols -= set(strings(parts[1]))
        elif head == "Table.AddColumn" and len(parts) >= 2:
            new = strings(parts[1])[:1]
            if cols is not None and new:
                if new[0] in cols:
                    findings.append(("DUPLICATE_COLUMN", loc, "Table.AddColumn adds '%s' but the table already has it" % new[0]))
                cols.add(new[0])
        elif head == "Table.TransformColumnTypes" and len(parts) >= 2:
            pairs = re.findall(r'\{\s*"((?:[^"]|"")*)"\s*,\s*([^{}]+?)\s*\}', parts[1])
            need([a for a, _ in pairs], "Table.TransformColumnTypes")
            typed = {a: type_kind(t) for a, t in pairs if type_kind(t)}
            if files and typed and sname == next((s for s, e in steps if e.startswith("Table.TransformColumnTypes")), sname):
                for col, fn, val, cnt in check_values(files, typed, headers_fix=fixed):
                    findings.append(("BAD_VALUE", loc, "column '%s' typed for conversion but %d value(s) in %s will not convert, e.g. '%s'" % (col, cnt, fn, val)))
        elif head in ("Table.ReplaceValue",) and len(parts) >= 5:
            need(strings(parts[-1]), "Table.ReplaceValue")
        elif head in ("Table.SelectRows", "Table.Distinct", "Table.Sort", "Table.Buffer", "Table.FillDown", "Table.ReplaceValue", "Table.TransformColumns"):
            if head == "Table.TransformColumns" and len(parts) >= 2:
                need(re.findall(r'\{\s*"((?:[^"]|"")*)"\s*,', parts[1]), "Table.TransformColumns")
        else:
            cols = None  # a step we do not model: stop checking this query's columns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", help="query file stem, e.g. 16_Fact_PrimaryArticle")
    args = ap.parse_args()

    model_names = set()
    import json
    for t in json.loads((PBI / "model.bim").read_text(encoding="utf-8"))["model"]["tables"]:
        model_names.add(t["name"])
    findings = []
    for f in sorted(PQ.glob("*.pq")):
        if args.only and f.stem != args.only:
            continue
        for i, body in enumerate(query_blocks(f)):
            follow(f.stem if i == 0 else "%s#%d" % (f.stem, i + 1), body, model_names | {"Fact Primary Sales"}, findings)
    if not findings:
        print("No refresh risks found by this check (it does not model joins or custom functions).")
        return 0
    seen = set()
    for kind, loc, msg in findings:
        key = (kind, loc, msg)
        if key in seen:
            continue
        seen.add(key)
        print("%-16s %s\n    %s" % (kind, loc, msg))
    print("\n%d finding(s)." % len(seen))
    return 1


if __name__ == "__main__":
    sys.exit(main())
