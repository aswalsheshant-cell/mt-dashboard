// =====================================================================
// FUNCTION: fnCombineFolder
// Combines every .csv / .xlsx / .xlsb file found in a sub-folder into one
// table. Works for the "drop a file each month and click Refresh" workflow:
// add a new file to the folder, refresh, and the rows are appended.
//
// - Files whose name starts with "_" are ignored (so _TEMPLATE_*.csv and
//   _archive files never get loaded).
// - Adds [Data Source File] and [Refresh Date] audit columns automatically.
// - First row of each file is treated as the header.
//
// Usage in another query:
//   = fnCombineFolder(pRootFolder & "\RawDataFolders\Offtake_Monthly")
// =====================================================================
let
    fnCombineFolder = (FolderPath as text) as table =>
        let
            Source = Folder.Files(FolderPath),

            // keep only real data files, skip templates / hidden / archive
            OnlyData = Table.SelectRows(
                Source,
                each ([Attributes]?[Hidden]? <> true)
                    and (Text.StartsWith([Name], "_") = false)
                    and (
                        Text.EndsWith(Text.Lower([Extension]), ".csv")
                        or Text.EndsWith(Text.Lower([Extension]), ".xlsx")
                        or Text.EndsWith(Text.Lower([Extension]), ".xlsb")
                    )
            ),

            // parse each file into a table depending on its type
            AddParsed = Table.AddColumn(OnlyData, "Parsed", each
                let
                    ext = Text.Lower([Extension]),
                    bin = [Content],
                    asTable =
                        if ext = ".csv" then
                            Csv.Document(bin, [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv])
                        else
                            // xlsx / xlsb : take the first sheet
                            let
                                wb = Excel.Workbook(bin, null, true),
                                firstSheet = wb{0}[Data]
                            in firstSheet,
                    promoted = Table.PromoteHeaders(asTable, [PromoteAllScalars=true])
                in
                    promoted
            ),

            // stamp source file + refresh timestamp on every row
            AddMeta = Table.AddColumn(AddParsed, "WithMeta", each
                Table.AddColumn(
                    Table.AddColumn([Parsed], "Data Source File", (r) => [Name], type text),
                    "Refresh Date", (r) => DateTime.LocalNow(), type datetime
                )
            ),

            Combined =
                if Table.RowCount(AddMeta) = 0 then
                    #table({"Data Source File","Refresh Date"}, {})
                else
                    Table.Combine(AddMeta[WithMeta])
        in
            Combined
in
    fnCombineFolder
