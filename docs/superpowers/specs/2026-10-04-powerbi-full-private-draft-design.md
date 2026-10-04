# Full Power BI dashboard, private draft

**Status:** design for review. **Target:** Power BI Service, My workspace, private draft. This does not clear B5 or approve modeled CM2 for leadership use.

## Intent and current state

The user wants the overall Modern Trade dashboard in Power BI, including the HTML dashboard's main tabs and useful subviews, available remotely as a private draft. They do not want a CM2-only report presented as the overall dashboard.

The checked-in `ModernTrade_Report.pbip` on the CM2 implementation branch has only `Finance sample (legacy)` and `CM2 governed draft` pages. The `main` report has no completed PBIR page definitions. The HTML dashboard has 11 main tabs. `PowerBI/docs/PageLayouts.md` describes an older 18-page manual assembly, and the Power Query/DAX files are assembly inputs rather than a finished all-page semantic model. A two-page upload would not meet this request.

## Report coverage

Create working native Power BI pages corresponding to the following HTML tabs. Named subviews may be separate report pages or bookmarks, provided their filters persist and each view has working visuals.

| HTML tab | Required Power BI coverage | Main data dependency |
| --- | --- | --- |
| Explorer | Filterable detail table, drill path, export, source and coverage labels | Primary, offtake, shared dimensions |
| Executive Cockpit | Governed KPIs, trends, comparison, insight context | Primary, offtake, targets and approved comparisons |
| Channel Dynamics | Primary Sales; Category & Pack Mix; Reliance Brand Counter | Primary sales, article/category masters |
| Inventory Health | Offtake Velocity; Demand-Supply Gap; Store Coverage | Offtake, primary, store and inventory inputs where available |
| Demand Planning | Demand Forecast; Promotional Impact; Competitive Landscape | Forecast, promotion, market data where available |
| P&L | Expense and contribution views, including separately labeled CM2 cuts | P&L expense, claim, CM2 contract v2 |
| Comparison | FY/MoM/YoY views with comparable-period and source-coverage rules | Shared date table and source facts |
| Analytics | Growth drivers and diagnostic views; provisional observed NPI comparison is separate from confirmed NPI YoY | Sales, article history, approved NPI definitions |
| Alerts | Traceable exception/watchlist rules with source and threshold | Governed measures and data-quality checks |
| Stores | Store-level coverage and performance drill | Store mapping and offtake |
| Inventory | Available stock/supply views with clear missing-source states | Inventory and supply inputs |

An unavailable or unapproved source must produce an explicit unavailable state, not a zero, fabricated measure, or an apparently complete chart. Such a page remains **incomplete** in the coverage audit even if its navigation exists. Page names can be shortened for Power BI navigation, but the mapping must be documented in the report and verified before publication.

## Shared model and behavior

Extend the current PBIP dataset from its seven financial/CM2 tables using the repository's existing Power Query and DAX source definitions. Build shared date, article, chain, category, geography, and store dimensions and relate each fact at its real grain. Validate cardinality, active date paths, fiscal-year parsing, units, tax treatment, and filter propagation. Do not import the PBIP descriptor as data or rely on copied visual output as a data source.

Use synchronized slicers for fiscal period, chain, geography, brand, category, and article where the underlying facts support them. A slicer must not imply filtering a visual whose source lacks that dimension. Report-level tooltips or visible notes should disclose differing source coverage and partial months. Exported tables must carry units and source context.

Preserve financial source rows and B5 evidence. CM2 must retain the two workbook-aligned views: provisioned claims and recorded MT Direct debit-note claims. Keep modeled cost assumptions and unresolved Finance approval visible; never label the modeled result approved actual CM2. The observed NPI comparison remains provisional, with confirmed-launch YoY blank until its evidence criterion is met.

## Build and validation

Work on a branch derived from the CM2 implementation branch. Assemble the native model and pages in PBIP source control, using the older `PageLayouts.md` as a visual reference but the 11-tab mapping above as the release scope. Build pages in source groups so each can be reconciled before the next group is added.

For every page/subview, verify in Power BI Desktop that it opens without definition errors, refreshes from its intended source, returns nonblank values where source rows exist, applies expected slicers, and reconciles key totals to the governed HTML/source calculation for the same filters and period. Capture the compared values, source revision, date, and any permitted variance. Test export and a cross-page filter scenario. Do not mark pages complete from static parsing alone.

Run the governed B5 Desktop cases independently. B5 remains `BLOCKED_PENDING_DESKTOP_EVIDENCE` until the required engine results and human screenshots meet its exit rules. A private draft can carry the explicit B5 limitation; it must not be described as production accepted.

## Remote publication

Publish the Desktop-validated PBIX to **My workspace** as a **private draft**. A draft may show an explicitly incomplete source page, but it must carry a visible page-coverage status and must not be called the completed overall dashboard until every required page is functional. Confirm the signed-in account, workspace, report name, dataset, page list, and service rendering before giving the user the link. Do not share it, create an app, promote it, or change production/PR merge state. A report is not considered remotely deployed merely because a local PBIP opens.

The initial service dataset may be a manually refreshed import snapshot. Before claiming automatic refresh, move source files to an authorized cloud source or configure an approved on-premises gateway and credentials; verify a scheduled refresh in the Service. The existing repository-local paths alone cannot establish remote refresh. If publication is blocked by Power BI license, tenant policy, account access, or missing source credentials, record the exact Service message and stop at the private local draft rather than claim success.

## Acceptance criteria

1. All 11 main tabs and every named subview above have working report navigation. Full-dashboard completion requires source-backed visuals on each; any unavailable-source state is recorded as incomplete in the private draft.
2. Shared filters, fiscal periods, units, and partial-month labels behave correctly across their supported pages.
3. Page-level key totals reconcile to the governed source and comparison basis; validation evidence identifies any unresolved variance.
4. Provisional NPI and CM2 claims/assumption labels remain visible; B5 status remains honest.
5. A private report in My workspace is opened and checked after publication, with a user-accessible link and a stated refresh mode. No broader audience receives it.
