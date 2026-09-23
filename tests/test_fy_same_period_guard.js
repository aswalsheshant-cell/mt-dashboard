// Regression test for FM-18 (FY05 -- Partial-year mismatch): buildComparison()'s
// article-level dimension branch (SubCategory/Range/PackSize/Article) was
// comparing full-FY totals with no shared-month restriction, so a partial
// current FY (e.g. FY27 YTD Apr-Aug) read as a decline against a full prior
// FY when the true same-period move was strong growth (Face Cleanser: shown
// -18.1%, true same-period +113.1%). Fixed by sameFYPeriodGuard(), extracted
// as its own page-global function in dashboard/index.html so it can be
// tested here with fixtures, independent of live data -- same pattern as
// tests/test_contribution_grouping.js (cumulative95Group) and
// tests/test_npi_filter_aware.js.
const { chromium } = require('/home/user/mt-dashboard/node_modules/playwright');

function approxEqual(a, b, eps = 0.01) { return Math.abs(a - b) < eps; }

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForTimeout(1000);

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  // ---- FIXTURE 1: partial current FY vs full prior FY -- must restrict to
  // shared months and flip the misleading full-year result to the correct
  // same-period one. Deterministic synthetic values, not live data. ----
  const partialYearFixture = await pg.evaluate(() => {
    const recs = [];
    // FY26: full 12 months, but back-loaded -- Apr-Aug at a low rate (8/mo =
    // 40), Sep-Mar at a higher rate (20/mo x 7 = 140) -> full-year total 180.
    ['April','May','June','July','Aug'].forEach(m => recs.push({ FY: 'FY26', Month: m, SubCategory: 'Widget', NSV: 8 }));
    ['Sept','Oct','Nov','Dec','Jan','Feb','March'].forEach(m => recs.push({ FY: 'FY26', Month: m, SubCategory: 'Widget', NSV: 20 }));
    // FY27: only Apr-Aug so far (YTD), but at a much higher run-rate (30/mo
    // = 150) -- real, strong same-period growth (40 -> 150). Comparing the
    // FY27 YTD total (150) against the FY26 FULL-year total (180) instead
    // reads as a -16.7% decline -- the exact direction-reversal failure mode
    // confirmed live (Face Cleanser: shown -18.1%, true same-period +113.1%).
    ['April','May','June','July','Aug'].forEach(m => recs.push({ FY: 'FY27', Month: m, SubCategory: 'Widget', NSV: 30 }));
    const fys = [...new Set(recs.map(r => r.FY))].sort();
    const [fyA, fyB] = [fys[fys.length - 2], fys[fys.length - 1]];
    const { recs: periodRecs, sharedMonths } = sameFYPeriodGuard(recs, fyA, fyB);
    const m = {};
    periodRecs.forEach(r => { (m[r.SubCategory] ??= {})[r.FY] = (m[r.SubCategory]?.[r.FY] || 0) + r.NSV; });
    const a = m.Widget[fyA] || 0, bVal = m.Widget[fyB] || 0;
    const naiveA = recs.filter(r => r.FY === fyA).reduce((s, r) => s + r.NSV, 0);
    const naiveB = recs.filter(r => r.FY === fyB).reduce((s, r) => s + r.NSV, 0);
    return {
      fyA, fyB, sharedCount: sharedMonths ? sharedMonths.size : null,
      samePeriodA: a, samePeriodB: bVal,
      naiveA, naiveB,
      naiveYoy: Math.round((naiveB / naiveA - 1) * 1000) / 10,
      samePeriodYoy: Math.round((bVal / a - 1) * 1000) / 10
    };
  });
  check('test_partial_year_restricts_to_5_shared_months', partialYearFixture.sharedCount === 5, partialYearFixture);
  check('test_partial_year_same_period_values_correct',
    partialYearFixture.samePeriodA === 40 && partialYearFixture.samePeriodB === 150, partialYearFixture);
  check('test_naive_full_year_comparison_shows_false_decline',
    partialYearFixture.naiveYoy === -16.7, partialYearFixture); // 150/180-1 = -16.7% (false decline)
  check('test_same_period_comparison_shows_true_growth',
    partialYearFixture.samePeriodYoy === 275.0, partialYearFixture); // 150/40-1 = +275% (true growth)
  check('test_same_period_guard_reverses_the_sign_naive_gets_wrong',
    partialYearFixture.naiveYoy < 0 && partialYearFixture.samePeriodYoy > 0, partialYearFixture);

  // ---- FIXTURE 2: full FY vs full FY (equal month coverage) -- must be a
  // no-op: sharedMonths null, recs pass through unchanged, no restriction. ----
  const fullYearFixture = await pg.evaluate(() => {
    const recs = [];
    ['April','May','June','July','Aug','Sept','Oct','Nov','Dec','Jan','Feb','March'].forEach(m => {
      recs.push({ FY: 'FY25', Month: m, SubCategory: 'Widget', NSV: 10 });
      recs.push({ FY: 'FY26', Month: m, SubCategory: 'Widget', NSV: 12 });
    });
    const { recs: periodRecs, sharedMonths } = sameFYPeriodGuard(recs, 'FY25', 'FY26');
    return { sharedMonths: sharedMonths, recsUnchanged: periodRecs.length === recs.length, recsAreSameRef: periodRecs === recs };
  });
  check('test_full_year_vs_full_year_is_noop_no_restriction', fullYearFixture.sharedMonths === null, fullYearFixture);
  check('test_full_year_vs_full_year_recs_pass_through_unchanged', fullYearFixture.recsUnchanged, fullYearFixture);
  check('test_full_year_vs_full_year_returns_same_array_reference', fullYearFixture.recsAreSameRef, fullYearFixture);

  // ---- FIXTURE 3: single FY only (no prior year at all) -- fyA is null,
  // guard must be a no-op (nothing to restrict against). ----
  const singleYearFixture = await pg.evaluate(() => {
    const recs = [{ FY: 'FY26', Month: 'April', SubCategory: 'Widget', NSV: 10 }];
    const { recs: periodRecs, sharedMonths } = sameFYPeriodGuard(recs, null, 'FY26');
    return { sharedMonths, recsUnchanged: periodRecs.length === recs.length };
  });
  check('test_no_prior_fy_is_noop', singleYearFixture.sharedMonths === null, singleYearFixture);
  check('test_no_prior_fy_recs_unchanged', singleYearFixture.recsUnchanged, singleYearFixture);

  // ---- LIVE-DATA TIE-BACK: confirm the fix is actually wired into
  // buildComparison() against real production data -- the exact confirmed
  // incident (Face Cleanser, SubCategory dim, All-FY filter). ----
  const liveCheck = await pg.evaluate(() => {
    F.FY = []; F.Chain = []; F.Category = [];
    cmpDim = 'SubCategory';
    wireCmpButtons(document.getElementById('tab-comparison'));
    buildComparison();
    const recs = recFilter('SubCategory');
    const fys = [...new Set(recs.map(r => r.FY))].sort();
    const [fyA, fyB] = [fys[fys.length - 2], fys[fys.length - 1]];
    const { sharedMonths } = sameFYPeriodGuard(recs, fyA, fyB);
    const noteShown = !!document.querySelector('#tab-comparison .drillhint');
    const tableText = document.querySelector('#tab-comparison table tbody')?.innerText || '';
    const idx = tableText.indexOf('Face Cleanser');
    const faceCleanserRow = idx >= 0 ? tableText.slice(idx, idx + 120).replace(/\s+/g, ' ') : '';
    return { fyA, fyB, sharedCount: sharedMonths ? sharedMonths.size : null, noteShown, faceCleanserRow, hasFace: tableText.includes('Face Cleanser') };
  });
  check('test_live_data_fy26_fy27_restricts_to_5_shared_months', liveCheck.sharedCount === 5, liveCheck);
  check('test_live_data_disclosure_note_shown', liveCheck.noteShown, liveCheck);
  check('test_live_data_face_cleanser_present', liveCheck.hasFace, liveCheck);
  check('test_live_data_face_cleanser_shows_correct_positive_growth',
    liveCheck.hasFace && /\+113\.1%|\+11[0-9]\.\d%/.test(liveCheck.faceCleanserRow), liveCheck);
  check('test_live_data_face_cleanser_does_not_show_stale_negative_value',
    liveCheck.hasFace && !liveCheck.faceCleanserRow.includes('-18.1%'), liveCheck);

  console.log(`\n  fy-same-period-guard tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
