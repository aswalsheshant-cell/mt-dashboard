// ============================================================
// MT Dashboard — Batch Import All DAX Measures (~480 measures)
// Run in: Tabular Editor 3 (or TE2) → C# Script (Advanced Scripting)
//
// PRE-REQUISITES:
//   1. All PQ queries loaded (Close & Apply done)
//   2. Date Table created (Modeling → New Table → paste 00_DateTable.dax)
//   3. Script 01 (relationships) already run
//
// WHAT THIS DOES:
//   - Reads every .dax file from your local PowerBI/DAX/ folder
//   - Parses measure definitions (Name = Expression)
//   - Creates each measure on the _Measures table
//   - Skips 00_DateTable.dax (calculated table, not measures)
//   - Flags calculated columns from files 10, 12, 13 (add manually)
//
// CHANGE THIS PATH to match your local repo:
// ============================================================

var daxFolder = @"C:\MT-Dashboard\PowerBI\DAX";

// ── Ensure _Measures table exists ─────────────────────────────
var measuresTable = "_Measures";
if (!Model.Tables.Contains(measuresTable)) {
    var t = Model.AddCalculatedTable(measuresTable,
        "ROW(\"Placeholder\", BLANK())");
    Info("Created _Measures table");
}
var mTable = Model.Tables[measuresTable];

// ── Files to skip entirely (calculated table) ─────────────────
var skipFiles = new HashSet<string>(StringComparer.OrdinalIgnoreCase) {
    "00_DateTable.dax"
};

// ── Files containing calculated columns (not measures) ────────
// These files ALSO have normal measures — the script imports
// those. The calc-column definitions are detected and skipped.
var calcColWarnings = new Dictionary<string, string>(
    StringComparer.OrdinalIgnoreCase)
{
    { "10_SIS_Reconciliation.dax",
      "Fact Offtake Sales[Offtake Channel]" },
    { "12_TOT_Measures.dax",
      "Fact Primary Article[TOT Method], [TOT Pass-on Value]" },
    { "13_CM2_Measures.dax",
      "PL Expense Input[Resolved Chain/Brand/Category/Bad Brand Or Category]" }
};

int created = 0, skipped = 0, errors = 0;
var calcColsFound = new List<string>();

foreach (var file in System.IO.Directory
        .GetFiles(daxFolder, "*.dax")
        .OrderBy(f => f))
{
    var fileName = System.IO.Path.GetFileName(file);
    if (skipFiles.Contains(fileName)) {
        Info("SKIP file (calculated table): " + fileName);
        continue;
    }

    var content = System.IO.File.ReadAllText(file);
    var lines = content.Split(new[] { "\r\n", "\n" },
        StringSplitOptions.None);

    string currentName = null;
    var currentDAX = new System.Text.StringBuilder();
    bool isCalcCol = false;
    bool inCommentBlock = false;

    for (int i = 0; i <= lines.Length; i++)
    {
        var line = i < lines.Length ? lines[i] : null;
        var trimmed = line?.TrimStart() ?? "";

        // Track block comments
        if (trimmed.StartsWith("/*")) inCommentBlock = true;
        if (inCommentBlock) {
            if (trimmed.Contains("*/")) inCommentBlock = false;
            if (line != null && currentName != null)
                continue;
            if (line != null) continue;
        }

        // Skip single-line comments at the start of a definition
        if (trimmed.StartsWith("//") && currentName == null)
            continue;

        bool isNewMeasure = false;
        string newName = null;
        string firstExpr = null;

        if (line != null && !trimmed.StartsWith("//")) {
            // Detect calculated column: 'TableName'[ColName] =
            var calcMatch = System.Text.RegularExpressions
                .Regex.Match(trimmed,
                @"^'[^']+'\[([^\]]+)\]\s*=");
            if (calcMatch.Success) {
                isCalcCol = true;
                // Still parse it so we can skip cleanly
            }

            // Match: MeasureName = expression
            // or:    [Measure Name] = expression
            var m = System.Text.RegularExpressions
                .Regex.Match(trimmed,
                @"^(?:\[([^\]]+)\]|([A-Za-z_][A-Za-z0-9_ ]*?))\s*=\s*");
            if (m.Success && !trimmed.StartsWith("//")
                && !calcMatch.Success)
            {
                isNewMeasure = true;
                newName = m.Groups[1].Success
                    ? m.Groups[1].Value.Trim()
                    : m.Groups[2].Value.Trim();
                firstExpr = line.Substring(
                    line.IndexOf("=") + 1).Trim();
            }
        }

        // Save previous measure when we hit a new one or EOF
        if ((isNewMeasure || isCalcCol || line == null)
            && currentName != null)
        {
            var dax = currentDAX.ToString().Trim();
            if (!string.IsNullOrEmpty(dax)) {
                try {
                    if (!mTable.Measures.Any(
                        x => x.Name == currentName))
                    {
                        var measure = mTable.AddMeasure(
                            currentName, dax);
                        measure.Description =
                            "Source: " + fileName;
                        created++;
                    } else {
                        skipped++;
                    }
                }
                catch (Exception ex) {
                    Info("ERR [" + currentName + "]: "
                         + ex.Message);
                    errors++;
                }
            }
            currentName = null;
            currentDAX.Clear();
        }

        // Handle calc column — log and skip
        if (isCalcCol) {
            calcColsFound.Add(fileName + " → " + trimmed
                .Substring(0, Math.Min(trimmed.Length, 60)));
            isCalcCol = false;
            currentName = null;
            currentDAX.Clear();
            continue;
        }

        if (isNewMeasure) {
            currentName = newName;
            currentDAX.Clear();
            currentDAX.AppendLine(firstExpr);
        }
        else if (currentName != null && line != null) {
            currentDAX.AppendLine(line);
        }
    }
}

// ── Summary ───────────────────────────────────────────────────
Info("═══════════════════════════════════════════════");
Info("Measures created:       " + created);
Info("Already existed:        " + skipped);
Info("Errors:                 " + errors);
Info("═══════════════════════════════════════════════");

if (calcColsFound.Count > 0) {
    Info("");
    Info("CALCULATED COLUMNS found (add manually on each table):");
    foreach (var cc in calcColsFound)
        Info("  • " + cc);
    Info("");
    Info("To add: right-click the table → New Calculated Column");
    Info("  → paste the DAX expression from the .dax file.");
    Info("  File 10 → Fact Offtake Sales[Offtake Channel]");
    Info("  File 12 → Fact Primary Article[TOT Method],");
    Info("            Fact Primary Article[TOT Pass-on Value]");
    Info("  File 13 → PL Expense Input[Resolved Chain],");
    Info("            [Resolved Brand], [Resolved Category],");
    Info("            [Bad Brand Or Category]");
}

Info("");
Info("Save to Power BI: Ctrl+S in Tabular Editor.");
