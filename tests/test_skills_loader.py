"""Unit tests for SkillRegistry."""
import textwrap
from pathlib import Path

import pytest

from skills_loader import SkillRegistry, _parse_yaml_simple, build_system_prompt


# ── helpers ───────────────────────────────────────────────────────────────────

def make_skills_dir(tmp_path: Path, files: dict[str, str]) -> Path:
    d = tmp_path / "skills"
    d.mkdir()
    for name, content in files.items():
        (d / name).write_text(content, encoding="utf-8")
    return d


VALID_MD = textwrap.dedent("""\
    ---
    name: promo-query
    description: "Answers promo inquiries."
    tags: [promo, data]
    ---
    # Instructions
    Query the promo table using date filters.
""")

NO_NAME_MD = textwrap.dedent("""\
    ---
    description: "No name field."
    tags: [test]
    ---
    Body text here.
""")

BAD_MD = "# No frontmatter\nJust body text.\n"


# ── loading ───────────────────────────────────────────────────────────────────

def test_load_single_skill(tmp_path):
    d = make_skills_dir(tmp_path, {"promo-query.md": VALID_MD})
    reg = SkillRegistry(d)
    assert len(reg) == 1


def test_load_multiple_skills(tmp_path):
    d = make_skills_dir(tmp_path, {
        "promo-query.md": VALID_MD,
        "data-validation.md": NO_NAME_MD,
    })
    reg = SkillRegistry(d)
    assert len(reg) == 2


def test_list_skills_contains_name_and_description(tmp_path):
    d = make_skills_dir(tmp_path, {"promo-query.md": VALID_MD})
    reg = SkillRegistry(d)
    catalog = reg.list_skills()
    assert "promo-query" in catalog
    assert "Answers promo inquiries." in catalog


def test_get_skill_returns_body(tmp_path):
    d = make_skills_dir(tmp_path, {"promo-query.md": VALID_MD})
    reg = SkillRegistry(d)
    body = reg.get_skill("promo-query")
    assert body is not None
    assert "Query the promo table" in body


def test_get_skill_unknown_returns_none(tmp_path):
    d = make_skills_dir(tmp_path, {"promo-query.md": VALID_MD})
    reg = SkillRegistry(d)
    assert reg.get_skill("nonexistent") is None


# ── missing directory ─────────────────────────────────────────────────────────

def test_missing_directory_does_not_crash(tmp_path):
    reg = SkillRegistry(tmp_path / "no_such_dir")
    assert len(reg) == 0
    assert reg.list_skills() == "(no skills loaded)"


def test_missing_directory_list_skills_safe(tmp_path):
    reg = SkillRegistry(tmp_path / "no_such_dir")
    result = reg.list_skills()
    assert isinstance(result, str)


# ── malformed frontmatter ─────────────────────────────────────────────────────

def test_malformed_frontmatter_skipped(tmp_path):
    d = make_skills_dir(tmp_path, {"bad.md": BAD_MD, "promo-query.md": VALID_MD})
    reg = SkillRegistry(d)
    assert len(reg) == 1  # bad.md skipped; promo-query.md loaded


def test_missing_name_falls_back_to_stem(tmp_path):
    d = make_skills_dir(tmp_path, {"my-skill.md": NO_NAME_MD})
    reg = SkillRegistry(d)
    assert reg.get_skill("my-skill") is not None


def test_empty_directory_is_safe(tmp_path):
    d = tmp_path / "skills"
    d.mkdir()
    reg = SkillRegistry(d)
    assert len(reg) == 0
    assert reg.list_skills() == "(no skills loaded)"


# ── yaml parser ───────────────────────────────────────────────────────────────

def test_parse_yaml_simple_inline_list():
    result = _parse_yaml_simple("tags: [promo, data, sql]")
    assert result["tags"] == ["promo", "data", "sql"]


def test_parse_yaml_simple_quoted_string():
    result = _parse_yaml_simple('description: "My description."')
    assert result["description"] == "My description."


def test_parse_yaml_simple_unquoted_string():
    result = _parse_yaml_simple("name: promo-query")
    assert result["name"] == "promo-query"


def test_parse_yaml_simple_ignores_lines_without_colon():
    result = _parse_yaml_simple("no colon here\nname: test")
    assert result == {"name": "test"}


def test_parse_yaml_simple_empty_input():
    result = _parse_yaml_simple("")
    assert result == {}


# ── system prompt builder ─────────────────────────────────────────────────────

def test_build_system_prompt_includes_catalog(tmp_path):
    d = make_skills_dir(tmp_path, {"promo-query.md": VALID_MD})
    reg = SkillRegistry(d)
    prompt = build_system_prompt("You are a helpful assistant.", reg)
    assert "Available Skills" in prompt
    assert "promo-query" in prompt


def test_build_system_prompt_injects_active_skill(tmp_path):
    d = make_skills_dir(tmp_path, {"promo-query.md": VALID_MD})
    reg = SkillRegistry(d)
    prompt = build_system_prompt("Base.", reg, active_skill="promo-query")
    assert "Active Skill: promo-query" in prompt
    assert "Query the promo table" in prompt


def test_build_system_prompt_unknown_active_skill_is_safe(tmp_path):
    d = make_skills_dir(tmp_path, {"promo-query.md": VALID_MD})
    reg = SkillRegistry(d)
    prompt = build_system_prompt("Base.", reg, active_skill="nonexistent")
    assert "Base." in prompt  # does not crash


# ── real skills directory ─────────────────────────────────────────────────────

def test_real_skills_directory_loads():
    """Smoke-test: the repo's own skills/ dir loads without crashing."""
    reg = SkillRegistry("skills")
    assert len(reg) >= 0  # empty is fine if dir missing in CI; never raises
