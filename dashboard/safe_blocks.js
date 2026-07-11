// Safe-to-build dashboard blocks for MT Leadership Dashboard
// Extends the existing dashboard with QC, Reconciliation, and Interim Offtake P&L (MRP basis only)
// Blocks all NSV-based, state-level, and BA profitability measures
// Marks June'26 as Partial in all outputs
// Generated 2026-07-11

const SAFE_BLOCKS_VERSION = "2026-07-11";

// Water markers for interim/pending blocks
const watermark_nsv_pending = '<span style="color:#C77D17;font-weight:700;font-size:12px">⚠ NSV unit pending</span>';
const watermark_june_partial = '<span style="color:#C77D17;font-weight:700;font-size:12px">⚠ Jun\'26 Partial</span>';
const watermark_interim_mrp = '<span style="color:#C77D17;font-weight:700;font-size:12px">Interim: MRP basis only</span>';

// Format rupees from Lakh (as MRP Sales Value is in rupees, not stored as Lakh in reconciliation)
// Reconciliation CSV has MRP in rupees; convert to Crore for display
const mrpCr = v => {
  if (v == null) return '–';
  const av = Math.abs(v);
  return av < 1e7 ? '₹' + (v / 1e5).toLocaleString('en-IN', { maximumFractionDigits: 1 }) + ' L'
    : '₹' + (v / 1e7).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' Cr';
};

// Build QC & Reconciliation page (safe block)
function buildQcReconciliation() {
  if (!window.QC) { console.warn('QC data not loaded'); return; }
  const s = document.getElementById('tab-qc');
  const recData = QC.reconciliation || [];

  // Monthly table
  const monthRows = recData.map(r => {
    const partialBadge = r.is_partial ? ' <span class="pill r">PARTIAL</span>' : '';
    return `<tr><td>${r.month}${partialBadge}</td>
      <td style="text-align:right">${r.files}</td>
      <td style="text-align:right">${num(r.rows)}</td>
      <td style="text-align:right">${mrpCr(r.mrp_L)}</td>
      <td style="text-align:right">${qtyFmt(r.qty)}</td>
      <td style="text-align:right" class="pill r">${r.neg_nsv_rows} rows</td></tr>`;
  }).join('');

  // Grand totals
  const gt = QC.grand_totals || {};

  // Chain coverage table
  const chainRows = (QC.chain_coverage || []).map(c => {
    const note = c.note ? ` <span style="font-size:11px;color:#6b7682">(${c.note})</span>` : '';
    return `<tr><td>${c.chain}${note}</td>
      <td style="text-align:right">${num(c.rows)}</td>
      <td style="text-align:right">${mrpCr(c.mrp_L)}</td></tr>`;
  }).join('');

  // Blocked measures
  const blockedList = (QC.blocked_measures || []).map(m => `<li>${m}</li>`).join('');
  const safeList = (QC.safe_measures || []).map(m => `<li>${m}</li>`).join('');

  s.innerHTML = `
    <h2 class="sec">QC & Reconciliation</h2>
    <p class="lead">Monthly data quality and coverage report. ${watermark_june_partial}</p>
    <div class="fynote">
      <b>June'26 is PARTIAL:</b> 78,111 rows from 16 chains only (some accounts pending).
      Negative NSV rows (12,705 across all months) are valid returns/credit notes, not errors.
      No deduplication of More Retail duplicates has been applied.
    </div>

    <h3 style="font-size:15px;margin:18px 0 8px">Monthly Reconciliation</h3>
    ${card('Monthly Row Counts, MRP Sales Value, and Quantity', 'Includes negative-value returns (shown as row count in rightmost column).',
      `<div class="tablewrap"><table><thead><tr>
        <th>Month</th><th>Files/Chains</th><th>Rows</th><th>MRP Sales Value</th><th>Sales Qty</th><th>Negative-Value Rows</th>
        </tr></thead><tbody>${monthRows}</tbody></table></div>`)}

    ${card('Grand Totals (Apr\'24 – Jun\'26)', '',
      `<div class="grid g3" style="grid-template-columns:1fr 1fr 1fr;gap:12px;margin:0">
        ${kpi('Total Rows', num(gt.rows), '4.21M rows, 582 files')}
        ${kpi('Total MRP Sales Value', mrpCr(gt.mrp_L), 'verified basis')}
        ${kpi('Total Sales Qty', qtyFmt(gt.qty), 'units')}
      </div>`)}

    <h3 style="font-size:15px;margin:18px 0 8px">Chain Coverage & Issues</h3>
    ${card('Chains & Row Volumes', 'Includes notes on variants and flagged chains.',
      `<div class="tablewrap"><table><thead><tr>
        <th>Chain</th><th>Rows</th><th>MRP Sales Value</th>
        </tr></thead><tbody>${chainRows}</tbody></table></div>`)}

    <h3 style="font-size:15px;margin:18px 0 8px">Blocked Measures (Awaiting Business Approval)</h3>
    <div class="card">
      <h3>Measures that CANNOT be published until business decisions clear</h3>
      <ul style="font-size:13px;line-height:1.6;color:#374151">${blockedList}</ul>
    </div>

    <h3 style="font-size:15px;margin:18px 0 8px">Safe to Publish (No Business Gates)</h3>
    <div class="card" style="border-left:4px solid #1E8E3E">
      <h3>✓ Measures that CAN be published immediately</h3>
      <ul style="font-size:13px;line-height:1.6;color:#374151">${safeList}</ul>
    </div>

    <h3 style="font-size:15px;margin:18px 0 8px">Pending Decisions</h3>
    <div class="ins" style="grid-template-columns:repeat(auto-fit,minmax(300px,1fr))">
      <div class="icard watch">
        <div class="tag">Decision 1</div>
        <h4>NSV Unit Validation (HIGHEST PRIORITY)</h4>
        <p>Confirm unit multiplier by anchoring to one known-good month (₹Cr). Blocks all P&L and profitability.</p>
      </div>
      <div class="icard watch">
        <div class="tag">Decision 2</div>
        <h4>More Retail Duplicates (₹1.36 Cr impact)</h4>
        <p>13,661 exact-dup rows (33.4%). Choose: de-dupe in Power Query, fix at source, or footnote as inflated.</p>
      </div>
      <div class="icard watch">
        <div class="tag">Decision 3</div>
        <h4>Brand Counter Classification</h4>
        <p>549,617 rows labeled "Brand Counter." Is it the BA channel, or a store type? Requires business ruling.</p>
      </div>
    </div>
  `;
}

// Build Interim Offtake P&L (MRP basis only, NSV pending)
function buildInterimOfftakePnl() {
  if (!window.DASH || !DASH.offtake) {
    const s = document.getElementById('tab-interim-pnl');
    s.innerHTML = '<h2 class="sec">Interim Offtake P&L (MRP Basis)</h2><p class="lead">Blocked: No offtake source data available in current data.js</p>';
    return;
  }

  const s = document.getElementById('tab-interim-pnl');
  const o = DASH.offtake;

  // Placeholder: this would be populated from offtake data in a full build
  // For now, show the note and structure
  s.innerHTML = `
    <h2 class="sec">Interim Offtake P&L (MRP Sales Value Basis)</h2>
    <p class="lead">${watermark_interim_mrp} · ${watermark_nsv_pending} · ${watermark_june_partial}</p>
    <div class="fynote" style="background:#fce8e6;border-color:#f0d8a8">
      <b>⚠ Interim Only:</b> This page uses <b>MRP Sales Value (verified, rupees)</b> as the value basis.
      Net Sales Value (NSV) is unit-unvalidated; all NSV-based measures (CM2, Margin, Profitability, BA reporting)
      remain blocked until finance confirms the NSV unit multiplier. June'26 is partial.
    </div>

    <h3 style="font-size:15px;margin:18px 0 8px">MRP Sales Value Performance</h3>
    ${card('Total Offtake (MRP Sales Value Basis)', 'All chains, all zones, MRP verified.',
      `<div class="grid g3" style="grid-template-columns:1fr 1fr 1fr">
        ${kpi('Offtake (MRP)', mrpCr(14434532270.36), 'Apr\'24–Jun\'26')}
        ${kpi('Average MRP/Month', mrpCr(14434532270.36 / 27), 'monthly')}
        ${kpi('Jun\'26 Partial', mrpCr(691025724.3), 'partial month')}
      </div>`)}

    <div class="methodbox">
      <summary>Why NSV-based measures are blocked</summary>
      <div class="note">
        <b>NSV Grand Total = 271,801</b> (unitless) vs <b>MRP Sales Value = ₹1,443.45 Cr</b> —
        these cannot both be in rupees. NSV unit is ambiguous (₹/unit/lac?).
        Until business provides a reference anchor (one month's signed-off NSV in ₹Cr),
        any ₹ conversion of NSV is mathematically incorrect.<br><br>
        <b>Interim rule:</b> Use MRP Sales Value for headline reporting.
        Render NSV raw/unconverted with "unit unvalidated" flag. Keep negative NSV as valid returns.
      </div>
    </div>

    <h3 style="font-size:15px;margin:18px 0 8px">NOT Available (Blocked)</h3>
    <div class="card" style="border-left:4px solid #C0392B">
      <ul style="font-size:13px;line-height:1.6;color:#374151">
        <li><b>Net Sales Value (NSV)</b> — unit unvalidated</li>
        <li><b>Gross Margin %</b> — uses NSV (unvalidated)</li>
        <li><b>Contribution %</b> — uses NSV (unvalidated)</li>
        <li><b>BA Profitability</b> — depends on NSV + BA Headcount (business input pending)</li>
        <li><b>P&L Summary</b> — all profitability blocked on NSV unit</li>
        <li><b>MoM/YoY % Growth (NSV basis)</b> — uses NSV (unvalidated)</li>
      </ul>
    </div>
  `;
}

// Enhance the existing buildOverview to add June'26 partial flag
const originalBuildOverview = window.BUILD ? window.BUILD.overview : null;
if (originalBuildOverview && typeof originalBuildOverview === 'function') {
  const enhancedBuildOverview = function() {
    originalBuildOverview.call(this);
    // Add June'26 partial flag to the overview section
    const s = document.getElementById('tab-overview');
    if (s) {
      const banner = document.createElement('div');
      banner.className = 'fynote';
      banner.style.cssText = 'background:#fff7e6;border-color:#f0d8a8;margin:0 0 14px';
      banner.innerHTML = `<b>📌 June'26 is PARTIAL:</b> Only 78,111 rows from 16 chains.
        Some accounts pending. All totals and trends include this partial month.`;
      s.insertBefore(banner, s.firstChild);
    }
  };
  if (window.BUILD) window.BUILD.overview = enhancedBuildOverview;
}

// Register the new builders in the BUILD map (BUILD is now defined by inline script)
if (window.BUILD) {
  window.BUILD.qc = buildQcReconciliation;
  window.BUILD['interim-pnl'] = buildInterimOfftakePnl;
  console.log('Safe blocks registered (' + SAFE_BLOCKS_VERSION + ')');
} else {
  console.warn('BUILD map not yet defined when safe_blocks.js loaded');
}

console.log('Safe blocks loaded (' + SAFE_BLOCKS_VERSION + ')');
