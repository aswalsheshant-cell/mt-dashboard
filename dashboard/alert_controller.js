/**
 * Sprint 9 Phase 1b: Alert Controller
 * Manages operational alerts from alerts_feed.json
 * Renders alert cards, updates navigation badge, and handles drill-down navigation
 */

// Attached to `window` deliberately: index.html's buildAlerts() gates on
// `window.AlertController`. A bare top-level `const` does NOT become a window
// property in a classic script, so that check silently failed and the
// Operational Alerts tab rendered blank with no console error.
// (inventory_engine.js already uses this same window.* form.)
window.AlertController = (function () {
  let activeAlerts = [];

  // The badge sits in the header bar, outside <nav>: the old 'nav .alert-badge'
  // selector never matched, so the hard-coded red "0" stayed on screen whatever
  // the feed said. Now: a count only when there are critical alerts, hidden on a
  // clean feed, and "!" (never a number) when the feed failed to load.
  function updateNavBadge() {
    const badge = document.querySelector('.alert-badge');
    if (!badge) return;
    const status = window.alertsFeedStatus;
    const feed = window.alertsFeed || { metadata: {} };
    const criticalCount = Number(feed.metadata?.critical_count) || 0;
    if (status === 'error') {
      badge.textContent = '!';
      badge.style.background = '#6b7280';
      badge.title = 'Alert feed failed to load - critical alert count unknown';
      badge.style.display = 'inline-block';
    } else if (status === 'loaded' && criticalCount > 0) {
      badge.textContent = String(criticalCount);
      badge.style.background = '#ef4444';
      badge.title = `${criticalCount} critical alert${criticalCount > 1 ? 's' : ''} - see Operational Alerts`;
      badge.style.display = 'inline-block';
    } else {
      badge.textContent = '';
      badge.title = '';
      badge.style.display = 'none';
    }
    badge.classList.toggle('active', status === 'loaded' && criticalCount > 0);
  }

  function getSeverityColor(severity) {
    switch (severity) {
      case 'CRITICAL': return '#ef4444';
      case 'WARNING': return '#f59e0b';
      case 'INFO': return '#3b82f6';
      default: return '#6b7280';
    }
  }

  function getSeverityClass(severity) {
    switch (severity) {
      case 'CRITICAL': return 'severity-critical';
      case 'WARNING': return 'severity-warning';
      case 'INFO': return 'severity-info';
      default: return 'severity-default';
    }
  }

  function formatTimestamp(iso) {
    if (!iso) return '–';
    const d = new Date(iso);
    return d.toLocaleString('en-IN', {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  }

  function renderAlertsList() {
    const feed = window.alertsFeed || { alerts: [] };
    activeAlerts = feed.alerts || [];

    const container = document.getElementById('alertsCardFeed');
    if (!container) return;

    // "No active alerts" is a claim about loaded data -- never show it when the
    // feed failed or has not arrived yet.
    if (window.alertsFeedStatus === 'error') {
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: #92400e; background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; font-size: 14px;">⚠ Alert feed unavailable — could not load alerts_feed.json. This is not a confirmation that metrics are healthy.</div>';
      return;
    }
    if (window.alertsFeedStatus === 'loading') {
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: #999; font-size: 14px;">Loading alerts…</div>';
      return;
    }

    if (!activeAlerts || activeAlerts.length === 0) {
      container.innerHTML = '<div style="padding: 20px; text-align: center; color: #999; font-size: 14px;">No active alerts. All metrics within thresholds.</div>';
      return;
    }

    const alertCards = activeAlerts.map(alert => {
      const severityColor = getSeverityColor(alert.severity);
      const severityClass = getSeverityClass(alert.severity);
      const timestamp = formatTimestamp(alert.timestamp);

      return `
        <div class="alert-card ${severityClass}" style="border-left: 4px solid ${severityColor}; padding: 16px; margin-bottom: 12px; background: #f9fafb; border-radius: 6px; cursor: pointer;" onclick="window.location.href='${alert.action_url || '#'}'">
          <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 8px;">
            <div style="flex: 1;">
              <div style="font-weight: 600; color: #111; margin-bottom: 4px;">${alert.account_name || alert.account_id || 'Unknown'}</div>
              <div style="font-size: 12px; color: #666;">${alert.alert_type} · ${alert.metric_name}</div>
            </div>
            <div style="padding: 2px 8px; background: ${severityColor}; color: white; border-radius: 3px; font-size: 11px; font-weight: 600; white-space: nowrap; margin-left: 12px;">${alert.severity}</div>
          </div>
          <div style="font-size: 13px; color: #333; margin: 8px 0; line-height: 1.4;">${alert.message}</div>
          <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; margin: 12px 0; font-size: 12px;">
            <div style="background: white; padding: 8px; border-radius: 4px;">
              <div style="color: #999; margin-bottom: 2px;">Current</div>
              <div style="font-weight: 600; color: #111;">${typeof alert.current_value === 'number' ? alert.current_value.toFixed(1) : '–'}${alert.metric_name === 'PES' ? '%' : alert.metric_name === 'CFR' || alert.metric_name === 'OTIF' ? '%' : 'd'}</div>
            </div>
            <div style="background: white; padding: 8px; border-radius: 4px;">
              <div style="color: #999; margin-bottom: 2px;">Target</div>
              <div style="font-weight: 600; color: #111;">${typeof alert.threshold === 'number' ? alert.threshold.toFixed(1) : '–'}${alert.metric_name === 'PES' ? '%' : alert.metric_name === 'CFR' || alert.metric_name === 'OTIF' ? '%' : 'd'}</div>
            </div>
            <div style="background: white; padding: 8px; border-radius: 4px;">
              <div style="color: #999; margin-bottom: 2px;">Gap</div>
              <div style="font-weight: 600; color: ${severityColor};">${typeof alert.gap === 'number' ? alert.gap.toFixed(1) : '–'}${alert.metric_name === 'PES' ? '%' : alert.metric_name === 'CFR' || alert.metric_name === 'OTIF' ? '%' : 'd'}</div>
            </div>
          </div>
          <div style="font-size: 12px; color: #666; margin-top: 8px; padding-top: 8px; border-top: 1px solid #e5e7eb;">${alert.recommendation || 'No recommendation'}</div>
          <div style="font-size: 11px; color: #999; margin-top: 6px;">Updated: ${timestamp}</div>
        </div>
      `;
    }).join('');

    container.innerHTML = alertCards;
  }

  function buildAlerts() {
    const s = document.getElementById('tab-alerts');
    if (!s) return;

    const feed = window.alertsFeed || { metadata: { total_alerts: 0, critical_count: 0, warning_count: 0 }, alerts: [] };
    const { total_alerts = 0, critical_count = 0, warning_count = 0 } = feed.metadata || {};
    // '–' rather than 0 until the feed has actually loaded: 0 reads as "verified none".
    const feedLoaded = !window.alertsFeedStatus || window.alertsFeedStatus === 'loaded';
    const shown = (v) => feedLoaded ? v : '–';

    const kpiHtml = [
      { label: 'Total Alerts', value: shown(total_alerts), color: '#6b7280' },
      { label: 'Critical', value: shown(critical_count), color: '#ef4444' },
      { label: 'Warnings', value: shown(warning_count), color: '#f59e0b' }
    ].map(kpi => `
      <div style="padding: 16px; background: #f9fafb; border-radius: 8px; border-left: 3px solid ${kpi.color};">
        <div style="color: #666; font-size: 12px; margin-bottom: 4px;">${kpi.label}</div>
        <div style="font-size: 28px; font-weight: 700; color: #111;">${kpi.value}</div>
      </div>
    `).join('');

    s.innerHTML = `
      <div style="padding: 24px;">
        <div class="scorecard-header">
          <h2 style="margin: 0 0 24px 0; font-size: 24px; font-weight: 700; color: #111;">Operational Alerts</h2>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 24px;">
            ${kpiHtml}
          </div>
        </div>
        <div id="alertsCardFeed" style="margin-top: 24px;"></div>
      </div>
    `;

    renderAlertsList();
    updateNavBadge();
  }

  return {
    buildAlerts,
    renderAlertsList,
    updateNavBadge,
    // Called when the alerts_feed.json fetch settles (index.html). Repaints the
    // tab if it was already rendered, so "Loading alerts…" never sticks.
    onFeedSettled() {
      updateNavBadge();
      const tab = document.getElementById('tab-alerts');
      if (tab && tab.innerHTML.trim()) buildAlerts();
    },
    load() {
      buildAlerts();
    }
  };
})();
