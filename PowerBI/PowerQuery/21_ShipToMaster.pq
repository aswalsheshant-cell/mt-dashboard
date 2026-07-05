// =====================================================================
// QUERY: Ship-To Master  (one row per Ship-To Party)
// Maps each Ship-to Party Name to its Direct/Distributor flag, primary
// (dominant) chain, zone, state, and the list of chains it serves.
// Edit SeedData\Masters\ShipToMaster.csv to re-map a ship-to to a chain.
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\ShipToMaster.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Ship To Name", type text},{"Direct/Distributor", type text},
        {"Primary Chain", type text},{"Zone", type text},{"State", type text},
        {"Chains Served", type text}}),
    Trimmed = Table.TransformColumns(Typed, {{"Ship To Name", each Text.Trim(_), type text}})
in
    Trimmed
