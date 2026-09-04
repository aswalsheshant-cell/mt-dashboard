// ==============================================================================
// scripts/ci/deploy_measures.cs
// Tabular Editor C# Script: Automated Batch Deployment of Primary & YoY Measures
// Usage: TabularEditor.exe "<PathToModel>" -S "scripts/ci/deploy_measures.cs"
// ==============================================================================

using System;
using System.Collections.Generic;

// 1. Target table for measures
string targetTableName = "_Measures";
Table measureTable;

if (!Model.Tables.Contains(targetTableName))
{
    // Create dedicated measures table if absent
    measureTable = Model.AddTable(targetTableName);
    measureTable.Description = "Central calculation group and measure repository for Modern Trade analytics.";

    // Add dummy hidden column required for empty table initialization
    if (!measureTable.Columns.Contains("Dummy"))
    {
        var dummyCol = measureTable.AddDataColumn("Dummy", "Dummy", DataType.String);
        dummyCol.IsHidden = true;
    }
}
else
{
    measureTable = Model.Tables[targetTableName];
}

// 2. Measure Definition Structure
class MeasureDefinition
{
    public string Name { get; set; }
    public string Expression { get; set; }
    public string FormatString { get; set; }
    public string DisplayFolder { get; set; }
    public string Description { get; set; }
}

// 3. Define measure inventory
var measuresToDeploy = new List<MeasureDefinition>
{
    new MeasureDefinition
    {
        Name = "Primary_NSV_FY25",
        Expression = @"CALCULATE(
    SUM('Fact_Primary_Derived_FY25'[Primary_NSV_Lakh]),
    'Dim_Date'[Fiscal_Year] = ""FY25""
)",
        FormatString = "\"₹\"#,##0.00\" L\";-\"₹\"#,##0.00\" L\";\"₹0.00 L\"",
        DisplayFolder = @"01. Primary Sales\FY Baselines",
        Description = "Synthesized FY25 primary net sales value baseline allocated to empirical store-article grain."
    },
    new MeasureDefinition
    {
        Name = "Primary_NSV_FY26",
        Expression = @"CALCULATE(
    SUM('Fact_Primary_Article_Monthly'[Primary_NSV_Lakh]),
    'Dim_Date'[Fiscal_Year] = ""FY26""
)",
        FormatString = "\"₹\"#,##0.00\" L\";-\"₹\"#,##0.00\" L\";\"₹0.00 L\"",
        DisplayFolder = @"01. Primary Sales\FY Baselines",
        Description = "Historical actual FY26 primary net sales value from direct distributor billing."
    },
    new MeasureDefinition
    {
        Name = "Primary_NSV_FY27",
        Expression = @"CALCULATE(
    SUM('Fact_Primary_Article_Monthly'[Primary_NSV_Lakh]),
    'Dim_Date'[Fiscal_Year] = ""FY27""
)",
        FormatString = "\"₹\"#,##0.00\" L\";-\"₹\"#,##0.00\" L\";\"₹0.00 L\"",
        DisplayFolder = @"01. Primary Sales\FY Baselines",
        Description = "Current run-rate FY27 YTD primary net sales value."
    },
    new MeasureDefinition
    {
        Name = "Unified_Primary_NSV",
        Expression = @"VAR SelectedFY = SELECTEDVALUE('Dim_Date'[Fiscal_Year])
RETURN
    SWITCH(
        SelectedFY,
        ""FY25"", [Primary_NSV_FY25],
        ""FY26"", [Primary_NSV_FY26],
        ""FY27"", [Primary_NSV_FY27],
        COALESCE([Primary_NSV_FY25], 0) +
        COALESCE([Primary_NSV_FY26], 0) +
        COALESCE([Primary_NSV_FY27], 0)
    )",
        FormatString = "\"₹\"#,##0.00\" L\";-\"₹\"#,##0.00\" L\";\"₹0.00 L\"",
        DisplayFolder = @"01. Primary Sales\Unified Analytics",
        Description = "Seamless 3-year unified primary NSV supporting dynamic slicer selection across FY25, FY26, and FY27."
    },
    new MeasureDefinition
    {
        Name = "Unified_Primary_NSV_PY",
        Expression = @"VAR CurrentFY = SELECTEDVALUE('Dim_Date'[Fiscal_Year])
RETURN
    SWITCH(
        CurrentFY,
        ""FY27"", [Primary_NSV_FY26],
        ""FY26"", [Primary_NSV_FY25],
        ""FY25"", BLANK(),
        BLANK()
    )",
        FormatString = "\"₹\"#,##0.00\" L\";-\"₹\"#,##0.00\" L\";\"₹0.00 L\"",
        DisplayFolder = @"01. Primary Sales\Unified Analytics",
        Description = "Prior-year primary NSV based on active fiscal year slicer context."
    },
    new MeasureDefinition
    {
        Name = "Unified_Primary_YoY_Growth_Lakh",
        Expression = @"VAR CurrentNSV = [Unified_Primary_NSV]
VAR PriorNSV = [Unified_Primary_NSV_PY]
RETURN
    IF(
        NOT ISBLANK(CurrentNSV) && NOT ISBLANK(PriorNSV),
        CurrentNSV - PriorNSV,
        BLANK()
    )",
        FormatString = "\"₹\"#,##0.00\" L\";-\"₹\"#,##0.00\" L\";\"₹0.00 L\"",
        DisplayFolder = @"02. YoY Growth & Variances",
        Description = "Absolute YoY expansion or contraction in ₹ Lakhs."
    },
    new MeasureDefinition
    {
        Name = "Unified_Primary_YoY_Growth_Pct",
        Expression = @"VAR CurrentNSV = [Unified_Primary_NSV]
VAR PriorNSV = [Unified_Primary_NSV_PY]
RETURN
    DIVIDE(
        CurrentNSV - PriorNSV,
        PriorNSV,
        BLANK()
    )",
        FormatString = "+0.0%;-0.0%;0.0%",
        DisplayFolder = @"02. YoY Growth & Variances",
        Description = "Percentage growth rate versus prior fiscal year."
    },
    new MeasureDefinition
    {
        Name = "YoY_Growth_FY25_to_FY26_Pct",
        Expression = @"DIVIDE(
    [Primary_NSV_FY26] - [Primary_NSV_FY25],
    [Primary_NSV_FY25],
    BLANK()
)",
        FormatString = "+0.0%;-0.0%;0.0%",
        DisplayFolder = @"02. YoY Growth & Variances\Step Growth",
        Description = "Direct growth rate from FY25 baseline to FY26 actuals."
    },
    new MeasureDefinition
    {
        Name = "YoY_Growth_FY26_to_FY27_Pct",
        Expression = @"DIVIDE(
    [Primary_NSV_FY27] - [Primary_NSV_FY26],
    [Primary_NSV_FY26],
    BLANK()
)",
        FormatString = "+0.0%;-0.0%;0.0%",
        DisplayFolder = @"02. YoY Growth & Variances\Step Growth",
        Description = "Run-rate growth from FY26 actuals to FY27 YTD actuals."
    },
    new MeasureDefinition
    {
        Name = "3Yr_Primary_CAGR",
        Expression = @"VAR BaseVal = [Primary_NSV_FY25]
VAR EndVal = [Primary_NSV_FY27]
RETURN
    IF(
        BaseVal > 0 && EndVal > 0,
        POWER(DIVIDE(EndVal, BaseVal), (1 / 2)) - 1,
        BLANK()
    )",
        FormatString = "+0.0%;-0.0%;0.0%",
        DisplayFolder = @"02. YoY Growth & Variances\Step Growth",
        Description = "2-period annualized compound growth rate spanning FY25 through FY27."
    }
};

// 4. Batch Execution Loop
int createdCount = 0;
int updatedCount = 0;

foreach (var mDef in measuresToDeploy)
{
    Measure measure;
    if (!measureTable.Measures.Contains(mDef.Name))
    {
        measure = measureTable.AddMeasure(mDef.Name, mDef.Expression);
        createdCount++;
    }
    else
    {
        measure = measureTable.Measures[mDef.Name];
        measure.Expression = mDef.Expression;
        updatedCount++;
    }

    measure.FormatString = mDef.FormatString;
    measure.DisplayFolder = mDef.DisplayFolder;
    measure.Description = mDef.Description;
}

// 5. Output Summary to Console
Output(string.Format("✓ Tabular Editor Deployment Complete: {0} measures created, {1} measures updated in table '{2}'.",
    createdCount, updatedCount, targetTableName));
