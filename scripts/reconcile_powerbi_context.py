"""Reconcile governed source files with the dashboard figures the Power BI report must match.

Read-only. For one period it recomputes each headline figure from the committed source
CSVs using the model's own rules (Offtake source NSV is lakh; Primary source NSV is rupees;
Reliance Brand Counter is isolated from Offtake only, never from Primary) and compares it
with the same months in dashboard/data.js.

This does not run DAX. "expected_report_amount" is the dashboard (HTML) value, and
"model_inr" is what the Power BI measure has to show in rupees; a Desktop run (plan
Task 7) is what proves the measure actually does.

A missing source is None, never 0. Anything the source cannot support is labelled, not guessed.
"""
import argparse
import csv
import json
import re
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_dashboard_units import audit_csv  # noqa: E402
from reconcile_offtake_html import load_html  # noqa: E402

LAKH = Decimal(100000)
TOLERANCE_LAKH = Decimal("0.01")          # same per-month tolerance as reconcile_offtake_html
MON = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
OFFTAKE_FILE = re.compile(r"offtake_store_article_([A-Za-z]{3})_(\d{2})")
PRIMARY_FILE = re.compile(r"primary_article_([A-Za-z]{3})_(\d{2})")
DEFAULT_OFFTAKE_KEY = ["Month", "Year", "Site Code", "Article"]

M_OFFTAKE = "MT offtake NSV (excl. Reliance Brand Counter)"
M_RBC = "Reliance Brand Counter offtake NSV (isolated, offtake only)"
M_PRIMARY = "Primary NSV (gross, no Reliance Brand Counter exclusion)"
M_YOY = "MT offtake NSV YoY (like-for-like months)"
M_NPI = "NPI NSV YoY (provisional observed-only)"


def fy_tag(year: int, month: int) -> str:
    """THE ONE FY RULE: Apr-Dec of year Y is FY(Y+1); Jan-Mar of year Y is FY(Y)."""
    return f"FY{(year + 1 if month >= 4 else year) % 100:02d}"


def parse_period(period: str) -> tuple[str, list[tuple[int, int]]]:
    """Return (label, [(year, month), ...]) for 'YYYY-MM' or 'FYnn'."""
    match = re.fullmatch(r"(\d{4})-(\d{2})", period or "")
    if match and 1 <= int(match[2]) <= 12:
        return period, [(int(match[1]), int(match[2]))]
    match = re.fullmatch(r"FY(\d{2})", period or "")
    if match:
        end = 2000 + int(match[1])
        return period, [(end - 1, m) for m in range(4, 13)] + [(end, m) for m in range(1, 4)]
    raise ValueError(f"period must be 'YYYY-MM' or 'FYnn', got {period!r}")


def label(year: int, month: int) -> str:
    return f"{MON[month - 1]}-{year % 100:02d}"


def _row(metric, period, unit, status, note, **extra):
    row = {"metric": metric, "period": period, "unit": unit, "source_amount": None,
           "expected_report_amount": None, "variance": None, "model_inr": None,
           "coverage": "", "covered_months": [], "status": status, "note": note,
           "duplicate_key_rows": 0, "source_files": []}
    row.update(extra)
    return row


def _files_by_month(directory: Path, pattern: re.Pattern) -> dict[tuple[int, int], list[Path]]:
    found: dict[tuple[int, int], list[Path]] = {}
    if not directory.is_dir():
        return found
    for path in sorted(directory.glob("*.csv")):
        match = pattern.search(path.name)
        if not match or match[1].title() not in MON:
            continue
        month = MON.index(match[1].title()) + 1
        # File names carry the calendar year (Apr_26 is April 2026).
        found.setdefault((2000 + int(match[2]), month), []).append(path)
    return found


def _offtake_key_columns(repo_root: Path) -> list[str]:
    manifest = repo_root / "PowerBI/full_report_sources.json"
    if manifest.is_file():
        for source in json.loads(manifest.read_text(encoding="utf-8-sig")).get("sources", []):
            if source.get("id") == "Fact_OfftakeSales" and source.get("key_columns"):
                return list(source["key_columns"])
    return list(DEFAULT_OFFTAKE_KEY)


def _duplicate_key_rows(path: Path, key_columns: list[str]) -> int:
    seen, duplicates = set(), 0
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if any(column not in (reader.fieldnames or []) for column in key_columns):
            return 0
        for record in reader:
            key = tuple((record.get(column) or "").strip() for column in key_columns)
            if not all(key):
                continue
            if key in seen:
                duplicates += 1
            seen.add(key)
    return duplicates


def _baseline(dash: dict, kind: str, tag: str) -> dict[str, float]:
    """Dashboard monthly values (lakh) keyed by 'Mon-YY' label; empty if there is none."""
    if kind == "offtake":
        block = dash.get("offtake") or {}
        labels, values = block.get(f"months_{tag.lower()}") or [], block.get(f"monthly_{tag.lower()}") or []
    elif kind == "primary":
        block = ((dash.get("detail_meta") or {}).get("fyx_primary") or {}).get(tag) or {}
        labels, values = block.get("months_canon") or [], block.get("monthly_canon") or []
    elif kind == "rbc":
        # The displayed Brand Counter breakout is reliance_bc. The older
        # reliance_brand_counters audit block is empty ("not available") and is not a baseline.
        block = dash.get("reliance_bc") or {}
        labels, values = block.get("months") or [], block.get("monthly") or []
    else:
        raise ValueError(kind)
    if len(labels) != len(values):
        raise ValueError(f"dashboard {kind} {tag}: month and value lengths differ")
    return {lab: val for lab, val in zip(labels, values) if val is not None}


def _sum_metric(metric, period, months, files, source_of, baseline_of, unit="INR_lakh", note=""):
    """Compare source with dashboard month by month; only months that have a source count."""
    covered, per_month = [], {}
    for ym in months:
        paths = files.get(ym, [])
        if len(paths) > 1:
            return _row(metric, period, unit, "DUPLICATE_SOURCE",
                        f"{len(paths)} source files for {label(*ym)}; not summed",
                        source_files=[p.name for p in paths])
        if paths:
            covered.append(ym)
            per_month[ym] = source_of(paths[0])
    if not covered:
        return _row(metric, period, unit, "SOURCE_UNAVAILABLE",
                    "No source file for any month in this period; shown blank, not zero",
                    coverage=f"0/{len(months)} months")
    source = sum((per_month[ym] for ym in covered), Decimal(0))
    coverage = f"{len(covered)}/{len(months)} months ({label(*covered[0])}..{label(*covered[-1])})"
    row = _row(metric, period, unit, "", note, source_amount=float(round(source, 6)),
               model_inr=float(round(source * LAKH, 2)), coverage=coverage,
               covered_months=[label(*ym) for ym in covered],
               source_files=[files[ym][0].name for ym in covered])
    values = [baseline_of(ym) for ym in covered]
    if any(v is None for v in values):
        row["status"] = "NO_DASHBOARD_BASELINE" if all(v is None for v in values) else "NOT_COMPARABLE"
        missing = [label(*ym) for ym, v in zip(covered, values) if v is None]
        row["note"] = (note + " " if note else "") + f"Dashboard has no value for {', '.join(missing)}."
        return row
    expected = sum((Decimal(str(v)) for v in values), Decimal(0))
    mismatch = any(abs(per_month[ym] - Decimal(str(v))) > TOLERANCE_LAKH for ym, v in zip(covered, values))
    row["expected_report_amount"] = float(expected)
    row["variance"] = float(round(source - expected, 6))
    row["status"] = "MISMATCH" if mismatch else "MATCH"
    return row


def reconcile_context(repo_root: Path, period: str, filters: dict[str, list[str]] | None = None) -> list[dict]:
    repo_root = Path(repo_root).resolve()
    period, months = parse_period(period)
    is_fy = period.startswith("FY")
    metrics = [M_OFFTAKE, M_RBC, M_PRIMARY] + ([M_YOY, M_NPI] if is_fy else [])
    active = {key: values for key, values in (filters or {}).items() if values}
    if active:
        note = (f"Filter(s) {sorted(active)} are not reconciled at source level; "
                "no filtered result is implied")
        return [_row(m, period, "pct" if m in (M_YOY, M_NPI) else "INR_lakh", "UNSUPPORTED_FILTER", note)
                for m in metrics]

    dash = load_html(repo_root / "dashboard/data.js")
    raw = repo_root / "PowerBI/RawDataFolders"
    offtake_files = _files_by_month(raw / "Offtake_Monthly", OFFTAKE_FILE)
    primary_files = _files_by_month(raw / "Primary_Article_Monthly", PRIMARY_FILE)
    cache: dict[Path, dict] = {}

    def offtake_audit(path: Path) -> dict:
        if path not in cache:
            cache[path] = audit_csv(path, "NSV", None, exclude_reliance_bc=True)
        return cache[path]

    def baseline_for(kind):
        tables: dict[str, dict] = {}

        def lookup(ym):
            tag = fy_tag(*ym)
            if tag not in tables:
                tables[tag] = _baseline(dash, kind, tag if kind != "rbc" else "")
            return tables[tag].get(label(*ym))
        return lookup

    rows = [
        _sum_metric(M_OFFTAKE, period, months, offtake_files,
                    lambda p: Decimal(offtake_audit(p)["governed_raw_sum"]), baseline_for("offtake"),
                    note="Source NSV is lakh; converted to rupees once in the model."),
        _sum_metric(M_RBC, period, months, offtake_files,
                    lambda p: Decimal(offtake_audit(p)["rbc_excluded_raw_sum"]), baseline_for("rbc"),
                    note="Offtake only; excluded from MT offtake, never from Primary."),
        _sum_metric(M_PRIMARY, period, months, primary_files,
                    lambda p: Decimal(audit_csv(p, "Inv. Net value(LOC)")["raw_sum"]) / LAKH,
                    baseline_for("primary"), note="Source NSV is rupees; shown in lakh."),
    ]
    key_columns = _offtake_key_columns(repo_root)
    if rows[0]["covered_months"] and rows[0]["status"] != "DUPLICATE_SOURCE":
        rows[0]["duplicate_key_rows"] = sum(
            _duplicate_key_rows(offtake_files[ym][0], key_columns)
            for ym in months if len(offtake_files.get(ym, [])) == 1)
        if rows[0]["duplicate_key_rows"]:
            rows[0]["note"] += f" {rows[0]['duplicate_key_rows']} duplicate-key row(s) kept as source rows."
    if is_fy:
        rows.append(_yoy_row(period, months, offtake_files, dash))
        rows.append(_npi_row(period, dash))
    return rows


def _yoy_row(period, months, offtake_files, dash) -> dict:
    tag = period
    prior_tag = f"FY{(int(tag[2:]) - 1) % 100:02d}"
    covered = [ym for ym in months if len(offtake_files.get(ym, [])) == 1]
    if not covered:
        return _row(M_YOY, period, "pct", "SOURCE_UNAVAILABLE", "No offtake source month in this FY; shown blank.")
    current = _baseline(dash, "offtake", tag)
    prior = _baseline(dash, "offtake", prior_tag)
    cur_months = [ym[1] for ym in covered]
    prior_months = []
    for lab in prior:
        name = lab.split("-")[0]
        prior_months.append(MON.index(name) + 1 if name in MON else None)
    if None in prior_months or sorted(cur_months) != sorted(prior_months):
        return _row(M_YOY, period, "pct", "SUPPRESSED_PARTIAL_PERIOD",
                    f"{tag} has {len(covered)} covered month(s) but {prior_tag} has {len(prior)}; "
                    "growth across unequal periods is not shown.",
                    coverage=f"{len(covered)} vs {len(prior)} months")
    cur_values = [current.get(label(*ym)) for ym in covered]
    if any(v is None for v in cur_values) or not prior:
        return _row(M_YOY, period, "pct", "NOT_COMPARABLE", "Dashboard is missing a month needed for the comparison.")
    cur_sum, prior_sum = Decimal(str(sum(cur_values))), Decimal(str(sum(prior.values())))
    if prior_sum == 0:
        return _row(M_YOY, period, "pct", "NOT_COMPARABLE", "Prior-year base is zero.")
    return _row(M_YOY, period, "pct", "COMPARABLE", f"{tag} vs {prior_tag} over the same {len(covered)} month(s).",
                expected_report_amount=float((cur_sum - prior_sum) / prior_sum * 100),
                coverage=f"{len(covered)} vs {len(prior)} months")


def _npi_row(period, dash) -> dict:
    entry = ((dash.get("npd") or {}).get("metrics_by_fy") or {}).get(period)
    if not entry:
        return _row(M_NPI, period, "pct", "NO_DASHBOARD_BASELINE", f"The dashboard has no NPI figures for {period}.")
    value = entry.get("yoy_npi_nsv_growth_pct")
    observed = entry.get("observed_only_launch_count") or 0
    if entry.get("yoy_comparison_valid") and not observed:
        return _row(M_NPI, period, "pct", "COMPARABLE", "Confirmed cohorts on both sides; no NPI fact exists in the model.",
                    expected_report_amount=value)
    caveat = entry.get("yoy_caveat") or f"{observed} launch(es) are observed-only"
    return _row(M_NPI, period, "pct", "PROVISIONAL_OBSERVED_ONLY",
                f"Provisional observed-only comparison - not confirmed NPI growth. {caveat} "
                "NPI cohorts are computed in the dashboard pipeline; the model has no NPI fact.",
                expected_report_amount=value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--period", required=True, help="YYYY-MM or FYnn")
    parser.add_argument("--filter", action="append", default=[], metavar="KEY=VALUE",
                        help="Any filter marks the rows UNSUPPORTED_FILTER; none is reconciled at source level")
    args = parser.parse_args(argv)
    filters: dict[str, list[str]] = {}
    for item in args.filter:
        key, _, value = item.partition("=")
        filters.setdefault(key, []).append(value)
    rows = reconcile_context(args.repo_root, args.period, filters)
    print(json.dumps(rows, indent=2))
    return 2 if any(r["status"] in ("MISMATCH", "DUPLICATE_SOURCE") for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
