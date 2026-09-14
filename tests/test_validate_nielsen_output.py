"""
Regression test for scripts/validate_nielsen_output.py.

Context: build-nielsen-dashboard.yml's old inline validator required the
generated HTML to be >=150KB ("expected ~238KB"), a threshold calibrated
against a template that embedded Chart.js inline (~205KB). Once Chart.js was
extracted to an external <script src="chart.umd.js"> reference, a correct
build dropped to ~36KB and the old check started failing a working build.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from validate_nielsen_output import validate_nielsen_html  # noqa: E402


def _old_size_check(html: str) -> list[str]:
    """The exact logic build-nielsen-dashboard.yml used before this fix."""
    errors = []
    if "__NIELSEN_DATA_PAYLOAD__" in html:
        errors.append("Placeholder was not replaced")
    if '"MONTHS"' not in html:
        errors.append("MONTHS key missing")
    if html.count("<canvas id=") < 5:
        errors.append("Too few canvas elements")
    size_kb = len(html) // 1024
    if size_kb < 150:
        errors.append(f"Output suspiciously small: {size_kb}KB (expected ~238KB)")
    return errors


def _build_real_output(tmp_path: Path) -> str:
    out = tmp_path / "nielsen_test.html"
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "build_nielsen_dashboard.py"),
            "--data", str(REPO_ROOT / "data" / "nielsen_aug26.json"),
            "--out", str(out),
        ],
        check=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )
    return out.read_text(encoding="utf-8")


def test_old_size_check_incorrectly_rejects_current_correct_output(tmp_path):
    html = _build_real_output(tmp_path)
    errors = _old_size_check(html)
    assert any("suspiciously small" in e for e in errors), (
        "This test documents the bug being fixed: the old ~238KB-based check "
        "should (incorrectly) flag today's real, correct ~36KB build."
    )


def test_new_validator_accepts_current_correct_output(tmp_path):
    html = _build_real_output(tmp_path)
    errors = validate_nielsen_html(html)
    assert errors == [], f"Real current build should validate cleanly, got: {errors}"


def test_new_validator_rejects_unresolved_placeholder():
    html = '<html>const DASHBOARD_DATA = /* __NIELSEN_DATA_PAYLOAD__ */ {};</html>'
    errors = validate_nielsen_html(html)
    assert any("placeholder" in e.lower() for e in errors)


def test_new_validator_rejects_missing_months_key():
    html = '<html>' + 'x' * 25000 + '<canvas id="a">' * 5 + '<script src="chart.umd.js"></script>' + 'id="bridge-wrap"' + 'DOMContentLoaded</html>'
    errors = validate_nielsen_html(html)
    assert any("MONTHS" in e for e in errors)


def test_new_validator_rejects_too_few_canvases():
    html = '<html>"MONTHS"' + 'x' * 25000 + '<canvas id="a">' + '<script src="chart.umd.js"></script>' + 'id="bridge-wrap"' + 'DOMContentLoaded</html>'
    errors = validate_nielsen_html(html)
    assert any("canvas" in e.lower() for e in errors)


def test_new_validator_rejects_truly_empty_output():
    html = "<html></html>"
    errors = validate_nielsen_html(html)
    assert any("suspiciously small" in e for e in errors)


def test_new_validator_rejects_missing_chartjs_reference():
    html = '<html>"MONTHS"' + 'x' * 25000 + '<canvas id="a">' * 5 + 'id="bridge-wrap"' + 'DOMContentLoaded</html>'
    errors = validate_nielsen_html(html)
    assert any("chart.js" in e.lower() for e in errors)


def test_new_validator_rejects_missing_container():
    html = '<html>"MONTHS"' + 'x' * 25000 + '<canvas id="a">' * 5 + '<script src="chart.umd.js"></script>' + 'DOMContentLoaded</html>'
    errors = validate_nielsen_html(html)
    assert any("container" in e.lower() for e in errors)


def test_new_validator_rejects_missing_init_entrypoint():
    html = '<html>"MONTHS"' + 'x' * 25000 + '<canvas id="a">' * 5 + '<script src="chart.umd.js"></script>' + 'id="bridge-wrap"</html>'
    errors = validate_nielsen_html(html)
    assert any("initialization" in e.lower() for e in errors)
