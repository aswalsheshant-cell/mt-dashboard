// =====================================================================
// QUERY: Fact Primary ShipTo   (grain = Month x Ship-To x Chain x Brand)
// Source = RawDataFolders\Primary_ShipTo_Monthly
//
// This is the ship-to-party primary feed where primary NSV is ALREADY
// allocated to Chain based on the secondary/offtake contribution % that
// month. (Direct ship-tos => one chain, Cont% = 100%. Distributor ship-tos
// => split across chains by Cont%.)
//
// The Cont% column is the dynamic, month-wise allocation driver (the
// "separate mapping table"). It is NOT hardcoded - it arrives in the monthly
// file and is also projected out as 'Primary Allocation Map' (query 34).
//
// Cleaning here is reproducible every month: brand/chain spellings are
// normalised and NSV (received in Lacs) is converted to absolute rupees so
// it lines up with Fact Offtake Sales.
// =====================================================================
let
    Combined = fnCombineFolder(pRootFolder & "\RawDataFolders\Primary_ShipTo_Monthly"),

    // Primary_ShipTo_FY24-25.csv and Primary_ShipTo_FY25-26_to_May26.csv are exact
    // subsets of Primary_ShipTo_FY24-26_Composite.csv on Month, Ship To Name, Brand,
    // NSV and MRP (every row found, same totals). Their Chain labels differ (the
    // composite uses the normalised names). Loading all three counted those
    // months two times.
    // New monthly files are still picked up. 41_DistContWeights.pq reads the
    // FY25-26 file by name, so the files stay in the folder.
    Source = Table.SelectRows(Combined, each not List.Contains(
        {"Primary_ShipTo_FY24-25.csv", "Primary_ShipTo_FY25-26_to_May26.csv"}, [Data Source File])),

    Typed = Table.TransformColumnTypes(Source, {
        {"Month", type text},
        {"MonthStart", type date},
        {"FY Year", type text},
        {"Ship To Name", type text},
        {"Direct/Distributor", type text},
        {"Chain", type text},
        {"Zone", type text},
        {"State", type text},
        {"Brand", type text},
        {"Primary NSV", type number},
        {"MRP Value", type number},
        {"Cont%", type number}
    }),

    Trimmed = Table.TransformColumns(Typed, {
        {"Ship To Name", each Text.Trim(Text.From(_)), type text},
        {"Chain", each Text.Trim(Text.From(_)), type text},
        {"Brand", each Text.Trim(Text.From(_)), type text}
    }),

    // --- normalise brand spellings (keep in sync with Brand Master) ---
    FixBrand = Table.ReplaceValue(Trimmed, "BBLUNT", "BBlunt", Replacer.ReplaceText, {"Brand"}),

    // --- normalise chain spellings (keep in sync with Chain Master) ---
    FixChain1 = Table.ReplaceValue(FixBrand, "Vmm",       "Vishal Mega Mart", Replacer.ReplaceValue, {"Chain"}),
    FixChain2 = Table.ReplaceValue(FixChain1,"VMM",       "Vishal Mega Mart", Replacer.ReplaceValue, {"Chain"}),
    FixChain3 = Table.ReplaceValue(FixChain2,"ARAMBAGH",  "Arambagh",         Replacer.ReplaceValue, {"Chain"}),
    FixChain4 = Table.ReplaceValue(FixChain3,"Reliance",  "Reliance Retail",  Replacer.ReplaceValue, {"Chain"}),
    FixChain5 = Table.ReplaceValue(FixChain4,"Dmart",     "D-Mart",           Replacer.ReplaceValue, {"Chain"}),
    FixChain6 = Table.ReplaceValue(FixChain5,"Spencer",   "Spencers",         Replacer.ReplaceValue, {"Chain"}),
    FixChain7 = Table.ReplaceValue(FixChain6,"H&G",       "Health & Glow",    Replacer.ReplaceValue, {"Chain"}),
    // owner-confirmed 2026-10-11 (same as CHAIN_ALIASES in scripts/build_dashboard_data.py)
    FixChain8  = Table.ReplaceValue(FixChain7, "Hypermax City Private Limited", "Carrefour", Replacer.ReplaceValue, {"Chain"}),
    FixChain9  = Table.ReplaceValue(FixChain8, "CARREFOUR",                      "Carrefour", Replacer.ReplaceValue, {"Chain"}),
    FixChain10 = Table.ReplaceValue(FixChain9, "Octopolis Technologies Pvt Ltd", "Apna Klub", Replacer.ReplaceValue, {"Chain"}),
    FixChain11 = Table.ReplaceValue(FixChain10,"Dabur New U",                    "H&B",       Replacer.ReplaceValue, {"Chain"}),
    FixChain12 = Table.ReplaceValue(FixChain11,"Centro",                         "Azorte",    Replacer.ReplaceValue, {"Chain"}),

    // If the file ever arrives in Lacs again instead of absolute rupees,
    // flip this flag. The seed already stores absolute rupees, so default = false.
    ConvertFromLacs = false,
    Scaled = if ConvertFromLacs
        then Table.TransformColumns(FixChain12, {
                {"Primary NSV", each _ * 100000, type number},
                {"MRP Value",  each _ * 100000, type number}})
        else FixChain12,

    // Direct rows may have blank Cont% -> treat as 100%
    FillCont = Table.ReplaceValue(Scaled, null, 1.0, Replacer.ReplaceValue, {"Cont%"}),

    // Cont% scale. Distributor rows arrive as fractions (a ship-to/brand/month group sums to 1)
    // or as percentages (the group sums to 100); both occur in the composite file and nothing
    // else does. A group that sums to more than 1.5 is divided by 100. Direct rows are 100%.
    ContSums = Table.Group(FillCont, {"Ship To Name", "Brand", "Month"},
        {{"Group Cont Sum", each List.Sum([#"Cont%"]), type number}}),
    ContJoined = Table.NestedJoin(FillCont, {"Ship To Name", "Brand", "Month"},
        ContSums, {"Ship To Name", "Brand", "Month"}, "CS", JoinKind.LeftOuter),
    ContExpanded = Table.ExpandTableColumn(ContJoined, "CS", {"Group Cont Sum"}),
    ContFixed = Table.AddColumn(ContExpanded, "Cont% Fixed", each
        if Text.Lower(Text.Trim([#"Direct/Distributor"] ?? "")) = "direct" then 1.0
        else if [Group Cont Sum] > 1.5 then [#"Cont%"] / 100
        else [#"Cont%"], type number),
    ContDone = Table.RenameColumns(Table.RemoveColumns(ContFixed, {"Cont%", "Group Cont Sum"}),
        {{"Cont% Fixed", "Cont%"}}),

    // Channel. The ShipTo files have no Channel column, so it comes from ShipToChannelMap.csv
    // (built by scripts/build_shipto_channel_map.py from Primary Article, where each ship-to name
    // sits in exactly one channel). Then the same pPrimaryChannel scope as Primary Article applies.
    // A ship-to that is not in the map is labelled UNMAPPED and kept, so it stays visible.
    ChannelMapRaw = Table.PromoteHeaders(
        Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\ShipToChannelMap.csv"),
            [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
        [PromoteAllScalars=true]),
    ChannelMapPicked = Table.SelectColumns(ChannelMapRaw, {"Ship To Name", "Channel"}),
    ChannelMap = Table.TransformColumns(ChannelMapPicked,
        {{"Ship To Name", each Text.Lower(Text.Trim(_)), type text},
         {"Channel", each Text.Upper(Text.Trim(_)), type text}}),
    WithChannelKey = Table.AddColumn(ContDone, "ShipTo Channel Key",
        each Text.Lower(Text.Trim([Ship To Name] ?? "")), type text),
    ChannelJoined = Table.NestedJoin(WithChannelKey, {"ShipTo Channel Key"}, ChannelMap, {"Ship To Name"}, "CM", JoinKind.LeftOuter),
    ChannelExpanded = Table.ExpandTableColumn(ChannelJoined, "CM", {"Channel"}),
    ChannelLabelled = Table.RemoveColumns(
        Table.ReplaceValue(ChannelExpanded, null, "UNMAPPED", Replacer.ReplaceValue, {"Channel"}),
        {"ShipTo Channel Key"}),
    ChannelScoped = if Text.Upper(pPrimaryChannel) = "ALL" then ChannelLabelled
        else Table.SelectRows(ChannelLabelled, each [Channel] = Text.Upper(Text.Trim(pPrimaryChannel)) or [Channel] = "UNMAPPED"),

    // rebuild MonthStart if the source only had the text label
    AddMonthStart = Table.AddColumn(ChannelScoped, "MonthStartCalc", each
        if [MonthStart] <> null then [MonthStart]
        else
            let m = Text.Start(Text.BeforeDelimiter([Month], "'"), 3),
                yy = Text.AfterDelimiter([Month], "'"),
                mn = Record.FieldOrDefault([Jan=1,Feb=2,Mar=3,Apr=4,May=5,Jun=6,Jul=7,Aug=8,Sep=9,Oct=10,Nov=11,Dec=12], m, null)
            in if mn = null then null else #date(2000 + Number.FromText(yy), mn, 1),
        type date),

    Cleaned = Table.SelectRows(AddMonthStart, each [Primary NSV] <> null)
in
    Cleaned
