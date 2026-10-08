# Claude FY branch review — 2026-10-03

**Reviewed branch:** `claude/youthful-carson-vzv9hh` at `853e01d1d450dab11e4ce34e7c2c4ebfd96d8132`, four commits ahead of main `84864ce4076164aee5cbc79493bb7f086743eb90`, zero behind at review time. The attached Claude session stopped during the Offtake unit investigation. This branch has no PR and is not approved for a wholesale merge.

| Commit | Decision | Reason / action |
|---|---|---|
| [`69b2583`](https://github.com/aswalsheshant-cell/mt-dashboard/commit/69b2583224486d186c8e74f0e97e1ea7a00bb3ec) | **Partially adopted** | The monthly Fact Primary Article is the loaded Primary source; the weekly Fact Primary Sales is deferred. Governed Offtake belongs in the gap and target basis. Date references in secondary DAX must name `Date Table`. These focused changes were independently tested in draft PR #294. The commit's other Data Quality edits need a separate baseline check. |
| [`7584a42`](https://github.com/aswalsheshant-cell/mt-dashboard/commit/7584a424f436139f9529e5b3d4455b2be732a07a) | **Hold for separate review** | Adds deployment and broad CI changes plus a Primary Reliance guard. Valuable, but unrelated to the proven Offtake import conversion; test the deploy/CI behavior on its own branch before adoption. Primary must stay gross; #294 leaves its source rows unchanged. |
| [`e93415d`](https://github.com/aswalsheshant-cell/mt-dashboard/commit/e93415d604e57d6382f8adfe7c75460528df4c2e) | **Revise** | FY28-ready gap output is useful, but its `[Q1 FY27 Secondary NSV Lakh]` filter changes from a fixed FY27 period to the moving `[TY FY Label]`. That would make a measure named FY27 follow a future FY. Keep the fixed-period scorecard fixed and review the dynamic gap separately with FY boundary cases. |
| [`853e01d`](https://github.com/aswalsheshant-cell/mt-dashboard/commit/853e01d1d450dab11e4ce34e7c2c4ebfd96d8132) | **Partially adopted; remainder revise** | `fnFYLabel` and Offtake FY derivation were adopted in #294, with explicit parsing of real `Month` values (`Apr'26`, Excel serial `46113.0`, bare `Jul`/`Aug`) and a fail-closed filename cross-check. The branch's original Offtake parser still assumed a quote and would not handle those committed rows. Its FY validator skips month labels it cannot parse, so a clean result would not cover those rows. Review the other five Power Query fact changes and HTML FY/Month UI with independent Desktop/browser evidence before porting them. |

## Checks and limits

- #294's source audit reads all 25 committed monthly/snapshot CSVs and preserves their SHA-256, row count and signed total. The source-to-HTML governed Offtake check matches Apr–Aug FY27 within 0.01 lakh; [reconciliation record](dashboard_unit_reconciliation_2026-10-03.md).
- QuickSetup in #294 is generated from its own changed query/measure sources. The Claude branch's consolidated files must not be copied over it.
- The FY filter test in the Claude branch hardcodes the current FY27 Apr–Aug months; add a later FY fixture and missing-month/orphan checks before calling the UI dynamic.
- No live Power BI Desktop refresh has yet proved the new model values. B5 remains blocked, and PR #119 / PR #267 retain their current holds.

**Next action for the held FY work:** create a separate draft correctness PR from current main after #294 is reviewed; port each relevant change with a failing regression first, then verify FY transition, null/orphan months, and generated QuickSetup. Do not merge the Claude branch as a unit.
