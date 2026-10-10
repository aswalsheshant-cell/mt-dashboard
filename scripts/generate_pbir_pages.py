"""Generate PBIR page scaffolding from PowerBI/full_report_pages.json.

Writes to PowerBI/PBIR_Generated/definition/pages/ and never touches
ModernTrade_Report.Report. Copy the folder contents into the Report project's
definition/pages/ on the Windows machine, then open the PBIP in Desktop.

Each page gets: a title, a row of five global slicers, a visible status banner
when the source is not READY, and up to 8 KPI cards from the page's measures.
Pages without a source say so on the page. Missing data is never drawn as zero.

This is scaffolding written outside Desktop. It has not been opened in Desktop.
Desktop is the authority: if it rejects or rewrites a file, trust Desktop.

Usage:
  python scripts/generate_pbir_pages.py
  python scripts/generate_pbir_pages.py --existing-pages-json path\\to\\pages.json   # keep your 2 current pages first
"""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBI = ROOT / "PowerBI"
CONTRACT = PBI / "full_report_pages.json"
MODEL = PBI / "model.bim"
OUT = PBI / "PBIR_Generated" / "definition" / "pages"

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/"
S_PAGES = SCHEMA + "pagesMetadata/1.0.0/schema.json"
S_PAGE = SCHEMA + "page/2.0.0/schema.json"
S_VISUAL = SCHEMA + "visualContainer/2.0.0/schema.json"

W, H, GUTTER = 1280, 720, 16
MAX_CARDS = 8

BANNER = {
    "MODEL_ERROR": "MODEL ERROR: measures on this page use tables that are not in the model: {detail}. Fix the DAX table names before trusting this page.",
    "NO_SOURCE": "SOURCE NOT AVAILABLE: no data files for {detail}. Values on this page are incomplete, not zero.",
    "PARTIAL": "PARTIAL DATA: {detail} do not cover every month in {period}. Values cover the months that have data.",
    "NO_MODEL_SOURCE": "NO SOURCE IN THE MODEL YET: this view exists in the HTML dashboard but nothing in the Power BI model feeds it.",
}


def vid(page_id, key):
    return hashlib.sha1(("%s:%s" % (page_id, key)).encode()).hexdigest()[:20]


def page_name(page_id):
    return "page_" + page_id.lower()


def pos(x, y, w, h, z=0):
    return {"x": x, "y": y, "z": z, "height": h, "width": w}


def textbox(page_id, key, text, box, size="12pt", bold=False):
    run = {"value": text, "textStyle": {"fontSize": size}}
    if bold:
        run["textStyle"]["fontWeight"] = "bold"
    return {
        "$schema": S_VISUAL, "name": vid(page_id, key), "position": box,
        "visual": {"visualType": "textbox", "objects": {"general": [{"properties": {
            "paragraphs": [{"textRuns": [run]}]}}]}},
    }


def slicer(page_id, table, column, box):
    return {
        "$schema": S_VISUAL, "name": vid(page_id, "slicer:" + table + "." + column), "position": box,
        "visual": {"visualType": "slicer", "query": {"queryState": {"Values": {"projections": [{
            "field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": column}},
            "queryRef": table + "." + column, "active": True}]}}},
            "drillFilterOtherVisuals": True},
    }


def card(page_id, measure, home, box):
    return {
        "$schema": S_VISUAL, "name": vid(page_id, "card:" + measure), "position": box,
        "visual": {"visualType": "card", "query": {"queryState": {"Values": {"projections": [{
            "field": {"Measure": {"Expression": {"SourceRef": {"Entity": home}}, "Property": measure}},
            "queryRef": home + "." + measure}]}}},
            "drillFilterOtherVisuals": True},
    }


def banner_text(p, period):
    if p["status"] == "READY":
        return None
    if p["status"] == "MODEL_ERROR":
        detail = ", ".join(sorted(p["measures_with_missing_tables"]))
    elif p["status"] == "NO_SOURCE":
        detail = ", ".join(p["blocking_tables"])
    elif p["status"] == "PARTIAL":
        detail = ", ".join(p["partial_tables"])
    else:
        detail = ""
    return BANNER[p["status"]].format(detail=detail, period=period)


def build_page(p, home_of, period):
    pid = p["page_id"]
    visuals = []
    visuals.append(textbox(pid, "title", "Page %s  |  %s" % (pid, p["name"]), pos(GUTTER, 8, W - 2 * GUTTER, 40), "20pt", True))
    n = len(p["slicers"])
    sw = (W - 2 * GUTTER - (n - 1) * 12) // n
    for i, s in enumerate(p["slicers"]):
        visuals.append(slicer(pid, s["table"], s["column"], pos(GUTTER + i * (sw + 12), 56, sw, 56)))
    y = 124
    text = banner_text(p, period)
    if text:
        visuals.append(textbox(pid, "banner", text, pos(GUTTER, y, W - 2 * GUTTER, 48), "12pt", True))
        y += 60
    cards = [m for m in p["measures"] if m in home_of][:MAX_CARDS]
    cw, ch = (W - 2 * GUTTER - 3 * 12) // 4, 120
    for i, m in enumerate(cards):
        r, c = divmod(i, 4)
        visuals.append(card(pid, m, home_of[m], pos(GUTTER + c * (cw + 12), y + r * (ch + 12), cw, ch)))
    y += ((len(cards) + 3) // 4) * (ch + 12) + 8
    rest = len(p["measures"]) - len(cards)
    foot = "Build the remaining visuals from PowerBI/docs/PageLayouts.md (page %s)." % pid
    if p["origin"] == "proposed":
        foot = "New page. No layout in PageLayouts.md. Source view: HTML tab '%s'%s." % (
            p["html_tab"], (", subview '%s'" % p["html_subviews"][0]) if p["html_subviews"] else "")
    if rest > 0:
        foot += " %d more measures are listed in full_report_pages.json." % rest
    visuals.append(textbox(pid, "footer", foot, pos(GUTTER, min(y, H - 56), W - 2 * GUTTER, 40), "10pt"))
    return visuals


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--existing-pages-json", help="your current pages.json; its pages stay first and untouched")
    args = ap.parse_args()

    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    model = json.loads(MODEL.read_text(encoding="utf-8"))["model"]
    home_of = {m["name"]: t["name"] for t in model["tables"] for m in t.get("measures", [])}
    period = "%s to %s" % tuple(contract["required_periods"])

    if OUT.parent.exists():
        shutil.rmtree(OUT.parent)  # this folder is generated output only
    order = []
    if args.existing_pages_json:
        existing = json.loads(Path(args.existing_pages_json).read_text(encoding="utf-8"))
        order = list(existing.get("pageOrder", []))

    count = 0
    for p in contract["pages"]:
        name = page_name(p["page_id"])
        folder = OUT / name
        (folder / "visuals").mkdir(parents=True, exist_ok=True)
        (folder / "page.json").write_text(json.dumps({
            "$schema": S_PAGE, "name": name, "displayName": "%s %s" % (p["page_id"], p["name"]),
            "displayOption": "FitToPage", "height": H, "width": W}, indent=2) + "\n", encoding="utf-8")
        for v in build_page(p, home_of, period):
            d = folder / "visuals" / v["name"]
            d.mkdir(exist_ok=True)
            (d / "visual.json").write_text(json.dumps(v, indent=2) + "\n", encoding="utf-8")
            count += 1
        if name not in order:
            order.append(name)

    (OUT / "pages.json").write_text(json.dumps({
        "$schema": S_PAGES, "pageOrder": order, "activePageName": order[0]}, indent=2) + "\n", encoding="utf-8")
    print("pages: %d  visuals: %d  -> %s" % (len(contract["pages"]), count, OUT.relative_to(ROOT)))


if __name__ == "__main__":
    main()
