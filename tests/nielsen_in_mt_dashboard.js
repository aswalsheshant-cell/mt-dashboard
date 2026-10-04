// The MT dashboard's Demand & S&OP > Market Share view shows the governed Nielsen cut.
// Usage: SWEEP_PORT=8899 node tests/nielsen_in_mt_dashboard.js   (dashboard/ served over HTTP)
const { launchChromium } = require('./browser_launch');
(async () => {
  const b = await launchChromium();
  const pg = await b.newPage({ viewport: { width: 1400, height: 900 } });
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  pg.on('console', m => { if (m.type() === 'error' && !/Failed to load resource|fonts\./.test(m.text())) errs.push('CONSOLE: ' + m.text()); });
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForTimeout(2500);
  const fails = [];
  for (const fy of [null, 'FY25', 'FY26', 'FY27']) {
    await pg.evaluate(f => { F.FY = f ? [f] : []; if (typeof applyFilters === 'function') applyFilters(); }, fy);
    await pg.evaluate(() => show('demand-planning'));
    await pg.evaluate(() => switchDemandSubview('market-share'));
    await pg.waitForTimeout(400);
    const t = await pg.evaluate(() => document.getElementById('tab-demand-planning').innerText);
    for (const bad of ['NaN', 'undefined', '[object Object]']) if (t.includes(bad)) fails.push(`${fy || 'no-filter'}: ${bad}`);
    for (const need of ['Competitive Market Share', 'IN URB MT', 'Which chains carried the growth', 'packs: where we are present and not present', 'Dmart'])
      if (!t.toLowerCase().includes(need.toLowerCase())) fails.push(`${fy || 'no-filter'}: missing "${need}"`);
    if (!/12\.8%/.test(t)) fails.push(`${fy || 'no-filter'}: facewash share 12.8% not shown`);
    const canv = await pg.$('#nielsenTrend');
    if (!canv) fails.push(`${fy || 'no-filter'}: trend chart canvas missing`);
  }
  if (process.argv[2]) await pg.screenshot({ path: process.argv[2], fullPage: true });
  if (errs.length) fails.push('JS errors: ' + errs.join(' | '));
  await b.close();
  if (fails.length) { console.error('FAIL\n- ' + fails.join('\n- ')); process.exit(1); }
  console.log('OK: Market Share view shows Nielsen cut in all 4 FY states, 0 JS errors');
})().catch(e => { console.error(e); process.exit(1); });
