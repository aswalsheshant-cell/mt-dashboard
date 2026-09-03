"""Unit tests for SkillRegistry — compatible with unittest discover and pytest."""
import tempfile
import textwrap
import unittest
from pathlib import Path

from skills_loader import SkillRegistry, _parse_yaml_simple, build_system_prompt


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_skills(directory: Path, files: dict) -> Path:
    d = directory / "skills"
    d.mkdir(exist_ok=True)
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


# ── test cases ────────────────────────────────────────────────────────────────

class TestSkillLoading(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_load_single_skill(self):
        d = _write_skills(self.base, {"promo-query.md": VALID_MD})
        reg = SkillRegistry(d)
        self.assertEqual(len(reg), 1)

    def test_load_multiple_skills(self):
        d = _write_skills(self.base, {
            "promo-query.md": VALID_MD,
            "data-validation.md": NO_NAME_MD,
        })
        reg = SkillRegistry(d)
        self.assertEqual(len(reg), 2)

    def test_list_skills_contains_name_and_description(self):
        d = _write_skills(self.base, {"promo-query.md": VALID_MD})
        reg = SkillRegistry(d)
        catalog = reg.list_skills()
        self.assertIn("promo-query", catalog)
        self.assertIn("Answers promo inquiries.", catalog)

    def test_get_skill_returns_body(self):
        d = _write_skills(self.base, {"promo-query.md": VALID_MD})
        reg = SkillRegistry(d)
        body = reg.get_skill("promo-query")
        self.assertIsNotNone(body)
        self.assertIn("Query the promo table", body)

    def test_get_skill_unknown_returns_none(self):
        d = _write_skills(self.base, {"promo-query.md": VALID_MD})
        reg = SkillRegistry(d)
        self.assertIsNone(reg.get_skill("nonexistent"))


class TestMissingDirectory(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_directory_does_not_crash(self):
        reg = SkillRegistry(self.base / "no_such_dir")
        self.assertEqual(len(reg), 0)

    def test_missing_directory_list_skills_safe(self):
        reg = SkillRegistry(self.base / "no_such_dir")
        self.assertEqual(reg.list_skills(), "(no skills loaded)")

    def test_empty_directory_is_safe(self):
        d = self.base / "skills"
        d.mkdir()
        reg = SkillRegistry(d)
        self.assertEqual(len(reg), 0)
        self.assertEqual(reg.list_skills(), "(no skills loaded)")


class TestMalformedFrontmatter(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_malformed_frontmatter_skipped(self):
        d = _write_skills(self.base, {"bad.md": BAD_MD, "promo-query.md": VALID_MD})
        reg = SkillRegistry(d)
        self.assertEqual(len(reg), 1)

    def test_missing_name_falls_back_to_stem(self):
        d = _write_skills(self.base, {"my-skill.md": NO_NAME_MD})
        reg = SkillRegistry(d)
        self.assertIsNotNone(reg.get_skill("my-skill"))


class TestYamlParser(unittest.TestCase):

    def test_inline_list(self):
        result = _parse_yaml_simple("tags: [promo, data, sql]")
        self.assertEqual(result["tags"], ["promo", "data", "sql"])

    def test_quoted_string(self):
        result = _parse_yaml_simple('description: "My description."')
        self.assertEqual(result["description"], "My description.")

    def test_unquoted_string(self):
        result = _parse_yaml_simple("name: promo-query")
        self.assertEqual(result["name"], "promo-query")

    def test_ignores_lines_without_colon(self):
        result = _parse_yaml_simple("no colon here\nname: test")
        self.assertEqual(result, {"name": "test"})

    def test_empty_input(self):
        result = _parse_yaml_simple("")
        self.assertEqual(result, {})


class TestSystemPromptBuilder(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_includes_skill_catalog(self):
        d = _write_skills(self.base, {"promo-query.md": VALID_MD})
        reg = SkillRegistry(d)
        prompt = build_system_prompt("You are a helpful assistant.", reg)
        self.assertIn("Available Skills", prompt)
        self.assertIn("promo-query", prompt)

    def test_injects_active_skill_body(self):
        d = _write_skills(self.base, {"promo-query.md": VALID_MD})
        reg = SkillRegistry(d)
        prompt = build_system_prompt("Base.", reg, active_skill="promo-query")
        self.assertIn("Active Skill: promo-query", prompt)
        self.assertIn("Query the promo table", prompt)

    def test_unknown_active_skill_is_safe(self):
        d = _write_skills(self.base, {"promo-query.md": VALID_MD})
        reg = SkillRegistry(d)
        prompt = build_system_prompt("Base.", reg, active_skill="nonexistent")
        self.assertIn("Base.", prompt)

    def test_no_active_skill_omits_body_section(self):
        d = _write_skills(self.base, {"promo-query.md": VALID_MD})
        reg = SkillRegistry(d)
        prompt = build_system_prompt("Base.", reg)
        self.assertNotIn("Active Skill:", prompt)


class TestRealSkillsDirectory(unittest.TestCase):

    def test_real_skills_directory_loads(self):
        """Smoke-test: the repo's own skills/ dir loads without crashing."""
        reg = SkillRegistry("skills")
        self.assertIsInstance(reg.list_skills(), str)

    def test_real_skills_directory_has_expected_skills(self):
        reg = SkillRegistry("skills")
        self.assertGreaterEqual(len(reg), 3)
        for name in ("promo-query", "data-validation", "report-generator"):
            self.assertIsNotNone(reg.get_skill(name), f"Missing skill: {name}")


if __name__ == "__main__":
    unittest.main()
