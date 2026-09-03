"""Strict JSON boundary helpers for generated ``window.DASH`` artifacts."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import Any


_WINDOW_DASH_RE = re.compile(
    r"\A\s*window\.DASH\s*=\s*(?P<payload>.*)\s*;\s*\Z",
    re.DOTALL,
)


def normalize_json_boundary(value: Any) -> Any:
    """Return a JSON-ready copy with non-finite floats represented as null."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {key: normalize_json_boundary(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_json_boundary(item) for item in value]
    return value


def serialize_window_dash(value: Any, *, indent: int | None = None) -> str:
    """Serialize a dashboard object as strict JSON inside its JS assignment."""
    normalized = normalize_json_boundary(value)
    payload = json.dumps(
        normalized,
        indent=indent,
        ensure_ascii=False,
        allow_nan=False,
    )
    return f"window.DASH = {payload};\n"


def _reject_nonstandard_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant is not allowed: {value}")


def parse_window_dash_strict(source: str) -> Any:
    """Parse a complete ``window.DASH`` assignment as strict JSON."""
    match = _WINDOW_DASH_RE.fullmatch(source)
    if not match:
        raise ValueError("invalid window.DASH wrapper")
    return json.loads(
        match.group("payload"),
        parse_constant=_reject_nonstandard_constant,
    )

