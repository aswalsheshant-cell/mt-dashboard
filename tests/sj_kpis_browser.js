// Sales Journey proxy KPIs: Numeric / Weighted Distribution (Inventory & Supply Health > TDP & Distribution),
// order-line value (Channel & Chain Performance > Primary Sales) and the promotion break-even calculator
// (Demand & S&OP Planning > Promotional Impact). Checks they render, filters and the calculator work, and there is no NaN/undefined.
const { launchChromium } = require('./browser_launch');
(async () => {
  const b = await launchChromium();
  const pg = await b.newPage({ viewport: { width: 1400, height: 1000 } });
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  pg.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForTimeout(2000);
  const fail = [];
  const bad = t => /\bNaN\b|\bundefined\b|\[object Object\]/.test(t);

  // 1. distribution
  await pg.evaluate(() => { show('inventory-health'); switchInventorySubview('tdp'); });
  await pg.waitForTimeout(800);
  let txt = await pg.evaluate(() => document.getElementById('tab-inventory-health').innerText);
  if (!/Numeric & Weighted Distribution/.test(txt)) fail.push('distribution section missing');
  if (!/not Nielsen/i.test(txt)) fail.push('proxy label missing');
  if (bad(txt)) fail.push('NaN/undefined in distribution');
  const gapAll = await pg.evaluate(() => parseInt(document.getElementById('sjGNote').textContent, 10));
  await pg.selectOption('#sjGChain', 'D-Mart');
  const gapDm = await pg.evaluate(() => parseInt(document.getElementById('sjGNote').textContent, 10));
  if (!(gapAll > 0 && gapDm > 0 && gapDm < gapAll)) fail.push(`gap filter not working (all ${gapAll}, D-Mart ${gapDm})`);
  const ndRows = await pg.evaluate(() => document.querySelectorAll('#sjDTbl tbody tr').length);
  if (!(ndRows > 5)) fail.push('ND/WD table empty');
  // every ND and WD shown is between 0 and 100
  const range = await pg.evaluate(() => [...document.querySelectorAll('#sjDTbl tbody tr')].every(tr => { const c = tr.children; const nd = parseFloat(c[4].textContent), wd = parseFloat(c[5].textContent); return nd >= 0 && nd <= 100 && wd >= 0 && wd <= 100; }));
  if (!range) fail.push('ND/WD outside 0-100');

  // 2. order-line value
  await pg.evaluate(() => { show('channel-dynamics'); });
  await pg.waitForTimeout(800);
  txt = await pg.evaluate(() => document.getElementById('tab-channel-dynamics').innerText);
  if (!/Order-line value \(proxy for average order value\)/.test(txt)) fail.push('order-line value section missing');
  if (!/Not value per order/i.test(txt)) fail.push('order-line caveat missing');
  if (bad(txt)) fail.push('NaN/undefined in primary sales');

  // 3. break-even calculator
  await pg.evaluate(() => { show('demand-planning'); switchDemandSubview('promo'); });
  await pg.waitForTimeout(800);
  txt = await pg.evaluate(() => document.getElementById('tab-demand-planning').innerText);
  if (!/Promotion break-even \(calculator\)/.test(txt)) fail.push('break-even section missing');
  if (bad(txt)) fail.push('NaN/undefined in promo');
  await pg.fill('#sjBeD', '30'); await pg.fill('#sjBeFu', '100'); await pg.fill('#sjBeM', '60'); await pg.fill('#sjBeR', '1');
  const out1 = await pg.evaluate(() => document.getElementById('sjBeOut').textContent);
  if (!/\+100%/.test(out1)) fail.push('calculator: 30/(60-30) should be +100%, got: ' + out1);     // 30 / (60 - 30) = 100%
  await pg.fill('#sjBeD', '70');
  const out2 = await pg.evaluate(() => document.getElementById('sjBeOut').textContent);
  if (!/no volume uplift breaks even/.test(out2)) fail.push('calculator: discount above margin should never break even, got: ' + out2);
  await pg.fill('#sjBeD', '');
  const out3 = await pg.evaluate(() => document.getElementById('sjBeOut').textContent);
  if (!/Enter all four numbers/.test(out3)) fail.push('calculator: blank input not handled');
  await pg.selectOption('#sjBeC', 'DMart');
  const tbl = await pg.evaluate(() => document.getElementById('sjBeTbl').innerText);
  if (bad(tbl) || tbl.length < 50) fail.push('break-even table empty or NaN');

  // 4. prescriptive priority actions on the Executive Cockpit
  await pg.evaluate(() => { show('executive-cockpit'); });
  await pg.waitForTimeout(800);
  txt = await pg.evaluate(() => document.getElementById('tab-executive-cockpit').innerText);
  if (!/What should we do: priority actions/.test(txt)) fail.push('priority actions card missing');
  if (!/Rule used/.test(txt) || !/Chain KAM/.test(txt)) fail.push('priority actions lack rule or owner');
  if (bad(txt)) fail.push('NaN/undefined in cockpit');

  if (errs.length) fail.push(...errs);
  if (process.env.SHOT) await pg.screenshot({ path: process.env.SHOT, fullPage: false });
  console.log(fail.length ? 'FAIL ' + fail.join(' | ') : `PASS gap lines ${gapAll} (D-Mart ${gapDm}), ND/WD rows ${ndRows}`);
  await b.close();
  process.exit(fail.length ? 1 : 0);
})();
