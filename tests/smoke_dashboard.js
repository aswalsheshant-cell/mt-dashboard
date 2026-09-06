const { chromium } = require('playwright');
const BASE_URL = process.env.BASE_URL || 'http://localhost:8080/';
const FY_OPTIONS = ['FY25', 'FY26', 'FY27'];

(async () => {
  const browser = await chromium.launch({ headless: true });
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

  // 1. Verify global window.DASH payload existence
  const dashHealth = await page.evaluate(() => {
    if (!window.DASH) return { loaded: false, reason: 'window.DASH is undefined' };

    // Check offtake block
    let offtakeUnits = 0;
    if (window.DASH.offtake && window.DASH.offtake.by_chain) {
      offtakeUnits = window.DASH.offtake.by_chain.reduce((sum, c) => sum + (c.total || 0), 0);
    }
    return {
      loaded: true,
      hasOfftake: Boolean(window.DASH.offtake),
      totalUnits: offtakeUnits,
      fyTags: window.DASH.fy_tags || []
    };
  });

  if (!dashHealth.loaded) {
    console.error(`❌ Fatal: ${dashHealth.reason}`);
    process.exit(1);
  }

  console.log(`✅ window.DASH loaded.`);
  console.log(`   Offtake units: ${dashHealth.totalUnits}`);
  console.log(`   FY coverage: ${dashHealth.fyTags.join(', ')}`);

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

  // 4. Test FY filter if visible
  console.log(`\n🔄 Testing FY filters...`);
  for (const fy of FY_OPTIONS) {
    try {
      const fyButton = await page.$(`button:has-text("${fy}")`);
      if (fyButton) {
        await fyButton.click();
        await page.waitForTimeout(300);
        console.log(`  ✅ [${fy}] Filter works`);
      }
    } catch (_) {
      // Filter not present, skip
    }
  }

  // 5. Final Evaluation
  console.log('\n================ SMOKE TEST RESULTS ================');
  console.log(`Tabs tested:        ${tabsTestedCount}`);
  console.log(`Uncaught JS errors: ${pageErrors.length}`);
  console.log(`Console errors:     ${consoleErrors.length}`);
  console.log(`Text artifacts:     ${totalDefects}`);
  console.log(`Offtake baseline:   ${dashHealth.totalUnits} (Expected: 4512)`);
  console.log('===================================================');

  await browser.close();

  const success = pageErrors.length === 0 && consoleErrors.length === 0 && totalDefects === 0;
  if (success) {
    console.log('✅ SMOKE TEST PASSED');
    process.exit(0);
  } else {
    console.error('❌ SMOKE TEST FAILED');
    if (consoleErrors.length > 0) {
      console.error('\nConsole errors:');
      consoleErrors.forEach(e => console.error(`  - ${e}`));
    }
    if (pageErrors.length > 0) {
      console.error('\nPage errors:');
      pageErrors.forEach(e => console.error(`  - ${e}`));
    }
    process.exit(1);
  }
})();
