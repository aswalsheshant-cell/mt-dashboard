#!/bin/bash
# scaffold_report.sh — Pre-stage PBIP Report visual layer

REPO_ROOT="${1:-.}"
REPORT_DIR="$REPO_ROOT/ModernTrade_Report.Report"
DEF_DIR="$REPORT_DIR/definition"

mkdir -p "$DEF_DIR"

# Create definition.pbir
cat > "$REPORT_DIR/definition.pbir" << 'EOF'
{
  "version": "1.0",
  "datasetReference": {
    "byPath": {
      "path": "../ModernTrade_Report.Dataset"
    },
    "byConnection": null
  }
}
EOF

# Create version.json
cat > "$DEF_DIR/version.json" << 'EOF'
{
  "version": "2.0"
}
EOF

# Create report.json
cat > "$DEF_DIR/report.json" << 'EOF'
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
EOF

echo "[PASS] ModernTrade_Report.Report scaffolded. 3 files created."
