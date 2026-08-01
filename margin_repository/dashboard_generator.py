# -*- coding: utf-8 -*-
"""Generate a self-contained HTML Approval & Monitoring Dashboard.

Opens in any browser — no server needed. Reads repository state and
produces a single HTML file with:
  - Pending approvals
  - Approved today
  - Rejected
  - High-risk changes
  - Expired margins
  - Future-effective margins
  - QC health
  - Chain-wise summary
  - Alerts feed
"""
import json
import os
import pandas as pd
from repository import MarginRepository
from alerts import scan_alerts
from config import DEFAULT_CONFIG, classify_margin_risk


def generate_dashboard(repo, output_path="Margin_Dashboard.html",
                       changelog=None, cfg=None):
    """Generate a self-contained HTML dashboard from repository state."""
    cfg = cfg or DEFAULT_CONFIG
    cur = repo.current(include_held=True)
    hist = repo.history
    alerts = scan_alerts(repo, changelog, cfg)

    _n = lambda s: pd.to_numeric(s, errors="coerce")
    today = pd.Timestamp.today().normalize()

    # Compute dashboard data
    total = len(cur)
    if total == 0:
        data = _empty_data()
    else:
        sev = cur["QC_Severity"].value_counts().to_dict()
        pub = int((cur["Record_Status"] == "PUBLISHED").sum())
        health = round(100.0 * pub / total, 1)

        # Chain summary
        chain_summary = []
        for chain, g in cur.groupby("Chain"):
            fem = _n(g.get("Final Effective Margin %"))
            chain_summary.append({
                "chain": str(chain),
                "articles": len(g),
                "avg_margin": round(fem.mean(), 2) if fem.notna().any() else 0,
                "pass": int((g["QC_Severity"] == "PASS").sum()),
                "warning": int((g["QC_Severity"] == "WARNING").sum()),
                "fail": int((g["QC_Severity"] == "FAIL").sum()),
                "blocked": int((g["QC_Severity"] == "BLOCKED").sum()),
                "health": round(100.0 * (g["Record_Status"] == "PUBLISHED").sum() / len(g), 1),
            })
        chain_summary.sort(key=lambda x: x["avg_margin"], reverse=True)

        # High-risk records
        high_risk = []
        if not cur.empty:
            fem = _n(cur.get("Final Effective Margin %"))
            for _, r in cur.iterrows():
                m = _n(pd.Series([r.get("Final Effective Margin %")])).iloc[0]
                if pd.notna(m) and (m > 50 or m < 5):
                    high_risk.append({
                        "chain": str(r.get("Chain", "")),
                        "article": str(r.get("Article", ""))[:50],
                        "ean": str(r.get("EAN", "")),
                        "margin": float(m),
                        "severity": str(r.get("QC_Severity", "")),
                        "flags": str(r.get("Validation_Flags", "")),
                    })

        # Expired
        expired = []
        if "Effective To" in cur.columns:
            eto = pd.to_datetime(cur["Effective To"], errors="coerce")
            exp_mask = eto < today
            for _, r in cur[exp_mask].iterrows():
                expired.append({
                    "chain": str(r.get("Chain", "")),
                    "article": str(r.get("Article", ""))[:50],
                    "ean": str(r.get("EAN", "")),
                    "effective_to": str(r.get("Effective To", "")),
                })

        # Future effective
        future = []
        if "Effective From" in cur.columns:
            efrom = pd.to_datetime(cur["Effective From"], errors="coerce")
            fut_mask = efrom > today
            for _, r in cur[fut_mask].iterrows():
                future.append({
                    "chain": str(r.get("Chain", "")),
                    "article": str(r.get("Article", ""))[:50],
                    "ean": str(r.get("EAN", "")),
                    "effective_from": str(r.get("Effective From", "")),
                    "margin": str(r.get("Final Effective Margin %", "")),
                })

        # HELD records (pending resolution)
        held = []
        for _, r in cur[cur["Record_Status"] == "HELD"].iterrows():
            held.append({
                "chain": str(r.get("Chain", "")),
                "article": str(r.get("Article", ""))[:50],
                "ean": str(r.get("EAN", "")),
                "severity": str(r.get("QC_Severity", "")),
                "flags": str(r.get("Validation_Flags", "")),
            })

        # Changelog summary
        cl_summary = []
        if changelog is not None and not changelog.empty:
            for _, r in changelog.head(50).iterrows():
                cl_summary.append({
                    "chain": str(r.get("Chain", "")),
                    "article": str(r.get("Article", ""))[:40],
                    "field": str(r.get("Field", "")),
                    "old": str(r.get("Old Value", "")),
                    "new": str(r.get("New Value", "")),
                    "diff": str(r.get("Difference", "")),
                })

        data = {
            "total": total,
            "pass": sev.get("PASS", 0),
            "warning": sev.get("WARNING", 0),
            "fail": sev.get("FAIL", 0),
            "blocked": sev.get("BLOCKED", 0),
            "published": pub,
            "held": total - pub,
            "health": health,
            "chains": int(cur["Chain"].nunique()),
            "versions": len(hist),
            "chain_summary": chain_summary,
            "high_risk": high_risk[:20],
            "expired": expired[:20],
            "future": future[:20],
            "held_records": held[:30],
            "changelog": cl_summary,
            "alerts": [{"severity": a["severity"], "title": a["title"],
                        "detail": a["detail"], "action": a.get("action", ""),
                        "count": a.get("count", 0)} for a in alerts],
            "generated": today.strftime("%Y-%m-%d %H:%M"),
        }

    html = _build_html(data)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


def _empty_data():
    return {
        "total": 0, "pass": 0, "warning": 0, "fail": 0, "blocked": 0,
        "published": 0, "held": 0, "health": 0, "chains": 0, "versions": 0,
        "chain_summary": [], "high_risk": [], "expired": [], "future": [],
        "held_records": [], "changelog": [], "alerts": [],
        "generated": pd.Timestamp.today().strftime("%Y-%m-%d %H:%M"),
    }


def _build_html(data):
    return '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Margin Repository — Approval Dashboard</title>
<style>
:root {
  --bg: #f5f7fa; --card-bg: #ffffff; --text: #1a1a2e; --text-muted: #6b7280;
  --border: #e5e7eb; --accent: #1f4e78; --accent-light: #2e75b6;
  --pass: #10b981; --pass-bg: #d1fae5; --warn: #f59e0b; --warn-bg: #fef3c7;
  --fail: #ef4444; --fail-bg: #fee2e2; --blocked: #991b1b; --blocked-bg: #fecaca;
  --info: #3b82f6; --info-bg: #dbeafe;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f172a; --card-bg: #1e293b; --text: #e2e8f0; --text-muted: #94a3b8;
    --border: #334155; --accent: #60a5fa; --accent-light: #93c5fd;
    --pass-bg: #064e3b; --warn-bg: #451a03; --fail-bg: #450a0a; --blocked-bg: #450a0a;
    --info-bg: #1e3a5f;
  }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
       background: var(--bg); color: var(--text); line-height: 1.5; }
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }
header { background: var(--accent); color: white; padding: 24px 20px; margin-bottom: 24px;
         border-radius: 12px; }
header h1 { font-size: 1.5rem; font-weight: 700; }
header p { font-size: 0.85rem; opacity: 0.85; margin-top: 4px; }
.stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
             gap: 16px; margin-bottom: 24px; }
.stat-card { background: var(--card-bg); border: 1px solid var(--border);
             border-radius: 10px; padding: 16px; text-align: center; }
.stat-card .value { font-size: 2rem; font-weight: 700; }
.stat-card .label { font-size: 0.78rem; color: var(--text-muted); text-transform: uppercase;
                    letter-spacing: 0.05em; margin-top: 4px; }
.stat-card.pass .value { color: var(--pass); }
.stat-card.warn .value { color: var(--warn); }
.stat-card.fail .value { color: var(--fail); }
.stat-card.blocked .value { color: var(--blocked); }
.stat-card.accent .value { color: var(--accent); }

.tabs { display: flex; gap: 4px; margin-bottom: 16px; flex-wrap: wrap; }
.tab { padding: 8px 18px; border: 1px solid var(--border); border-radius: 8px 8px 0 0;
       background: var(--card-bg); cursor: pointer; font-size: 0.85rem;
       color: var(--text-muted); border-bottom: none; }
.tab.active { background: var(--accent); color: white; border-color: var(--accent); }
.tab-content { display: none; background: var(--card-bg); border: 1px solid var(--border);
               border-radius: 0 8px 8px 8px; padding: 20px; margin-bottom: 24px; }
.tab-content.active { display: block; }

table { width: 100%%; border-collapse: collapse; font-size: 0.82rem; }
th { background: var(--accent); color: white; padding: 10px 12px; text-align: left;
     font-weight: 600; position: sticky; top: 0; }
td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
tr:hover { background: var(--info-bg); }
.overflow-x { overflow-x: auto; }

.alert { padding: 12px 16px; border-radius: 8px; margin-bottom: 10px;
         border-left: 4px solid; }
.alert.critical { background: var(--fail-bg); border-color: var(--fail); }
.alert.high { background: var(--warn-bg); border-color: var(--warn); }
.alert.medium { background: var(--info-bg); border-color: var(--info); }
.alert.info { background: var(--pass-bg); border-color: var(--pass); }
.alert .title { font-weight: 600; font-size: 0.9rem; }
.alert .detail { font-size: 0.82rem; color: var(--text-muted); margin-top: 2px; }
.alert .action { font-size: 0.78rem; margin-top: 4px; font-style: italic; }

.badge { display: inline-block; padding: 2px 8px; border-radius: 4px;
         font-size: 0.72rem; font-weight: 600; }
.badge.pass { background: var(--pass-bg); color: #065f46; }
.badge.warning { background: var(--warn-bg); color: #92400e; }
.badge.fail { background: var(--fail-bg); color: #991b1b; }
.badge.blocked { background: var(--blocked-bg); color: #450a0a; }

.health-bar { width: 100%%; height: 8px; background: var(--border); border-radius: 4px;
              overflow: hidden; margin-top: 6px; }
.health-fill { height: 100%%; border-radius: 4px; transition: width 0.5s; }

.section-title { font-size: 1.1rem; font-weight: 700; color: var(--accent);
                 margin-bottom: 12px; padding-bottom: 8px;
                 border-bottom: 2px solid var(--accent); }

footer { text-align: center; padding: 20px; color: var(--text-muted);
         font-size: 0.78rem; }
</style>
</head>
<body>
<div class="container">
<header>
  <h1>Margin Repository — Approval & Monitoring Dashboard</h1>
  <p>Honasa Consumer | Modern Trade | Generated: %(generated)s</p>
</header>

<div class="stat-grid">
  <div class="stat-card accent"><div class="value">%(total)d</div><div class="label">Total Articles</div></div>
  <div class="stat-card accent"><div class="value">%(chains)d</div><div class="label">Chains</div></div>
  <div class="stat-card pass"><div class="value">%(published)d</div><div class="label">Published</div></div>
  <div class="stat-card pass"><div class="value">%(pass)d</div><div class="label">Pass</div></div>
  <div class="stat-card warn"><div class="value">%(warning)d</div><div class="label">Warning</div></div>
  <div class="stat-card fail"><div class="value">%(fail)d</div><div class="label">Fail</div></div>
  <div class="stat-card blocked"><div class="value">%(blocked)d</div><div class="label">Blocked</div></div>
  <div class="stat-card accent">
    <div class="value">%(health).1f%%</div><div class="label">Health Score</div>
    <div class="health-bar"><div class="health-fill" style="width:%(health).1f%%; background:%(health_color)s;"></div></div>
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab('alerts')">Alerts (%(alert_count)d)</div>
  <div class="tab" onclick="showTab('held')">Pending Resolution (%(held)d)</div>
  <div class="tab" onclick="showTab('chains')">Chain Summary</div>
  <div class="tab" onclick="showTab('highrisk')">High Risk</div>
  <div class="tab" onclick="showTab('changelog')">Recent Changes</div>
  <div class="tab" onclick="showTab('expired')">Expired</div>
  <div class="tab" onclick="showTab('future')">Future Effective</div>
</div>

<div id="tab-alerts" class="tab-content active">
  <div class="section-title">Business Alerts</div>
  %(alerts_html)s
</div>

<div id="tab-held" class="tab-content">
  <div class="section-title">Records Pending Resolution</div>
  <div class="overflow-x">
  <table>
    <thead><tr><th>Chain</th><th>Article</th><th>EAN</th><th>Severity</th><th>Validation Flags</th></tr></thead>
    <tbody>%(held_html)s</tbody>
  </table>
  </div>
</div>

<div id="tab-chains" class="tab-content">
  <div class="section-title">Chain-wise Margin Summary</div>
  <div class="overflow-x">
  <table>
    <thead><tr><th>Chain</th><th>Articles</th><th>Avg Margin %%</th><th>Pass</th><th>Warn</th><th>Fail</th><th>Blocked</th><th>Health %%</th></tr></thead>
    <tbody>%(chains_html)s</tbody>
  </table>
  </div>
</div>

<div id="tab-highrisk" class="tab-content">
  <div class="section-title">High-Risk Margins</div>
  <div class="overflow-x">
  <table>
    <thead><tr><th>Chain</th><th>Article</th><th>EAN</th><th>Margin %%</th><th>Severity</th><th>Flags</th></tr></thead>
    <tbody>%(highrisk_html)s</tbody>
  </table>
  </div>
</div>

<div id="tab-changelog" class="tab-content">
  <div class="section-title">Recent Margin Changes</div>
  <div class="overflow-x">
  <table>
    <thead><tr><th>Chain</th><th>Article</th><th>Field</th><th>Old</th><th>New</th><th>Delta</th></tr></thead>
    <tbody>%(changelog_html)s</tbody>
  </table>
  </div>
</div>

<div id="tab-expired" class="tab-content">
  <div class="section-title">Expired Commercial Terms</div>
  <div class="overflow-x">
  <table>
    <thead><tr><th>Chain</th><th>Article</th><th>EAN</th><th>Effective To</th></tr></thead>
    <tbody>%(expired_html)s</tbody>
  </table>
  </div>
</div>

<div id="tab-future" class="tab-content">
  <div class="section-title">Future-Effective Margins</div>
  <div class="overflow-x">
  <table>
    <thead><tr><th>Chain</th><th>Article</th><th>EAN</th><th>Effective From</th><th>Margin %%</th></tr></thead>
    <tbody>%(future_html)s</tbody>
  </table>
  </div>
</div>

<footer>
  Margin Repository v1.1.0 | Schema version 1.1.0 | %(versions)d version records
</footer>
</div>

<script>
function showTab(id) {
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  event.target.classList.add('active');
}
</script>
</body>
</html>''' % _build_template_vars(data)


def _build_template_vars(data):
    health = data.get("health", 0)
    if health >= 90:
        hc = "#10b981"
    elif health >= 70:
        hc = "#f59e0b"
    else:
        hc = "#ef4444"

    def _esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Alerts
    alerts_html = ""
    for a in data.get("alerts", []):
        sev_class = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium"}.get(
            a["severity"], "info")
        alerts_html += '<div class="alert %s">' % sev_class
        alerts_html += '<div class="title">[%s] %s</div>' % (_esc(a["severity"]), _esc(a["title"]))
        alerts_html += '<div class="detail">%s</div>' % _esc(a["detail"])
        if a.get("action"):
            alerts_html += '<div class="action">Action: %s</div>' % _esc(a["action"])
        alerts_html += '</div>\n'
    if not alerts_html:
        alerts_html = '<div class="alert info"><div class="title">No alerts</div></div>'

    # Held records
    held_html = ""
    for r in data.get("held_records", []):
        badge = '<span class="badge %s">%s</span>' % (r["severity"].lower(), _esc(r["severity"]))
        held_html += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n' % (
            _esc(r["chain"]), _esc(r["article"]), _esc(r["ean"]), badge, _esc(r["flags"]))
    if not held_html:
        held_html = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No held records</td></tr>'

    # Chain summary
    chains_html = ""
    for c in data.get("chain_summary", []):
        bar_color = "#10b981" if c["health"] >= 90 else "#f59e0b" if c["health"] >= 70 else "#ef4444"
        chains_html += '<tr><td><strong>%s</strong></td><td>%d</td><td>%.1f</td>' % (
            _esc(c["chain"]), c["articles"], c["avg_margin"])
        chains_html += '<td>%d</td><td>%d</td><td>%d</td><td>%d</td>' % (
            c["pass"], c["warning"], c["fail"], c["blocked"])
        chains_html += '<td>%.1f<div class="health-bar"><div class="health-fill" style="width:%.1f%%;background:%s;"></div></div></td></tr>\n' % (
            c["health"], c["health"], bar_color)

    # High risk
    highrisk_html = ""
    for r in data.get("high_risk", []):
        highrisk_html += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%.1f</td><td>%s</td><td>%s</td></tr>\n' % (
            _esc(r["chain"]), _esc(r["article"]), _esc(r["ean"]),
            r["margin"], _esc(r["severity"]), _esc(r["flags"]))
    if not highrisk_html:
        highrisk_html = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">No high-risk records</td></tr>'

    # Changelog
    changelog_html = ""
    for r in data.get("changelog", []):
        changelog_html += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n' % (
            _esc(r["chain"]), _esc(r["article"]), _esc(r["field"]),
            _esc(r["old"]), _esc(r["new"]), _esc(r["diff"]))
    if not changelog_html:
        changelog_html = '<tr><td colspan="6" style="text-align:center;color:var(--text-muted)">No recent changes</td></tr>'

    # Expired
    expired_html = ""
    for r in data.get("expired", []):
        expired_html += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n' % (
            _esc(r["chain"]), _esc(r["article"]), _esc(r["ean"]), _esc(r["effective_to"]))
    if not expired_html:
        expired_html = '<tr><td colspan="4" style="text-align:center;color:var(--text-muted)">No expired records</td></tr>'

    # Future
    future_html = ""
    for r in data.get("future", []):
        future_html += '<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\n' % (
            _esc(r["chain"]), _esc(r["article"]), _esc(r["ean"]),
            _esc(r["effective_from"]), _esc(r.get("margin", "")))
    if not future_html:
        future_html = '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">No future-effective records</td></tr>'

    def _pct_safe(s):
        return s.replace("%", "%%")

    return {
        "total": data["total"], "chains": data["chains"],
        "published": data["published"], "pass": data["pass"],
        "warning": data["warning"], "fail": data["fail"],
        "blocked": data["blocked"], "held": data["held"],
        "health": health, "health_color": hc,
        "versions": data["versions"],
        "alert_count": len(data.get("alerts", [])),
        "alerts_html": _pct_safe(alerts_html),
        "held_html": _pct_safe(held_html),
        "chains_html": _pct_safe(chains_html),
        "highrisk_html": _pct_safe(highrisk_html),
        "changelog_html": _pct_safe(changelog_html),
        "expired_html": _pct_safe(expired_html),
        "future_html": _pct_safe(future_html),
        "generated": data["generated"],
    }
