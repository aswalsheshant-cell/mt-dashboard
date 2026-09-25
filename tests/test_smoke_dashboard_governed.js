// Regression test for FM-26: tests/smoke_dashboard.js used to print
// "Offtake baseline: 0 (Expected: 4512)" and still report PASS -- the 4512
// had no governed source, the field it summed does not exist, and the line was
// never asserted. It now asserts config/baselines.json. This test proves:
//   1. real baselines                 -> smoke exits 0
//   2. one tampered baseline value    -> smoke exits 1 and names the key
//   3. browser resolver order is PW_CHROMIUM_PATH > bundled > PLAYWRIGHT_BROWSERS_PATH,
//      and a missing browser is a named error, never a silent skip.
// Needs the dashboard served at BASE_URL (default http://localhost:8080/).
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const { resolveChromium } = require('./browser_launch');

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log(`  PASS ${name}`); }
  else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
}

const smoke = path.join(__dirname, 'smoke_dashboard.js');
const run = env => spawnSync(process.execPath, [smoke], { env: { ...process.env, ...env }, encoding: 'utf8', timeout: 240000 });

// 1. real governed baselines
const ok = run({});
check('test_smoke_passes_on_governed_baselines', ok.status === 0, (ok.stdout + ok.stderr).slice(-400));
check('test_smoke_no_longer_prints_unsourced_4512', !/4512/.test(ok.stdout));

// 2. tamper one frozen value in a temp copy (the real file is never touched)
const real = path.join(__dirname, '..', 'config', 'baselines.json');
const before = fs.readFileSync(real, 'utf8');
const bl = JSON.parse(before);
bl.checks[0].expected = bl.checks[0].expected + 1;
const tmp = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'smoke-bl-')), 'baselines.json');
fs.writeFileSync(tmp, JSON.stringify(bl));
const bad = run({ BASELINES_PATH: tmp });
check('test_smoke_fails_on_baseline_mismatch', bad.status === 1, bad.status);
check('test_smoke_names_the_mismatched_key', (bad.stdout + bad.stderr).includes(bl.checks[0].key));
check('test_real_baselines_file_untouched', fs.readFileSync(real, 'utf8') === before);

// 3. resolver order (pure, no browser launched)
const yes = () => true, no = () => false;
const r1 = resolveChromium({ PW_CHROMIUM_PATH: '/x/chrome', PLAYWRIGHT_BROWSERS_PATH: '/p' }, yes, () => '/b');
check('test_env_override_wins', r1.source === 'PW_CHROMIUM_PATH' && r1.executablePath === '/x/chrome', r1);
const r2 = resolveChromium({ PLAYWRIGHT_BROWSERS_PATH: '/p' }, yes, () => '/b');
check('test_bundled_browser_used_when_present', r2.source === 'playwright-bundled' && r2.executablePath === undefined, r2);
const r3 = resolveChromium({ PLAYWRIGHT_BROWSERS_PATH: '/p' }, p => p === path.join('/p', 'chromium'), () => '/b');
check('test_preinstalled_dir_fallback', r3.executablePath === path.join('/p', 'chromium'), r3);
let e4 = null; try { resolveChromium({}, no, () => '/b'); } catch (e) { e4 = e.message; }
check('test_missing_browser_is_named_error', /npx playwright install/.test(e4 || ''), e4);
let e5 = null; try { resolveChromium({ PW_CHROMIUM_PATH: '/nope' }, no, () => '/b'); } catch (e) { e5 = e.message; }
check('test_bad_override_is_named_error', /PW_CHROMIUM_PATH/.test(e5 || ''), e5);

console.log(`\n  smoke-dashboard-governed tests: ${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
