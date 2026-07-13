"""Command: "derive-npi-list" — derive the NPI universe from the primary
sell-in history (business-approved rule).

The leadership NPI list file never arrived, but the repo carries the real
committed primary-article history (``PowerBI/RawDataFolders/
Primary_Article_Monthly/primary_article_*.csv``, Apr'25 onward). The rule
confirmed by the business: **an article is an NPI if its primary (sell-in)
starts recently** — "consider from where the primary has been started, and
that article to be considered for NPI".

Derivation, fully data-driven (THE ONE FY RULE — the window is the latest
FY present in the data, never a hardcoded year):

- Scan every committed primary month; record each EAN's FIRST month of
  primary appearance (any invoiced row).
- NPI = first primary appearance falls in the latest FY in the data
  (currently FY27, i.e. Apr'26 onward). Articles already selling in
  earlier months are established, not NPIs.
- **Censoring caveat** (stamped into the derivation report): history
  starts Apr'25, so an article first seen in Apr'25 may have launched
  earlier — that only affects OLD articles, never the NPI set itself.

Output: ``PowerBI/SeedData/Masters/NPI_List.csv`` — the exact path the
diff engine (``cfg.npi_list``) already reads and the gated DAX §D
(``'NPI List'``) binds to. The EAN column is named ``EAN`` (and the
primary code column deliberately NOT ``Article``/``Article Code``) so the
diff engine's column-priority matching lands on the EAN, which is the one
key shared by primary and offtake extracts — their internal article codes
are different numbering systems.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .config import Config
from .fyrules import MON3_NUM, fy_tag_from_ym

_PRIMARY_GLOB = "primary_article_*.csv"


def discover_primary_files(raw_dir: Path) -> list[tuple[int, int, Path, str]]:
    import re
    rx = re.compile(r"_([A-Za-z]{3})_(\d{2})\.csv$")
    out = []
    for p in sorted(raw_dir.glob(_PRIMARY_GLOB)):
        m = rx.search(p.name)
        if not m:
            continue
        mon3, yy = m.group(1).title(), int(m.group(2))
        if mon3 not in MON3_NUM:
            continue
        out.append((2000 + yy, MON3_NUM[mon3], p, f"{mon3}'{yy:02d}"))
    return sorted(out, key=lambda t: (t[0], t[1]))


def derive_npi_list(cfg: Config, raw_dir: Path | None = None) -> dict:
    root = cfg.root()
    raw_dir = raw_dir or (root / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly")
    if not raw_dir.exists():
        return {"blocked_reason": f"primary article folder not found: {raw_dir}"}
    files = discover_primary_files(raw_dir)
    if not files:
        return {"blocked_reason": f"no {_PRIMARY_GLOB} files found in {raw_dir}"}

    first_seen: dict = {}     # ean -> (year, month, label)
    attrs: dict = {}          # ean -> latest-known descriptive attributes
    rows_scanned = 0
    for year, month, path, label in files:
        with open(path, newline="", encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                ean = (row.get("EAN No.") or "").strip()
                if not ean:
                    continue
                rows_scanned += 1
                if ean not in first_seen:
                    first_seen[ean] = (year, month, label)
                attrs[ean] = {
                    "Primary Article Code": (row.get("Article Code") or "").strip(),
                    "Description": (row.get("Description") or "").strip(),
                    "Brand": (row.get("brand") or "").strip(),
                    "Category": (row.get("category") or "").strip(),
                    "Sub-category": (row.get("sub_category") or "").strip(),
                }

    if not first_seen:
        return {"blocked_reason": "no EAN-bearing rows found in the primary sources"}

    # data-driven NPI window: the latest FY present in the history
    latest_fy = fy_tag_from_ym(*max((y, m) for y, m, _ in first_seen.values()))
    earliest = min((y, m) for y, m, _ in first_seen.values())
    npis = {ean: v for ean, v in first_seen.items()
            if fy_tag_from_ym(v[0], v[1]) == latest_fy}

    out_path = root / "PowerBI" / "SeedData" / "Masters" / "NPI_List.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["EAN", "Primary Article Code", "Description", "Brand", "Category",
                    "Sub-category", "First Primary Month", "NPI FY"])
        for ean, (y, m, label) in sorted(npis.items(), key=lambda kv: (kv[1][0], kv[1][1], kv[0])):
            a = attrs[ean]
            w.writerow([ean, a["Primary Article Code"], a["Description"], a["Brand"],
                        a["Category"], a["Sub-category"], label, latest_fy])

    report = {
        "npi_window_fy": latest_fy,
        "npi_count": len(npis),
        "total_articles_in_history": len(first_seen),
        "history_months": [label for _, _, _, label in files],
        "rows_scanned": rows_scanned,
        "rule": "NPI = first primary (sell-in) appearance falls in the latest FY present in the data",
        "censoring_caveat": f"history starts {files[0][3]} -- articles first seen then may have "
                             "launched earlier; affects only non-NPI classification, never the NPI set",
        "output": str(out_path.relative_to(root)),
    }
    report_dir = cfg.path(cfg.pbi_build_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "NPI_Derivation_Report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "output_file": str(out_path.relative_to(root)),
        "validation_result": json.dumps(report),
        "warning": "",
    }
