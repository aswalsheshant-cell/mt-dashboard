"""Build PowerBI/full_report_pages.json, the page contract for the full report.

Inputs (all read-only):
  PowerBI/docs/PageLayouts.md        what each page should hold
  PowerBI/model.bim                  which measures and tables really exist
  PowerBI/full_report_sources.json   which sources have data (run powerbi_full_sources.py first)
  dashboard/index.html               the 11 tabs and their subviews

For each page it records the measures found in the layout text (kept only if they
exist in model.bim), the fact tables those measures read (followed through nested
measures), and a status taken from the source coverage:
  READY            every fact table the page reads has data for the required window
  PARTIAL          data exists but some required months are missing
  NO_SOURCE        a fact table has no data files (template, empty or missing)
  NO_MODEL_SOURCE  the page has no table in the model at all (HTML-only tab)
  MODEL_ERROR      a measure on the page names a table that is not in the model

Usage: python scripts/build_full_report_pages.py
"""

import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PBI = ROOT / "PowerBI"
LAYOUT = PBI / "docs" / "PageLayouts.md"
MODEL = PBI / "model.bim"
SOURCES = PBI / "full_report_sources.json"
INDEX_HTML = ROOT / "dashboard" / "index.html"
OUT = PBI / "full_report_pages.json"

# page id, name, key in PageLayouts.md ("## Page <key> ..."), HTML tab, HTML subviews, origin
PAGES = [
    ("1", "Executive Summary", "1", "executive-cockpit", [], "layout"),
    ("2", "Primary vs Offtake Overview", "2", "inventory-health", ["velocity", "gap"], "layout"),
    ("2B", "Ship-to Primary Allocation", "2B", "channel-dynamics", ["primary"], "layout"),
    ("3", "Chain Performance", "3", "channel-dynamics", ["primary"], "layout"),
    ("4", "Chain-wise P&L", "4", "pnl", [], "layout"),
    ("5", "Forecast Dashboard", "5", "demand-planning", ["forecast"], "layout"),
    ("6", "Brand & Category Deep Dive", "6", "channel-dynamics", ["category"], "layout"),
    ("7", "SKU / Article Performance", "7", "analytics", [], "layout"),
    ("8", "Zone & State Performance", "8", "comparison", [], "layout"),
    ("9", "Nielsen Market Share MoM", "9", "demand-planning", ["market-share"], "layout"),
    ("10", "TDP Distribution Analysis", "10", "inventory-health", ["tdp"], "layout"),
    ("11", "Raw Data Export View", "11", "explorer", [], "layout"),
    ("12", "Data Quality Check", "12", None, [], "layout"),
    ("18", "Refresh Guide", "18", None, [], "layout"),
    # No page in PageLayouts.md for these HTML views. New pages are proposed.
    ("19", "Promotional Impact", None, "demand-planning", ["promo"], "proposed"),
    ("20", "Reliance Brand Counter", None, "channel-dynamics", ["reliance"], "proposed"),
    ("21", "State, Pack & Store Type", None, "inventory-health", ["storecuts"], "proposed"),
    ("22", "Operational Alerts", None, "alerts", [], "proposed"),
    ("23", "Store Audit Scorecard", None, "stores", [], "proposed"),
    ("24", "Supply Chain & Inventory", None, "inventory", [], "proposed"),
]

# A page can also stand in for a view that belongs to a different HTML tab.
EXTRA_SERVES = {"8": [("inventory-health", ["coverage"])]}

# Measures for proposed pages come from named DAX files or name patterns.
PROPOSED_FROM_DAX = {"19": "15_Promo_Measures.dax", "21": "20_Store_Type_Pack_Measures.dax"}
PROPOSED_PATTERN = {"20": re.compile(r"RBC|Reliance|Brand Counter", re.I)}

SLICER_ROW = [
    ("Date Table", "Month"), ("Chain Master", "Chain"), ("Zone State Master", "Zone"),
    ("Brand Master", "Brand"), ("Category Master", "Category"),
]
EXTRA_SOURCE_TABLES = {"Dim Promo Calendar"}  # file-backed dimension that Promo measures depend on
BAD_FACT = {"TEMPLATE_ONLY", "EMPTY", "MISSING"}


def serves(p):
    out = [(p["html_tab"], p["html_subviews"])] if p["html_tab"] else []
    return out + [(t, s) for t, s in p.get("also_serves", [])]


def load_model():
    model = json.loads(MODEL.read_text(encoding="utf-8"))["model"]
    tables = {t["name"] for t in model["tables"]}
    measures = {}
    for t in model["tables"]:
        for m in t.get("measures", []):
            e = m["expression"]
            measures[m["name"]] = {"table": t["name"], "expr": "\n".join(e) if isinstance(e, list) else e}
    return model, tables, measures


def fact_tables_for(measure, measures, tables, seen=None):
    """Tables a measure reads, following measures it calls (guards against loops)."""
    seen = seen if seen is not None else set()
    if measure in seen or measure not in measures:
        return set()
    seen.add(measure)
    expr = measures[measure]["expr"]
    found = {t for t in re.findall(r"'([^']+)'\[", expr) if t in tables}
    found |= {t for t in re.findall(r"(?<![\w'\]])([A-Za-z_][\w]*)\[", expr) if t in tables}
    for ref in re.findall(r"\[([^\]]+)\]", expr):
        if ref in measures:
            found |= fact_tables_for(ref, measures, tables, seen)
    return found


def missing_table_refs(measure, measures, tables):
    """Table names a measure uses that do not exist in the model (e.g. Dim_PromoCalendar)."""
    expr = re.sub(r"//.*", "", measures[measure]["expr"])
    bad = {q for q in re.findall(r"'([^']+)'\[", expr) if q not in tables}
    bad |= {u for u in re.findall(r"(?<![\w'\]\[])([A-Za-z][A-Za-z0-9]*_[A-Za-z0-9_]*)\[", expr) if u not in tables}
    return bad


def layout_sections():
    text = LAYOUT.read_text(encoding="utf-8")
    parts = re.split(r"^## (?:\*\*)?Page (\w+)\b", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def dax_measure_names(filename):
    """Measure names defined in one DAX file, using the same parser that builds model.bim."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_model_bim import parse_dax_measures
    found, _, _ = parse_dax_measures(PBI / "DAX")
    return [m["name"] for m in found if m["source"] == filename]


def html_tabs_and_subviews():
    html = INDEX_HTML.read_text(encoding="utf-8")
    tabs = re.findall(r"\['([\w-]+)','([^']+)'\]", html[html.index("const TABS="):][:900])
    subs = {}
    for line in re.findall(r"const subviews\s*=\s*\[([^\]]+)\]", html):
        ids = re.findall(r"'([\w-]+)'", line)
        subs[tuple(ids)] = ids
    return tabs, list(subs.values())


def status_for(facts, sources):
    by = {t["table"]: t for t in sources["tables"]}

    def effective(name, depth=0):
        t = by.get(name)
        if not t or depth > 5:
            return None
        if t["status"] == "DERIVED":
            kids = [effective(k, depth + 1) for k in t.get("derived_from", [])]
            kids = [k for k in kids if k]
            if any(k in BAD_FACT for k in kids):
                return "NO_SOURCE"
            return "PARTIAL" if "INCOMPLETE_PERIODS" in kids else "READY"
        if t["status"] in BAD_FACT:
            return "NO_SOURCE"
        if t["status"] == "INCOMPLETE_PERIODS":
            return "PARTIAL"
        return "READY"

    states = {f: effective(f) for f in facts}
    blocking = sorted(f for f, s in states.items() if s == "NO_SOURCE")
    partial = sorted(f for f, s in states.items() if s == "PARTIAL")
    if not states:
        return "NO_MODEL_SOURCE", blocking, partial
    if blocking:
        return "NO_SOURCE", blocking, partial
    return ("PARTIAL" if partial else "READY"), blocking, partial


PARITY = PBI / "docs" / "FullReportParity.md"
STATUS_TEXT = {
    "READY": "Source has every required month",
    "PARTIAL": "Months missing for: {t}",
    "NO_SOURCE": "No data files for: {t}",
    "NO_MODEL_SOURCE": "Nothing in the model feeds this view",
    "MODEL_ERROR": "Measures use tables that do not exist: {t}",
}


def write_parity(doc):
    """Human-readable HTML-to-Power-BI map, rebuilt from the contract every run."""
    L = ["# Full report parity: HTML dashboard to Power BI pages", "",
         "Rebuilt by `scripts/build_full_report_pages.py`. Do not edit by hand.", "",
         "Basis: %s" % doc["basis"], "",
         "Required window: %s to %s. HTML tabs: %d. HTML subviews: %d (CLAUDE.md lists 9; `index.html` has 11)." % (
             doc["required_periods"][0], doc["required_periods"][1], doc["html_tab_count"], doc["html_subview_count"]), "",
         "## Tab and subview to page", "",
         "| HTML tab | Subview | Power BI page | Page status | Why |", "|---|---|---|---|---|"]
    by_id = {p["page_id"]: p for p in doc["pages"]}
    for t in doc["tabs"]:
        pids = t["pages"]
        if not pids:
            L.append("| %s | all | none | NO_PAGE | No page maps to this tab |" % t["label"])
            continue
        for pid in pids:
            p = by_id[pid]
            why_tables = p["measures_with_missing_tables"] and ", ".join(p["measures_with_missing_tables"]) \
                or ", ".join(p["blocking_tables"] if p["status"] == "NO_SOURCE" else p["partial_tables"])
            subs_here = sorted({x for tt, ss in serves(p) if tt == t["tab"] for x in ss})
            L.append("| %s | %s | %s %s | %s | %s |" % (
                t["label"], ", ".join(subs_here) or "-", pid, p["name"], p["status"],
                STATUS_TEXT[p["status"]].format(t=why_tables)))
    L += ["", "## Pages in the layout with no HTML tab", ""]
    for p in doc["pages"]:
        if not serves(p):
            L.append("- Page %s %s (%s): internal page, no HTML equivalent." % (p["page_id"], p["name"], p["status"]))
    L += ["", "## Pages proposed because PageLayouts.md has none", ""]
    for p in doc["pages"]:
        if p["origin"] == "proposed":
            L.append("- Page %s %s: %d measures, status %s." % (p["page_id"], p["name"], p["measure_count"], p["status"]))
    L += ["", "## Measure names in the layout text that are not in the model", "",
          "Each is either a column/field written in backticks or a measure the layout expects but the model lacks. Check before building the visual.", ""]
    for p in doc["pages"]:
        if p["layout_names_not_in_model"]:
            L.append("- Page %s: %s" % (p["page_id"], ", ".join("`%s`" % n for n in p["layout_names_not_in_model"])))
    L += ["", "## Status meaning", "",
          "- READY: every source table the page reads has data for the whole window.",
          "- PARTIAL: some months missing. Show what exists, label it partial.",
          "- NO_SOURCE: a source table has no data files. Show the incomplete banner.",
          "- NO_MODEL_SOURCE: HTML-only view. Needs a source and a query before it can show numbers.",
          "- MODEL_ERROR: a measure names a table that is not in the model. Fix the DAX first.", ""]
    PARITY.write_text("\n".join(L), encoding="utf-8")


def main():
    model, tables, measures = load_model()
    column_names = {c["name"] for t in model["tables"] for c in t.get("columns", [])}
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    sections = layout_sections()
    tabs, sub_groups = html_tabs_and_subviews()

    pages = []
    for pid, name, key, tab, subs, origin in PAGES:
        if origin == "layout":
            body = sections.get(key, "")
            tokens = re.findall(r"`([^`]+)`", body)
            candidates = tokens
        elif pid in PROPOSED_FROM_DAX:
            candidates = dax_measure_names(PROPOSED_FROM_DAX[pid])
        elif pid in PROPOSED_PATTERN:
            candidates = [m for m in measures if PROPOSED_PATTERN[pid].search(m)]
        else:
            candidates = []
        used, seen = [], set()
        for c in candidates:
            if c in measures and c not in seen:
                seen.add(c)
                used.append(c)
        unmatched = []
        if origin == "layout":
            # Names in backticks that look like a measure but are not in model.bim.
            # Real drift between the layout text and the model shows up here.
            unmatched = sorted({c for c in candidates if c not in measures and c not in column_names
                                and c not in tables and not re.search(r"[\[\]/▸×=(){}:<>]|^\d", c)
                                and re.fullmatch(r"[A-Za-z][A-Za-z0-9 %&.\-']{2,45}", c)})
        facts = set()
        for m in used:
            facts |= fact_tables_for(m, measures, tables)
        facts = sorted(f for f in facts if f.startswith("Fact ") or f in EXTRA_SOURCE_TABLES)
        status, blocking, partial = status_for(facts, sources)
        broken = {}
        for m in used:
            for t in missing_table_refs(m, measures, tables):
                broken.setdefault(t, []).append(m)
        if broken:
            status = "MODEL_ERROR"
        notes = []
        if origin == "proposed":
            notes.append("No page in PageLayouts.md. New page proposed to cover this HTML view.")
        if pid == "20":
            notes.append("Reliance Brand Counter split applies to Offtake only. Primary stays gross.")
        if status == "NO_MODEL_SOURCE" and origin == "proposed":
            notes.append("HTML-only view. No Power Query or table in model.bim feeds it, so the page shows an incomplete state until a source is added.")
        pages.append({
            "page_id": pid, "name": name, "origin": origin, "layout_section": key,
            "html_tab": tab, "html_subviews": subs,
            "also_serves": [[t, s] for t, s in EXTRA_SERVES.get(pid, [])],
            "measures": used, "measure_count": len(used),
            "layout_names_not_in_model": unmatched,
            "fact_tables": facts,
            "blocking_tables": blocking, "partial_tables": partial,
            "slicers": [{"table": t, "column": c} for t, c in SLICER_ROW],
            "measures_with_missing_tables": {k: sorted(v) for k, v in sorted(broken.items())},
            "status": status, "notes": notes,
        })

    # Tab and subview coverage
    sub_labels = {s for g in sub_groups for s in g}
    coverage = []
    for tid, label in tabs:
        mapped = [p for p in pages if any(t == tid for t, _ in serves(p))]
        coverage.append({"tab": tid, "label": label, "pages": [p["page_id"] for p in mapped],
                         "subviews": sorted({x for p in mapped for t, s in serves(p) if t == tid for x in s})})
    sub_cov = []
    for g in sub_groups:
        for s in g:
            mapped = [p["page_id"] for p in pages if any(s in subs_ for _, subs_ in serves(p))]
            sub_cov.append({"subview": s, "pages": mapped})

    table_pages = {}
    for p in pages:
        for f in p["fact_tables"]:
            table_pages.setdefault(f, []).append(p["page_id"])

    doc = {
        "generated": date.today().isoformat(),
        "basis": "Built from PageLayouts.md, model.bim and full_report_sources.json. Statuses are source-side only, not a Desktop result.",
        "required_periods": [sources["required_periods"][0], sources["required_periods"][-1]],
        "html_tab_count": len(tabs),
        "html_subview_count": len(sub_cov),
        "status_counts": {s: sum(1 for p in pages if p["status"] == s) for s in sorted({p["status"] for p in pages})},
        "tabs": coverage,
        "subviews": sub_cov,
        "fact_table_to_pages": {k: sorted(v) for k, v in sorted(table_pages.items())},
        "pages": pages,
    }
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    write_parity(doc)

    unmapped_tabs = [c["tab"] for c in coverage if not c["pages"]]
    unmapped_subs = [c["subview"] for c in sub_cov if not c["pages"]]
    print("tabs:", len(tabs), "subviews:", len(sub_cov), "pages:", len(pages))
    print("status counts:", doc["status_counts"])
    print("tabs with no page:", unmapped_tabs or "none", "| subviews with no page:", unmapped_subs or "none")
    for p in pages:
        print("  %-3s %-32s %-16s measures=%-3d unmatched=%-3d facts=%s" % (p["page_id"], p["name"], p["status"], p["measure_count"], len(p["layout_names_not_in_model"]), ",".join(f.replace("Fact ", "") for f in p["fact_tables"])))


if __name__ == "__main__":
    main()
