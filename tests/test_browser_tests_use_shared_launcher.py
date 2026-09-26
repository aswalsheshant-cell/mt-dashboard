"""Guard: browser tests launch Chromium through tests/browser_launch.js.

Found 2026-09-26 (pr-deep-review of #226): 18 tests in tests/ plus
test_sprint8_compliance_inventory.js hard-coded
`chromium.launch({ executablePath: '/opt/pw-browsers/chromium' })`, and the 18
also loaded Playwright from `/home/user/mt-dashboard/node_modules/playwright`.
Both paths exist only in the cloud container, so these tests fail with
"Executable doesn't exist" / "Cannot find module" on a runner or a local clone
-- an environment failure, not a dashboard one. tests/browser_launch.js
resolves PW_CHROMIUM_PATH -> Playwright's bundled browser ->
PLAYWRIGHT_BROWSERS_PATH/chromium and fails with a named error, never a skip.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = ROOT / "tests" / "browser_launch.js"


def _browser_scripts():
    files = sorted((ROOT / "tests").glob("*.js")) + sorted(ROOT.glob("test_*.js"))
    return [f for f in files if f != LAUNCHER]


def _rel(f):
    return str(f.relative_to(ROOT))


def test_no_hard_coded_browser_path():
    bad = [_rel(f) for f in _browser_scripts() if "/opt/pw-browsers" in f.read_text(encoding="utf-8")]
    assert bad == [], f"use launchChromium() from tests/browser_launch.js: {bad}"


def test_no_absolute_node_modules_require():
    pat = re.compile(r"require\(\s*['\"]/[^'\"]*node_modules/")
    bad = [_rel(f) for f in _browser_scripts() if pat.search(f.read_text(encoding="utf-8"))]
    assert bad == [], f"require('playwright') or ./browser_launch, not an absolute path: {bad}"


def test_only_the_shared_launcher_calls_chromium_launch():
    bad = [_rel(f) for f in _browser_scripts() if "chromium.launch(" in f.read_text(encoding="utf-8")]
    assert bad == [], f"call launchChromium() instead of chromium.launch(): {bad}"


def test_launcher_still_fails_loudly():
    src = LAUNCHER.read_text(encoding="utf-8")
    assert "PW_CHROMIUM_PATH" in src and "PLAYWRIGHT_BROWSERS_PATH" in src
    assert "throw new Error(" in src, "a missing browser must be a named error, not a skip"
