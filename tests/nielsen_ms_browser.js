// Browser check for the Nielsen market-share dashboard (templates/dashboard_template.html, built).
// Usage: node tests/nielsen_ms_browser.js <built.html> [screenshot-dir]
// Fails (exit 1) on a JS error, NaN / undefined / [object Object] in the page, a wrong
// Both / Facewash / Shampoo layout, or a figure that does not match the real data.
const fs = require('fs');
const path = require('path');
const { launchChromium } = require('./browser_launch');

const htmlPath = path.resolve(process.argv[2] || '');
const shotDir = process.argv[3] ? path.resolve(process.argv[3]) : null;
// 'jul' (default) = the July payload, 'aug' = the governed Aug-26 Nielsen payload.
const mode = process.argv[4] || 'jul';
const EXPECT = {
  jul: { both: ['+2.4pp YoY', '+6.4pp YoY', '+25.6% YoY', '+18% YoY', '7,025', '#4', 'same as last yr', '₹0.82 Cr', '₹2.76 Cr', 'Honasa Facewash share: 12.2%'],
         sh: ['pack structure', '73.1%', 'distribution cannot be sized', '+91'], opp: ['₹5.1 Cr', '₹2.8 Cr', '7,280 more stores'], stale: true },
  aug: { both: ['+2.6pp YoY', '+5.9pp YoY', '+25.2% YoY', '+40.7% YoY', '13,132', '#4', '₹0.82 Cr', 'Honasa Facewash share: 13.7%', 'Market: IN URB MT', '+86 bps YoY', '8,966', '₹1.80 Cr', 'Reach is the gap'],
         sh: ['pack structure', '83.1%', '81.8', 'reach is the gap'], opp: ['Shampoo reach', 'Facewash: +1 pp of share'], stale: false }
}[mode];
const failures = [];
const check = (cond, msg) => { if (!cond) failures.push(msg); };

(async () => {
  if (!fs.existsSync(htmlPath)) { console.error('built html not found: ' + htmlPath); process.exit(2); }
  // The build references chart.umd.js next to the page.
  const lib = path.join(path.dirname(htmlPath), 'chart.umd.js');
  if (!fs.existsSync(lib)) fs.copyFileSync(path.join(__dirname, '..', 'dashboard', 'chart.umd.js'), lib);

  const browser = await launchChromium();
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error' && !/fonts\.googleapis|ERR_|Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
  await page.goto('file://' + htmlPath);
  await page.waitForSelector('#ins-grid .ins');

  const text = async () => page.evaluate(() => document.body.innerText);
  const vis = async sel => page.evaluate(s => { const e = document.querySelector(s); return !!e && getComputedStyle(e).display !== 'none' && e.offsetHeight > 0; }, sel);
  const clean = async label => {
    const t = await text();
    for (const bad of ['NaN', 'undefined', '[object Object]', 'Infinity']) check(!t.includes(bad), `${label}: page text contains ${bad}`);
    return t;
  };

  // ---- Both
  let t = await clean('both');
  check(await vis('#blk-fw') && await vis('#blk-sh'), 'both: both blocks must be visible');
  const boxes = await page.evaluate(() => ['#blk-fw', '#blk-sh'].map(s => { const r = document.querySelector(s).getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width }; }));
  check(Math.abs(boxes[0].y - boxes[1].y) < 6 && boxes[1].x > boxes[0].x, 'both: Facewash and Shampoo must sit side by side at 1280px');
  check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2), 'both: horizontal overflow');
  check(t.includes('Pond\'s') && !t.includes("Pond'S"), "brand name Pond's must not be mangled");
  // figures computed from the real files (Jul 26 vs Jul 25)
  for (const needle of EXPECT.both) {
    check(t.includes(needle), `both: expected "${needle}"`);
  }
  for (const stale of EXPECT.stale ? ['+10.1pp', '+32.3%', '+11.6%', '+1 vs'] : []) check(!t.includes(stale), `both: stale figure ${stale}`);
  const insBoth = await page.$$eval('#ins-grid .ins', n => n.length);
  check(insBoth >= 6, `both: expected >=6 insights, got ${insBoth}`);
  if (shotDir) { fs.mkdirSync(shotDir, { recursive: true }); await page.screenshot({ path: path.join(shotDir, 'both.png'), fullPage: true }); }

  // ---- Facewash only
  await page.click('#seg button[data-view="fw"]');
  t = await clean('fw');
  check(await vis('#blk-fw') && !(await vis('#blk-sh')), 'fw: only the Facewash block');
  check(/share per wd point/i.test(t) && /pack split/i.test(t), 'fw: detail sections missing');
  if (shotDir) await page.screenshot({ path: path.join(shotDir, 'facewash.png'), fullPage: true });

  // ---- Shampoo only
  await page.click('#seg button[data-view="sh"]');
  t = await clean('sh');
  check(await vis('#blk-sh') && !(await vis('#blk-fw')), 'sh: only the Shampoo block');
  for (const needle of EXPECT.sh) check(t.toLowerCase().includes(needle), `sh: expected "${needle}"`);
  if (EXPECT.stale) check(!t.includes('41.2%') && !t.includes('41.8%'), 'sh: the unsupported 41% pack figure must not appear');
  if (shotDir) await page.screenshot({ path: path.join(shotDir, 'shampoo.png'), fullPage: true });

  // ---- Opportunity
  await page.click('.tab-btn:nth-child(2)');
  await page.waitForSelector('#opp-grid .opp');
  t = await clean('opportunity');
  for (const needle of EXPECT.opp) check(t.includes(needle), `opportunity: expected "${needle}"`);
  if (EXPECT.stale) check(!t.includes('₹6.2 Cr') && !t.includes('₹3.8 Cr'), 'opportunity: stale tiles must not appear');
  if (shotDir) await page.screenshot({ path: path.join(shotDir, 'opportunity.png'), fullPage: true });

  // ---- Tracker + dark theme
  await page.click('.tab-btn:nth-child(3)');
  await clean('tracker');
  await page.click('.theme-btn');
  await clean('dark');

  // ---- Chains & Packs
  await page.click('.tab-btn:nth-child(4)');
  t = await clean('chains');
  if (mode === 'aug') {
    for (const needle of ['Which chains carried the growth', 'Dmart', 'Not present', 'Under-indexed', 'Does not tie', 'Maharashtra', 'Named plays', 'States present'])
      check(t.toLowerCase().includes(needle.toLowerCase()), `chains: expected "${needle}"`);
    const rows = await page.$$eval('#fwp-tbody tr', n => n.length);
    check(rows >= 5, `chains: facewash pack table has ${rows} rows`);
    if (shotDir) await page.screenshot({ path: path.join(shotDir, 'chains.png'), fullPage: true });
  }

  // ---- narrow screen
  await page.setViewportSize({ width: 420, height: 800 });
  await page.click('.tab-btn:nth-child(1)');
  check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 8), 'phone width: horizontal overflow');

  check(errors.length === 0, 'JS errors: ' + errors.join(' | '));
  await browser.close();
  if (failures.length) { console.error('FAIL\n- ' + failures.join('\n- ')); process.exit(1); }
  console.log('OK: Both / Facewash / Shampoo / Opportunity / Tracker, ' + insBoth + ' insights in Both, 0 JS errors');
})().catch(e => { console.error(e); process.exit(1); });
