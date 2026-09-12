# Retrieval and Evaluation — RAG Controls and Quality Metrics

**Scope:** Grounding rules for retrieved content, evaluation dataset requirements,
and quality metrics for agent-produced outputs.

---

## RAG Retrieval Controls

### Retrieval-Before-Claim Rule

An agent may not assert a fact without retrieving a source first. The retrieval
step is not optional and not skippable. If no relevant chunk is returned, the
correct response is:

```
[NOT FOUND IN AVAILABLE SOURCES]
Claim: <what was asked>
Sources searched: <list>
Action: Cannot confirm. Locate a primary source or mark claim as unverified.
```

Fabricating a plausible-sounding answer when retrieval fails is a P0 violation
of the evidence-grounded operating principle.

### Relevance Threshold

Chunks below the relevance threshold must not be used as evidence:

| Similarity Method | Minimum Threshold | Action if Below |
|---|---|---|
| Cosine (dense vector) | 0.75 | Discard; search fails |
| BM25 (sparse keyword) | Score in top-5 | Discard if rank > 5 |
| Hybrid re-rank | 0.70 combined | Discard |

When all retrieved chunks fall below threshold, report retrieval failure — do not
lower the bar to produce an answer.

### Citation Requirements

Every factual claim in agent output must include a citation:

```
Format: [SOURCE: <document_name>, <section/row/page>]

Example: "FY27 Primary MRP was 31,336.79 L [SOURCE: FY27_Monthly_GMV_MRP.csv, row Jun-26]"
```

Uncited numbers and named entities in agent output are treated as unverified and
must be labelled `[UNVERIFIED]` before delivery.

### Conflict Resolution

When two retrieved chunks contradict each other:

1. Prefer the chunk with the higher relevance score
2. If scores are equal, prefer the more recent document
3. If recency is unknown, prefer the chunk matching a control total in the data
4. If no resolution is possible, report the conflict explicitly:

```
[CONFLICT IN SOURCES]
Claim A: <value> [SOURCE: doc1, row X]
Claim B: <value> [SOURCE: doc2, row Y]
Resolution: Cannot determine which is correct. Human review required.
```

### Hallucination Check Protocol

Before finalising any agent output containing numbers or named entities:

1. For each number in the output, confirm it appears verbatim in a retrieved chunk
2. For each named entity (person, company, product, date), confirm it appears in source
3. For each percentage or derived metric, confirm the numerator and denominator are sourced
4. Flag any value that cannot be traced back:

```
[HALLUCINATION RISK]
Value: <value>
Status: Not found verbatim in any retrieved chunk.
Action: Remove from output or source explicitly before delivery.
```

---

## Evaluation Datasets

### What Evaluation Datasets Are For

Evaluation datasets let the team measure whether an agent produces correct outputs
consistently. They are not training data — they are test fixtures.

### Required Dataset Structure

Each evaluation dataset must include:

```csv
eval_id,input_description,input_source,expected_output,expected_output_type,tolerance,tags
E001,"FY27 Primary MRP for Jun-26","FY27_Monthly_GMV_MRP.csv","31336.79","numeric","0.01","primary,fy27"
E002,"D1 governance status","cm2_decision_register.csv","PENDING_APPROVAL","exact","","governance,cm2"
```

Fields:
- `eval_id`: unique ID for the test case
- `input_description`: human-readable description of what the agent is asked
- `input_source`: the file/table the agent must retrieve from
- `expected_output`: the correct answer
- `expected_output_type`: `numeric`, `exact`, `regex`, `contains`
- `tolerance`: for numeric, the allowed absolute difference (e.g. `0.01` for rounding)
- `tags`: comma-separated tags for filtering eval runs

### Passing Criteria

| Output Type | Pass Condition |
|---|---|
| numeric | `abs(actual - expected) <= tolerance` |
| exact | `actual.strip() == expected.strip()` |
| regex | `re.search(pattern, actual)` |
| contains | `expected in actual` |

An eval set must have ≥ 80% pass rate for an agent to be considered release-ready.
Regressions (any previously-passing eval now failing) block release.

### Eval Dataset Location

```
tests/evals/<agent-name>/
  eval_dataset.csv    — input/expected pairs
  README.md           — what this eval covers, known gaps
```

### Running Evaluations

```bash
python3 -m scripts.evals.run --agent <agent-name> --dataset tests/evals/<agent-name>/eval_dataset.csv
```

Output lands in `outputs/evals/<agent-name>/results_<timestamp>.json`.

---

## Quality Metrics

### Output Quality Dimensions

| Dimension | Definition | Measurement |
|---|---|---|
| Groundedness | Fraction of claims traceable to a retrieved source | Manual spot-check + citation count |
| Completeness | Fraction of required fields populated in output | Schema validation |
| Accuracy | Fraction of numeric outputs within tolerance of expected | Eval dataset comparison |
| Consistency | Same input produces same output across runs | Re-run test (determinism check) |
| Latency | Time from task start to first complete output | Wall-clock ms |

### Minimum Quality Gates (Release Requirement)

- Groundedness: ≥ 95% of facts cited
- Completeness: 100% of required schema fields non-null
- Accuracy: ≥ 80% of eval cases pass (no regressions vs. prior run)
- Consistency: Identical deterministic output on re-run (use `hashlib.sha256`, not `hash()`)
- Latency: P95 < 60 seconds for standard tasks; alert if > 120 seconds

### Reporting Quality Metrics

Every agent run reports metrics in `outputs/evals/<run-id>/quality_report.json`:

```json
{
  "run_id": "2026-07-25T12:00:00Z",
  "agent": "run-evidence-grounded-agents",
  "task": "...",
  "groundedness": 0.97,
  "completeness": 1.0,
  "accuracy": 0.85,
  "consistency": true,
  "latency_p95_ms": 42000,
  "eval_pass_count": 17,
  "eval_total_count": 20,
  "gate_status": "PASS"
}
```

`gate_status` is `PASS` only when all five dimensions meet minimums.

---

## Unsupported Claim Classification

| Situation | Label | Action |
|---|---|---|
| Claim not in any source | `[UNSUPPORTED]` | Remove or source before delivery |
| Source found but below threshold | `[LOW-CONFIDENCE]` | Disclose; do not assert as fact |
| Conflicting sources, unresolved | `[CONFLICT]` | Report conflict; do not pick a side |
| Number not traceable to source | `[UNVERIFIED]` | Remove or add `NOT FOR PRODUCTION` |
| Estimate, not a retrieved fact | `[ESTIMATE — NOT FOR PRODUCTION]` | Finance/owner approval required |

Labels propagate: if an output contains a labelled value, the entire output is
labelled until the value is resolved.

---

**Reference version:** 2026-07-25
