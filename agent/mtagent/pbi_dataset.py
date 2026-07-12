"""Command: "Build the Power BI-ready dataset from the latest offtake files."

Fully automated (steps 1-4 of the workflow: validate sources -> build
datasets -> generate dim/fact -> validate keys). Reads real committed
offtake CSVs (``PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_*.csv``)
and the seed masters (``PowerBI/SeedData/Masters/ChainMaster.csv`` /
``ArticleMaster.csv``) — never fabricates data, never writes to a source
file. All outputs go to ``agent/pbi_build/<build_id>/`` (gitignored).

NOTE on master coverage: the committed ``ArticleMaster.csv`` is a small
SEED file (13 reference SKUs), not the full production article master. A
mostly-unmapped article exception report against that seed is therefore
EXPECTED, not a bug — see ``Data_Quality_Report``'s note field. Point
``masters_dir`` at the real production master export (via config) for
full coverage. Chain-level mapping uses the full 45-chain ChainMaster and
is representative.
"""
from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from .config import Config
from .fyrules import MON3_NUM, fy_tag_from_ym

REQUIRED_OFFTAKE_COLUMNS = [
    "Zone", "State", "Chain Name", "DC Code", "Site Code", "Site Name",
    "Article", "EAN", "Brand", "Category", "Sub_category",
    "MRP", "Sales Qty", "MRP Sales Value", "NSV", "Month", "Year",
]

_FILENAME_RE = re.compile(r"_([A-Za-z]{3})_(\d{2})\.csv$")
_MIN_COMPLETE_ROWS = 1000   # heuristic: fewer rows than this -> treat month as incomplete


def _norm_key(s: str) -> str:
    """TRIM + UPPER + strip non-alphanumerics — the same normalization
    contract used elsewhere in the agent's DuckDB views, so a chain like
    'D-Mart' and 'Dmart' key-match while a genuine gap like 'Frankros'
    vs. 'Frank Ross' still correctly reports as unmapped.
    """
    return re.sub(r"[^A-Z0-9]", "", (s or "").strip().upper())


def discover_offtake_files(raw_dir: Path) -> list[tuple[int, int, Path, str]]:
    """Return [(year, month, path, label), ...] sorted oldest -> newest,
    skipping template/readme files.
    """
    out = []
    for p in sorted(raw_dir.glob("offtake_store_article_*.csv")):
        m = _FILENAME_RE.search(p.name)
        if not m:
            continue
        mon3, yy = m.group(1).title(), int(m.group(2))
        if mon3 not in MON3_NUM:
            continue
        year = 2000 + yy
        month = MON3_NUM[mon3]
        out.append((year, month, p, f"{mon3}'{yy:02d}"))
    return sorted(out, key=lambda t: (t[0], t[1]))


def _count_rows(path: Path) -> int:
    with open(path, newline="", encoding="utf-8") as fh:
        return sum(1 for _ in fh) - 1  # minus header


def load_chain_master(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[_norm_key(row["Chain"])] = row
    return out


def load_article_master(path: Path) -> dict:
    out = {}
    if not path.exists():
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out[_norm_key(row["EAN Code"])] = row
    return out


def build_dataset(cfg: Config, raw_dir: Path | None = None, masters_dir: Path | None = None) -> dict:
    root = cfg.root()
    raw_dir = raw_dir or (root / "PowerBI" / "RawDataFolders" / "Offtake_Monthly")
    masters_dir = masters_dir or (root / "PowerBI" / "SeedData" / "Masters")

    # --- Step 1: validate source files -----------------------------------
    if not raw_dir.exists():
        return {"blocked_reason": f"source folder not found: {raw_dir}"}
    files = discover_offtake_files(raw_dir)
    if not files:
        return {"blocked_reason": f"no offtake_store_article_*.csv files found in {raw_dir}"}

    year, month, path, label = files[-1]
    row_count = _count_rows(path)
    excluded_incomplete = None
    if row_count < _MIN_COMPLETE_ROWS and len(files) > 1:
        excluded_incomplete = label
        year, month, path, label = files[-2]
        row_count = _count_rows(path)

    with open(path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    missing_cols = [c for c in REQUIRED_OFFTAKE_COLUMNS if c not in header]
    if missing_cols:
        return {"blocked_reason": f"{path.name} is missing required column(s): {missing_cols}"}
    idx = {h: i for i, h in enumerate(header)}

    # --- masters -----------------------------------------------------
    chain_master = load_chain_master(masters_dir / "ChainMaster.csv")
    article_master = load_article_master(masters_dir / "ArticleMaster.csv")

    # --- Step 2/3: stream-aggregate into fact + detect exceptions -------
    fact = defaultdict(lambda: {"NSV": 0.0, "MRP_Sales_Value": 0.0, "Sales_Qty": 0.0, "sites": set()})
    unmapped_chains = defaultdict(lambda: {"count": 0, "nsv": 0.0})
    unmapped_articles = defaultdict(lambda: {"count": 0, "nsv": 0.0})
    key_seen = defaultdict(int)
    blank_key_rows = 0
    blank_key_nsv = 0.0
    blank_field_counts = {"Site Code": 0, "EAN": 0, "Chain Name": 0}
    fy_tag = fy_tag_from_ym(year, month)

    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        next(reader)  # header
        for row in reader:
            try:
                nsv = float(row[idx["NSV"]] or 0)
                mrp_val = float(row[idx["MRP Sales Value"]] or 0)
                qty = float(row[idx["Sales Qty"]] or 0)
            except (ValueError, IndexError):
                blank_key_rows += 1
                continue

            site_code = row[idx["Site Code"]].strip()
            ean = row[idx["EAN"]].strip()
            chain_raw = row[idx["Chain Name"]].strip()
            zone = row[idx["Zone"]].strip().upper()

            if not site_code or not ean or not chain_raw:
                blank_key_rows += 1
                blank_key_nsv += nsv
                if not site_code:
                    blank_field_counts["Site Code"] += 1
                if not ean:
                    blank_field_counts["EAN"] += 1
                if not chain_raw:
                    blank_field_counts["Chain Name"] += 1
                continue

            biz_key = (site_code, ean, label)
            key_seen[biz_key] += 1

            chain_key = _norm_key(chain_raw)
            chain_row = chain_master.get(chain_key)
            if chain_row is None:
                unmapped_chains[chain_raw]["count"] += 1
                unmapped_chains[chain_raw]["nsv"] += nsv
                chain_out = f"UNMAPPED:{chain_raw}"
            else:
                chain_out = chain_row["Account"]

            article_key = _norm_key(ean)
            article_row = article_master.get(article_key)
            if article_row is None:
                unmapped_articles[ean]["count"] += 1
                unmapped_articles[ean]["nsv"] += nsv
                brand = row[idx["Brand"]].strip()
                category = row[idx["Category"]].strip()
                sub_category = row[idx["Sub_category"]].strip()
            else:
                brand = article_row["Brand"]
                category = article_row["Category"]
                sub_category = article_row["Sub-category"]

            fact_key = (fy_tag, label, zone, chain_out, ean, brand, category, sub_category)
            f = fact[fact_key]
            f["NSV"] += nsv
            f["MRP_Sales_Value"] += mrp_val
            f["Sales_Qty"] += qty
            f["sites"].add(site_code)

    duplicate_keys = {k: c for k, c in key_seen.items() if c > 1}

    # --- write outputs -------------------------------------------------
    build_id = f"{fy_tag}_{label.replace(chr(39), '')}"
    out_dir = cfg.path(cfg.pbi_build_dir) / build_id
    out_dir.mkdir(parents=True, exist_ok=True)

    fact_path = out_dir / "Fact_OfftakeSales.csv"
    with open(fact_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["FY", "Month", "Zone", "Chain", "EAN", "Brand", "Category",
                    "Sub_Category", "NSV", "MRP_Sales_Value", "Sales_Qty", "Store_Count"])
        for (fy, mon, zone, chain, ean, brand, cat, subcat), v in sorted(fact.items()):
            w.writerow([fy, mon, zone, chain, ean, brand, cat, subcat,
                        round(v["NSV"], 4), round(v["MRP_Sales_Value"], 2),
                        round(v["Sales_Qty"], 2), len(v["sites"])])

    dim_date_path = out_dir / "Dim_Date.csv"
    with open(dim_date_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["FY", "Month", "MonthNo", "Quarter"])
        fy_month_no = month - 3 if month >= 4 else month + 9
        quarter = f"Q{-(-fy_month_no // 3)}"
        w.writerow([fy_tag, label, month, quarter])

    dim_chain_path = out_dir / "Dim_Chain.csv"
    with open(dim_chain_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Chain", "Account", "Chain Type", "Primary Zone", "Active"])
        for row in chain_master.values():
            w.writerow([row["Chain"], row["Account"], row["Chain Type"], row["Primary Zone"], row["Active"]])

    dim_article_path = out_dir / "Dim_Article.csv"
    with open(dim_article_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Article Code", "Article Description", "EAN Code", "Brand", "Category", "Sub-category", "Range", "Pack Size"])
        for row in article_master.values():
            w.writerow([row["Article Code"], row["Article Description"], row["EAN Code"],
                        row["Brand"], row["Category"], row["Sub-category"], row["Range"], row["Pack Size"]])

    exc_path = out_dir / "Mapping_Exception_Report.csv"
    with open(exc_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["exception_type", "value", "row_count", "nsv_impact"])
        for chain, d in sorted(unmapped_chains.items(), key=lambda kv: -kv[1]["nsv"]):
            w.writerow(["unmapped_chain", chain, d["count"], round(d["nsv"], 2)])
        for ean, d in sorted(unmapped_articles.items(), key=lambda kv: -kv[1]["nsv"])[:500]:
            w.writerow(["unmapped_article_ean", ean, d["count"], round(d["nsv"], 2)])

    source_nsv_total = sum(v["NSV"] for v in fact.values()) + blank_key_nsv
    fact_nsv_total = sum(v["NSV"] for v in fact.values())

    dq_path = out_dir / "Data_Quality_Report.csv"
    with open(dq_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "value", "note"])
        w.writerow(["latest_month_used", label, "excluded_incomplete_month=" + str(excluded_incomplete)])
        w.writerow(["source_row_count", row_count, ""])
        w.writerow(["blank_key_rows_dropped", blank_key_rows,
                    f"excluded from Fact -- by field: {blank_field_counts}"])
        w.writerow(["duplicate_business_keys", len(duplicate_keys), "(site, ean, month) seen >1x in source"])
        w.writerow(["unmapped_chains", len(unmapped_chains), "see Mapping_Exception_Report"])
        w.writerow(["unmapped_articles", len(unmapped_articles),
                    "ArticleMaster.csv is a small seed (13 SKUs) -- high unmapped count here is expected, "
                    "not a data-quality defect; supply the production master for full coverage"])

    recon_path = out_dir / "Source_Reconciliation_Report.csv"
    variance = round(source_nsv_total - fact_nsv_total, 6)
    with open(recon_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["metric", "source_value", "output_value", "variance", "status"])
        w.writerow(["NSV", round(source_nsv_total, 2), round(fact_nsv_total, 2), variance,
                    "PASS" if abs(variance) < 0.01 else "FAIL"])
        w.writerow(["row_count", row_count, sum(1 for _ in fact), "n/a (fact is aggregated, not 1:1)", "INFO"])

    build_log = {
        "build_id": build_id, "source_file": str(path.relative_to(root)),
        "fy": fy_tag, "month": label, "source_row_count": row_count,
        "fact_row_count": len(fact), "blank_key_rows_dropped": blank_key_rows,
        "blank_field_counts": blank_field_counts,
        "duplicate_business_keys": len(duplicate_keys),
        "unmapped_chains": len(unmapped_chains), "unmapped_articles": len(unmapped_articles),
        "reconciliation_variance": variance,
    }
    log_path = out_dir / "Dataset_Build_Log.json"
    log_path.write_text(json.dumps(build_log, indent=2), encoding="utf-8")

    warning = ""
    if unmapped_chains or blank_key_rows or abs(variance) >= 0.01:
        warning = (f"{len(unmapped_chains)} unmapped chain(s), {blank_key_rows} blank-key row(s) dropped, "
                   f"NSV reconciliation variance {variance}")

    return {
        "output_file": str(out_dir.relative_to(root)),
        "validation_result": json.dumps(build_log),
        "warning": warning,
    }
