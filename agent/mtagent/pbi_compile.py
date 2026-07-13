"""Command: "compile-model" — programmatic Power BI semantic-model compilation.

Automates the MODEL half of workflow step 11 (manual_desktop_actions):
instead of hand-importing CSVs, drawing relationships, and pasting DAX in
Power BI Desktop, this generates a **.pbip (Power BI Project)** structure —
``PowerBI/ModelDefinition.pbip`` + ``ModelDefinition.SemanticModel/model.bim``
(TMSL/TOM JSON) + a minimal ``ModelDefinition.Report`` — that Desktop or
Tabular Editor opens directly.

What is compiled in, fully offline:

- **Data bindings**: M partitions binding the 0-fail-reconciled build outputs
  (``agent/pbi_build/<id>/``: Dim_Date, Dim_Chain, Dim_Article,
  Fact_OfftakeSales) plus the committed ``SeedData/Targets/FY2627_Targets.csv``.
  Paths flow through two M parameters (``BuildDir``/``RepoDir``) so a new
  machine edits exactly one value (or re-runs this command).
  Fact columns are renamed in M to the names the existing DAX library binds
  to (NSV→Offtake NSV, Sales_Qty→Offtake Qty, MRP_Sales_Value→MRP Sales,
  Counter_Type→Counter Type) and ``MonthStart`` is derived from the
  ``May'26``-style label, so measures work unmodified.
- **Star-schema relationships** — with one deliberate correction to the
  naive spec: ``Dim_Chain[Account]`` is NOT unique in the real master
  (Reliance×2, Landmark Group×3), so a raw
  ``Fact[Chain] → Dim_Chain[Account]`` relationship would be rejected by
  the Tabular engine. The compiler derives a distinct-Account dimension
  (``Chain Master``) in M and relates through it; the full chain detail
  stays loaded (disconnected) as ``Chain Detail``. The ``FY,Month``
  composite spec collapses to single-column ``Month`` (labels like
  ``May'26`` carry the year, so Month alone is unique) — TMSL has no
  composite relationships.
- **DAX injection with dependency gating**: every measure in
  ``PowerBI/DAX/*.dax`` is parsed (via ``dax_validator``); a measure is
  injected only when every table/column/measure it references resolves
  against the compiled model. Everything excluded is listed, with the
  exact unresolved reference, in ``Model_Compile_Report.json`` — measures
  that bind to tables this model doesn't load (Fact P&L, Fact Nielsen,
  Fact TDP, …) are staged for the full-kit model, never silently baked in
  broken. The Brand-Counter isolation suite (``Offtake NSV (Adjusted)``,
  ``BC Isolation Check``) is asserted present — compilation FAILS if the
  double-counting guard didn't make it in.

Honest limits (also stamped into the compile report): this environment
cannot run Power BI Desktop or the Tabular engine, so DAX is validated
statically (balance/dependency/lint), not executed. First open in Desktop
is the semantic verification — that is workflow step 12's evidence, which
stays a human step.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .config import Config
from .dax_validator import extract_definitions, strip_comments_and_strings

MODEL_NAME = "ModelDefinition"
COMPAT_LEVEL = 1550

# tables compiled into this model -> their columns (post-M names)
_FACT_COLUMNS = [
    ("FY", "string"), ("Month", "string"), ("Zone", "string"), ("State", "string"),
    ("Chain", "string"), ("Counter Type", "string"), ("EAN", "string"),
    ("Brand", "string"), ("Category", "string"), ("Sub_Category", "string"),
    ("Offtake NSV", "double"), ("MRP Sales", "double"), ("Offtake Qty", "double"),
    ("Store_Count", "int64"), ("MonthStart", "dateTime"),
]
_DIM_DATE_COLUMNS = [("FY", "string"), ("Month", "string"), ("MonthNo", "int64"), ("Quarter", "string")]
_CHAIN_MASTER_COLUMNS = [("Account", "string"), ("Chain Count", "int64"), ("Chains", "string")]
_CHAIN_DETAIL_COLUMNS = [("Chain", "string"), ("Account", "string"), ("Chain Type", "string"),
                          ("Primary Zone", "string"), ("Active", "string"), ("No Store Grain", "string")]
_ARTICLE_COLUMNS = [("Article Code", "string"), ("Article Description", "string"),
                     ("EAN Code", "string"), ("Brand", "string"), ("Category", "string"),
                     ("Sub-category", "string"), ("Range", "string"), ("Pack Size", "string")]
_TARGETS_COLUMNS = [("MonthStart", "dateTime"), ("Month", "string"), ("FY Year", "string"),
                     ("Quarter", "string"), ("Target NSV Cr", "double"), ("Target NSV", "double")]
_DATE_TABLE_COLUMNS = [  # calculated table -- names must match 00_DateTable.dax
    ("Date", "dateTime"), ("MonthStart", "dateTime"), ("Year", "int64"),
    ("Month No", "int64"), ("Month Name", "string"), ("FY Month No", "int64"),
    ("FY Year", "string"), ("Quarter", "string"), ("Month", "string"),
    ("Month Year Sort", "int64"), ("Is Future", "boolean"),
]

_QUOTED_COL_RE = re.compile(r"'([^']+)'\s*\[([^\[\]]+)\]")
_BARE_COL_RE = re.compile(r"(?<![\w'\]])([A-Za-z_][A-Za-z0-9_ ]*?)\s*\[([^\[\]]+)\]")
_LONE_BRACKET_RE = re.compile(r"(?<![\w'\]])\[([^\[\]]+)\]")


def _csv_m(path_expr: str, renames: list[tuple[str, str]] | None = None,
           types: list[tuple[str, str]] | None = None, extra: str = "") -> str:
    """Assemble a standard CSV-load M expression."""
    steps = [
        f'Source = Csv.Document(File.Contents({path_expr}), '
        f'[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv])',
        "Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true])",
    ]
    last = "Promoted"
    if renames:
        pairs = ", ".join('{"%s", "%s"}' % (a, b) for a, b in renames)
        steps.append(f"Renamed = Table.RenameColumns(Promoted, {{{pairs}}})")
        last = "Renamed"
    if types:
        pairs = ", ".join('{"%s", %s}' % (c, t) for c, t in types)
        steps.append(f"Typed = Table.TransformColumnTypes({last}, {{{pairs}}})")
        last = "Typed"
    if extra:
        steps.append(extra)
        last = extra.split("=", 1)[0].strip()
    body = ",\n    ".join(steps)
    return f"let\n    {body}\nin\n    {last}"


def _fact_m() -> str:
    month_start = (
        'WithMonthStart = Table.AddColumn(Typed, "MonthStart", each '
        'let m = Text.BeforeDelimiter([Month], "\'"), '
        'y = 2000 + Number.FromText(Text.AfterDelimiter([Month], "\'")), '
        'n = Record.Field([Jan=1, Feb=2, Mar=3, Apr=4, May=5, Jun=6, '
        'Jul=7, Aug=8, Sep=9, Oct=10, Nov=11, Dec=12], m) '
        'in #date(y, n, 1), type date)'
    )
    return _csv_m(
        'BuildDir & "Fact_OfftakeSales.csv"',
        renames=[("NSV", "Offtake NSV"), ("Sales_Qty", "Offtake Qty"),
                 ("MRP_Sales_Value", "MRP Sales"), ("Counter_Type", "Counter Type")],
        types=[("Offtake NSV", "type number"), ("MRP Sales", "type number"),
               ("Offtake Qty", "type number"), ("Store_Count", "Int64.Type")],
        extra=month_start,
    )


def _chain_master_m() -> str:
    group = ('Grouped = Table.Group(Promoted, {"Account"}, '
             '{{"Chain Count", each Table.RowCount(_), Int64.Type}, '
             '{"Chains", each Text.Combine([Chain], ", "), type text}})')
    return _csv_m('BuildDir & "Dim_Chain.csv"', extra=group)


def _targets_m() -> str:
    extra = ('WithValue = Table.AddColumn(Typed, "Target NSV", '
             'each [Target NSV Cr] * 10000000, type number)')
    return _csv_m('RepoDir & "PowerBI/SeedData/Targets/FY2627_Targets.csv"',
                  types=[("MonthStart", "type date"), ("Target NSV Cr", "type number")],
                  extra=extra)


def _dim_date_m() -> str:
    return _csv_m('BuildDir & "Dim_Date.csv"', types=[("MonthNo", "Int64.Type")])


def _chain_detail_m() -> str:
    return _csv_m('BuildDir & "Dim_Chain.csv"')


def _article_m() -> str:
    return _csv_m('BuildDir & "Dim_Article.csv"')


def _table(name: str, columns: list, m_expr: str) -> dict:
    return {
        "name": name,
        "columns": [{"name": c, "dataType": t, "sourceColumn": c} for c, t in columns],
        "partitions": [{"name": name, "mode": "import",
                         "source": {"type": "m", "expression": m_expr}}],
    }


def _calculated_table(name: str, columns: list, dax_expr: str) -> dict:
    return {
        "name": name,
        "columns": [{"type": "calculatedTableColumn", "name": c, "dataType": t,
                      "isNameInferred": True, "sourceColumn": f"[{c}]"} for c, t in columns],
        "partitions": [{"name": name, "mode": "import",
                         "source": {"type": "calculated", "expression": dax_expr}}],
    }


def _load_date_table_expression(dax_dir: Path) -> str:
    """Extract the 'Date Table = ...' calculated-table DAX from 00_DateTable.dax."""
    text = (dax_dir / "00_DateTable.dax").read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if re.match(r"\s*Date Table\s*=", ln))
    # expression runs until the next top-level comment banner or EOF
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].strip().startswith("// ---") and ")" in "".join(lines[start:i]):
            end = i
            break
    block = "\n".join(lines[start:end])
    return block.split("=", 1)[1].strip()


def _extract_measures(dax_dir: Path) -> list[dict]:
    """Parse every measure definition from PowerBI/DAX/*.dax.

    Bodies are re-sliced from the ORIGINAL file text (extract_definitions
    works on comment/string-blanked text, which would blank string literals
    like "Brand Counter" inside expressions); the blanked text is kept per
    measure for reference scanning, where blanked strings are exactly what
    we want (no false table/measure refs from prose).
    """
    measures = []
    for path in sorted(dax_dir.glob("*.dax")):
        text = path.read_text(encoding="utf-8-sig")
        cleaned, _ = strip_comments_and_strings(text)
        defs = extract_definitions(cleaned, str(path))
        orig_lines = text.splitlines()
        clean_lines = cleaned.splitlines()
        for i, d in enumerate(defs):
            if d.name == "Date Table":
                continue  # injected as a calculated table, not a measure
            last = defs[i + 1].line - 1 if i + 1 < len(defs) else len(orig_lines)
            block = "\n".join(orig_lines[d.line - 1:last])
            scan = "\n".join(clean_lines[d.line - 1:last])
            expression = block.split("=", 1)[1].strip()
            measures.append({"name": d.name, "expression": expression,
                              "scan": scan, "file": path.name})
    return measures


def _gate_measures(measures: list[dict], model_columns: dict) -> tuple[list, list]:
    """Dependency-gate: include a measure only when every table, column, and
    measure reference resolves against the compiled model. Returns
    (included, excluded_with_reasons)."""
    all_columns = {c for cols in model_columns.values() for c in cols}
    names = {m["name"] for m in measures}
    reasons: dict[str, str] = {}

    def unresolved_static(m) -> str:
        scan = m["scan"]
        for table, col in _QUOTED_COL_RE.findall(scan):
            if table not in model_columns:
                return f"references table '{table}' not in this model"
            if col not in model_columns[table]:
                return f"references '{table}'[{col}] -- column not in the compiled table"
        for table, col in _BARE_COL_RE.findall(scan):
            table = table.strip()
            if table in model_columns and col not in model_columns[table]:
                return f"references {table}[{col}] -- column not in the compiled table"
            if table not in model_columns and table in _KNOWN_FOREIGN_TABLES:
                return f"references table '{table}' not in this model"
        return ""

    for m in measures:
        r = unresolved_static(m)
        if r:
            reasons[m["name"]] = r

    # iterate measure->measure deps to a fixpoint
    changed = True
    while changed:
        changed = False
        for m in measures:
            if m["name"] in reasons:
                continue
            for ref in _LONE_BRACKET_RE.findall(m["scan"]):
                if ref in all_columns:
                    continue          # row-context column ref, fine
                if ref in names and ref not in reasons:
                    continue          # resolves to an included measure
                if ref in reasons:
                    reasons[m["name"]] = f"depends on excluded measure [{ref}]"
                else:
                    reasons[m["name"]] = f"references [{ref}] -- not a model column or included measure"
                changed = True
                break

    included = [m for m in measures if m["name"] not in reasons]
    excluded = [{"name": m["name"], "file": m["file"], "reason": reasons[m["name"]]}
                for m in measures if m["name"] in reasons]
    return included, excluded


# tables the wider kit uses; a bare reference to one of these means the
# measure belongs to the full model, not this compiled subset
_KNOWN_FOREIGN_TABLES = {
    "Targets", "Assumption Table", "Forecast Override", "Store Master",
    "Sales Team Mapping", "Primary Allocation Map", "Primary Allocation Override",
    "PL Expense Input", "CustCode Chain Map", "GST Config",
}


def compile_model(cfg: Config, build_dir: Path | None = None) -> dict:
    root = cfg.root()
    dax_dir = root / "PowerBI" / "DAX"
    if build_dir is None:
        base = cfg.path(cfg.pbi_build_dir)
        candidates = sorted([p for p in base.glob("FY*_*") if (p / "Fact_OfftakeSales.csv").exists()]) \
            if base.exists() else []
        if not candidates:
            return {"blocked_reason": f"no completed dataset build under {base} -- run `pbi build-dataset` first"}
        build_dir = candidates[-1]
    for required in ("Fact_OfftakeSales.csv", "Dim_Date.csv", "Dim_Chain.csv", "Dim_Article.csv"):
        if not (build_dir / required).exists():
            return {"blocked_reason": f"{required} missing from {build_dir} -- run `pbi build-dataset` first"}
    if not dax_dir.exists():
        return {"blocked_reason": f"DAX library not found: {dax_dir}"}

    # -- 1-side uniqueness checks against the REAL files (the Tabular engine
    # enforces these on load; failing early here beats a broken .pbip) -----
    import csv as _csv
    with open(build_dir / "Dim_Date.csv", newline="", encoding="utf-8") as fh:
        months = [r["Month"] for r in _csv.DictReader(fh)]
    if len(months) != len(set(months)):
        return {"blocked_reason": "Dim_Date.csv Month values are not unique -- cannot be a 1-side"}
    with open(build_dir / "Dim_Article.csv", newline="", encoding="utf-8") as fh:
        eans = [r["EAN Code"] for r in _csv.DictReader(fh)]
    if len(eans) != len(set(eans)):
        return {"blocked_reason": "Dim_Article.csv EAN Code values are not unique -- cannot be a 1-side"}

    model_columns = {
        "Fact Offtake Sales": {c for c, _ in _FACT_COLUMNS},
        "Dim_Date": {c for c, _ in _DIM_DATE_COLUMNS},
        "Chain Master": {c for c, _ in _CHAIN_MASTER_COLUMNS},
        "Chain Detail": {c for c, _ in _CHAIN_DETAIL_COLUMNS},
        "Dim_Article": {c for c, _ in _ARTICLE_COLUMNS},
        "Targets": {c for c, _ in _TARGETS_COLUMNS},
        "Date Table": {c for c, _ in _DATE_TABLE_COLUMNS},
    }

    measures = _extract_measures(dax_dir)
    # duplicate definition names (the DAX linter flags these as DAX002) would
    # be rejected by the Tabular engine on load -- keep the first, report the rest
    seen_names: dict[str, str] = {}
    deduped, duplicates = [], []
    for m in measures:
        if m["name"] in seen_names:
            duplicates.append({"name": m["name"], "file": m["file"],
                                "reason": f"duplicate of definition in {seen_names[m['name']]} -- "
                                          "engine rejects duplicate measure names (see check-dax DAX002)"})
            continue
        seen_names[m["name"]] = m["file"]
        deduped.append(m)
    included, excluded = _gate_measures(deduped, model_columns)
    excluded.extend(duplicates)

    # the double-counting guard is the point of this model -- hard-fail if gated out
    included_names = {m["name"] for m in included}
    for critical in ("Offtake NSV (Adjusted)", "BC Isolation Check", "Reliance BC NSV", "NSV"):
        if critical not in included_names:
            reason = next((e["reason"] for e in excluded if e["name"] == critical), "not found in DAX library")
            raise RuntimeError(f"critical measure {critical!r} failed to compile into the model: {reason}")

    fact_table = _table("Fact Offtake Sales", _FACT_COLUMNS, _fact_m())
    fact_table["measures"] = [
        {"name": m["name"], "expression": m["expression"],
         "displayFolder": m["file"].replace(".dax", "")}
        for m in included
    ]

    tables = [
        fact_table,
        _table("Dim_Date", _DIM_DATE_COLUMNS, _dim_date_m()),
        _table("Chain Master", _CHAIN_MASTER_COLUMNS, _chain_master_m()),
        _table("Chain Detail", _CHAIN_DETAIL_COLUMNS, _chain_detail_m()),
        _table("Dim_Article", _ARTICLE_COLUMNS, _article_m()),
        _table("Targets", _TARGETS_COLUMNS, _targets_m()),
        _calculated_table("Date Table", _DATE_TABLE_COLUMNS, _load_date_table_expression(dax_dir)),
    ]

    relationships = [
        {"name": "Fact_Chain_to_Account", "fromTable": "Fact Offtake Sales", "fromColumn": "Chain",
         "toTable": "Chain Master", "toColumn": "Account"},
        {"name": "Fact_EAN_to_Article", "fromTable": "Fact Offtake Sales", "fromColumn": "EAN",
         "toTable": "Dim_Article", "toColumn": "EAN Code"},
        {"name": "Fact_Month_to_DimDate", "fromTable": "Fact Offtake Sales", "fromColumn": "Month",
         "toTable": "Dim_Date", "toColumn": "Month"},
        {"name": "Fact_MonthStart_to_DateTable", "fromTable": "Fact Offtake Sales",
         "fromColumn": "MonthStart", "toTable": "Date Table", "toColumn": "MonthStart"},
        {"name": "Targets_MonthStart_to_DateTable", "fromTable": "Targets",
         "fromColumn": "MonthStart", "toTable": "Date Table", "toColumn": "MonthStart"},
    ]
    table_cols = {t["name"]: {c["name"] for c in t["columns"]} for t in tables}
    for r in relationships:
        assert r["fromColumn"] in table_cols[r["fromTable"]], r
        assert r["toColumn"] in table_cols[r["toTable"]], r

    build_dir_str = str(build_dir.resolve()).replace("\\", "/") + "/"
    repo_dir_str = str(root.resolve()).replace("\\", "/") + "/"
    model_bim = {
        "name": MODEL_NAME,
        "compatibilityLevel": COMPAT_LEVEL,
        "model": {
            "culture": "en-US",
            "expressions": [
                {"name": "BuildDir", "kind": "m",
                 "expression": f'"{build_dir_str}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'},
                {"name": "RepoDir", "kind": "m",
                 "expression": f'"{repo_dir_str}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]'},
            ],
            "tables": tables,
            "relationships": relationships,
            "annotations": [
                {"name": "GeneratedBy", "value": "mtagent pbi compile-model"},
                {"name": "SourceBuild", "value": build_dir.name},
            ],
        },
    }

    out_root = root / "PowerBI"
    sm_dir = out_root / f"{MODEL_NAME}.SemanticModel"
    rp_dir = out_root / f"{MODEL_NAME}.Report"
    sm_dir.mkdir(parents=True, exist_ok=True)
    rp_dir.mkdir(parents=True, exist_ok=True)

    (sm_dir / "model.bim").write_text(json.dumps(model_bim, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (sm_dir / "definition.pbism").write_text(json.dumps({"version": "4.0", "settings": {}}, indent=2) + "\n", encoding="utf-8")
    (rp_dir / "definition.pbir").write_text(json.dumps({
        "version": "1.0",
        "datasetReference": {"byPath": {"path": f"../{MODEL_NAME}.SemanticModel"}},
    }, indent=2) + "\n", encoding="utf-8")
    (rp_dir / "report.json").write_text(json.dumps({
        "config": "{}", "layoutOptimization": 0, "resourcePackages": [],
        "sections": [{"name": "page1", "displayName": "Executive Growth Engine",
                       "visualContainers": [], "config": "{}", "displayOption": 1,
                       "height": 720, "width": 1280}],
    }, indent=2) + "\n", encoding="utf-8")
    (out_root / f"{MODEL_NAME}.pbip").write_text(json.dumps({
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{MODEL_NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    }, indent=2) + "\n", encoding="utf-8")

    report = {
        "source_build": build_dir.name,
        "tables": sorted(table_cols),
        "relationships": [f'{r["fromTable"]}[{r["fromColumn"]}] -> {r["toTable"]}[{r["toColumn"]}]'
                           for r in relationships],
        "measures_injected": len(included),
        "measures_excluded": len(excluded),
        "excluded_detail": excluded,
        "critical_measures_verified": ["NSV", "Offtake NSV (Adjusted)", "Reliance BC NSV", "BC Isolation Check"],
        "design_notes": [
            "Chain relationship goes through a distinct-Account 'Chain Master' derived in M -- "
            "Dim_Chain[Account] is not unique in the raw master (Reliance x2, Landmark Group x3), "
            "so the naive Fact[Chain]->Dim_Chain[Account] relationship would be rejected by the engine.",
            "FY+Month composite relationship collapsed to single-column Month -- labels like May'26 "
            "carry the year, and TMSL has no composite relationships.",
        ],
        "verification_limits": "DAX validated statically (balance/dependency-gated), NOT executed -- "
                                "this environment cannot run Power BI Desktop/the Tabular engine. "
                                "First Desktop open is the semantic verification (workflow step 12).",
    }
    report_path = build_dir / "Model_Compile_Report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    warning = ""
    if excluded:
        warning = (f"{len(excluded)} measure(s) excluded (bind to tables/columns outside this "
                   f"model -- full-kit measures, see Model_Compile_Report.json)")

    return {
        "output_file": str((out_root / f"{MODEL_NAME}.pbip").relative_to(root)),
        "validation_result": json.dumps({k: report[k] for k in
                                          ("source_build", "tables", "relationships",
                                           "measures_injected", "measures_excluded",
                                           "critical_measures_verified")}),
        "warning": warning,
        "compile_report": str(report_path.relative_to(root)),
    }
