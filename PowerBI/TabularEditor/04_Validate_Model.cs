// ============================================================
// MT Dashboard — Model Validation Check
// Run in: Tabular Editor 3 (or TE2) → C# Script (Advanced Scripting)
//
// Run this AFTER scripts 01, 02, 03 to verify the model.
// It checks: table count, relationship count, measure count,
// hierarchy count, sort orders, orphan tables, and DAX errors.
// ============================================================

var sb = new System.Text.StringBuilder();
sb.AppendLine("╔═══════════════════════════════════════════╗");
sb.AppendLine("║   MT Dashboard — Model Validation Report  ║");
sb.AppendLine("╚═══════════════════════════════════════════╝");
sb.AppendLine();

bool allGood = true;

// ── 1. Table count ────────────────────────────────────────────
var tables = Model.Tables
    .Where(t => t.ObjectType == ObjectType.Table)
    .ToList();
sb.AppendLine("Tables:         " + tables.Count);

// ── 2. Relationship count ─────────────────────────────────────
int relCount = Model.Relationships.Count;
sb.AppendLine("Relationships:  " + relCount);
if (relCount < 36) {
    sb.AppendLine("  ⚠ Expected at least 36 — check Script 01 output");
    allGood = false;
}

// ── 3. Measure count ─────────────────────────────────────────
int measureCount = Model.AllMeasures.Count();
sb.AppendLine("Measures:       " + measureCount);
if (measureCount < 400) {
    sb.AppendLine("  ⚠ Expected ~480 — check Script 02 output");
    allGood = false;
}

// ── 4. Hierarchy count ────────────────────────────────────────
int hierCount = tables.SelectMany(t => t.Hierarchies).Count();
sb.AppendLine("Hierarchies:    " + hierCount);
if (hierCount < 4) {
    sb.AppendLine("  ⚠ Expected 4 — check Script 03 output");
    allGood = false;
}

// ── 5. Date Table check ──────────────────────────────────────
sb.AppendLine();
if (Model.Tables.Contains("Date Table")) {
    var dt = Model.Tables["Date Table"];
    sb.AppendLine("Date Table:     present");
    sb.AppendLine("  DataCategory: " + dt.DataCategory);
    if (dt.DataCategory != "Time")
        sb.AppendLine("  ⚠ Mark as date table: Modeling → "
            + "Mark as date table → [Date]");
} else {
    sb.AppendLine("Date Table:     MISSING!");
    sb.AppendLine("  → Create via: Modeling → New Table → "
        + "paste 00_DateTable.dax");
    allGood = false;
}

// ── 6. _Measures table check ─────────────────────────────────
if (Model.Tables.Contains("_Measures")) {
    sb.AppendLine("_Measures:      present ("
        + Model.Tables["_Measures"].Measures.Count()
        + " measures)");
} else {
    sb.AppendLine("_Measures:      MISSING — run Script 02");
    allGood = false;
}

// ── 7. Key dimension tables ──────────────────────────────────
sb.AppendLine();
sb.AppendLine("Key dimension tables:");
var requiredDims = new[] {
    "Chain Master", "Brand Master", "Category Master",
    "Article Master", "Store Master", "Zone State Master",
    "Ship-To Master"
};
foreach (var dim in requiredDims) {
    if (Model.Tables.Contains(dim))
        sb.AppendLine("  ✓ " + dim);
    else {
        sb.AppendLine("  ✗ " + dim + " — MISSING");
        allGood = false;
    }
}

// ── 8. Key fact tables ───────────────────────────────────────
sb.AppendLine();
sb.AppendLine("Key fact tables:");
var requiredFacts = new[] {
    "Fact Primary Sales", "Fact Offtake Sales", "Fact P&L",
    "Fact Nielsen", "Fact TDP", "Fact Primary ShipTo",
    "Fact Primary Article"
};
foreach (var fact in requiredFacts) {
    if (Model.Tables.Contains(fact)) {
        int rels = Model.Relationships
            .Where(r => r.FromTable.Name == fact
                     || r.ToTable.Name == fact)
            .Count();
        sb.AppendLine("  ✓ " + fact + " (" + rels + " rels)");
    }
    else {
        sb.AppendLine("  ✗ " + fact + " — MISSING");
        allGood = false;
    }
}

// ── 9. Disconnected tables (expected: helpers) ───────────────
sb.AppendLine();
sb.AppendLine("Disconnected tables (no relationships):");
int disconnected = 0;
foreach (var t in tables) {
    int rels = Model.Relationships
        .Where(r => r.FromTable == t || r.ToTable == t)
        .Count();
    if (rels == 0) {
        sb.AppendLine("  • " + t.Name);
        disconnected++;
    }
}
if (disconnected == 0)
    sb.AppendLine("  (none)");
sb.AppendLine("  Expected disconnected: Primary Allocation Map,");
sb.AppendLine("    Override, Assumption Table, Forecast Override,");
sb.AppendLine("    GST Rate QC Table, GST Config, CustCode Chain Map");

// ── 10. Sort-by-column audit ─────────────────────────────────
sb.AppendLine();
sb.AppendLine("Sort-by-column settings:");
int sortCount = 0;
foreach (var t in tables) {
    foreach (var c in t.Columns
        .Where(c => c.SortByColumn != null))
    {
        sb.AppendLine("  " + t.Name + "[" + c.Name + "]"
            + " → [" + c.SortByColumn.Name + "]");
        sortCount++;
    }
}
if (sortCount == 0)
    sb.AppendLine("  (none set — run Script 03)");

// ── 11. Measures with DAX errors ─────────────────────────────
sb.AppendLine();
var errMeasures = Model.AllMeasures
    .Where(m => !string.IsNullOrEmpty(m.ErrorMessage))
    .ToList();
sb.AppendLine("Measures with errors: " + errMeasures.Count);
if (errMeasures.Count > 0) {
    allGood = false;
    foreach (var m in errMeasures.Take(15)) {
        sb.AppendLine("  ✗ " + m.Name);
        sb.AppendLine("    " + m.ErrorMessage);
    }
    if (errMeasures.Count > 15)
        sb.AppendLine("  ... and "
            + (errMeasures.Count - 15) + " more");
}

// ── 12. Hierarchy detail ─────────────────────────────────────
sb.AppendLine();
sb.AppendLine("Hierarchy detail:");
foreach (var t in tables) {
    foreach (var h in t.Hierarchies) {
        sb.AppendLine("  " + t.Name + " → " + h.Name);
        foreach (var l in h.Levels)
            sb.AppendLine("    " + (l.Ordinal + 1) + ". "
                + l.Column.Name);
    }
}

// ── Final verdict ────────────────────────────────────────────
sb.AppendLine();
sb.AppendLine("═══════════════════════════════════════════");
if (allGood)
    sb.AppendLine("✓ ALL CHECKS PASSED — model looks complete.");
else
    sb.AppendLine("⚠ SOME CHECKS FAILED — review items above.");
sb.AppendLine("═══════════════════════════════════════════");

Info(sb.ToString());
