// Semantic tests for the 95%-cumulative-contribution presentation hierarchy
// (Brand -> Emerging Brands; Subcategory-within-Category -> Others).
// Follows the same pattern as tests/dashboard_sweep.js: boot the REAL page in
// headless Chromium so the functions under test (cumulative95Group,
// subcatPareto95, grp -- all defined as page-global functions in
// dashboard/index.html) are called exactly as the dashboard itself calls
// them, with no re-implementation/duplication of their logic here.
//
// Covers (see PR discussion, "95% Contribution Hierarchy" spec):
//   test_brand_95_contribution_conservation
//   test_brand_emerging_group_conservation
//   test_brand_95_boundary_deterministic
//   test_subcategory_95_within_parent_category
//   test_subcategory_others_conservation
//   test_negative_subcategory_preserved
//   test_negative_subcategory_not_abs
//   test_category_total_unchanged
//   test_equal_value_sort_deterministic
const { chromium } = require('/home/user/mt-dashboard/node_modules/playwright');

function approxEqual(a, b, eps = 1e-6) { return Math.abs(a - b) < eps; }

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForTimeout(1500);

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail ? ' -- ' + detail : ''}`); }
  }

  // ---- test_brand_95_boundary_deterministic + worked example from the spec ----
  const workedExample = await pg.evaluate(() => {
    const items = [
      { name: 'Mamaearth', nsv: 70 }, { name: "The Derma Co", nsv: 15 },
      { name: 'Aqualogica', nsv: 6 }, { name: "Dr Sheth's", nsv: 4 },
      { name: 'Brand E', nsv: 2 }, { name: 'Brand F', nsv: 1.5 }, { name: 'Brand G', nsv: 1.5 },
    ];
    const g = cumulative95Group(items, 'name', 'nsv', 'Emerging Brands');
    return { majorNames: g.major.map(x => x.name), tailValue: g.tailValue, tailCount: g.tailCount };
  });
  check('test_brand_95_boundary_deterministic (major set matches worked example)',
    JSON.stringify(workedExample.majorNames) === JSON.stringify(['Mamaearth', "The Derma Co", 'Aqualogica', "Dr Sheth's"]),
    JSON.stringify(workedExample.majorNames));
  check('test_brand_emerging_group_conservation (E+F+G = 5.0)',
    approxEqual(workedExample.tailValue, 5.0), workedExample.tailValue);

  // ---- test_brand_95_contribution_conservation: major + tail = total, on REAL dashboard data ----
  const realBrandConservation = await pg.evaluate(() => {
    const brands = (D.primary && D.primary.by_brand) || [];
    // Same dynamic per-FY key the actual prBrand chart code uses (p.by_brand
    // items carry e.g. "fy26", not a plain "nsv" field) -- exercise the real
    // shape, not an assumed one.
    const fyKeys = brands.length ? Object.keys(brands[0]).filter(k => /^fy\d+$/.test(k)) : [];
    const valueKey = fyKeys[0];
    if (!valueKey) return null;
    const items = brands.filter(b => (b[valueKey] || 0) > 0.5);
    if (!items.length) return null;
    const g = cumulative95Group(items, 'name', valueKey, 'Emerging Brands');
    const totalIn = items.reduce((a, x) => a + x[valueKey], 0);
    const totalOut = g.major.reduce((a, x) => a + x[valueKey], 0) + g.tailValue;
    return { totalIn, totalOut, majorCount: g.major.length, tailCount: g.tailCount };
  });
  if (realBrandConservation) {
    check('test_brand_95_contribution_conservation (real primary.by_brand)',
      approxEqual(realBrandConservation.totalIn, realBrandConservation.totalOut),
      `${realBrandConservation.totalIn} vs ${realBrandConservation.totalOut}`);
  } else {
    console.log('  SKIP test_brand_95_contribution_conservation -- D.primary.by_brand not present in this build');
  }

  // ---- test_equal_value_sort_deterministic: repeated calls on tied values never reorder ----
  const tieDeterminism = await pg.evaluate(() => {
    const items = [{ name: 'Fragrances', nsv: 39.8 }, { name: 'Hair Colour', nsv: 39.8 }, { name: 'Face', nsv: 100 }];
    const runs = [0, 1, 2].map(() => cumulative95Group(items, 'name', 'nsv', 'X').major.map(x => x.name).join(','));
    return runs;
  });
  check('test_equal_value_sort_deterministic (3 runs identical, tie broken name-asc)',
    tieDeterminism.every(r => r === tieDeterminism[0]) && tieDeterminism[0] === 'Face,Fragrances,Hair Colour',
    JSON.stringify(tieDeterminism));

  // ---- test_negative_subcategory_preserved + test_negative_subcategory_not_abs ----
  // Spec example: A +2.0, B +1.0, C -0.5 (return-heavy) -> Others = 2.5, not 3.5.
  const negativeHandling = await pg.evaluate(() => {
    const recs = [
      { Category: 'Cat1', SubCategory: 'Major', NSV: 100 },
      { Category: 'Cat1', SubCategory: 'A', NSV: 2.0 },
      { Category: 'Cat1', SubCategory: 'B', NSV: 1.0 },
      { Category: 'Cat1', SubCategory: 'C', NSV: -0.5 },
    ];
    const out = subcatPareto95(recs);
    const others = out.find(x => x[0] === 'Others');
    return others ? others[1] : null;
  });
  check('test_negative_subcategory_preserved (Others bucket exists and is signed)', negativeHandling !== null);
  check('test_negative_subcategory_not_abs (Others = 2.5, not 3.5 or |2.5|-mangled)',
    approxEqual(negativeHandling, 2.5), negativeHandling);

  // ---- test_subcategory_95_within_parent_category: two categories, independent 95% ----
  // Cat1: Sub1=95 (dominant, alone >=95% of Cat1), Sub2=5 -> Sub1 major, Sub2 -> Others.
  // Cat2: SubX=50, SubY=50 -> both needed to reach 95% of Cat2 (cum 50%<95%, then 100%) -> both major.
  const withinCategory = await pg.evaluate(() => {
    const recs = [
      { Category: 'Cat1', SubCategory: 'Sub1', NSV: 95 },
      { Category: 'Cat1', SubCategory: 'Sub2', NSV: 5 },
      { Category: 'Cat2', SubCategory: 'SubX', NSV: 50 },
      { Category: 'Cat2', SubCategory: 'SubY', NSV: 50 },
    ];
    const out = Object.fromEntries(subcatPareto95(recs));
    return out;
  });
  check('test_subcategory_95_within_parent_category (Sub1 named, Cat1 Sub2 -> Others)',
    withinCategory['Sub1'] === 95 && (withinCategory['Others'] || 0) === 5,
    JSON.stringify(withinCategory));
  check('test_subcategory_95_within_parent_category (Cat2: both SubX and SubY named individually, not folded)',
    withinCategory['SubX'] === 50 && withinCategory['SubY'] === 50,
    JSON.stringify(withinCategory));

  // ---- test_subcategory_others_conservation + test_category_total_unchanged ----
  const catConservation = await pg.evaluate(() => {
    const recs = [
      { Category: 'Cat1', SubCategory: 'Sub1', NSV: 95 },
      { Category: 'Cat1', SubCategory: 'Sub2', NSV: 5 },
      { Category: 'Cat2', SubCategory: 'SubX', NSV: 50 },
      { Category: 'Cat2', SubCategory: 'SubY', NSV: 50 },
    ];
    const totalBefore = recs.reduce((a, r) => a + r.NSV, 0);
    const out = subcatPareto95(recs);
    const totalAfter = out.reduce((a, [, v]) => a + v, 0);
    return { totalBefore, totalAfter };
  });
  check('test_subcategory_others_conservation / test_category_total_unchanged (sum before == sum after grouping)',
    approxEqual(catConservation.totalBefore, catConservation.totalAfter),
    `${catConservation.totalBefore} vs ${catConservation.totalAfter}`);

  // ---- live-path check: the ACTUAL rendered Category & Pack Mix drill table
  // (Channel & Chain Performance > Category & Pack Mix > drill into a
  // Category) must show the grouped Sub-Category table with an "Others" row,
  // not a raw unbounded list. This is the real, reachable visual the fix
  // applies to -- buildPrimary()/buildCategory() (the functions named
  // prBrand/catSubP originally pointed to) are legacy, pre-v1.1.0-
  // consolidation code with no live caller (confirmed: grep finds no call
  // site for either), so the fix was NOT wired there; it was wired into
  // renderChannelSubview()'s live 'category' sub-view instead.
  await pg.evaluate(() => { F.FY = []; if (typeof applyFilters === 'function') applyFilters(); });
  await pg.evaluate(() => show('channel-dynamics'));
  await pg.waitForTimeout(300);
  await pg.evaluate(() => {
    channelDynamicsState.subview = 'category';
    channelDynamicsState.catPath = [];
  });
  await pg.evaluate(() => show('channel-dynamics'));
  await pg.waitForTimeout(300);
  const drillClicked = await pg.evaluate(() => {
    const a = document.querySelector('[data-cat-drill]');
    if (!a) return false;
    a.click();
    return true;
  });
  await pg.waitForTimeout(300);
  const liveTableText = drillClicked
    ? await pg.evaluate(() => document.getElementById('channel-subview-content')?.innerText || '')
    : '';
  check('test_live_subcategory_drill_shows_grouped_table (Category & Pack Mix, real render)',
    drillClicked && /Others \(\d+ sub-categories, <95% cutoff\)/.test(liveTableText),
    drillClicked ? liveTableText.slice(0, 200) : 'no drillable category link found');

  console.log(`\n  contribution-grouping tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
