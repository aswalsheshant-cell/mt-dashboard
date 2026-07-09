"""
Module 3 — LLM provider abstraction (swappable local / remote backends).

The rest of the agent never talks to a model directly; it goes through an
`LLMProvider`. This keeps the LLM interaction cleanly separated so the whole
pipeline can be unit-tested with **no model installed** (via the offline
deterministic provider), and so local vs. remote is a one-line swap.

Providers
---------
OfflineDeterministicProvider
    NOT a language model. A transparent, rule-based, schema-grounded
    NL->SQL translator. It exists so the pipeline runs and is testable in
    air-gapped environments, and as a safe fallback when no model is
    reachable. It only ever emits SQL against columns that actually exist in
    the provided schema — it never invents tables.

OllamaProvider
    Local model served by Ollama at http://localhost:11434 (offline; data
    stays on the machine). Uses only the standard library (urllib) so there
    is no extra dependency.

RemoteOptInProvider
    Placeholder for a hosted API (OpenAI-compatible shape). Disabled unless
    the caller passes allow_data_egress=True, because using it sends prompt
    content off-machine. Wired but intentionally gated per the security model.
"""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Dict, List, Optional


SQL_SYSTEM_PROMPT = (
    "You are a careful analytics engineer. Given a database schema and a "
    "question, return a single valid, read-only SQL SELECT statement that "
    "answers it. Use only tables and columns that appear in the schema. "
    "Return ONLY the SQL, with no prose and no code fences."
)


def build_sql_prompt(question: str, schema: Dict[str, List[str]]) -> str:
    lines = ["Schema:"]
    for table, cols in schema.items():
        lines.append(f"  {table}({', '.join(cols)})")
    lines.append("")
    lines.append(f"Question: {question}")
    lines.append("SQL:")
    return "\n".join(lines)


_SQL_FENCE = re.compile(r"```(?:sql)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_sql(text: str) -> str:
    """Pull a bare SQL statement out of a model's raw completion."""
    m = _SQL_FENCE.search(text)
    if m:
        text = m.group(1)
    text = text.strip()
    # keep from the first SELECT/WITH onward if the model added a preamble
    m = re.search(r"\b(SELECT|WITH)\b", text, re.IGNORECASE)
    if m:
        text = text[m.start():]
    return text.strip().rstrip(";").strip()


class LLMProvider:
    """Base interface. Real models implement `complete`; NL->SQL defaults to a
    prompt round-trip so any text model works without extra glue."""

    name = "base"

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        raise NotImplementedError

    def translate_to_sql(self, question: str, schema: Dict[str, List[str]]) -> str:
        prompt = build_sql_prompt(question, schema)
        raw = self.complete(prompt, system=SQL_SYSTEM_PROMPT)
        return extract_sql(raw)

    def is_available(self) -> bool:
        return True


# --------------------------------------------------------------------------
# Offline deterministic provider (no model required)
# --------------------------------------------------------------------------
class OfflineDeterministicProvider(LLMProvider):
    """Rule-based, schema-grounded NL->SQL. Deterministic and fully offline.

    This is intentionally simple and transparent — it is a *fallback and test
    harness*, not a substitute for a real model. It resolves the question to a
    real table and real columns, then emits standard SQL (COUNT / GROUP BY /
    DISTINCT / TOP-N / preview). Anything it cannot map becomes a safe preview
    (`SELECT * ... LIMIT n`) rather than a guess.
    """

    name = "offline"

    _COUNT = re.compile(r"\b(how many|count|number of|total number)\b", re.I)
    _GROUP = re.compile(r"\b(?:by|per|for each|group(?:ed)? by)\s+([a-z0-9 _-]+)", re.I)
    _DISTINCT = re.compile(r"\b(distinct|unique|list of)\s+([a-z0-9 _-]+)", re.I)
    _TOPN = re.compile(r"\b(?:top|highest|largest|biggest)\s+(\d+)?\b", re.I)

    def complete(self, prompt: str, system: Optional[str] = None) -> str:  # pragma: no cover
        raise RuntimeError(
            "OfflineDeterministicProvider does free-form completion is not "
            "supported; it implements translate_to_sql only."
        )

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _tokens(text: str) -> List[str]:
        return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if t]

    def _pick_table(self, question: str, schema: Dict[str, List[str]]) -> str:
        qtokens = set(self._tokens(question))
        best, best_score = None, -1
        for table in schema:
            ttokens = set(self._tokens(table))
            # singular/plural friendly overlap
            score = 0
            for qt in qtokens:
                for tt in ttokens:
                    if qt == tt or qt == tt + "s" or qt + "s" == tt or (len(qt) > 3 and qt in tt):
                        score += 1
            if score > best_score:
                best, best_score = table, score
        return best or next(iter(schema))

    def _resolve_column(self, phrase: str, columns: List[str]) -> Optional[str]:
        ptokens = self._tokens(phrase)
        if not ptokens:
            return None
        # exact/joined match first
        joined = "_".join(ptokens)
        for c in columns:
            if c == joined:
                return c
        # best token-overlap match
        best, best_score = None, 0
        for c in columns:
            ctokens = set(c.split("_"))
            score = sum(1 for pt in ptokens if pt in ctokens or any(pt in ct or ct in pt for ct in ctokens))
            if score > best_score:
                best, best_score = c, score
        return best if best_score > 0 else None

    def translate_to_sql(self, question: str, schema: Dict[str, List[str]]) -> str:
        if not schema:
            raise ValueError("No tables loaded; cannot translate.")
        table = self._pick_table(question, schema)
        columns = schema[table]
        qt = '"' + table + '"'

        # distinct / unique <col>
        m = self._DISTINCT.search(question)
        if m:
            col = self._resolve_column(m.group(2), columns)
            if col:
                return f'SELECT DISTINCT "{col}" FROM {qt} ORDER BY "{col}"'

        # group by <col> (optionally counting)
        m = self._GROUP.search(question)
        if m:
            col = self._resolve_column(m.group(1), columns)
            if col:
                return (
                    f'SELECT "{col}", COUNT(*) AS n FROM {qt} '
                    f'GROUP BY "{col}" ORDER BY n DESC'
                )

        # how many / count
        if self._COUNT.search(question):
            return f'SELECT COUNT(*) AS n FROM {qt}'

        # top N (preview ordered) — falls back to preview when no numeric hint
        m = self._TOPN.search(question)
        if m:
            n = int(m.group(1)) if m.group(1) else 10
            return f'SELECT * FROM {qt} LIMIT {n}'

        # default: safe preview
        return f'SELECT * FROM {qt} LIMIT 20'


# --------------------------------------------------------------------------
# Local Ollama provider (offline, on-machine model)
# --------------------------------------------------------------------------
class OllamaProvider(LLMProvider):
    """Talk to a local Ollama server. Offline: data never leaves the machine."""

    name = "ollama"

    def __init__(self, model: str = "mistral", endpoint: str = "http://localhost:11434",
                 timeout: float = 60.0):
        self.model = model
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or "",
            "stream": False,
            "options": {"temperature": 0.2},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.endpoint}/api/generate", data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return (body.get("response") or "").strip()


# --------------------------------------------------------------------------
# Remote (opt-in) provider — gated because it sends data off-machine
# --------------------------------------------------------------------------
class RemoteOptInProvider(LLMProvider):
    """Placeholder for a hosted, OpenAI-compatible endpoint.

    Deliberately inert unless `allow_data_egress=True` is passed, to honour the
    'local by default, cloud only on explicit per-request opt-in' rule. Fill in
    `complete` with a real HTTP call when you wire a specific vendor.
    """

    name = "remote"

    def __init__(self, model: str = "", endpoint: str = "", api_key: str = "",
                 allow_data_egress: bool = False):
        self.model = model
        self.endpoint = endpoint
        self.api_key = api_key
        self.allow_data_egress = allow_data_egress

    def is_available(self) -> bool:
        return bool(self.allow_data_egress and self.endpoint and self.api_key)

    def complete(self, prompt: str, system: Optional[str] = None) -> str:
        if not self.allow_data_egress:
            raise PermissionError(
                "RemoteOptInProvider is disabled. Sending the prompt to a hosted "
                "API would move data off-machine; pass allow_data_egress=True to "
                "explicitly opt in (and log the call in the audit trail)."
            )
        raise NotImplementedError(
            "Wire your vendor's HTTP call here once a remote endpoint is chosen."
        )


# --------------------------------------------------------------------------
# Factory
# --------------------------------------------------------------------------
def get_provider(name: str = "auto", **kwargs) -> LLMProvider:
    """Return a provider by name.

    'auto'    -> local Ollama if reachable, else offline deterministic.
    'offline' -> OfflineDeterministicProvider (no model, no network).
    'ollama'  -> OllamaProvider (local).
    'remote'  -> RemoteOptInProvider (gated).
    """
    name = (name or "auto").lower()
    if name == "offline":
        return OfflineDeterministicProvider()
    if name == "ollama":
        return OllamaProvider(**kwargs)
    if name == "remote":
        return RemoteOptInProvider(**kwargs)
    if name == "auto":
        ollama = OllamaProvider(**kwargs)
        if ollama.is_available():
            return ollama
        return OfflineDeterministicProvider()
    raise ValueError(f"Unknown provider: {name!r}")
