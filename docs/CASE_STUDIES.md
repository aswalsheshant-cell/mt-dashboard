# Case Studies

Real, unscripted root-cause investigations from this project — kept as reusable
interview-prep and onboarding material. Each one happened as actual debugging
work, not a rehearsed exercise, and every number here is the real one produced
during that investigation (see the commit referenced in each case for the
exact diff).

**Why this file exists.** A rehearsed "tell me about a time you found a bug"
answer is usually vague because the bug is invented after the fact to fit the
question. This file works the other way: real bugs, found and fixed on this
project, written up afterward in the structure an interview or a QBR would
want — so the answer is grounded in something that actually happened and can
be checked against the commit.

---

## CS-01: The Reliance Brand Counter sub-view that never showed data

**Commit:** `60a062b` (PR [#143](https://github.com/aswalsheshant-cell/mt-dashboard/pull/143))
**Found:** 2026-09-16, during a deliberate tab-by-tab, sub-tab-by-sub-tab audit
of the dashboard, requested specifically to find issues the automated CI
sweep would not catch on its own.

### Problem

Channel & Chain Performance → **Reliance Brand Counter** sub-view showed "No
Reliance records" — every time, under every FY filter (All / FY26 / FY27).
This is not a cosmetic gap: `CLAUDE.md`'s own governance names Reliance Brand
Counter isolation a "Critical Data Boundary" (the ~350 staffed-counter
dedup rule), so a sub-view that silently shows nothing here is a real,
named analysis feature quietly not working.

### Why the automated CI sweep didn't catch it

This project already runs a 44-state sweep (11 tabs × 4 FY filters) on every
change, asserting zero JS errors and zero `NaN`/`undefined` text. That sweep
passed on this exact broken code, every time. **A query that runs cleanly and
returns zero rows produces no error and no `NaN`** — it just quietly shows an
empty state, which is indistinguishable from "correctly, there's no data for
this filter" unless someone checks whether there was *supposed* to be data.
The lesson generalizes: an automated regression suite catches "did this
crash," not "did this actually work" — those are different questions, and
the second one still needs a human (or a content-aware check) to ask it.

### Evidence

Read the relevant code (`dashboard/index.html`, in the `channel-dynamics`
tab's `reliance` sub-view branch):

```javascript
const recs = recFilter('Brand');
const reliance = recs.filter(r => r.Brand === 'Reliance');
```

Checked what that condition could actually match, directly against the live
`dashboard/data.js` rather than assuming the code's intent was correct:

```javascript
const chains = new Set(), brands = new Set();
for (const r of recs) { if (r.Chain) chains.add(r.Chain); if (r.Brand) brands.add(r.Brand); }
// Chain values containing "Reliance":  ['Reliance Retail']
// Brand values containing "Reliance":  []
// Sample Brand values: ['The Derma Co','Mamaearth','Aqualogica','BBlunt',"Dr. Sheth's",'Pure Origin','Lumineve','Staze']
```

### Root cause

`Reliance` is a **Chain** (Account) value in this data model — never a
Brand. Brand values are things like Mamaearth or The Derma Co. The filter
`r.Brand === 'Reliance'` could never match a single row of the 160,834 in
`detail_records`, so the sub-view was structurally guaranteed to show "No
Reliance records" regardless of any filter — this was not an edge case or a
recent regression, it had never worked.

### Fix

One line, minimal, scoped to exactly what was broken:

```diff
- const reliance = recs.filter(r => r.Brand === 'Reliance');
+ const reliance = recs.filter(r => r.Chain === 'Reliance Retail');
```

`recFilter('Brand')` (excluding the Brand dimension from the active global
filters) was deliberately left unchanged — that's a legitimate, unrelated
design choice: the Reliance Brand Counter view is meant to show the full
counter picture regardless of any Brand filter selected elsewhere on the
dashboard, and touching it was not needed to fix this bug.

### Verification

Not just "no more errors" — the fix was checked against real, expected
content:

- Full 44-state sweep re-run: 0 JS errors, 0 `NaN`/`undefined` (same as
  before the fix — this confirms the sweep alone would never have caught
  this bug either way, which is the point above).
- Direct content check: the sub-view now renders **32,505 real Reliance
  transactions** with a correct zone breakdown (North ₹39.1L, East ₹37.4L,
  West ₹22L, South 1 ₹20.2L, South 2 ₹12.5L, Central ₹5.8L under the "All"
  filter), confirmed consistent under FY26 and FY27 filters too.

### Impact

Recovered a previously-always-broken, governance-named analysis feature.
Before: 0 rows shown under any filter, ever. After: 32,505 real rows,
correctly zone-split, correctly responsive to the FY filter.

### The reusable methodology

1. **Scope the symptom before hypothesizing.** "No Reliance records" is a UI
   symptom, not yet a diagnosis — it doesn't tell you if the data is missing,
   the filter is wrong, or the field name is wrong.
2. **Don't trust a passing automated suite as proof the feature works.** It
   proves the feature doesn't crash. Those are different claims.
3. **Read the code's assumption, then check it against the real data** —
   never assume a filter condition matches what it looks like it should
   match. A five-line inspection script against the live data source settled
   the question definitively.
4. **Fix exactly the broken line.** Leaving `recFilter('Brand')` alone kept
   the fix minimal and reviewable — a one-line diff is easy to trust; a
   larger refactor invites new bugs and a harder review.
5. **Verify with real numbers, not just "tests pass."** The sweep passing
   before and after the fix proves it was never a useful check for this
   specific bug — the actual proof is the 32,505-row content check.

### One paragraph for an interview

*"I found a dashboard section that always showed 'no data,' on every filter,
and the CI suite was green. I read the filter condition, then checked the
real dataset directly instead of trusting what the code implied — the
condition was matching a Brand field for a value that only ever existed as a
Chain field, so it could never return a row. I fixed the one line, then
verified it by checking the actual row count and content came back correct,
not just that the test suite stayed green — because a query that returns
zero rows cleanly passes an error-based test suite every time, which is
exactly why this bug had been live indefinitely."*

---

## Adding the next case study

Same structure: Problem → why automated checks didn't (or did) catch it →
evidence → root cause → fix → verification → impact → the reusable lesson →
one interview paragraph. Only add a case that actually happened on this
project, with a real commit reference — this file is not for hypothetical
or generic examples.
