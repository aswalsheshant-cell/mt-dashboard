// Three defects from a user screenshot of Commercial Analytics (2026-09-26, main f3b9d64):
//  1. The header alert badge never updated: alert_controller.js looked for
//     'nav .alert-badge' but the badge sits outside <nav>, so it showed the
//     hard-coded red "0" forever -- even with critical alerts in the feed.
//  2. At a zoomed/narrower window the "FY27 cohort -- sample launches" table
//     pushed its .g2 grid column (1fr = minmax(auto,1fr)) past the viewport,
//     giving the whole page a horizontal scrollbar.
//  3. The YoY NPI KPI printed "Not comparable -- see caveat below" in the 26px
//     value font (three lines); the value is now "–" with the reason underneath.
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }
  const url = `http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`;
  const errs = [];

  // 1. Alert badge follows the feed state.
  const pg = await b.newPage();
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(url, { waitUntil: 'load' });
  await pg.waitForFunction(() => window.AlertController && window.alertsFeedStatus && window.alertsFeedStatus !== 'loading', { timeout: 30000 });
  const badge = await pg.evaluate(() => {
    const el = () => document.querySelector('.alert-badge');
    const read = () => { const e = el(); const cs = getComputedStyle(e);
      return { text: e.textContent.trim(), shown: cs.display !== 'none' && cs.visibility !== 'hidden', title: e.getAttribute('title') || '' }; };
    const out = { initial: read() };
    const saveFeed = window.alertsFeed, saveStatus = window.alertsFeedStatus;
    window.alertsFeed = { metadata: { total_alerts: 3, critical_count: 3, warning_count: 0 }, alerts: [] };
    window.alertsFeedStatus = 'loaded'; AlertController.updateNavBadge(); out.three = read();
    window.alertsFeed = { metadata: { total_alerts: 0, critical_count: 0, warning_count: 0 }, alerts: [] };
    AlertController.updateNavBadge(); out.zero = read();
    window.alertsFeedStatus = 'error'; AlertController.updateNavBadge(); out.error = read();
    window.alertsFeed = saveFeed; window.alertsFeedStatus = saveStatus; AlertController.updateNavBadge();
    out.realCritical = (saveFeed && saveFeed.metadata && saveFeed.metadata.critical_count) || 0;
    return out;
  });
  check('badge shows the critical count (3) from the feed', badge.three.shown && badge.three.text === '3', badge.three);
  check('badge hidden when the feed is loaded with 0 critical alerts (no red "0")', !badge.zero.shown, badge.zero);
  check('badge on a failed feed load says so, never a count', badge.error.shown && badge.error.text !== '0' && /fail/i.test(badge.error.title), badge.error);
  check('badge after page load matches the real feed (no hard-coded "0")',
        badge.realCritical > 0 ? (badge.initial.shown && badge.initial.text === String(badge.realCritical)) : !badge.initial.shown, badge);
  await pg.close();

  // 2 + 3. Commercial Analytics at a zoomed width (~150% on a 1850px screen).
  const p2 = await b.newPage({ viewport: { width: 1230, height: 700 } });
  p2.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await p2.goto(url, { waitUntil: 'load' });
  await p2.waitForFunction(() => typeof buildAnalytics === 'function' && typeof D !== 'undefined', { timeout: 30000 });
  const lay = await p2.evaluate(async () => {
    const btn = [...document.querySelectorAll('button,a,[data-tab]')].find(e => /Commercial Analytics/.test(e.textContent));
    if (btn) btn.click();
    await new Promise(r => setTimeout(r, 2500));
    const W = document.documentElement.clientWidth;
    const over = [...document.querySelectorAll('#tab-analytics .card')].filter(e => e.offsetParent && e.getBoundingClientRect().right > W + 1)
      .map(e => ({ h3: (e.querySelector('h3') || {}).innerText, right: Math.round(e.getBoundingClientRect().right) }));
    const k = [...document.querySelectorAll('#tab-analytics .kpi')].find(x => /YoY NPI NSV growth/i.test(x.querySelector('.lab').textContent));
    return { clicked: !!btn, W, scrollW: document.documentElement.scrollWidth, over,
             kpi: k ? { val: k.querySelector('.val').textContent.trim(), sub: k.innerText } : null };
  });
  check('Commercial Analytics opened', lay.clicked);
  check('no card wider than the window at 1230px (no page-level horizontal scroll)', lay.scrollW <= lay.W && lay.over.length === 0, lay);
  check('YoY NPI KPI value is "–" (reason shown underneath, not as the number)',
        lay.kpi && lay.kpi.val === '–' && /Not comparable|no prior cohort/i.test(lay.kpi.sub), lay.kpi);
  await p2.close();

  check('no JS errors', errs.length === 0, errs.slice(0, 3));
  console.log(`\n  alert-badge-and-npd-layout tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
