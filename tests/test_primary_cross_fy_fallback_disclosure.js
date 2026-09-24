// Regression test for F3 (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md):
// renderChannelSubview()'s "Top Chains by Primary NSV" table has a real
// cross-FY fallback -- if EVERY chain (or channel) genuinely lacks the
// selected FY entirely, it silently relabels the prior FY's rows as the
// selected FY. F3's recommended action was to document this fallback
// condition clearly so a future data gap doesn't silently relabel FYs.
// Fixed by (a) a code comment at the fallback site and (b) a visible
// .fynote disclosure banner that renders whenever the fallback actually
// fires -- so "silently" stops being true even if the fallback path itself
// is unchanged. This test proves both: the disclosure fires exactly when
// the fallback fires, never otherwise, and the underlying table values are
// unaffected either way (same relabeled numbers as before this fix).
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

  // Mount the tab so #channel-subview-content exists, then call
  // renderChannelSubview() directly with synthetic chains/channels --
  // isolates this test from whatever real D.primary.by_chain happens to
  // contain today, and lets us construct the exact fallback-triggering
  // shape (every chain missing fy27 entirely) deterministically.
  await pg.evaluate(() => show('channel-dynamics'));
  await pg.waitForTimeout(300);

  const result = await pg.evaluate(() => {
    const yrLab = { fy26: 'FY26', fy27: 'FY27' };

    // Case 1: fallback SHOULD fire -- no chain/channel has fy27 at all.
    const fallbackChains = [
      { name: 'ChainA', fy26: 100 },
      { name: 'ChainB', fy26: 50 },
    ];
    const fallbackChannels = [{ name: 'MT', fy26: 150 }];
    channelDynamicsState.subview = 'primary';
    renderChannelSubview(fallbackChains, [], fallbackChannels, 'fy27', 'FY27', yrLab);
    const fallbackHtml = document.getElementById('channel-subview-content').innerHTML;

    // Case 2: fallback should NOT fire -- real fy27 data present on every chain.
    const realChains = [
      { name: 'ChainA', fy27: 120 },
      { name: 'ChainB', fy27: 60 },
    ];
    const realChannels = [{ name: 'MT', fy27: 180 }];
    renderChannelSubview(realChains, [], realChannels, 'fy27', 'FY27', yrLab);
    const realHtml = document.getElementById('channel-subview-content').innerHTML;

    // Case 3: live data today, whatever it is -- must not show the
    // disclosure banner (confirms the doc's "not currently triggered" claim
    // still holds against the real, certified data.js).
    F.FY = [];
    buildChannelDynamics();
    const liveFy26Html = document.getElementById('channel-subview-content').innerHTML;
    F.FY = ['FY27'];
    buildChannelDynamics();
    const liveFy27Html = document.getElementById('channel-subview-content').innerHTML;
    F.FY = [];

    return {
      fallbackHtml, realHtml, liveFy26Html, liveFy27Html,
    };
  });

  const disclosureText = 'No FY27 Primary chain data available';
  check('test_fallback_case_shows_disclosure_banner',
    result.fallbackHtml.includes(disclosureText), result.fallbackHtml.slice(0, 300));
  // crc(100) -> '₹1.00 Cr' (ChainA's fy26 value, relabeled into the fy27 column)
  check('test_fallback_case_relabels_prior_fy_chain_a_value_into_table',
    result.fallbackHtml.includes('₹1.00 Cr'), result.fallbackHtml.slice(0, 400));
  check('test_real_data_case_shows_no_disclosure_banner',
    !result.realHtml.includes(disclosureText), result.realHtml.slice(0, 300));
  // crc(120) -> '₹1.20 Cr' (ChainA's real fy27 value, unrelabeled)
  check('test_real_data_case_uses_real_fy27_values_not_relabeled',
    result.realHtml.includes('₹1.20 Cr'), result.realHtml.slice(0, 400));
  check('test_live_fy26_shows_no_disclosure_banner_today',
    !result.liveFy26Html.includes('No data available') ? !result.liveFy26Html.includes(disclosureText) : true,
    result.liveFy26Html.slice(0, 200));
  check('test_live_fy27_shows_no_disclosure_banner_today',
    !result.liveFy27Html.includes(disclosureText), result.liveFy27Html.slice(0, 200));
  check('test_no_js_errors', errs.length === 0, errs);

  console.log(`\n  primary-cross-fy-fallback-disclosure tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
