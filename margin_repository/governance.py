# -*- coding: utf-8 -*-
"""Data governance — owner mapping, SLA config, KPI snapshots.

Every validation flag routes to a named function-owner with a resolution SLA.
The KPI snapshot captures repository health at import time so leadership can
track trend over time.
"""
import datetime as dt
from collections import Counter
import pandas as pd


OWNER_MAP = {
    "BLANK_EAN":                ("MDM",                "Master Data Team",       7),
    "MISSING_CHAIN":            ("MDM",                "Master Data Team",       3),
    "MISSING_BRAND":            ("MDM",                "Master Data Team",       3),
    "MISSING_CATEGORY":         ("MDM",                "Master Data Team",       3),
    "INCORRECT_PACK_SIZE":      ("MDM",                "Master Data Team",       7),
    "DUPLICATE_EAN":            ("MDM",                "Master Data Team",       5),
    "DUPLICATE_CHAIN_ARTICLE":  ("Data Team",          "Data Engineering",       5),
    "DUPLICATE_EFFECTIVE_DATE": ("Data Team",          "Data Engineering",       3),

    "BLANK_MRP":                ("Sales Ops",          "Sales Operations",       3),
    "INACTIVE_ARTICLE":         ("Sales Ops",          "Sales Operations",       7),

    "BLANK_GST":                ("Finance",            "Finance / Tax Team",     5),
    "INCORRECT_GST":            ("Finance",            "Finance / Tax Team",     3),

    "MARGIN_OVER_100":          ("Commercial Finance", "Commercial Finance",     1),
    "NEGATIVE_MARGIN":          ("Commercial Finance", "Commercial Finance",     1),
    "BLANK_TRADE_MARGIN":       ("Commercial",         "Commercial Team",        5),
    "MISSING_COMMERCIALS":      ("Commercial",         "Commercial Team",        5),
    "EXPIRED_COMMERCIAL":       ("Commercial",         "Commercial Team",        3),
    "GST_CHANGED":              ("Finance",            "Finance / Tax Team",     3),
}


def owner_for(flag):
    """(dept, team, sla_days) for a validation flag. Unknown → MDM/7."""
    return OWNER_MAP.get(flag, ("MDM", "Master Data Team", 7))


def issue_log(validated_df, snapshot_date=None):
    """One row per (record, flag). Columns: Article_Key/EAN/Chain, Flag, Owner,
    Team, SLA_Days, Open_Date, Due_Date. Ready for a governance tracker."""
    snapshot_date = snapshot_date or dt.date.today()
    rows = []
    for _, r in validated_df.iterrows():
        flags = str(r.get("Validation_Flags") or "").split("; ")
        for f in filter(None, flags):
            dept, team, sla = owner_for(f)
            due = snapshot_date + dt.timedelta(days=sla)
            rows.append({
                "Open_Date": snapshot_date.isoformat(),
                "Chain": r.get("Chain", ""),
                "EAN": r.get("EAN", ""),
                "Article": r.get("Article", ""),
                "Brand": r.get("Brand", ""),
                "Validation_Flag": f,
                "Severity": r.get("QC_Severity", ""),
                "Owner_Dept": dept,
                "Owner_Team": team,
                "SLA_Days": sla,
                "Due_Date": due.isoformat(),
                "Resolution_Date": "",
                "Approval_Status": "OPEN",
            })
    return pd.DataFrame(rows, columns=[
        "Open_Date", "Chain", "EAN", "Article", "Brand",
        "Validation_Flag", "Severity", "Owner_Dept", "Owner_Team",
        "SLA_Days", "Due_Date", "Resolution_Date", "Approval_Status",
    ])


def kpi_snapshot(validated_df, enrich_report=None, snapshot_date=None):
    """Leadership KPI snapshot for one repository refresh."""
    snapshot_date = snapshot_date or dt.date.today()
    n = len(validated_df)
    sev = validated_df["QC_Severity"].value_counts().to_dict()
    published = int((validated_df["Record_Status"] == "PUBLISHED").sum())
    flag_counts = Counter()
    for f in validated_df["Validation_Flags"]:
        if f:
            for x in str(f).split("; "):
                flag_counts[x] += 1

    def pct(v):
        return round(100.0 * v / n, 2) if n else 0.0

    kpis = {
        "Snapshot_Date":       snapshot_date.isoformat(),
        "Total_Records":       n,
        "Unique_EANs":         int(validated_df["EAN"].nunique()),
        "Total_Chains":        int(validated_df["Chain"].nunique()),
        "PASS":                sev.get("PASS", 0),
        "WARNING":             sev.get("WARNING", 0),
        "FAIL":                sev.get("FAIL", 0),
        "BLOCKED":             sev.get("BLOCKED", 0),
        "PASS_pct":            pct(sev.get("PASS", 0)),
        "WARNING_pct":         pct(sev.get("WARNING", 0)),
        "FAIL_pct":            pct(sev.get("FAIL", 0)),
        "BLOCKED_pct":         pct(sev.get("BLOCKED", 0)),
        "Published_Rows":      published,
        "Repository_Health_pct": pct(published),
        "Confidence_Score_pct": round(
            100.0 * (sev.get("PASS", 0) + 0.6 * sev.get("WARNING", 0)) / n, 2
        ) if n else 0.0,
        "Blank_GST":           flag_counts.get("BLANK_GST", 0),
        "Blank_MRP":           flag_counts.get("BLANK_MRP", 0),
        "Blank_Pack_Size":     flag_counts.get("INCORRECT_PACK_SIZE", 0),
        "Duplicate_Chain_Article": flag_counts.get("DUPLICATE_CHAIN_ARTICLE", 0),
        "Negative_Margin":     flag_counts.get("NEGATIVE_MARGIN", 0),
    }
    if enrich_report:
        kpis.update({
            "Fountain_Matched_Rows":  enrich_report.get("fountain_matched_rows", 0),
            "Fountain_Match_pct":     enrich_report.get("fountain_matched_pct", 0.0),
            "New_EANs_Not_In_Master": len(enrich_report.get("unmatched_eans", [])),
            "Pack_Size_Parsed":       enrich_report.get("pack_size_parsed_from_name", 0),
            "Pack_Size_Still_Missing": enrich_report.get("final_missing_pack_size", 0),
        })
    return kpis


def append_kpi_history(kpi_dict, history_path):
    """Append a KPI snapshot to a CSV history for trend tracking."""
    import os
    df_new = pd.DataFrame([kpi_dict])
    if os.path.exists(history_path):
        df_old = pd.read_csv(history_path)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new
    df.to_csv(history_path, index=False)
    return df


def kpis_vs_targets(kpi_dict, targets=None):
    """Compare current KPIs to target thresholds."""
    targets = targets or {
        "Repository_Health_pct":  100.0,
        "PASS_pct":                99.0,
        "WARNING_pct":              1.0,
        "BLOCKED_pct":              0.0,
        "Fountain_Match_pct":     100.0,
        "New_EANs_Not_In_Master":   0,
        "Blank_GST":                0,
        "Blank_MRP":                0,
    }
    comparators = {
        "PASS_pct":              lambda cur, tgt: cur >= tgt,
        "Repository_Health_pct": lambda cur, tgt: cur >= tgt,
        "Fountain_Match_pct":    lambda cur, tgt: cur >= tgt,
    }
    rows = []
    for kpi, tgt in targets.items():
        cur = kpi_dict.get(kpi)
        if cur is None:
            continue
        cmp = comparators.get(kpi, lambda cur, tgt: cur <= tgt)
        status = "✅ ON TARGET" if cmp(cur, tgt) else "⚠️ GAP"
        rows.append({"KPI": kpi, "Current": cur, "Target": tgt, "Status": status})
    return pd.DataFrame(rows)


def build_exception_register(validated_df, out_path=None,
                             flag_to_reason=None):
    """Convert remaining WARNING/FAIL/BLOCKED rows to a documented
    business-exception register with owner + action + SLA + impact.
    """
    flag_to_reason = flag_to_reason or {
        "INCORRECT_PACK_SIZE": {
            "justification": "No trusted source has Pack Size (Fountain missing, "
                             "name has no numeric spec, and MDM has not yet supplied)",
            "action": "MDM to retrieve Pack Size from SAP article master",
            "expected_source": "SAP Article Master → Article_Master_Extension.csv",
            "impact": "Article held out of forecast until Pack Size supplied",
        },
        "BLANK_GST": {
            "justification": "No GST rate on file",
            "action": "Finance to publish GST_Master.csv entry",
            "expected_source": "SAP tax classification",
            "impact": "Cannot compute post-tax landed cost",
        },
        "BLANK_MRP": {
            "justification": "MRP missing at source",
            "action": "Sales Ops to supply MRP",
            "expected_source": "SAP pricing / Chain PO",
            "impact": "Cannot compute rupee margin",
        },
        "DUPLICATE_EAN": {
            "justification": "Same EAN mapped to multiple articles within a chain",
            "action": "MDM to consolidate",
            "expected_source": "SAP Article Master",
            "impact": "Ambiguous margin assignment",
        },
    }

    rows = []
    for _, r in validated_df[validated_df["QC_Severity"].isin(
            ("WARNING", "FAIL", "BLOCKED"))].iterrows():
        flags = [f for f in str(r.get("Validation_Flags") or "").split("; ") if f]
        for f in flags:
            spec = flag_to_reason.get(f, {
                "justification": f"Flag '{f}' — see validation.py",
                "action": "Investigate", "expected_source": "TBD",
                "impact": "TBD",
            })
            dept, team, sla = owner_for(f)
            rows.append({
                "EAN": r.get("EAN", ""), "Chain": r.get("Chain", ""),
                "Brand": r.get("Brand", ""), "Article": str(r.get("Article", ""))[:80],
                "Flag": f, "Severity": r.get("QC_Severity", ""),
                "Justification": spec["justification"],
                "Owner_Dept": dept, "Owner_Team": team,
                "Required_Action": spec["action"],
                "Expected_Source": spec["expected_source"],
                "SLA_Days": sla,
                "Business_Impact": spec["impact"],
            })
    df = pd.DataFrame(rows)
    if out_path and len(df):
        df.to_excel(out_path, index=False)
    return df


def quality_gate(validated_df, exception_register_df=None,
                 require_zero_blocked=True, require_zero_fail=True,
                 require_documented_warnings=True):
    """Return (passed: bool, reasons: list[str]) for build-gate enforcement."""
    reasons = []
    sev = validated_df["QC_Severity"].value_counts().to_dict()
    n = len(validated_df)

    if require_zero_blocked and sev.get("BLOCKED", 0) > 0:
        reasons.append("BLOCKED > 0 (%d records)" % sev["BLOCKED"])
    if require_zero_fail and sev.get("FAIL", 0) > 0:
        reasons.append("FAIL > 0 (%d records)" % sev["FAIL"])

    total_sev = sum(sev.values())
    if total_sev != n:
        reasons.append("Severity does not reconcile (%d != %d)" % (total_sev, n))

    warning_count = sev.get("WARNING", 0)
    if require_documented_warnings and warning_count > 0:
        if exception_register_df is None or exception_register_df.empty:
            reasons.append("WARNING > 0 without exception register")
        else:
            documented_eans = set(exception_register_df["EAN"].astype(str))
            warned_eans = set(
                validated_df.loc[validated_df["QC_Severity"] == "WARNING", "EAN"]
                .astype(str)
            )
            undocumented = warned_eans - documented_eans
            if undocumented:
                reasons.append(
                    "%d WARNING EAN(s) undocumented in exception register"
                    % len(undocumented)
                )

    return (len(reasons) == 0, reasons)


def enrich_from_previous_repo(dms_df, previous_repo_df):
    """Fallback enrichment: fill still-missing fields from a prior repository
    snapshot (last-known-good values). Uses Chain+EAN as key."""
    if previous_repo_df is None or previous_repo_df.empty:
        return dms_df, {"filled_from_prior": 0}

    def clean_ean(v):
        s = str(v).strip()
        return s[:-2] if s.endswith(".0") else s

    df = dms_df.copy()
    df["_key"] = df["Chain"].astype(str).str.strip() + "|" + df["EAN"].map(clean_ean)
    prior = previous_repo_df.copy()
    prior["_key"] = prior["Chain"].astype(str).str.strip() + "|" + prior["EAN"].map(clean_ean)
    prior = prior.drop_duplicates(subset=["_key"], keep="last")

    fill_cols = ["Pack Size", "GST %", "Category", "Sub Category", "Range", "Brand"]
    prior_slim = prior[["_key"] + [c for c in fill_cols if c in prior.columns]].rename(
        columns={c: f"_prev_{c}" for c in fill_cols if c in prior.columns}
    )
    merged = df.merge(prior_slim, on="_key", how="left")

    filled = 0
    for c in fill_cols:
        prev_c = f"_prev_{c}"
        if prev_c not in merged.columns:
            continue
        blank = merged[c].map(lambda v: (v is None) or str(v).strip() == "" or pd.isna(v))
        fill_mask = blank & merged[prev_c].notna()
        merged.loc[fill_mask, c] = merged.loc[fill_mask, prev_c]
        filled += int(fill_mask.sum())

    merged = merged.drop(columns=[c for c in merged.columns if c.startswith("_prev_")])
    merged = merged.drop(columns=["_key"])
    return merged.reset_index(drop=True), {"filled_from_prior": filled}
