// Regression test for FM-21 (FY02/FY03 -- global FY filter not propagated):
// mappingHealthSection() (Commercial Analytics > Chain Mapping Health) always
// showed the LATEST FY in D.mapping_health.by_fy regardless of the global FY
// filter bar -- confirmed live by comparing rendered HTML with no filter vs
// FY26 selected: byte-identical. Fixed to follow the same pattern already
// used by npiCohortSection() (default to the global filter when it names a
// real FY in this block's own coverage, else latest).
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && !!D.mapping_health, { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  const result = await pg.evaluate(() => {
    const fys = Object.keys(D.mapping_health.by_fy);
    if (fys.length < 2) return { skip: true, fys };
    const oldestFy = fys[0], latestFy = fys[fys.length - 1];

    F.FY = []; const htmlNoFilter = mappingHealthSection();
    F.FY = [oldestFy]; const htmlOldest = mappingHealthSection();
    F.FY = [latestFy]; const htmlLatest = mappingHealthSection();
    F.FY = [];

    const extractPct = (html) => {
      const m = html.match(/Mapping completeness \(([^)]+)\)[^0-9]*(\d+\.\d+)%/);
      return m ? { fyLabel: m[1], pct: m[2] } : null;
    };

    return {
      skip: false,
      fys, oldestFy, latestFy,
      backend_oldest: D.mapping_health.by_fy[oldestFy].completeness_pct,
      backend_latest: D.mapping_health.by_fy[latestFy].completeness_pct,
      shown_no_filter: extractPct(htmlNoFilter),
      shown_oldest_filter: extractPct(htmlOldest),
      shown_latest_filter: extractPct(htmlLatest),
      no_filter_equals_latest_filter: htmlNoFilter === htmlLatest,
      oldest_filter_differs_from_latest: htmlOldest !== htmlLatest
    };
  });

  if (result.skip) {
    console.log(`  SKIP -- D.mapping_health.by_fy has < 2 FYs (${JSON.stringify(result.fys)}), cannot prove filter-responsiveness`);
  } else {
    check('test_no_filter_still_shows_latest_fy_by_default',
      result.no_filter_equals_latest_filter, result);
    check('test_oldest_fy_filter_changes_the_rendered_output',
      result.oldest_filter_differs_from_latest, result);
    check('test_oldest_fy_filter_shows_oldest_fy_label',
      result.shown_oldest_filter && result.shown_oldest_filter.fyLabel === result.oldestFy, result);
    // Display is .toFixed(1) of the backend value -- compare against that
    // same rounding, not a raw float equality (two close backend values,
    // e.g. 99.99 and 99.95, can both legitimately round to the same "100.0").
    check('test_oldest_fy_filter_shows_oldest_fy_backend_value',
      result.shown_oldest_filter && result.shown_oldest_filter.pct === result.backend_oldest.toFixed(1), result);
    check('test_latest_fy_filter_shows_latest_fy_backend_value',
      result.shown_latest_filter && result.shown_latest_filter.pct === result.backend_latest.toFixed(1), result);
  }

  console.log(`\n  mapping-health-fy-filter tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
