"""Agent configuration: sensible defaults + optional agent/config.json overrides.

JSON (not YAML) so the config layer stays stdlib-only. Every path default is
derived from the repo root, which is auto-detected by walking up from this
file until CLAUDE.md / dashboard/ is found.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, fields
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    p = (start or Path(__file__).resolve()).absolute()
    if p.is_file():
        p = p.parent
    for cand in [p, *p.parents]:
        if (cand / "CLAUDE.md").exists() or (cand / "dashboard" / "index.html").exists():
            return cand
    return Path.cwd()


@dataclass
class Config:
    repo_root: str = ""
    # --- Ollama (all optional at runtime; agent degrades gracefully) ---
    ollama_url: str = "http://127.0.0.1:11434"
    chat_model: str = "llama3.1:8b"
    embed_model: str = "nomic-embed-text"
    llm_timeout_s: int = 180
    temperature: float = 0.1
    # --- retrieval ---
    top_k: int = 5
    chunk_chars: int = 1400
    chunk_overlap: int = 200
    # --- paths (relative to repo_root unless absolute) ---
    index_path: str = "agent/index/index.json"
    db_path: str = "agent/index/mt.duckdb"
    metadata_dir: str = "agent/metadata"   # drop model.bim / INFO.* exports here
    pdf_dirs: list = field(default_factory=lambda: ["agent/metadata"])
    # --- proactive diff engine (place / meeting --drilldown) ---
    npi_list: str = "PowerBI/SeedData/Masters/NPI_List.csv"  # optional; proxy used if absent
    mom_drop_threshold_pct: float = 10.0   # Zone/DC MoM drop that triggers an exception
    drilldown_top_n: int = 5               # underperforming outlets shown in drilldown
    # --- Power BI workflow controller (Module 2) ---
    pbi_build_dir: str = "agent/pbi_build"           # generated dataset/DAX-gap/QC output root
    pbi_reconciliation_tolerance_pct: float = 0.5    # source-vs-model variance % before FAIL

    def root(self) -> Path:
        return Path(self.repo_root) if self.repo_root else find_repo_root()

    def path(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else self.root() / p


def load_config(path: str | None = None) -> Config:
    """Defaults <- agent/config.json (if present) <- explicit --config path."""
    cfg = Config()
    candidates = []
    default_cfg = find_repo_root() / "agent" / "config.json"
    if default_cfg.exists():
        candidates.append(default_cfg)
    if path:
        candidates.append(Path(path))
    names = {f.name for f in fields(Config)}
    for c in candidates:
        try:
            data = json.loads(Path(c).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise SystemExit(f"config: cannot read {c}: {e}")
        for k, v in data.items():
            if k in names:
                setattr(cfg, k, v)
    if env := os.environ.get("OLLAMA_HOST"):
        if "://" not in env:
            env = "http://" + env
        cfg.ollama_url = env
    return cfg
