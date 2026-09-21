# Risk & Control Centre — Phase A (Foundation)

Scoped-down first slice of a much larger request (a full ISO 31000-style
Risk Register, KRI registry, Control library, and a "Risk & Control Centre"
dashboard tab with a heatmap). This document explains what Phase A actually
is, what it deliberately is not yet, and why.

## Why this is scoped down

The full request would build a Risk Register, a KRI registry, a Control
library and a Likelihood×Impact scoring model largely from scratch. A
DISCOVER pass (2026-09-21) found this repo already has most of that
machinery — just not consolidated under one name:

- **Release gates**: `scripts/ci_validate_datajs.py` (baseline drift),
  `scripts/release_gate.py` (MANDATORY/ADVISORY severity), `scripts/
  aug26_data_readiness_gate.py`, and ~15 more `ci_validate_*.py`/
  `validate_*.py` scripts.
- **Exception registers**: `config/data_source_registry.yml`'s
  `validation_status` field, `scripts/store_history_readiness.py`'s 7-state
  `SOURCE_STATES` machine, the incentive workbook's `08_Exceptions`/
  `12_Rule_Decisions` sheets.
- **Severity vocabularies**: `config/analytics_config.json`'s `rag` block
  (green/amber/red bands for 5 metrics), `dashboard/alert_controller.js`'s
  CRITICAL/WARNING/INFO enum, `release_gate.py`'s MANDATORY/ADVISORY.
- **Readiness gates**: `readiness_gate()` in `scripts/build_dashboard_data.py`
  already evaluates 8 analytical layers (chain_primary, pvm, profitability,
  scorecard_execution, npd, sales_consolidation, incentive,
  persona_reporting) and publishes the result as `DASH.readiness` in
  `dashboard/data.js` — status, measured value, threshold, and what
  unblocks it, per gate.

Building a second, parallel Risk Register next to all of this would be
exactly the "duplicate truth" anti-pattern the original request itself
forbids (§31 of the request: "The Risk Engine should REFER TO an existing
KPI. It should not recalculate it independently."). So Phase A is
**consolidation, not construction**: a registry of rules that each *point
at* one of the mechanisms above, plus a thin aggregator that reads them.

**What's genuinely absent, confirmed by search:** a Likelihood×Impact
scoring model (zero matches for "likelihood" anywhere in this repo), a
named Risk Register, a KRI registry, and any Risk-labeled dashboard
surface. Phase A does not invent these either — see "What Phase A does not
do" below.

## What Phase A actually is

- **`config/risk_rule_registry.yml`** — 5 rules, each declaring: which
  existing module/function/config it reads, its risk family, its severity
  vocabulary (reused from the source, never invented), its owner, and an
  `evaluation` status (`IMPLEMENTED` or `NOT_IMPLEMENTED_PHASE_A`). No rule
  recomputes a business number.
- **`scripts/risk_rule_aggregate.py`** — reads the registry, evaluates each
  `IMPLEMENTED` rule by calling/reading the real source it points at, and
  produces a deterministic snapshot of current risk instances. Each
  instance has a stable `risk_key` (`<rule_id>::<entity>`) so the same
  underlying condition produces the same key on every run — the append-only
  history that would let a key be *tracked* over time is Phase B, not built
  here (Phase A is a snapshot, not a ledger).
- **`scripts/test_risk_rule_aggregate.py`** — 18 tests: registry schema
  invariants (unique rule IDs, every rule declares a real source, no rule
  claims an approval status this pass can't back), the aggregator's output
  cross-checked against this repo's own already-known real state (e.g. the
  `offtake_fy26_store_article` MISSING source registered during the SSG/2D
  work, `DASH.readiness.blocked`, `phase2c_gate_status()`), determinism
  across repeated runs, and fixture-isolated tests for edge cases (empty
  registry, missing `data.js`).

Run it: `python scripts/risk_rule_aggregate.py [--out path.json]`.

## Risk taxonomy (Phase A — 5 families, not 20)

| Family | Covers |
|---|---|
| `DATA_QUALITY` | Source correctness, completeness, freshness, availability |
| `RECONCILIATION` | Whether a tracked total still ties to its declared baseline |
| `RELEASE_CHANGE` | Release-gate / baseline-drift status |
| `PROCESS_READINESS` | Whether an analytical layer's own stated precondition holds |
| `THIRD_PARTY_SOURCE` | External or business-supplied source dependency status |

The original request's 20-family taxonomy is not adopted wholesale —
most of those families (Forecast risk, Primary Allocation risk, NPI risk,
Financial/Margin risk, AI risk, Security risk, Governance/Approval risk,
…) have no rule pointing at a real, already-computed signal yet. Adding a
family with no rule behind it would be exactly the "invented coverage"
this document argues against. New families get added when a Phase B/C
rule is actually built for them — see `docs/AGENT_ARCHITECTURE_MAPPING.md`
for the same discipline applied to specialist-agent roles.

## Risk vs Issue vs Incident (definitions only — no mechanism yet)

- **Risk**: something that *may* occur (e.g. "the SSG source may never
  arrive").
- **Issue**: a risk that is *currently* occurring (e.g. "the SSG source is
  overdue" — this is what `RR-SSG-SOURCE-BLOCKED` actually reports today).
- **Incident**: a specific realized, investigation-worthy event (e.g. "a
  dashboard was published while a mandatory baseline was failing"). No
  Incident mechanism exists yet — Phase A's aggregator only ever reports
  Issues (current, observed conditions), never speculative future Risks or
  investigated-and-closed Incidents.

## What Phase A does NOT do

Per the agreed scope ("Risk Rule Registry + thin read-only aggregator, no
new scoring invented, no new UI yet"):

- **No Likelihood×Impact / inherent-residual scoring.** No approved model
  exists anywhere in this repo. Inventing one now would violate the
  request's own §6 ("Do not invent quantitative values where no rule/owner
  exists... STATUS = PROVISIONAL rather than pretending the score is
  authoritative"). Every rule's `approval_status` is `PROVISIONAL` or
  `NOT_APPROVED` for exactly this reason.
- **No persistent Risk Register / history / audit trail.** The aggregator
  produces a snapshot; nothing is written to a database or append-only
  store yet.
- **No new dashboard tab.** The existing "Operational Alerts" tab
  (`buildAlerts()` + `dashboard/alert_controller.js`) already occupies
  the natural "alerts" slot in the nav — it is a metric-threshold-breach
  feed (CRITICAL/WARNING/INFO, account-level), not a risk register (no
  taxonomy, no control mapping, no owner workflow). A future Risk & Control
  Centre tab must not silently duplicate it; that decision is deferred to
  Phase C, not made here.
- **No Control Register, CAPA/Action tracking, Emerging Risk log,
  concentration-risk monitoring, third-party source tracker beyond the SSG
  rule, AI Risk Analyst, or release-gate wiring.** All explicitly Phase B–E
  (see below).
- **No Forecast WAPE/Bias evaluation.** `RR-FORECAST-RELIABILITY` is
  defined but marked `NOT_IMPLEMENTED_PHASE_A` — that calculation is
  client-side JS only (`computeForecastAccuracy()` in
  `dashboard/index.html`), and no WAPE/bias tolerance is registered
  anywhere in `config/analytics_config.json`. A Python-side reimplementation
  would be a second WAPE formula — exactly what this whole design exists to
  prevent.

## Recommended next phases (unchanged from the original request's own §42)

- **Phase B — Core MT Risk Engine**: add rules for Forecast (once a
  Python-side read-path or a WAPE tolerance exists), Primary Allocation
  fallback exposure, Master Data mapping gaps (via
  `mapping-approval-governor`'s existing classification output).
- **Phase C — Risk & Control Centre dashboard**: KPIs, heatmap, trend —
  only after Phase B gives it real rules to visualize, and only after an
  explicit decision on its relationship to the existing Operational Alerts
  tab.
- **Phase D — Controls/CAPA**: a Control Register cataloguing the release
  gates that already exist as code, plus action tracking.
- **Phase E — Advanced intelligence**: Emerging Risk log, concentration
  risk, broader third-party source tracking, AI Risk Analyst (summarizing
  only — never creating financial truth, never closing a risk, never
  changing a threshold, per the original request's own §24).

## Validation

`python -m py_compile scripts/risk_rule_aggregate.py
scripts/test_risk_rule_aggregate.py`; `python3 -m pytest
scripts/test_risk_rule_aggregate.py` (18/18); full repo suite unaffected
(new files only, nothing existing modified). `dashboard/data.js`,
`dashboard/index.html`, and every SSG/Phase-2 artifact are untouched by
this phase.
