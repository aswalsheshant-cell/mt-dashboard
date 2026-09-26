// Regression test: the Channel & Chain "Top Chains by Primary NSV" table must
// not hide any chain -- "Unmapped Chain" or a negative return/credit chain -- so the rows shown add up
// to the FY Primary total (owner decision 2026-09-26, option A: show the row).
// Before the fix the table hid Unmapped Chain (FY27 +Rs 10.13 L) and every
// negative return/credit chain (FY26 Apna Klub -0.91 L; FY27 Relay, Broadway,
// Sohum Shoppe -4.31 L): FY26 rows summed to 32,901.27 vs 32,900.36 total,
// FY27 to 22,233.77 vs 22,239.59.
// Display values are rounded (Rs Cr, 2 dp), so the check compares the rendered
// chain NAMES with the source data and sums the source values of those rows.
// Needs the dashboard served at 127.0.0.1:$SWEEP_PORT (default 8899).
const { chromium } = require('/home/user/mt-dashboard/node_modules/playwright');

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && typeof consolidateChains === 'function', { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  for (const fy of ['FY26', 'FY27']) {
    await pg.evaluate((f) => { F.FY = [f]; if (typeof applyFilters === 'function') applyFilters(); show('channel-dynamics'); }, fy);
    await pg.waitForTimeout(400);
    const r = await pg.evaluate((f) => {
      // Source rows exactly as the view reads them, before any display filter.
      const src = f === 'FY27'
        ? consolidateChains(FPX('FY27').by_chain).map(c => ({ name: c.name, v: c.nsv }))
        : (D.primary.by_chain || []).map(c => ({ name: c.name, v: c.fy26 }));
      const total = f === 'FY27' ? FPX('FY27').nsv : D.primary.nsv_fy26;
      const tab = document.getElementById('tab-channel-dynamics');
      const table = tab && tab.querySelector('table.tbl');   // first table = Top Chains
      const shown = table ? [...table.querySelectorAll('tbody tr')].map(tr => tr.cells[0].innerText.trim()) : [];
      const byName = Object.fromEntries(src.map(c => [c.name, c.v]));
      const expected = src.filter(c => (c.v || 0) !== 0).map(c => c.name).sort();   // negatives too (FM-20)
      const shownSum = shown.reduce((a, n) => a + (byName[n] || 0), 0);
      const unmapped = byName['Unmapped Chain'] || 0;
      return { total, shownSum, unmapped, shown: shown.slice().sort(), expected,
               missing: expected.filter(n => !shown.includes(n)) };
    }, fy);
    check(`${fy}: every non-zero chain is shown`, r.missing.length === 0, r.missing);
    check(`${fy}: shown chains add up to the FY total`, Math.abs(r.shownSum - r.total) < 0.01,
          { shown: +r.shownSum.toFixed(2), total: r.total });
    if (r.unmapped > 0) check(`${fy}: Unmapped Chain row is visible`, r.shown.includes('Unmapped Chain'), r.unmapped);
  }
  check('no JS errors', errs.length === 0, errs.slice(0, 3));
  console.log(`\n  unmapped-chain-visible tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
