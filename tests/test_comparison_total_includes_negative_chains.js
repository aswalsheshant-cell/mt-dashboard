// Regression test for a defect found 2026-09-27 from a live screenshot:
// Performance & Comparison's "Total (FY27 ...)" card read Rs 222.44 Cr while
// the governed FY27 article-wise Primary total is Rs 222.40 Cr
// (detail_meta.fyx_primary.FY27.nsv = 22,239.59 L). buildComparison() kept
// only chains with NSV > 0, so 3 chains with net returns (Sohum Shoppe,
// Broadway, Relay; -4.31 L together) fell out of both the "Chains Compared"
// count and the Total. The same filter dropped one all-negative chain in the
// FY25/FY26 view. Fixed by keeping every chain with real non-zero NSV.
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
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

  const readCards = async (fy) => {
    await pg.evaluate((f) => { F.FY = f ? [f] : []; if (typeof applyFilters === 'function') applyFilters(); }, fy);
    await pg.evaluate(() => show('comparison'));
    await pg.waitForTimeout(300);
    return pg.evaluate(() => {
      const cards = [...document.querySelectorAll('#tab-comparison .kpis .kpi')].map(k => k.innerText);
      return { cards };
    });
  };

  // Governed totals straight from data.js, in Crore, as crc() renders them.
  const gov = await pg.evaluate(() => {
    const fp = D.detail_meta.fyx_primary.FY27;
    return {
      fy27Cr: (fp.nsv / 100).toFixed(2),
      fy27Chains: consolidateChains(fp.by_chain).filter(x => x.nsv != null && x.nsv !== 0).length,
      fy27Negative: fp.by_chain.filter(x => x.nsv < 0).length,
      fy26Cr: ((D.primary.by_chain || []).reduce((s, x) => s + (x.fy26 || 0), 0) / 100).toFixed(2),
    };
  });

  check('test_premise_fy27_has_net_negative_chains', gov.fy27Negative > 0, gov);

  const c27 = await readCards('FY27');
  const tot27 = c27.cards.find(t => /Total/i.test(t)) || '';
  const cmp27 = c27.cards.find(t => /Compared/i.test(t)) || '';
  check('test_fy27_total_card_equals_governed_fy27_primary', tot27.includes(gov.fy27Cr), { card: tot27, expected: gov.fy27Cr });
  check('test_fy27_chains_compared_includes_net_negative_chains', cmp27.includes(String(gov.fy27Chains)), { card: cmp27, expected: gov.fy27Chains });

  const c26 = await readCards('FY26');
  const tot26 = c26.cards.find(t => /Total/i.test(t)) || '';
  check('test_fy26_total_card_equals_governed_fy26_primary', tot26.replace(/,/g, '').includes(gov.fy26Cr), { card: tot26, expected: gov.fy26Cr });

  check('test_no_js_errors', errs.length === 0, errs);
  console.log(`\n  comparison-total-includes-negative-chains tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
