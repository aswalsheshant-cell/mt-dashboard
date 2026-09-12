# AI Orchestrator Readiness Assessment

**Frozen:** 2026-08-07  
**Branch:** `claude/primary-pipeline-allocation-fy27-l9bdf6`  
**Commit:** `91b66c3`  
**Scope:** Readiness of the current codebase to serve as the trusted knowledge foundation for a future AI Agent / Orchestrator as described in the Strategic Roadmap.

---

## Agent Capability Map

The Strategic Roadmap identifies four AI capabilities. This assessment maps each to the trusted knowledge sources currently in this repository and rates readiness.

---

### Capability 1 — Business Logic Understanding

**Agent needs:** Understand KPI definitions, allocation rules, FY classification, chain hierarchy, master data, and reconciliation identities — well enough to explain them and detect when they are violated.

| Knowledge Source | Location | Quality | AI-Accessible? |
|-----------------|----------|---------|---------------|
| THE ONE FY RULE | `scripts/build_dashboard_data.py:42–93` + `CLAUDE.md` | Excellent — single authoritative implementation | Yes — code + doc |
| Chain allocation logic | `PowerBI/docs/DistributorPrimaryAllocation_Logic.md` | Excellent — step-by-step with examples | Yes — structured doc |
| Business Logic Registry | `docs/BUSINESS_LOGIC_REGISTRY.md` (this sprint) | Excellent — complete inventory with owner + approval status | Yes |
| KPI definitions | `PowerBI/docs/DataDictionary.md` | Good — all columns defined with units | Yes — structured doc |
| Master data canonicalization | `scripts/build_dashboard_data.py:107–217` | Good — CHAIN_ALIASES, BRAND_MAP | Yes — code |
| Finance decision status | `PowerBI/docs/Finance_Approval_Decision_Log.md` | Good — two open decisions with context | Yes — structured doc |
| Reconciliation identity | `PowerBI/docs/DistributorPrimaryAllocation_Logic.md` (QC section) | Good | Yes |

**Readiness rating: READY**  
All business logic is documented and machine-readable. An AI agent can be grounded in these sources and answer questions about KPI definitions, allocation rules, and reconciliation identities accurately. The critical gap is that Finance Decision 1 and Decision 2 are still PENDING — the agent must represent this uncertainty faithfully, not resolve it.

---

### Capability 2 — Anomaly Detection and Root Cause Analysis

**Agent needs:** Given a KPI value, detect whether it is anomalous and trace the root cause through the reconciliation chain (Source → Pipeline → Dashboard).

| Knowledge Source | Location | Quality | AI-Accessible? |
|-----------------|----------|---------|---------------|
| Release Gate report | `release_gate_report.json` (CI artifact) | Excellent — structured JSON with actual vs threshold | Yes — JSON |
| Test suite results | `pytest` output (167 tests) | Good — covers reconciliation, allocation, disclosure | Yes — structured |
| Reconciliation identity checks | `scripts/test_pipeline.py` | Good — allocation variance, unmapped NSV | Yes |
| Raw data QC flags | `D.reliance_bc.june_status`, `universe.storetype_note` | Good — disclosure fields in `data.js` | Yes |
| Negative frac tracking | `D.alloc.unmapped_note`, `rows_unmapped` | Good | Yes |

**Readiness rating: CONDITIONALLY READY**  
The reconciliation chain exists (gate reports, test results, disclosure fields). However, the agent cannot access raw source workbooks (gitignored) — it can only analyze the aggregated `data.js` output. Root cause analysis that requires raw row inspection is limited to what the Python scripts expose in their QC outputs. The agent would need access to `release_gate_report.json` at runtime.

**Gap:** The reconciliation chain is one-directional (source → dashboard). No reverse-tracing infrastructure exists yet (dashboard KPI → which source rows → why that value).

---

### Capability 3 — Forecasting and Scenario Analysis

**Agent needs:** Understand the TY target/forecast model, seasonal patterns, and the distinction between Primary (sell-in) and Offtake (sell-out) for forecasting purposes.

| Knowledge Source | Location | Quality | AI-Accessible? |
|-----------------|----------|---------|---------------|
| Forecast block | `D.forecast` in `data.js` | Good — monthly targets by brand/channel | Yes — JSON |
| Offtake patterns | `D.offtake` in `data.js` | Good — 26 months of sell-out | Yes — JSON |
| Primary patterns | `D.primary` + `D.detail_meta` in `data.js` | Good — FY25/26 + FY27 article-level | Yes — JSON |
| FY27 article-level primary | `D.detail_records` in `data.js` | Good — full granularity | Yes — JSON |
| Nielsen market share | `D.share` in `data.js` | Limited — data absent for FY27+ | Partial |

**Readiness rating: CONDITIONALLY READY**  
Historical data in `data.js` is sufficient for a pattern-recognition agent. Nielsen and TDP data gaps (empty source folders) mean market-context forecasting is limited to internal sell-in/sell-out signals only. A simple trend-extension agent is feasible; a causal model with market share is not yet.

---

### Capability 4 — Executive Insights (Why/Which/What Causal Analytics)

**Agent needs:** Explain why a KPI moved, which chains/brands/categories drove it, and what actions are recommended.

| Knowledge Source | Location | Quality | AI-Accessible? |
|-----------------|----------|---------|---------------|
| Drill hierarchy | `DRILL_HIER = ['Channel','Chain','Zone','State','Brand','Category','Article']` in `index.html` | Excellent — 7-level hierarchy | Yes — JS constant |
| Detail records | `D.detail_records` in `data.js` | Excellent — row-level article/chain/month | Yes — JSON |
| Comparison data | `D.comparison` block in `data.js` | Good — YoY/QoQ by dimension | Yes — JSON |
| Promo calendar | `D.promo` in `data.js` | Good — campaign dates + spend | Yes — JSON |
| Distribution universe | `D.universe` in `data.js` | Good — store counts by dimension | Yes — JSON |

**Readiness rating: READY (data foundation)**  
The data structure supports multi-level causal decomposition. The drill hierarchy is already implemented in the dashboard; an agent can reuse the same dimension hierarchy for narrative generation. The agent would need a structured prompt template and access to `data.js` at runtime.

---

## Agent-to-Knowledge-Source Mapping Summary

| Agent Capability | Primary Knowledge Sources | Readiness |
|-----------------|--------------------------|-----------|
| Business Logic Understanding | `BUSINESS_LOGIC_REGISTRY.md`, `DistributorPrimaryAllocation_Logic.md`, `DataDictionary.md`, `build_dashboard_data.py` | **READY** |
| Anomaly Detection / RCA | `release_gate_report.json`, test suite, `data.js` disclosure fields | **CONDITIONALLY READY** |
| Forecasting / Scenario | `data.js` (primary + offtake + forecast blocks) | **CONDITIONALLY READY** |
| Executive Insights (Why/Which) | `data.js` (detail_records + comparison + promo), drill hierarchy | **READY (data)** |

---

## Infrastructure Readiness for AI Orchestration

| Requirement | Status | Notes |
|-------------|--------|-------|
| Machine-readable business rules | READY | `BUSINESS_LOGIC_REGISTRY.md` (this sprint) |
| Structured data output | READY | `data.js` is JSON, accessible programmatically |
| Automated QC outputs | READY | `release_gate_report.json` from CI |
| Knowledge base (docs) | READY | 16 structured markdown docs in `PowerBI/docs/` |
| API / agent integration layer | NOT STARTED | No REST API, no agent SDK integration |
| Prompt templates | NOT STARTED | No agent prompts authored yet |
| Conversation memory | NOT STARTED | No memory layer designed |
| Tool definitions | NOT STARTED | No tool wrappers around pipeline functions |

---

## Critical Findings for AI Orchestrator Design

1. **Finance decisions must be represented as uncertainty, not facts.** The agent must know that Jun'26 allocation is PROVISIONAL and neg-frac treatment is unresolved. It must never present these as approved facts. The `Finance_Approval_Decision_Log.md` is the authoritative source.

2. **The agent must not mix Reliance BC into offtake.** `D.reliance_bc` is a separate data source with 49% double-count risk. Any agent accessing `data.js` must be explicitly instructed that `reliance_bc` rows must never be added to `D.offtake` totals.

3. **The agent must apply THE ONE FY RULE.** Any agent reasoning about time periods must implement `fy_tag_from_ym()` semantics — Apr–Dec Y → FY(Y+1); Jan–Mar Y → FY(Y). Hardcoded FY boundaries are prohibited.

4. **Release Gate is the trust anchor.** The agent should treat any `data.js` produced without a passing gate as unreliable. `gate_status: "PASS"` in `release_gate_report.json` is the minimum trust signal.

5. **No fabrication of Finance numbers.** The agent must mark any unavailable Finance control total as `AWAITING FINANCE CONTROL TOTAL` — not interpolate or infer.

---

## Recommended Next Steps for AI Orchestrator Development

**Priority order:**

1. Resolve Finance Decisions 1 and 2 — these are the foundational trust issue. An AI agent cannot accurately represent the Jun'26 allocation status without a decision.
2. Build a tool wrapper around `build_dashboard_data.py` that exposes the gate report, reconciliation output, and KPI block in a structured, agent-readable format.
3. Author a Business Knowledge Layer document that translates `BUSINESS_LOGIC_REGISTRY.md` into agent-facing prompt context (natural language, not code references).
4. Design the Anomaly Detection agent first (highest business value, clearest data contracts) using `release_gate_report.json` + `data.js` disclosure fields.
5. Add reverse-tracing infrastructure: given a dashboard KPI, produce the source rows and allocation path that produced it.

**Estimated readiness for Phase 1 agent (Business Logic Q&A):** 3–4 weeks of agent development after Finance decisions are resolved.
