// Regression test for F7 (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md):
// buildInventoryHealth()'s "Total Offtake" headline KPI used to fall back to
// a fabricated 0 (`?? 0`) when neither o.total[fyR] nor o.total_fyR existed,
// rendering "Rs 0.00 Cr" instead of an honest "-". Fixed to `?? null`,
// mirroring F1's NOT_AVAILABLE pattern -- crc(null) already renders '-'.
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && !!D.offtake, { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  const preNav = await pg.evaluate(() => {
    const o = D.offtake;
    const fyTags = (o && o.fy_tags) || (D.primary && D.primary.fy_tags) || [];
    const fyR = fyTags[fyTags.length - 1] || 'fy26';

    // Real data today: the live total for the latest real FY, unchanged by
    // the fix (both o.total[fyR] and o.total_fyR are populated today).
    const liveTotal = o?.total?.[fyR] ?? o?.[`total_${fyR}`] ?? null;

    // Synthetic case: neither field present for a FY tag that genuinely has
    // no data (e.g. a future FY far past coverage) -- must resolve to null,
    // not 0, and crc(null) must render '-', not 'Rs0.00 Cr'.
    const missingFyTotal = o?.total?.['fy99'] ?? o?.[`total_fy99`] ?? null;

    return {
      fyR, liveTotal, missingFyTotal,
      crcOfMissing: crc(missingFyTotal),
      crcOfLive: crc(liveTotal),
    };
  });

  // show() builds the tab body inside a setTimeout(...,0) -- wait for it to
  // actually run before querying the rendered DOM (same pattern as
  // tests/dashboard_sweep.js).
  await pg.evaluate(() => show('inventory-health'));
  await pg.waitForTimeout(300);
  const postNav = await pg.evaluate(() => {
    const kpiCards = [...document.querySelectorAll('#tab-inventory-health .kpi-card')];
    const totalOfftakeCard = kpiCards.find(c => c.querySelector('.kpi-label')?.textContent.trim() === 'Total Offtake');
    return { renderedValue: totalOfftakeCard ? totalOfftakeCard.querySelector('.kpi-value').textContent.trim() : null };
  });
  const result = { ...preNav, ...postNav };

  check('test_live_fy_total_is_real_nonzero_number_unchanged',
    typeof result.liveTotal === 'number' && result.liveTotal > 0, result);
  check('test_genuinely_missing_fy_resolves_to_null_not_zero',
    result.missingFyTotal === null, result);
  check('test_crc_of_missing_renders_dash_not_rs_zero',
    result.crcOfMissing === '–', result);
  check('test_live_kpi_tile_shows_real_value_matching_crc',
    result.renderedValue === result.crcOfLive, result);
  check('test_no_js_errors', errs.length === 0, errs);

  console.log(`\n  total-offtake-kpi-not-fabricated tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
