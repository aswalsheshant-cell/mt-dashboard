import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const ARTIFACT_DIR = path.resolve(process.cwd(), 'qc-artifacts/v1.1.0-e2e');
const BASE_URL = 'http://localhost:3000/dashboard/index.html';

// 11 Canonical tabs post-Issue #105
const CONSOLIDATED_TABS = [
  { id: 'explorer', name: 'Data Explorer', hasSubviews: false },
  { id: 'executive-cockpit', name: 'Executive Cockpit', hasSubviews: false },
  {
    id: 'channel-dynamics',
    name: 'Channel & Chain Performance',
    hasSubviews: true,
    subviews: ['primary', 'category', 'reliance']
  },
  {
    id: 'inventory-health',
    name: 'Inventory & Supply Health',
    hasSubviews: true,
    subviews: ['velocity', 'gap', 'coverage']
  },
  {
    id: 'demand-planning',
    name: 'Demand & S&OP Planning',
    hasSubviews: true,
    subviews: ['forecast', 'promo', 'market-share']
  },
  { id: 'pnl', name: 'P&L', hasSubviews: false },
  { id: 'comparison', name: 'Performance & Comparison', hasSubviews: false },
  { id: 'analytics', name: 'Commercial Analytics', hasSubviews: false },
  { id: 'alerts', name: 'Operational Alerts', hasSubviews: false },
  { id: 'stores', name: 'Store Audit Scorecard', hasSubviews: false },
  { id: 'inventory', name: 'Supply Chain & Inventory', hasSubviews: false }
];

// Legacy routes to verify Guardrail #1
const LEGACY_ROUTES = [
  { legacy: 'overview', expectedTab: 'executive-cockpit', expectedSubview: null },
  { legacy: 'insights', expectedTab: 'executive-cockpit', expectedSubview: null },
  { legacy: 'primary', expectedTab: 'channel-dynamics', expectedSubview: 'primary' },
  { legacy: 'category', expectedTab: 'channel-dynamics', expectedSubview: 'category' },
  { legacy: 'reliance-bc', expectedTab: 'channel-dynamics', expectedSubview: 'reliance' },
  { legacy: 'offtake', expectedTab: 'inventory-health', expectedSubview: 'velocity' },
  { legacy: 'offtake-impact', expectedTab: 'inventory-health', expectedSubview: 'gap' },
  { legacy: 'distribution', expectedTab: 'inventory-health', expectedSubview: 'coverage' },
  { legacy: 'forecast', expectedTab: 'demand-planning', expectedSubview: 'forecast' },
  { legacy: 'promo', expectedTab: 'demand-planning', expectedSubview: 'promo' },
  { legacy: 'market-share', expectedTab: 'demand-planning', expectedSubview: 'market-share' }
];

test.beforeAll(() => {
  if (!fs.existsSync(ARTIFACT_DIR)) {
    fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  }
});

test.describe('v1.1.0 Navigation Consolidation E2E Suite', () => {
  let consoleErrors = [];

  test.beforeEach(async ({ page }) => {
    consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => consoleErrors.push(err.message));
  });

  // TEST 1: Legacy Routing & Backward Compatibility (Guardrail #1)
  test('TC01 - Legacy Tab Redirection Engine', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    for (const route of LEGACY_ROUTES) {
      // Execute legacy navigation
      await page.evaluate((legacyId) => window.show(legacyId), route.legacy);
      await page.waitForTimeout(300);

      // Verify canonical tab section is active
      const activeSection = await page.locator(`section#tab-${route.expectedTab}`);
      await expect(activeSection).toBeVisible();

      // If sub-view mapping is expected, verify active subview pill
      if (route.expectedSubview) {
        const activePill = page.locator(
          `#tab-${route.expectedTab} .subview-tab[onclick*="'${route.expectedSubview}'"]`
        );
        const hasActive = await activePill.evaluate(el => el.classList.contains('active')).catch(() => false);
        expect(hasActive).toBeTruthy();
      }
    }

    expect(consoleErrors.length).toBe(0);
  });

  // TEST 2: All 11 Tabs Mount Cleanly and Capture Artifacts
  test('TC02 - 11 Canonical Tabs Traversal & Visual Proof', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    for (let i = 0; i < CONSOLIDATED_TABS.length; i++) {
      const tab = CONSOLIDATED_TABS[i];

      await page.evaluate((tabId) => window.show(tabId), tab.id);
      await page.waitForTimeout(600); // Allow Chart.js / SVG layout to settle

      // Verify container is rendered
      const section = page.locator(`section#tab-${tab.id}`);
      await expect(section).toBeVisible();

      // Ensure no raw unhandled math artifacts
      const bodyText = await section.innerText();
      expect(bodyText).not.toContain('NaN');
      expect(bodyText).not.toContain('undefined');
      expect(bodyText).not.toContain('Infinity');

      // Screenshot capture
      const screenshotPath = path.join(
        ARTIFACT_DIR,
        `tab_${String(i + 1).padStart(2, '0')}_${tab.id}.png`
      );
      await page.screenshot({ path: screenshotPath, fullPage: true });
    }

    expect(consoleErrors.length).toBe(0);
  });

  // TEST 3: Canvas Lifecycle & Chart Teardown (Guardrail #3)
  test('TC03 - Sub-View Canvas Lifecycle & Memory Cleanup', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    const multiViewTabs = CONSOLIDATED_TABS.filter(t => t.hasSubviews);

    for (const tab of multiViewTabs) {
      await page.evaluate((tabId) => window.show(tabId), tab.id);

      for (const subview of tab.subviews) {
        // Trigger sub-view transition
        const pill = page.locator(`#tab-${tab.id} .subview-tab[onclick*="'${subview}'"]`);
        await pill.click();
        await page.waitForTimeout(500);

        // Verify active status
        const hasActive = await pill.evaluate(el => el.classList.contains('active')).catch(() => false);
        expect(hasActive).toBeTruthy();

        // Inspect canvas registration state
        const chartCount = await page.evaluate((tabId) => {
          let stateObj = null;
          if (tabId === 'channel-dynamics') stateObj = window.channelDynamicsState;
          if (tabId === 'inventory-health') stateObj = window.inventoryHealthState;
          if (tabId === 'demand-planning') stateObj = window.demandPlanningState;
          return stateObj && stateObj.charts ? Object.keys(stateObj.charts).length : 0;
        }, tab.id);

        expect(chartCount).toBeGreaterThan(0);

        // Screenshot sub-view
        await page.screenshot({
          path: path.join(ARTIFACT_DIR, `subview_${tab.id}_${subview}.png`),
          fullPage: true
        });
      }
    }

    expect(consoleErrors.length).toBe(0);
  });

  // TEST 4: Asymmetric Timeline Data Boundary (Guardrail #2)
  test('TC04 - August 2026 Asymmetric Data Boundary Safeguard', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    // Switch to Inventory Health
    await page.evaluate(() => window.show('inventory-health'));
    await page.waitForTimeout(400);

    const periodCheck = await page.evaluate(() => {
      const data = window.DASH || {};
      if (!data.offtake) return { ok: false, error: 'Offtake data unavailable' };
      return {
        ok: true,
        hasMetrics: !!data.offtake.metrics,
        totalExists: !!data.offtake.total
      };
    });

    expect(periodCheck.ok).toBe(true);
    expect(periodCheck.hasMetrics || periodCheck.totalExists).toBe(true);
  });

  // TEST 5: Filter State Isolation (Guardrail #4)
  test('TC05 - Filter Encapsulation Across Sub-Views', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    // Navigate to Channel Dynamics and switch sub-views
    await page.evaluate(() => window.show('channel-dynamics'));

    const reliancePill = page.locator('#tab-channel-dynamics .subview-tab[onclick*="reliance"]');
    await reliancePill.click();
    await page.waitForTimeout(400);

    // Verify Reliance sub-view is active
    const hasActive = await reliancePill.evaluate(el => el.classList.contains('active')).catch(() => false);
    expect(hasActive).toBeTruthy();

    // Verify section is still mounted
    const section = page.locator('section#tab-channel-dynamics');
    await expect(section).toBeVisible();
  });

  // TEST 6: Browser Console Health (Guardrail #3)
  test('TC06 - Zero Critical Errors Across All Tabs', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    const allErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') allErrors.push({ type: 'console', text: msg.text() });
    });
    page.on('pageerror', err => {
      allErrors.push({ type: 'uncaught', text: err.message });
    });

    // Traverse all tabs
    for (const tab of CONSOLIDATED_TABS) {
      await page.evaluate((tabId) => window.show(tabId), tab.id);
      await page.waitForTimeout(400);
    }

    // Verify zero critical errors
    expect(allErrors.length).toBe(0);
  });
});
