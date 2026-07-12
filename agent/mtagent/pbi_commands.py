"""Registers every Power BI command with ``pbi_registry`` and wires the
automated ones through ``WorkflowController`` so state, audit events and
error handling are consistent across commands. Import this module once
(``cli.py`` does) to populate the registry — the decorators in
``pbi_registry`` are what make each command discoverable via
``python -m mtagent pbi list``.
"""
from __future__ import annotations

from pathlib import Path

from .config import Config
from .pbi_dataset import build_dataset
from .pbi_dax_gap import generate_dax_library
from .pbi_reconcile import reconcile_source_to_model
from .pbi_registry import register_command
from .pbi_workflow import AUTOMATED, WorkflowController, run_automated_step


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
    return run_automated_step(controller, "reconcile_source_to_model",
                               lambda: reconcile_source_to_model(cfg, source_path, build_dir))


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
