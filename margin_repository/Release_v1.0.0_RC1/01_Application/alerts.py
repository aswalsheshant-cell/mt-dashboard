# -*- coding: utf-8 -*-
"""Business alerts engine for the Margin Repository.

Scans the repository for conditions that require attention and produces
a structured alert feed. Alerts are classified by severity (CRITICAL,
HIGH, MEDIUM, LOW, INFO) and category.
"""
import pandas as pd
from config import DEFAULT_CONFIG, classify_margin_risk


def scan_alerts(repo, changelog=None, cfg=None):
    """Scan the repository and return a list of alert dicts.

    Each alert: {severity, category, title, detail, articles, action}.
    """
    cfg = cfg or DEFAULT_CONFIG
    alerts = []
    cur = repo.current(include_held=True)
    hist = repo.history

    if cur.empty:
        return [{"severity": "INFO", "category": "repository",
                 "title": "Empty repository", "detail": "No articles imported yet.",
                 "count": 0, "action": "Import a chain margin file"}]

    _n = lambda s: pd.to_numeric(s, errors="coerce")
    today = pd.Timestamp.today().normalize()

    # 1. High-risk margin changes (from changelog)
    if changelog is not None and not changelog.empty:
        margin_fields = {"Final Effective Margin %", "Trade Margin %", "TOT %"}
        mc = changelog[changelog["Field"].isin(margin_fields)].copy()
        mc["delta"] = _n(mc["Difference"]).abs()
        high_risk = mc[mc["delta"] > cfg["risk_thresholds"]["warning_max_pp"]]
        if not high_risk.empty:
            alerts.append({
                "severity": "CRITICAL",
                "category": "margin_change",
                "title": "High-risk margin changes detected",
                "detail": "%d changes exceed ±%.1f pp threshold" % (
                    len(high_risk), cfg["risk_thresholds"]["warning_max_pp"]),
                "count": len(high_risk),
                "articles": high_risk[["Chain", "Article", "EAN", "Field",
                                       "Old Value", "New Value", "Difference"]].to_dict("records"),
                "action": "Review and approve with commercial/finance sign-off",
            })

    # 2. Duplicate EANs
    dups = cur[cur["Validation_Flags"].str.contains("DUPLICATE_EAN", na=False)]
    if not dups.empty:
        alerts.append({
            "severity": "HIGH",
            "category": "data_quality",
            "title": "Duplicate EAN codes detected",
            "detail": "%d records share an EAN with another article in the same chain" % len(dups),
            "count": len(dups),
            "articles": dups[["Chain", "Article", "EAN"]].to_dict("records"),
            "action": "Resolve duplicate EANs — verify article master",
        })

    # 3. Missing GST
    gst_issues = cur[cur["Validation_Flags"].str.contains("BLANK_GST|INCORRECT_GST", na=False)]
    if not gst_issues.empty:
        alerts.append({
            "severity": "HIGH",
            "category": "gst",
            "title": "GST validation issues",
            "detail": "%d records with blank or incorrect GST" % len(gst_issues),
            "count": len(gst_issues),
            "articles": gst_issues[["Chain", "Article", "EAN", "GST %",
                                     "Validation_Flags"]].to_dict("records"),
            "action": "Verify GST rates with Finance/Tax team",
        })

    # 4. Expired margins
    if "Effective To" in cur.columns:
        eto = pd.to_datetime(cur["Effective To"], errors="coerce")
        expired = cur[eto < today]
        if not expired.empty:
            alerts.append({
                "severity": "MEDIUM",
                "category": "expiry",
                "title": "Expired commercial terms",
                "detail": "%d articles have expired Effective To dates" % len(expired),
                "count": len(expired),
                "articles": expired[["Chain", "Article", "EAN",
                                      "Effective To"]].to_dict("records"),
                "action": "Renew or delist expired commercials",
            })

    # 5. Future-effective margins about to activate
    if "Effective From" in cur.columns:
        efrom = pd.to_datetime(cur["Effective From"], errors="coerce")
        upcoming = cur[(efrom > today) & (efrom <= today + pd.Timedelta(days=30))]
        if not upcoming.empty:
            alerts.append({
                "severity": "INFO",
                "category": "upcoming",
                "title": "Margins becoming active within 30 days",
                "detail": "%d articles have future effective dates" % len(upcoming),
                "count": len(upcoming),
                "articles": upcoming[["Chain", "Article", "EAN",
                                       "Effective From"]].to_dict("records"),
                "action": "Verify readiness for upcoming margin activation",
            })

    # 6. Chains with no approved margins
    all_chains_with_data = set(cur["Chain"].dropna().unique())
    published = cur[cur["Record_Status"] == "PUBLISHED"]
    chains_with_approved = set(published["Chain"].dropna().unique())
    no_approved = all_chains_with_data - chains_with_approved
    if no_approved:
        alerts.append({
            "severity": "HIGH",
            "category": "coverage",
            "title": "Chains with no approved margins",
            "detail": "%d chains have articles but none are forecast-ready" % len(no_approved),
            "count": len(no_approved),
            "articles": [{"Chain": c} for c in sorted(no_approved)],
            "action": "Review and resolve validation failures for these chains",
        })

    # 7. Articles without any margin
    tm = _n(cur.get("Trade Margin %"))
    fem = _n(cur.get("Final Effective Margin %"))
    no_margin = cur[(tm.isna() | (tm == 0)) & (fem.isna() | (fem == 0))]
    if not no_margin.empty:
        alerts.append({
            "severity": "MEDIUM",
            "category": "missing_data",
            "title": "Articles without margin data",
            "detail": "%d articles have zero or blank margins" % len(no_margin),
            "count": len(no_margin),
            "articles": no_margin[["Chain", "Article", "EAN"]].to_dict("records"),
            "action": "Provide commercial terms for these articles",
        })

    # 8. BLOCKED records needing resolution
    blocked = cur[cur["QC_Severity"] == "BLOCKED"]
    if not blocked.empty:
        alerts.append({
            "severity": "CRITICAL",
            "category": "blocked",
            "title": "BLOCKED records require resolution",
            "detail": "%d records are blocked from publication" % len(blocked),
            "count": len(blocked),
            "articles": blocked[["Chain", "Article", "EAN",
                                  "Validation_Flags"]].to_dict("records"),
            "action": "Fix validation issues or obtain override approval",
        })

    # 9. FAIL records
    fails = cur[cur["QC_Severity"] == "FAIL"]
    if not fails.empty:
        alerts.append({
            "severity": "HIGH",
            "category": "failed",
            "title": "FAIL records held from forecast",
            "detail": "%d records have validation failures" % len(fails),
            "count": len(fails),
            "articles": fails[["Chain", "Article", "EAN",
                                "Validation_Flags"]].to_dict("records"),
            "action": "Correct data issues or reclassify severity",
        })

    # 10. Repository health summary
    total = len(cur)
    pub = int((cur["Record_Status"] == "PUBLISHED").sum())
    health = round(100.0 * pub / total, 1) if total else 0
    if health < 90:
        alerts.append({
            "severity": "MEDIUM",
            "category": "health",
            "title": "Repository health below 90%%",
            "detail": "Health: %.1f%% (%d/%d published)" % (health, pub, total),
            "count": total - pub,
            "action": "Resolve held records to improve health score",
        })

    alerts.sort(key=lambda a: {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2,
                                "LOW": 3, "INFO": 4}.get(a["severity"], 5))
    return alerts


def format_alert_text(alerts):
    """Format alerts as a human-readable text report."""
    if not alerts:
        return "No alerts — repository is clean."
    lines = ["MARGIN REPOSITORY — BUSINESS ALERTS", "=" * 50, ""]
    sev_icon = {"CRITICAL": "[!!]", "HIGH": "[!]", "MEDIUM": "[~]",
                "LOW": "[-]", "INFO": "[i]"}
    for a in alerts:
        icon = sev_icon.get(a["severity"], "[?]")
        lines.append("%s %s  %s" % (icon, a["severity"], a["title"]))
        lines.append("    %s" % a["detail"])
        lines.append("    Action: %s" % a.get("action", ""))
        lines.append("")
    return "\n".join(lines)
