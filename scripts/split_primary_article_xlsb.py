#!/usr/bin/env python3
"""
Split the heavy File 2 (Distributor article-wise primary, .xlsb) into
month-wise CSVs for the Power BI folder refresh — and PRINT THE EXACT HEADERS
so the query-16 mapping is locked with no assumptions.

Why this runs locally (not in the cloud session): the file is ~175 MB and the
session's egress proxy blocks Google Drive (403) and can't ingest a file this
size. Run this on the machine where the file is downloaded.

Usage:
    pip install pyxlsb
    python scripts/split_primary_article_xlsb.py \
        "MT, Eb2B & SIS primary April_23 to May_26.xlsb" \
        "C:/MT-Dashboard/RawDataFolders/Primary_Article_Monthly"

Step 1 (headers only): run with --headers-only to just print the header row(s):
    python scripts/split_primary_article_xlsb.py "<file>.xlsb" --headers-only

Then paste the printed header line back so the query-16 RenameColumns is finalised.
The script streams rows (low memory) and writes one CSV per month.
"""
import sys, os, csv, argparse, datetime, re

def open_wb(path):
    import pyxlsb
    return pyxlsb.open_workbook(path)

def serial_to_month(v):
    """Excel serial date or 'MMM'YY' style -> ('May'26', date) best-effort."""
    if isinstance(v, (int, float)):
        d = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=float(v))
        return d.strftime("%b'%y"), d
    s = str(v).strip()
    m = re.match(r"([A-Za-z]+)[''`]?(\d{2,4})", s)
    if m:
        mon = m.group(1)[:3].title(); yy = m.group(2)[-2:]
        return f"{mon}'{yy}", None
    return s, None

def print_headers(path):
    wb = open_wb(path)
    print("SHEETS:", wb.sheets)
    for sh in wb.sheets:
        with wb.get_sheet(sh) as s:
            for i, row in enumerate(s.rows()):
                vals = [c.v for c in row]
                while vals and vals[-1] is None:
                    vals.pop()
                print(f"\n[{sh}] row {i}:", vals)
                if i >= 2:
                    break

def split(path, outdir, sheet=None, month_col=None, header_row=0):
    os.makedirs(outdir, exist_ok=True)
    wb = open_wb(path)
    sheets = [sheet] if sheet else wb.sheets
    writers, files, counts = {}, {}, {}
    header = None
    total = 0
    for sh in sheets:
        with wb.get_sheet(sh) as s:
            for i, row in enumerate(s.rows()):
                vals = [c.v for c in row]
                if i < header_row:
                    continue
                if i == header_row:
                    header = [str(v).strip() if v is not None else f"col{j}"
                              for j, v in enumerate(vals)]
                    # locate the month column
                    global_mc = month_col
                    if global_mc is None:
                        for j, h in enumerate(header):
                            if h.strip().lower() in ("month", "revised month"):
                                global_mc = j; break
                    if global_mc is None:
                        raise SystemExit("Could not find a 'Month' column; pass --month-col <index>. "
                                         f"Headers were: {header}")
                    mc = global_mc if isinstance(global_mc, int) else header.index(global_mc)
                    continue
                if not any(v is not None for v in vals):
                    continue
                while len(vals) < len(header):
                    vals.append(None)
                label, _ = serial_to_month(vals[mc])
                safe = re.sub(r"[^A-Za-z0-9]", "_", label)
                if safe not in writers:
                    fpath = os.path.join(outdir, f"primary_article_{safe}.csv")
                    fh = open(fpath, "w", newline="", encoding="utf-8")
                    w = csv.writer(fh); w.writerow(header)
                    writers[safe] = w; files[safe] = fh; counts[safe] = 0
                writers[safe].writerow(vals[:len(header)])
                counts[safe] += 1; total += 1
    for fh in files.values():
        fh.close()
    print(f"\nHEADER ({len(header)} cols): {header}")
    print(f"\nTotal rows: {total:,}  ->  {len(counts)} month files in {outdir}")
    for k in sorted(counts):
        print(f"  primary_article_{k}.csv : {counts[k]:,} rows")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsb")
    ap.add_argument("outdir", nargs="?", default="./Primary_Article_Monthly")
    ap.add_argument("--headers-only", action="store_true")
    ap.add_argument("--sheet", default=None)
    ap.add_argument("--month-col", default=None, help="month column name or 0-based index")
    ap.add_argument("--header-row", type=int, default=0)
    a = ap.parse_args()
    if a.headers_only:
        print_headers(a.xlsb); sys.exit(0)
    mc = a.month_col
    if mc is not None and mc.isdigit():
        mc = int(mc)
    split(a.xlsb, a.outdir, a.sheet, mc, a.header_row)
