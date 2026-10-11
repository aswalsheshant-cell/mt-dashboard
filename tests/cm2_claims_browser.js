// P&L tab: distributor claims applied chain-wise, with the unresolved items listed.
// Usage: serve dashboard/ on SWEEP_PORT (default 8899), then: node tests/cm2_claims_browser.js
const { launchChromium } = require('./browser_launch');
(async () => {
  const b = await launchChromium();
  const pg = await b.newPage({ viewport: { width: 1400, height: 1800 } });
  const errs = [];
  pg.on('pageerror', e => errs.push(e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForTimeout(2500);
  let bad = 0;
  const check = (ok, msg) => { if (!ok) { bad++; console.log('  FAIL ' + msg); } else console.log('  ok   ' + msg); };
  for (const fy of ['FY27', null]) {
    await pg.evaluate(f => { F.FY = f ? [f] : []; if (typeof applyFilters === 'function') applyFilters(); }, fy);
    await pg.evaluate(() => show('pnl'));
    await pg.waitForTimeout(700);
    const t = await pg.evaluate(() => document.getElementById('tab-pnl').innerText);
    const L = fy || 'no filter';
    check(t.includes('of which distributor claim'), `${L}: claim column in the chain CM2 table`);
    check(t.includes('Distributor claims applied chain-wise'), `${L}: unresolved panel shown`);
    check(/ALLOCATED_PROVISIONAL/.test(t) && /approval reference PENDING/.test(t), `${L}: provisional and approval pending stated`);
    check(/Spar: claim not applied/.test(t) && /Ratnadeep: no month/.test(t), `${L}: Spar and Ratnadeep listed as open`);
    check(/Driver aliases awaiting Finance decision\s+7 of 7/.test(t), `${L}: 7 pending aliases listed`);
    check(!/\bNaN\b|\bundefined\b|\[object Object\]/.test(t), `${L}: no NaN / undefined`);
  }
  check(errs.length === 0, `no JS errors (${errs.length})`);
  await b.close();
  process.exit(bad ? 1 : 0);
})();
