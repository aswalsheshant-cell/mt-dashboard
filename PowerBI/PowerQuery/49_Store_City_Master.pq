// =====================================================================
// QUERY: Store City Master  (grain = Store Key; one row per store)
// Source = SeedData\Masters\Store_City_Master.csv, built by scripts/build_store_city_master.py from the
// chain-wise store list workbook (Jan-Jun 26) plus stores that sold in later offtake months (Source column).
// No employee, SO or ASE columns.
//
// Key columns: Store Key = Chain Name & Site Code (matches the offtake file's Unique column; stores without a code
// use Chain Name | Store Name). City Final = master city, or the offtake city where the master holds only a locality.
// Visit Status = Considered / Near listed city / Not considered / City not available, against Visit_City_List.csv.
// Relate Fact Offtake Sales[Store Key] -> Store City Master[Store Key]. Add Store Key to Fact Offtake Sales as a calculated
// column:  Store Key = 'Fact Offtake Sales'[Chain] & 'Fact Offtake Sales'[Store Code]   (check match % with [Visit Master Match %]).
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\Store_City_Master.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Store Key", type text}, {"Chain Name", type text}, {"Site Code", type text}, {"Store Name", type text},
        {"Zone", type text}, {"State", type text},
        {"City (store list)", type text}, {"City (offtake file)", type text}, {"City Final", type text}, {"City Source", type text},
        {"Visit City", type text}, {"Visit Region", type text}, {"Visit Status", type text}, {"Nearest Listed City", type text},
        {"Store Type", type text}, {"Dup Rows", Int64.Type}, {"Source", type text}
    })
in
    Typed
