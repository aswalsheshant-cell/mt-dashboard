#!/usr/bin/env python3
"""Validate the canonical skill suite.

Runs every gate the suite depends on: frontmatter contract, naming, manifest
agreement, trigger overlap, handoff resolution, reference integrity, and the
safety checks that keep untrusted imported material out of the prompt.

Usage:
    python skill-suite/scripts/validate_skills.py
    python skill-suite/scripts/validate_skills.py --overlap-only
    python skill-suite/scripts/validate_skills.py --json
    python skill-suite/scripts/validate_skills.py --suite path/to/skill-suite

Exit code 0 when no ERROR-level finding is present, 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    sys.exit(
        "PyYAML is required: pip install pyyaml\n"
        "The suite deliberately does not ship a hand-rolled YAML parser -- a manual "
        "line parser mishandles block scalars and multi-line values and fails silently."
    )

# --------------------------------------------------------------------------- config

ALLOWED_FRONTMATTER_KEYS = {"name", "description"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DESCRIPTION_MIN = 80
DESCRIPTION_MAX = 1024
DESCRIPTION_SOFT_MAX = 900

REQUIRED_SECTIONS = [
    "# Role and mandate",
    "# Scope and boundaries",
    "## In scope",
    "## Required handoffs",
    "# Execution workflow",
    "# Guardrails",
    "# Output contract",
]

# Descriptions are rendered into XML by some hosts; these characters corrupt the
# markup unless the renderer escapes them.
XML_SENSITIVE = ("&", "<", ">")

# Strings that would open or close a prompt boundary if they arrived through
# imported reference material.
PROMPT_BOUNDARY_PATTERNS = [
    re.compile(r"</?(system|human|assistant)>", re.I),
    re.compile(r"</?(available_)?skills?>", re.I),
    re.compile(r"\bignore (all |any )?(previous|prior|above) instructions\b", re.I),
    re.compile(r"\bdisregard (all |any )?(previous|prior|above)\b", re.I),
    re.compile(r"\byou are now\b.{0,40}\b(dan|jailbr|unrestricted)", re.I),
    re.compile(r"<\|.*?\|>"),
]

EXECUTABLE_SUFFIXES = {
    ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".com", ".msi",
    ".ps1", ".sh", ".bash", ".zsh", ".jar", ".apk", ".scr", ".pyc",
}
ALLOWED_SUFFIXES = {".md", ".txt", ".csv", ".json", ".yaml", ".yml"}

STOPWORDS = {
    "a", "an", "and", "any", "are", "as", "at", "be", "been", "but", "by", "can",
    "for", "from", "handles", "has", "have", "in", "into", "is", "it", "its", "not",
    "of", "on", "or", "over", "own", "the", "then", "this", "to", "use", "used",
    "user", "uses", "using", "was", "what", "when", "where", "which", "who", "why",
    "with", "asks", "wants", "excludes", "hands", "off", "skill", "invoke", "that",
}

OVERLAP_ERROR = 0.55
OVERLAP_WARN = 0.40

# --------------------------------------------------------------------------- model


@dataclass
class Finding:
    level: str  # ERROR | WARN | INFO
    gate: str
    location: str
    message: str

    def render(self) -> str:
        return f"{self.level:<5} [{self.gate}] {self.location}: {self.message}"


@dataclass
class Skill:
    name: str
    directory: Path
    skill_md: Path
    description: str = ""
    body: str = ""
    files: list[Path] = field(default_factory=list)


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    checksums: dict[str, dict[str, str]] = field(default_factory=dict)

    def add(self, level: str, gate: str, location: str, message: str) -> None:
        self.findings.append(Finding(level, gate, location, message))

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "ERROR"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "WARN"]


# --------------------------------------------------------------------------- helpers


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Return (frontmatter_yaml, body). frontmatter is None when absent."""
    if not text.startswith("---"):
        return None, text
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not match:
        return None, text
    return match.group(1), match.group(2)


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z][a-z0-9-]{2,}", text.lower())
    return {w for w in words if w not in STOPWORDS}


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


# --------------------------------------------------------------------------- gates


def load_skills(suite: Path, report: Report) -> list[Skill]:
    skills_root = suite / "skills"
    if not skills_root.is_dir():
        report.add("ERROR", "layout", str(skills_root), "skills/ directory not found")
        return []

    skills: list[Skill] = []
    for directory in sorted(p for p in skills_root.iterdir() if p.is_dir()):
        skill_md = directory / "SKILL.md"
        if not skill_md.is_file():
            report.add("ERROR", "layout", str(directory), "missing SKILL.md")
            continue
        skills.append(
            Skill(
                name=directory.name,
                directory=directory,
                skill_md=skill_md,
                files=sorted(p for p in directory.rglob("*") if p.is_file()),
            )
        )
    return skills


def gate_frontmatter(skill: Skill, report: Report) -> None:
    text = skill.skill_md.read_text(encoding="utf-8")
    frontmatter, body = split_frontmatter(text)
    skill.body = body

    if frontmatter is None:
        report.add("ERROR", "frontmatter", skill.name, "no YAML frontmatter delimited by ---")
        return

    try:
        data = yaml.safe_load(frontmatter)
    except yaml.YAMLError as exc:
        report.add("ERROR", "frontmatter", skill.name, f"YAML did not parse: {exc}")
        return

    if not isinstance(data, dict):
        report.add("ERROR", "frontmatter", skill.name, "frontmatter is not a mapping")
        return

    keys = set(data)
    extra = keys - ALLOWED_FRONTMATTER_KEYS
    missing = ALLOWED_FRONTMATTER_KEYS - keys
    if extra:
        report.add(
            "ERROR",
            "frontmatter",
            skill.name,
            f"disallowed key(s) {sorted(extra)}; versions and dependencies belong in manifest.json",
        )
    if missing:
        report.add("ERROR", "frontmatter", skill.name, f"missing key(s) {sorted(missing)}")
        return

    name = str(data["name"]).strip()
    description = str(data["description"]).strip()
    skill.description = description

    if name != skill.directory.name:
        report.add(
            "ERROR", "naming", skill.name,
            f"frontmatter name '{name}' does not match directory '{skill.directory.name}'",
        )
    if not NAME_PATTERN.match(name):
        report.add("ERROR", "naming", skill.name, f"name '{name}' is not kebab-case")

    if len(description) < DESCRIPTION_MIN:
        report.add(
            "ERROR", "description", skill.name,
            f"description is {len(description)} chars; under {DESCRIPTION_MIN} it will not route reliably",
        )
    elif len(description) > DESCRIPTION_MAX:
        report.add(
            "ERROR", "description", skill.name,
            f"description is {len(description)} chars; limit is {DESCRIPTION_MAX}",
        )
    elif len(description) > DESCRIPTION_SOFT_MAX:
        report.add(
            "WARN", "description", skill.name,
            f"description is {len(description)} chars; keep under {DESCRIPTION_SOFT_MAX} to avoid crowding the prompt",
        )

    lowered = description.lower()
    if "use when" not in lowered:
        report.add("WARN", "description", skill.name, "description does not open with a 'Use when' trigger clause")
    if "hands off to" not in lowered:
        report.add("WARN", "description", skill.name, "description declares no handoff condition")


def gate_sections(skill: Skill, report: Report) -> None:
    for heading in REQUIRED_SECTIONS:
        pattern = re.compile(rf"^{re.escape(heading)}\s*$", re.M)
        if not pattern.search(skill.body):
            report.add("ERROR", "template", skill.name, f"missing required section '{heading}'")


def gate_xml_safety(skill: Skill, report: Report) -> None:
    """Descriptions are rendered into XML by some hosts.

    A raw & < or > corrupts that markup. This does not forbid the characters --
    it verifies that escaping them is lossless, and flags them so the rendering
    path is known to escape rather than strip.
    """
    import html

    present = [c for c in XML_SENSITIVE if c in skill.description]
    if not present:
        return

    escaped = html.escape(skill.description, quote=True)
    if html.unescape(escaped) != skill.description:
        report.add("ERROR", "xml-safety", skill.name, "description does not round-trip through html.escape")
        return

    report.add(
        "WARN", "xml-safety", skill.name,
        f"description contains XML-sensitive character(s) {present}; the renderer must escape, not strip",
    )


def gate_prompt_boundaries(skill: Skill, report: Report) -> None:
    for path in skill.files:
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            report.add("ERROR", "encoding", str(path), "file is not valid UTF-8")
            continue
        for pattern in PROMPT_BOUNDARY_PATTERNS:
            for match in pattern.finditer(text):
                line = text[: match.start()].count("\n") + 1
                report.add(
                    "ERROR", "prompt-boundary", f"{path}:{line}",
                    f"prompt-boundary or injection pattern found: {match.group(0)[:60]!r}",
                )


def gate_files(skill: Skill, report: Report, suite: Path) -> None:
    for path in skill.files:
        if not is_within(path, suite):
            report.add("ERROR", "path-traversal", str(path), "file resolves outside the suite root")
            continue
        if path.is_symlink():
            report.add("ERROR", "path-traversal", str(path), "symlinks are not permitted in a skill directory")
        suffix = path.suffix.lower()
        if suffix in EXECUTABLE_SUFFIXES:
            report.add("ERROR", "executable", str(path), f"unexpected executable file type '{suffix}'")
        elif suffix not in ALLOWED_SUFFIXES:
            report.add("WARN", "file-type", str(path), f"unexpected file type '{suffix}' in a skill directory")
        if ".." in path.parts:
            report.add("ERROR", "path-traversal", str(path), "path contains a parent-directory segment")


def gate_references(skill: Skill, report: Report, suite: Path) -> None:
    """Every relative markdown/inline reference inside the skill must resolve.

    Resolution is attempted against the containing file, the skill root, the
    skills root (so one skill may cite another's reference) and the suite root
    (so manifest.json resolves). Placeholders such as DI-YYYYMMDD-NNN.md are
    skipped -- they are templates, not links.
    """
    link_pattern = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|csv|json|txt))`")
    md_link_pattern = re.compile(r"\]\(([^)]+)\)")
    placeholder = re.compile(r"(YYYY|MMDD|NNN|XXX|<|>|\[)")

    for path in skill.files:
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        candidates = set(link_pattern.findall(text)) | {
            link for link in md_link_pattern.findall(text)
            if not link.startswith(("http://", "https://", "#", "mailto:"))
        }
        for candidate in candidates:
            # Paths pointing at the wider repository are informational, not suite links.
            if candidate.startswith(("scripts/", "dashboard/", "PowerBI/", "docs/", "skill-suite/")):
                continue
            if placeholder.search(candidate):
                continue
            roots = [path.parent, skill.directory, suite / "skills", suite]
            if any((root / candidate).resolve().exists() for root in roots):
                continue
            report.add("WARN", "reference", str(path), f"relative reference does not resolve: {candidate}")


def gate_overlap(skills: list[Skill], report: Report) -> None:
    tokens = {s.name: tokenize(s.description) for s in skills if s.description}
    names = sorted(tokens)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            score = jaccard(tokens[left], tokens[right])
            if score >= OVERLAP_ERROR:
                report.add(
                    "ERROR", "overlap", f"{left} vs {right}",
                    f"trigger overlap {score:.2f} >= {OVERLAP_ERROR}; merge them or narrow one and declare a handoff",
                )
            elif score >= OVERLAP_WARN:
                report.add(
                    "WARN", "overlap", f"{left} vs {right}",
                    f"trigger overlap {score:.2f}; confirm the boundary clause distinguishes them",
                )


def gate_manifest(suite: Path, skills: list[Skill], report: Report) -> dict:
    manifest_path = suite / "manifest.json"
    if not manifest_path.is_file():
        report.add("ERROR", "manifest", str(manifest_path), "manifest.json not found")
        return {}

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.add("ERROR", "manifest", str(manifest_path), f"invalid JSON: {exc}")
        return {}

    for key in ("schema_version", "suite_version", "skills"):
        if key not in manifest:
            report.add("ERROR", "manifest", "manifest.json", f"missing required key '{key}'")

    entries = manifest.get("skills", [])
    entry_names = [e.get("name", "") for e in entries]
    directory_names = [s.name for s in skills]

    duplicates = {n for n in entry_names if entry_names.count(n) > 1}
    for name in sorted(duplicates):
        report.add("ERROR", "manifest", name, "duplicate manifest entry")

    for name in sorted(set(directory_names) - set(entry_names)):
        report.add("ERROR", "manifest", name, "skill directory has no manifest entry")
    for name in sorted(set(entry_names) - set(directory_names)):
        report.add("ERROR", "manifest", name, "manifest entry has no skill directory")

    known = set(entry_names)
    for entry in entries:
        name = entry.get("name", "<unnamed>")
        for key in ("version", "source", "dependencies", "handoffs", "sha256"):
            if key not in entry:
                report.add("ERROR", "manifest", name, f"entry missing '{key}'")
        version = str(entry.get("version", ""))
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            report.add("ERROR", "manifest", name, f"version '{version}' is not semantic")
        source = entry.get("source", "")
        if source != f"skills/{name}":
            report.add("ERROR", "manifest", name, f"source '{source}' should be 'skills/{name}'")
        for handoff in entry.get("handoffs", []):
            if handoff not in known:
                report.add("ERROR", "handoff", name, f"declared handoff '{handoff}' is not a skill in the suite")
        for dependency in entry.get("dependencies", []):
            if dependency not in known:
                report.add("ERROR", "dependency", name, f"dependency '{dependency}' is not a skill in the suite")

    # Every skill named in a description must be a declared handoff.
    declared = {e.get("name"): set(e.get("handoffs", [])) for e in entries}
    for skill in skills:
        mentioned = set(re.findall(r"`([a-z0-9-]+)`", skill.description))
        mentioned &= known
        mentioned.discard(skill.name)
        undeclared = mentioned - declared.get(skill.name, set())
        for name in sorted(undeclared):
            report.add(
                "ERROR", "handoff", skill.name,
                f"description references '{name}' but the manifest does not declare it as a handoff",
            )

    return manifest


# --------------------------------------------------------------------------- driver


def validate(suite: Path, overlap_only: bool = False) -> Report:
    report = Report()
    skills = load_skills(suite, report)
    report.skills = [s.name for s in skills]

    for skill in skills:
        gate_frontmatter(skill, report)

    if overlap_only:
        gate_overlap(skills, report)
        return report

    for skill in skills:
        gate_sections(skill, report)
        gate_xml_safety(skill, report)
        gate_prompt_boundaries(skill, report)
        gate_files(skill, report, suite)
        gate_references(skill, report, suite)
        report.checksums[skill.name] = {
            str(p.relative_to(skill.directory)): sha256_file(p) for p in skill.files
        }

    gate_overlap(skills, report)
    gate_manifest(suite, skills, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--suite", type=Path, default=Path(__file__).resolve().parents[1],
                        help="path to the skill-suite root (default: the parent of scripts/)")
    parser.add_argument("--overlap-only", action="store_true", help="run only the trigger-overlap gate")
    parser.add_argument("--json", action="store_true", dest="as_json", help="emit findings as JSON")
    args = parser.parse_args()

    report = validate(args.suite, overlap_only=args.overlap_only)

    if args.as_json:
        print(json.dumps({
            "skills": report.skills,
            "findings": [f.__dict__ for f in report.findings],
            "checksums": report.checksums,
            "ok": not report.errors,
        }, indent=2))
        return 0 if not report.errors else 1

    for finding in report.findings:
        print(finding.render())

    print()
    print(f"{len(report.skills)} skills, {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    if report.errors:
        print("VALIDATION FAILED")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
