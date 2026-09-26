// Regression test for FM-22 (FY02/FY03 -- global FY filter not propagated,
// same class as FM-21): primaryOfftakeGapSection() and renderPogGapCharts()
// (Channel & Chain Performance > Comparison > Primary-Offtake Gap card)
// always showed FY27 whenever it had any rows, regardless of the global FY
// filter bar -- confirmed live: selecting FY26 still rendered a
// "Primary-Offtake Gap (FY27)" heading with FY27's numbers. Fixed via a
// shared pogGapWindow(g) helper that honors fOne('FY') when it names a
// covered key (fy26/fy27), else keeps the previous FY27-preferred default.
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && !!D.primary_offtake_gap, { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  const result = await pg.evaluate(() => {
    const g = D.primary_offtake_gap;
    if (!g.fy26 || !g.fy27 || !g.fy26.by_month.rows.length || !g.fy27.by_month.rows.length) {
      return { skip: true };
    }
    F.FY = []; const htmlNoFilter = primaryOfftakeGapSection();
    F.FY = ['FY26']; const htmlFY26 = primaryOfftakeGapSection();
    F.FY = ['FY27']; const htmlFY27 = primaryOfftakeGapSection();
    F.FY = [];

    const heading = (html) => (html.match(/Primary–Offtake Gap \(([^)]+)\)/) || [])[1];
    const win = pogGapWindow(g);

    return {
      skip: false,
      heading_no_filter: heading(htmlNoFilter),
      heading_fy26_selected: heading(htmlFY26),
      heading_fy27_selected: heading(htmlFY27),
      fy26_differs_from_fy27: htmlFY26 !== htmlFY27,
      helper_default_window: win
    };
  });

  if (result.skip) {
    console.log('  SKIP -- D.primary_offtake_gap does not have both fy26 and fy27 rows in this build, cannot prove filter-responsiveness');
  } else {
    check('test_no_filter_defaults_to_fy27', result.heading_no_filter === 'FY27', result);
    check('test_fy26_filter_shows_fy26_heading', result.heading_fy26_selected === 'FY26', result);
    check('test_fy27_filter_shows_fy27_heading', result.heading_fy27_selected === 'FY27', result);
    check('test_fy26_and_fy27_selections_render_differently', result.fy26_differs_from_fy27, result);
    check('test_pogGapWindow_default_matches_fy27_preferred_behavior', result.helper_default_window === 'fy27', result);
  }

  console.log(`\n  pog-gap-fy-filter tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
