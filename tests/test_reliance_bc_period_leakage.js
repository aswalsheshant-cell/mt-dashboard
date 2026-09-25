// Regression test for F19 (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md
// follow-up sweep, 2026-09-25): buildRelianceBC()'s zoneVal/stateVal/
// brandVal/catVal used `x[fyk]||x.total||0` -- when a row had no entry for
// the selected/default FY (e.g. the real "Unallocated (prior period, no
// store-level detail available)" buckets, which carry only `fy26` and
// `total`, no `fy27`), this fell back to `.total` (the all-time figure) and
// rendered FY26-only money as if it were FY27 -- a real period-leakage bug.
//
// Correction on severity: buildRelianceBC() has ZERO call sites anywhere in
// index.html and its target container (`#tab-reliance-bc`) does not exist in
// the DOM template -- the live Reliance Brand Counter subview
// (renderChannelSubview()'s sv==='reliance' branch) reads detail_records via
// recFilter() instead, which already applies the real FY filter per-row with
// no cross-period fallback. So this bug never reached a real user; it is
// fixed anyway per this repo's "never leave a landmine even if dormant"
// principle (same as F8/F10). This test proves the FIX, not that a visible
// regression is now resolved -- it exercises buildRelianceBC() directly by
// injecting the DOM container it expects, since no navigation path reaches
// it in the live app.
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

  const result = await pg.evaluate(() => {
    // buildRelianceBC() is dead code (no call site, no DOM container in the
    // template) -- inject the container it expects so its logic can be
    // exercised directly, matching the real shape confirmed in the
    // certified data.js (an "Unallocated" bucket with fy26+total only, real
    // fy27-only rows alongside it).
    const container = document.createElement('section');
    container.id = 'tab-reliance-bc';
    document.body.appendChild(container);

    const savedBc = D.reliance_bc;
    const savedFy = F.FY.slice();

    D.reliance_bc = {
      fy_tags: ['fy26', 'fy27'],
      total_fy26: 4562.5, total_fy27: 2582.16, total: 7144.66,
      months_fy26: ['Mar-26'], monthly_fy26: [4562.5],
      months_fy27: ['Apr-26'], monthly_fy27: [2582.16],
      by_zone: [
        { name: 'Unallocated (prior period, no store-level detail available)', total: 4562.49, fy26: 4562.49 },
        { name: 'East', total: 806.91, fy27: 806.91 },
      ],
      by_state: [
        { state: 'Legacy State', zone: 'Unallocated (prior period, no store-level detail available)', total: 4562.49, fy26: 4562.49 },
        { state: 'Maharashtra', zone: 'East', total: 806.91, fy27: 806.91 },
      ],
      by_brand: [
        { name: 'Unallocated (prior period, no brand-level detail available)', total: 4562.49, fy26: 4562.49 },
        { name: 'Mamaearth', total: 2129.87, fy27: 2129.87 },
      ],
      by_category: [
        { name: 'Unallocated (prior period, no category-level detail available)', total: 4562.49, fy26: 4562.49 },
        { name: 'Face', total: 1427.07, fy27: 1427.07 },
      ],
    };

    function snapshot() {
      buildRelianceBC();
      return container.innerHTML;
    }

    F.FY = []; const htmlNoFilter = snapshot();
    F.FY = ['FY27']; const htmlFY27 = snapshot();
    F.FY = ['FY26']; const htmlFY26 = snapshot();

    F.FY = savedFy;
    D.reliance_bc = savedBc;
    container.remove();

    return { htmlNoFilter, htmlFY27, htmlFY26 };
  });

  // "Unallocated" carries only fy26 -- must never appear (as an FY27 number,
  // via the old .total fallback) in the default view or an explicit FY27
  // filter, but must appear correctly when FY26 is explicitly selected.
  check('test_no_filter_defaults_to_fy27_and_excludes_fy26_only_unallocated_zone',
    !result.htmlNoFilter.includes('Unallocated'), result.htmlNoFilter.slice(0, 400));
  check('test_fy27_filter_excludes_fy26_only_unallocated_brand',
    !result.htmlFY27.includes('Unallocated'), result.htmlFY27.slice(0, 400));
  check('test_fy27_filter_still_shows_real_fy27_rows',
    result.htmlFY27.includes('East') && result.htmlFY27.includes('Mamaearth') && result.htmlFY27.includes('Face'),
    result.htmlFY27.slice(0, 400));
  check('test_fy26_filter_correctly_shows_the_real_fy26_unallocated_rows',
    result.htmlFY26.includes('Unallocated'), result.htmlFY26.slice(0, 400));
  check('test_fy26_filter_excludes_fy27_only_rows',
    !result.htmlFY26.includes('>East<') && !result.htmlFY26.includes('>Mamaearth<') && !result.htmlFY26.includes('>Face<'),
    result.htmlFY26.slice(0, 400));
  // The lead paragraph legitimately differs ("₹ Lakh." vs "FY27 only.") --
  // what must match is that both resolve to the same fyk ('fy27', the
  // default-latest tag) and therefore the same real rows/values.
  const bcOffFrom = (html) => (html.match(/BC Offtake<\/div><div class="val">([^<]+)</) || [])[1];
  check('test_no_filter_and_fy27_filter_resolve_to_the_same_fy27_total',
    bcOffFrom(result.htmlNoFilter) === bcOffFrom(result.htmlFY27) && !!bcOffFrom(result.htmlFY27),
    { noFilter: bcOffFrom(result.htmlNoFilter), fy27: bcOffFrom(result.htmlFY27) });

  check('test_no_js_errors', errs.length === 0, errs);

  console.log(`\n  reliance-bc-period-leakage tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
