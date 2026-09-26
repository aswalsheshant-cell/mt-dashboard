// Regression test: a failed alerts_feed.json load must not look like a healthy,
// empty alert feed (old PR #156, rebuilt on main 8ba13f8).
// Before the fix, index.html did fetch('alerts_feed.json')...catch(()=>{}), so a
// 404 or network error left the default empty feed in place and the Operational
// Alerts tab said "No active alerts. All metrics within thresholds." with 0 in
// every KPI card -- a false all-clear.
// Cases: feed fails (404, aborted), feed genuinely empty, and the tab opened
// while the fetch is still pending (must repaint when it settles).
// Needs the dashboard served at 127.0.0.1:$SWEEP_PORT (default 8899).
const { launchChromium } = require('./browser_launch');   // shared launcher (PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH)
const BASE = `http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`;
const ALL_CLEAR = 'No active alerts. All metrics within thresholds.';
const EMPTY = JSON.stringify({ metadata: { total_alerts: 0, critical_count: 0, warning_count: 0 }, alerts: [] });

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log(`  PASS ${name}`); }
  else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
}

async function openAlerts(b, route) {
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push(e.message));
  let release;
  const held = new Promise(r => { release = r; });
  await pg.route('**/alerts_feed.json', async rt => {
    if (route === 'abort') return rt.abort();
    if (route === '404') return rt.fulfill({ status: 404, body: 'not found' });
    if (route === 'empty') return rt.fulfill({ status: 200, contentType: 'application/json', body: EMPTY });
    if (route === 'held') { await held; return rt.fulfill({ status: 404, body: 'not found' }); }
  });
  await pg.goto(BASE, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof show === 'function' && window.AlertController, { timeout: 30000 });
  if (route !== 'held') await pg.waitForTimeout(300);   // let the fetch settle
  await pg.evaluate(() => show('alerts'));
  await pg.waitForTimeout(200);
  const read = () => pg.evaluate(() => {
    const t = document.getElementById('tab-alerts');
    return { text: t ? t.innerText : '', status: window.alertsFeedStatus };
  });
  return { pg, errs, read, release };
}

(async () => {
  const b = await launchChromium();

  for (const route of ['404', 'abort']) {
    const { pg, errs, read } = await openAlerts(b, route);
    const r = await read();
    check(`${route}: no false all-clear`, !r.text.includes(ALL_CLEAR), r.text.slice(0, 300));
    check(`${route}: says the feed is unavailable`, /unavailable/i.test(r.text), r.text.slice(0, 300));
    check(`${route}: KPI cards show – not 0`, !/\n0\n/.test('\n' + r.text + '\n') && r.text.includes('–'), r.text.slice(0, 300));
    check(`${route}: status is error`, r.status === 'error', r.status);
    check(`${route}: no JS errors`, errs.length === 0, errs);
    await pg.close();
  }

  {
    const { pg, errs, read } = await openAlerts(b, 'empty');
    const r = await read();
    check('empty feed: shows the genuine all-clear', r.text.includes(ALL_CLEAR), r.text.slice(0, 300));
    check('empty feed: status is loaded', r.status === 'loaded', r.status);
    check('empty feed: no JS errors', errs.length === 0, errs);
    await pg.close();
  }

  {
    const { pg, errs, read, release } = await openAlerts(b, 'held');
    const before = await read();
    check('pending: no all-clear while loading', !before.text.includes(ALL_CLEAR), before.text.slice(0, 300));
    check('pending: status is loading', before.status === 'loading', before.status);
    release();
    await pg.waitForFunction(() => window.alertsFeedStatus !== 'loading', { timeout: 10000 }).catch(() => {});
    await pg.waitForTimeout(200);
    const after = await read();
    check('pending -> failed: open tab repaints to unavailable', /unavailable/i.test(after.text), after.text.slice(0, 300));
    check('pending: no JS errors', errs.length === 0, errs);
    await pg.close();
  }

  console.log(`\n  alerts-feed-load-state tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
