# agent/metadata — Power BI metadata exports (drop zone)

Everything in this folder is optional and stays local (heavy exports are
gitignored). The agent uses whatever it finds here to upgrade its checks
from "docs-derived" to "exact model":

| Drop here | How to produce it | What it unlocks |
|---|---|---|
| `model.bim` or `database.json` | Tabular Editor → File → Save As (TMSL) | exact table/column/measure inventory → DAX003 unknown-table check at full strength + DAX006 unknown-measure check |
| `INFO.TABLES.csv`, `INFO.COLUMNS.csv`, `INFO.MEASURES.csv` | DAX Studio → `EVALUATE INFO.TABLES()` (etc.) → export CSV | same as above, no Tabular Editor needed |
| `*.pdf` | any exported leadership deck / SOP | gets parsed into the `ask` knowledge index (needs `pip install pypdf`) |

After adding or updating files run:

    python -m mtagent index      # refresh the knowledge index
    python -m mtagent check-dax  # re-lint against the exact inventory
