// Regression test for F15 (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md
// follow-up sweep, 2026-09-25) -- contract changed by Issue #113 (2026-09-26).
//
// Before #113: the Promo Elasticity charts + Executive Brief were unreachable
// dead code (no wired button, no canvas in the DOM template) that fell through
// to fabricated numbers if reconnected (a literal 0.3 "elasticity" default, a
// 0.35 "macro elasticity" OR-fallback). An elasticityMethodologyValidated()
// guard gated them, and this test exercised that guard.
//
// Issue #113 removed that dead UI outright (Sprint 6 commit 4a2fe00; its last
// caller went with buildOfftakeImpact() in PR #112). The risk the guard
// covered -- a fabricated elasticity reaching a user -- is now closed at the
// source, so the contract becomes:
//   1. the real data is still unvalidated (the reason the feature stays off);
//   2. the removed functions, the brief modal and its constant are gone;
//   3. no dashboard code reads D.correlations unless it also checks
//      methodology_validated === true (a future rebuild must re-add the gate);
//   4. the live, unrelated "Promo Depth vs. Sell-Through -- Correlation" card
//      (computePromoSellThroughCorrelation, reads D.promo, not D.correlations)
//      is kept -- same name family, different feature;
//   5. the tab and legacy routes that used to host the dead UI load cleanly.
// The pipeline side (scripts/promo_offtake_correlation.py never fabricates
// lift/elasticity) stays covered by tests/test_promo_elasticity_not_fabricated.py.
const fs = require('fs');
const path = require('path');
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

const REMOVED = [
  'renderElasticityCurves', 'renderROIHeatmap', 'renderWaterfall', 'renderScatterTrend',
  'exportOfftakeCorrelations', 'getFilteredCorrelationData', 'elasticityMethodologyValidated',
  'generateExecutiveBrief', 'showExecutiveBriefModal', 'closeExecutiveBriefModal',
  'exportExecutiveBriefImage', 'exportExecutiveBriefPDF', 'copyExecutiveBriefToClipboard',
  'onGlobalFilterChange', 'ELASTICITY_NOT_AVAILABLE_TEXT',
];

(async () => {
  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  // Static: every first-party dashboard script (not vendored libs, not data.js).
  const dash = path.join(__dirname, '..', 'dashboard');
  const files = ['index.html', ...fs.readdirSync(dash).filter(f => f.endsWith('.js') && f !== 'data.js' && !f.endsWith('.min.js') && f !== 'chart.umd.js')];
  const ungated = files.filter(f => {
    const t = fs.readFileSync(path.join(dash, f), 'utf8');
    return /\bD(ASH)?\.correlations\b/.test(t) && !/methodology_validated\s*===\s*true/.test(t);
  });
  check('test_no_ungated_reader_of_D_correlations', ungated.length === 0, ungated);

  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && !!D.universe, { timeout: 30000 });

  const realState = await pg.evaluate(() => ({
    validated: D.correlations ? D.correlations.methodology_validated : undefined,
  }));
  check('test_real_data_is_not_validated_today', realState.validated !== true, realState);

  const live = await pg.evaluate((names) => ({
    stillDefined: names.filter(n => { try { return typeof eval(n) !== 'undefined'; } catch (e) { return false; } }),
    briefModal: !!document.getElementById('executiveBriefModal'),
    sellThroughKept: typeof computePromoSellThroughCorrelation === 'function',
  }), REMOVED);
  check('test_dead_elasticity_and_brief_code_is_removed', live.stillDefined.length === 0, live.stillDefined);
  check('test_executive_brief_modal_is_removed', live.briefModal === false);
  check('test_live_promo_sell_through_correlation_is_kept', live.sellThroughKept === true);

  // The tab that absorbed Promo/Forecast/Share, and the legacy routes whose
  // builders once owned the removed helpers, must still render without errors.
  for (const route of ['demand-planning', 'inventory-health', 'promo', 'offtake-impact', 'distribution', 'forecast']) {
    await pg.evaluate(r => show(r), route);
    await pg.waitForTimeout(600);
    const s = await pg.evaluate(() => {
      const sec = document.querySelector('section.active');
      const txt = sec ? sec.innerText : '';
      return { id: sec && sec.id, len: txt.length, bad: /\bNaN\b|\bundefined\b|\[object Object\]/.test(txt) };
    });
    check(`test_route_${route}_renders_cleanly`, !!s.id && s.len > 50 && !s.bad, s);
  }

  check('test_no_js_errors', errs.length === 0, errs);

  console.log(`\n  promo-elasticity-guard tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
