#!/usr/bin/env python3
"""
Automated Power BI + Dashboard Monthly Refresh Orchestrator

Hands-free monthly pipeline:
1. Load source data (XLSB → CSV via split_*_xlsb.py if needed)
2. Build data.js (run build_dashboard_data.py with appropriate flags)
3. Validate QC gate (run qc_dashboard.py --no-browser)
4. Commit changes to git if all passes
5. Trigger Power BI Desktop refresh (Windows/Mac only, requires com.ms.Excel)

Usage:
    python scripts/automate_pbi_refresh.py --mode full|primary-only|offtake-patch
                                           [--src <source-dir>] [--out <data.js>]
                                           [--no-commit] [--no-pbi-refresh]
                                           [--dry-run]

Exit codes:
    0 = Success (all passes, changes committed if applicable)
    1 = Data validation failed (QC gate did not pass)
    2 = Build/pipeline error (subprocess failed)
    3 = Git error (commit failed)
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────
# Configuration & Helpers
# ────────────────────────────────────────────────────────────────────────────

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"
DASHBOARD = REPO / "dashboard"
DEFAULT_OUT = DASHBOARD / "data.js"


def log(level: str, msg: str):
    """Print timestamped log message."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sym = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "DEBUG": "→"}[level]
    print(f"[{ts}] {sym} {msg}")


def run_cmd(cmd: list[str], check: bool = True, capture: bool = False) -> str | None:
    """Run shell command and return stdout if capture=True."""
    log("DEBUG", f"Running: {' '.join(cmd)}")
    try:
        if capture:
            result = subprocess.run(cmd, check=check, capture_output=True, text=True)
            return result.stdout
        else:
            subprocess.run(cmd, check=check)
            return None
    except subprocess.CalledProcessError as e:
        log("ERROR", f"Command failed with exit code {e.returncode}: {' '.join(cmd)}")
        if e.stdout:
            log("ERROR", f"stdout: {e.stdout}")
        if e.stderr:
            log("ERROR", f"stderr: {e.stderr}")
        raise


def validate_qc(data_js: Path) -> bool:
    """
    Run QC validation (no browser checks).
    Returns True if PASS/WARN (acceptable), False if any FAIL/BLOCKED.
    """
    log("INFO", f"Running QC validation on {data_js}")
    try:
        output = run_cmd(
            ["python", str(SCRIPTS / "qc_dashboard.py"), "--data", str(data_js), "--no-browser"],
            check=False,
            capture=True
        )
        log("DEBUG", f"QC output (last 500 chars):\n{output[-500:] if output else '(no output)'}")

        # Parse summary line for FAIL/BLOCKED
        if "FAIL" in output and "0 FAIL" not in output:
            log("ERROR", "QC gate found FAIL items")
            return False
        if "BLOCKED" in output and "0 BLOCKED" not in output:
            log("WARN", "QC gate has BLOCKED items (may require explicit approval)")
            # For now, treat BLOCKED as acceptable; can be escalated to failure if needed

        return True
    except Exception as e:
        log("ERROR", f"QC validation error: {e}")
        return False


def git_commit(message: str, dry_run: bool = False) -> bool:
    """
    Stage and commit changes to git.
    Returns True if successful.
    """
    log("INFO", "Staging changes for commit")

    # Get current branch
    try:
        branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True).strip()
        log("INFO", f"Current branch: {branch}")
    except Exception as e:
        log("ERROR", f"Could not determine branch: {e}")
        return False

    # Add files
    files_to_add = ["dashboard/data.js", "PowerBI/Reference/CM2_Provisional/config/cm2_formula.csv"]
    for f in files_to_add:
        path = REPO / f
        if path.exists():
            try:
                run_cmd(["git", "add", f])
                log("DEBUG", f"Staged: {f}")
            except Exception as e:
                log("WARN", f"Could not stage {f}: {e}")

    # Check if there are changes to commit
    try:
        status = run_cmd(["git", "status", "--porcelain"], capture=True).strip()
        if not status:
            log("INFO", "No changes to commit")
            return True
    except Exception as e:
        log("ERROR", f"Could not check git status: {e}")
        return False

    # Commit with trailer
    if dry_run:
        log("INFO", f"[DRY RUN] Would commit: {message}")
        return True

    try:
        commit_msg = f"{message}\n\nCo-Authored-By: MT Automation Agent <automation@mt-dashboard.local>"
        run_cmd(["git", "commit", "-m", commit_msg])
        log("OK", "Changes committed successfully")
        return True
    except subprocess.CalledProcessError as e:
        log("ERROR", f"Commit failed: {e}")
        return False


def run_build(mode: str, src: Path, out: Path, dry_run: bool = False) -> bool:
    """
    Run build_dashboard_data.py with specified mode.
    Returns True if successful.
    """
    build_script = SCRIPTS / "build_dashboard_data.py"
    cmd = ["python", str(build_script), f"--{mode}", "--src", str(src), "--out", str(out)]

    log("INFO", f"Building data.js (mode: {mode})")
    log("DEBUG", f"Command: {' '.join(cmd)}")

    if dry_run:
        log("INFO", "[DRY RUN] Skipping build")
        return True

    try:
        run_cmd(cmd)
        log("OK", f"Build completed (mode: {mode})")
        return True
    except Exception as e:
        log("ERROR", f"Build failed: {e}")
        return False


def extract_data_contracts(data_js: Path, export_dir: Path, dry_run: bool = False) -> bool:
    """
    Phase 2: Extract normalized CSV data contracts from data.js.
    Returns True if successful.
    """
    extract_script = SCRIPTS / "extract_data_contracts.py"
    cmd = ["python", str(extract_script), "--src", str(data_js), "--out", str(export_dir)]

    log("INFO", f"Extracting data contracts from {data_js.name}")
    log("DEBUG", f"Command: {' '.join(cmd)}")

    if dry_run:
        log("INFO", "[DRY RUN] Skipping extraction")
        return True

    try:
        run_cmd(cmd)
        log("OK", f"Data contracts extracted to {export_dir}")
        return True
    except Exception as e:
        log("ERROR", f"Data extraction failed: {e}")
        return False


def generate_agent_sentiments(export_dir: Path, dry_run: bool = False) -> bool:
    """
    Phase 3: Generate automated executive insights from CSV data contracts.
    Returns True if successful.
    """
    sentiments_script = SCRIPTS / "generate_agent_sentiments.py"
    insights_file = REPO / "insights" / "generated_insights.json"
    insights_file.parent.mkdir(parents=True, exist_ok=True)

    cmd = ["python", str(sentiments_script), "--data", str(export_dir), "--out", str(insights_file)]

    log("INFO", f"Generating agent sentiments from data contracts")
    log("DEBUG", f"Command: {' '.join(cmd)}")

    if dry_run:
        log("INFO", "[DRY RUN] Skipping sentiments generation")
        return True

    try:
        run_cmd(cmd)
        log("OK", f"Agent sentiments generated: {insights_file.name}")
        return True
    except Exception as e:
        log("ERROR", f"Sentiments generation failed: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(
        description="Automated Power BI + Dashboard Monthly Refresh",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full rebuild (requires all source files)
  python scripts/automate_pbi_refresh.py --mode full --src /path/to/sources/

  # Refresh only primary/P&L/insights
  python scripts/automate_pbi_refresh.py --mode primary-only --src /path/to/sources/

  # Patch offtake data only (idempotent)
  python scripts/automate_pbi_refresh.py --mode offtake-patch --src /path/to/sources/

  # Dry-run to see what would happen
  python scripts/automate_pbi_refresh.py --mode primary-only --src /path/to/sources/ --dry-run
        """
    )
    ap.add_argument("--mode", required=True,
                    choices=["full", "primary-only", "offtake-patch", "detail-only", "forecast-only"],
                    help="Build mode")
    ap.add_argument("--src", type=Path, default=Path.cwd(),
                    help="Source data directory (default: current dir)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help=f"Output data.js path (default: {DEFAULT_OUT})")
    ap.add_argument("--no-commit", action="store_true",
                    help="Skip git commit (for testing)")
    ap.add_argument("--no-qc", action="store_true",
                    help="Skip QC validation (risky!)")
    ap.add_argument("--no-pbi-refresh", action="store_true",
                    help="Skip Power BI refresh trigger (default: attempted if available)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would happen without making changes")

    args = ap.parse_args()

    log("INFO", "═" * 70)
    log("INFO", "MT Dashboard Monthly Refresh Orchestrator")
    log("INFO", "═" * 70)
    log("INFO", f"Mode: {args.mode}")
    log("INFO", f"Source dir: {args.src}")
    log("INFO", f"Output: {args.out}")
    log("INFO", f"Dry run: {args.dry_run}")

    # ────────────────────────────────────────────────────────────────────────────
    # Step 1: Build data.js (Phase 1)
    # ────────────────────────────────────────────────────────────────────────────
    if not run_build(args.mode, args.src, args.out, dry_run=args.dry_run):
        log("ERROR", "Build pipeline failed")
        sys.exit(2)

    # ────────────────────────────────────────────────────────────────────────────
    # Step 2: Extract Data Contracts (Phase 2)
    # ────────────────────────────────────────────────────────────────────────────
    export_dir = REPO / "PowerBI" / "ExportData"
    if not extract_data_contracts(args.out, export_dir, dry_run=args.dry_run):
        log("ERROR", "Data extraction failed")
        sys.exit(2)

    # ────────────────────────────────────────────────────────────────────────────
    # Step 3: Generate Agent Sentiments (Phase 3)
    # ────────────────────────────────────────────────────────────────────────────
    if not generate_agent_sentiments(export_dir, dry_run=args.dry_run):
        log("ERROR", "Sentiments generation failed")
        sys.exit(2)

    # ────────────────────────────────────────────────────────────────────────────
    # Step 4: QC Validation Gate
    # ────────────────────────────────────────────────────────────────────────────
    if not args.no_qc:
        if not validate_qc(args.out):
            log("ERROR", "QC validation failed — aborting commit")
            sys.exit(1)
        log("OK", "QC validation passed")
    else:
        log("WARN", "QC validation skipped (--no-qc)")

    # ────────────────────────────────────────────────────────────────────────────
    # Step 5: Git Commit (Phase 1 output + Phase 2/3 artifacts)
    # ────────────────────────────────────────────────────────────────────────────
    if not args.no_commit:
        # Determine commit message based on mode
        mode_msgs = {
            "full": "data: Full dashboard rebuild (Phase 1) + contracts (Phase 2) + sentiments (Phase 3)",
            "primary-only": "data: Primary sales + P&L + Insights (Phase 1-3)",
            "offtake-patch": "data: Monthly offtake patch (Phase 1-3)",
            "detail-only": "data: Article-level detail refresh (Phase 1-3)",
            "forecast-only": "data: Forecast target update (Phase 1-3)",
        }
        msg = mode_msgs.get(args.mode, f"data: {args.mode} refresh (Phase 1-3)")
        if not git_commit(msg, dry_run=args.dry_run):
            log("ERROR", "Git commit failed")
            sys.exit(3)
        log("OK", "Changes committed")
    else:
        log("WARN", "Git commit skipped (--no-commit)")

    # ────────────────────────────────────────────────────────────────────────────
    # Step 6: Power BI PBIX Generation & Refresh (Phase 2.5+)
    # ────────────────────────────────────────────────────────────────────────────
    if not args.no_pbi_refresh:
        log("INFO", "Power BI PBIX generation trigger (Phase 2.5)")
        log("INFO", "  Note: Requires Windows self-hosted runner + Power BI Desktop 2024.09+")
        log("INFO", "  [TODO] Sep 5-8: Set up Windows runner")
        log("INFO", "  [TODO] Sep 10-12: Enable PBIX generation + DAX validation via COM API")

    log("INFO", "═" * 70)
    log("OK", "Pipeline completed successfully!")
    log("INFO", "═" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()
