"""Lightweight skill registry — scans skills/*.md, parses YAML frontmatter, serves catalog."""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)


class SkillRegistry:
    """Load domain skill files from a directory and serve them on demand."""

    def __init__(self, skills_dir: str | Path = "skills") -> None:
        self._dir = Path(skills_dir)
        self._skills: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._dir.is_dir():
            logger.warning("Skills directory not found: %s — registry is empty", self._dir)
            return

        # Load flat .md files (e.g., skills/promo-query.md)
        for path in sorted(self._dir.glob("*.md")):
            try:
                self._parse(path)
            except Exception as exc:
                logger.warning("Skipping %s — parse error: %s", path, exc)

        # Load nested skill directories (e.g., .claude/skills/mt-python-pipeline/SKILL.md)
        for skill_dir in sorted(self._dir.glob("*/SKILL.md")):
            try:
                self._parse(skill_dir)
            except Exception as exc:
                logger.warning("Skipping %s — parse error: %s", skill_dir, exc)

    def _parse(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            logger.warning("%s has no valid YAML frontmatter — skipped", path)
            return
        meta = _parse_yaml_simple(m.group(1))
        name = meta.get("name") or path.stem
        self._skills[name] = {
            "name": name,
            "description": meta.get("description", ""),
            "tags": meta.get("tags", []),
            "body": m.group(2).strip(),
        }

    def list_skills(self) -> str:
        """Compact catalog — inject into base system prompt to tell the LLM what skills exist."""
        if not self._skills:
            return "(no skills loaded)"
        return "\n".join(
            f"- {s['name']}: {s['description']}" for s in self._skills.values()
        )

    def get_skill(self, name: str) -> str | None:
        """Full Markdown body for *name*, or None if not found."""
        entry = self._skills.get(name)
        return entry["body"] if entry else None

    def __len__(self) -> int:
        return len(self._skills)


def _parse_yaml_simple(yaml_text: str) -> dict[str, Any]:
    """Minimal inline YAML parser: handles string, quoted string, and inline list values."""
    result: dict[str, Any] = {}
    for line in yaml_text.splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            result[key] = [i.strip().strip("\"'") for i in raw[1:-1].split(",") if i.strip()]
        else:
            result[key] = raw.strip("\"'")
    return result


# ── integration example ──────────────────────────────────────────────────────

def build_system_prompt(base_prompt: str, registry: SkillRegistry, active_skill: str | None = None) -> str:
    """Compose a full system prompt with skill catalog + optional active skill body.

    Usage:
        registry = SkillRegistry("skills")
        prompt = build_system_prompt(BASE_PROMPT, registry, active_skill="promo-query")
    """
    parts = [base_prompt.rstrip(), "", "## Available Skills", registry.list_skills()]
    if active_skill:
        body = registry.get_skill(active_skill)
        if body:
            parts += ["", f"## Active Skill: {active_skill}", body]
    return "\n".join(parts)
