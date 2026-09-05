# Scaffold-Report.ps1 — Pre-stage PBIP Report visual layer
param([string]$RepoRoot = ".")

$ReportDir = "$RepoRoot/ModernTrade_Report.Report"
$DefDir = "$ReportDir/definition"

if (!(Test-Path $DefDir)) {
    New-Item -ItemType Directory -Force -Path $DefDir | Out-Null
}

# Create definition.pbir (dataset binding)
@"
{
  "version": "1.0",
  "datasetReference": {
    "byPath": {
      "path": "../ModernTrade_Report.Dataset"
    },
    "byConnection": null
  }
}
"@ | Set-Content "$ReportDir/definition.pbir"

# Create version.json
@"
{
  "version": "2.0"
}
"@ | Set-Content "$DefDir/version.json"

# Create report.json (visual layout)
@"
{
  "name": "Page 1",
  "displayName": "Finance Dashboard",
  "pageHeight": 1.0,
  "pageWidth": 1.6,
  "objects": {
    "pivotTable1": {
      "objectMetadata": {
        "objectId": "fb8c4e00-01ff-4000-8000-000000000001"
      },
      "properties": {
        "values": [
          { "queryRef": "[NSV_Jun26_Allocated]" },
          { "queryRef": "[Contribution_Margin_INR]" },
          { "queryRef": "[Cont_Margin_Pct]" },
          { "queryRef": "[Cont_Margin_Badge]" }
        ],
        "rows": [
          { "queryRef": "[Chain_Name]" },
          { "queryRef": "[Category_Name]" }
        ],
        "formatters": [
          {
            "measure": "[Cont_Margin_Pct]",
            "formatting": { "formatType": "percentage", "precision": 1 }
          },
          {
            "measure": "[Cont_Margin_Badge]",
            "fontColor": "[Cont_Margin_Color]"
          }
        ]
      }
    }
  }
}
"@ | Set-Content "$DefDir/report.json"

Write-Host "[PASS] ModernTrade_Report.Report scaffolded. 3 files created."
