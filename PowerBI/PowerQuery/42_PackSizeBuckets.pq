// =====================================================================
// QUERY: Pack Size Buckets  (Dimension helper)
// Joins to Fact Primary Article and Fact Offtake Sales on [Pack Size]
// Classifies articles into standard ML-bucket tiers used by Category &
// Pack tab. Works for BOTH primary (net_content column) and offtake
// (Net Weight column) — both are renamed to [Pack Size] in their facts.
//
// Bucket tiers (business-confirmed, keep in sync with dashboard logic):
//   Micro   : ≤  50 ml/g          (travel, trial, sachets)
//   Small   : 51 – 150 ml/g
//   Standard: 151 – 300 ml/g
//   Large   : 301 – 500 ml/g
//   XL      : > 500 ml/g          (value packs, combos)
//   Unknown : blank / non-numeric  (kits, bundles, unit ambiguous)
//
// Usage: Home > Manage Relationships — link [Pack Size] here to
//   Fact Primary Article [net_content] and Fact Offtake Sales [Pack Size].
// =====================================================================
let
    // ---- 1. Collect every distinct Pack Size string from both facts ----
    //   (this ensures the dimension covers all values, even those without
    //    a counterpart in one of the fact tables)
    PrimaryPS = Table.SelectColumns(#"Fact Primary Article", {"net_content"}),
    PrimaryPS2 = Table.RenameColumns(PrimaryPS, {{"net_content", "Pack Size Raw"}}),

    OfftakePS = Table.SelectColumns(#"Fact Offtake Sales", {"Pack Size"}),
    OfftakePS2 = Table.RenameColumns(OfftakePS, {{"Pack Size", "Pack Size Raw"}}),

    AllPS = Table.Distinct(Table.Combine({PrimaryPS2, OfftakePS2})),

    // ---- 2. Extract numeric value (strip units: "150ml", "150 g", "150", …) ----
    AddNumeric = Table.AddColumn(AllPS, "Pack ML", each
        let raw = Text.Trim(Text.From([Pack Size Raw] ?? "")),
            digits = Text.Select(raw, {"0".."9", "."}),   // keep digits and decimal
            n = if digits = "" then null else Number.FromText(digits)
        in n,
        type number),

    // ---- 3. Assign bucket ----
    AddBucket = Table.AddColumn(AddNumeric, "Pack Bucket", each
        if [Pack ML] = null              then "Unknown"
        else if [Pack ML] <= 50          then "Micro"
        else if [Pack ML] <= 150         then "Small"
        else if [Pack ML] <= 300         then "Standard"
        else if [Pack ML] <= 500         then "Large"
        else                                  "XL",
        type text),

    // ---- 4. Sort order for slicers and charts ----
    AddSortOrder = Table.AddColumn(AddBucket, "Bucket Sort", each
        Record.FieldOrDefault(
            [Unknown=0, Micro=1, Small=2, Standard=3, Large=4, XL=5],
            [Pack Bucket], 0),
        type number),

    // ---- 5. Range label for tooltips ("≤ 50 ml", "51–150 ml", …) ----
    AddLabel = Table.AddColumn(AddSortOrder, "Bucket Label", each
        Record.FieldOrDefault(
            [Unknown  = "Unknown / Bundle",
             Micro    = "≤ 50 ml/g",
             Small    = "51–150 ml/g",
             Standard = "151–300 ml/g",
             Large    = "301–500 ml/g",
             XL       = "> 500 ml/g"],
            [Pack Bucket], ""),
        type text),

    // ---- 6. Final column order ----
    Final = Table.SelectColumns(AddLabel, {
        "Pack Size Raw", "Pack ML", "Pack Bucket", "Bucket Sort", "Bucket Label"
    }),

    Typed = Table.TransformColumnTypes(Final, {
        {"Pack Size Raw", type text},
        {"Pack ML", type number},
        {"Pack Bucket", type text},
        {"Bucket Sort", Int64.Type},
        {"Bucket Label", type text}
    })
in
    Typed
