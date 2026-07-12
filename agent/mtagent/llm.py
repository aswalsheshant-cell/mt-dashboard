"""Minimal Ollama client — stdlib urllib only, no SDK dependency.

Everything here is best-effort: if the Ollama daemon is not running the
caller gets a clean ``OllamaUnavailable`` and falls back (the ask command
prints retrieved passages instead of a generated answer; the vector store
falls back to hashed TF-IDF embeddings).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import Config


class OllamaUnavailable(RuntimeError):
    pass


def _post(url: str, payload: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as e:
        raise OllamaUnavailable(f"Ollama not reachable at {url}: {e}") from e


class Ollama:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.base = cfg.ollama_url.rstrip("/")

    def available(self) -> bool:
        try:
            req = urllib.request.Request(self.base + "/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                json.loads(resp.read().decode("utf-8"))
            return True
        except Exception:
            return False

    def models(self) -> list[str]:
        try:
            req = urllib.request.Request(self.base + "/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def chat(self, system: str, user: str, model: str | None = None) -> str:
        data = _post(self.base + "/api/chat", {
            "model": model or self.cfg.chat_model,
            "stream": False,
            "options": {"temperature": self.cfg.temperature},
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
        }, self.cfg.llm_timeout_s)
        return (data.get("message") or {}).get("content", "")

    def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        # /api/embed (batch, Ollama >= 0.2.6) with /api/embeddings fallback.
        model = model or self.cfg.embed_model
        try:
            data = _post(self.base + "/api/embed",
                         {"model": model, "input": texts}, self.cfg.llm_timeout_s)
            if "embeddings" in data:
                return data["embeddings"]
        except OllamaUnavailable:
            raise
        except Exception:
            pass
        out = []
        for t in texts:
            data = _post(self.base + "/api/embeddings",
                         {"model": model, "prompt": t}, self.cfg.llm_timeout_s)
            out.append(data["embedding"])
        return out
