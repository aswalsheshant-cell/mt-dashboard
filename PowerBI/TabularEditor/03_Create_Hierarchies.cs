// ============================================================
// MT Dashboard — Create Hierarchies + Set Sort Orders
// Run in: Tabular Editor 3 (or TE2) → C# Script (Advanced Scripting)
// Source: PowerBI/docs/DataModel.md § Hierarchies
//
// PRE-REQUISITES:
//   1. All PQ queries loaded
//   2. Scripts 01 + 02 already run
//
// CREATES:
//   4 hierarchies (Geography, Product, Product Pack, Time FY)
//   4 sort-by-column orders (Zone, Month, Brand, Category)
// ============================================================

// Helper: add hierarchy on a table
void AddHierarchy(string tableName, string hierName,
    string[] levels)
{
    if (!Model.Tables.Contains(tableName)) {
        Info("SKIP — table missing: " + tableName);
        return;
    }
    var table = Model.Tables[tableName];

    // Remove existing hierarchy with same name
    if (table.Hierarchies.Contains(hierName))
        table.Hierarchies[hierName].Delete();

    var h = table.AddHierarchy(hierName);
    int added = 0;
    foreach (var col in levels) {
        if (table.Columns.Contains(col)) {
            h.AddLevel(table.Columns[col]);
            added++;
        }
        else
            Info("  SKIP level (column missing): "
                 + tableName + "[" + col + "]");
    }
    Info("OK: " + tableName + " → " + hierName
         + " (" + added + "/" + levels.Length + " levels)");
}

// Helper: set sort-by-column
void SetSort(string table, string col, string sortBy) {
    if (!Model.Tables.Contains(table)) return;
    var t = Model.Tables[table];
    if (!t.Columns.Contains(col)) {
        Info("SKIP sort — column missing: "
             + table + "[" + col + "]");
        return;
    }
    if (!t.Columns.Contains(sortBy)) {
        Info("SKIP sort — sort column missing: "
             + table + "[" + sortBy + "]");
        return;
    }
    t.Columns[col].SortByColumn = t.Columns[sortBy];
    Info("SORT: " + table + "[" + col + "] by [" + sortBy + "]");
}

// ── Geography Hierarchy ───────────────────────────────────────
// Zone → State (on Zone State Master)
// Chain and Store drill via Store Master relationships
AddHierarchy("Zone State Master", "Geography",
    new[] { "Zone", "State" });

// ── Product Hierarchy ─────────────────────────────────────────
// Category → Sub-category → Brand → Article Code
AddHierarchy("Article Master", "Product",
    new[] { "Category", "Sub-category",
            "Brand", "Article Code" });

// ── Product (Pack) Hierarchy ──────────────────────────────────
// Category → Brand → Pack Size → Article Code
AddHierarchy("Article Master", "Product (Pack)",
    new[] { "Category", "Brand",
            "Pack Size", "Article Code" });

// ── Time (FY) Hierarchy ───────────────────────────────────────
// FY Year → Quarter → Month Name
// Indian FY: Apr–Mar, not calendar year
AddHierarchy("Date Table", "Time (FY)",
    new[] { "FY Year", "Quarter", "Month Name" });

// ── Sort Orders ───────────────────────────────────────────────
SetSort("Zone State Master", "Zone",       "Zone Sort Order");
SetSort("Date Table",        "Month Name", "Month Year Sort");
SetSort("Brand Master",      "Brand",      "Brand Sort Order");
SetSort("Category Master",   "Category",   "Category Sort Order");

Info("");
Info("═══════════════════════════════════════════════");
Info("4 hierarchies + 4 sort orders set.");
Info("Save to Power BI: Ctrl+S in Tabular Editor.");
Info("═══════════════════════════════════════════════");
