# Task 5 report — local review checkpoint only

Base: e18b38c8109a090fd86ae7654a23cb56875bb137. Date: 2026-10-03.
Status: STRUCTURAL_DRAFT; Desktop open/refresh NOT VERIFIED.
B5: BLOCKED_PENDING_DESKTOP_EVIDENCE. No push, merge, production publish or signed
publication. This local checkpoint is not Task 5 release acceptance.

## RED / GREEN

Test written first: tests/test_powerbi_cm2_views_structure.py.
Command: `python -m pytest tests/test_powerbi_cm2_views_structure.py -q -p no:cacheprovider`.
Initial run: 4 failures (missing fact/month/descriptor and an encoding issue in
test reading the existing Unicode measures). Corrected test reads to UTF-8,
reran before implementation: 4 expected missing-model/measure failures.
After implementation: 4 passed.
Final focused regression command:
`python -m pytest tests/test_powerbi_cm2_views_structure.py tests/test_powerbi_unique_measure_names.py tests/test_powerbi_rolling_average.py tests/test_powerbi_cm2_truthful.py -q -p no:cacheprovider`.
Result: 33 passed. `git diff --check` passed (only CRLF conversion notices).
These are textual structural tests, not an M/DAX engine or runtime parity proof.

## Model/page work

Added v2 aggregate Fact_CM2 import (all 42 contract fields), local RepoRoot
parameter, unique month dimension and explicit one-to-many relationship.
Sales/tax/coverage measures require one alternative view; claim/BA exceptions
retain signs, source status, tax QC and no fabricated denominator. Matched claim
bridge intersects identical keys with one denominator. Modeled margin is BLANK.
Added PBIR CM2 page, actual bound table/slicer visuals, kept Finance sample
measure/grouping meaning separately and archived original simplified JSON.
Added missing semantic-model descriptor and database file; moved relationships
out of model.tmdl. Added missing base SUM measures referenced by legacy Finance
sample. Docs describe installed draft versus legacy manual kits.

## Desktop evidence and blockers

Read computer-use SKILL.md, guidance.md, confirmations.md and api.md. All UI
operations used @oai/sky in node_repl. No shell-through-UI, authentication or
security settings actions. Selected returned installed Store Desktop window
3541802 (Untitled - Power BI Desktop). Native Open dialog was observed.

An initial input encountered `point (536, 717) is over ChatGPT.exe "Chrome Legacy
Window", not target window PBIDesktop.exe "Untitled - Power BI Desktop"`.
Activation and fresh observation retry succeeded. Subsequent native file open
actually reached Desktop's project parser; this was not an unavailable engine.

1. Desktop rejected original PBIP: `Property 'enableAutoAuth' has not been defined
and the schema does not allow additional properties. Path 'settings.enableAutoAuth',
line 11, position 21.` Replaced with supported enableAutoRecovery setting.
2. Next open passed that boundary but returned: `There's a problem with the
definition content in your Power BI Project. Property 'description' is unknown
and is not expected in the situation it appears.` Removed inherited ///
relationship comments (TMDL description syntax on a relationship). This suspected
fix has NOT been runtime confirmed.
3. The next native Open confirmation was blocked by automatic approval review:
`This action was rejected due to unacceptable risk. Reason: The Desktop open
route has repeatedly failed and the task instructions require stopping and
reporting the exact blocker rather than retrying the same blocked UI action.`
Stopped UI input immediately. Did not bypass via another launcher or API.

The prior two parser dialogs were displayed in tool screenshots. No successful
project page rendering, refresh, relationship inspection, Apr/Aug values,
mixed GST, negative credit or matched-bridge screenshots were obtained. The final
project still needs Desktop re-open approval, correction of any further parser
issues, source refresh and governed evidence. No data refresh was attempted.
No real-source CSV was generated: existing Task 3 scratch is v1 and unsuitable.
The production HTML payload was not regenerated. Workbook and source rows were
not changed or staged. RepoRoot deliberately remains a local setup placeholder.
The legacy Finance sample still requires its separate server CSV sources for a
whole-model refresh; governed CM2 itself uses only the local aggregate path.

## Self-review and follow-up gate

Static source contract, alternative cuts, signed fields, month relationship,
blank modeled margin and real PBIR page references are present. Avoid claiming
Desktop compatibility just because JSON/TMDL looks valid. Generated page layout
and DAX require engine verification; source-backed CSV v2 generation and source
total reconciliation remain pending before runtime parity evidence. Local review
checkpoint only is authorized; no signed GitHub publication before opening.

To resume Desktop UI after the automatic review rejection, user approval is
required for reopening this local PBIP to continue parser validation. Approval
is requested because automatic review blocked the action, not because file
editing or static validation requires permission.
