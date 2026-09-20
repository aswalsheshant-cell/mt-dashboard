// Tests for the NPI filter-aware performance layer (computeNpiPerformance()
// / npiCohortSection() in dashboard/index.html) -- STATIC IDENTITY, DYNAMIC
// PERFORMANCE: cohort membership (D.npd.by_fy) must never change under a
// dashboard filter; performance metrics (NSV/units/active/contribution)
// must respond to the same global filter bar every other Commercial
// Analytics card uses. Boots the real page in headless Chromium, same
// pattern as tests/test_contribution_grouping.js.
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

  await pg.evaluate(() => { F.Chain = []; F.Category = []; F.FY = []; onFilterChange(); });
  await pg.waitForTimeout(300);

  // ---- unfiltered aggregation exactly matches the immutable identity layer ----
  const unfiltered = await pg.evaluate(() => {
    const fys = Object.keys(D.npd.metrics_by_fy);
    const out = {};
    fys.forEach(fy => { out[fy] = computeNpiPerformance(D.npd, fy); });
    return { fys, out, backend: D.npd.metrics_by_fy };
  });
  unfiltered.fys.forEach(fy => {
    const p = unfiltered.out[fy], m = unfiltered.backend[fy];
    check(`test_unfiltered_${fy}_launches_matches_backend`, p.launches === m.npi_launches, [p.launches, m.npi_launches]);
    check(`test_unfiltered_${fy}_nsv_matches_backend`, approxEqual(p.nsv, m.npi_nsv), [p.nsv, m.npi_nsv]);
    check(`test_unfiltered_${fy}_active_matches_backend`, p.active_count === m.active_npi_count, [p.active_count, m.active_npi_count]);
    check(`test_unfiltered_${fy}_contribution_matches_backend`, m.npi_contribution_pct == null || approxEqual(p.contribution_pct, m.npi_contribution_pct), [p.contribution_pct, m.npi_contribution_pct]);
  });

  // ---- cohort identity (D.npd.by_fy) never changes when a filter is applied ----
  const identityBefore = await pg.evaluate(() => JSON.stringify(D.npd.by_fy.FY27.slice(0, 20)));
  await pg.evaluate(() => { F.Chain = ['DMart']; onFilterChange(); });
  await pg.waitForTimeout(300);
  const identityAfter = await pg.evaluate(() => JSON.stringify(D.npd.by_fy.FY27.slice(0, 20)));
  check('test_cohort_identity_immutable_under_chain_filter', identityBefore === identityAfter);

  // ---- filtering to one chain: every visible launch actually belongs to that chain ----
  const dmartFiltered = await pg.evaluate(() => {
    const p = computeNpiPerformance(D.npd, 'FY27');
    return { launches: p.launches, allDmart: p.rows.every(r => r.chain === 'DMart'), totalUnfiltered: D.npd.metrics_by_fy.FY27.npi_launches };
  });
  check('test_chain_filter_reduces_launch_count', dmartFiltered.launches < dmartFiltered.totalUnfiltered, dmartFiltered);
  check('test_chain_filter_only_shows_that_chains_launches', dmartFiltered.allDmart);
  check('test_chain_filter_launches_positive', dmartFiltered.launches > 0, dmartFiltered.launches);

  // ---- contribution % under a filter uses the FILTERED total, not the global total ----
  const contributionCheck = await pg.evaluate(() => {
    const p = computeNpiPerformance(D.npd, 'FY27');
    const filteredTotalNsv = REC.filter(r => FILT.every(([k]) => !F[k].length || F[k].includes(String(r[k])))).reduce((a, r) => a + (r.NSV || 0), 0);
    const expectedPct = filteredTotalNsv ? p.nsv / filteredTotalNsv * 100 : null;
    return { reported: p.contribution_pct, expected: expectedPct };
  });
  check('test_contribution_pct_uses_filtered_total_not_global',
    approxEqual(contributionCheck.reported, contributionCheck.expected), contributionCheck);

  // ---- switching the cohort selector changes which cohort is shown, not identity ----
  await pg.evaluate(() => { F.Chain = []; onFilterChange(); });
  await pg.waitForTimeout(300);
  const cohortSwitch = await pg.evaluate(() => {
    npiSetCohortFy('FY26');
    return { launches: computeNpiPerformance(D.npd, 'FY26').launches, backend: D.npd.metrics_by_fy.FY26.npi_launches };
  });
  check('test_cohort_selector_switch_matches_backend_for_selected_fy',
    cohortSwitch.launches === cohortSwitch.backend, cohortSwitch);

  // ---- category filter that excludes an article: article disappears from
  // metrics, but its cohort identity entry is still present in D.npd.by_fy ----
  const categoryDrop = await pg.evaluate(() => {
    const before = D.npd.by_fy.FY27.length;
    F.Category = ['__no_such_category_xyz__']; onFilterChange();
    const p = computeNpiPerformance(D.npd, 'FY27');
    const after = D.npd.by_fy.FY27.length;
    F.Category = []; onFilterChange();
    return { before, after, filteredLaunches: p.launches };
  });
  check('test_impossible_category_filter_shows_zero_launches', categoryDrop.filteredLaunches === 0, categoryDrop);
  check('test_impossible_category_filter_does_not_shrink_cohort_map', categoryDrop.before === categoryDrop.after, categoryDrop);

  console.log(`\n  npi-filter-aware tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
