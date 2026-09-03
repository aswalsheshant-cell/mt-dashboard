// ============================================================================
// Power Query: Promo Calendar Dimension (Sep 2026+)
// Purpose: Reference dimension for promotional mechanics
// Input: PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_YYYY.csv
// Output: Dim_PromoCalendar table (linked to Dim_Brand, Dim_Calendar)
// ============================================================================

let
    // Step 1: Read source CSV from watch folder
    Source = Csv.Document(
        File.Contents("PowerBI/RawDataFolders/Promo_Calendar/promo_mechanics_Sep_2026.csv"),
        [Delimiter = ",", Columns = 18, Encoding = 65001, QuoteStyle = QuoteStyle.None]
    ),

    // Step 2: Promote first row as headers
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),

    // Step 3: Standardize column names and types
    TypedColumns = Table.TransformColumnTypes(
        PromotedHeaders,
        {
            {"Source_Month", type text},           // "2026-09"
            {"Chain Name", type text},              // Retail channel name
            {"Brand", type text},                   // Mamaearth, The Derma Co, etc.
            {"Category", type text},                // Product category
            {"Sub_Category", type text},            // Product sub-category
            {"Range", type text},                   // Product range/line
            {"EAN Code", type text},                // EAN (may contain decimals)
            {"Article Code", type text},            // Article/SKU code
            {"Description", type text},             // Full product description
            {"MRP", type number},                   // Maximum Retail Price (INR)
            {"Offer to consumer", type any},        // Offer value/discount
            {"ME_Contribution_Pct", type number},   // Mamaearth contribution %
            {"Chain_Contribution_Pct", type number}, // Chain contribution %
            {"Total_Contribution_Pct", type number}, // Total trade spend allocation %
            {"Locations", type number},             // Number of store locations
            {"From ", type date},                   // Promotion start date
            {"To", type date},                      // Promotion end date
            {"Promo_Type", type text}               // Promotion type classification
        }
    ),

    // Step 4: Add derived columns for Power BI slicing
    AddDerivedColumns = Table.AddColumn(
        TypedColumns,
        "Promo_Month",
        each Date.Month(
            Date.FromText([Source_Month] & "-01")
        ),
        Int64.Type
    ),

    AddPromoYear = Table.AddColumn(
        AddDerivedColumns,
        "Promo_Year",
        each Date.Year(
            Date.FromText([Source_Month] & "-01")
        ),
        Int64.Type
    ),

    AddPromoDuration = Table.AddColumn(
        AddPromoYear,
        "Duration_Days",
        each Duration.Days([To] - [From ]) + 1,
        Int64.Type
    ),

    // Step 5: Clean chain name (standardize to match Dim_Chain canonical names)
    StandardizeChain = Table.ReplaceValue(
        AddPromoDuration,
        each [Chain Name],
        each
            if Text.Contains([Chain Name], "Dmart", Comparer.OrdinalIgnoreCase) then "D-Mart"
            else if Text.Contains([Chain Name], "VMM", Comparer.OrdinalIgnoreCase) or
                    Text.Contains([Chain Name], "Vishal", Comparer.OrdinalIgnoreCase) then "Vishal Mega Mart"
            else if Text.Contains([Chain Name], "Reliance", Comparer.OrdinalIgnoreCase) then "Reliance Retail"
            else if Text.Contains([Chain Name], "Apollo", Comparer.OrdinalIgnoreCase) then "Apollo"
            else if Text.Contains([Chain Name], "More", Comparer.OrdinalIgnoreCase) then "More Retail"
            else if Text.Contains([Chain Name], "H&G", Comparer.OrdinalIgnoreCase) or
                    Text.Contains([Chain Name], "Health", Comparer.OrdinalIgnoreCase) then "Health & Glow"
            else if Text.Contains([Chain Name], "Metro", Comparer.OrdinalIgnoreCase) then "Metro"
            else if Text.Contains([Chain Name], "Lulu", Comparer.OrdinalIgnoreCase) then "Lulu Hypermarket"
            else [Chain Name],
        Replacer.ReplaceText,
        [{"Chain Name"}]
    ),

    // Step 6: Add Promo Key for fact table joins
    AddPromoKey = Table.AddColumn(
        StandardizeChain,
        "Promo_Key",
        each [Source_Month] & "|" & [Chain Name] & "|" & [EAN Code],
        type text
    ),

    // Step 7: Remove nulls (EAN codes may be empty for bundle/promotion-only SKUs)
    RemoveNulls = Table.SelectRows(
        AddPromoKey,
        each [EAN Code] <> null and [EAN Code] <> ""
    ),

    // Step 8: Remove duplicates (in case of file consolidation)
    RemoveDuplicates = Table.Distinct(
        RemoveNulls,
        {"Promo_Key"}
    ),

    // Step 9: Reorder columns for readability
    ReorderedColumns = Table.ReorderColumns(
        RemoveDuplicates,
        {
            "Source_Month", "Promo_Month", "Promo_Year", "From ", "To", "Duration_Days",
            "Chain Name", "Brand", "Category", "Sub_Category", "Range",
            "EAN Code", "Article Code", "Description", "MRP", "Offer to consumer",
            "ME_Contribution_Pct", "Chain_Contribution_Pct", "Total_Contribution_Pct",
            "Locations", "Promo_Type", "Promo_Key"
        }
    )

in
    ReorderedColumns

// ============================================================================
// RELATIONSHIP SETUP (Manual in Model View):
// ============================================================================
// 1. Dim_PromoCalendar[Chain Name] → Dim_Chain[Chain_Name] (One-to-Many)
//    Direction: Single (1 → *)
//    Cross-Filter: Single
//
// 2. Dim_PromoCalendar[From ] → Dim_Calendar[Date] (One-to-Many, period slice)
//    Direction: Single (1 → *)
//    Cross-Filter: Single
//
// 3. Dim_PromoCalendar[Brand] → Dim_Brand[Brand_Name] (One-to-Many)
//    Direction: Single (1 → *)
//    Cross-Filter: Single
//
// ============================================================================
// MEASUREMENT GUIDANCE (DAX):
// ============================================================================
// Planned Trade Spend Allocation:
// [Planned_ME_Contribution] = SUM(Dim_PromoCalendar[ME_Contribution_Pct])
//
// Planned Chain Investment:
// [Planned_Chain_Contribution] = SUM(Dim_PromoCalendar[Chain_Contribution_Pct])
//
// Planned vs. Actual Variance (once Sep billing data arrives):
// [Trade_Spend_Variance] = [Actual_ME_Contribution] - [Planned_ME_Contribution]
//
// Promo Penetration Rate:
// [SKU_Penetration_Rate] = DISTINCTCOUNT(Dim_PromoCalendar[EAN Code]) / DISTINCTCOUNT(Dim_Brand[EAN])
//
// ============================================================================
