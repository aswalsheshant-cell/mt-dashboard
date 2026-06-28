#!/usr/bin/env python3
"""
Split the heavy article-level secondary/offtake file (store x article, .xlsb)
into month-wise CSVs for the Power BI folder refresh — and PRINT THE EXACT
HEADERS so the offtake query mapping is locked with no assumptions.

Same format and options as scripts/split_primary_article_xlsb.py. Runs locally
on the machine where the file is downloaded (the ~185 MB file cannot be pulled
into the cloud session — Drive egress is blocked and .xlsb isn't text-readable).

It does NOT rename any columns — it passes the source headers through verbatim.
Column mapping is finalised separately in Power Query (query 11 / Offtake) once
the printed headers are confirmed.

Usage:
    pip install pyxlsb
    # (a) headers only — paste the printed header line back to lock the mapping:
    python scripts/split_offtake_store_article_xlsb.py \
        "FY-24-26 Chain offtake Store Wise File till May.xlsb" --headers-only
    # (b) split month-wise into the offtake watch folder:
    python scripts/split_offtake_store_article_xlsb.py \
        "FY-24-26 Chain offtake Store Wise File till May.xlsb" \
        "C:/MT-Dashboard/RawDataFolders/Offtake_Monthly"
"""
import sys, os, csv, argparse, datetime, re

def open_wb(path):
    import pyxlsb
    return pyxlsb.open_workbook(path)

def serial_to_month(v):
    if isinstance(v, (int, float)):
        d = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=float(v))
        return d.strftime("%b'%y")
    s = str(v).strip()
    m = re.match(r"([A-Za-z]+)[''`]?(\d{2,4})", s)
    if m:
        return f"{m.group(1)[:3].title()}'{m.group(2)[-2:]}"
    return s

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

def split(path, outdir, sheet=None, month_col=None, header_row=0, prefix="offtake_store_article"):
    os.makedirs(outdir, exist_ok=True)
    wb = open_wb(path)
    sheets = [sheet] if sheet else wb.sheets
    writers, files, counts = {}, {}, {}
    header = None; mc = None; total = 0
    for sh in sheets:
        with wb.get_sheet(sh) as s:
            for i, row in enumerate(s.rows()):
                vals = [c.v for c in row]
                if i < header_row:
                    continue
                if i == header_row:
                    header = [str(v).strip() if v is not None else f"col{j}"
                              for j, v in enumerate(vals)]
                    gc = month_col
                    if gc is None:
                        for j, h in enumerate(header):
                            if h.strip().lower() in ("month", "revised month", "offtake month"):
                                gc = j; break
                    if gc is None:
                        raise SystemExit("Could not find a 'Month' column; pass --month-col <index>. "
                                         f"Headers were: {header}")
                    mc = gc if isinstance(gc, int) else header.index(gc)
                    continue
                if not any(v is not None for v in vals):
                    continue
                while len(vals) < len(header):
                    vals.append(None)
                label = serial_to_month(vals[mc])
                safe = re.sub(r"[^A-Za-z0-9]", "_", label)
                if safe not in writers:
                    fh = open(os.path.join(outdir, f"{prefix}_{safe}.csv"), "w", newline="", encoding="utf-8")
                    w = csv.writer(fh); w.writerow(header)
                    writers[safe] = w; files[safe] = fh; counts[safe] = 0
                writers[safe].writerow(vals[:len(header)])
                counts[safe] += 1; total += 1
    for fh in files.values():
        fh.close()
    print(f"\nHEADER ({len(header)} cols): {header}")
    print(f"\nTotal rows: {total:,}  ->  {len(counts)} month files in {outdir}")
    for k in sorted(counts):
        print(f"  {prefix}_{k}.csv : {counts[k]:,} rows")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("xlsb")
    ap.add_argument("outdir", nargs="?", default="./Offtake_Monthly")
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
