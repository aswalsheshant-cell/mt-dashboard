#!/usr/bin/env python3
"""
Data Catalog -- reusable discovery service over config/data_source_registry.yml.

Purpose: give every future analytical question (human or agent) one place to
ask "where does this number come from" and "what's the latest month available"
BEFORE searching folders by hand or concluding data is missing. This is
additive to the existing platform -- it reads the registry and the filesystem,
it does not replace build_dashboard_data.py, the release gate, or any DAX/M
logic, and it never writes to a source file.

Usage (library):
    from scripts.data_catalog import DataCatalog
    cat = DataCatalog()
    cat.find_source("offtake_nsv")
    cat.get_historical_source("offtake_nsv", "2025-08")
    cat.get_latest_available("offtake_nsv")
    cat.get_lineage("offtake_nsv")

Usage (CLI, for a quick manual check):
    python3 scripts/data_catalog.py find offtake_nsv
    python3 scripts/data_catalog.py historical offtake_nsv 2025-08
    python3 scripts/data_catalog.py latest offtake_nsv
"""
from __future__ import annotations

import glob
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "config" / "data_source_registry.yml"

# Metric name -> registry dataset_id(s), ordered by which one to try first for
# a MONTH in that range. This is the only place a metric alias lives -- do not
# duplicate this mapping elsewhere.
METRIC_ALIASES: dict[str, list[str]] = {
    "offtake_nsv": ["offtake_preagg_fy25_fy26", "offtake_article_fy27_patch"],
    "offtake": ["offtake_preagg_fy25_fy26", "offtake_article_fy27_patch"],
    "primary_nsv": ["primary_article_monthly", "primary_aug26_adhoc"],
    "primary": ["primary_article_monthly", "primary_aug26_adhoc"],
    "chain_allocation": ["chain_allocation_tool"],
    "category_mapping": ["article_category_mapping"],
    "sub_category": ["article_category_mapping"],
}

MONTH_FILE_RE = re.compile(
    r"(?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)_(?P<yy>\d{2})",
    re.IGNORECASE,
)
_MON_NUM = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


@dataclass
class SourceMatch:
    dataset_id: str
    entry: dict[str, Any]
    reason: str


class DataCatalog:
    def __init__(self, registry_path: Path = REGISTRY_PATH):
        self.registry_path = registry_path
        with open(registry_path, encoding="utf-8") as f:
            self.registry = yaml.safe_load(f)
        self.datasets: dict[str, dict[str, Any]] = self.registry.get("datasets", {})

    # ---- lookups -----------------------------------------------------
    def _candidates(self, metric: str) -> list[str]:
        ids = METRIC_ALIASES.get(metric)
        if ids:
            return ids
        if metric in self.datasets:
            return [metric]
        raise KeyError(
            f"'{metric}' is not a known metric alias or dataset_id. "
            f"Known metrics: {sorted(METRIC_ALIASES)}. "
            f"Known dataset_ids: {sorted(self.datasets)}. "
            "If this is a genuinely new metric, add it to METRIC_ALIASES here "
            "and a dataset entry to config/data_source_registry.yml -- do not "
            "silently invent a source."
        )

    def find_source(self, metric: str) -> list[SourceMatch]:
        """All registered sources for a metric, in priority order (registry order)."""
        return [SourceMatch(did, self.datasets[did], "registered for this metric")
                for did in self._candidates(metric) if did in self.datasets]

    def get_source_priority(self, metric: str, month: str | None = None) -> list[str]:
        return self._candidates(metric)

    def get_fallback_source(self, metric: str) -> str | None:
        matches = self.find_source(metric)
        for m in matches:
            fb = m.entry.get("fallback_source")
            if fb:
                return fb
        return None

    def get_validation_status(self, dataset_id: str) -> str:
        if dataset_id not in self.datasets:
            raise KeyError(f"Unknown dataset_id '{dataset_id}'")
        return self.datasets[dataset_id].get("validation_status", "UNKNOWN")

    def get_lineage(self, metric: str) -> str:
        matches = self.find_source(metric)
        if not matches:
            return f"No registered source for '{metric}' -- see docs/DATA_LINEAGE.md for what IS traced."
        lines = [f"Lineage candidates for '{metric}' (priority order):"]
        for m in matches:
            e = m.entry
            lines.append(
                f"  [{m.dataset_id}] {e.get('source_path')}\n"
                f"    pipeline: {e.get('existing_pipeline')}\n"
                f"    downstream: {e.get('downstream_outputs')}\n"
                f"    status: {e.get('validation_status')} / priority: {e.get('source_priority')}\n"
                f"    last_validated: {e.get('last_validated')}"
            )
        lines.append("Full narrative lineage: docs/DATA_LINEAGE.md")
        return "\n".join(lines)

    def get_field_mapping(self, field: str) -> str:
        """Best-effort: search registry `important_columns` and `notes` for a field name."""
        hits = []
        for did, e in self.datasets.items():
            cols = e.get("important_columns") or []
            if any(field.lower() in c.lower() for c in cols):
                hits.append((did, "important_columns", cols))
            if field.lower() in (e.get("notes") or "").lower():
                hits.append((did, "notes", None))
        if not hits:
            return (f"'{field}' not found in any registry entry's important_columns or notes. "
                    "Check docs/BUSINESS_LOGIC_REGISTRY.md (canonicalization rules BL-03) next.")
        return "\n".join(f"{did} ({where}): {cols if cols else 'mentioned in notes -- read that entry'}"
                          for did, where, cols in hits)

    # ---- filesystem discovery (never trust a hardcoded date in the YAML) --
    def _month_files(self, glob_pattern: str) -> list[tuple[int, int, Path]]:
        """Return (year, month, path) tuples for every file matching pattern,
        sorted oldest first. Year is inferred as 2000+yy (repo's convention)."""
        out = []
        for p in glob.glob(str(REPO_ROOT / glob_pattern)):
            m = MONTH_FILE_RE.search(Path(p).name)
            if not m:
                continue
            mon = _MON_NUM[m.group("mon").title()]
            yy = 2000 + int(m.group("yy"))
            out.append((yy, mon, Path(p)))
        return sorted(out)

    def get_latest_available(self, metric: str) -> dict[str, Any]:
        """Discover the actual latest month on disk for a metric's raw monthly
        source -- never trust a stale date_max written in the registry."""
        candidates = self._candidates(metric)
        result = {}
        for did in candidates:
            entry = self.datasets.get(did, {})
            path_field = entry.get("source_path", "")
            first_path = path_field.split(";")[0].strip()
            if "<Mon>_<YY>" in first_path:
                pattern = first_path.replace(str(REPO_ROOT) + "/", "")
                pattern = re.sub(r"<Mon>_<YY>", "*", pattern)
                files = self._month_files(pattern)
                if files:
                    yy, mon, p = files[-1]
                    result[did] = {"latest_file": str(p), "year": yy, "month": mon}
        return result or {"note": f"No monthly-file dataset pattern found for '{metric}' -- "
                                   f"check {candidates} in config/data_source_registry.yml directly."}

    def get_historical_source(self, metric: str, month: str) -> str:
        """month: 'YYYY-MM' or 'Mon-YY' (e.g. '2025-08' or 'Aug-25')."""
        candidates = self.find_source(metric)
        lines = [f"Historical source check for '{metric}' @ {month}:"]
        for m in candidates:
            e = m.entry
            dmin, dmax = e.get("date_min"), e.get("date_max")
            lines.append(f"  [{m.dataset_id}] declared coverage: {dmin} .. {dmax or 'DISCOVER AT RUNTIME'}")
            lines.append(f"    -> {e.get('source_path')}")
            if e.get("notes"):
                lines.append(f"    note: {e['notes'].strip().splitlines()[0]}")
        lines.append("Do not conclude MISSING until every candidate above has been checked against the actual file/JSON.")
        return "\n".join(lines)


def _cli():
    if len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    cat = DataCatalog()
    cmd, metric = sys.argv[1], sys.argv[2]
    if cmd == "find":
        for m in cat.find_source(metric):
            print(m.dataset_id, "->", m.entry.get("source_path"))
    elif cmd == "historical":
        month = sys.argv[3] if len(sys.argv) > 3 else ""
        print(cat.get_historical_source(metric, month))
    elif cmd == "latest":
        print(cat.get_latest_available(metric))
    elif cmd == "lineage":
        print(cat.get_lineage(metric))
    elif cmd == "fallback":
        print(cat.get_fallback_source(metric))
    else:
        print(f"Unknown command '{cmd}'. Use find|historical|latest|lineage|fallback.")
        raise SystemExit(1)


if __name__ == "__main__":
    _cli()
