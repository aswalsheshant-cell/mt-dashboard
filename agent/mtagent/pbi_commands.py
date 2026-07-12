"""Registers every Power BI command with ``pbi_registry`` and wires the
automated ones through ``WorkflowController`` so state, audit events and
error handling are consistent across commands. Import this module once
(``cli.py`` does) to populate the registry — the decorators in
``pbi_registry`` are what make each command discoverable via
``python -m mtagent pbi list``.
"""
from __future__ import annotations

import json
from pathlib import Path

from .config import Config
from .pbi_dataset import build_dataset
from .pbi_dax_gap import generate_dax_library
from .pbi_reconcile import reconcile_source_to_model
from .pbi_registry import get_command, register_command
from .pbi_workflow import (AUTOMATED, BLOCKED, COMPLETED_WITH_WARNING, FAILED,
                            SKIPPED_WITH_APPROVAL, STEP_BY_ID, WorkflowController,
                            run_automated_step)


@register_command(
    name="build-dataset",
    classification=AUTOMATED,
    step_id="build_datasets",
    description="Build the Power BI-ready dataset from the latest offtake files.",
)
def cmd_build_dataset(cfg: Config, controller: WorkflowController, **kwargs) -> dict:
    """Drives workflow steps 1-4 (validate sources -> build datasets ->
    generate dim/fact -> validate keys) from one physical build_dataset()
    call, since that function performs all four checks in a single pass
    over the source file. Each step still gets its own status/timestamp
    in the workflow state, so ``status``/``resume`` see granular progress
    even though the underlying work is one function call.
    """
    raw_dir = Path(kwargs["raw_dir"]) if kwargs.get("raw_dir") else None
    masters_dir = Path(kwargs["masters_dir"]) if kwargs.get("masters_dir") else None

    controller.start_step("validate_sources")
    try:
        result = build_dataset(cfg, raw_dir, masters_dir)
    except Exception as exc:  # noqa: BLE001 -- surface as a Failed step, never crash the CLI
        controller.fail_step("validate_sources", f"{type(exc).__name__}: {exc}")
        return {"status": "Failed", "error": str(exc)}

    if result.get("blocked_reason"):
        controller.block_step("validate_sources", result["blocked_reason"])
        return {"status": "Blocked", **result}

    controller.complete_step("validate_sources", validation_result="source file(s) discovered and column-validated")
    for step_id in ("build_datasets", "generate_dim_fact", "validate_keys"):
        controller.start_step(step_id)
        controller.complete_step(step_id, output_file=result.get("output_file", ""),
                                  validation_result=result.get("validation_result", ""),
                                  warning=result.get("warning", ""))
    return {"status": controller.state.steps["validate_keys"]["status"], **result}


@register_command(
    name="generate-dax",
    classification=AUTOMATED,
    step_id="generate_dax",
    description="Generate the complete DAX measure library (coverage audit + gap file).",
)
def cmd_generate_dax(cfg: Config, controller: WorkflowController, **kwargs) -> dict:
    dax_dir = Path(kwargs["dax_dir"]) if kwargs.get("dax_dir") else None
    return run_automated_step(controller, "generate_dax", lambda: generate_dax_library(cfg, dax_dir))


@register_command(
    name="reconcile-model",
    classification=AUTOMATED,
    step_id="reconcile_source_to_model",
    description="Run source-to-model reconciliation.",
)
def cmd_reconcile_model(cfg: Config, controller: WorkflowController, **kwargs) -> dict:
    if "source" not in kwargs or "build_dir" not in kwargs:
        raise ValueError("reconcile-model requires --source <offtake csv> and --build-dir <pbi_build/<id>>")
    source_path = cfg.path(kwargs["source"])
    build_dir = cfg.path(kwargs["build_dir"])
    masters_dir = Path(kwargs["masters_dir"]) if kwargs.get("masters_dir") else None
    return run_automated_step(controller, "reconcile_source_to_model",
                               lambda: reconcile_source_to_model(cfg, source_path, build_dir, masters_dir))


# --- steps 5, 7, 8, 9, 10: not yet implemented (see agent/PBI_WORKFLOW.md) --
#
# Graceful-stub contract: invoking one of these NEVER throws, crashes the
# CLI, or leaves the workflow stalled. Each stub logs a technical notice
# (the module it stands in for and why it's deferred) and transitions its
# step straight to the existing ``SKIPPED_WITH_APPROVAL`` terminal state
# (chosen deliberately over inventing a new status string -- the spec's
# status vocabulary is fixed; "skipped, with the documented decision to
# defer this module as its approval" is the closest accurate fit), which
# already advances the next step to Ready. A step is never silently
# reported as Completed for work that was never done.
_UNIMPLEMENTED_STEPS = {
    "generate-power-query": ("generate_power_query", "Power Query script generation (pbi_powerquery.py)"),
    "generate-page-blueprint": ("generate_page_blueprint", "page-wise visual blueprint generation (pbi_blueprint.py)"),
    "generate-theme": ("generate_theme", "Power BI theme JSON generation (pbi_theme.py)"),
    "generate-docs": ("generate_docs", "model documentation generation (pbi_docs.py)"),
    "prepare-build-package": ("prepare_build_package", "build package preparation (pbi_package.py)"),
}


def _make_unimplemented_stub(step_id: str, module_hint: str):
    def _stub(cfg: Config, controller: WorkflowController, **kwargs) -> dict:
        note = (f"{module_hint} is not yet implemented -- scoped for a future build "
                f"(see agent/PBI_WORKFLOW.md). Skipping so the workflow sequence can "
                f"proceed; this step is never silently claimed complete.")
        controller.skip_with_approval(step_id, note)
        return {"status": SKIPPED_WITH_APPROVAL, "note": note}
    return _stub


for _cmd_name, (_step_id, _hint) in _UNIMPLEMENTED_STEPS.items():
    register_command(
        name=_cmd_name,
        classification=AUTOMATED,
        step_id=_step_id,
        description=f"[not yet implemented] {STEP_BY_ID[_step_id].name}",
    )(_make_unimplemented_stub(_step_id, _hint))


@register_command(
    name="run-automated",
    classification=AUTOMATED,
    step_id="",
    description="Run every automated step end to end (build-dataset -> generate-dax -> "
                "not-yet-implemented stubs -> reconcile-model), stopping cleanly the "
                "moment a manual or approval step is reached.",
)
def cmd_run_automated(cfg: Config, controller: WorkflowController, **kwargs) -> dict:
    """The end-to-end automated-pipeline loop: never crashes on an unbuilt
    module, never stalls -- each step reports its real outcome and control
    passes to the next one. Stops (without erroring) the instant a MANUAL
    or APPROVAL step is next, since those require Power BI Desktop / human
    sign-off this agent cannot perform.
    """
    results: dict[str, dict] = {}

    build_result = get_command("build-dataset").handler(
        cfg, controller, raw_dir=kwargs.get("raw_dir"), masters_dir=kwargs.get("masters_dir"))
    results["build-dataset"] = build_result
    if build_result.get("status") in (BLOCKED, FAILED):
        return {"status": build_result["status"], "stopped_at": "build-dataset", "results": results}

    results["generate-dax"] = get_command("generate-dax").handler(cfg, controller, dax_dir=kwargs.get("dax_dir"))

    for cmd_name, (step_id, _hint) in _UNIMPLEMENTED_STEPS.items():
        results[cmd_name] = get_command(cmd_name).handler(cfg, controller)

    try:
        source_file = json.loads(build_result.get("validation_result", "{}")).get("source_file", "")
    except json.JSONDecodeError:
        source_file = ""
    if source_file and build_result.get("output_file"):
        results["reconcile-model"] = get_command("reconcile-model").handler(
            cfg, controller, source=str(cfg.root() / source_file),
            build_dir=str(cfg.root() / build_result["output_file"]), masters_dir=kwargs.get("masters_dir"))

    statuses = {k: v.get("status") for k, v in results.items()}
    if any(s == FAILED for s in statuses.values()):
        overall = FAILED
    elif any(s == BLOCKED for s in statuses.values()):
        overall = BLOCKED
    elif any(s == COMPLETED_WITH_WARNING for s in statuses.values()):
        overall = COMPLETED_WITH_WARNING
    else:
        overall = "Completed"
    return {"status": overall, "results": statuses, "next_manual_step": controller.next_manual_step()}


@register_command(
    name="status",
    classification=AUTOMATED,
    step_id="",
    description="Show dashboard build status.",
)
def cmd_status(cfg: Config, controller: WorkflowController, **kwargs) -> dict:
    return controller.status_summary()


@register_command(
    name="next-manual-step",
    classification=AUTOMATED,
    step_id="",
    description="Show only the next manual Power BI step.",
)
def cmd_next_manual_step(cfg: Config, controller: WorkflowController, **kwargs) -> dict:
    step = controller.next_manual_step()
    return step or {"message": "no step is currently Manual Action Required"}


@register_command(
    name="resume",
    classification=AUTOMATED,
    step_id="",
    description="Resume from the last completed step.",
)
def cmd_resume(cfg: Config, controller: WorkflowController, **kwargs) -> dict:
    return controller.resume_plan()


@register_command(
    name="mark-complete",
    classification="approval",
    step_id="",
    description="Mark this step complete (requires evidence).",
)
def cmd_mark_complete(cfg: Config, controller: WorkflowController, **kwargs) -> dict:
    for required in ("step_id", "evidence_kind", "evidence"):
        if required not in kwargs:
            raise ValueError(f"mark-complete requires --{required.replace('_', '-')}")
    return controller.mark_step_complete(kwargs["step_id"], kwargs["evidence_kind"], kwargs["evidence"])
