# Decision types

Every unresolved item — a single row or a compressed rule — gets exactly one of six
classifications. None of them set the owner's decision; they describe what kind of ask
it is.

| Type | Means | Requires |
|---|---|---|
| `AUTO_GOVERNABLE` | Evidence + an already-approved policy uniquely determines the answer | A prior, still-valid policy record covering this exact scope. Never a first-time approval — that always needs a human, however obvious it looks. |
| `OWNER_RULE_APPROVAL` | Multiple rows share one consistent proposed chain from one evidence source, with no contradiction | Every row in the cluster resolves to the same chain; the source is named; the rows remain individually listed for audit even though the ask is one line |
| `OWNER_ROW_EXCEPTION` | A row (or a cluster that failed to broaden) has unique or conflicting evidence | The specific conflict or uniqueness stated in plain language — "why this can't join the rule above" |
| `SOURCE_DATA_FIX_REQUIRED` | No mapping logic can resolve this; the source data itself is wrong or malformed | The specific defect (e.g. a corrupted field value) and what a fixed extract would need to contain |
| `INSUFFICIENT_EVIDENCE` | Not enough evidence exists to propose even a provisional answer | State exactly what evidence is missing, not just "unclear" |
| `NON_MATERIAL_MONITOR` | Real but low-value; tracked, not blocking | The value and why it's below the materiality bar, with a pointer to where it's tracked |

## Worked calibration (this repo's provisional bucket)

- A distributor whose every brand-month in the provisional bucket points to the same
  single chain, all sourced from the same workbook Dump-sheet snapshot → candidate
  `OWNER_RULE_APPROVAL` at Distributor→Chain scope, provided no month shows a different
  chain for that distributor (checked, not assumed).
- A distributor split across 2-3 chains by brand, with the same percentage split stable
  across every month present → still `OWNER_RULE_APPROVAL`, but the rule is a named
  split table (chain, %), not a single chain — the owner approves the split, not one
  answer.
- A distributor whose chain assignment differs by month with no explainable pattern
  (not a governed alias, not a documented business change) → `OWNER_ROW_EXCEPTION`,
  scoped to the specific month(s) that disagree — never absorbed into the surrounding
  rule by majority.
- The May'26 `SOURCE_SCHEMA_ANOMALY` rows (PO Type corrupted to an MTD-Sale-type value)
  → `SOURCE_DATA_FIX_REQUIRED`, never `OWNER_ROW_EXCEPTION` — no mapping decision fixes
  a corrupted source field; only a corrected extract does.
- A `MAPPING_NOT_FOUND` row where the distributor+brand+month combination has no
  matching workbook row and no Secondary evidence for that month → `INSUFFICIENT_EVIDENCE`
  if genuinely no proposal is defensible, or `SOURCE_DATA_FIX_REQUIRED` if the missing
  workbook row is itself the defect (the business simply hasn't captured that split yet).
- A ₹0.9L row that would otherwise be its own exception → `NON_MATERIAL_MONITOR` if it's
  below the stated materiality floor and isolated (no pattern linking it to a larger
  issue) — tracked in the exception list, not sent to the owner as a blocking ask.
