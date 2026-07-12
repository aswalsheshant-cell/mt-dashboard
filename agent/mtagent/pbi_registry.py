"""Power BI command registry — every command is registered with metadata
(classification, description, the workflow step it maps to) so ``pbi list``
and future automation can discover what exists without hardcoding a
parallel list. Registration is a decorator: importing the module that
defines a command is what makes it show up here, so ``cli.py`` imports
each command module once at startup.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CommandSpec:
    name: str
    classification: str      # "automated" | "manual" | "approval"
    step_id: str
    description: str
    handler: Callable


_REGISTRY: dict[str, CommandSpec] = {}


def register_command(name: str, classification: str, step_id: str, description: str):
    def deco(fn: Callable):
        if name in _REGISTRY:
            raise ValueError(f"command {name!r} already registered")
        _REGISTRY[name] = CommandSpec(name, classification, step_id, description, fn)
        return fn
    return deco


def get_command(name: str) -> CommandSpec:
    if name not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY))
        raise KeyError(f"unknown pbi command {name!r}. Known commands: {known}")
    return _REGISTRY[name]


def list_commands() -> list[CommandSpec]:
    return sorted(_REGISTRY.values(), key=lambda c: c.name)
