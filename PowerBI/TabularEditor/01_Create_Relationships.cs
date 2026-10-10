// ============================================================
// MT Dashboard — Create All Relationships
// Run in: Tabular Editor 3 (or TE2) → C# Script (Advanced Scripting)
// Source: PowerBI/docs/DataModel.md
//
// PRE-REQUISITE: All Power Query tables must be loaded first
// (paste from QuickSetup/AllPowerQuery_Consolidated.txt, Close & Apply).
// ============================================================

// Helper: create a single-direction 1:* relationship
void AddRel(string dimTable, string dimCol,
            string factTable, string factCol)
{
    if (!Model.Tables.Contains(dimTable)) {
        Info("SKIP — dimension table missing: " + dimTable);
        return;
    }
    if (!Model.Tables.Contains(factTable)) {
        Info("SKIP — fact table missing: " + factTable);
        return;
    }
    if (!Model.Tables[dimTable].Columns.Contains(dimCol)) {
        Info("SKIP — column missing: " + dimTable + "[" + dimCol + "]");
        return;
    }
    if (!Model.Tables[factTable].Columns.Contains(factCol)) {
        Info("SKIP — column missing: " + factTable + "[" + factCol + "]");
        return;
    }

    // Check if relationship already exists
    foreach (var existing in Model.Relationships) {
        if (existing.ToTable.Name == dimTable
            && existing.ToColumn.Name == dimCol
            && existing.FromTable.Name == factTable
            && existing.FromColumn.Name == factCol)
        {
            Info("EXISTS: " + dimTable + "[" + dimCol + "] → "
                 + factTable + "[" + factCol + "]");
            return;
        }
    }

    try {
        var rel = Model.AddRelationship();
        rel.FromColumn = Model.Tables[factTable].Columns[factCol];
        rel.ToColumn   = Model.Tables[dimTable].Columns[dimCol];
        rel.CrossFilteringBehavior = CrossFilteringBehavior.OneDirection;
        Info("OK: " + dimTable + "[" + dimCol + "] 1→* "
             + factTable + "[" + factCol + "]");
    }
    catch (Exception ex) {
        Info("ERROR: " + dimTable + " → " + factTable + ": " + ex.Message);
    }
}

int before = Model.Relationships.Count;

// ── Date Table → Facts (9 relationships) ──────────────────────
AddRel("Date Table",    "Date",       "Fact Primary Sales",     "Week Start Date");
AddRel("Date Table",    "MonthStart", "Fact Offtake Sales",     "MonthStart");
AddRel("Date Table",    "MonthStart", "Fact P&L",               "MonthStart");
AddRel("Date Table",    "MonthStart", "Fact Nielsen",           "MonthStart");
AddRel("Date Table",    "MonthStart", "Fact TDP",               "MonthStart");
AddRel("Date Table",    "MonthStart", "Targets",                "MonthStart");
AddRel("Date Table",    "MonthStart", "Fact Primary ShipTo",    "MonthStartCalc");
AddRel("Date Table",    "MonthStart", "Fact Primary Article",   "MonthStart");
AddRel("Date Table",    "MonthStart", "PL Expense Input",       "MonthStart");

// ── Chain Master → Facts (7 relationships) ────────────────────
AddRel("Chain Master",  "Chain", "Fact Offtake Sales",     "Chain");
AddRel("Chain Master",  "Chain", "Fact Primary Sales",     "Chain");
AddRel("Chain Master",  "Chain", "Fact P&L",               "Chain");
AddRel("Chain Master",  "Chain", "Fact TDP",               "Chain");
AddRel("Chain Master",  "Chain", "Fact Primary ShipTo",    "Chain");
AddRel("Chain Master",  "Chain", "Fact Primary Article",   "Chain");
AddRel("Chain Master",  "Chain", "Fact Account Category",  "Chain");

// ── Brand Master → Facts (6 relationships) ────────────────────
AddRel("Brand Master",  "Brand", "Fact Offtake Sales",     "Brand");
AddRel("Brand Master",  "Brand", "Fact Primary Sales",     "Brand");
AddRel("Brand Master",  "Brand", "Fact P&L",               "Brand");
AddRel("Brand Master",  "Brand", "Fact TDP",               "Brand");
AddRel("Brand Master",  "Brand", "Fact Nielsen",           "Brand");
AddRel("Brand Master",  "Brand", "Fact Primary Article",   "Brand");

// ── Category Master → Facts (6 relationships) ─────────────────
AddRel("Category Master", "Category",         "Fact Offtake Sales",    "Category");
AddRel("Category Master", "Category",         "Fact Primary Sales",    "Category");
AddRel("Category Master", "Category",         "Fact P&L",              "Category");
AddRel("Category Master", "Category",         "Fact TDP",              "Category");
AddRel("Category Master", "Nielsen Category", "Fact Nielsen",          "Nielsen Category");
AddRel("Category Master", "Category",         "Fact Primary Article",  "Category");

// ── Article Master → Facts (3 relationships) ──────────────────
AddRel("Article Master", "Article Code", "Fact Offtake Sales",  "Article Code");
AddRel("Article Master", "Article Code", "Fact Primary Sales",  "Article Code");
AddRel("Article Master", "Article Code", "Fact TDP",            "Article Code");

// ── Store Master → Facts (3 relationships) ────────────────────
AddRel("Store Master",   "Store Code", "Fact Offtake Sales",  "Store Code");
AddRel("Store Master",   "Store Code", "Fact Primary Sales",  "Store Code");
AddRel("Store Master",   "Store Code", "Store SO Mapping",    "Store Code");

// ── Zone State Master (1 relationship) ────────────────────────
AddRel("Zone State Master", "Zone", "Fact Offtake Sales", "Zone");

// ── Ship-To Master (1 relationship) ──────────────────────────
AddRel("Ship-To Master", "Ship To Name", "Fact Primary ShipTo", "Ship To Name");

// ── Brand Master → Fact Primary ShipTo (1 relationship) ──────
AddRel("Brand Master", "Brand", "Fact Primary ShipTo", "Brand");

// ── Nielsen Competitor Master (1 relationship) ────────────────
AddRel("Nielsen Competitor Master", "Brand", "Fact Nielsen Brand Cut", "Brand");

// ── Fact Nielsen Pack (2 relationships) ───────────────────────
AddRel("Date Table",      "MonthStart",       "Fact Nielsen Pack",     "MonthStart");
AddRel("Category Master", "Nielsen Category",  "Fact Nielsen Pack",     "Nielsen Category");

// ── Fact Account Category (1 more — Date already above) ──────
AddRel("Date Table", "MonthStart", "Fact Account Category", "MonthStart");

// ── Fact Account Category Geo (2 relationships) ──────────────
AddRel("Date Table",   "MonthStart", "Fact Account Category Geo", "MonthStart");
AddRel("Chain Master", "Chain",      "Fact Account Category Geo", "Chain");

// ── Fact Account Assortment (2 relationships) ────────────────
AddRel("Date Table",   "MonthStart", "Fact Account Assortment", "MonthStart");
AddRel("Chain Master", "Chain",      "Fact Account Assortment", "Chain");

// ── Fact Nielsen Brand Cut — Date (1 relationship) ───────────
AddRel("Date Table", "MonthStart", "Fact Nielsen Brand Cut", "MonthStart");

// ── Store City Master (1 relationship) ───────────────────────
AddRel("Fact Offtake Sales", "Match Key", "Store City Master", "Match Key");

// ── Visit City List (1 relationship) ─────────────────────────
AddRel("Visit City List", "City", "Store City Master", "Visit City");

int after = Model.Relationships.Count;
Info("═══════════════════════════════════════════════");
Info("Relationships before: " + before);
Info("Relationships after:  " + after);
Info("Created:              " + (after - before));
Info("═══════════════════════════════════════════════");
Info("Save to Power BI: Ctrl+S in Tabular Editor.");
