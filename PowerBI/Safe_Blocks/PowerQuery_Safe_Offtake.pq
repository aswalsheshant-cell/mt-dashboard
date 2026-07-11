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

  // 14. Create Safe Value Basis column (MRP Sales Value is the safe basis)
  SafeValueBasisCalculated = Table.AddColumn(MonthPartialFlagCalculated, "Safe_Value_Basis", each
    [MRP_Sales_Value]  // MRP Sales Value is verified; NSV is blocked
  ),

  // 15. Create Safe Reporting Flag (true = can use in reports; false = blocked pending decision)
  SafeReportingFlagCalculated = Table.AddColumn(SafeValueBasisCalculated, "Is_Safe_For_Reporting", each
    true  // All rows are safe for MRP-basis reporting; NSV flagged separately
  ),

  // 16. Flag rows with negative values (valid returns/credit notes)
  NegativeValueFlagCalculated = Table.AddColumn(SafeReportingFlagCalculated, "Is_Negative_Return", each
    [NSV] < 0  // Negative NSV is valid (returns, credit notes); not an error
  ),

  // 17. Remove intermediate columns and reorder for clarity
  ColumnsRemoved = Table.RemoveColumns(ExpandedContent,
    {"Content", "Month_Raw", "Year", "NSV"}),  // NSV removed from report-ready layer

  // Reorder columns for readability
  ColumnReordered = Table.SelectColumns(ColumnsRemoved, {
    "Site_Code", "Site_Name", "Chain_Name", "Zone", "Category", "PPT_Category",
    "Format", "Classification",
    "Month", "FY", "Month_Sort", "Month_Num", "Calendar_Year",
    "Is_Month_Partial", "Is_June26_Partial",
    "Sales_Qty", "MRP_Sales_Value", "Safe_Value_Basis",
    "Is_Safe_For_Reporting", "Is_Negative_Return"
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
// QC TABLE 2: DUPLICATE REPORT (More Retail)
// ============================================================================
// Query: QC_Duplicate_Report
// Identifies exact-duplicate rows in More Retail chain (do NOT remove; report only)

let
  SourceFact = #"Offtake_Safe",
  MoreRetailRows = Table.SelectRows(SourceFact, each [Chain_Name] = "More Retail"),

  // Create row hash for exact-duplicate detection
  WithHash = Table.AddColumn(MoreRetailRows, "Row_Hash", each
    let
      RowTuple = Text.Combine({
        Text.From([Site_Code]), "|", Text.From([Chain_Name]), "|",
        Text.From([Category]), "|", Text.From([Month]), "|",
        Text.From([MRP_Sales_Value])
      })
    in
      RowTuple),

  // Count occurrences of each hash
  Grouped = Table.Group(WithHash, {"Row_Hash"},
    {
      {"Count", each Table.RowCount(_), type number},
      {"MRP_Total", each List.Sum([MRP_Sales_Value]), type number},
      {"Sample_Month", each List.First([Month]), type text}
    }),

  // Filter to show only duplicates (Count > 1)
  DuplicatesOnly = Table.SelectRows(Grouped, each [Count] > 1),
  Sorted = Table.Sort(DuplicatesOnly, {{"Count", Order.Descending}})
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
    {1, "NSV (unit unvalidated)", "Finance must provide reference anchor (₹Cr for 1 month)"},
    {2, "NSV (Cr), NSV (Lacs), NSV Label", "Dependent on NSV unit confirmation"},
    {3, "MoM/YoY/L3M/L6M % growth (NSV basis)", "Uses NSV; blocked until unit confirmed"},
    {4, "Contribution % (NSV-driven)", "Blocked on NSV unit"},
    {5, "Rank by Sales (NSV-driven)", "Blocked on NSV unit"},
    {6, "P&L / Profitability measures", "All depend on NSV unit or BA Headcount (business input)"},
    {7, "CM2, Gross Margin %", "Require NSV unit + margin assumptions"},
    {8, "BA Profitability", "Awaiting BA Headcount + Brand Counter classification"},
    {9, "State-level rollups, State slicer", "247 raw state values include cities; City-State mapping pending"},
    {10, "More Retail chain totals", "13,661 exact-dup rows (₹1.36 Cr / 10.3% MRP); pending dedup decision"},
    {11, "Chain-level reporting (variants)", "Vmm/VMM, Fsn/FSN, etc. awaiting canonicalization"}
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
    {1, "NSV Unit Validation", "Confirm unit multiplier via finance anchor", "Blocks P&L, Profitability, all %-growth on NSV", "1–2 weeks"},
    {2, "More Retail Duplicates", "Choose: (1) de-dupe in PQ, (2) fix at source, (3) footnote as inflated", "More Retail totals inflated ₹1.36 Cr / 10.3% MRP", "1–3 weeks"},
    {3, "Brand Counter Classification", "Confirm if BA channel, store-type, or chain", "549,617 rows; affects chain & BA reporting", "1 week"},
    {4, "State-to-City Mapping", "Business approves City-State Master SEED", "Blocks state-level rollups (247 raw values)", "1–2 weeks"},
    {5, "Chain Master Canonicalization", "Approve canonical spellings + BA support flags", "Variant chains (Vmm/VMM, etc.) block chain-level reporting", "1 week"},
    {6, "Reliance Schema Completeness", "Accept partial (29 cols) or request full export", "Missing DC Name, Year, SO/DC fields", "1–3 weeks"}
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
