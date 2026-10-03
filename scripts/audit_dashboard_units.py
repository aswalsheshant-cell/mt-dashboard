"""Read-only source-unit audit for large monthly dashboard CSVs."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median


def _number(value: str | None, *, path: Path, row: int, column: str) -> Decimal | None:
    if value is None or not value.strip():
        return None
    try:
        return Decimal(value.strip().replace(",", ""))
    except InvalidOperation as exc:
        raise ValueError(f"{path.name} row {row}: invalid {column}") from exc


def audit_csv(
    path: Path,
    amount_column: str,
    mrp_column: str | None = None,
    *,
    sample_stride: int = 50,
    exclude_reliance_bc: bool = False,
) -> dict:
    """Return hashes, signed totals and both unit hypotheses without writing the CSV."""
    path = Path(path)
    if sample_stride < 1:
        raise ValueError("sample_stride must be positive")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    total = Decimal(0)
    governed_total = Decimal(0)
    rbc_excluded_total = Decimal(0)
    rbc_excluded_rows = 0
    rows = 0
    null_amount_rows = 0
    months = Counter()
    month_totals = Counter()
    governed_month_totals = Counter()
    ratios = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        for column in (amount_column, mrp_column):
            if column and column not in columns:
                raise ValueError(f"{path.name}: missing column {column}")
        if exclude_reliance_bc:
            for column in ("Chain Name", "Store Type"):
                if column not in columns:
                    raise ValueError(f"{path.name}: missing column {column}")
        for rows, record in enumerate(reader, start=1):
            amount = _number(record.get(amount_column), path=path, row=rows, column=amount_column)
            month = (record.get("Month") or "<blank>").strip() or "<blank>"
            excluded = exclude_reliance_bc and (
                "reliance" in (record.get("Chain Name") or "").strip().lower()
                and (record.get("Store Type") or "").strip().lower() == "brand counter"
            )
            if amount is None:
                null_amount_rows += 1
            else:
                total += amount
                if "Month" in columns:
                    month_totals[month] += amount
                if excluded:
                    rbc_excluded_total += amount
                else:
                    governed_total += amount
                    if "Month" in columns:
                        governed_month_totals[month] += amount
            if excluded:
                rbc_excluded_rows += 1
            if "Month" in columns:
                months[month] += 1
            if mrp_column and rows % sample_stride == 0 and amount is not None:
                mrp = _number(record.get(mrp_column), path=path, row=rows, column=mrp_column)
                if amount > 0 and mrp is not None and mrp > 0:
                    ratios.append(float(amount / mrp))

    return {
        "path": str(path),
        "sha256": digest.hexdigest(),
        "bytes": path.stat().st_size,
        "rows": rows,
        "null_amount_rows": null_amount_rows,
        "raw_sum": str(total),
        "governed_raw_sum": str(governed_total),
        "rbc_excluded_rows": rbc_excluded_rows,
        "rbc_excluded_raw_sum": str(rbc_excluded_total),
        "rupees_if_rupees": str(total),
        "rupees_if_lakh": str(total * Decimal(100000)),
        "median_nsv_mrp_raw": median(ratios) if ratios else None,
        "median_nsv_mrp_if_lakh": median(ratios) * 100000 if ratios else None,
        "ratio_sample_rows": len(ratios),
        "months": dict(months),
        "month_totals_raw": {month: str(value) for month, value in month_totals.items()},
        "month_totals_governed_raw": {
            month: str(value) for month, value in governed_month_totals.items()
        },
    }


def audit_sources(repo_root: Path, *, sample_stride: int = 50) -> dict:
    root = Path(repo_root).resolve()
    specs = (
        ("Offtake_Monthly", "offtake_store_article_*.csv", "NSV", "MRP Sales Value"),
        ("Primary_Article_Monthly", "primary_article_*.csv", "Inv. Net value(LOC)", "Total MRP sales"),
        ("Primary_ShipTo_Monthly", "Primary_ShipTo*.csv", "Primary NSV", "MRP Value"),
    )
    files = []
    for folder, pattern, amount_column, mrp_column in specs:
        directory = root / "PowerBI" / "RawDataFolders" / folder
        if not directory.is_dir():
            raise ValueError(f"missing source directory {directory}")
        matches = sorted(directory.glob(pattern))
        if not matches:
            raise ValueError(f"no source files matching {pattern} in {directory}")
        for path in matches:
            item = audit_csv(
                path,
                amount_column,
                mrp_column,
                sample_stride=sample_stride,
                exclude_reliance_bc=folder == "Offtake_Monthly",
            )
            item["path"] = path.relative_to(root).as_posix()
            item["source_family"] = folder
            item["amount_column"] = amount_column
            item["source_unit"] = "UNVERIFIED"
            item["scope"] = "offtake_excluding_reliance_brand_counter" if folder == "Offtake_Monthly" else "gross_source"
            files.append(item)
    return {"mode": "READ_ONLY_SOURCE_AUDIT", "model_currency_contract": "absolute_rupees", "files": files}


def write_report(report: dict, out: Path, repo_root: Path) -> None:
    root = Path(repo_root).resolve()
    out = Path(out).resolve()
    if out.is_relative_to(root / "dashboard"):
        raise ValueError("refusing to write audit data into the published dashboard")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--sample-stride", type=int, default=50)
    args = parser.parse_args(argv)
    report = audit_sources(args.repo_root, sample_stride=args.sample_stride)
    write_report(report, args.out, args.repo_root)
    print(f"Audited {len(report['files'])} source files; aggregate report: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

