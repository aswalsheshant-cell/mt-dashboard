"""
Playwright-based UI regression suite for dashboard/index.html.

Run locally:
  pytest tests/test_dashboard_ui.py -v

CI: launched by .github/workflows/ui-smoke.yml
Chromium is pre-installed at /opt/pw-browsers/chromium; do NOT call playwright install.
"""

import asyncio
import pathlib
import pytest
from playwright.async_api import async_playwright

INDEX = pathlib.Path(__file__).parent.parent / "dashboard" / "index.html"
CHROMIUM = "/opt/pw-browsers/chromium"
FILE_URL = INDEX.as_uri()

TABS_KEYWORDS = {
    "overview": ["Command Center", "Key Account MoM", "Sell-Out Velocity"],
    "forecast": ["Q3", "Forecast Horizon", "Scenario", "Forecast Accuracy", "MAPE"],
    "distribution": ["SPD", "Chain Distribution Coverage", "Numeric Distribution"],
}

ALL_TAB_IDS = [
    "explorer", "overview", "monthly-briefing", "primary", "offtake", "reliance-bc",
    "pnl", "category", "forecast", "promo", "offtake-impact",
    "share", "distribution", "comparison", "channel-economics", "execution-excellence",
    "demand-supply", "market-research", "retail-execution", "analytics", "stores",
    "inventory", "forecast-tracking", "cm2", "insights",
]


# ---------------------------------------------------------------------------
# Shared session-scoped state — built once, reused by all tests
# ---------------------------------------------------------------------------

_SESSION: dict = {}


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


async def _build_session():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            executable_path=CHROMIUM, args=["--no-sandbox"]
        )
        page = await browser.new_page()
        js_errors: list[str] = []
        page.on("pageerror", lambda e: js_errors.append(str(e)))
        await page.goto(FILE_URL, wait_until="networkidle", timeout=30_000)
        await page.wait_for_timeout(2_000)

        tab_texts: dict[str, str] = {}
        for tab_id in ALL_TAB_IDS:
            btn = await page.query_selector(f'nav button[data-t="{tab_id}"]')
            if btn:
                await btn.click()
                await page.wait_for_timeout(1_200)
                tab_texts[tab_id] = await page.evaluate(
                    f'document.getElementById("tab-{tab_id}").innerText'
                )

        dash_checks = await page.evaluate("""
            (() => {
                const D = window.DASH || {};
                const sc = D.mom_chain_scorecard || null;
                const diag = (D.forecast && D.forecast.diagnostics) || null;
                return {
                    universe_active: D.universe && D.universe.active_stores,
                    fc_labels_len: (D.forecast && D.forecast.fc_labels && D.forecast.fc_labels.length) || 0,
                    mom_scorecard_len: Array.isArray(sc) ? sc.length : -1,
                    mom_scorecard_first_keys: sc && sc.length ? Object.keys(sc[0]) : [],
                    diag_keys: diag ? Object.keys(diag) : [],
                    diag_ok: diag ? ['n_calibrated_months','mape_pct','bias_pct','mae_lakh'].every(k => k in diag) : false,
                };
            })()
        """)

        await browser.close()
        return {"js_errors": js_errors, "tab_texts": tab_texts, "dash": dash_checks}


@pytest.fixture(scope="session", autouse=True)
def session_data():
    if not _SESSION:
        _SESSION.update(_run(_build_session()))
    return _SESSION


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_no_js_errors_on_load(session_data):
    errs = session_data["js_errors"]
    assert errs == [], f"JS page errors on load: {errs}"


@pytest.mark.parametrize("tab_id,keywords", list(TABS_KEYWORDS.items()))
def test_tab_keywords_present(session_data, tab_id, keywords):
    text = session_data["tab_texts"].get(tab_id, "")
    assert text, f"Tab '{tab_id}' produced no text (button missing?)"
    missing = [k for k in keywords if k not in text]
    assert not missing, f"{tab_id}: keywords not found — {missing}"


@pytest.mark.parametrize("tab_id", ALL_TAB_IDS)
def test_no_nan_undefined(session_data, tab_id):
    text = session_data["tab_texts"].get(tab_id)
    if text is None:
        pytest.skip(f"Tab '{tab_id}' not rendered (button not in nav)")
    nan_c = text.count("NaN")
    undef_c = text.count("undefined")
    assert nan_c == 0, f"{tab_id}: {nan_c} occurrences of 'NaN'"
    assert undef_c == 0, f"{tab_id}: {undef_c} occurrences of 'undefined'"


def test_dash_mom_chain_scorecard_structure(session_data):
    """Present only after a full data rebuild with secondary_sales source files."""
    d = session_data["dash"]
    if d["mom_scorecard_len"] == -1:
        pytest.skip("mom_chain_scorecard not in DASH (pre-rebuild data.js)")
    assert d["mom_scorecard_len"] > 0, "mom_chain_scorecard is empty"
    required = {"chain", "apr_lakh", "may_lakh", "jun_lakh", "trajectory"}
    actual = set(d["mom_scorecard_first_keys"])
    missing = required - actual
    assert not missing, f"mom_chain_scorecard[0] missing keys: {missing}"


def test_dash_forecast_diagnostics(session_data):
    """Present only after a full data rebuild that runs compute_forecast_diagnostics."""
    d = session_data["dash"]
    if not d["diag_keys"]:
        pytest.skip("forecast.diagnostics not in DASH (pre-rebuild data.js)")
    assert d["diag_ok"], (
        f"forecast.diagnostics missing required keys. Present: {d['diag_keys']}"
    )


def test_dash_universe_stores(session_data):
    count = session_data["dash"]["universe_active"]
    assert isinstance(count, (int, float)) and count > 0, (
        f"universe.active_stores invalid: {count}"
    )


def test_dash_forecast_fc_labels_12months(session_data):
    length = session_data["dash"]["fc_labels_len"]
    assert length == 12, f"forecast.fc_labels: expected 12, got {length}"
