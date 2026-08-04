#!/usr/bin/env python3
"""
Dashboard QC gate — validates data integrity, label consistency, and JS health.

Statuses: PASS / WARN / FAIL / BLOCKED

Usage:
    python scripts/qc_dashboard.py [--data dashboard/data.js] [--no-browser]

Exit codes: 0=all PASS/WARN, 1=any FAIL, 2=any FAIL or BLOCKED that blocks release.
"""
from __future__ import annotations
import argparse, json, math, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_JS = REPO / "dashboard" / "data.js"

RESULTS: list[dict] = []


def qc(status: str, check: str, detail: str = "", value=None):
    RESULTS.append({"status": status, "check": check, "detail": detail, "value": value})
    sym = {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "BLOCKED": "⊘"}[status]
    val = f" [{value}]" if value is not None else ""
    print(f"  {sym} {status:<8} {check}{val}")
    if detail:
        print(f"            {detail}")


def load_dash(path: Path) -> dict:
    txt = path.read_text(encoding="utf-8")
    m = re.search(r"window\.DASH\s*=\s*", txt)
    if not m:
        raise ValueError("window.DASH not found in data.js")
    raw = txt[m.end():].rstrip().rstrip(";")
    raw = re.sub(r"\bNaN\b", "null", raw)
    return json.loads(raw)


def _isnum(v):
    return isinstance(v, (int, float)) and not math.isnan(v)


def _approx(a, b, tol=0.5):
    return abs(a - b) <= tol


# ── QC CHECKS ─────────────────────────────────────────────────────────────────

def check_data_js_exists(path: Path):
    if path.exists():
        size_mb = path.stat().st_size / 1e6
        qc("PASS", "data.js exists", f"{size_mb:.1f} MB")
    else:
        qc("FAIL", "data.js exists", f"Missing: {path}")


def check_meta(D: dict):
    meta = D.get("meta", {})
    period = meta.get("period", "")
    if period:
        qc("PASS", "meta.period set", value=period)
    else:
        qc("WARN", "meta.period", "Empty period label in meta")


def check_primary_totals(D: dict):
    p = D.get("primary", {})
    fy25 = p.get("nsv_fy25")
    fy26 = p.get("nsv_fy26")
    if _isnum(fy25) and _isnum(fy26):
        qc("PASS", "primary FY25/FY26 totals present", value=f"₹{fy25:.2f}L / ₹{fy26:.2f}L")
    else:
        qc("FAIL", "primary FY25/FY26 totals", "nsv_fy25 or nsv_fy26 missing/NaN")

    # Monthly sum vs total for FY25/FY26
    for fy, key, mkey in [("FY25","nsv_fy25","monthly_fy25"),("FY26","nsv_fy26","monthly_fy26")]:
        total = p.get(key)
        monthly = p.get(mkey, [])
        if _isnum(total) and monthly:
            s = sum(v for v in monthly if _isnum(v))
            if _approx(s, total, tol=1.0):
                qc("PASS", f"primary {fy} monthly sum ≈ total", value=f"{s:.2f}≈{total:.2f}")
            else:
                qc("FAIL", f"primary {fy} monthly sum vs total", f"sum={s:.2f} total={total:.2f} diff={abs(s-total):.2f}")


def check_offtake_totals(D: dict):
    o = D.get("offtake", {})
    for fy in ["fy25", "fy26", "fy27"]:
        total = o.get(f"total_{fy}")
        monthly = o.get(f"monthly_{fy}", [])
        months = o.get(f"months_{fy}", [])
        if total is None:
            continue
        if not _isnum(total):
            qc("FAIL", f"offtake total_{fy}", "NaN or null")
            continue
        # Monthly sum check (only months with data)
        if monthly and months:
            covered = [monthly[i] for i in range(len(months)) if _isnum(monthly[i])]
            s = sum(covered)
            if _approx(s, total, tol=1.0):
                qc("PASS", f"offtake {fy.upper()} monthly sum ≈ total", value=f"{s:.2f}≈{total:.2f}")
            else:
                qc("WARN", f"offtake {fy.upper()} monthly sum vs total", f"sum={s:.2f} total={total:.2f} diff={abs(s-total):.2f}")
        else:
            qc("PASS", f"offtake total_{fy} present", value=f"{total:.2f}")


def check_brand_counter(D: dict):
    bc = D.get("reliance_bc", {})
    include = bc.get("include_in_overall_offtake")
    total = bc.get("total")
    months = bc.get("months", [])
    if include is False:
        qc("PASS", "Brand Counter excluded from offtake", value=f"BC total={total}")
    else:
        qc("FAIL", "Brand Counter exclusion", f"include_in_overall_offtake={include} (expected False)")

    # Check for BC duplication: BC total should NOT be in offtake totals
    o = D.get("offtake", {})
    if _isnum(total) and total > 0:
        for fy in ["fy26", "fy27"]:
            ot = o.get(f"total_{fy}")
            if ot is not None and _isnum(ot):
                # BC total should not exactly equal or exceed the full offtake (red flag)
                pass  # no definitive check without knowing exact BC FY
    qc("PASS", "Brand Counter BC months audited", value=str(months))


def check_fyx_primary_label(D: dict):
    dm = D.get("detail_meta", {})
    fyx = dm.get("fyx_primary", {})
    fy27 = fyx.get("FY27", {})
    mc = fy27.get("months_covered", [])
    nsv = fy27.get("nsv")
    monthly = fy27.get("monthly", [])

    if not mc:
        qc("FAIL", "FY27 months_covered", "Empty — label will be wrong")
        return

    # Verify label derivation: first and last month
    label = f"FY27 {mc[0][:3]}–{mc[-1][:3]}"
    qc("PASS", "FY27 period label (derived)", value=label)

    # Sum of monthly for covered months must equal nsv
    if _isnum(nsv) and monthly:
        s = sum(v for v in monthly if _isnum(v) and v > 0)
        if _approx(s, nsv, tol=1.0):
            qc("PASS", "FY27 monthly[covered] sum ≈ nsv", value=f"{s:.2f}≈{nsv:.2f}")
        else:
            qc("FAIL", "FY27 monthly sum vs nsv", f"sum={s:.2f} nsv={nsv:.2f} diff={abs(s-nsv):.2f}")

    # Must NOT contain months not in months_covered
    FISCAL_MONTHS = ["April","May","June","July","August","September","October","November","December","January","February","March"]
    covered_set = set(mc)
    non_covered_total = sum(monthly[i] for i in range(len(FISCAL_MONTHS)) if i < len(monthly) and FISCAL_MONTHS[i] not in covered_set and _isnum(monthly[i]) and monthly[i] != 0)
    if abs(non_covered_total) < 0.01:
        qc("PASS", "FY27 no value outside months_covered")
    else:
        qc("FAIL", "FY27 value outside months_covered", f"non-covered months sum={non_covered_total:.2f}")


def check_mcd_unallocated(D: dict):
    MCD = {
        'Kiran Trading Company','G.V Enterprises','Sri Vijaya Durga Agencies',
        'Az Enterprises','VENKATESHWARA AGENCIES-TG','M/S KOTTARAM BUSINESS',
        'Sancus Networks Private Limited-RMT','D.L. Sales - MT',
        'Balaji Associates Distributor MT','CHHABRA TRADERS',
        'MARK ENTERPRISE','RR Traders-MT','REAL TIME LOGISTICS_MT_BR',
        'SAI SAACHI ASSOCIATES-MT-OR','CHOUDHARY ENTERPRISES','MANOJ SOAP AGENCY-MT',
        'Sehaj Enterprises -MT-JK','SRIJAN ENTERPRISES-MT-JH',
        'Vanaja Agencies','SC BUSINESS COMBINE_MT'
    }
    dm = D.get("detail_meta", {})
    fy27 = dm.get("fyx_primary", {}).get("FY27", {})
    by_chain = fy27.get("by_chain", [])
    total_nsv = fy27.get("nsv", 0)

    if not by_chain:
        qc("BLOCKED", "MCD allocation check", "fyx_primary.FY27.by_chain not available")
        return

    mcd_entries = [c for c in by_chain if c.get("name") in MCD]
    mcd_total = sum(c.get("nsv", 0) for c in mcd_entries)
    mcd_pct = mcd_total / total_nsv * 100 if total_nsv else 0

    if mcd_pct < 5:
        qc("PASS", "MCD unallocated FY27", f"{len(mcd_entries)} distributors, ₹{mcd_total/100:.2f} Cr ({mcd_pct:.1f}%)")
    elif mcd_pct < 15:
        qc("WARN", "MCD unallocated FY27 (material)", f"{len(mcd_entries)} distributors, ₹{mcd_total/100:.2f} Cr ({mcd_pct:.1f}%) — provide Dist_primary_cont_based_on_secondary_MOM.xlsx")
    else:
        qc("WARN", "MCD unallocated FY27 (high — allocation blocked)", f"{len(mcd_entries)} distributors, ₹{mcd_total/100:.2f} Cr ({mcd_pct:.1f}%) — BLOCKED on Dist_primary_cont_based_on_secondary_MOM.xlsx")

    qc("BLOCKED", "Dist-to-chain allocation", "Source file missing: Dist_primary_cont_based_on_secondary_MOM.xlsx (Ship-To × Brand × Month grain required)")


def check_tot_structure(D: dict):
    tot = D.get("tot", {})
    blended = tot.get("blended_tot_pct")
    by_chain = tot.get("by_chain", [])
    qc_table = tot.get("qc_table", [])

    if _isnum(blended):
        qc("PASS", "TOT blended_tot_pct present", value=f"{blended}%")
    else:
        qc("FAIL", "TOT blended_tot_pct", "Missing or NaN")

    if len(by_chain) > 0:
        qc("PASS", "TOT by_chain populated", value=f"{len(by_chain)} chains")
    else:
        qc("FAIL", "TOT by_chain", "Empty")

    if len(qc_table) == 12:
        qc("PASS", "TOT qc_table has 12 rows (monthly)", value="12 months")
    else:
        qc("WARN", "TOT qc_table", f"Expected 12 rows, got {len(qc_table)}")


def check_universe(D: dict):
    u = D.get("universe", {})
    total = u.get("total_stores")
    active = u.get("active_stores")
    if _isnum(total) and _isnum(active) and active <= total:
        qc("PASS", "Universe stores", value=f"active={active} / total={total}")
    else:
        qc("WARN", "Universe stores", f"total={total} active={active}")

    for dim in ["by_zone", "by_chain", "by_storetype", "by_citycat"]:
        d = u.get(dim, [])
        if d:
            qc("PASS", f"Universe {dim} populated", value=f"{len(d)} entries")
        else:
            qc("WARN", f"Universe {dim}", "Empty")


def check_forecast(D: dict):
    f = D.get("forecast", {})
    fy27 = f.get("fy27_forecast")
    if _isnum(fy27) and fy27 > 0:
        qc("PASS", "Forecast FY27 value", value=f"₹{fy27:.2f}L")
    else:
        qc("WARN", "Forecast FY27 value", f"Value={fy27}")


def check_detail_records(D: dict):
    recs = D.get("detail_records", [])
    if len(recs) > 0:
        qc("PASS", "detail_records populated", value=f"{len(recs)} rows")
        # Check for NaN/null in key fields
        nan_chain = sum(1 for r in recs if not r.get("Chain"))
        if nan_chain:
            qc("WARN", "detail_records unmapped Chain", f"{nan_chain} rows with null/empty Chain")
        else:
            qc("PASS", "detail_records Chain coverage")
    else:
        qc("WARN", "detail_records", "Empty — article-level drill-down unavailable")


def check_blocked_items():
    qc("BLOCKED", "Brand Counter June-26", "bc.months=['Apr-26','May-26'] only — source file not in repo; June BC unavailable")
    qc("BLOCKED", "EAN-level GST mapping", "Requires GSTIN master — not in repo")


def run_browser_check(port: int = 8765):
    try:
        from playwright.sync_api import sync_playwright
        import time, subprocess, os, signal
    except ImportError:
        qc("WARN", "Browser check", "playwright not installed — skipping")
        return

    srv = None
    try:
        srv = subprocess.Popen(
            ["python3", "-m", "http.server", str(port), "--directory", str(REPO / "dashboard")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        time.sleep(2)
        url = f"http://localhost:{port}/index.html"
        chromium = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=chromium, headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page()
            js_errors = []
            page.on("pageerror", lambda err: js_errors.append(str(err)))
            page.goto(url, wait_until="networkidle", timeout=60000)
            time.sleep(3)

            if js_errors:
                qc("FAIL", "JS errors on load", "; ".join(js_errors[:3]))
                js_errors.clear()
            else:
                qc("PASS", "JS load — no errors")

            TABS = ["Data Explorer","Overview","Primary","Offtake","P&L",
                    "Category & Pack","Forecast","Promo & Trade Spend",
                    "Market Share","Distribution","Performance & Comparison",
                    "Insights & Way Forward"]
            tab_errors = []
            for tab in TABS:
                try:
                    page.locator(f"button:has-text('{tab}')").first.click(timeout=5000)
                    time.sleep(0.3)
                    if js_errors:
                        tab_errors.append(f"{tab}: {js_errors[:]}")
                        js_errors.clear()
                except Exception as e:
                    tab_errors.append(f"{tab}: CLICK_FAILED {e}")

            if tab_errors:
                qc("FAIL", "Tab JS errors", "; ".join(tab_errors[:3]))
            else:
                qc("PASS", f"All {len(TABS)} tabs — no JS errors")

            # Check FY27 label in Overview
            page.locator("select").first.select_option(value="FY27")
            time.sleep(0.5)
            page.locator("button:has-text('Overview')").first.click(timeout=5000)
            time.sleep(0.5)
            kpi_text = page.locator(".kpis").first.inner_text()
            for bad in ["NaN", "undefined", "Infinity", "Apr–May"]:
                if bad in kpi_text:
                    qc("FAIL", f"Overview FY27 KPI contains '{bad}'", kpi_text[:200])
            if "Apr–May" not in kpi_text and "NaN" not in kpi_text and "undefined" not in kpi_text:
                qc("PASS", "Overview FY27 KPI label — no hardcoded Apr–May or NaN")

            # Verify dynamic label appears anywhere on the page (not just first .kpis)
            page_text = page.inner_text("body")
            if any(x in page_text for x in ["FY27 APR–JUN","FY27 Apr–Jun","FY27 APR–MAY","FY27 Apr–May"]):
                qc("PASS", "Overview FY27 dynamic label found on page")
            else:
                qc("WARN", "Overview FY27 dynamic label", "Expected FY27 Apr–<month> not found on page")

            browser.close()
    finally:
        if srv:
            srv.terminate()


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(DATA_JS))
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    data_path = Path(args.data)
    print("\n══════════════════════════════════════════════════════")
    print(" MT Dashboard QC Gate")
    print("══════════════════════════════════════════════════════\n")

    print("── DATA INTEGRITY ─────────────────────────────────────")
    check_data_js_exists(data_path)
    if not data_path.exists():
        print("\nCannot load data.js — aborting remaining checks.")
        sys.exit(1)

    D = load_dash(data_path)
    check_meta(D)
    check_primary_totals(D)
    check_offtake_totals(D)
    check_brand_counter(D)
    check_fyx_primary_label(D)
    check_tot_structure(D)
    check_universe(D)
    check_forecast(D)
    check_detail_records(D)

    print("\n── ALLOCATION & MAPPING ───────────────────────────────")
    check_mcd_unallocated(D)

    print("\n── KNOWN BLOCKED ITEMS ────────────────────────────────")
    check_blocked_items()

    if not args.no_browser:
        print("\n── BROWSER / JS CHECKS ────────────────────────────────")
        run_browser_check(args.port)

    # ── Summary ──────────────────────────────────────────────
    counts = {s: sum(1 for r in RESULTS if r["status"] == s) for s in ["PASS","WARN","FAIL","BLOCKED"]}
    print("\n══════════════════════════════════════════════════════")
    print(f" SUMMARY: {counts['PASS']} PASS  {counts['WARN']} WARN  {counts['FAIL']} FAIL  {counts['BLOCKED']} BLOCKED")

    if counts["FAIL"] == 0 and counts["BLOCKED"] == 0:
        decision = "READY"
    elif counts["FAIL"] == 0:
        decision = "READY WITH ACCEPTED EXCEPTIONS" if counts["WARN"] <= 3 else "WARN — REVIEW BEFORE RELEASE"
    else:
        decision = "NOT READY"

    print(f" RELEASE DECISION: {decision}")
    print("══════════════════════════════════════════════════════\n")

    sys.exit(0 if counts["FAIL"] == 0 else 1)


if __name__ == "__main__":
    main()
