# Initiative state machines

Each tracked initiative below is a state machine, not a status note. The state is only
ever established by re-reading the named source (a PR, an issue, `git log`) at the time
of the question — the entries here are a map of *where to look*, and the *last known*
reading is recorded only so a stale entry is visibly stale rather than silently trusted.
If the live source disagrees with the entry below, the live source wins, and the entry
should be corrected in the same reply.

## Historical Primary chain backfill (Apr'25–Jul'26)

```
BACKFILL_VALIDATED → TECHNICAL_REVIEW → OWNER_DISPOSITION → BASELINE_MERGED
   → GOVERNANCE_IMPLEMENTED → FULL_REVALIDATION → POWER_BI_INTEGRATION
   → BUSINESS_ACCEPTANCE
```

| State | Cleared when | Source of truth |
|---|---|---|
| `BACKFILL_VALIDATED` | 16/16 monthly reconciliation PASS, 25/25 tests pass, provenance recorded | `scripts/historical_primary_chain_backfill_report.py` output; `scripts/test_historical_primary_chain_backfill.py` |
| `TECHNICAL_REVIEW` | Explicit reviewer disposition against PR's checklist; logic-affecting comments trigger a full rerun before re-freezing | PR #119, its "Review gate (technical)" section |
| `OWNER_DISPOSITION` | Every one of the 266 Distributor×Brand×Chain lines is Approve/Reject/Amend (not blank); disposition reconciles to ₹9,455.1997L | Returned `ProvisionalMapping_OwnerApproval_Apr25_Jul26.xlsx`, processed by `scripts/provisional_mapping_disposition.py`; tracked in issue #120 |
| `BASELINE_MERGED` | PR #119 merged to `main` — only after both `TECHNICAL_REVIEW` and `OWNER_DISPOSITION` are cleared | PR #119 `merged` status |
| `GOVERNANCE_IMPLEMENTED` | A *separate* PR applies only the owner-approved/amended mappings, referencing the signed-off register's SHA-256; total Primary unchanged at ₹51,481.65L | The follow-on governance PR (not opened as of this writing) |
| `FULL_REVALIDATION` | Backfill rerun after governance implementation; 16/16 reconciliation still PASS; explicit `PROVISIONAL → GOVERNED + UNALLOCATED/REJECTED` movement shown | The governance PR's test/reconciliation output |
| `POWER_BI_INTEGRATION` | Historical output wired into Power BI/reporting; provisional/unallocated classifications cannot silently render as governed Primary | Not started — blocked on every prior state |
| `BUSINESS_ACCEPTANCE` | Leadership/business consumption of the integrated numbers | Not started |

**Last known reading** (verify against the sources above before trusting — do not quote
this table's numbers without a fresh check when the question is time-sensitive):
`BACKFILL_VALIDATED` complete; `TECHNICAL_REVIEW` and `OWNER_DISPOSITION` both PENDING,
running in parallel; branch frozen at commit `51487b6d874ba5a63495202c44688cdcfcd65175`;
tracked in GitHub issue #120 (`aswalsheshant-cell/mt-dashboard`). Fixed figures that do
not move until a gate clears: total Primary ₹51,481.65L; provisional disposition target
₹9,455.1997L (₹9,455.20L rounded).

**What "what should I work on next" resolves to while both gates are PENDING**: HOLD on
further backfill engineering. The branch stays at the frozen SHA. The only legitimate
work is (a) reacting to a technical review event on PR #119 — full rerun only if the
comment is logic-affecting — or (b) processing a returned owner register the moment it
arrives (hash it, preserve it unchanged, run the disposition script). Anything else —
another script, another investigation, Power BI wiring — is scope creep on a HOLD.

## Adding a new tracked initiative

Copy the table shape above: named states in the intended order, what clears each one,
and the specific source (PR/issue/file/command) that answers it — never a paraphrase of
a prior conversation. An initiative with no PR/issue/commit to point at is not ready to
be tracked here; track the missing artifact first.
