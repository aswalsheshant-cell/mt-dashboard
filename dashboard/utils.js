/**
 * MT Dashboard Utilities: Error Intelligence & Currency Formatting
 * Provides root-cause analysis across 4 layers and unified currency rendering
 */

// ============================================================================
// ERROR INTELLIGENCE FRAMEWORK
// ============================================================================

const ErrorLayers = {
  INGESTION: 'INGESTION_LAYER',
  TRANSFORMATION: 'TRANSFORMATION_LAYER',
  STATE: 'STATE_LAYER',
  PRESENTATION: 'PRESENTATION_LAYER'
};

class ErrorIntelligence {
  constructor() {
    this.errors = [];
    this.warnings = [];
    this.status = 'PASS'; // PASS | WARN | FAIL | BLOCKED
  }

  ingest(error, layerType, evidence = {}) {
    const entry = {
      timestamp: new Date().toISOString(),
      layer: layerType,
      message: error,
      evidence: {
        raw_input: evidence.raw_input || null,
        active_filters: evidence.active_filters || [],
        stack: evidence.stack || null,
        affected_record_count: evidence.affected_record_count || 0,
        data_slice: evidence.data_slice || null
      },
      severity: evidence.severity || 'ERROR'
    };

    if (entry.severity === 'ERROR') {
      this.errors.push(entry);
      this.status = 'FAIL';
    } else {
      this.warnings.push(entry);
      if (this.status !== 'FAIL') this.status = 'WARN';
    }

    return entry;
  }

  blocked(missing_dependency, failing_layer, root_cause, required_action) {
    this.status = 'BLOCKED';
    const blocked_entry = {
      status: 'BLOCKED',
      missing_dependency,
      failing_layer,
      root_cause,
      required_action,
      timestamp: new Date().toISOString()
    };
    this.errors.push(blocked_entry);
    return blocked_entry;
  }

  partial(description) {
    if (this.status !== 'FAIL' && this.status !== 'BLOCKED') {
      this.status = 'PARTIAL';
    }
    this.ingest(description, ErrorLayers.INGESTION, { severity: 'WARN' });
  }

  getReport() {
    return {
      status: this.status,
      error_count: this.errors.length,
      warning_count: this.warnings.length,
      errors: this.errors,
      warnings: this.warnings,
      summary: this.getSummary()
    };
  }

  getSummary() {
    const layers = {};
    this.errors.forEach(e => {
      if (!layers[e.layer]) layers[e.layer] = [];
      layers[e.layer].push(e.message);
    });
    return layers;
  }

  logToConsole() {
    if (this.errors.length > 0) {
      console.error('=== ERROR INTELLIGENCE REPORT ===');
      console.error('Status:', this.status);
      this.errors.forEach(e => {
        console.error(`[${e.layer}] ${e.message}`, e.evidence);
      });
    }
    if (this.warnings.length > 0) {
      console.warn('=== WARNINGS ===');
      this.warnings.forEach(w => {
        console.warn(`[${w.layer}] ${w.message}`);
      });
    }
  }
}

// Singleton instance
const dashboardErrors = new ErrorIntelligence();

// ============================================================================
// UNIFIED CURRENCY FORMATTING
// ============================================================================

const CurrencyUnits = {
  RUPEES: 'rupees',
  LAKHS: 'lakhs',
  CRORES: 'crores'
};

function formatCurrency(value, targetUnit = CurrencyUnits.CRORES, decimals = 2) {
  // Input safety: handle null, undefined, NaN
  if (value === null || value === undefined || isNaN(value)) {
    return '—';
  }

  const num = parseFloat(value);

  // Render based on target unit
  switch (targetUnit) {
    case CurrencyUnits.RUPEES:
      return `₹${(num * 100000).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

    case CurrencyUnits.LAKHS:
      return `${num.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} L`;

    case CurrencyUnits.CRORES:
    default:
      const crores = num / 100;
      return `₹${crores.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })} Cr`;
  }
}

// Quick formatters for common use cases
const fmt = {
  cr: (val) => formatCurrency(val, CurrencyUnits.CRORES, 2),
  l: (val) => formatCurrency(val, CurrencyUnits.LAKHS, 2),
  pct: (val) => {
    if (val === null || val === undefined || isNaN(val)) return '—';
    return parseFloat(val).toFixed(2) + '%';
  },
  int: (val) => {
    if (val === null || val === undefined || isNaN(val)) return '—';
    return Math.round(val).toLocaleString('en-IN');
  }
};

// ============================================================================
// DATA VALIDATION HELPERS
// ============================================================================

/**
 * Validate that a dataset has expected structure and no critical gaps
 */
function validateDataset(data, expectedKeys) {
  const errors = [];

  if (!data) {
    dashboardErrors.ingest('Dataset is null or undefined', ErrorLayers.INGESTION);
    return { valid: false, errors };
  }

  (expectedKeys || []).forEach(key => {
    if (!(key in data)) {
      dashboardErrors.ingest(`Missing expected key: ${key}`, ErrorLayers.INGESTION, {
        affected_record_count: 1
      });
      errors.push(`Missing: ${key}`);
    }
  });

  return {
    valid: errors.length === 0,
    errors
  };
}

/**
 * Grain coverage check.
 *
 * Some accounts and some vendor export formats report offtake at a national or
 * article-only grain with no store/state geography (Jun-26 arrives tagged
 * "Pan India"). That is a KNOWN FORMAT LIMITATION, not a data defect, so it
 * must NOT raise an INGESTION/TRANSFORMATION error or mark the load BLOCKED --
 * doing so would train readers to ignore the badge. It is reported as WARN
 * with an explicit note, and the value is asserted to still be present in the
 * totals so a degraded grain never becomes lost money.
 *
 * Returns { status, months, note, issues }.
 */
const GRAIN_NOTE =
  'Offtake ingested at Article level; Store/State granularity N/A by vendor format.';

function validateGrainCoverage(dash) {
  const D = dash || (typeof window !== 'undefined' ? window.DASH : null);
  const issues = [], months = {};
  const out = { status: 'PASS', months, note: GRAIN_NOTE, issues };
  const off = D && D.offtake;
  if (!off) {
    dashboardErrors.ingest('No offtake block to check grain coverage against',
      ErrorLayers.INGESTION, { severity: 'WARN' });
    issues.push('offtake block absent');
    out.status = 'WARN';
    return out;
  }

  const cov = off.grain_coverage || {};
  let degraded = 0, degradedValue = 0;
  Object.entries(cov).forEach(([mo, c]) => {
    months[mo] = { value: c.value, geo: !!c.geo, sources: c.sources || [] };
    if (!c.geo) {
      degraded++;
      degradedValue += c.value || 0;
      // WARN, deliberately not an error: the value is present and correct,
      // only its geographic split is unavailable.
      dashboardErrors.ingest(`${mo}: ${GRAIN_NOTE}`, ErrorLayers.INGESTION, {
        severity: 'WARN', data_slice: (c.sources || []).join(','),
        raw_input: { month: mo, value: c.value }
      });
      issues.push(`${mo} national-grain only (${c.value} L)`);
    }
  });
  if (degraded) out.status = 'WARN';
  out.degraded_months = degraded;
  out.degraded_value = Number(degradedValue.toFixed(2));

  // The whole point of the N/A bucket: degraded grain must not lose value.
  // Assert every FY's breakdowns still reconcile to its total.
  const tags = off.fy_tags || [];
  out.reconciliation = {};
  tags.forEach(fy => {
    const total = off['total_' + fy];
    if (total == null) return;
    const sum = arr => (arr || []).reduce((a, r) => a + (r[fy] || 0), 0);
    const chain = sum(off.by_chain), zone = sum(off.by_zone), state = sum(off.by_state);
    const worst = Math.max(Math.abs(total - chain), Math.abs(total - zone),
      Math.abs(total - state));
    out.reconciliation[fy] = {
      total, by_chain: Number(chain.toFixed(2)), by_zone: Number(zone.toFixed(2)),
      by_state: Number(state.toFixed(2)), worst_gap: Number(worst.toFixed(2))
    };
    // Tolerance is RELATIVE (0.1% of the FY total, floored at 0.5 L). An
    // absolute threshold mis-fires here: the pre-aggregated FY25/FY26 pivot is
    // rounded to whole Lakh at source, so it carries a standing 3-5 L zone/state
    // gap on 21,840-31,082 L (~0.02%) that no pipeline change can remove.
    // Failing on that would train readers to ignore the badge. Real defects are
    // orders of magnitude larger -- the Jun-26 drop was 36% of FY27, the
    // by_state double-count 3.7% -- so 0.1% separates them cleanly.
    const tol = Math.max(0.5, Math.abs(total) * 0.001);
    const pct = total ? (worst / Math.abs(total)) * 100 : 0;
    out.reconciliation[fy].tolerance = Number(tol.toFixed(2));
    out.reconciliation[fy].gap_pct = Number(pct.toFixed(4));
    if (worst > tol) {
      dashboardErrors.ingest(
        `${fy.toUpperCase()} breakdowns do not reconcile to total (worst gap ` +
        `${worst.toFixed(2)} L, ${pct.toFixed(2)}%) — a dimension is dropping ` +
        `or double-counting value.`,
        ErrorLayers.TRANSFORMATION,
        { data_slice: `offtake.total_${fy}`, raw_input: out.reconciliation[fy] });
      issues.push(`${fy} reconciliation gap ${worst.toFixed(2)} L (${pct.toFixed(2)}%)`);
      out.status = 'FAIL';
    } else if (worst > 0.5) {
      // visible, but correctly framed as source rounding rather than a defect
      issues.push(`${fy} residual ${worst.toFixed(2)} L (${pct.toFixed(3)}%, ` +
        `within ${tol.toFixed(2)} L tolerance — source rounded to whole Lakh)`);
    }
  });
  return out;
}

/**
 * Assert that Reliance BA-counter sell-out is NOT inside the main Offtake
 * aggregates. Reads window.DASH directly so it can be run from the console
 * with no arguments: validateRelianceIsolation().
 *
 * The guard: for every FY the isolation covers,
 *     offtake.by_chain[Reliance].fyNN  ===  combined_before - ba_removed
 * Any drift means something re-added the BA stream to the macro total, and
 * that is reported as a TRANSFORMATION_LAYER error (INGESTION_LAYER when the
 * BA block itself never arrived).
 */
function validateRelianceIsolation(dash) {
  const D = dash || (typeof window !== 'undefined' ? window.DASH : null);
  const issues = [], TOL = 0.01;
  const out = { status: 'PASS', by_fy: {}, issues, ba_total: 0, macro_total: 0 };

  const ba = D && D.reliance_ba;
  if (!ba) {
    dashboardErrors.ingest(
      'Reliance BA block absent — BA counters cannot be proven excluded from Offtake',
      ErrorLayers.INGESTION, { severity: 'WARN' });
    issues.push('No reliance_ba block; isolation unverified');
    out.status = 'BLOCKED';
    return out;
  }

  const row = ((D.offtake && D.offtake.by_chain) || [])
    .find(c => c.name === ba.chain);
  if (!row) {
    dashboardErrors.ingest(`Offtake has no "${ba.chain}" chain row to validate`,
      ErrorLayers.STATE, { severity: 'WARN' });
    issues.push('Reliance row missing from offtake.by_chain');
    out.status = 'WARN';
    return out;
  }

  Object.entries(ba.isolation_audit || {}).forEach(([fy, a]) => {
    const expected = (a.combined_before || 0) - (a.ba_removed || 0);
    const actual = row[fy];
    const drift = Math.abs((actual || 0) - expected);
    const ok = drift <= TOL;
    out.by_fy[fy] = {
      combined_before: a.combined_before, ba_removed: a.ba_removed,
      expected_macro: Number(expected.toFixed(2)), actual_macro: actual,
      drift: Number(drift.toFixed(4)), passes: ok
    };
    out.ba_total += a.ba_removed || 0;
    out.macro_total += actual || 0;
    if (!ok) {
      dashboardErrors.ingest(
        `Reliance ${fy.toUpperCase()} Offtake includes BA counter sales — ` +
        `expected macro ${expected.toFixed(2)} L, found ${actual} L ` +
        `(drift ${drift.toFixed(2)} L). BA must live only on the Reliance BA tab.`,
        ErrorLayers.TRANSFORMATION,
        { affected_record_count: 1, data_slice: `offtake.by_chain[${ba.chain}].${fy}`,
          raw_input: a });
      issues.push(`${fy}: BA leaked into Offtake total (drift ${drift.toFixed(2)} L)`);
      out.status = 'FAIL';
    }
  });

  // months the source could not split are honest gaps, not failures
  (ba.months_not_isolable || []).forEach(m => {
    dashboardErrors.ingest(
      `${m.month}: ${m.reason} — ${m.reliance_nsv} L remains un-isolated in macro`,
      ErrorLayers.INGESTION, { severity: 'WARN', data_slice: m.file });
    issues.push(`${m.month} not isolable (${m.reliance_nsv} L)`);
    if (out.status === 'PASS') out.status = 'PARTIAL';
  });

  out.ba_total = Number(out.ba_total.toFixed(2));
  out.macro_total = Number(out.macro_total.toFixed(2));
  out.combined_total = Number((out.ba_total + out.macro_total).toFixed(2));
  return out;
}

/**
 * Verify that all expected months in a fiscal period are present
 */
function validateFiscalPeriodCoverage(data, fy, expectedMonths) {
  const coverage = {
    fy,
    expected_months: expectedMonths,
    found_months: [],
    missing_months: [],
    complete: false
  };

  expectedMonths.forEach(month => {
    const monthKey = `${fy}_${month}`;
    // Check if month exists in data (implementation depends on data structure)
    if (data && data[monthKey]) {
      coverage.found_months.push(month);
    } else {
      coverage.missing_months.push(month);
    }
  });

  coverage.complete = coverage.missing_months.length === 0;

  if (coverage.missing_months.length > 0) {
    dashboardErrors.partial(
      `Missing months in FY${fy}: ${coverage.missing_months.join(', ')}`,
    );
  }

  return coverage;
}

// ============================================================================
// STATUS BADGE RENDERING
// ============================================================================

/**
 * Generate HTML for status badge
 * @param status - one of: FINAL, PARTIAL, PROVISIONAL, APPROVAL_PENDING, PASS, WARN, FAIL, BLOCKED
 */
function renderStatusBadge(status) {
  const badgeStyles = {
    FINAL: { bg: '#e6f4ea', color: '#1e8e3e', text: '✓ FINAL' },
    PARTIAL: { bg: '#fff7e6', color: '#c77d17', text: '⚠ PARTIAL' },
    PROVISIONAL: { bg: '#fce8e6', color: '#c0392b', text: '◆ PROVISIONAL' },
    APPROVAL_PENDING: { bg: '#e8f0fe', color: '#1f6db5', text: '⏳ APPROVAL PENDING' },
    PASS: { bg: '#e6f4ea', color: '#1e8e3e', text: '✓ PASS' },
    WARN: { bg: '#fff7e6', color: '#c77d17', text: '⚠ WARN' },
    FAIL: { bg: '#fce8e6', color: '#c0392b', text: '✗ FAIL' },
    BLOCKED: { bg: '#f0f0f0', color: '#5a5a5a', text: '⊘ BLOCKED' }
  };

  const style = badgeStyles[status] || badgeStyles.PASS;
  return `<span style="display:inline-block;background:${style.bg};color:${style.color};padding:3px 9px;border-radius:4px;font-size:11px;font-weight:700;margin-left:8px">${style.text}</span>`;
}

// ============================================================================
// RECONCILIATION HELPERS
// ============================================================================

/**
 * Reconcile two comparable datasets (e.g., Primary vs Offtake)
 */
function reconcile(primary, offtake, tolerance_pct = 0.05) {
  const variance = Math.abs(primary - offtake) / Math.max(primary, offtake, 1) * 100;
  return {
    primary,
    offtake,
    variance_pct: variance.toFixed(3),
    passes_tolerance: variance <= tolerance_pct,
    status: variance <= tolerance_pct ? 'PASS' : 'WARN'
  };
}

// Export for use in HTML
window.ErrorIntelligence = ErrorIntelligence;
window.dashboardErrors = dashboardErrors;
window.formatCurrency = formatCurrency;
window.fmt = fmt;
window.validateDataset = validateDataset;
window.validateRelianceIsolation = validateRelianceIsolation;
window.validateFiscalPeriodCoverage = validateFiscalPeriodCoverage;
window.renderStatusBadge = renderStatusBadge;
window.reconcile = reconcile;
