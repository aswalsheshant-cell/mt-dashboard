"""Source contract validation for the canonical engine's two inputs:
Primary detail_records and Offtake by_chain (contracts/primary_contract.yaml,
contracts/offtake_contract.yaml, plus the shared channel_contract.yaml /
chain_contract.yaml they reference).

Deliberately lightweight, per the certification instruction that a "huge
framework" is not needed here -- these are plain YAML documents read with
yaml.safe_load, validated with plain Python, no schema-validation library
dependency beyond PyYAML. Every validate_* function returns a list of
violation strings (empty list = contract satisfied).

This does NOT replace scripts/ci_validate_datajs.py's release-gate checks
(baseline invariants, detail-coverage regression) -- it is a narrower,
input-shape contract specifically for what the canonical engine reads.
"""
import math
import re
from pathlib import Path

import yaml

CONTRACTS_DIR = Path(__file__).resolve().parent.parent.parent / "contracts"


def load_contract(name):
    path = CONTRACTS_DIR / name
    with open(path) as f:
        return yaml.safe_load(f)


def _type_ok(value, declared_type):
    if declared_type == "string":
        return isinstance(value, str)
    if declared_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if declared_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if declared_type == "any":
        return True
    return True


def validate_channel_contract(data):
    """Every Channel value in detail_records must be in the closed
    channel_contract.yaml allowlist -- an unrecognized channel is a mapping
    defect, not a new business channel, until a human confirms otherwise."""
    contract = load_contract("channel_contract.yaml")
    allowed = set(contract["allowed_values"])
    rows = data.get("detail_records") or []
    seen_bad = sorted({r.get("Channel") for r in rows if r.get("Channel") not in allowed})
    if seen_bad:
        return [f"Channel value(s) not in closed allowlist {sorted(allowed)}: {seen_bad}"]
    return []


def validate_chain_contract(data):
    """Chain is an open list (new chains are expected over time) -- this
    only checks shape: non-null, non-empty string, on both Primary
    detail_records.Chain and offtake.by_chain[].name."""
    problems = []
    rows = data.get("detail_records") or []
    for r in rows:
        chain = r.get("Chain")
        if chain is None or (isinstance(chain, str) and not chain.strip()):
            problems.append(f"detail_records row has null/empty Chain: {r}")
            break  # one example is enough; this can be a large table
    by_chain = (data.get("offtake") or {}).get("by_chain") or []
    for row in by_chain:
        name = row.get("name")
        if name is None or (isinstance(name, str) and not name.strip()):
            problems.append(f"offtake.by_chain row has null/empty name: {row}")
    return problems


_PRIMARY_FY_FIELDS = ("Month", "FY", "Channel", "Zone", "State", "Chain", "Brand",
                      "Category", "SubCategory", "Range", "PackSize", "Article",
                      "EAN", "NSV", "MRP", "Qty")


def validate_primary_contract(data):
    """Validates dashboard/data.js's detail_records against
    contracts/primary_contract.yaml: required fields present, correct type,
    nullability, FY pattern, and full-row duplicate detection."""
    contract = load_contract("primary_contract.yaml")
    fields = contract["fields"]
    rows = data.get("detail_records") or []
    problems = []

    if not rows:
        return ["detail_records is empty -- no Primary fact rows to validate"]

    fy_pattern = re.compile(fields["FY"]["pattern"])
    seen_full_rows = set()
    duplicate_examples = []

    for i, r in enumerate(rows):
        for fname, spec in fields.items():
            value = r.get(fname)
            if spec.get("required") and fname not in r:
                problems.append(f"row {i}: missing required field {fname!r}")
                continue
            if value is None:
                if not spec.get("nullable", False) and spec.get("required"):
                    problems.append(f"row {i}: required field {fname!r} is null")
                continue
            if not _type_ok(value, spec["type"]):
                problems.append(f"row {i}: field {fname!r}={value!r} is not type {spec['type']}")
            if fname == "NSV":
                if isinstance(value, (int, float)):
                    if math.isnan(value) or math.isinf(value):
                        problems.append(f"row {i}: NSV is NaN/Infinity")
                    if value < 0 and not spec.get("negative_allowed", False):
                        problems.append(f"row {i}: NSV={value} negative but not allowed")
        fy = r.get("FY")
        if fy and not fy_pattern.match(fy):
            problems.append(f"row {i}: FY={fy!r} does not match pattern {fields['FY']['pattern']!r}")

        full_key = tuple(r.get(f) for f in _PRIMARY_FY_FIELDS)
        if full_key in seen_full_rows:
            duplicate_examples.append(full_key)
        else:
            seen_full_rows.add(full_key)

        if len(problems) > 200:
            problems.append("... more than 200 problems, stopping early")
            break

    if duplicate_examples:
        problems.append(
            f"{len(duplicate_examples)} exact full-row duplicate(s) found "
            f"(e.g. {duplicate_examples[0]}) -- indicates a double-loaded billing line")

    problems.extend(validate_channel_contract(data))
    return problems


def validate_offtake_contract(data):
    """Validates dashboard/data.js's offtake block against
    contracts/offtake_contract.yaml: chain-row shape, no duplicate chain
    names, FY field naming pattern, and no NaN/Infinity/negative offtake
    values."""
    problems = []
    offtake = data.get("offtake") or {}
    by_chain = offtake.get("by_chain") or []

    if not by_chain:
        return ["offtake.by_chain is empty -- no Offtake fact rows to validate"]

    fy_field_pattern = re.compile(r"^fy\d{2}$")
    secondary_fy_pattern = re.compile(r"^secondary_fy\d{2}$")
    seen_names = set()

    for i, row in enumerate(by_chain):
        name = row.get("name")
        if not name:
            problems.append(f"by_chain[{i}]: missing/empty 'name'")
            continue
        if name in seen_names:
            problems.append(f"by_chain: duplicate chain name {name!r} (offtake block must be pre-aggregated, one row per chain)")
        seen_names.add(name)

        for key, value in row.items():
            if key in ("name", "raw", "value", "total", "yoy"):
                continue
            if fy_field_pattern.match(key) or secondary_fy_pattern.match(key):
                if value is None:
                    continue
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    problems.append(f"by_chain[{name}].{key}={value!r} is not numeric")
                    continue
                if math.isnan(value) or math.isinf(value):
                    problems.append(f"by_chain[{name}].{key} is NaN/Infinity")
                if value < 0:
                    problems.append(f"by_chain[{name}].{key}={value} is negative (not allowed for offtake NSV)")

    problems.extend(validate_chain_contract(data))
    return problems


def validate_all(data):
    """{"primary": [...], "offtake": [...]} -- every source contract's
    violations, keyed by which input they belong to."""
    return {
        "primary": validate_primary_contract(data),
        "offtake": validate_offtake_contract(data),
    }
