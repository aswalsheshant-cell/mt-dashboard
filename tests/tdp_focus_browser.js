// Opens Inventory & Supply Health > TDP & Distribution and checks the article focus list renders, filters and has no NaN/undefined.
const { launchChromium } = require('./browser_launch');
(async () => {
  const b = await launchChromium();
  const pg = await b.newPage({ viewport: { width: 1400, height: 1000 } });
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  pg.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForTimeout(2000);
  await pg.evaluate(() => { show('inventory-health'); switchInventorySubview('tdp'); });
  await pg.waitForTimeout(800);
  const txt = await pg.evaluate(() => document.getElementById('tab-inventory-health').innerText);
  const fail = [];
  if (!/Article focus list/.test(txt)) fail.push('focus card missing');
  if (/\bNaN\b|\bundefined\b|\[object Object\]/.test(txt)) fail.push('NaN/undefined text');
  const cnt = () => pg.evaluate(() => parseInt(document.getElementById('tfNote').textContent, 10));
  const all = await cnt();
  await pg.selectOption('#tfSel', 'NPI_NEW_TO_CHAIN');
  const npi = await cnt();
  if (!(all > 0 && npi > 0 && npi < all)) fail.push(`filter not working (all ${all}, npi ${npi})`);
  if (errs.length) fail.push(...errs);
  if (process.env.SHOT) await pg.screenshot({ path: process.env.SHOT, fullPage: false });
  console.log(fail.length ? 'FAIL ' + fail.join(' | ') : `PASS rows ${all}, new-to-chain rows ${npi}`);
  await b.close();
  process.exit(fail.length ? 1 : 0);
})();
