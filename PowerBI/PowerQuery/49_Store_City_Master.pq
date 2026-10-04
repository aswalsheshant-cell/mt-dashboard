// =====================================================================
// QUERY: Store City Master  (grain = Store Key; one row per store)
// Source = SeedData\Masters\Store_City_Master.csv, built by scripts/build_store_city_master.py from the
// chain-wise store list workbook (Jan-Jun 26) plus stores that sold in later offtake months (Source column).
// No employee, SO or ASE columns.
//
// One row per store. Store Key = standard chain name | site code (chain | store name or chain | city where there is no code).
// Chain Name is ONE standard spelling per chain (scripts/visit_cities.py CHAIN_STANDARD); Chain (as in source) keeps the spelling in the file.
// State is one standard spelling (State (as in source) keeps the original; State Note explains any change). City Final = master city,
// or the offtake city where the master holds only a locality. Visit Status = Considered / Near listed city / Not considered /
// City not available, against Visit_City_List.csv.
// Relate Fact Offtake Sales to this table on [Match Key]: add a calculated column to the fact
//   Match Key = UPPER ( TRIM ( 'Fact Offtake Sales'[Chain] ) ) & "|" & UPPER ( TRIM ( 'Fact Offtake Sales'[Store Code] ) )
// (Match Key = chain as spelt in the offtake file, upper case | site code). Stores without a code have no Match Key.
// A store listed under more than one code is ONE row here (Other Site Codes lists the other codes); the codes are in 56_Store_Key_Alias.pq, which gives the
// Match Key formula to use on the fact so the sales of every code land on that one row.
// Check the join with [Visit Master Match %] before using the city measures.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\Store_City_Master.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Store Key", type text}, {"Chain Name", type text}, {"Chain (as in source)", type text}, {"Site Code", type text}, {"Store Name", type text},
        {"Zone", type text}, {"State", type text}, {"State (as in source)", type text}, {"State Note", type text},
        {"City (store list)", type text}, {"City (offtake file)", type text}, {"City Final", type text}, {"City Source", type text},
        {"Visit City", type text}, {"Visit Region", type text}, {"Visit Status", type text}, {"Nearest Listed City", type text},
        {"Store Type", type text}, {"Match Key", type text}, {"Source", type text},
        {"Other Site Codes", type text}, {"Merged Rows", Int64.Type}
    })
in
    Typed
