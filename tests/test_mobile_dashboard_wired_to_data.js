// Regression test for F9 (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md):
// dashboard/mobile.html had no <script src="data.js"> anywhere, so
// window.DASH was always {} and every tab showed "Dashboard data not
// loaded" -- and even the parts written against the real schema
// (initializeFilters()) never ran. Separately, most render functions read
// fields that never existed (D.rbc, D.by_chain, D.primary_total,
// D.offtake_total, D.store_count, D.yoy_metrics) instead of the real
// top-level D.primary/D.offtake/D.universe/D.reliance_bc/D.detail_meta
// shape, and D.insights rows were read via the wrong field names
// (headline/detail instead of title/text).
//
// This test loads mobile.html against the REAL, certified data.js and
// proves: the app actually loads, every tab renders real, non-fabricated
// values, no NaN/undefined/[object Object]/blank-card leaks through, the
// FY filter now offers FY27 (previously impossible -- D.primary.fy_tags
// alone never includes it) and actually changes rendered totals, and the
// formatNum() fix (INR Lakh, not raw rupees) renders a real, correctly
// labeled currency string rather than a bare unlabeled number.
const { chromium } = require('/home/user/mt-dashboard/node_modules/playwright');

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  pg.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/mobile.html`, { waitUntil: 'load' });
  await pg.waitForTimeout(800);

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  const bodyTextEarly = await pg.evaluate(() => document.body.innerText);
  check('test_data_actually_loaded_not_the_old_placeholder_message',
    !bodyTextEarly.includes('Dashboard data not loaded'), bodyTextEarly.slice(0, 200));

  // ---- Overview tab (default) ----
  const overview = await pg.evaluate(() => ({
    text: document.getElementById('content').innerText,
    hasNaN: /\bNaN\b/.test(document.getElementById('content').innerText),
    hasUndefined: /\bundefined\b/.test(document.getElementById('content').innerText),
    hasObjObj: document.getElementById('content').innerText.includes('[object Object]'),
  }));
  check('test_overview_no_nan', !overview.hasNaN, overview.text.slice(0, 300));
  check('test_overview_no_undefined', !overview.hasUndefined, overview.text.slice(0, 300));
  check('test_overview_no_object_object', !overview.hasObjObj, overview.text.slice(0, 300));
  check('test_overview_shows_top_chains_table_not_empty',
    overview.text.includes('Top Chains') && !overview.text.includes('No chain-level'), overview.text.slice(0, 400));
  // Active Stores real value (D.universe.active_stores) -- pinned per
  // CLAUDE.md's verified baseline (426 active stores).
  check('test_overview_shows_real_active_stores_426', overview.text.includes('426'), overview.text.slice(0, 400));
  // formatNum() fix: a real Lakh-scale value must render with a currency
  // symbol and unit (Cr/L), never a bare unlabeled number like "32900".
  check('test_overview_currency_values_have_unit_labels',
    /₹[\d,.]+\s*(Cr|L)/.test(overview.text), overview.text.slice(0, 400));

  // ---- Primary tab ----
  await pg.evaluate(() => switchTab('primary'));
  await pg.waitForTimeout(300);
  const primary = await pg.evaluate(() => document.getElementById('content').innerText);
  check('test_primary_no_nan_undefined_objobj',
    !/\bNaN\b/.test(primary) && !/\bundefined\b/.test(primary) && !primary.includes('[object Object]'),
    primary.slice(0, 300));
  check('test_primary_shows_by_chain_table', primary.includes('By Chain') && !primary.includes('No chain-level'), primary.slice(0, 400));
  check('test_primary_shows_like_for_like_yoy_badge', primary.includes('like-for-like'), primary.slice(0, 300));

  // ---- Offtake tab ----
  await pg.evaluate(() => switchTab('offtake'));
  await pg.waitForTimeout(300);
  const offtake = await pg.evaluate(() => document.getElementById('content').innerText);
  check('test_offtake_no_nan_undefined_objobj',
    !/\bNaN\b/.test(offtake) && !/\bundefined\b/.test(offtake) && !offtake.includes('[object Object]'),
    offtake.slice(0, 300));
  check('test_offtake_shows_top_chains_by_offtake', offtake.includes('Top Chains by Offtake'), offtake.slice(0, 400));
  check('test_offtake_active_counters_kpi_removed', !offtake.includes('Active Counters'), offtake.slice(0, 300));

  // ---- Insights tab ----
  await pg.evaluate(() => switchTab('insights'));
  await pg.waitForTimeout(300);
  const insights = await pg.evaluate(() => document.getElementById('content').innerText);
  check('test_insights_no_nan_undefined_objobj',
    !/\bNaN\b/.test(insights) && !/\bundefined\b/.test(insights) && !insights.includes('[object Object]'),
    insights.slice(0, 300));
  check('test_insights_cards_not_blank_have_real_title_text',
    insights.length > 40 && !insights.includes('No additional insights available'), insights.slice(0, 400));
  check('test_insights_no_fabricated_yoy_summary_card', !insights.includes('Annual Growth Comparison'), insights.slice(0, 300));

  // ---- FY filter now offers FY27, and selecting it changes real numbers ----
  const fyTest = await pg.evaluate(() => {
    const opts = [...document.getElementById('fySelect').options].map(o => o.value);
    switchTab('overview');
    const noFilterText = document.getElementById('content').innerText;
    document.getElementById('fySelect').value = 'fy27';
    filters.fy = 'fy27';
    switchTab('overview');
    const fy27Text = document.getElementById('content').innerText;
    return { opts, noFilterText, fy27Text };
  });
  check('test_fy_dropdown_now_offers_fy27', fyTest.opts.includes('fy27'), fyTest.opts);
  check('test_selecting_fy27_actually_changes_rendered_overview',
    fyTest.noFilterText !== fyTest.fy27Text, { before: fyTest.noFilterText.slice(0, 150), after: fyTest.fy27Text.slice(0, 150) });

  check('test_no_js_errors_across_whole_run', errs.length === 0, errs);

  console.log(`\n  mobile-dashboard-wired-to-data tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
