#!/usr/bin/env python3
"""Turn the monthly Nielsen workbooks (.xlsb) into plain CSVs under data/nielsen/.

The workbooks stay outside Git. What is committed is aggregate market data only
(market x fact x brand x month), with every number copied as it appears in the
report: nothing is rounded, filled or converted. A blank cell stays blank.

Usage:
    python scripts/extract_nielsen_report.py \\
        --facewash Nielson_FW_Report_Aug26.xlsb --shampoo Nielson_Shampoo_Report_Aug26.xlsb \\
        --label Aug26 --out data/nielsen

Needs pyxlsb (pip install pyxlsb). Reading is separated from the transforms so the
transforms can be tested without a workbook.
"""
import argparse
import csv
import re
from pathlib import Path

MONTH = re.compile(r"^[A-Z][a-z]{2} \d{2}$")
# Facts kept from the pack sheets (the full sheets are ~2,400 rows each and not needed).
PACK_FACTS = ("Sales Value in Cr.", "Sales (Vol (KG/LT/000NO))", "Wghtd Dist Handling", "Wghtd Dist Out of Stock")
SNAPSHOT_SHEETS = {"facewash": "SFW Snapshot", "shampoo": "Shampoo Snapshot"}
CATEGORY_NAME = {"facewash": "FACE WASH", "shampoo": "BOTTLES"}
OWN_BRAND = "MAMAEARTH"


def read_sheet(path: Path, sheet: str) -> list[list]:
    from pyxlsb import open_workbook      # imported here: tests do not need the dependency
    with open_workbook(str(path)) as wb, wb.get_sheet(sheet) as sh:
        return [[c.v for c in row] for row in sh.rows()]


def clean(rows: list[list]) -> list[list]:
    """Drop fully empty rows and pad every row to the header width."""
    width = len(rows[0])
    out = [rows[0]]
    for row in rows[1:]:
        if any(v not in (None, "") for v in row):
            out.append((list(row) + [None] * width)[:width])
    return out


def month_columns(header: list) -> list[str]:
    return [h for h in header if isinstance(h, str) and MONTH.match(h)]


def snapshot_rows(rows: list[list]) -> list[list]:
    rows = clean(rows)
    header = rows[0]
    if header[:3] != ["Markets", "Facts", "Products"]:
        raise ValueError(f"unexpected snapshot header: {header[:3]}")
    if not month_columns(header):
        raise ValueError("snapshot has no monthly columns")
    return rows


def pack_rows(rows: list[list], *, brand_sheet: bool) -> list[list]:
    """Category x Basepack, or Brand x Basepack reduced to Mamaearth; limited to PACK_FACTS."""
    rows = clean(rows)
    header = rows[0]
    fact = header.index("Facts")
    brand = header.index("BRAND") if brand_sheet else None
    keep = [header]
    for row in rows[1:]:
        if row[fact] not in PACK_FACTS:
            continue
        if brand_sheet and str(row[brand]).strip().upper() != OWN_BRAND:
            continue
        keep.append(row)
    return keep


def write_csv(path: Path, rows: list[list]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for row in rows:
            writer.writerow(["" if v is None else v for v in row])


def extract(category: str, workbook: Path, label: str, out: Path) -> list[Path]:
    snap = read_sheet(workbook, SNAPSHOT_SHEETS[category])
    written = []
    name = {"facewash": "FW", "shampoo": "Shampoo"}[category]
    path = out / f"Nielsen_{name}_Snapshot_{label}.csv"
    write_csv(path, snapshot_rows(snap)); written.append(path)
    for sheet, brand_sheet, tag in (("Category x Basepack", False, "PacksCategory"), ("Brand x Basepack", True, "PacksMamaearth")):
        path = out / f"Nielsen_{name}_{tag}_{label}.csv"
        write_csv(path, pack_rows(read_sheet(workbook, sheet), brand_sheet=brand_sheet)); written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--facewash", type=Path, required=True)
    parser.add_argument("--shampoo", type=Path, required=True)
    parser.add_argument("--label", required=True, help="period label used in file names, e.g. Aug26")
    parser.add_argument("--out", type=Path, default=Path("data/nielsen"))
    args = parser.parse_args()
    for category, workbook in (("facewash", args.facewash), ("shampoo", args.shampoo)):
        for path in extract(category, workbook, args.label, args.out):
            print("wrote", path, f"({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
