// =====================================================================
// QUERY: Sales Team Mapping  (one row per Month x Store x Sales Person)
// Unpivots Store-SO Mapping (SO1/SO2/SO3 + Cont%1/2/3) so a store split
// across officers becomes multiple rows carrying the Cont% weight.
// Used by the Forecast page to attribute TY target ownership to a Sales
// Person (via the store's Chain/Zone in the offtake/primary facts).
// =====================================================================
let
    Source = #"Store SO Mapping",   // from query 32
    // build 3 candidate SO rows, then keep the non-blank ones
    R1 = Table.SelectColumns(Source, {"Month","Store Code","Employee ID 1","SO Name 1","Cont% 1"}),
    R1r = Table.RenameColumns(R1, {{"Employee ID 1","Employee ID"},{"SO Name 1","Sales Person"},{"Cont% 1","Cont%"}}),
    R2 = Table.SelectColumns(Source, {"Month","Store Code","Employee ID 2","SO Name 2","Cont% 2"}),
    R2r = Table.RenameColumns(R2, {{"Employee ID 2","Employee ID"},{"SO Name 2","Sales Person"},{"Cont% 2","Cont%"}}),
    R3 = Table.SelectColumns(Source, {"Month","Store Code","Employee ID 3","SO Name 3","Cont% 3"}),
    R3r = Table.RenameColumns(R3, {{"Employee ID 3","Employee ID"},{"SO Name 3","Sales Person"},{"Cont% 3","Cont%"}}),
    Combined = Table.Combine({R1r, R2r, R3r}),
    Clean = Table.SelectRows(Combined, each
        [Sales Person] <> null and Text.Trim(Text.From([Sales Person])) <> "" and ([Cont%] ?? 0) > 0),
    Trimmed = Table.TransformColumns(Clean, {
        {"Store Code", each Text.Trim(Text.From(_)), type text},
        {"Sales Person", each Text.Trim(Text.From(_)), type text}}),
    Typed = Table.TransformColumnTypes(Trimmed, {
        {"Month", type text},{"Store Code", type text},{"Employee ID", type text},
        {"Sales Person", type text},{"Cont%", type number}})
in
    Typed
