// =====================================================================
// DIMENSION / MASTER QUERIES
// Each master loads a single CSV from SeedData\Masters. These are slowly
// changing reference tables you edit by hand (add a chain, a brand, an SKU).
// Create ONE query per block below (split into separate queries in Power BI).
// =====================================================================

// ---------- Chain Master ----------
let
    Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\ChainMaster.csv"),
        [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {
        {"Chain", type text},{"Account", type text},{"Chain Type", type text},
        {"Primary Zone", type text},{"Active", type text}})
in Typed

// ---------- Brand Master ----------
// let Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\BrandMaster.csv"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),
//     H=Table.PromoteHeaders(Source,[PromoteAllScalars=true]),
//     T=Table.TransformColumnTypes(H,{{"Brand",type text},{"Brand Group",type text},{"Brand Sort Order",Int64.Type},{"Active",type text}})
// in T

// ---------- Category Master ----------
// let Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\CategoryMaster.csv"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),
//     H=Table.PromoteHeaders(Source,[PromoteAllScalars=true]),
//     T=Table.TransformColumnTypes(H,{{"Category",type text},{"Sub-category",type text},{"Nielsen Category",type text},{"Category Sort Order",Int64.Type}})
// in T

// ---------- SKU / Article Master ----------
// let Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\ArticleMaster.csv"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),
//     H=Table.PromoteHeaders(Source,[PromoteAllScalars=true]),
//     T=Table.TransformColumnTypes(H,{{"Article Code",type text},{"Article Description",type text},{"EAN Code",type text},{"Brand",type text},{"Category",type text},{"Sub-category",type text},{"Range",type text},{"Pack Size",type text}})
// in T

// ---------- Zone / State Master ----------
// let Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\ZoneStateMaster.csv"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),
//     H=Table.PromoteHeaders(Source,[PromoteAllScalars=true]),
//     T=Table.TransformColumnTypes(H,{{"Zone",type text},{"Zone Sort Order",Int64.Type},{"State",type text},{"Region",type text}})
// in T

// ---------- Store Master ----------
// let Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\StoreMaster.csv"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),
//     H=Table.PromoteHeaders(Source,[PromoteAllScalars=true]),
//     T=Table.TransformColumns(Table.TransformColumnTypes(H,{{"Store Code",type text},{"Store Name",type text},{"Chain",type text},{"Account",type text},{"Zone",type text},{"State",type text},{"City",type text}}),{{"Store Code",each Text.Trim(_),type text}})
// in T

// ---------- Nielsen Competitor Master ----------
// let Source = Csv.Document(File.Contents(pRootFolder & "\SeedData\Masters\NielsenCompetitorMaster.csv"),[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv]),
//     H=Table.PromoteHeaders(Source,[PromoteAllScalars=true]),
//     T=Table.TransformColumnTypes(H,{{"Nielsen Category",type text},{"Brand",type text},{"Is Honasa",type text},{"Competitor Sort Order",Int64.Type}})
// in T
