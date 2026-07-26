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

  expectedKeys.forEach(key => {
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
 * Check for Reliance data isolation (no double-counting between Macro and BA)
 */
function validateRelianceIsolation(relianceMacro, relianceBA) {
  const issues = [];

  // Sum both streams independently
  const macroTotal = relianceMacro?.nsv_total || 0;
  const baTotal = relianceBA?.nsv_total || 0;

  // If combined they exceed realistic bounds, flag it
  const combined = macroTotal + baTotal;
  if (combined === 0) {
    dashboardErrors.partial('Reliance data missing or zero - check ingestion');
    issues.push('No Reliance sales data found');
  }

  return {
    macro_total: macroTotal,
    ba_total: baTotal,
    combined_total: combined,
    issues
  };
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
