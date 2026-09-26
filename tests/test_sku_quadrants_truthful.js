// SKU Portfolio Quadrants must not place SKUs from invented numbers.
//
// Found 2026-09-26 on main a3c6c72 (docs/VISUAL_REGISTRY.md section 5, never fixed):
// computeSKUQuadrants() used `Gross_Margin_Pct ?? 45` and `stores_count || 100`
// (and median fallbacks of 45 / 50). None of the 160,834 detail rows carries
// Gross_Margin_Pct or Units, and D.primary.stores_count is absent, so the
// Commercial Analytics tab plotted all 50 SKUs at exactly 45% margin and ROS 0
// under action labels "Core Driver (protect)" ... "Delist Review".
//
// Scenario 1 uses the committed data.js as is. Scenario 2 injects real-looking
// fields on a few rows in the browser only (never written to disk).
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && typeof buildAnalytics === 'function' && typeof REC !== 'undefined', { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  const r = await pg.evaluate(async () => {
    const wait = ms => new Promise(res => setTimeout(res, ms));
    const snap = async () => {
      destroyAnalyticsCharts(); buildAnalytics(); await wait(400);
      const el = document.getElementById('cvQuadrant');
      const c = window._chartQuadrant && window._chartQuadrant.canvas && el && el.contains(window._chartQuadrant.canvas)
        ? window._chartQuadrant : null;
      return { text: el ? el.innerText : null, chart: !!c,
               points: c ? c.data.datasets.map(d => ({ sku: d.label, x: d.data[0].x, y: d.data[0].y })) : [] };
    };
    const out = {};
    out.realHasMargin = REC.some(x => typeof x.Gross_Margin_Pct === 'number');
    out.realHasUnits = REC.some(x => typeof x.Units === 'number');
    out.realStores = D.primary ? D.primary.stores_count : undefined;
    out.real = await snap();

    // Scenario 2: every row of 6 top-NSV articles gets real fields; all other
    // articles stay missing. detail_records is article x chain x month, so an
    // article spans many rows -- it must be plotted once, not once per row.
    const arts = [...new Set(REC.filter(x => x.Article).slice().sort((a, b2) => (b2.NSV || 0) - (a.NSV || 0)).map(x => x.Article))].slice(0, 6);
    const given = {};
    arts.forEach((a, i) => { given[a] = 30 + i * 7; });
    const rows = REC.filter(x => x.Article in given);
    const saved = rows.map(x => ({ x, m: x.Gross_Margin_Pct, u: x.Units }));
    rows.forEach(x => { x.Gross_Margin_Pct = given[x.Article]; x.Units = 10; });
    const hadPrimary = !!D.primary, oldStores = hadPrimary ? D.primary.stores_count : undefined;
    if (!hadPrimary) D.primary = {};
    D.primary.stores_count = 250;
    out.given = given;
    out.partial = await snap();

    // Scenario 3: fields present but store count missing -> still not available (no 100-store guess).
    delete D.primary.stores_count;
    out.noStores = await snap();

    saved.forEach(s => { if (s.m === undefined) delete s.x.Gross_Margin_Pct; else s.x.Gross_Margin_Pct = s.m;
                         if (s.u === undefined) delete s.x.Units; else s.x.Units = s.u; });
    if (!hadPrimary) delete D.primary; else if (oldStores === undefined) delete D.primary.stores_count; else D.primary.stores_count = oldStores;
    destroyAnalyticsCharts(); buildAnalytics(); await wait(200);
    return out;
  });

  // Scenario 1: the committed data.js has none of the required fields.
  check('committed data.js has no Gross_Margin_Pct / Units / stores_count (precondition)',
        !r.realHasMargin && !r.realHasUnits && r.realStores == null, [r.realHasMargin, r.realHasUnits, r.realStores]);
  check('no data: no quadrant chart drawn', !r.real.chart, r.real.points.slice(0, 3));
  check('no data: card says Not available', /Not available/.test(r.real.text || ''), r.real.text);
  check('no data: card names every missing field',
        /Gross_Margin_Pct/.test(r.real.text || '') && /Units/.test(r.real.text || '') && /stores_count/.test(r.real.text || ''), r.real.text);

  // Scenario 2: only rows with real fields are plotted, at their own values.
  const pts = r.partial.points;
  check('partial: chart drawn', r.partial.chart);
  check('partial: only SKUs with real fields are plotted', pts.length > 0 && pts.every(p => p.sku in r.given), pts.map(p => p.sku));
  check('partial: each SKU is plotted once (rows grouped by article)',
        new Set(pts.map(p => p.sku)).size === pts.length && pts.length === Object.keys(r.given).length, pts.map(p => p.sku));
  check('partial: every margin is the SKU\'s own value (no 45 default)', pts.every(p => Math.abs(p.y - r.given[p.sku]) < 1e-9), pts);
  check('partial: ROS uses the real store count', pts.every(p => p.x > 0), pts.map(p => p.x));
  check('partial: coverage note says how many SKUs have the fields', /of \d[\d,]* SKU/.test(r.partial.text || ''), r.partial.text);

  // Scenario 3: fields present but store count missing.
  check('no store count: no chart, names stores_count', !r.noStores.chart && /stores_count/.test(r.noStores.text || ''), r.noStores.text);

  check('no JS errors', errs.length === 0, errs.slice(0, 3));
  console.log(`\n  sku-quadrants-truthful tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
