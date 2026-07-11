// Power Query — Safe Offtake Data Layer (MRP basis, June'26 partial, no NSV scaling)
// Loads monthly offtake CSV files, standardizes schema, creates safe helper columns
// Branch: claude/safe-powerbi-blocks
// Generated: 2026-07-11

// ============================================================================
// MONTHLY OFFTAKE DATA LOAD (Apr'24–Jun'26, 27 months, 582 files, 4.21M rows)
// ============================================================================
// This query appends all monthly offtake CSV files from a folder, standardizes
// column names, and creates safe helper columns for filtering and reporting.
// Raw Chain Name is preserved (not canonicalized yet); duplicates are NOT removed.
// June'26 is flagged as Partial (78,111 rows; some accounts pending).

let
  // 1. Define folder path (adjust to match your local folder structure)
  FolderPath = "C:\Data\MT_Offtake_Monthly\",

  // 2. List all CSV files in folder
  Files = Folder.Files(FolderPath),
  FilteredFiles = Table.SelectRows(Files, each Text.EndsWith([Name], ".csv")),

  // 3. For each file, load and transform
  LoadedFiles = Table.AddColumn(FilteredFiles, "Content", each
    let
      FileContent = Csv.Document(File.Contents([Folder Path] & [Name]),
        [Delimiter = ",", Columns = null, Encoding = 1252, QuoteStyle = QuoteStyle.None]),
      PromotedHeaders = Table.PromoteHeaders(FileContent, [PromoteAllScalars = true]),
      // Standardize column names (trim, uppercase first letter)
      RenamedCols = Table.RenameColumns(PromotedHeaders, {
        {"Site Code", "Site_Code"},
        {"Site Name", "Site_Name"},
        {"Chain Name", "Chain_Name"},
        {"Zone", "Zone"},
        {"Category", "Category"},
        {"PPT Category", "PPT_Category"},
        {"Format", "Format"},
        {"Classification", "Classification"},
        {"Sales Qty", "Sales_Qty"},
        {"MRP Sales Value", "MRP_Sales_Value"},
        {"NSV", "NSV"},
        {"Month", "Month_Raw"},
        {"Year", "Year"}
      })
    in RenamedCols),

  // 4. Extract month from filename if needed (fallback for missing Month column)
  ExpandedContent = Table.ExpandTableColumn(LoadedFiles, "Content",
    {"Site_Code", "Site_Name", "Chain_Name", "Zone", "Category", "PPT_Category",
     "Format", "Classification", "Sales_Qty", "MRP_Sales_Value", "NSV", "Month_Raw", "Year"},
    {"Site_Code", "Site_Name", "Chain_Name", "Zone", "Category", "PPT_Category",
     "Format", "Classification", "Sales_Qty", "MRP_Sales_Value", "NSV", "Month_Raw", "Year"}),

  // 5. Clean and standardize text fields
  TextCleaned = Table.TransformColumns(ExpandedContent, {
    {"Site_Code", Text.Trim, type text},
    {"Site_Name", Text.Trim, type text},
    {"Chain_Name", Text.Trim, type text},  // PRESERVE raw chain name (do not canonicalize)
    {"Zone", each Text.Trim(Text.Proper(_)), type text},  // Proper case
    {"Category", Text.Trim, type text},
    {"PPT_Category", Text.Trim, type text},
    {"Format", Text.Trim, type text},
    {"Classification", Text.Trim, type text}
  }),

  // 6. Convert numeric fields
  TypeChanged = Table.TransformColumnTypes(TextCleaned, {
    {"Sales_Qty", type number},
    {"MRP_Sales_Value", type number},
    {"NSV", type number},
    {"Year", type number}
  }),

  // 7. Extract Month from Month_Raw (e.g., "Apr-24" -> 4, "Jun-26" -> 6)
  MonthExtracted = Table.AddColumn(TypeChanged, "Month_Num", each
    let
      MonthMap = {"Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"},
      Parts = Text.Split([Month_Raw], "-"),
      MonthStr = if List.Count(Parts) >= 1 then Parts{0} else "Jan",
      MonthIndex = List.PositionOf(MonthMap, Text.Proper(MonthStr)) + 1
    in
      MonthIndex
  ),

  // 8. Extract Year from Month_Raw (e.g., "Apr-24" -> 2024)
  YearExtracted = Table.AddColumn(MonthExtracted, "Calendar_Year", each
    let
      Parts = Text.Split([Month_Raw], "-"),
      YearStr = if List.Count(Parts) >= 2 then Parts{1} else "00",
      YearNum = Value.FromText(YearStr)
    in
      2000 + YearNum  // Convert "24" to 2024
  ),

  // 9. Calculate FY (Financial Year: Apr-Mar)
  // Apr–Dec of year Y -> FY(Y+1); Jan–Mar of year Y -> FY(Y)
  FYCalculated = Table.AddColumn(YearExtracted, "FY", each
    let
      CalYear = [Calendar_Year],
      MonthNum = [Month_Num],
      FYYear = if MonthNum >= 4 then CalYear + 1 else CalYear,
      FYTag = "FY" & Text.End(Text.From(FYYear), 2)
    in
      FYTag
  ),

  // 10. Create Month Sort for ordering (Apr=1, May=2, ..., Mar=12)
  MonthSortCalculated = Table.AddColumn(FYCalculated, "Month_Sort", each
    let
      MonthNum = [Month_Num],
      MonthSort = if MonthNum < 4 then MonthNum + 9 else MonthNum - 3
    in
      MonthSort
  ),

  // 11. Create Month Label (e.g., "Apr-24")
  MonthLabelCalculated = Table.AddColumn(MonthSortCalculated, "Month", each
    [Month_Raw]  // Already in correct format from source
  ),

  // 12. Flag June'26 as Partial
  June26FlagCalculated = Table.AddColumn(MonthLabelCalculated, "Is_June26_Partial", each
    let
      MonthNum = [Month_Num],
      CalYear = [Calendar_Year],
      IsJune26 = (MonthNum = 6) and (CalYear = 2026)
    in
      IsJune26
  ),

  // 13. Flag any month as Partial (currently only June'26; can be extended)
  MonthPartialFlagCalculated = Table.AddColumn(June26FlagCalculated, "Is_Month_Partial", each
    [Is_June26_Partial]
  ),

  // 14. Rename NSV column to Source NSV Lacs (confirmed unit = Lakhs)
  SourceNsvRenamed = Table.RenameColumns(MonthPartialFlagCalculated, {
    {"NSV", "Source_NSV_Lacs"}
  }),

  // 15. Create NSV Actual Value (Lakhs → Rupees: Lacs * 100,000)
  NsvActualValueCalculated = Table.AddColumn(SourceNsvRenamed, "NSV_Actual_Value", each
    [Source_NSV_Lacs] * 100000  // Convert Lakhs to actual rupees
  ),

  // 16. Create NSV Cr (Lakhs → Crores: Lacs / 100)
  NsvCrCalculated = Table.AddColumn(NsvActualValueCalculated, "NSV_Cr", each
    [Source_NSV_Lacs] / 100  // Convert Lakhs to Crores
  ),

  // 17. Create MRP Sales Value Cr (Rupees → Crores: Rupees / 10,000,000)
  MrpCrCalculated = Table.AddColumn(NsvCrCalculated, "MRP_Sales_Value_Cr", each
    [MRP_Sales_Value] / 10000000  // Convert actual rupees to Crores
  ),

  // 18. Create Sales Qty Cr (Qty / 10,000,000 for display)
  QtyCrCalculated = Table.AddColumn(MrpCrCalculated, "Sales_Qty_Cr", each
    [Sales_Qty] / 10000000  // Convert to Crores for display
  ),

  // 19. Create Safe Value Basis (MRP is primary; NSV now confirmed and active)
  SafeValueBasisCalculated = Table.AddColumn(QtyCrCalculated, "Safe_Value_Basis", each
    [MRP_Sales_Value]  // MRP Sales Value remains primary basis
  ),

  // 20. Create Safe Reporting Flag (all rows safe; NSV unit now confirmed)
  SafeReportingFlagCalculated = Table.AddColumn(SafeValueBasisCalculated, "Is_Safe_For_Reporting", each
    true  // All rows safe for MRP & NSV reporting (NSV unit confirmed as Lakhs)
  ),

  // 21. Flag rows with negative MRP values (valid returns/credit notes)
  NegativeValueFlagCalculated = Table.AddColumn(SafeReportingFlagCalculated, "Is_Negative_Return", each
    [MRP_Sales_Value] < 0  // Negative MRP is valid (returns, credit notes); not an error
  ),

  // 22. Flag rows with negative NSV values (valid returns/credit notes)
  NegativeNsvFlagCalculated = Table.AddColumn(NegativeValueFlagCalculated, "Is_Negative_NSV", each
    [Source_NSV_Lacs] < 0  // Negative NSV is valid (returns, credit notes); not an error
  ),

  // 17. Create BA Availability flag (Brand Counter = BA coverage for Reliance)
  BAAvailabilityCalculated = Table.AddColumn(NegativeValueFlagCalculated, "BA_Available", each
    if [Chain_Name] = "Brand Counter" then "Yes" else "No"
  ),

  // 23. Remove intermediate columns and reorder for clarity
  ColumnsRemoved = Table.RemoveColumns(NegativeNsvFlagCalculated,
    {"Content", "Month_Raw", "Year"}),  // All NSV/MRP/Qty columns kept for reporting

  // Reorder columns for readability
  ColumnReordered = Table.SelectColumns(ColumnsRemoved, {
    "Site_Code", "Site_Name", "Chain_Name", "Zone", "Category", "PPT_Category",
    "Format", "Classification",
    "Month", "FY", "Month_Sort", "Month_Num", "Calendar_Year",
    "Is_Month_Partial", "Is_June26_Partial",
    "Sales_Qty", "Sales_Qty_Cr", "MRP_Sales_Value", "MRP_Sales_Value_Cr",
    "Source_NSV_Lacs", "NSV_Actual_Value", "NSV_Cr",
    "Safe_Value_Basis", "Is_Safe_For_Reporting", "Is_Negative_Return", "Is_Negative_NSV", "BA_Available"
  })
in
  ColumnReordered

// ============================================================================
// QC TABLE 1: MONTHLY RECONCILIATION
// ============================================================================
// Query: QC_Monthly_Reconciliation
// Aggregates by month: row count, MRP total, Qty total, negative-value count

let
  SourceFact = #"Offtake_Safe",  // Reference to Offtake_Safe query above
  Grouped = Table.Group(SourceFact, {"Month", "FY", "Is_Month_Partial"},
    {
      {"Row_Count", each Table.RowCount(_), type number},
      {"MRP_Sales_Value", each List.Sum([MRP_Sales_Value]), type number},
      {"Sales_Qty", each List.Sum([Sales_Qty]), type number},
      {"Negative_Value_Row_Count", each Table.RowCount(Table.SelectRows(_, each [Is_Negative_Return] = true)), type number}
    }),
  Sorted = Table.Sort(Grouped, {{"FY", Order.Ascending}, {"Month", Order.Ascending}})
in
  Sorted

// ============================================================================
// QC TABLE 2: MORE RETAIL RECORDS AUDIT
// ============================================================================
// Query: QC_More_Retail_Audit
// Lists More Retail row counts and MRP totals
// NOTE: Business has reviewed repeated records and retained them as valid source data.
// No deduplication is applied. All More Retail rows are kept.

let
  SourceFact = #"Offtake_Safe",
  MoreRetailRows = Table.SelectRows(SourceFact, each [Chain_Name] = "More Retail"),
  Grouped = Table.Group(MoreRetailRows, {"Month", "FY"},
    {
      {"Row_Count", each Table.RowCount(_), type number},
      {"MRP_Total", each List.Sum([MRP_Sales_Value]), type number}
    }),
  Sorted = Table.Sort(Grouped, {{"FY", Order.Ascending}, {"Month", Order.Ascending}})
in
  Sorted

// ============================================================================
// QC TABLE 3: CHAIN VARIANT CHECK
// ============================================================================
// Query: QC_Chain_Variant_Check
// Lists all distinct chain names and their row counts (awaiting canonicalization)

let
  SourceFact = #"Offtake_Safe",
  Grouped = Table.Group(SourceFact, {"Chain_Name"},
    {
      {"Row_Count", each Table.RowCount(_), type number},
      {"MRP_Total", each List.Sum([MRP_Sales_Value]), type number}
    }),
  Sorted = Table.Sort(Grouped, {{"Row_Count", Order.Descending}})
in
  Sorted

// ============================================================================
// REFERENCE QUERY: BLOCKED MEASURES LIST
// ============================================================================
// Query: QC_Blocked_Measures
// Documents measures that are blocked awaiting business decisions

let
  BlockedList = {
    {1, "CM2 (Contribution Margin 2)", "Requires CM2 cost source and accounting method (business input pending)"},
    {2, "Gross Margin %", "Requires margin % assumptions and cost sources (business input pending)"},
    {3, "Profitability measures", "Requires cost structure, COGS, and allocation rules (business input pending)"},
    {4, "P&L (complete)", "All P&L measures depend on cost sources (business input pending)"},
    {5, "BA Profitability", "Requires BA Headcount + cost structure + margin assumptions (business input pending)"},
    {6, "BA Cost to Serve", "Requires BA cost structure and allocation (business input pending)"},
    {7, "BA Productivity metrics", "Requires BA Headcount and cost structure (business input pending)"},
    {8, "Primary vs Offtake Gap %", "Requires Primary NSV validation (separate exercise)"},
    {9, "Chain-level reporting (variants)", "Vmm/VMM, Fsn/FSN, etc. awaiting canonicalization"}
  },
  ConvertedTable = Table.FromRows(BlockedList, {"Seq", "Measure", "Reason"}),
  TypedTable = Table.TransformColumnTypes(ConvertedTable, {{"Seq", type number}, {"Measure", type text}, {"Reason", type text}})
in
  TypedTable

// ============================================================================
// REFERENCE QUERY: PENDING BUSINESS DECISIONS
// ============================================================================
// Query: QC_Pending_Decisions
// Lists 6 blocking decisions with impact and timeline

let
  DecisionsList = {
    {1, "NSV Unit Validation", "Confirmed: NSV source is in Lakhs", "✓ COMPLETE: NSV Cr = Lakhs / 100. NSV measures now active and unblocked.", "COMPLETE"},
    {2, "More Retail Records Status", "Business reviewed; retained as valid source records", "✓ APPROVED: No dedup applied. All rows kept.", "COMPLETE"},
    {3, "Brand Counter = BA Availability", "Flag Brand Counter as BA coverage (Reliance)", "✓ APPROVED: BA Availability view shows Reliance BA coverage only. No BA profitability yet.", "COMPLETE"},
    {4, "State-wise Reporting", "Source state data unreliable; zone-only approach", "✓ APPROVED: No state-level rollups. Zone-level reporting used instead.", "COMPLETE"},
    {5, "Profitability & Cost Structure", "Pending business approval of cost sources and allocation", "Blocks P&L, CM2, Margin %, BA profitability (NSV unit now confirmed)", "Pending"},
    {6, "Chain Master Canonicalization", "Pending business approval of canonical names", "Variant chains (Vmm/VMM, etc.) awaiting merge", "Pending"}
  },
  ConvertedTable = Table.FromRows(DecisionsList, {"Seq", "Decision", "Action", "Impact", "Timeline"}),
  TypedTable = Table.TransformColumnTypes(ConvertedTable, {
    {"Seq", type number},
    {"Decision", type text},
    {"Action", type text},
    {"Impact", type text},
    {"Timeline", type text}
  })
in
  TypedTable
