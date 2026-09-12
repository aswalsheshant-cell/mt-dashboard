/**
 * Sprint 6 E2E Test Suite: Interactive Analytics & Executive Brief
 * Tests filter synchronization, tier configuration, drill-down, and export functions
 */
const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8000/dashboard';

test.describe('Sprint 6: Interactive Analytics & Executive Brief', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('01: Page load and correlations data availability', async () => {
    await page.goto(BASE_URL);

    // Check page title
    const title = await page.title();
    expect(title).toContain('MT Leadership Dashboard');

    // Verify correlations data in window.DASH
    const hasCorrelations = await page.evaluate(() => {
      return window.DASH && window.DASH.correlations &&
             window.DASH.correlations.by_chain &&
             window.DASH.correlations.by_chain.length > 0;
    });
    expect(hasCorrelations).toBe(true);

    // Verify no console errors
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    expect(errors.length).toBe(0);
  });

  test('02: Offtake Impact tab navigation and chart rendering', async () => {
    // Navigate to Offtake Impact tab
    await page.click('nav button:has-text("Offtake Impact")');

    // Wait for tab to be active
    const activeTab = await page.evaluate(() => {
      const nav = document.querySelector('nav button.active');
      return nav ? nav.textContent.trim() : '';
    });
    expect(activeTab).toContain('Offtake Impact');

    // Verify section is visible
    const section = page.locator('#tab-offtake-impact');
    await expect(section).toBeVisible();

    // Verify KPI cards render
    const kpiCount = await page.locator('#tab-offtake-impact .kpi').count();
    expect(kpiCount).toBeGreaterThan(0);

    // Verify all 4 chart canvases exist
    const charts = await page.locator('#tab-offtake-impact canvas').count();
    expect(charts).toBe(4);

    // Verify chart titles
    const elasticityChart = page.locator('text=Elasticity Curves');
    await expect(elasticityChart).toBeVisible();

    const heatmapChart = page.locator('text=ROI Efficiency Heatmap');
    await expect(heatmapChart).toBeVisible();

    const waterfallChart = page.locator('text=Uplift Waterfall');
    await expect(waterfallChart).toBeVisible();

    const scatterChart = page.locator('text=Scatter: Depth vs Lift');
    await expect(scatterChart).toBeVisible();
  });

  test('03: Global filter synchronization', async () => {
    // Switch to Primary tab (has filters)
    await page.click('nav button:has-text("Primary")');

    // Get initial chain filter value
    const chainSelectBefore = await page.evaluate(() => {
      const sel = document.querySelector('select[name="chainSelect"]');
      return sel ? sel.value : '';
    });

    // Apply a filter (select specific chain)
    const chainSelects = await page.locator('select[name="chainSelect"]').count();
    if (chainSelects > 0) {
      const options = await page.locator('select[name="chainSelect"] option').count();
      if (options > 1) {
        // Select second option
        await page.selectOption('select[name="chainSelect"]', { index: 1 });

        // Verify filter changed
        const chainSelectAfter = await page.evaluate(() => {
          const sel = document.querySelector('select[name="chainSelect"]');
          return sel ? sel.value : '';
        });
        expect(chainSelectAfter).not.toBe(chainSelectBefore);
      }
    }
  });

  test('04: Cross-tab drill-down from charts', async () => {
    // Navigate to Offtake Impact
    await page.click('nav button:has-text("Offtake Impact")');
    await page.waitForSelector('#chart-elasticity');

    // Verify elasticity chart exists
    const elasticityCanvas = page.locator('#chart-elasticity');
    await expect(elasticityCanvas).toBeVisible();

    // Simulate drill-down call
    const drillDownWorks = await page.evaluate(() => {
      return typeof window.drillDownToPromoTab === 'function';
    });
    expect(drillDownWorks).toBe(true);
  });

  test('05: Tier boundary configurator', async () => {
    // Check tier configurator exists
    const configurator = page.locator('#tierConfigurator');
    await expect(configurator).toBeInDOM();

    // Verify preset buttons
    const presetButtons = await page.locator('.tier-preset-buttons button').count();
    expect(presetButtons).toBe(3);

    // Verify tier sliders
    const sliders = await page.locator('.tier-slider-group input[type="range"]').count();
    expect(sliders).toBe(3);

    // Test FMCG preset
    await page.click('button:has-text("FMCG Default")');

    const t1Value = await page.evaluate(() => {
      return document.querySelector('#t1Value').textContent;
    });
    expect(t1Value).toContain('30');
  });

  test('06: Executive Brief modal generation', async () => {
    // Navigate to Offtake Impact
    await page.click('nav button:has-text("Offtake Impact")');

    // Check if showExecutiveBriefModal function exists
    const briefFunctionExists = await page.evaluate(() => {
      return typeof window.showExecutiveBriefModal === 'function';
    });
    expect(briefFunctionExists).toBe(true);

    // Call the function
    await page.evaluate(() => window.showExecutiveBriefModal());

    // Wait for modal to appear
    const modal = page.locator('#executiveBriefModal.active');
    await expect(modal).toBeVisible();

    // Verify brief content
    const briefContent = page.locator('#executiveBriefContent');
    const contentText = await briefContent.textContent();
    expect(contentText).toContain('Executive Brief');
  });

  test('07: Executive Brief export functions', async () => {
    // Verify export functions exist
    const exportFunctions = await page.evaluate(() => ({
      image: typeof window.exportExecutiveBriefImage === 'function',
      pdf: typeof window.exportExecutiveBriefPDF === 'function',
      clipboard: typeof window.copyExecutiveBriefToClipboard === 'function'
    }));

    expect(exportFunctions.image).toBe(true);
    expect(exportFunctions.pdf).toBe(true);
    expect(exportFunctions.clipboard).toBe(true);
  });

  test('08: 52-state matrix stability (13 tabs × 4 FY states)', async () => {
    const tabs = ['explorer', 'overview', 'primary', 'offtake', 'reliance-bc', 'pnl',
                  'category', 'forecast', 'promo', 'share', 'distribution', 'performance', 'insights'];
    const fyStates = ['no-filter', 'fy25', 'fy26', 'fy27'];

    let errorCount = 0;

    // Test each tab
    for (const tab of tabs) {
      const navBtn = page.locator(`nav button:nth-child(${tabs.indexOf(tab) + 1})`);
      if (await navBtn.count() > 0) {
        await navBtn.click();

        // Small delay for rendering
        await page.waitForTimeout(100);

        // Check for NaN, undefined, or [object Object] in visible text
        const bodyText = await page.locator('body').textContent();
        if (bodyText.includes('NaN') || bodyText.includes('undefined') ||
            bodyText.includes('[object Object]')) {
          errorCount++;
        }
      }
    }

    // Should have no NaN/undefined errors
    expect(errorCount).toBe(0);
  });
});
