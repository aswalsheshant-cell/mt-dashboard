# D1 — Finance decision request: does CM2 include COGS?

**Status:** OPEN — blocking release
**Owner:** Finance
**Raised by:** Data Engineering
**Raised:** 2026-07-25
**Gate it blocks:** `GOV-FORMULA-DRAFT` (severity **BLOCKED**) in `scripts/dataeng/governance.py`
**Register row:** `config/cm2_decision_register.csv` → `D1`

---

## Why this is the last blocker

The release readiness gate reports **BLOCKED 1 · FAIL 0**. That single BLOCKED
finding is this decision. It is *not* a code defect — every code-side gate is
green (120 tests, CI green, FAIL 0). It cannot be cleared by engineering,
because clearing it means writing an approver name and date into
`config/cm2_formula.csv`, and an approval that engineering writes for itself is
not an approval.

```
GOV-FORMULA-DRAFT   BLOCKED
  summary      CM2 formula is DRAFT -- every CM2 figure must be labelled provisional
  evidence     9/9 components DRAFT
  location     config/cm2_formula.csv
  owner        Finance
  decision_ref D1
  remediation  Display "CM2 PROVISIONAL — FORMULA APPROVAL PENDING"; do not publish as final.
```

The remediation is now enforced in the product (commit `077997a`): the P&L tab
carries a provisional banner listing every reason. That makes the current state
*safe to ship*, not *approved*.

---

## The question

> Is approved product cost (COGS) deducted **inside** the reported CM2, or does
> CM2 stop at post-trade-spend contribution with COGS shown below it?

| Option | CM2 definition | Q1 FY27 effect |
|---|---|---|
| **(a) INCLUDE** | CM2 = NSV − COGS − trade − field force − logistics − other | reduces CM2 by **1,922.66 L** (Q1 FY27, NSV basis) |
| **(b) EXCLUDE** | CM2 = NSV − trade − field force − logistics − other; COGS reported below CM2 | CM2 unchanged; COGS disclosed separately |

Recommended safe default currently in force: **staged outside reported CM2**
(neither option applied to a published figure).

---

## What is already settled — do not re-litigate

| Ref | Settled | Approved |
|---|---|---|
| **D10** | COGS applies to **GMV/MRP**; logistics applies to **NSV**. Calculated independently. | 2026-07-24 |
| **D11** | COGS and logistics are **separate components**; logistics is not inside the COGS rate. | 2026-07-24 |
| **D12** | Jun-26 GMV/MRP recovered from an authoritative source (control total matched to 0.02 L). | 2026-07-24 |

D1 is **only** the inclusion question. The *basis* is already approved — an
approved basis is not an approved inclusion.

---

## Computed inputs awaiting the decision

| Component | Basis | Q1 FY27 | Status |
|---|---|---|---|
| Approved product cost (COGS) | GMV/MRP | 3,057.00 L (Apr+May) + Jun from seed | basis approved (D10), inclusion pending |
| Approved logistics cost | NSV | 275.53 L (Apr+May); 170.45 L Jun memo | basis approved (D10/D11), inclusion pending |
| Approved trade expenses | absolute | 818.45 L candidate | pending D2, D3, D4 |
| Approved field-force expenses | absolute | 692.94 L CTC + 18.22 L reimb | pending D5, D6, D7 |
| Visibility / rental | absolute | no real source supplied | blocked |
| Other / shared corporate | absolute | no real source supplied | blocked |

---

## Second, independent reason CM2 is provisional

Separate from D1: **all three rows** in
`PowerBI/SeedData/Masters/PL_Expense_Input.csv` are marked
`EXAMPLE ROW -- replace with real data` (12.50 + 28.40 + 6.75 = **47.65 L**).

That is why the dashboard currently shows CM2 at **99.9% of NSV** — an
artefact of example data, not a real margin. Approving D1 alone will **not**
clear the banner; real expense rows are also required.

**Owner for that half:** Finance / Trade Marketing MIS.

---

## What Finance needs to return

To clear the gate, supply for each component in `config/cm2_formula.csv`:

1. `Include_Status` — `INCLUDE` or `EXCLUDE`
2. `Approved_By` — a named approver
3. `Approval_Date` — ISO date
4. `Status` — `APPROVED` (replacing `DRAFT`)
5. Evidence reference for the register row

The governance engine treats an approval missing approver, date **or** evidence
as not an approval (`GOV-WEAKAPPROVAL-*`, severity FAIL), so partial sign-off
will fail the gate rather than pass it.

Once `Status` is `APPROVED` on all components and real expense rows are loaded,
re-run:

```bash
python3 scripts/patch_cm2_provisional.py     # clears the banner (idempotent)
python3 -m scripts.dataeng.cli health        # expect BLOCKED 0
```

Both the banner and the gate are derived from this config — no code change is
needed when the decision lands.

---

## Explicitly not done

- No approver name, date or evidence has been written by engineering.
- `D1` and `D9` remain `PENDING_APPROVAL` in the decision register.
- No CM2 figure is labelled final anywhere.
- No NSV-to-GMV conversion was used.
