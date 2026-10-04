// Executive Cockpit and Inventory & Supply Health must show the same store universe, tentative chains and NA for FSN.
// Usage: node tests/store_universe_browser.js   (opens dashboard/index.html from disk)
const path = require('path');
const { launchChromium } = require('./browser_launch');
(async () => {
  const b = await launchChromium();
  const p = await b.newPage({ viewport: { width: 1500, height: 900 } });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + path.resolve(__dirname, '..', 'dashboard', 'index.html'));
  await p.waitForTimeout(3500);
  const fails = [], seen = {};
  for (const t of ['executive-cockpit', 'inventory-health']) {
    await p.evaluate(id => show(id), t);
    await p.waitForTimeout(300);
    const r = await p.evaluate(id => {
      const e = document.getElementById('tab-' + id), txt = e.innerText;
      const k = [...e.querySelectorAll('.kpi,.kpi-card')].map(x => x.innerText.replace(/\n+/g, ' | ')).find(x => /ACTIVE MT STORES/i.test(x));
      return { strip: (txt.match(/Store universe:[^\n]*/) || [])[0], kpi: k, txt };
    }, t);
    seen[t] = r;
    if (!r.strip || !/stores in the store master/.test(r.strip) || !/tentative/.test(r.strip)) fails.push(`${t}: universe line missing`);
    if (!r.kpi) fails.push(`${t}: Active MT Stores tile missing`);
    for (const bad of ['NaN', 'undefined', '[object Object]']) if (r.txt.includes(bad)) fails.push(`${t}: ${bad}`);
  }
  const num = s => (s.match(/ACTIVE MT STORES \| ([\d,]+)/i) || [])[1];
  if (num(seen['executive-cockpit'].kpi || '') !== num(seen['inventory-health'].kpi || '')) fails.push('the two tabs show different store counts');
  if (seen['executive-cockpit'].strip !== seen['inventory-health'].strip) fails.push('the universe line differs between tabs');
  const inv = seen['inventory-health'].txt;
  if (!/Reliance Retail\t[\d,–]+\t~1,000 \(tentative\)/.test(inv)) fails.push('Reliance Retail should read ~1,000 (tentative)');
  if (!/More Retail\t[\d,–]+\t~400 \(tentative\)/.test(inv)) fails.push('More Retail should read ~400 (tentative)');
  if (!/Nykaa \(FSN\)\t[\d,–]+\tNA\t/.test(inv)) fails.push('Nykaa (FSN) should read NA');
  if (errs.length) fails.push('JS errors: ' + errs.join(' | '));
  await b.close();
  if (fails.length) { console.error('FAIL\n- ' + fails.join('\n- ')); process.exit(1); }
  console.log('OK: same store universe in Executive Cockpit and Inventory & Supply Health, 0 JS errors');
})().catch(e => { console.error(e); process.exit(1); });
