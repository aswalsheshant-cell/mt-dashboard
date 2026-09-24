// Regression test for F8 (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md):
// dashboard/mobile.html's RBC Total KPI used to render a literal hardcoded
// '▲ +10.7%' badge whenever D.yoy_metrics.status==='active', with zero real
// data behind it -- unlike the neighboring Primary/Offtake YoY badges, which
// read a real top_line.*_growth field. Confirmed dormant in production
// (F9: mobile.html has no <script src="data.js"> anywhere, window.DASH is
// never actually set there), so this test injects window.DASH via
// page.addInitScript (before mobile.html's own inline script runs) to
// exercise the code path directly, rather than relying on live data that
// this file is disconnected from.
const { chromium } = require('/home/user/mt-dashboard/node_modules/playwright');
const path = require('path');

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  // Inject a fixture window.DASH BEFORE the page's own script runs, gating
  // open exactly the branch F8 concerns (D.rbc.rbc_total present AND
  // D.yoy_metrics.status==='active') -- the only way to reach this dead
  // code in a controlled way, since mobile.html never loads real data.js.
  await pg.addInitScript(() => {
    window.DASH = {
      rbc: { rbc_total: 123.45 },
      yoy_metrics: { status: 'active', top_line: { primary_nsv_growth: 5.2, offtake_value_growth: -3.1 } },
    };
  });
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/mobile.html`, { waitUntil: 'load' });
  await pg.waitForTimeout(500);

  const result = await pg.evaluate(() => {
    const bodyText = document.body.innerText;
    const kpiLabels = [...document.querySelectorAll('.kpi .lab')].map(e => e.innerText.trim());
    const rbcLabel = [...document.querySelectorAll('.kpi .lab')].find(e => e.textContent.includes('RBC Total'));
    const rbcBadge = rbcLabel ? rbcLabel.querySelector('.yoy-badge') : undefined;
    return {
      bodyText,
      kpiLabels,
      rbcLabelFound: !!rbcLabel,
      rbcHasBadge: !!rbcBadge,
      rbcBadgeText: rbcBadge ? rbcBadge.textContent : null,
    };
  });

  check('test_no_hardcoded_10_7_percent_anywhere_on_page',
    !result.bodyText.includes('10.7%'), result.bodyText.slice(0, 200));
  check('test_rbc_total_kpi_still_renders', result.rbcLabelFound, result);
  check('test_rbc_total_kpi_has_no_growth_badge_at_all',
    result.rbcLabelFound && !result.rbcHasBadge, result);
  check('test_no_js_errors', errs.length === 0, errs);

  console.log(`\n  mobile-rbc-badge-not-fabricated tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
