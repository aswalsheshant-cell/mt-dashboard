#!/usr/bin/env node
/**
 * Headless validation sweep for dashboard/index.html.
 *
 * Implements the check CLAUDE.md requires before committing dashboard changes:
 * every tab x every FY state, asserting no NaN / undefined / empty-broken cards
 * / JS errors, plus the canonical-chain and Reliance-BA isolation guards.
 *
 *   node scripts/sweep_dashboard.js [baseUrl]
 *
 * Chromium resolution order:
 *   1. $CHROMIUM_PATH                 (explicit override)
 *   2. $PLAYWRIGHT_BROWSERS_PATH glob (survives Playwright version bumps,
 *      e.g. chromium-1194 -> chromium-1250, which a hardcoded path would not)
 *   3. common system locations
 * Exits 0 only when every check passes.
 */
const fs = require('fs');
const path = require('path');

const PW = process.env.PLAYWRIGHT_BROWSERS_PATH || '/opt/pw-browsers';
const NODE_MODULES = '/opt/node22/lib/node_modules';
const { chromium } = require(
  fs.existsSync(path.join(NODE_MODULES, 'playwright'))
    ? path.join(NODE_MODULES, 'playwright') : 'playwright');

function resolveChromium() {
  if (process.env.CHROMIUM_PATH) return process.env.CHROMIUM_PATH;
  // newest chromium-<rev> under the Playwright browsers dir
  try {
    const revs = fs.readdirSync(PW)
      .filter(d => /^chromium-\d+$/.test(d))
      .sort((a, b) => Number(b.split('-')[1]) - Number(a.split('-')[1]));
    for (const r of revs) {
      const p = path.join(PW, r, 'chrome-linux', 'chrome');
      if (fs.existsSync(p)) return p;
    }
  } catch { /* dir absent -- fall through to system paths */ }
  for (const p of ['/usr/bin/chromium', '/usr/bin/chromium-browser',
                   '/usr/bin/google-chrome']) {
    if (fs.existsSync(p)) return p;
  }
  return undefined;   // let Playwright use its own bundled default
}

const BASE = process.argv[2] || 'http://127.0.0.1:8099/index.html';
const TABS = ['explorer', 'overview', 'primary', 'offtake', 'reliance-ba', 'pnl',
  'category', 'forecast', 'promo', 'share', 'distribution', 'comparison', 'insights'];
const FYS = [null, 'FY25', 'FY26', 'FY27'];

// Console noise that is NOT a dashboard defect. The Vercel speed-insights script
// is injected for the hosted deploy and legitimately 404s on a local server.
const BENIGN = [/_vercel\/speed-insights/, /favicon\.ico/];
const isBenign = t => BENIGN.some(re => re.test(t));

(async () => {
  const executablePath = resolveChromium();
  console.log('chromium: ' + (executablePath || '(playwright default)'));
  const browser = await chromium.launch({
    executablePath, headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  const errs = [];
  const note = t => { if (!isBenign(t)) errs.push(t); };
  page.on('pageerror', e => note('PAGEERROR: ' + e.message));
  page.on('console', m => {
    if (m.type() !== 'error') return;
    // A failed-subresource console error carries the URL in location(), NOT in
    // text() ("Failed to load resource: ...404"), so the benign check has to
    // look at both or every ignorable 404 still fails the run.
    const loc = (m.location() && m.location().url) || '';
    note('CONSOLE: ' + m.text() + (loc ? ' @ ' + loc : ''));
  });
  page.on('requestfailed', r => note('REQFAIL: ' + r.url()));

  await page.goto(BASE, { waitUntil: 'networkidle' });

  // ---- window bindings must be present (the automation contract) ----
  const bindings = await page.evaluate(() => ['F', 'TABS', 'D', 'show', 'showTab',
    'fyKey', 'BUILD', 'validateRelianceIsolation'].filter(k => typeof window[k] === 'undefined'));
  if (bindings.length) errs.push('MISSING window bindings: ' + bindings.join(', '));
  console.log('window bindings: ' + (bindings.length ? 'MISSING ' + bindings : 'all present'));

  // ---- switch tabs by CLICKING the real nav button (data-t), not by calling in ----
  async function openTab(id) {
    await page.click(`nav button[data-t="${id}"]`);
    // show() defers its build one tick via setTimeout -- wait for real content
    await page.waitForFunction((tab) => {
      const el = document.getElementById('tab-' + tab);
      return el && el.classList.contains('active') && el.innerText.trim().length > 0;
    }, id, { timeout: 5000 });
  }

  // ---- set FY through the real <select> + change event ----
  async function setFY(fy) {
    await page.evaluate(() => { window.F.FY = []; });
    if (fy) {
      await page.selectOption('select[data-k="FY"]', fy).catch(() => {});
      await page.evaluate((v) => {
        const s = document.querySelector('select[data-k="FY"]');
        if (s && !window.F.FY.includes(v)) { s.value = v; s.dispatchEvent(new Event('change', { bubbles: true })); }
      }, fy);
    }
    await page.waitForTimeout(80);
    return page.evaluate(() => window.F.FY.slice());
  }

  let bad = 0;
  for (const fy of FYS) {
    const applied = await setFY(fy);
    if (fy && !applied.includes(fy)) { errs.push(`FY ${fy} did not apply via DOM (got ${JSON.stringify(applied)})`); bad++; }
    for (const t of TABS) {
      const before = errs.length;
      let flags = [];
      try { await openTab(t); }
      catch (e) { flags.push('NO-RENDER'); errs.push(`OPEN ${t}/${fy}: ${e.message.split('\n')[0]}`); }
      const txt = await page.evaluate((tab) => {
        const el = document.getElementById('tab-' + tab); return el ? el.innerText : '';
      }, t);
      if (/\bNaN\b/.test(txt)) flags.push('NaN');
      if (/\bundefined\b/.test(txt)) flags.push('undefined');
      if (!txt.trim()) flags.push('EMPTY');
      if (flags.length || errs.length > before) {
        bad++;
        console.log(`  x ${String(fy).padEnd(5)} ${t.padEnd(13)} ${flags.join(',')} ${errs.slice(before).join(' ')}`);
      }
    }
  }
  console.log(`\ntabs: ${TABS.length * FYS.length} tab x FY combos, ${bad} with issues`);

  // ---- canonical chain master ----
  const chains = await page.evaluate(() =>
    [...new Set(window.D.detail_records.map(r => r.Chain))].filter(Boolean).sort());
  const norm = chains.map(c => c.toLowerCase().replace(/[^a-z0-9]/g, ''));
  const collisions = norm.filter((v, i) => norm.indexOf(v) !== i);
  console.log(`chains: ${chains.length} unique, ${collisions.length} collisions` +
    (collisions.length ? ' -> ' + collisions : ''));
  if (collisions.length) errs.push('chain collisions: ' + collisions.join(', '));

  // ---- Reliance BA isolation ----
  const iso = await page.evaluate(() => window.validateRelianceIsolation());
  const drifted = Object.entries(iso.by_fy).filter(([, v]) => !v.passes);
  console.log(`isolation: status=${iso.status} ` +
    Object.entries(iso.by_fy).map(([k, v]) => `${k} drift=${v.drift}`).join(' ') +
    (iso.issues.length ? ` | ${iso.issues.join('; ')}` : ''));
  if (drifted.length) errs.push('BA drift: ' + drifted.map(([k]) => k).join(', '));
  if (iso.status === 'FAIL' || iso.status === 'BLOCKED') errs.push('isolation status ' + iso.status);

  console.log(`\nreal errors: ${errs.length}`);
  errs.slice(0, 15).forEach(e => console.log('  ! ' + e));
  await browser.close();
  const ok = bad === 0 && errs.length === 0;
  console.log(ok ? '\nSWEEP PASS' : '\nSWEEP FAIL');
  process.exit(ok ? 0 : 1);
})().catch(e => { console.error(e); process.exit(1); });
