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

  // ---- per-record grain check, governed by CHAIN_GRAIN_CONFIG ----
  // A missing Site Code / State is only an INGESTION error when that chain is
  // EXPECTED to carry it. For a declared macro-reporting chain it is the vendor
  // format, so it is filled with the declared fallback and reported as WARN --
  // never BLOCKED, and never as an error that would train readers to ignore
  // the badge.
  const recs = Array.isArray(data) ? data
    : (Array.isArray(data.detail_records) ? data.detail_records : null);
  const grain = { checked: 0, exempt: 0, filled: 0, violations: [] };
  if (recs) {
    // Is this dataset store-grained AT ALL? detail_records is article x chain x
    // state primary — it carries no store identifier for ANY chain, by design.
    // Without this guard every Group C chain (Dmart, Apollo, H&G, ...) gets
    // flagged for "missing" a column the source never had, which is 17 bogus
    // errors and exactly the noise that makes a status badge worth ignoring.
    // A grain expectation only applies to a feed that actually carries it.
    // Must ignore the synthetic 'N/A' this module itself writes at load time --
    // counting our own fallback as evidence of store grain would make the
    // detector always say "yes" and re-introduce the false positives.
    const realStore = r => {
      const v = r.SiteCode || r.siteCode || r.StoreName || r.storeName;
      return v && v !== NA_FIELD;
    };
    const storeGrained = recs.some(realStore);
    grain.store_grained_source = storeGrained;
    if (!storeGrained) {
      grain.note = 'Dataset carries no store identifier for any chain ' +
        '(article-level source) — per-chain store checks skipped.';
    }
    const missByChain = new Map();
    recs.forEach(r => {
      const chain = r.Chain !== undefined ? r.Chain : r.chain;
      const noStore = storeGrained && !realStore(r);
      const noGeo = !(r.State || r.state);
      if (!noStore && !noGeo) { grain.checked++; return; }
      grain.checked++;
      const exemptStore = grainAllowsMissingStore(chain);
      const exemptGeo = grainAllowsMissingGeo(chain);
      if ((!noStore || exemptStore) && (!noGeo || exemptGeo)) {
        grain.exempt++;
        normalizeGrainRecord(r);
        grain.filled++;
        return;
      }
      const k = String(chain);
      const m = missByChain.get(k) || { chain: k, store: 0, geo: 0 };
      if (noStore && !exemptStore) m.store++;
      if (noGeo && !exemptGeo) m.geo++;
      missByChain.set(k, m);
    });
    missByChain.forEach(m => {
      if (!m.store && !m.geo) return;
      grain.violations.push(m);
      // a chain NOT declared macro-reporting really is missing something
      dashboardErrors.ingest(
        `${m.chain}: ${m.store ? m.store + ' record(s) without a store identifier' : ''}` +
        `${m.store && m.geo ? ', ' : ''}${m.geo ? m.geo + ' record(s) without State' : ''}` +
        ` — not declared macro-reporting in CHAIN_GRAIN_CONFIG.`,
        ErrorLayers.INGESTION,
        { severity: 'WARN', affected_record_count: m.store + m.geo, data_slice: m.chain });
      errors.push(`${m.chain}: undeclared missing grain`);
    });
    if (grain.exempt) {
      dashboardErrors.ingest(
        `${grain.exempt} record(s) across declared macro-reporting chains: ` + GRAIN_NOTE,
        ErrorLayers.INGESTION, { severity: 'WARN', affected_record_count: grain.exempt });
    }
  }

  return {
    valid: errors.length === 0,
    status: errors.length ? 'WARN' : 'PASS',
    note: GRAIN_NOTE,
    grain,
    errors
  };
}

/* ===================================================================
 * PERMANENT CHAIN GRAIN MASTER
 *
 * Declares, per chain, the FINEST grain that chain's vendor format is expected
 * to deliver. This is a POLICY table, not an assertion about today's file: it
 * says "a missing Site Code here is the format, not a defect", so ingestion
 * must fall back rather than raise INGESTION/TRANSFORMATION errors or BLOCK.
 *
 * Matching is alias-tolerant on purpose. Records carry CANONICAL chain names
 * (canon_chain in build_dashboard_data.py), and five of the names below change
 * under canonicalisation -- "Beauty & Nutrie"->"B&N", "Sancus(Rmt)"->
 * "RMT-Sancus", "Reliance"->"Reliance Retail", "Ratanadeep"->"Ratnadeep",
 * "FSN"/"Nykaa"->"Nykaa (FSN)". A plain Array.includes(record.chain) would
 * therefore match NONE of them and the whole table would be a silent no-op, so
 * every lookup goes through chainKey() (case/punctuation-insensitive) and both
 * spellings are listed.
 * =================================================================== */
const CHAIN_GRAIN_CONFIG = {
  // Reports at Pan-India / Article level only: no Zone, State, or store.
  PAN_INDIA_ONLY: ['FSN', 'Nykaa', 'Nykaa (FSN)', 'Nykaa E-Retail Limited'],
  // Reports to Zone/State but never to an individual store.
  ZONE_STATE_ONLY: [
    'Arambagh',
    'Beauty & Nutrie', 'Beauty & Nutrition', 'B&N',
    'Frankross', 'Frank Ross',
    'More Retail', 'MoreRetail',
    'National Mart',
    'Ratanadeep', 'Ratnadeep',
    'Reliance', 'Reliance Retail',          // MACRO offtake stream only
    'Sancus(Rmt)', 'Sancus Retail', 'RMT-Sancus',
    'Sumo Save', 'SumoSave',
    'V-Mart', 'V-Mart Retail', 'V-Mart Retail Limited'
  ],
  // Everything else (Dmart, Apollo, Wellness Forever, H&G, Metro C&C, Lulu,
  // Reliance BA Counters, ...) is expected to report at store level.
  // Reliance BA is deliberately its OWN entry: the BA counter stream reports at
  // ~320 real site codes even though the Reliance macro stream above does not.
  FULL_STORE_LEVEL_EXCEPTIONS: ['Reliance BA', 'Reliance BA Counters', 'Brand Counter']
};
if (typeof window !== 'undefined') window.CHAIN_GRAIN_CONFIG = CHAIN_GRAIN_CONFIG;

const NA_FIELD = 'N/A';
const PAN_INDIA = 'Pan India';

/** Case/punctuation-insensitive chain key, so "Sancus(Rmt)" === "RMT-Sancus"
 *  never silently fails to match. */
function chainKey(name) {
  return String(name == null ? '' : name).toLowerCase().replace(/[^a-z0-9]/g, '');
}
const _GRAIN_INDEX = (() => {
  const idx = new Map();
  Object.entries(CHAIN_GRAIN_CONFIG).forEach(([group, names]) =>
    names.forEach(n => idx.set(chainKey(n), group)));
  return idx;
})();

/** 'PAN_INDIA_ONLY' | 'ZONE_STATE_ONLY' | 'FULL_STORE_LEVEL_EXCEPTIONS' | 'FULL' */
function chainGrainGroup(chain) {
  return _GRAIN_INDEX.get(chainKey(chain)) || 'FULL';
}
/** Is a missing store/site identifier EXPECTED for this chain? */
function grainAllowsMissingStore(chain) {
  const g = chainGrainGroup(chain);
  return g === 'PAN_INDIA_ONLY' || g === 'ZONE_STATE_ONLY';
}
/** Is a missing Zone/State EXPECTED for this chain? */
function grainAllowsMissingGeo(chain) {
  return chainGrainGroup(chain) === 'PAN_INDIA_ONLY';
}

/**
 * Apply the declared fallback to ONE record, in place.
 * Only ever FILLS blanks -- never overwrites a value the source provided. That
 * distinction matters: Nykaa currently ships 17 states in this dataset, so the
 * Pan-India default must not flatten real geography if the format improves.
 * Returns the record for chaining.
 */
function normalizeGrainRecord(rec) {
  if (!rec) return rec;
  const chain = rec.Chain !== undefined ? rec.Chain : rec.chain;
  const group = chainGrainGroup(chain);
  const fill = (camel, Pascal, val) => {
    if (rec[camel] === undefined || rec[camel] === null || rec[camel] === '') {
      if (rec[Pascal] === undefined || rec[Pascal] === null || rec[Pascal] === '') {
        rec[camel] = val; rec[Pascal] = val;
      } else { rec[camel] = rec[Pascal]; }
    }
  };
  if (group === 'PAN_INDIA_ONLY') {
    fill('zone', 'Zone', PAN_INDIA);
    fill('state', 'State', PAN_INDIA);
    fill('siteCode', 'SiteCode', NA_FIELD);
    fill('storeName', 'StoreName', NA_FIELD);
  } else if (group === 'ZONE_STATE_ONLY') {
    fill('siteCode', 'SiteCode', NA_FIELD);
    fill('storeName', 'StoreName', NA_FIELD);
  }
  return rec;
}

/** Apply normalizeGrainRecord across a record array; returns a small summary. */
function normalizeGrainRecords(recs) {
  const summary = { total: 0, pan_india_filled: 0, store_filled: 0, by_group: {} };
  (recs || []).forEach(r => {
    summary.total++;
    const g = chainGrainGroup(r.Chain !== undefined ? r.Chain : r.chain);
    summary.by_group[g] = (summary.by_group[g] || 0) + 1;
    const hadGeo = !!(r.State || r.state);
    const hadStore = !!(r.SiteCode || r.siteCode);
    normalizeGrainRecord(r);
    if (!hadGeo && (r.State === PAN_INDIA)) summary.pan_india_filled++;
    if (!hadStore && (r.SiteCode === NA_FIELD)) summary.store_filled++;
  });
  return summary;
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
