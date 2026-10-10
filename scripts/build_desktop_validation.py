"""Write the Desktop validation queries and runbook with expected values filled in.

Outputs (rebuilt from PowerBI/reconciliation_expected.json and PowerBI/model.bim, so
the numbers cannot go stale):
  PowerBI/TabularEditor/05_DAXStudio_Validation.dax   run in DAX Studio against the open model
  docs/evidence/POWERBI_DESKTOP_RUNBOOK.md            the steps and a results table to fill in

Every table, column and measure used is checked against model.bim before writing.

Usage: python scripts/build_desktop_validation.py
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBI = ROOT / "PowerBI"
EXP = json.loads((PBI / "reconciliation_expected.json").read_text(encoding="utf-8"))
MODEL = json.loads((PBI / "model.bim").read_text(encoding="utf-8"))["model"]
OUT_DAX = PBI / "TabularEditor" / "05_DAXStudio_Validation.dax"
OUT_MD = ROOT / "docs" / "evidence" / "POWERBI_DESKTOP_RUNBOOK.md"


def fmt(x):
    return "{:,.2f}".format(float(x))


ch = EXP["primary_article_by_channel"]["fy_channel_lakh"]
off = EXP["offtake"]
off_m = off["gross"]["monthly_lakh"]
off_gm = off["governed_ex_reliance_brand_counter"]["monthly_lakh"]
off_fy27 = off["gross"]["fy_lakh"]["FY27"]
off_fy27_gov = off["governed_ex_reliance_brand_counter"]["fy_lakh"]["FY27"]
pa_all = EXP["primary_article"]["gross"]["fy_lakh"]
st = EXP["primary_shipto"]["fy_lakh"]
chk = EXP["offtake_chain_master_check"]
toth = EXP["secondary_tot_hierarchy"]
mt_cm = chk["by_master_channel"]["MT"]
rbc_cm = chk["by_master_channel"]["RBC"]
eb_cm = chk["by_master_channel"].get("EB2B", "0")
unm_tot = chk["unmatched_total_lakh"]
unm = ", ".join("%s %s" % (k, fmt(v)) for k, v in chk["unmatched_chains_lakh"].items())

CHECKS = [
    # id, title, expected text, DAX
    ("Q1", "Row counts (tables that should have data must be above 0; empty watch folders show 0)",
     "Primary Article, Offtake, ShipTo, Secondary, Claim Master, Promo above 0. Primary Sales, Nielsen, TDP are 0 until their files arrive.",
     """EVALUATE
UNION(
  ROW("Table", "Fact Primary Article", "Rows", COUNTROWS('Fact Primary Article')),
  ROW("Table", "Fact Offtake Sales", "Rows", COUNTROWS('Fact Offtake Sales')),
  ROW("Table", "Fact Primary ShipTo", "Rows", COUNTROWS('Fact Primary ShipTo')),
  ROW("Table", "Fact Secondary Sales", "Rows", COUNTROWS('Fact Secondary Sales')),
  ROW("Table", "Fact Claim Master", "Rows", COUNTROWS('Fact Claim Master')),
  ROW("Table", "Dim Promo Calendar", "Rows", COUNTROWS('Dim Promo Calendar')),
  ROW("Table", "Fact Primary Sales", "Rows", COUNTROWS('Fact Primary Sales')),
  ROW("Table", "Fact Nielsen", "Rows", COUNTROWS('Fact Nielsen')),
  ROW("Table", "Fact TDP", "Rows", COUNTROWS('Fact TDP'))
)
ORDER BY [Rows] DESC"""),
    ("Q2", "Primary Article NSV by FY and Channel (Rs lakh)",
     "Default pPrimaryChannel = MT, so only MT rows load: FY 25-26 MT %s and FY 26-27 (Apr-Aug) MT %s, with no EB2B or SIS rows. With pPrimaryChannel = ALL you would also see EB2B %s and SIS %s for FY 25-26 (total %s)." % (
         fmt(ch["FY26"]["MT"]), fmt(ch["FY27"]["MT"]), fmt(ch["FY26"]["EB2B"]), fmt(ch["FY26"]["SIS"]), fmt(pa_all["FY26"])),
     """EVALUATE
SUMMARIZECOLUMNS(
  'Date Table'[FY Year],
  'Fact Primary Article'[Channel],
  "NSV Lakh", DIVIDE([Total Primary NSV], 100000)
)
ORDER BY 'Date Table'[FY Year], 'Fact Primary Article'[Channel]"""),
    ("Q3", "FY 25-26 Primary NSV (Rs lakh)",
     "%s with the default pPrimaryChannel = MT (the MT basis). It reads %s only if the parameter is set to ALL." % (fmt(ch["FY26"]["MT"]), fmt(pa_all["FY26"])),
     """EVALUATE
ROW(
  "FY26 Primary NSV Lakh", CALCULATE([Total Primary NSV], 'Date Table'[FY Year] = "25-26") / 100000
)"""),
    ("Q4", "Offtake Apr-Aug 2026, gross and MT split (Rs lakh)",
     "Gross [Total Offtake NSV] %s. [Total MT NSV] %s, [Total RBC NSV] %s and EB2B %s (Chain Master channel, after the alias step in query 11). FSN is EB2B (owner decision 2026-10-10), so MT + EB2B = %s, the dashboard figure ex Reliance Brand Counter (%s). Chains with no Chain Master row: %s L (%s)." % (
         fmt(off_fy27), fmt(mt_cm), fmt(rbc_cm), fmt(eb_cm), fmt(float(mt_cm) + float(eb_cm)), fmt(off_fy27_gov), fmt(unm_tot), unm or "none"),
     """EVALUATE
ROW(
  "Gross Offtake Lakh", CALCULATE([Total Offtake NSV], 'Date Table'[FY Year] = "26-27") / 100000,
  "MT (ex RBC) Lakh", CALCULATE([Total MT NSV], 'Date Table'[FY Year] = "26-27") / 100000,
  "RBC Lakh", CALCULATE([Total RBC NSV], 'Date Table'[FY Year] = "26-27") / 100000,
  "EB2B Lakh", CALCULATE([Total Offtake NSV], 'Chain Master'[Channel] = "EB2B", 'Date Table'[FY Year] = "26-27") / 100000
)"""),
    ("Q5", "Offtake by month, gross and MT ex Reliance Brand Counter (Rs lakh)",
     "Gross: " + "; ".join("%s %s" % (m, fmt(v)) for m, v in sorted(off_m.items())) + ". Dashboard ex RBC (data.js; [Total MT NSV] will be lower by the unmatched chains, see Q4): " + "; ".join("%s %s" % (m, fmt(v)) for m, v in sorted(off_gm.items())),
     """EVALUATE
SUMMARIZECOLUMNS(
  'Date Table'[MonthStart],
  "Gross Offtake Lakh", DIVIDE([Total Offtake NSV], 100000),
  "MT ex RBC Lakh", DIVIDE([Total MT NSV], 100000)
)
ORDER BY 'Date Table'[MonthStart]"""),
    ("Q6", "Primary ShipTo NSV by FY (Rs lakh). Catches the double-load of overlapping snapshot files",
     "FY 24-25 %s, FY 25-26 %s, FY 26-27 %s (Apr-Jul only; the composite file has no Jun-26 and no Aug-26 rows). If FY 25-26 is near double (about 65,800), the two subset files are being loaded again." % (
         fmt(st["FY25"]), fmt(st["FY26"]), fmt(st["FY27"])),
     """EVALUATE
SUMMARIZECOLUMNS(
  'Date Table'[FY Year],
  "ShipTo NSV Lakh", DIVIDE(SUM('Fact Primary ShipTo'[Primary NSV]), 100000)
)
ORDER BY 'Date Table'[FY Year]"""),
    ("Q6b", "Promo sell-out table (Fact Secondary TOT Hierarchy), NSV by month (Rs lakh)",
     "%d rows. " % toth["rows"] + "; ".join("%s %s" % (m, fmt(x)) for m, x in toth["monthly_lakh"].items()) + ". Total %s. %d of %d promo EANs find sell-out (the others have no Apr-Aug sell-out rows)." % (
         fmt(toth["total_lakh"]), toth["promo_ean_found_in_sellout"], toth["promo_ean_count"]),
     """EVALUATE
ROW(
  "Rows", COUNTROWS('Fact Secondary TOT Hierarchy'),
  "Total NSV Lakh", SUM('Fact Secondary TOT Hierarchy'[NSV_Lakh]),
  "Promoted NSV Lakh", [Actual Promoted NSV Lakh],
  "Promoted SKU Breadth %", [Promoted SKU Breadth %]
)"""),
    ("Q7", "Primary Article rows with no Chain (header-spelling bug check)",
     "0, or only rows that are genuinely unmapped distributor rows. A count in the tens of thousands means the Chain column is not being read.",
     """EVALUATE
ROW(
  "Rows with blank Chain", COUNTROWS(FILTER('Fact Primary Article', ISBLANK('Fact Primary Article'[Chain]))),
  "Total rows", COUNTROWS('Fact Primary Article')
)"""),
    ("Q8", "Promo contribution placeholder check",
     "Minimum is blank or above -1,000,000,000. A value near -9.2e18 means the placeholder cleanup did not run.",
     """EVALUATE
ROW(
  "Min Chain_Contribution_Pct", MIN('Dim Promo Calendar'[Chain_Contribution_Pct]),
  "Min Total_Contribution_Pct", MIN('Dim Promo Calendar'[Total_Contribution_Pct])
)"""),
    ("Q9", "Date table range",
     "Starts at or before Apr 2024 and runs past Aug 2026.",
     """EVALUATE
ROW(
  "Min Date", MIN('Date Table'[Date]),
  "Max Date", MAX('Date Table'[Date]),
  "Months", DISTINCTCOUNT('Date Table'[MonthStart])
)"""),
    ("Q10", "MoM Growth % by month (sanity)",
     "No blank or absurd values for months that have data. Months with no data stay blank, not zero.",
     """EVALUATE
SUMMARIZECOLUMNS(
  'Date Table'[MonthStart],
  "NSV", [NSV],
  "MoM Growth %", [MoM Growth %]
)
ORDER BY 'Date Table'[MonthStart]"""),
]


def verify():
    tables = {t["name"]: {c["name"] for c in t.get("columns", [])} for t in MODEL["tables"]}
    measures = {m["name"] for t in MODEL["tables"] for m in t.get("measures", [])}
    bad = []
    text = "\n".join(c[3] for c in CHECKS)
    for tb, col in re.findall(r"'([^']+)'\[([^\]]+)\]", text):
        if tb not in tables or (col not in tables[tb] and col not in measures):
            bad.append("%s[%s]" % (tb, col))
    for t in re.findall(r"(?:COUNTROWS|FILTER)\(\s*'([^']+)'", text):
        if t not in tables:
            bad.append(t)
    for ref in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", text):
        if ref not in measures and ref not in {"Rows", "Table"}:
            bad.append("[%s]" % ref)
    if bad:
        sys.exit("Validation query uses names missing from model.bim: " + ", ".join(sorted(set(bad))))


def main():
    verify()
    dax = ["-- DAX Studio validation queries. Rebuilt by scripts/build_desktop_validation.py.",
           "-- Connect DAX Studio to the open Power BI Desktop model. Select ONE query at a time and press F5.",
           "-- Expected values come from the raw files (PowerBI/reconciliation_expected.json). They are source-side, not Desktop results.",
           "-- FY labels follow fnFYLabel: 25-26 = Apr-25 to Mar-26, 26-27 = Apr-26 to Mar-27.", ""]
    for cid, title, expected, q in CHECKS:
        dax += ["-- ------------------------------------------------------------", "-- %s. %s" % (cid, title),
                "-- Expected: %s" % expected, "-- ------------------------------------------------------------", q, "", ""]
    OUT_DAX.write_text("\n".join(dax), encoding="utf-8")

    md = ["# Power BI Desktop runbook", "",
          "Rebuilt by `scripts/build_desktop_validation.py`. Do not edit the expected values by hand.", "",
          "Expected values are what the raw files should give. They are not Desktop results. Fill the last column from DAX Studio.", "",
          "## Steps (about 30 minutes)", "",
          "1. Pull branch `claude/gallant-shannon-wou27y`. Before anything else, run the two read-only commands in `docs/evidence/powerbi_full_ledger.md` and compare your 20 deletions with the ledger. Do not restore or clean.",
          "2. Install Tabular Editor 2 (free) and DAX Studio. Open Power BI Desktop with a blank report.",
          "3. Start Desktop with a blank report and keep it open. Find its local port: in Tabular Editor use File, Open, From DB, and pick the Power BI Desktop instance (a server like `localhost:5xxxx`).",
          "4. In Tabular Editor: File, Open, From File, `PowerBI/model.bim`. Model, Deploy, choose that Desktop instance, and tick Deploy Model Structure, Deploy Connections and Deploy Shared Expressions. `model.bim` already carries the `pRootFolder` parameter and the two helper functions; you do not paste any query. If Tabular Editor shows an error, send the exact message.",
          "4b. In Desktop: Transform data, Manage parameters, set `pRootFolder` to your local `PowerBI` folder, for example `C:\\Users\\you\\mt-dashboard\\PowerBI`. Spaces in the path are fine. No quotes and no trailing slash. Leave `pPrimaryChannel` at `MT` (the MT basis); set it to `ALL` only to check the all-channel total. The default is `C:\\MT-Dashboard`, which will not exist on your machine.",
          "5. In Desktop: Home, Refresh. If a query fails, copy the query name and the full error text, and send it. Do not edit measures to get around it. If a query says it cannot find `#\"Some Name\"`, that is a query-to-query reference; send it as is.",
          "6. Save As `.pbip` (Power BI Project) so Desktop writes the full model files.",
          "7. In DAX Studio: connect to the model, open `PowerBI/TabularEditor/05_DAXStudio_Validation.dax`, run Q1 to Q10 one at a time.",
          "8. Record each result below. A mismatch is a finding. Do not adjust a measure until the cause is traced to a source file or query.",
          "9. Copy `PowerBI/PBIR_Generated/definition/pages/` into the report's `definition/pages/` (keep your two current pages first: `python scripts/generate_pbir_pages.py --existing-pages-json <your pages.json>`). Open the report and screenshot every page.",
          "10. Run B5 separately: `docs/evidence/B5_RUN_SHEET.md`. B5 stays blocked until its own exit rule is met.",
          "11. Publish a private draft to My workspace only after steps 5 to 9 are clean. Record the URL and say it is a manual import refresh.", "",
          "## Checks", "",
          "| # | Check | Expected | Desktop result | Match |", "|---|---|---|---|---|"]
    for cid, title, expected, _ in CHECKS:
        md.append("| %s | %s | %s |  |  |" % (cid, title, expected.replace("|", "/")))
    md += ["", "## Known gaps that are not errors", "",
           "- Primary Weekly, Nielsen and TDP raw folders are empty. Their tables refresh as empty. Pages that need them show an incomplete banner.",
           "- Offtake FY26 is not in `Offtake_Monthly` (it starts Apr-26), so the model cannot show the 31,119.88 L FY26 baseline. That figure lives in `dashboard/data.js`.",
           "- Primary Article loads MT-channel rows only (parameter `pPrimaryChannel`, default MT). Set it to ALL to load EB2B and SIS as well; the total then reads 32,900.36 L. Primary ShipTo has no Channel column and is all channels (FY 25-26 32,900.36 L), so it will not equal Primary Article on the MT setting.",
           "- Store Cuts files cover Apr-26 to Aug-26 only.",
           "- FSN offtake maps to the Chain Master row `Nykaa (FSN)`, channel EB2B (owner decision 2026-10-10), so it is not in [Total MT NSV].", ""]
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print("wrote", OUT_DAX.relative_to(ROOT), "and", OUT_MD.relative_to(ROOT))


if __name__ == "__main__":
    main()
