const fs = require('fs');
const path = require('path');
const { launchChromium } = require('./browser_launch');
const BASE_URL = process.env.BASE_URL || 'http://localhost:8080/';
// Protected values come from the ONE governed baseline file (also used by
// scripts/ci_validate_datajs.py) -- never a number typed into this test.
const BASELINES_PATH = process.env.BASELINES_PATH ||
  path.join(__dirname, '..', 'config', 'baselines.json');

(async () => {
  const baselineChecks = JSON.parse(fs.readFileSync(BASELINES_PATH, 'utf8')).checks;
  const browser = await launchChromium();
  const page = await browser.newPage();
  const consoleErrors = [];
  const pageErrors = [];

  // Capture uncaught exceptions and console error logs
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text());
    }
  });

  page.on('pageerror', (err) => {
    pageErrors.push(err.message);
  });

  console.log(`\n🔍 Navigating to ${BASE_URL}...`);
  await page.goto(BASE_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });

  // 1. Verify global window.DASH payload existence, and that the numbers the
  //    browser actually loaded match config/baselines.json (same rule as
  //    ci_validate_datajs.py: exact within tolerance; tracked_universe > 0).
  const dashHealth = await page.evaluate((checks) => {
    if (!window.DASH) return { loaded: false, reason: 'window.DASH is undefined' };
    const dig = (o, p) => p.split('.').reduce((a, k) => (a == null ? undefined : a[k]), o);
    const baseline = checks.map(c => {
      const actual = dig(window.DASH, c.path);
      let ok;
      if (typeof actual !== 'number' || !isFinite(actual)) ok = false;
      else if (c.class === 'tracked_universe') ok = actual > 0 && Math.abs(actual - c.expected) <= (c.tolerance ?? 0.01);
      else ok = Math.abs(actual - c.expected) <= (c.tolerance ?? 0.01);
      return { key: c.key, path: c.path, expected: c.expected, actual: actual === undefined ? null : actual, ok };
    });
    return { loaded: true, baseline };
  }, baselineChecks);

  if (!dashHealth.loaded) {
    console.error(`❌ Fatal: ${dashHealth.reason}`);
    process.exit(1);
  }

  console.log(`✅ window.DASH loaded.`);
  const baselineFails = dashHealth.baseline.filter(b => !b.ok);
  dashHealth.baseline.forEach(b =>
    console.log(`   ${b.ok ? '✅' : '❌'} ${b.key}: ${b.actual} (expected ${b.expected})`));

  // 2. Discover and test tabs
  const tabSelector = 'nav button, .nav-item, [role="tab"]';
  const tabElements = await page.$$(tabSelector);
  console.log(`📋 Found ${tabElements.length} navigation elements.`);

  let totalDefects = 0;
  let tabsTestedCount = 0;

  // 3. Basic smoke: click first few tabs and check for NaN
  for (let i = 0; i < Math.min(5, tabElements.length); i++) {
    const tab = tabElements[i];
    const tabName = (await tab.innerText()).trim().replace(/\n/g, ' ') || `Tab #${i + 1}`;

    try {
      await tab.click();
      await page.waitForTimeout(400); // Allow render

      const pageText = await page.evaluate(() => document.body.innerText);
      const nanMatches = (pageText.match(/\bNaN\b/g) || []).length;
      const undefMatches = (pageText.match(/\bundefined\b/g) || []).length;

      if (nanMatches > 0 || undefMatches > 0) {
        console.error(`  ⚠️ [${tabName}] Found: ${nanMatches} NaN, ${undefMatches} undefined`);
        totalDefects += (nanMatches + undefMatches);
      } else {
        console.log(`  ✅ [${tabName}] Clean`);
      }

      tabsTestedCount++;
    } catch (err) {
      console.error(`  ❌ [${tabName}] Error: ${err.message}`);
    }
  }

  // 4. FY filter. The FY filter is the global bar's <select id="filter-FY">;
  //    its options come from the data (THE ONE FY RULE), not a fixed list.
  //    A missing control is a defect, not a skip.
  console.log(`\n🔄 Testing FY filters...`);
  let fyTested = 0, fyFailures = 0;
  const fyValues = await page.$$eval('#filter-FY option', os => os.map(o => o.value).filter(Boolean));
  if (!fyValues.length) {
    console.error('  ❌ FY filter (#filter-FY) not found or has no FY options');
    fyFailures++;
  }
  for (const fy of fyValues) {
    await page.selectOption('#filter-FY', fy);            // toggles fy on
    await page.waitForTimeout(300);
    const t = await page.evaluate(() => document.body.innerText);
    const bad = (t.match(/\bNaN\b/g) || []).length + (t.match(/\bundefined\b/g) || []).length;
    const selected = await page.evaluate(v => typeof F !== 'undefined' && F.FY.length === 1 && F.FY[0] === v, fy);
    if (bad || !selected) { console.error(`  ❌ [${fy}] ${bad} NaN/undefined, applied=${selected}`); fyFailures++; }
    else console.log(`  ✅ [${fy}] Filter applied, clean`);
    await page.selectOption('#filter-FY', '');             // clear
    await page.waitForTimeout(200);
    fyTested++;
  }

  // 5. Final Evaluation
  console.log('\n================ SMOKE TEST RESULTS ================');
  console.log(`Tabs tested:        ${tabsTestedCount}`);
  console.log(`Uncaught JS errors: ${pageErrors.length}`);
  console.log(`Console errors:     ${consoleErrors.length}`);
  console.log(`Text artifacts:     ${totalDefects}`);
  console.log(`FY filters tested:  ${fyTested} (failures: ${fyFailures})`);
  console.log(`Baseline checks:    ${dashHealth.baseline.length - baselineFails.length}/${dashHealth.baseline.length} match config/baselines.json`);
  console.log('===================================================');

  await browser.close();

  const success = pageErrors.length === 0 && consoleErrors.length === 0 && totalDefects === 0 &&
    fyFailures === 0 && baselineFails.length === 0 && tabsTestedCount > 0;
  if (success) {
    console.log('✅ SMOKE TEST PASSED');
    process.exit(0);
  } else {
    console.error('❌ SMOKE TEST FAILED');
    if (consoleErrors.length > 0) {
      console.error('\nConsole errors:');
      consoleErrors.forEach(e => console.error(`  - ${e}`));
    }
    if (baselineFails.length > 0) {
      console.error('\nBaseline mismatches (config/baselines.json):');
      baselineFails.forEach(b => console.error(`  - ${b.key} (${b.path}): got ${b.actual}, expected ${b.expected}`));
    }
    if (pageErrors.length > 0) {
      console.error('\nPage errors:');
      pageErrors.forEach(e => console.error(`  - ${e}`));
    }
    process.exit(1);
  }
})();
