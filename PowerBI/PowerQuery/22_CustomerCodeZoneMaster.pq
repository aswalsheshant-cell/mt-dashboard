// =====================================================================
// QUERY: Customer Code Zone-State Master  (PRIMARY zone/state reference)
// Source: SeedData\Mapping\CustomerCode_Zone_State_Mapping.csv
// (built from the shared Central Zone Mapping file, keyed on Cust-SAP Code)
//
// Use this as the FIRST source for Zone / State / Business Region wherever a
// Customer Code (= Store Code / Cust-SAP Code) is available. It preserves the
// TRUE State plus the business sub-region (e.g. Maharashtra -> Mumbai / Pune /
// Vidarbha; Uttar Pradesh -> UPW / Lucknow-UPE). Does NOT overwrite the
// inferred chain-account mapping.
//
// Resolution order (apply in the fact via merge or DAX, see docs):
//   1) Match on Customer Code (Store Code)
//   2) else Ship-to Name + City/Location
//   3) else leave Zone/State blank and tag "Needs Check"
// =====================================================================
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Mapping\CustomerCode_Zone_State_Mapping.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Customer Code", type text},
        {"Customer Name / Ship-to Name", type text},
        {"State", type text},
        {"Zone", type text},
        {"City / Location", type text},
        {"Business Region / Sub-region", type text},
        {"Chain Name", type text},
        {"Account", type text},
        {"Channel", type text},
        {"Mapping Source", type text},
        {"Validation Status", type text},
        {"Remarks", type text}}),
    Trimmed = Table.TransformColumns(Typed, {{"Customer Code", each Text.Trim(Text.From(_)), type text}})
in
    Trimmed
