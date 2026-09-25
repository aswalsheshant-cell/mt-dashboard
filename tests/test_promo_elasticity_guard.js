// Regression test for F15's JS-side defense-in-depth guard
// (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md follow-up sweep,
// 2026-09-25): the Promo Elasticity charts + Executive Brief are currently
// unreachable in the live app (no wired button, no canvas elements in the
// DOM template), but several of these functions fell through to a
// hardcoded/fabricated number (e.g. a literal 0.3 "elasticity" default, a
// 0.35 "macro elasticity" OR-fallback that fires even with real-but-null
// chain data) the moment reconnected. elasticityMethodologyValidated()
// gates every one of them on D.correlations.methodology_validated === true
// -- this proves the gate blocks when unvalidated (today's real state) and
// does NOT block once validated (so a future real fix isn't permanently
// disabled by this guard).
const { chromium } = require('/home/user/mt-dashboard/node_modules/playwright');

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && !!D.universe, { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  // Real, current data state: proves the guard is actually engaged today,
  // not just in a synthetic fixture.
  const realState = await pg.evaluate(() => ({
    validated: D.correlations ? D.correlations.methodology_validated : undefined,
    hasCorrelations: !!D.correlations,
  }));
  check('test_real_data_is_not_validated_today',
    realState.validated !== true, realState);

  const chartCalls = await pg.evaluate(() => {
    // inject the canvases these functions expect (none exist in the real
    // DOM -- confirmed dead code) so their logic can be exercised directly.
    ['chart-elasticity', 'chart-heatmap', 'chart-waterfall', 'chart-scatter'].forEach(cid => {
      if (!document.getElementById(cid)) {
        const c = document.createElement('canvas');
        c.id = cid; c.width = 400; c.height = 200;
        document.body.appendChild(c);
      }
    });

    const savedCorr = D.correlations;
    const fakeChains = [{ name: 'X', elasticity_tiers: { tier_1: { elasticity: 0.5, avg_lift: 10, avg_discount: 40, count: 3 } } }];

    let calls;
    const OrigChart = window.Chart;
    function CountingChart(...args) { calls++; return new OrigChart(...args); }
    CountingChart.prototype = OrigChart.prototype;

    // Case 1: unvalidated -- must NOT build a single chart.
    D.correlations = { methodology_validated: false, by_chain: fakeChains };
    calls = 0; window.Chart = CountingChart;
    renderElasticityCurves(fakeChains);
    renderROIHeatmap(fakeChains);
    renderWaterfall(fakeChains);
    renderScatterTrend(fakeChains, []);
    window.Chart = OrigChart;
    const callsWhenUnvalidated = calls;

    // Case 2: validated -- must build all 4 (guard doesn't permanently
    // disable the feature, only gates it on real validation).
    D.correlations = { methodology_validated: true, by_chain: fakeChains };
    calls = 0; window.Chart = CountingChart;
    renderElasticityCurves(fakeChains);
    renderROIHeatmap(fakeChains);
    renderWaterfall(fakeChains);
    renderScatterTrend(fakeChains, []);
    window.Chart = OrigChart;
    const callsWhenValidated = calls;

    D.correlations = savedCorr;
    // clean up injected charts so they don't linger for later tests in a
    // shared browser context
    charts.splice(0, charts.length).forEach(c => { try { c.destroy(); } catch (e) {} });

    return { callsWhenUnvalidated, callsWhenValidated };
  });

  check('test_unvalidated_blocks_all_four_chart_functions',
    chartCalls.callsWhenUnvalidated === 0, chartCalls);
  check('test_validated_allows_all_four_chart_functions',
    chartCalls.callsWhenValidated === 4, chartCalls);

  const briefResult = await pg.evaluate(() => {
    const savedCorr = D.correlations;
    D.correlations = { methodology_validated: false, by_chain: [] };
    const unvalidatedBrief = generateExecutiveBrief();

    D.correlations = {
      methodology_validated: true,
      by_chain: [{ name: 'Reliance Retail', elasticity_tiers: { tier_2: { elasticity: 0.6, avg_discount: 55 } } }],
      summary: { optimal_depth_range: '45-55%' },
    };
    const validatedBrief = generateExecutiveBrief();

    D.correlations = savedCorr;
    return { unvalidatedBrief, validatedBrief };
  });

  check('test_unvalidated_brief_is_explicitly_not_available',
    briefResult.unvalidatedBrief.not_available === true && briefResult.unvalidatedBrief.macro_elasticity === '–',
    briefResult.unvalidatedBrief);
  check('test_validated_brief_computes_normally',
    briefResult.validatedBrief.not_available !== true && typeof briefResult.validatedBrief.macro_elasticity === 'string',
    briefResult.validatedBrief);

  // exportOfftakeCorrelations() alerts and refuses when unvalidated.
  let dialogText = null;
  pg.once('dialog', async d => { dialogText = d.message(); await d.accept(); });
  await pg.evaluate(() => {
    const saved = D.correlations;
    D.correlations = { methodology_validated: false, by_chain: [] };
    exportOfftakeCorrelations();
    D.correlations = saved;
  });
  await pg.waitForTimeout(100);
  check('test_export_alerts_and_refuses_when_unvalidated',
    dialogText !== null && /not available/i.test(dialogText), dialogText);

  check('test_no_js_errors', errs.length === 0, errs);

  console.log(`\n  promo-elasticity-guard tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
