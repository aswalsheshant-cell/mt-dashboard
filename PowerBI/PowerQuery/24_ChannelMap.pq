// =====================================================================
// CHANNEL MAP QUERIES  (resolve MT / EB2B / SIS on the offtake side)
// The store x article offtake file has NO Channel column, so channel is
// derived: Store Code override first, else chain default, else "Unmapped".
// The primary File 2 already carries an explicit Channel — used as the SIS
// source of truth in the reconciliation (see DAX 10).
// Create BOTH queries below (split the two blocks).
// =====================================================================

// ---------- Channel Map Store (SIS/EB2B store overrides) ----------
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\ChannelMap_Store.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {{"Store Code", type text},{"Channel", type text},{"Remarks", type text}}),
    Trimmed = Table.TransformColumns(Typed, {{"Store Code", each Text.Trim(Text.From(_)), type text}}),
    Deduped = Table.Distinct(Trimmed, {"Store Code"})
in
    Deduped

// ---------- Channel Map Chain (default channel per chain) ----------
// let
//     Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\ChannelMap_Chain.csv"),
//         [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
//     Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
//     Typed = Table.TransformColumnTypes(Headers, {{"Chain", type text},{"Channel", type text},{"Remarks", type text}}),
//     Deduped = Table.Distinct(Typed, {"Chain"})
// in
//     Deduped
