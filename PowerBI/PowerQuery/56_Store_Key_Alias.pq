// =====================================================================
// QUERY: Store Key Alias  (grain = one alias store key; stand-alone lookup table)
// Source = SeedData\Masters\Store_Key_Aliases.csv, built by scripts/build_store_city_master.py.
// Some stores are listed under more than one code (same chain + store name + city, for example a re-coded Apollo or B&N store). The store master keeps ONE row
// per store (Store City Master[Store Key]) and the other codes are listed here, so a store counts once and its sales add up under one row.
// To make the offtake follow, build the fact's Match Key through this table (replaces the formula in 49_Store_City_Master.pq):
//   Match Key =
//       VAR _k = UPPER ( TRIM ( 'Fact Offtake Sales'[Chain] ) ) & "|" & UPPER ( TRIM ( 'Fact Offtake Sales'[Store Code] ) )
//       RETURN COALESCE ( LOOKUPVALUE ( 'Store Key Alias'[Store Match Key], 'Store Key Alias'[Alias Match Key], _k ), _k )
// No relationship is needed. Stores with no code have no Match Key and are not in this table.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\Store_Key_Aliases.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Alias Store Key", type text}, {"Alias Match Key", type text}, {"Alias Site Code", type text},
        {"Store Key", type text}, {"Store Match Key", type text}, {"Reason", type text}
    })
in
    Typed
