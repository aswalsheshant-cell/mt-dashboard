"""Environment Readiness Skill + Dependency Management Skill.

Confirms the machine is ready before running dependent tests or release
checks, and classifies *why* a check didn't run -- code failure, missing
dependency, environment problem, or missing test data -- so a skip is
never silently reported as a pass.
"""
from __future__ import annotations

import importlib
import importlib.metadata
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

READY = "ENVIRONMENT_READY"
BLOCKED = "ENVIRONMENT_BLOCKED"

# --------------------------------------------------------------------- #
# Dependency Management Skill: classify why a check didn't produce a
# clean PASS. A dependency-related skip must never be reported as a
# passed validation -- these are the only vocabulary allowed for "why".
# --------------------------------------------------------------------- #
CODE_FAILURE = "code_failure"
DEPENDENCY_FAILURE = "dependency_failure"
ENVIRONMENT_FAILURE = "environment_failure"
MISSING_TEST_DATA = "missing_test_data"

# Declared once, matching agent/requirements.txt -- if a release-gate
# check needs a package to run for real (not degrade), it belongs here,
# not left as "merely optional".
RELEASE_REQUIRED_PACKAGES = ("openpyxl",)  # redaction_scan / formula_error_scan need it for real


@dataclass
class DependencyCheck:
    name: str
    declared_in: str          # e.g. "agent/requirements.txt"
    installed: bool
    version: str | None
    required_for_release: bool


@dataclass
class ReadinessReport:
    status: str                       # ENVIRONMENT_READY | ENVIRONMENT_BLOCKED
    python_version: str
    pip_version: str
    project_root_ok: bool
    write_permission_ok: bool
    requirements_file: str | None
    dependencies: list                # list[DependencyCheck]
    missing: list                     # list[str] -- human-readable corrective lines
    failure_class: str | None = None  # one of the 4 classification constants, or None if READY


def _check_package(name: str, declared_in: str, required_for_release: bool) -> DependencyCheck:
    try:
        version = importlib.metadata.version(name)
        installed = True
    except importlib.metadata.PackageNotFoundError:
        version, installed = None, False
    # Cross-check with an actual import -- a package can be "installed"
    # per metadata but broken/unimportable; never assume from one signal.
    if installed:
        try:
            importlib.import_module(name)
        except ImportError:
            installed = False
    return DependencyCheck(name, declared_in, installed, version, required_for_release)


def check_environment(cfg=None, repo_root: str | Path | None = None) -> ReadinessReport:
    """Real checks only -- no assumption is made from a command exiting
    without visible errors; every claim here is independently verified
    (e.g. package presence is checked via BOTH importlib.metadata AND an
    actual import, not just one).
    """
    py_version = sys.version.split()[0]
    try:
        pip_out = subprocess.run([sys.executable, "-m", "pip", "--version"],
                                  capture_output=True, text=True, timeout=15)
        pip_version = pip_out.stdout.strip() if pip_out.returncode == 0 else f"pip check failed: {pip_out.stderr.strip()}"
        pip_ok = pip_out.returncode == 0
    except Exception as exc:  # noqa: BLE001
        pip_version = f"pip check raised {type(exc).__name__}: {exc}"
        pip_ok = False

    root = Path(repo_root) if repo_root else (Path(cfg.root()) if cfg is not None else Path.cwd())
    project_root_ok = (root / "agent" / "mtagent").is_dir()

    write_permission_ok = False
    probe = root / "agent" / "index" / ".write_probe"
    try:
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("probe", encoding="utf-8")
        probe.unlink()
        write_permission_ok = True
    except OSError:
        write_permission_ok = False

    req_path = root / "agent" / "requirements.txt"
    requirements_file = str(req_path) if req_path.exists() else None

    dependencies = [
        _check_package(pkg, requirements_file or "agent/requirements.txt (not found)",
                        required_for_release=(pkg in RELEASE_REQUIRED_PACKAGES))
        for pkg in ("openpyxl", "pandas", "duckdb", "pypdf")
    ]

    missing: list = []
    failure_class = None
    if not project_root_ok:
        missing.append(f"project root not found at expected layout under {root} -- "
                        f"expected corrective action: run from the actual mt-dashboard clone")
        failure_class = ENVIRONMENT_FAILURE
    if not write_permission_ok:
        missing.append(f"no write permission under {root / 'agent' / 'index'} -- "
                        f"expected corrective action: fix directory permissions")
        failure_class = ENVIRONMENT_FAILURE
    if not pip_ok:
        missing.append("pip is not usable in this interpreter -- expected corrective action: "
                        "reinstall Python or repair pip (python -m ensurepip)")
        failure_class = ENVIRONMENT_FAILURE
    for dep in dependencies:
        if dep.required_for_release and not dep.installed:
            missing.append(
                f"'{dep.name}' not installed (required for release-gate checks, not merely optional) -- "
                f"expected corrective action: python -m pip install -r {dep.declared_in}, "
                f"then verify with: python -c \"import {dep.name}; print({dep.name}.__version__)\""
            )
            if failure_class is None:
                failure_class = DEPENDENCY_FAILURE

    status = BLOCKED if missing else READY
    return ReadinessReport(
        status=status, python_version=py_version, pip_version=pip_version,
        project_root_ok=project_root_ok, write_permission_ok=write_permission_ok,
        requirements_file=requirements_file, dependencies=dependencies,
        missing=missing, failure_class=failure_class,
    )


def format_report(report: ReadinessReport) -> str:
    lines = [f"Environment result: {report.status}", ""]
    lines.append(f"Python version: {report.python_version}")
    lines.append(f"pip: {report.pip_version}")
    lines.append(f"Project root OK: {report.project_root_ok}")
    lines.append(f"Write permission OK: {report.write_permission_ok}")
    lines.append(f"Requirements file: {report.requirements_file or '(not found)'}")
    lines.append("")
    lines.append("Dependencies:")
    for dep in report.dependencies:
        tag = "REQUIRED FOR RELEASE" if dep.required_for_release else "optional"
        state = f"installed v{dep.version}" if dep.installed else "NOT installed"
        lines.append(f"  - {dep.name} ({tag}): {state}")
    if report.missing:
        lines.append("")
        lines.append(f"Failure class: {report.failure_class}")
        lines.append("Missing / corrective action:")
        for m in report.missing:
            lines.append(f"  - {m}")
    return "\n".join(lines)


def classify_skip_reason(*, code_raised: bool = False, dependency_missing: bool = False,
                          environment_broken: bool = False, data_missing: bool = False) -> str:
    """A test/check didn't produce a clean pass -- name exactly why, in
    the fixed vocabulary above. Never described as a passed validation.
    Priority: environment > dependency > missing data > code, since an
    environment problem usually masks the others.
    """
    if environment_broken:
        return ENVIRONMENT_FAILURE
    if dependency_missing:
        return DEPENDENCY_FAILURE
    if data_missing:
        return MISSING_TEST_DATA
    if code_raised:
        return CODE_FAILURE
    raise ValueError("classify_skip_reason called with no failure signal set -- nothing to classify")
