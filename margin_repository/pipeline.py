# -*- coding: utf-8 -*-
"""One-click end-to-end refresh pipeline.

    DMS import → Fountain enrich → Master enrich (GST/Article Ext)
        → merge team responses → validate → publish to repository
        → action files → Power BI star schema → KPI snapshot → leadership summary
"""
import os
import json
import datetime as dt


def run(dms_path, repo_root, out_dir, action_dir=None, masters_dir=None,
        merge_responses_from=None, verbose=True):
    """End-to-end pipeline. Returns a summary dict."""
    from dms_adapter import load_dms
    from fountain_enricher import load_fountain_master, enrich
    from merge_responses import (merge_all_responses, apply_gst_master_to_frame,
                                  before_after_summary)
    from validation import validate_frame
    from action_files import generate_all_action_files
    from governance import kpi_snapshot, kpis_vs_targets, append_kpi_history, issue_log
    from repository import MarginRepository
    from powerbi_connector import export_star_schema

    os.makedirs(out_dir, exist_ok=True)
    log = _stepper(verbose)
    summary = {"started_at": dt.datetime.now().isoformat(timespec="seconds"),
               "dms_path": dms_path, "out_dir": out_dir}

    log(1, "Load DMS (raw + deduplicated)")
    dms_raw, meta_raw = load_dms(dms_path, deduplicate=False)
    dms_dedup, meta = load_dms(dms_path)
    summary["dms_rows_raw"] = len(dms_raw)
    summary["dms_rows_deduped"] = len(dms_dedup)

    log(2, "Enrich from Fountain master")
    fm, fm_meta = load_fountain_master()
    enriched, enrich_report = enrich(dms_dedup, fm)
    summary["fountain_source"] = fm_meta["source_file"]
    summary["fountain_match_pct"] = enrich_report["fountain_matched_pct"]

    log(3, "Enrich from persistent GST master (if any)")
    enriched, gst_fill = apply_gst_master_to_frame(enriched, masters_dir=masters_dir) \
        if masters_dir else apply_gst_master_to_frame(enriched)
    summary["gst_master_filled"] = gst_fill["filled"]

    validated_before = validate_frame(enriched)

    if merge_responses_from and os.path.isdir(merge_responses_from):
        log(4, "Merge business-team responses from " + merge_responses_from)
        enriched, merge_summary = merge_all_responses(
            merge_responses_from, enriched,
            masters_dir=masters_dir or None,
        )
        summary["merge_summary"] = {
            k: {"applied": v.get("applied"), "audit_rows": len(v.get("audit", []))}
            for k, v in merge_summary.items() if isinstance(v, dict)
        }
    else:
        summary["merge_summary"] = "no responses supplied"

    log(5, "Validate")
    validated = validate_frame(enriched)
    summary["before_after"] = before_after_summary(validated_before, validated).to_dict("records")

    log(6, "Publish to repository (append-only versioned)")
    repo = MarginRepository(repo_root)
    imp_summary, changelog, removed = repo.import_frame(
        enriched, source_file=os.path.basename(dms_path)
    )
    summary["import_summary"] = imp_summary

    log(7, "Generate action files for uncovered issues")
    action_out = action_dir or os.path.join(out_dir, "Action_Files")
    counts = generate_all_action_files(dms_raw, dms_dedup, validated, fm, action_out)
    summary["action_files"] = {os.path.basename(p): n for p, n in counts.items()}

    log(8, "Export Power BI star schema (dim + fact tables)")
    pbi_dir = os.path.join(out_dir, "PowerBI")
    pbi_paths = export_star_schema(repo, pbi_dir, fmt="csv")
    summary["powerbi_tables"] = {k: os.path.basename(v) for k, v in pbi_paths.items()}

    log(9, "KPI snapshot + trend history")
    kpi = kpi_snapshot(validated, enrich_report)
    kpi_hist = os.path.join(out_dir, "KPI_History.csv")
    append_kpi_history(kpi, kpi_hist)
    summary["kpi_snapshot"] = kpi
    summary["kpis_vs_targets"] = kpis_vs_targets(kpi).to_dict("records")

    log(10, "Issue log (routed by owner + SLA)")
    il = issue_log(validated)
    il_path = os.path.join(out_dir, "Issue_Log.xlsx")
    il.to_excel(il_path, sheet_name="Issues", index=False)
    summary["issue_log_rows"] = len(il)

    log(11, "Leadership summary")
    leadership = _build_leadership_summary(kpi, summary)
    lead_path = os.path.join(out_dir, "Leadership_Summary.md")
    with open(lead_path, "w") as f:
        f.write(leadership)
    summary["leadership_summary"] = lead_path

    summary["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")

    summary_path = os.path.join(out_dir, "Pipeline_Summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    if verbose:
        print("\n" + "=" * 68)
        print(" PIPELINE COMPLETE — %s" % summary["finished_at"])
        print("=" * 68)
        print("  Output dir:  %s" % out_dir)
        print("  Summary:     %s" % summary_path)
        print("  Leadership:  %s" % lead_path)
    return summary


def _stepper(verbose):
    def log(n, msg):
        if verbose:
            print("[%2d/11] %s" % (n, msg))
    return log


def _build_leadership_summary(kpi, summary):
    date = dt.date.today().strftime("%d %b %Y")
    actions = summary.get("action_files", {})
    return (
        "# Margin Repository Refresh — %s\n\n"
        "## Headline metrics\n"
        "- Records processed: **%d**\n"
        "- Unique EANs: **%d** across **%d** chains\n"
        "- Repository health: **%s%%**\n"
        "- Confidence score: **%s%%**\n"
        "- Fountain match: **%s%%**\n\n"
        "## Data quality\n"
        "- PASS: %d | WARNING: %d | FAIL: %d | BLOCKED: %d\n"
        "- Missing GST: %d\n"
        "- Missing Pack Size: %d\n"
        "- Missing MRP: %d\n"
        "- New EANs (not in master): %d\n\n"
        "## Action required\n"
        "- MDM (New EAN Creation): %d records\n"
        "- Finance (GST Upload): %d records\n"
        "- Commercial (Margin Conflicts): %d records\n"
        "- Sales Ops (Missing MRP): %d records\n\n"
        "_Pipeline finished %s. Full summary: Pipeline_Summary.json._\n"
        % (
            date,
            kpi.get("Total_Records", 0),
            kpi.get("Unique_EANs", 0),
            kpi.get("Total_Chains", 0),
            kpi.get("Repository_Health_pct", 0),
            kpi.get("Confidence_Score_pct", 0),
            kpi.get("Fountain_Match_pct", 0),
            kpi.get("PASS", 0), kpi.get("WARNING", 0),
            kpi.get("FAIL", 0), kpi.get("BLOCKED", 0),
            kpi.get("Blank_GST", 0),
            kpi.get("Blank_Pack_Size", 0),
            kpi.get("Blank_MRP", 0),
            kpi.get("New_EANs_Not_In_Master", 0),
            actions.get("01_New_EAN_Creation.xlsx", 0),
            actions.get("02_GST_Upload.xlsx", 0),
            actions.get("03_Margin_Conflict.xlsx", 0),
            actions.get("04_Missing_MRP.xlsx", 0),
            summary.get("finished_at", ""),
        )
    )
