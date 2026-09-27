# Project Completion Blocker Pack

**Baseline:** `main` `f960e1f` (final certification, 2026-09-26) — verdict
**READY_WITH_GOVERNED_BLOCKERS**
**Issued:** 2026-09-27
**Purpose:** one place with every request that stands between this project and a
fully-ready verdict: who owns it, what we need, and the exact exit condition.

Blocker status lives in `docs/PROJECT_STATE.md` (CB table). This pack does not
replace it — it is the outgoing request set. When an item closes, update the CB
row in `PROJECT_STATE.md`, not this file.

---

## Feature freeze (from `f960e1f`)

No new dashboards, tabs, forecast enhancements, risk centre, plugin policy,
convenience tooling or new dependencies (Great Expectations, dbt, pbi-tools,
Tabular Editor BPA, Fabric deployment) are merged until the blockers below are
cleared. New work is allowed only if it:

1. clears a blocker named in this pack, or
2. fixes a newly **reproduced** correctness defect (with a failing test first).

Closed on 2026-09-26/27 as outside the certified scope, branches kept, can be
rebuilt from current `main` if the need returns: #129, #130, #135, #136
(superseded by #243, #238, #240, #237) and #134, #165, #168, #169, #170.

---

## Summary

| # | Blocker | Owner | What we need | Exit condition |
|---|---|---|---|---|
| B1 | CB-01 — non-MT sales inside MT zone totals (₹11.64 Cr) | MT Leadership + MT Analytics | Nykaa (FSN) decision; FY27 article-wise primary, Apr–Aug'26 | `mt_channel_reconciliation.py` exits 0; FY25/FY26 unchanged; CI step made blocking |
| B2 | #120 → #119 — historical Primary chain backfill | Business owner of the mapping | 266-line approval register returned, every line decided | Decisions reconcile to ₹9,455.1997 L with no material Pending; 16/16 months reconcile; total ₹51,481.65 L unchanged |
| B3 | #229 — CM2 expense load (HOLD) | Finance + MT Leadership | Nykaa SS treatment, Tnsi chain, full Jul/Aug register, coverage label, scope of other costs | Rebuilt from current `main`; CM2 shows its expense coverage; all checks green |
| B4 | Power BI P&L assumptions, Jun–Aug'26 | Finance | Approved AssumptionTable rows | Assumption Coverage Gate passes (no `BLOCKED_FINANCE_INPUT`) |
| B5 | Power BI Desktop runtime checks | MT Channel Analyst Lead (Windows) | Two manual runs | CM2 Case 1 as expected; FY parser `Failures` = 0 rows |
| B6 | Incentive V1 business decisions | MT Leadership, Finance, MT Ops, HR | Decisions (a)–(e) + target basis, C1–C6, caps, proration | Every decision recorded; no payout calculated before that |

Not a blocker: issue #194 (`github-advanced-security` fails with a GitHub-side
`CAPIError 400`; not a required check; no repo change).

---

## B1 — CB-01: non-MT sales inside MT zone totals

**What happened.** FY27 zone totals (Apr–Aug'26) are all-channel. ₹11.64 Cr of
non-MT primary sits inside them: Nykaa (FSN) ₹10.41 Cr (billed eB2B), other eB2B
+ SIS ₹1.23 Cr (Eremedium, Azorte, Shoppers Stop). "Pan India" offtake
(₹1,035.14 L) is Nykaa, not a geography.

**Business impact.** MT totals are identical under every Nykaa option — Nykaa
leaves MT in all of them. Zones move: East conversion 73.8% → 85.2% (Nykaa is
13.4% of East primary), North 85.1% → 90.3%. National stays ≈85.5%.

**Decision (MT Leadership).** How Nykaa (FSN) is reported outside MT — the feed
mixes FSN B2C marketplace and Nykaa SS eB2B at article level:

- **A** — all under eB2B (matches the July deck; FSN B2C sits inside eB2B)
- **B** — split FSN B2C / Nykaa SS eB2B (needs a separated feed from the data team)
- **C** — Nykaa (FSN) as its own channel line

Record the owner as "MT Leadership" (role, not a name). A one-letter reply is not
a decision; the confirmation must name the option.

**Data (MT Analytics).** FY27 article-wise primary, uncapped, with the Channel
column, for **Apr, May, Jun, Jul and Aug'26** (the files
`scripts/build_dashboard_data.py` reads for `fyx_primary`; local D: drive, not in
Git).

**Exit condition.**
- `python3 scripts/mt_channel_reconciliation.py dashboard/data.js` exits **0**:
  zone rollup = MT-only total; no non-MT account in MT views.
- FY25/FY26 blocks in `data.js` byte-identical before/after.
- Then, in a separate PR, remove `continue-on-error` from that step in
  `.github/workflows/production-acceptance-gate.yml` so it blocks.

**Ready-to-send — MT Leadership**

> Subject: Decision needed — Nykaa (FSN) channel treatment for FY27 MT reporting
>
> Hi,
> Correcting the FY27 zone view removes ₹11.64 Cr of non-MT primary from MT;
> Nykaa (FSN) is ₹10.41 Cr of it. MT totals are the same whichever option you
> choose, but zone conversion changes (East 73.8% → 85.2%).
> Please confirm how Nykaa (FSN) should be reported outside MT:
> A) all under eB2B (same as the July deck; includes FSN B2C, which the feed cannot separate)
> B) split FSN B2C and Nykaa SS eB2B — needs a separated feed
> C) Nykaa (FSN) as its own channel line
> Decision owner will be recorded as "MT Leadership".
> Thanks

**Ready-to-send — MT Analytics**

> Subject: Files needed — FY27 article-wise primary, Apr–Aug'26
>
> Hi,
> To correct the MT zone totals we need the full (uncapped) article-wise primary
> files for Apr, May, Jun, Jul and Aug 2026, with the Channel column included —
> the same files used for the FY27 dashboard build. Please share them in the
> usual D: drive location.
> Thanks

**Agent prompt — once both arrive**

> CB-01 inputs have arrived: MT Leadership confirmed Option <A/B/C> (owner "MT
> Leadership", date <date>), and the FY27 article-wise primary files for Apr–Aug'26
> are in <path>. On a fresh branch from `main`: (1) snapshot the FY25/FY26 blocks
> of `dashboard/data.js`; (2) in `scripts/build_dashboard_data.py` apply
> `Channel == 'MT'` before any zone aggregation and route Nykaa (FSN) per the
> confirmed option; (3) rebuild FY27 only with the documented partial-refresh
> mode; (4) prove FY25/FY26 unchanged; (5) run `mt_channel_reconciliation.py`
> until it exits 0; (6) run the full validation (pytest, canonical gate, 44-state
> sweep, subviews, `ci_validate_datajs.py`); (7) record the decision under CB-01
> in `PROJECT_STATE.md`; (8) open a draft PR and stop. Making the CI step blocking
> is a second, separate PR.

---

## B2 — #120 → #119: historical Primary chain backfill

**What happened.** PR #119 (frozen at `51487b6`) maps ₹9,455.1997 L (18.37% of
₹51,481.65 L total Primary, Apr'25–Jul'26) to chains *provisionally*. Technical
gate passed on 2026-09-10; the owner gate is open — all 266
Distributor × Brand × Chain lines in the approval register are still blank.

**Decision (mapping business owner).** Return
`ProvisionalMapping_OwnerApproval_Apr25_Jul26.xlsx` with every line marked
Approve / Reject / Amend (Amend = give the correct chain).

**Exit condition.**
- Returned file fingerprinted (SHA-256) and kept unchanged as evidence before
  processing.
- `scripts/provisional_mapping_disposition.py` (on the #119 branch
  `feat/historical-primary-chain-backfill`, not on `main`):
  `Approved + Rejected + Amended + Pending = ₹9,455.1997 L`, with no material
  Pending (unresolved lines go back alone, not the whole workbook).
- All 16 months re-run; the `PROVISIONAL → GOVERNED + UNALLOCATED/REJECTED`
  movement shown; total Primary stays ₹51,481.65 L.
- Only then is #119 rebuilt against current `main` (it is far behind).

**Ready-to-send — mapping owner**

> Subject: Approval needed — 266 provisional Distributor × Brand × Chain mappings (Apr'25–Jul'26)
>
> Hi,
> ₹9,455.20 L of historical primary (18.4% of the total) is mapped to chains
> provisionally. Please mark each of the 266 lines in the attached register as
> Approve, Reject or Amend (for Amend, give the correct chain). A rejected line is
> never silently moved to another chain; it falls back to the validated hierarchy.
> Partial returns are fine — we will send back only the lines still open.
> Thanks

**Agent prompt — once the register returns**

> The #120 owner register has returned at <path>. Fingerprint it (SHA-256) and
> store the hash before reading it. Run `scripts/provisional_mapping_disposition.py`
> (from the #119 branch) and show Approved/Rejected/Amended/Pending against ₹9,455.1997 L. If material
> Pending remains, list only those lines for resend and stop. If fully decided:
> apply decisions once, re-run all 16 months, append the next baseline (never
> overwrite), show the movement table, prove total Primary = ₹51,481.65 L, update
> issue #120 and stop for approval before rebuilding #119 on current `main`.

---

## B3 — #229: CM2 expense load (HOLD)

**What happened.** #229 loads MT Direct debit-note claims: ₹1,274.71 L excl. GST,
FY27 Apr–Aug'26, 64 rows, reconciled to the paisa against the register's own
pivot. It stays HOLD because CM2 would read ~94% with most costs still missing.

**Decisions / inputs.**

| # | Question | Owner |
|---|---|---|
| 1 | Show "Expenses loaded: MT Direct DN claims only" on the P&L tab before any rebuild? (recommended) | MT Leadership |
| 2 | Nykaa SS (FSN) claims ₹206.04 L — load once B1 is decided, or keep out? | MT Leadership (follows B1) |
| 3 | Tnsi Retail Pvt Ltd (customer 1100027, ₹5.20 L) — which chain? | MT Ops |
| 4 | Full July and August 2026 DN register (Jul ₹245.95 L, Aug ₹103.57 L vs ₹315–431 L/month in Apr–Jun) | Finance |
| 5 | Scope of CM2 for FY27: are indirect (distributor) claims, field force, COGS and logistics in or out, and if in, which source? | Finance |

**Exit condition.** Rebuilt on a fresh branch from current `main` (the PR is
behind); expense coverage is visible on the dashboard; FM-14 double-count guard
holds (no Aug'26 MT National Provision for the same chain/month/head); all
checks green; FY25/FY26 unchanged.

**Ready-to-send — Finance**

> Subject: CM2 — inputs needed before MT Direct claims go live
>
> Hi,
> MT Direct debit-note claims for Apr–Aug'26 (₹1,274.71 L excl. GST) are ready to
> load. Before we switch CM2 on we need: (1) the complete July and August 2026 DN
> register — current totals look partial; (2) confirmation of which other costs
> belong in FY27 CM2 (indirect claims, field force, COGS, logistics) and their
> source. Until then CM2 will be labelled as "MT Direct DN claims only".
> Thanks

**Agent prompt — once inputs arrive**

> #229 inputs have arrived: <list>. On a fresh branch from `main`, rebuild the
> MT Direct DN load with `scripts/ingest_mt_direct_dn.py` (brought over from the
> #229 branch `claude/mt-direct-dn-expense-input`) against the full
> register, apply the confirmed Tnsi chain and Nykaa SS treatment, add the P&L
> expense-coverage label, keep the FM-14 guard, run all validation, and open a
> draft PR superseding #229. Do not rebuild `data.js` in the same PR.

---

## B4 — Power BI P&L assumptions, Jun–Aug'26

**What we need (Finance).** Approved Gross Margin %, Trade Spend %, Visibility
and Scheme Spend rows for Jun, Jul and Aug 2026 in
`PowerBI/SeedData/Masters/AssumptionTable.csv`. Real Primary/Offtake already
exist for those months; only the assumptions are missing. Do not estimate or
interpolate.

**Exit condition.** `scripts/check_assumption_coverage.py` passes and the
Assumption Coverage Gate no longer reports `BLOCKED_FINANCE_INPUT`.

**Ready-to-send — Finance**

> Subject: Approved P&L assumptions needed — Jun, Jul, Aug 2026
>
> Hi,
> The Power BI trade P&L needs your approved Gross Margin %, Trade Spend %,
> Visibility and Scheme Spend for June, July and August 2026. Sales data for
> these months is already in; only the assumption rows are missing. We will not
> estimate them.
> Thanks

**Agent prompt.** "Finance-approved AssumptionTable rows for Jun–Aug'26 are at
<path> (approval reference <ref>). Append them to
`PowerBI/SeedData/Masters/AssumptionTable.csv` without changing existing rows,
run `scripts/check_assumption_coverage.py` and the gate, open a draft PR and stop."

---

## B5 — Power BI Desktop runtime checks

CI checks the structure of the DAX and Power Query; only Power BI Desktop can run
them. Two runs on the Windows machine:

| Check | File | How | Expected |
|---|---|---|---|
| CM2 Case 1 | `tests/powerbi/cm2_availability_cases.dax` | DAX Studio (or DAX query view) on the Desktop model; run the CASE 1 block alone | RowsLoaded, ExpenseLoaded, CM2, CM2Pct = BLANK; NSV = a real number |
| FY parser | `tests/powerbi/pq39_fy_parser_cases.pq` | Transform data → New Source → Blank Query → Advanced Editor → paste; delete the query afterwards | `Failures` step returns **0 rows** |

**Exit condition.** Both as expected; result (screenshot or copied output) noted
under CB in `PROJECT_STATE.md`. Cases 2–4 of the CM2 file wait for B3 data.

---

## B6 — Incentive V1 business decisions

Code foundation exists; payout is blocked on decisions only. Values are from
`PROJECT_STATE.md` "Next Approved Task"; the working decision pack is regenerated
locally (not in Git).

| # | Decision | Owner |
|---|---|---|
| a | Are North and Central H1-only? (~₹5,091.77 L) | MT Leadership |
| b | 5 accounts with no target row (~₹2,598.18 L); are 445 D-Mart stores without WoA inside the measurement scope? (₹7,535.62 L of actuals) | MT Leadership |
| c | ₹2,456.83 L of the target gap is explained by nothing | Finance |
| d | 28 WoA signatures + 3 exceptions | MT Ops |
| e | 9 unpayable grades (5 `#N/A`, 4 blank) | HR |
| f | Target basis: Primary or Offtake; C1–C6; caps; proration | MT Leadership + Finance |

**Exit condition.** Every decision recorded with its owner role. **No incentive
payout is calculated until then**, and NPD, OSA/OOS, profitability, persona
reporting and the Power BI incentive dashboard stay gated.

---

## After the blockers: one delta-certification

Not a rebuild. Re-run only what the cleared blockers touched: the affected
reconciliation, canonical financial gate, Power BI validation, browser sweep,
generated-file drift checks and open PR/issue disposition. Update
`PROJECT_STATE.md` once. Move beyond READY_WITH_GOVERNED_BLOCKERS only if no
blocker above remains open.
