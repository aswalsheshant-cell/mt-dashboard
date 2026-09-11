const { chromium } = require('/home/user/mt-dashboard/node_modules/playwright');
(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  pg.on('console', m => { if (m.type() === 'error') errs.push('CONSOLE: ' + m.text()); });
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForTimeout(2500);

  const TABS = await pg.evaluate(() => TABS.map(t => t[0]));
  const FYS  = [null, 'FY25', 'FY26', 'FY27'];
  let bad = 0, n = 0;
  for (const fy of FYS) {
    await pg.evaluate((f) => {
      F.FY = f ? [f] : [];
      if (typeof applyFilters === 'function') applyFilters();
    }, fy).catch(()=>{});
    for (const t of TABS) {
      n++;
      const before = errs.length;
      await pg.evaluate((id) => show(id), t);
      await pg.waitForTimeout(220);
      const txt = await pg.evaluate((id) => {
        const el = document.getElementById('tab-' + id);
        return el ? el.innerText : '';
      }, t);
      const hits = [];
      if (/\bNaN\b/.test(txt)) hits.push('NaN');
      if (/\bundefined\b/.test(txt)) hits.push('undefined');
      if (/\[object Object\]/.test(txt)) hits.push('[object Object]');
      const newErrs = errs.length - before;
      if (hits.length || newErrs) {
        bad++;
        console.log(`  FAIL ${String(fy||'no-filter').padEnd(10)} ${t.padEnd(20)} ${hits.join(',')||''} ${newErrs?`(+${newErrs} js err)`:''}`);
        if (newErrs) errs.slice(before).forEach(e => console.log('        ' + e.slice(0,160)));
      }
    }
  }
  console.log(`\n  states swept: ${n}  |  failing: ${bad}  |  total JS errors: ${errs.length}`);
  await b.close();
  process.exit(bad || errs.length ? 1 : 0);
})();
