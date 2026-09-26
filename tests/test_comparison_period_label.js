// Performance & Comparison, FY27 chain/brand view: the prior-year series must be
// labelled with ITS OWN months.
//
// Found 2026-09-26 on main a39d55c from a user screenshot: title and legend read
// "FY26 Apr-26–Aug-26 vs FY27 Apr-26–Aug-26". The values were right -- the blue
// bars are FY26 Apr'25–Aug'25 (DMart Rs44.09 Cr = its Apr–Aug'25 detail sum; full
// FY26 is Rs121.91 Cr) -- but buildComparison() built one month label from FY27's
// months_canon and put it on both years, so the prior year read as the same
// calendar months as the current one.
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && typeof buildComparison === 'function', { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  const out = await pg.evaluate(async () => {
    const res = {};
    for (const dim of ['Chain', 'Brand']) {
      F.FY = ['FY27']; cmpDim = dim; buildComparison();
      await new Promise(r => setTimeout(r, 500));
      const c = charts.filter(x => x.canvas && x.canvas.id === 'cmpChart' && document.body.contains(x.canvas)).pop();   // the live chart, not a stale one from the previous dimension
      const fp = FPX('FY27');
      const cov = new Set(fp.months_covered);
      const key = dim === 'Chain' ? 'Chain' : 'Brand';
      const prev = {};
      (D.detail_records || []).forEach(r => { if (r.FY === 'FY26' && cov.has(r.Month)) prev[r[key]] = (prev[r[key]] || 0) + (r.NSV || 0); });
      const top = c ? c.data.labels.slice(0, 5) : [];
      res[dim] = { title: document.querySelector('#tab-comparison .card h3')?.innerText || '',
                   legend: c ? c.data.datasets.map(d => d.label) : [], canon: fp.months_canon,
                   blueOk: c ? top.every((n, i) => Math.abs((c.data.datasets[0].data[i] || 0) - (prev[n] || 0)) < 0.01) : false };
    }
    F.FY = []; cmpDim = 'Chain'; buildComparison();
    return res;
  });

  const shift = l => l.replace(/-(\d{2})$/, (m, y) => '-' + String((+y + 99) % 100).padStart(2, '0'));
  for (const [dim, r] of Object.entries(out)) {
    const first = r.canon[0], last = r.canon[r.canon.length - 1];
    const prevLbl = `FY26 ${shift(first)}–${shift(last)}`, currLbl = `FY27 ${first}–${last}`;
    check(`${dim}: prior-year legend names its own months (${prevLbl})`, r.legend[0] === prevLbl, r.legend);
    check(`${dim}: current-year legend unchanged (${currLbl})`, r.legend[1] === currLbl, r.legend);
    check(`${dim}: title reads ${prevLbl} vs ${currLbl}`, r.title.includes(`${prevLbl} vs ${currLbl}`), r.title);
    check(`${dim}: blue bars are the prior FY's same months (values unchanged)`, r.blueOk);
  }
  check('no JS errors', errs.length === 0, errs.slice(0, 3));
  console.log(`\n  comparison-period-label tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
