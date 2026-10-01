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
| B1 | CB-01 — non-MT sales inside MT zone totals (₹11.64 Cr) | MT Leadership | B1a: OK to show Nykaa as pending (inputs already in repo); B1b: Nykaa option | `mt_channel_reconciliation.py` exits 0; FY25/FY26 unchanged; CI step made blocking |
| B2 | #120 → #119 — historical Primary chain backfill | Business owner of the mapping | 266-line approval register returned, every line decided | Decisions reconcile to ₹9,455.1997 L with no material Pending; 16/16 months reconcile; total ₹51,481.65 L unchanged |
| B3 | CM2 expense scope — MT Direct DN loaded by #229 (merged `3aa6895`, Jul/Aug PARTIAL); distributor claims #267 (HOLD; rebuild of #252, which is closed) and other cost heads not loaded | Finance + MT Leadership | Full Jul/Aug DN register; FY27 CM2 scope (indirect claims, field force, COGS, logistics); distributor-claim monthly timing and Direct DN overlap rule; Nykaa SS after B1 | Each in-scope head loaded from an approved source or named as not loaded; no quarterly claim spread to months without an approved basis; FY25/FY26 unchanged; all checks green |
| B4 | Power BI P&L assumptions, Apr–Aug'26 (Apr/May present but unapproved; Jun–Aug missing) | Finance | Approved AssumptionTable rows | Assumption Coverage Gate passes (no `BLOCKED_FINANCE_INPUT`) |
| B5 | Power BI Desktop runtime checks — `BLOCKED_PENDING_DESKTOP_EVIDENCE` | MT Channel Analyst Lead (Windows) | One Desktop session per `docs/evidence/B5_RUN_SHEET.md` | FY parser `Failures` = 0 rows; CM2 Cases 2–8 on the current model as expected (Case 5 `Leak` = 0, Case 7 `BrandLeak` = `CategoryLeak` = 0, Case 8 `Violations` = 0); L3M/L6M rolling averages `Mismatches` = 0; durable evidence file |
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

**Split into two parts (2026-09-27).** B1 bundles two different questions:

- **B1a — what belongs in MT** (technical): answered by the `Channel` field in the
  source files. It does not depend on the Nykaa choice, because MT totals are the
  same under A, B and C.
- **B1b — where Nykaa is reported outside MT** (reporting policy): the A/B/C
  choice above.

B1a can close on the files alone **if MT Leadership agrees** that, until B1b is
decided, Nykaa (FSN) is shown outside MT as `PENDING_DECISION` rather than under
eB2B. That agreement is itself a question in the MT Leadership email below; the
agent never picks a Nykaa bucket on its own.

**Data — already in the repo (found 2026-09-27).** The FY27 article-wise primary
for **Apr–Aug'26** is tracked at
`PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_{Mon}_26.csv`
(committed 2026-09-14; `detail_records_real()` reads these when no `.xlsb` is in
`--src`). Every required column is present, `Channel` is filled on every row, and
each month ties exactly to `detail_meta.fyx_primary` (total ₹22,239.59 L). **No
file request to MT Analytics is needed for B1a.** The earlier note that the source
was "absent from the working tree" was out of date (FM-09 pattern).

**Input contract (checked before any rebuild).** A file that fails a column is
not used, and the gap is reported, never filled:

| Month | Expected file | Present | Channel column | Rows | SHA-256 | Accepted |
|---|---|---|---|---|---|---|
| Apr'26 | `primary_article_Apr_26.csv` | ✅ | ✅ 0 blank | 30,757 | `f63066b9…33e45a2` | ✅ ₹5,076.86 L = fyx |
| May'26 | `primary_article_May_26.csv` | ✅ | ✅ 0 blank | 19,399 | `0c10f2d6…cac95c6` | ✅ ₹4,415.74 L = fyx |
| Jun'26 | `primary_article_Jun_26.csv` | ✅ | ✅ 0 blank | 23,192 | `1de0ad86…d516d121d` | ✅ ₹4,167.38 L = fyx |
| Jul'26 | `primary_article_Jul_26.csv` | ✅ | ✅ 0 blank | 31,355 | `497e55d2…1720545e` | ✅ ₹4,921.31 L = fyx |
| Aug'26 | `primary_article_Aug_26.csv` | ✅ | ✅ 0 blank | 19,070 | `959124f7…5f3b686` | ✅ ₹3,658.30 L = fyx |

Checked 2026-09-27 on `main` `b9dcdc9`. Full SHA-256 values are in the commit that
filled this table. Channel split (₹ L): MT 21,075.63 · EB2B 1,080.68 · SIS 83.27 —
the same split `mt_channel_reconciliation.py` reports.

Accepted = present, has `Channel`, parses, month matches THE ONE FY RULE (FY27),
and its all-channel NSV ties to `detail_meta.fyx_primary` for that month. The
filled table goes in the B1 PR description, so next month's refresh has the same
check.

**Rebuild dry-run on `main` `374de1f` (2026-09-27, isolated worktree, nothing
committed).** Before any B1a change, `--detail-only` was run from the tracked files
to prove the baseline reproduces:

| Run | Result vs committed `data.js` |
|---|---|
| `--src Primary_Article_Monthly` (default row cap) | `detail_records` 160,834 → 40,000, coverage 100% → 92.9% (the FM-03 trap). Every other block, incl. `fyx_primary` FY27 and all FY25/FY26 blocks, identical |
| same + `--detail-max-rows 0` | 160,834 rows, 100% coverage; everything identical **except** `alloc.governance` |
| same, `--src` = primary + `Offtake_Monthly/offtake_store_article_*_26.csv` | same single difference |

The one difference is labelling only, no amounts: 12 distributor-allocation rows
(₹12.13 L) read `Article_Not_Listed` 7 / `Brand_Not_Listed` 5 in the committed file
and `Not_Eligible` 12 (`flagged_rows` 0 → 12) on rebuild. Those tiers depend on the
offtake universe `build_offtake_universe(src)` reads; the 2026-09-25 build (#209) saw a
different set. The B1a PR must: run with `--detail-max-rows 0`, show this
`alloc.governance` change separately from the MT-only zone change, and not present
it as part of the channel fix.

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
> Two questions:
> 1) May we correct the MT zone totals now, with Nykaa (FSN) shown outside MT as
>    "pending decision" until you choose below? (MT totals do not depend on the choice.)
> 2) How should Nykaa (FSN) be reported outside MT?
> A) all under eB2B (same as the July deck; includes FSN B2C, which the feed cannot separate)
> B) split FSN B2C and Nykaa SS eB2B — needs a separated feed
> C) Nykaa (FSN) as its own channel line
> Decision owner will be recorded as "MT Leadership".
> Thanks

**MT Analytics — no request needed.** The files are already in the repo (above).
Ask only if a month's source is re-issued or corrected.

**Agent prompt — once both arrive**

> CB-01 inputs have arrived: MT Leadership confirmed Option <A/B/C> — or agreed
> that Nykaa (FSN) shows as PENDING_DECISION outside MT until B1b is decided —
> (owner "MT Leadership", date <date>), and the FY27 article-wise primary files for Apr–Aug'26
> are in `PowerBI/RawDataFolders/Primary_Article_Monthly/` (already tracked). On a fresh branch from `main`: (1) snapshot the FY25/FY26 blocks
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

**Make the review easy, not different.** The register already sent stays the
record. If the owner wants help, give a read-only companion view generated from
the same file: lines sorted by value (largest first, showing how many lines cover
80% of ₹9,455.20 L), with distributor, brand, proposed chain, amount and evidence
per line, and only three allowed answers — Approve / Reject / Amend. The
`mapping-approval-governor` skill can group lines that share one rule, so the
owner can approve a rule once instead of line by line; it never fills in an
answer. Partial returns are accepted; only the open lines go back.

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

## B3 — CM2 expense scope (MT Direct DN merged via #229; distributor claims #267 on HOLD)

**Finance decision 2026-10-01 (DA).** A1: distributor claims and MT Direct DN are
**additive**. A2: include distributor claims in monthly and quarterly CM2.
Quarterly Q1 ₹449.77 L stays ACTUAL. Monthly is split per Chain × Expense Head by
the chain's Apr/May/Jun distributor-secondary share (ALLOCATED_PROVISIONAL), with
each line reconciling to its Q1 claim and no equal ÷3 split. #267 now carries
that allocation file. Wiring it into dashboard / Power BI CM2 is a separate PR.
Still open for B3: A3 (Jul/Aug DN register complete?) and A4 (other cost heads).

**Current state (2026-09-30).** #229 merged on 2026-09-27 (`3aa6895`) with the
owner decisions of that day: 64 MT Direct DN rows, ₹1,274.71 L excl. GST,
Apr–Aug'26; Nykaa (FSN) excluded until CB-01; Tnsi Retail (1100027) = WH-Smith;
Jul/Aug marked PARTIAL; the P&L tab names the loaded heads and the cost buckets
not loaded. What remains open is Finance's, below (questions 1 and 3 are
answered). Distributor claims are PR #267: a Q1 FY27 seed at Quarter × Chain ×
Expense Head (32 rows, ₹449.77 L), not in CM2, never spread into months without
real monthly data or a Finance-approved method, and overlapping MT Direct DN on
four chains (DMart, Reliance, H&G, Apollo; see the #267 PR body).
#267 rebuilt the original #252 on current `main` (same four files, seed
byte-identical); #252 was closed on 2026-09-30 as superseded, not merged,
with its branch kept as evidence. The history below is kept as written.


**What happened.** #229 loads MT Direct debit-note claims: ₹1,274.71 L excl. GST,
FY27 Apr–Aug'26, 64 rows, reconciled to the paisa against the register's own
pivot. It stays HOLD because CM2 would read ~94% with most costs still missing.

**First decision — one sentence from Finance:** *"FY27 CM2 includes ___, from
___, for ___ months."* Then fill:

| Included expense heads | Excluded heads | Source per head | Period covered | Allocation grain | Double-count rule |
|---|---|---|---|---|---|
| | | | | | |

Two valid answers: **full CM2** (wait until every in-scope head has a source) or
**partial CM2** (load what exists; the dashboard states exactly which heads are
loaded and never presents it as final margin). Missing ≠ zero and partial ≠
complete either way. #229 is rebuilt only after this is written down.

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

## B4 — Power BI P&L assumptions, Apr–Aug'26

**Current state (2026-09-30).** `scripts/check_assumption_coverage.py` exits 3: Jun, Jul, Aug'26 MISSING; Apr, May'26 PRESENT_BUT_UNAPPROVED.

**What we need (Finance).** Approved Gross Margin %, Trade Spend %, Visibility
and Scheme Spend rows for Jun, Jul and Aug 2026 in
`PowerBI/SeedData/Masters/AssumptionTable.csv`. Real Primary/Offtake already
exist for those months; only the assumptions are missing. Do not estimate or
interpolate.

**Input contract.** Rows in the file's existing columns — `Month, Chain, Brand,
Category, Gross Margin %, Trade Spend %, Visibility Spend, Scheme Spend, Other
Spend, Contribution Margin %, Remarks` — with at least one `ALL/ALL/ALL` row per
month (that is the row the gate counts), percentages as decimals (0.52 = 52%),
and the Finance approval reference and date in `Remarks`. No verbal or "rough"
figures.

**Also confirm the existing rows.** The Apr'26 and May'26 `ALL/ALL/ALL` rows on
`main` read "Default portfolio assumption - update with actuals when available"
(GM 52%, Trade Spend 8%), and the two May'26 chain rows carry no approval
reference either. Until 2026-09-27 the gate counted Apr and May as covered because of
them; it now reports them as UNAPPROVED (a month counts only when its ALL/ALL/ALL row
has `Approved: <reference>` in Remarks). Finance
should confirm them as approved or send replacements, so the gate's READY means
approved, not placeholder. They are not changed until Finance answers.

**Exit condition.** `scripts/check_assumption_coverage.py` passes and the
Assumption Coverage Gate no longer reports `BLOCKED_FINANCE_INPUT`.

**Ready-to-send — Finance**

> Subject: Approved P&L assumptions needed — Jun, Jul, Aug 2026
>
> Hi,
> The Power BI trade P&L needs your approved Gross Margin %, Trade Spend %,
> Visibility and Scheme Spend for June, July and August 2026. Sales data for
> these months is already in; only the assumption rows are missing. We will not
> estimate them. Please also confirm whether the April and May 2026 rows now in
> the file (GM 52%, Trade Spend 8%, marked "default assumption") are approved, or
> send the approved values. An approval reference per month is all we need.
> Thanks

**Agent prompt.** "Finance-approved AssumptionTable rows for Jun–Aug'26 are at
<path> (approval reference <ref>). Append them to
`PowerBI/SeedData/Masters/AssumptionTable.csv` without changing existing rows,
run `scripts/check_assumption_coverage.py` and the gate, open a draft PR and stop."

---

## B5 — Power BI Desktop runtime checks

**Status: `BLOCKED_PENDING_DESKTOP_EVIDENCE`.** CI checks the structure of the DAX
and Power Query; only Power BI Desktop can run them.

**Exit condition changed 2026-09-29 (owner decision, B5 only).** The original
condition was CM2 Case 1 plus the FY parser. Case 1 ("no expense rows, CM2
BLANK") describes the model as it was before #229 (`6b49e3a`). #229
(`3aa6895`) loaded 64 real expense rows (₹1,274.71 L, Apr–Aug 2026), so on the
current model Case 1's precondition no longer exists. The Case 1 PASS reported
on `6b49e3a` stays on record as `PASS_REPORTED_EVIDENCE_NOT_RETAINED`; it is
not re-run and not counted towards closure. B5 is now judged on the current
model:

| Check | File | Expected (from the governed test file) |
|---|---|---|
| FY parser | `tests/powerbi/pq39_fy_parser_cases.pq` | `Failures` step returns **0 rows** |
| CM2 Case 2 | `tests/powerbi/cm2_availability_cases.dax` | months with expense: `CM2 = NSV − Expense`; months without: Expense and CM2 BLANK; no `FAIL` rows |
| CM2 Case 3 | same | `Unmapped > 0`, Mapped BLANK, CM2 BLANK — or `NOT_EXERCISED` if the model has 0 unmapped rows (count recorded) |
| CM2 Case 4 | same | chains with expense: `ChainCM2 = NSV − ChainExpense`; without: both BLANK; `Violations` = 0 |
| CM2 Case 5 | same | **`Leak` = 0** |
| CM2 Case 6 | same | FY26 Expense and CM2 BLANK; FY27 Expense = mapped part of the ₹1,274.71 L load |
| CM2 Case 7 | same | **`BrandLeak` = 0** and **`CategoryLeak` = 0** |
| CM2 Case 8 | same | **`Violations` = 0** |
| Rolling averages (added 2026-10-01, owner decision, #273) | `tests/powerbi/rolling_average_cases.dax` | CASE 1 **`Mismatches` = 0**; CASE 2 L3M and L6M BLANK; CASE 3 L3M = Expected |

Step-by-step procedure, per-case PASS rules and load cross-checks:
`docs/evidence/B5_RUN_SHEET.md`.

**Exit condition.** Every check above as expected, **with durable evidence**: the
filled-in copy of `docs/evidence/B5_EVIDENCE_TEMPLATE.md` saved as
`docs/evidence/B5_powerbi_runtime_<date>.md` (commit SHA, Desktop version,
model file, expected vs actual, PASS/FAIL per case), plus a screenshot per step
attached to the B5 PR. A result reported only in chat does not close B5. Any
FAIL keeps B5 open as a defect; the expectation is never re-worded to fit a
result.

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

**One decision session, not six email threads.** Run a 30–45 minute session
with MT Leadership, Finance, MT Ops and HR. For each row show only: decision,
financial impact, options, owner, answer required. No employee names, IDs or
payout amounts go into this repo; person-level detail stays in the local working
pack. A visible BLOCKED status is safer than a polished payout on an assumed
denominator.

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
