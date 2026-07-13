"""Command: "derive-article-master" — build a real ArticleMaster from the
offtake data itself (business-approved cross-chain consolidation).

The committed ``SeedData/Masters/ArticleMaster.csv`` is a 13-row synthetic
seed whose EANs match nothing real, so article mapping sat at ~0%. The
production master export never arrived — but every offtake row already
carries the article's own attributes (Brand, Category, Sub_category, Range,
standardized description, net weight). The business rule confirmed for this
command: *the same article maintained under different chains is the same
article* — so consolidating those attributes per EAN across ALL chains and
ALL committed months yields a real, data-derived master.

Consolidation rule, per EAN and per field: the most frequent non-blank value
(ties broken by first-seen). Nothing is invented — every value in the output
exists verbatim in the source rows. Where chains genuinely disagree on a
MATERIAL field (Brand or Category), the majority value is still written but
the EAN is listed in ``Article_Conflict_Report.csv`` with every variant and
its row count, for explicit human adjudication — silent majority-wins on a
material conflict is exactly the kind of quiet guess this pipeline refuses
to make.

Output goes to ``PowerBI/RawDataFolders/Masters/ArticleMaster.csv`` — the
production drop-in location that ``resolve_master_file`` already prefers
over the seed, so the very next ``build-dataset`` run picks it up with no
config change. (A later real production export dropped into the same path
simply replaces this derived one.)
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from .config import Config
from .fyrules import MON3_NUM  # noqa: F401  (kept for parity with sibling modules)
from .pbi_dataset import PRODUCTION_MASTERS_DIR, discover_offtake_files

# offtake source column -> ArticleMaster output column
_FIELD_MAP = [
    ("Article", "Article Code"),
    ("Description as per Fountain", "Article Description"),
    ("Brand", "Brand"),
    ("Category", "Category"),
    ("Sub_category", "Sub-category"),
    ("Range", "Range"),
    ("Net Weight", "Pack Size"),
]
_MATERIAL_FIELDS = ("Brand", "Category")   # cross-chain disagreement here = human decision


def derive_article_master(cfg: Config, raw_dir: Path | None = None) -> dict:
    root = cfg.root()
    raw_dir = raw_dir or (root / "PowerBI" / "RawDataFolders" / "Offtake_Monthly")
    if not raw_dir.exists():
        return {"blocked_reason": f"source folder not found: {raw_dir}"}
    files = discover_offtake_files(raw_dir)
    if not files:
        return {"blocked_reason": f"no offtake_store_article_*.csv files found in {raw_dir}"}

    # ean -> output field -> Counter of observed non-blank values
    values: dict = defaultdict(lambda: defaultdict(Counter))
    # ean -> field -> value -> set of chains that reported it (for the conflict report)
    chains_by_value: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    first_seen: dict = {}
    rows_scanned = 0

    for _, _, path, label in files:
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                ean = (row.get("EAN") or "").strip()
                if not ean:
                    continue
                rows_scanned += 1
                chain = (row.get("Chain Name") or "").strip()
                if ean not in first_seen:
                    first_seen[ean] = len(first_seen)
                for src, out in _FIELD_MAP:
                    val = (row.get(src) or "").strip()
                    if val:
                        values[ean][out][val] += 1
                        if out in _MATERIAL_FIELDS:
                            chains_by_value[ean][out][val].add(chain)

    if not values:
        return {"blocked_reason": "no EAN-bearing rows found in the offtake sources"}

    # consolidate: most frequent non-blank value per field, first-seen tiebreak
    master_rows = []
    conflicts = []
    for ean in sorted(values, key=lambda e: first_seen[e]):
        rec = {"EAN Code": ean}
        for _, out in _FIELD_MAP:
            counter = values[ean][out]
            rec[out] = counter.most_common(1)[0][0] if counter else ""
        for field in _MATERIAL_FIELDS:
            variants = values[ean][field]
            if len(variants) > 1:
                conflicts.append({
                    "EAN Code": ean, "field": field,
                    "chosen (majority)": rec[field],
                    "variants": "; ".join(
                        f"{val} ({cnt} rows, chains: {', '.join(sorted(chains_by_value[ean][field][val]))})"
                        for val, cnt in variants.most_common()),
                })
        master_rows.append(rec)

    out_dir = root / PRODUCTION_MASTERS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "ArticleMaster.csv"
    header = ["Article Code", "Article Description", "EAN Code", "Brand", "Category",
              "Sub-category", "Range", "Pack Size"]
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        for rec in master_rows:
            w.writerow({k: rec.get(k, "") for k in header})

    conflict_dir = cfg.path(cfg.pbi_build_dir)
    conflict_dir.mkdir(parents=True, exist_ok=True)
    conflict_path = conflict_dir / "Article_Conflict_Report.csv"
    with open(conflict_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["EAN Code", "field", "chosen (majority)", "variants"])
        w.writeheader()
        w.writerows(conflicts)

    summary = {
        "articles_derived": len(master_rows),
        "source_rows_scanned": rows_scanned,
        "source_months": [label for _, _, _, label in files],
        "material_conflicts": len(conflicts),
        "output": str(out_path.relative_to(root)),
        "conflict_report": str(conflict_path.relative_to(root)),
    }
    warning = ""
    if conflicts:
        warning = (f"{len(conflicts)} EAN(s) have cross-chain Brand/Category disagreement -- "
                   f"majority value used, human adjudication list in {conflict_path.name}")
    return {
        "output_file": str(out_path.relative_to(root)),
        "validation_result": json.dumps(summary),
        "warning": warning,
    }
