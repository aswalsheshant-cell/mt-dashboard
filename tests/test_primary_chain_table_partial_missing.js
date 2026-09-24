// Regression test for a real production defect found 2026-09-24 while
// regenerating dashboard/data.js from the raw source for the first time
// after F14 (primary_block()'s dim_rows() fix, docs/PHASE_2B_FINANCIAL_
// CONSUMER_INVENTORY.md) landed in this repo's history.
//
// renderChannelSubview()'s "Top Chains by Primary NSV" table used
// `chains.every(c=>c[primYr]!=null)` to decide whether to render the table
// at all -- requiring EVERY chain (all 45) to carry a value for the
// selected FY, or the WHOLE table was nuked to "No Primary Sales data
// available", triggering the whole-FY cross-FY fallback (F3) meant for a
// genuinely different, much rarer scenario (every chain lacking data, not
// 2 of 45). This was harmless only by accident: before F14, every chain
// always got a fabricated 0 for a missing FY, so every() trivially passed.
// The moment F14's fix reached a real data.js refresh and correctly nulled
// 2 of 45 chains (Dabur New U, Medanta -- no real FY26 primary rows),
// every() started failing and the entire 45-chain table went blank, even
// though 43 of 45 chains had real data -- confirmed live via screenshot
// during this session, not a synthetic scenario.
//
// Fixed by filtering to chains that have real primYr data instead of
// requiring all of them to. This test proves both directions: a few
// missing chains must not blank the table (only they are excluded), and
// the true whole-FY-missing case (F3's actual scenario) must still trigger
// the cross-FY fallback correctly.
const { chromium } = require('/home/user/mt-dashboard/node_modules/playwright');

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && !!D.primary, { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  await pg.evaluate(() => show('channel-dynamics'));
  await pg.waitForTimeout(400);

  const result = await pg.evaluate(() => {
    const yrLab = { fy26: 'FY26', fy27: 'FY27' };

    // Case 1: a FEW chains missing (real shape, live data today: 43 of 45
    // have fy26, 2 have null) -- must render the 43, not blank the table.
    const fewMissingChains = [
      { name: 'A', fy26: 100 }, { name: 'B', fy26: 50 }, { name: 'C', fy26: null },
    ];
    const fewMissingChannels = [{ name: 'MT', fy26: 150 }];
    channelDynamicsState.subview = 'primary';
    renderChannelSubview(fewMissingChains, [], fewMissingChannels, 'fy26', 'FY26', yrLab);
    const fewMissingHtml = document.getElementById('channel-subview-content').innerHTML;

    // Case 2: ALL chains missing (F3's actual documented scenario) -- must
    // still trigger the whole-FY cross-FY fallback (or the honest "no data"
    // message when the fallback FY also has nothing).
    const allMissingChains = [{ name: 'A', fy26: null }, { name: 'B', fy26: null }];
    const allMissingChannels = [{ name: 'MT', fy26: null }];
    renderChannelSubview(allMissingChains, [], allMissingChannels, 'fy26', 'FY26', yrLab);
    const allMissingHtml = document.getElementById('channel-subview-content').innerHTML;

    // Case 3: real live data today (43 of 45 chains have fy26) -- the
    // actual regression, on the actual certified data.js.
    const p = D.primary, o = D.offtake;
    const liveChains = (p.by_chain || []).filter(c => c.name !== 'Unmapped Chain');
    renderChannelSubview(liveChains, p.by_brand, p.by_channel, 'fy26', 'FY26', yrLab);
    const liveHtml = document.getElementById('channel-subview-content').innerHTML;
    const liveMissingCount = liveChains.filter(c => c.fy26 == null).length;

    return { fewMissingHtml, allMissingHtml, liveHtml, liveMissingCount, liveTotalChains: liveChains.length };
  });

  check('test_a_few_missing_chains_does_not_blank_the_table',
    result.fewMissingHtml.includes('A') && result.fewMissingHtml.includes('B') &&
    !result.fewMissingHtml.includes('No Primary Sales data available'), result.fewMissingHtml.slice(0, 300));
  check('test_a_few_missing_chains_excludes_only_the_missing_one',
    !/>C</.test(result.fewMissingHtml), result.fewMissingHtml.slice(0, 300));
  check('test_all_chains_missing_still_triggers_fallback_or_honest_no_data',
    result.allMissingHtml.includes('No Primary Sales data available') ||
    result.allMissingHtml.includes('No FY26 Primary chain data available'), result.allMissingHtml.slice(0, 300));

  check('test_live_data_today_has_a_few_missing_chains_not_zero_not_all',
    result.liveMissingCount > 0 && result.liveMissingCount < result.liveTotalChains,
    { missing: result.liveMissingCount, total: result.liveTotalChains });
  check('test_live_data_top_chains_table_renders_not_blank',
    !result.liveHtml.includes('No Primary Sales data available'), result.liveHtml.slice(0, 300));
  check('test_live_data_table_shows_most_chains_not_just_a_couple',
    (result.liveHtml.match(/<tr>/g) || []).length >= result.liveTotalChains - result.liveMissingCount,
    result.liveHtml.slice(0, 200));

  check('test_no_js_errors', errs.length === 0, errs);

  console.log(`\n  primary-chain-table-partial-missing tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
