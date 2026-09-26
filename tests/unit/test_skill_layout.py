"""Guards for the skills an agent loads from this repository.

Catches the failure patterns found on 2026-09-26:
  * a skill saved as `skill.md` (lower case) -> Claude Code never loads it
  * a skill with no frontmatter description -> the agent cannot tell when to use it
  * the Codex copy (.agents/skills) drifting from skill-suite/ unnoticed,
    because `sync_skills.py --check` only checks project-claude by default
  * a skill script that edits the generated dashboard/data.js or commits/pushes
    on its own
  * an agent in .claude/agents listing a skill that is not installed

The layout checks are stdlib only; the suite validator and sync check need
PyYAML, which validate.yml installs from requirements.txt.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOTS = [ROOT / ".claude" / "skills", ROOT / ".agents" / "skills"]


def _frontmatter(text: str) -> dict:
    """Return the simple `key: value` pairs of a leading --- block ({} if none)."""
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip()
    return out


def _skill_dirs():
    for root in SKILL_ROOTS:
        if root.is_dir():
            for d in sorted(root.iterdir()):
                if d.is_dir() and not d.name.startswith("."):
                    yield d


class SkillLayoutTest(unittest.TestCase):
    def test_every_skill_file_is_named_SKILL_md(self):
        bad = []
        for d in _skill_dirs():
            names = [p.name for p in d.iterdir() if p.is_file()]
            if "SKILL.md" not in names:
                bad.append(f"{d.relative_to(ROOT)} has {sorted(n for n in names if n.lower() == 'skill.md') or 'no SKILL.md'}")
        self.assertEqual(bad, [], "skills that will not load")

    def test_every_skill_has_a_description_and_matching_name(self):
        bad = []
        for d in _skill_dirs():
            f = d / "SKILL.md"
            if not f.is_file():
                continue  # reported by the test above
            fm = _frontmatter(f.read_text(encoding="utf-8"))
            if not fm.get("description"):
                bad.append(f"{f.relative_to(ROOT)}: no frontmatter description")
            if "name" in fm and fm["name"] != d.name:
                bad.append(f"{f.relative_to(ROOT)}: name '{fm['name']}' != folder '{d.name}'")
        self.assertEqual(bad, [])

    def _run(self, *args):
        return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)

    def test_skill_suite_validates(self):
        r = self._run("skill-suite/scripts/validate_skills.py")
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-1000:])
        self.assertIn("0 warning(s)", r.stdout)

    def test_installed_copies_match_the_suite(self):
        for target in ("project-claude", "project-codex"):
            with self.subTest(target=target):
                r = self._run("skill-suite/scripts/sync_skills.py", "--check", "--target", target)
                self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-1000:])
                # --check exits 0 for "absent"/"outdated" (fine for a personal target);
                # the two copies committed here must match the suite exactly.
                states = re.findall(r"^\s{2}(\w+)\s+([\w-]+)$", r.stdout, re.M)
                self.assertTrue(states, r.stdout[-2000:])
                self.assertEqual([f"{st} {n}" for st, n in states if st != "clean"], [])

    def test_agents_name_real_skills(self):
        """Every .claude/agents/*.md has name + description, and each skill in its
        `skills:` list is installed in .claude/skills (else it silently loads none)."""
        agents = sorted((ROOT / ".claude" / "agents").glob("*.md"))
        bad = []
        for f in agents:
            text = f.read_text(encoding="utf-8")
            fm = _frontmatter(text)
            if fm.get("name") != f.stem or not fm.get("description"):
                bad.append(f"{f.name}: needs name '{f.stem}' and a description")
            block = re.search(r"^skills:\s*\n((?:\s+-\s*\S+\s*\n)+)", text, re.M)
            for skill in re.findall(r"-\s*(\S+)", block.group(1)) if block else []:
                if not (ROOT / ".claude" / "skills" / skill / "SKILL.md").is_file():
                    bad.append(f"{f.name}: skill '{skill}' is not installed")
        self.assertEqual(bad, [])

    def test_sentinel_script_is_read_only(self):
        src = (ROOT / ".claude/skills/dashboard-qa-sentinel/auto-fix.js").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"writeFileSync\(\s*(DATA_JS|INDEX_HTML)", src),
                          "sentinel writes data.js/index.html")
        self.assertIsNone(re.search(r"git\s+(add|commit|push)", src),
                          "sentinel stages, commits or pushes")


if __name__ == "__main__":
    unittest.main()
