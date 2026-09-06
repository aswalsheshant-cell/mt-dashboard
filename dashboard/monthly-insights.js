/**
 * Monthly Insights Renderer — One-page executive summary component.
 * Displays: Primary vs Secondary alignment, ND/WD positioning, distributor health,
 * forecast accuracy, and prioritized action items linked to 7-point strategy.
 */

function renderMonthlyInsightsBrief(brief, container) {
  """
  Render a complete monthly insights brief into a container element.

  Args:
    brief: Object from revenue_presentation_engine.py with structure:
      {
        month, headline, metrics, alignment, distribution,
        distributor_health[], forecast_accuracy, action_items[]
      }
    container: DOM element or selector to render into
  """
  if (!brief) {
    console.warn('No brief data provided to renderMonthlyInsightsBrief');
    return;
  }

  const el = typeof container === 'string' ? document.querySelector(container) : container;
  if (!el) return;

  el.innerHTML = `
    <div class="monthly-insights-container">
      ${renderInsightHeader(brief)}
      <div class="insights-grid">
        ${renderHeadlineCard(brief)}
        ${renderMetricsRow(brief)}
      </div>
      <div class="insights-grid">
        ${renderAlignmentCard(brief.alignment)}
        ${renderDistributionCard(brief.distribution)}
        ${renderForecastCard(brief.forecast_accuracy)}
      </div>
      ${renderDistributorHealthSection(brief.distributor_health)}
      ${renderActionItemsSection(brief.action_items)}
    </div>
  `;

  // Attach event listeners
  attachInsightEventListeners(el);
}

function renderInsightHeader(brief) {
  const month = brief.month || '—';
  const generated = brief.generated_at ? new Date(brief.generated_at).toLocaleDateString() : '—';

  return `
    <div class="insight-header">
      <div>
        <h2>${month} — Monthly Leadership Insight</h2>
        <p class="insight-subheader">Generated ${generated} | 7-Point Revenue Uplift Strategy</p>
      </div>
    </div>
  `;
}

function renderHeadlineCard(brief) {
  const headline = brief.headline || 'Review metrics for insights';

  return `
    <div class="insight-card headline-card">
      <h3>Headline Insight</h3>
      <p class="headline-text">${headline}</p>
    </div>
  `;
}

function renderMetricsRow(brief) {
  const primary = brief.metrics.primary_lakhs || '—';
  const secondary = brief.metrics.secondary_lakhs || '—';

  return `
    <div class="insight-card metrics-card">
      <div class="metric-pair">
        <div class="metric-item">
          <span class="metric-label">Primary Sales</span>
          <span class="metric-value">₹${primary !== '—' ? (primary / 100).toFixed(2) : '—'} Cr</span>
        </div>
        <div class="metric-item">
          <span class="metric-label">Secondary Sales</span>
          <span class="metric-value">₹${secondary !== '—' ? (secondary / 100).toFixed(2) : '—'} Cr</span>
        </div>
      </div>
    </div>
  `;
}

function renderAlignmentCard(alignment) {
  if (!alignment) return '';

  const primary = alignment.primary_value || 0;
  const secondary = alignment.secondary_value || 0;
  const delta = alignment.delta_pct || 0;
  const status = alignment.health_status || 'NO_DATA';
  const interpretation = alignment.interpretation || '';

  const statusClass = {
    'HEALTHY': 'status-pass',
    'WARNING': 'status-warn',
    'CRITICAL': 'status-fail',
    'NO_DATA': 'status-unknown'
  }[status] || 'status-unknown';

  return `
    <div class="insight-card alignment-card">
      <h3>Primary vs Secondary Alignment</h3>
      <div class="alignment-chart">
        <div class="align-bar">
          <div class="align-primary" style="width: ${Math.min(primary/10, 95)}%">
            <span class="bar-label">Primary</span>
          </div>
        </div>
        <div class="align-bar">
          <div class="align-secondary" style="width: ${Math.min(secondary/10, 95)}%">
            <span class="bar-label">Secondary</span>
          </div>
        </div>
      </div>
      <div class="alignment-metrics">
        <div><strong>Delta:</strong> ${delta.toFixed(1)}%</div>
        <div><strong>Status:</strong> <span class="status-badge ${statusClass}">${status}</span></div>
      </div>
      <p class="alignment-insight">${interpretation}</p>
    </div>
  `;
}

function renderDistributionCard(distribution) {
  if (!distribution) return '';

  const ndPct = distribution.nd_pct || 0;
  const wdPct = distribution.wd_pct || 0;
  const positioning = distribution.positioning || 'UNKNOWN';
  const action = distribution.action || '';

  const positioningClass = {
    'WINNING': 'pos-winning',
    'SPREAD_THIN': 'pos-spread',
    'CONCENTRATED': 'pos-conc',
    'LOSING': 'pos-losing'
  }[positioning] || 'pos-unknown';

  return `
    <div class="insight-card distribution-card">
      <h3>ND vs WD Positioning</h3>
      <div class="nd-wd-matrix">
        <div class="matrix-metric">
          <div class="metric-label">Numeric Distribution (ND)</div>
          <div class="metric-bar">
            <div class="bar-fill" style="width: ${ndPct}%"></div>
          </div>
          <div class="metric-detail">${ndPct.toFixed(1)}% (Target: ${distribution.nd_target}%)</div>
        </div>
        <div class="matrix-metric">
          <div class="metric-label">Weighted Distribution (WD)</div>
          <div class="metric-bar">
            <div class="bar-fill wd-bar" style="width: ${wdPct}%"></div>
          </div>
          <div class="metric-detail">${wdPct.toFixed(1)}% (Target: ${distribution.wd_target}%)</div>
        </div>
      </div>
      <div class="positioning-badge ${positioningClass}">${positioning}</div>
      <p class="action-text">${action}</p>
    </div>
  `;
}

function renderForecastCard(forecast) {
  if (!forecast) return '';

  const wape = forecast.wape_pct || 0;
  const bias = forecast.bias_pct || 0;
  const accuracy = forecast.accuracy_pct || 0;
  const status = forecast.status || 'UNKNOWN';
  const interpretation = forecast.interpretation || '';

  const statusClass = status === 'ON_TRACK' ? 'status-pass' : 'status-warn';

  return `
    <div class="insight-card forecast-card">
      <h3>Forecast Accuracy</h3>
      <div class="forecast-metrics">
        <div class="forecast-item">
          <div class="forecast-value">${wape.toFixed(1)}%</div>
          <div class="forecast-label">WAPE (Target: ≤8%)</div>
        </div>
        <div class="forecast-item">
          <div class="forecast-value">${bias.toFixed(1)}%</div>
          <div class="forecast-label">Bias (Target: ±2%)</div>
        </div>
        <div class="forecast-item">
          <div class="forecast-value">${accuracy.toFixed(1)}%</div>
          <div class="forecast-label">Accuracy</div>
        </div>
      </div>
      <div class="forecast-status">
        <span class="status-badge ${statusClass}">${status}</span>
      </div>
      <p class="forecast-insight">${interpretation}</p>
    </div>
  `;
}

function renderDistributorHealthSection(distributors) {
  if (!distributors || distributors.length === 0) return '';

  const healthyCount = distributors.filter(d => d.engagement_status === 'HIGH').length;
  const atRiskCount = distributors.filter(d => d.engagement_status !== 'HIGH').length;

  return `
    <div class="distributor-health-section">
      <h3>Top Distributor Health Check</h3>
      <div class="distributor-summary">
        <div class="summary-stat healthy">
          <span class="stat-number">${healthyCount}</span>
          <span class="stat-label">Healthy</span>
        </div>
        <div class="summary-stat at-risk">
          <span class="stat-number">${atRiskCount}</span>
          <span class="stat-label">At Risk</span>
        </div>
      </div>

      <div class="distributor-table-wrapper">
        <table class="distributor-table">
          <thead>
            <tr>
              <th>Distributor</th>
              <th>Monthly Avg (₹L)</th>
              <th>Rotation (days)</th>
              <th>Annual Turns</th>
              <th>Est. Earnings (₹L)</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            ${distributors.map(d => `
              <tr class="row-${d.engagement_status.toLowerCase()}">
                <td><strong>${d.distributor}</strong></td>
                <td>${d.monthly_purchase_lakhs.toFixed(1)}</td>
                <td>${d.rotation_days}</td>
                <td>${d.annual_turns.toFixed(1)}x</td>
                <td>₹${d.est_annual_earnings_lakhs.toFixed(2)}L/yr</td>
                <td><span class="status-badge status-${d.engagement_status.toLowerCase()}">${d.engagement_status}</span></td>
                <td>${d.action_required ? '⚠️ Action' : '✓'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    </div>
  `;
}

function renderActionItemsSection(actions) {
  if (!actions || actions.length === 0) return '';

  return `
    <div class="action-items-section">
      <h3>Prioritized Action Items (7-Point Revenue Uplift Strategy)</h3>
      <div class="actions-container">
        ${actions.map((action, idx) => `
          <div class="action-card priority-${action.priority.toLowerCase()}">
            <div class="action-header">
              <span class="action-priority">${action.priority}</span>
              <h4>${action.action}</h4>
            </div>
            <p class="action-detail">${action.detail}</p>
            <div class="action-metadata">
              <div class="action-meta-item">
                <span class="meta-label">Expected Impact:</span>
                <span class="meta-value">${action.expected_impact}</span>
              </div>
              <div class="action-meta-item">
                <span class="meta-label">Owner:</span>
                <span class="meta-value">${action.owner}</span>
              </div>
              <div class="action-meta-item">
                <span class="meta-label">Timeline:</span>
                <span class="meta-value">${action.timeline}</span>
              </div>
            </div>
            <div class="action-footer">
              <span class="initiative-tag">${action.initiative}</span>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function attachInsightEventListeners(container) {
  // Add click handlers for expandable sections, drills, etc.
  // Placeholder for future interactivity
  container.querySelectorAll('.action-card').forEach(card => {
    card.addEventListener('click', function() {
      this.classList.toggle('expanded');
    });
  });
}

/**
 * Export monthly insight brief as printable/downloadable HTML
 */
function exportMonthlyInsightPDF(briefData) {
  // Uses jsPDF if available, otherwise generates printable HTML
  const title = `MT Dashboard — ${briefData.month} Monthly Insights`;
  const html = document.querySelector('.monthly-insights-container').innerHTML;

  // Simple print approach
  const printWindow = window.open('', '', 'height=600,width=1000');
  printWindow.document.write(`
    <html>
      <head>
        <title>${title}</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; }
          h2 { color: #1f7a63; }
          .card { border: 1px solid #ddd; padding: 15px; margin: 10px 0; }
        </style>
      </head>
      <body>
        <h1>${title}</h1>
        ${html}
      </body>
    </html>
  `);
  printWindow.document.close();
  printWindow.print();
}
