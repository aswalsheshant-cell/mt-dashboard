# Playbooks: strict Finance gate, and a month with no Primary file

Two situations that recur every month. For each: what the agent sees, what a person
actually does, what the agent checks before it accepts the result, and what it must not do.

Run first: `python scripts/finance_input_readiness.py` (read-only, exit 3 while anything is open).

---

## Playbook A - "AssumptionTable missing or unapproved months" (Finance gate red)

**What the agent sees**
`check_assumption_coverage.py` prints `BLOCKED_FINANCE_INPUT: AssumptionTable missing Jun'26...` and/or
`UNAPPROVED (no 'Approved: <reference>' in Remarks)`. The CI check "Assumption Coverage Gate" is red.

**Why it is correct that it is red**
The P&L reads Gross Margin %, Trade Spend % and spend heads from this table. Without a Finance row the
margin would be a guess (an earlier version silently used 50% GM / 0% trade spend). The gate exists so that
cannot reach a report. Red means "waiting for Finance", not "broken".

**What a person does (owner: Finance; helper: MT Channel Analyst Lead)**
1. Analyst runs `python scripts/finance_input_readiness.py --write-request exports/Finance_Assumption_Request.csv`.
   This gives a sheet with the missing months and every value blank.
2. Analyst sends it to the Finance owner with the short message in `decision-pack-template.md`.
3. Finance fills for each month: Gross Margin %, Trade Spend %, Visibility, Scheme, Other spend,
   Contribution Margin % (their numbers, from their books), and types their own approval reference
   (mail subject, ticket or memo ID plus date) in Remarks as `Approved: <reference> <date>`.
4. Finance returns the sheet. Analyst pastes the rows into `PowerBI/SeedData/Masters/AssumptionTable.csv`
   (add rows, keep existing rows, show the diff).
5. For Apr'26 and May'26 (present but "Default portfolio assumption"): Finance either confirms them and gives a
   reference, or sends corrected rows. Until then they stay UNAPPROVED.
6. Re-run the gate. Green = every required month has an approved ALL/ALL/ALL row.

**What the agent checks before accepting returned rows**
- Four proofs present (decision, named approver, date, reference) and scope matches the month.
- The reference is a real-looking ID, not `<ref>`, `TBD`, `pending`, or our own text.
- Percentages are fractions in the same unit as existing rows (0.52, not 52); GM% > CM% > 0 sanity; trade
  spend not negative.
- No month was copied from another month or from the portfolio default. If a row equals the default and
  carries no new reference, treat it as UNAPPROVED.
- After applying: `check_assumption_coverage.py` exits 0, and the pinned gap tests are updated in the same
  change (`tests/test_assumption_coverage_gate.py` names the documented gap months).

**What the agent must not do**
- Do not invent, interpolate, roll forward or "reasonably assume" any value.
- Do not type `Approved:` into Remarks itself. (The gate only looks for the words, so a placeholder would pass
  falsely. The request sheet therefore keeps Remarks blank.)
- Do not relax, skip or `continue-on-error` the gate to turn CI green.
- Do not treat "the user said ok" as Finance's approval. Record the user's name, and keep the Finance
  confirmation open.

**Meanwhile**
The dashboard keeps showing Primary, Offtake and claims. P&L margin for the open months shows as pending
Finance, not a number. PRs can still merge on the owner's explicit decision, noting the red gate in the PR text.

---

## Playbook B - "Primary for the latest Offtake month is not loaded" (for example Sep'26)

**What the agent sees**
Offtake has the month (for example offtake_store_article_Sep_26.csv) but
`PowerBI/RawDataFolders/Primary_Article_Monthly/primary_article_Sep_26.csv` does not exist. The dashboard
Primary vs Offtake view cannot compare that month; the exploratory Offtake card says Primary is not loaded.

**Why it is correct to leave it empty**
Primary is SAP billing. It cannot be estimated from Offtake or Distributor Secondary; mixing the measures
is the error the project guards against. The FY27 Primary total must stay at the last loaded month.

**What a person does (owner: whoever pulls SAP billing, usually the MT Analyst Lead; Finance only if the
billing extract needs sign-off)**
1. Pull the SAP billing extract for the month (all MT invoices, invoice date inside the month), the same
   report used for Aug'26 (53 raw SAP columns).
2. Drop it in `data/monthly/` (not in Git) and map it to the 24-column Primary schema with the Aug'26 ingest
   script pattern (`scripts/ingest_aug26_primary.py`; copy its column mapping for the new month).
   Output name: primary_article_Sep_26.csv. Month label `Sep'26`, FY `FY27`.
3. Check totals against the SAP source: row count and NSV must match exactly after mapping.
4. Rebuild the Primary block: `python scripts/build_dashboard_data.py --detail-only --detail-max-rows 0 --src <dir> --out dashboard/data.js`
   (uncapped on purpose; the default 40,000 row cap silently drops detail coverage).
5. Run `scripts/ci_validate_datajs.py`, the 44-state sweep, and diff FY25 / FY26 blocks (must be unchanged).
6. Raw monthly files stay out of Git (restricted source policy); only `data.js` and small seeds are committed.
7. Update the Primary row in `docs/DATA_AVAILABILITY_MATRIX.md` and the month note in
   `config/data_source_registry.yml`; pin the new FY27 Primary total in the tests that carry it.

**What the agent checks before accepting the file**
`finance_input_readiness.py` shows Primary status READY: same columns as the last loaded month, only one
Month value, FY27 tag, invoice dates inside the month, row count and NSV printed. Then the reconciliation
steps above; hand the number tie-out to `sales-data-reconciliation`.

**What the agent must not do**
- Do not estimate Sep'26 Primary (not from Offtake, not from an L3M average, not from Secondary).
- Do not put the file in a different folder or rename columns to make the check pass.
- Do not apply Reliance Brand Counter isolation to Primary (Offtake only).
- Do not commit the raw CSV.

**Meanwhile**
Primary vs Offtake keeps comparing only the months both have. The Sep'26 Offtake and its exploratory estimate
remain labelled as Offtake.

---

## Reporting both to leadership (plain wording)

- "P&L margin for Jun to Sep'26 is waiting for Finance's approved assumptions. We have sent the request sheet.
  No margin is shown for those months until it is back."
- "Sep'26 Primary billing is not loaded yet; we need the SAP billing extract for September. Offtake for September
  is loaded and shown separately."
