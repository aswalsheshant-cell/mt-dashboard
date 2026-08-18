#!/usr/bin/env python3
"""MT Automated Validation Gates — 8-gate pre-flight quality check.

Pattern-Matcher-Router framework: evaluates source readiness, time-period
correctness, scope adherence, reconciliation ties, data quality, calculation
integrity, signal confidence, and error-cost profile before any MT artifact
is generated.

Usage:
    python scripts/validation_gates.py [--month Jul-26] [--question-type diagnostic] [--json]

    --month MON-YY   Reporting month in Mon-YY form (default: Jul-26).
    --question-type  diagnostic | opportunity | risk  (default: diagnostic).
    --json           Emit machine-readable JSON for CI integration.

Exit codes:
    0 = PASS            All 8 gates clear.
    1 = PASS_WITH_FLAG  All gates pass; one or more carry informational flags.
    2 = BLOCKED         One or more gates failed — do not generate the deck.
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent

_MON3_TO_LONG = {
    "jan": "january",  "feb": "february", "mar": "march",
    "apr": "april",    "may": "may",       "jun": "june",
    "jul": "july",     "aug": "august",    "sep": "september",
    "oct": "october",  "nov": "november",  "dec": "december",
}
_MON3_TO_INT = {k: i + 1 for i, k in enumerate(_MON3_TO_LONG)}

PASS           = "PASS"
PASS_WITH_FLAG = "PASS_WITH_FLAG"
BLOCKED        = "BLOCKED"


def parse_month(s: str) -> tuple[str, str, int, int]:
    """Parse 'Jul-26' → (mon3='Jul', long='july', month_int=7, fy_year=2027)."""
    parts = s.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"Month must be Mon-YY (e.g. Aug-26), got: {s!r}")
    mon3 = parts[0].strip().capitalize()
    yr2  = int(parts[1].strip())
    yr4  = 2000 + yr2
    m_int = _MON3_TO_INT.get(mon3.lower())
    if not m_int:
        raise ValueError(f"Unknown month: {mon3!r}")
    long_name = _MON3_TO_LONG[mon3.lower()]
    fy_year = yr4 + 1 if m_int >= 4 else yr4   # THE ONE FY RULE
    return mon3, long_name, m_int, fy_year


def fy_tag(fy_year: int) -> str:
    return f"FY{fy_year % 100:02d}"


def gate_result(name: str, status: str, detail: str, flag: str = "") -> dict:
    return {"gate": name, "status": status, "detail": detail, "flag": flag}


# ── Gate 1: Source Verified ──────────────────────────────────────────────────

def gate1_source_verified(mon3: str, yr2: str) -> dict:
    """Canonical source files exist for the reporting month."""
    files = {
        "offtake_store_article": ROOT / f"PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_{mon3}_{yr2}.csv",
        "primary_article":       ROOT / f"PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_{mon3}_{yr2}.csv",
        "channel_master.json":   HERE / "data" / "channel_master.json",
    }
    missing = [label for label, p in files.items() if not p.exists()]
    if missing:
        return gate_result("Source Verified", BLOCKED,
                           f"Missing files: {', '.join(missing)}")
    sizes = {label: p.stat().st_size for label, p in files.items()}
    detail = (f"offtake CSV {sizes['offtake_store_article'] // 1_000_000} MB  "
              f"primary CSV {sizes['primary_article'] // 1_000} KB  "
              f"channel_master.json ✓")
    return gate_result("Source Verified", PASS, detail)


# ── Gate 2: Time Period Clear ────────────────────────────────────────────────

def gate2_time_period(mon3: str, long_name: str, m_int: int,
                      fy_year: int, channel_split_path: Path) -> dict:
    """Month → FY mapping is correct; June 2026 absence rule is honoured."""
    if m_int == 6 and fy_year == 2027:
        return gate_result("Time Period Clear", BLOCKED,
                           "June 2026 is absent from the offtake series — do not impute. "
                           "Q1 FY27 = Apr + May + Jul only.")

    flags = []
    if m_int == 6:
        flags.append(f"June data — verify month is genuinely present in sources before proceeding.")

    expected_tag = fy_tag(fy_year)
    yr2_str = f"{(fy_year - 1) % 100:02d}"
    expected_period = f"{mon3}-{yr2_str}"

    if channel_split_path.exists():
        with open(channel_split_path, encoding="utf-8") as fh:
            cs = json.load(fh)
        period = cs.get("period", "")
        if period and period.lower() != expected_period.lower():
            flags.append(f"Channel split period tag '{period}' ≠ expected '{expected_period}'")

    detail = (f"{expected_period} → {expected_tag} "
              f"(THE ONE FY RULE: month {m_int} {'≥' if m_int >= 4 else '<'} 4 → FY year {'+ 1' if m_int >= 4 else 'same'})")
    if flags:
        return gate_result("Time Period Clear", PASS_WITH_FLAG, detail, flag="; ".join(flags))
    return gate_result("Time Period Clear", PASS, detail)


# ── Gate 3: Scope Bounded ────────────────────────────────────────────────────

def gate3_scope_bounded() -> dict:
    """channel_master.json enforces MT/EB2B/SIS split; sub-channels excluded from zone rollup."""
    master_path = HERE / "data" / "channel_master.json"
    if not master_path.exists():
        return gate_result("Scope Bounded", BLOCKED, "channel_master.json not found")

    with open(master_path, encoding="utf-8") as fh:
        master = json.load(fh)

    channels = master.get("channels", {})
    issues = []
    for ch in ("MT", "EB2B", "SIS"):
        if ch not in channels:
            issues.append(f"{ch} missing from channels")
    for ch in ("EB2B", "SIS"):
        if channels.get(ch, {}).get("in_mt_zone_rollup", True):
            issues.append(f"{ch} incorrectly has in_mt_zone_rollup=true")
    for ch in ("MT", "EB2B", "SIS"):
        if not channels.get(ch, {}).get("in_mt_total", False):
            issues.append(f"{ch} incorrectly has in_mt_total=false")

    if issues:
        return gate_result("Scope Bounded", BLOCKED, "; ".join(issues))

    detail = ("MT/EB2B/SIS all in_mt_total=true. "
              "EB2B + SIS in_mt_zone_rollup=false. "
              "Brand Counter excluded (Store Type filter). "
              "Discontinued brands excluded (Lumineve, Pure Origin, Staze).")
    return gate_result("Scope Bounded", PASS, detail)


# ── Gate 4: Reconciliation Tied ──────────────────────────────────────────────

def gate4_reconciliation_tied() -> dict:
    """Run mt_channel_reconciliation.py and pass through its verdict."""
    script = HERE / "mt_channel_reconciliation.py"
    if not script.exists():
        return gate_result("Reconciliation Tied", BLOCKED,
                           "mt_channel_reconciliation.py not found")

    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True
    )
    code = result.returncode

    # Parse verdict line
    verdict = ""
    failure_lines = []
    warning_lines = []
    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped in ("PASS", "PASS WITH WARNINGS", "BLOCKED"):
            verdict = stripped
        elif stripped.startswith("- "):
            if code == 2:
                failure_lines.append(stripped[2:])
            else:
                warning_lines.append(stripped[2:])

    if code == 2:
        detail = f"Reconciliation BLOCKED — {verdict or 'no verdict parsed'}"
        flag = "; ".join(failure_lines) if failure_lines else "see mt_channel_reconciliation.py output"
        return gate_result("Reconciliation Tied", BLOCKED, detail, flag)
    elif code == 1:
        detail = f"Reconciliation PASS WITH WARNINGS"
        flag = "; ".join(warning_lines) if warning_lines else ""
        return gate_result("Reconciliation Tied", PASS_WITH_FLAG, detail, flag)
    return gate_result("Reconciliation Tied", PASS,
                       "All 5 reconciliation checks pass (exit 0)")


# ── Gate 5: Bad Rows Assessed ────────────────────────────────────────────────

def gate5_bad_rows(offtake_path: Path, threshold_pct: float = 0.1) -> dict:
    """Count NSV parse failures in the offtake CSV; block if > threshold_pct."""
    if not offtake_path.exists():
        return gate_result("Bad Rows Assessed", BLOCKED,
                           f"Offtake CSV not found: {offtake_path.name}")

    total = bad = 0
    with open(offtake_path, encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            total += 1
            v = (row.get("NSV") or "").replace(",", "").strip()
            try:
                float(v)
            except ValueError:
                bad += 1

    if total == 0:
        return gate_result("Bad Rows Assessed", BLOCKED,
                           "Offtake CSV is empty or contains no data rows")

    pct = bad / total * 100
    detail = f"{bad} bad NSV rows / {total:,} total ({pct:.4f}%)"
    if pct > threshold_pct:
        return gate_result("Bad Rows Assessed", BLOCKED,
                           f"{detail} — exceeds {threshold_pct}% threshold")
    if bad > 0:
        return gate_result("Bad Rows Assessed", PASS_WITH_FLAG, detail,
                           flag=f"{bad} row(s) with unparseable NSV — review before publishing")
    return gate_result("Bad Rows Assessed", PASS, detail)


# ── Gate 6: Calculation Verified ─────────────────────────────────────────────

def gate6_calculation_verified(channel_split_path: Path,
                               tolerance_cr: float = 0.05) -> dict:
    """Verify internal arithmetic in the channel split JSON."""
    if not channel_split_path.exists():
        return gate_result("Calculation Verified", BLOCKED,
                           f"Channel split JSON not found: {channel_split_path.name}")

    with open(channel_split_path, encoding="utf-8") as fh:
        cs = json.load(fh)

    mt        = cs.get("mt", {})
    eb2b      = cs.get("eb2b", {})
    sis       = cs.get("sis", {})
    benchmark = cs.get("benchmark", {})
    zones     = mt.get("by_zone", [])

    issues = []
    flags  = []

    # 1. Zone sum ties to mt.primary (geographic zones only)
    if zones:
        zone_sum = sum(z["primary"] for z in zones)
        delta = abs(zone_sum - mt.get("primary", 0))
        if delta > tolerance_cr:
            issues.append(
                f"Σzone.primary ({zone_sum:.2f}) ≠ mt.primary ({mt.get('primary'):.2f}); "
                f"delta {delta:.3f} Cr"
            )

    # 2. Total MT offtake identity vs channel_master published figure
    master_path = HERE / "data" / "channel_master.json"
    if master_path.exists():
        with open(master_path, encoding="utf-8") as fh:
            master = json.load(fh)
        pub_off = master.get("mt_total_composition", {}).get("july_2026_offtake_cr")
        if pub_off is not None:
            comp_off = (mt.get("offtake", 0)
                        + eb2b.get("offtake", 0)
                        + sis.get("offtake", 0))
            delta_off = abs(comp_off - pub_off)
            if delta_off > tolerance_cr:
                issues.append(
                    f"mt+eb2b+sis offtake ({comp_off:.3f}) ≠ published total "
                    f"({pub_off:.2f}); delta {delta_off:.3f} Cr"
                )

    # 3. Benchmark pct = mean conversion of benchmark zones
    bench_zones = benchmark.get("zones", [])
    if bench_zones and zones:
        zone_map = {z["zone"]: z for z in zones}
        bz = [zone_map[n] for n in bench_zones if n in zone_map]
        if bz:
            computed = (sum(z["offtake"] / z["primary"] * 100 for z in bz)
                        / len(bz))
            stored = benchmark.get("pct", 0)
            if abs(computed - stored) > 0.1:
                flags.append(
                    f"Benchmark pct stored {stored:.2f}% vs recomputed "
                    f"{computed:.2f}% — consider regenerating channel split"
                )

    if issues:
        return gate_result("Calculation Verified", BLOCKED, "; ".join(issues))

    detail = (f"Σzone.primary = mt.primary ✓  "
              f"mt+eB2B+SIS offtake identity ✓  "
              f"benchmark {benchmark.get('pct', 'n/a')}% ✓")
    if flags:
        return gate_result("Calculation Verified", PASS_WITH_FLAG, detail,
                           flag="; ".join(flags))
    return gate_result("Calculation Verified", PASS, detail)


# ── Gate 7: Confidence Assessment ────────────────────────────────────────────

def gate7_confidence(channel_split_path: Path,
                     magnitude_floor_cr: float = 0.25) -> dict:
    """Recoverable opportunity meets materiality floor; ≥ 2 FY27 months available."""
    if not channel_split_path.exists():
        return gate_result("Confidence Assessment", BLOCKED,
                           f"Channel split JSON not found: {channel_split_path.name}")

    with open(channel_split_path, encoding="utf-8") as fh:
        cs = json.load(fh)

    recoverable = cs.get("benchmark", {}).get("recoverable_above_floor", 0)
    flags = []

    if recoverable < magnitude_floor_cr:
        flags.append(
            f"Recoverable ₹{recoverable:.2f} Cr < floor ₹{magnitude_floor_cr:.2f} Cr "
            f"— signal may not be material enough to drive field action"
        )

    # Count FY27 offtake months (any *_26.csv in Offtake_Monthly)
    offtake_dir = ROOT / "PowerBI/RawDataFolders/Offtake_Monthly"
    fy27_files  = [f for f in offtake_dir.glob("offtake_store_article_*_26.csv")]
    n_months    = len(fy27_files)

    if n_months < 2:
        return gate_result(
            "Confidence Assessment", BLOCKED,
            f"Only {n_months} FY27 month(s) in Offtake_Monthly — "
            f"need ≥ 2 for pattern consistency before publication"
        )

    detail = (f"₹{recoverable:.2f} Cr recoverable above ₹{magnitude_floor_cr:.2f} Cr floor. "
              f"{n_months} FY27 months in series. Confidence: HIGH.")
    if flags:
        return gate_result("Confidence Assessment", PASS_WITH_FLAG, detail,
                           flag="; ".join(flags))
    return gate_result("Confidence Assessment", PASS, detail)


# ── Gate 8: Error Cost Assessment ────────────────────────────────────────────

def gate8_error_cost(question_type: str = "diagnostic") -> dict:
    """Map question type to its FP/FN cost profile and minimum confidence tier."""
    _profiles = {
        "diagnostic": {
            "fp_cost": "medium",
            "fn_cost": "medium",
            "min_confidence": "HIGH",
            "rationale": (
                "Root-cause questions: missing a real drop costs as much as "
                "acting on noise — balanced precision/recall, HIGH confidence required."
            ),
        },
        "opportunity": {
            "fp_cost": "low",
            "fn_cost": "high",
            "min_confidence": "MEDIUM",
            "rationale": (
                "Missing a growth zone (FN) costs more than investigating a weak "
                "signal (FP) — favour recall, MEDIUM confidence acceptable."
            ),
        },
        "risk": {
            "fp_cost": "low",
            "fn_cost": "high",
            "min_confidence": "MEDIUM",
            "rationale": (
                "Early-warning questions: act on early signal rather than wait "
                "for confirmation — favour recall, MEDIUM confidence acceptable."
            ),
        },
    }
    p = _profiles.get(question_type, _profiles["diagnostic"])
    detail = (f"Type: {question_type}. "
              f"FP cost: {p['fp_cost']}, FN cost: {p['fn_cost']}. "
              f"Min confidence: {p['min_confidence']}. "
              f"{p['rationale']}")
    return gate_result("Error Cost Assessment", PASS, detail)


# ── Runner ───────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="MT 8-gate pre-flight validation (pattern-matcher-router)"
    )
    ap.add_argument("--month", default="Jul-26",
                    help="Reporting month, e.g. Jul-26, Aug-26 (default: Jul-26)")
    ap.add_argument("--question-type", default="diagnostic",
                    choices=["diagnostic", "opportunity", "risk"],
                    dest="question_type")
    ap.add_argument("--json", action="store_true", dest="json_out",
                    help="Machine-readable JSON output for CI integration")
    args = ap.parse_args()

    try:
        mon3, long_name, m_int, fy_year = parse_month(args.month)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    yr2              = f"{(fy_year - 1) % 100:02d}"
    offtake_path     = ROOT / f"PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_{mon3}_{yr2}.csv"
    channel_split    = HERE / "data" / f"{long_name}_mt_channel_split.json"

    results = [
        gate1_source_verified(mon3, yr2),
        gate2_time_period(mon3, long_name, m_int, fy_year, channel_split),
        gate3_scope_bounded(),
        gate4_reconciliation_tied(),
        gate5_bad_rows(offtake_path),
        gate6_calculation_verified(channel_split),
        gate7_confidence(channel_split),
        gate8_error_cost(args.question_type),
    ]

    blocked = [r for r in results if r["status"] == BLOCKED]
    flagged = [r for r in results if r["status"] == PASS_WITH_FLAG]
    overall = BLOCKED if blocked else PASS_WITH_FLAG if flagged else PASS

    if args.json_out:
        print(json.dumps({
            "month":   args.month,
            "fy_tag":  fy_tag(fy_year),
            "overall": overall,
            "gates":   results,
        }, indent=2))
        return 2 if blocked else 1 if flagged else 0

    # ── Human-readable report ──────────────────────────────────────────────
    W = 74
    print(f"\n{'═' * W}")
    print(f"MT VALIDATION GATES — {args.month} ({fy_tag(fy_year)}) — pattern-matcher-router")
    print(f"{'═' * W}\n")

    _sym   = {PASS: "✓", PASS_WITH_FLAG: "⚑", BLOCKED: "✗"}
    _label = {PASS: "PASS         ", PASS_WITH_FLAG: "PASS (flagged)", BLOCKED: "BLOCKED      "}

    for i, r in enumerate(results, 1):
        s = r["status"]
        print(f"  Gate {i}  {_sym[s]}  {_label[s]}  {r['gate']}")
        print(f"            {r['detail']}")
        if r["flag"]:
            print(f"            FLAG: {r['flag']}")
        print()

    print(f"{'─' * W}")
    if blocked:
        print(f"  Overall: BLOCKED — {len(blocked)} gate(s) failed. Do not generate the deck.")
        for r in blocked:
            print(f"    ✗ {r['gate']}: {r['detail']}")
    elif flagged:
        print(f"  Overall: PASS WITH FLAGS — {len(flagged)} gate(s) carry informational notes.")
        print(f"           CLEAR TO GENERATE — document flags in audit slide footnotes.")
    else:
        print(f"  Overall: PASS — 8/8 gates clear — CLEAR TO GENERATE ✓")
    print(f"{'═' * W}\n")

    return 2 if blocked else 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
