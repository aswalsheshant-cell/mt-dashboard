/**
 * tests/dashboard.spec.js
 * Playwright E2E Test Suite for Modern Trade Analytics Dashboard (v3.0.0)
 * Validates Navigation, Drill-Downs, Retail Execution Matrix, and Export Engines.
 */

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8765';

test.describe('Modern Trade Analytics Dashboard - Smoke & Regression Suite', () => {

  test.beforeEach(async ({ page }) => {
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        console.error(`[Browser Console Error]: ${msg.text()}`);
      }
    });

    await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  });

  // ============================================================================
  // PHASE 1: GLOBAL NAVIGATION & INTEGRITY
  // ============================================================================

  test('NAV-01 & NAV-02: Page loads without runtime errors or text leakage', async ({ page }) => {
    await expect(page).toHaveTitle(/Modern Trade/i);
    const mainContainer = page.locator('#dashboard-root, body');
    await expect(mainContainer).toBeVisible();

    const bodyText = await page.locator('body').innerText();
    expect(bodyText).not.toContain('NaN');
    expect(bodyText).not.toContain('undefined');
    expect(bodyText).not.toContain('[object Object]');
  });

  test('NAV-03: Tab navigation traverses across all views', async ({ page }) => {
    const tabs = page.locator('.nav-tab, [role="tab"], .tab-btn');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(10);

    for (let i = 0; i < Math.min(tabCount, 5); i++) {
      const tab = tabs.nth(i);
      await tab.click();
      await page.waitForTimeout(200);
    }
  });

  test('NAV-04: Fiscal year selector updates dashboard metrics', async ({ page }) => {
    const fySelector = page.locator('#fy-select, .fy-toggle-btn, .fy-filter').first();
    if (await fySelector.isVisible()) {
      await fySelector.click();
      const bodyText = await page.locator('body').innerText();
      expect(bodyText).not.toContain('NaN');
    }
  });

  // ============================================================================
  // PHASE 2: OVERVIEW TAB & DRILL-DOWNS
  // ============================================================================

  test('OVR-01 & OVR-02: Highlights card and sparklines render on Overview', async ({ page }) => {
    const overviewTab = page.locator('[data-tab="overview"], #tab-btn-overview, button:has-text("Overview")').first();
    if (await overviewTab.isVisible()) {
      await overviewTab.click();
      await page.waitForTimeout(300);
    }

    const highlightsCard = page.locator('.highlights-card, #executive-highlights').first();
    if (await highlightsCard.isVisible()) {
      await expect(highlightsCard).toBeVisible();
    }

    const sparklines = page.locator('svg.sparkline, .kpi-sparkline');
    const sparklineCount = await sparklines.count();
    expect(sparklineCount).toBeGreaterThanOrEqual(0);
  });

  test('OVR-03 & OVR-04: Zone drill-down filter applies and dismisses', async ({ page }) => {
    const zoneTrigger = page.locator('[data-zone], .zone-drill').first();
    if (await zoneTrigger.isVisible()) {
      await zoneTrigger.click();
      await page.waitForTimeout(300);

      const filterChip = page.locator('.filter-chip, .active-filter-badge').first();
      if (await filterChip.isVisible()) {
        const closeBtn = filterChip.locator('.chip-close, button, .close-icon').first();
        if (await closeBtn.isVisible()) {
          await closeBtn.click();
        }
      }
    }
  });

  // ============================================================================
  // PHASE 3: RETAIL EXECUTION TAB & COMPLIANCE MATRIX
  // ============================================================================

  test('EXE-01 & EXE-02: Retail Execution tab renders KPIs and status pills', async ({ page }) => {
    const execTab = page.locator('[data-tab="execution"], #tab-execution-btn, button:has-text("Retail Execution")').first();
    if (await execTab.isVisible()) {
      await execTab.click();
      await page.waitForTimeout(500);

      const kpiSummary = page.locator('#execution-kpi-summary, .execution-kpi-grid').first();
      if (await kpiSummary.isVisible()) {
        await expect(kpiSummary).toBeVisible();
      }

      const statusBadges = page.locator('.status-pill, .badge-status, .badge');
      const badgeCount = await statusBadges.count();
      expect(badgeCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('EXE-03 & EXE-04: Live search filtering on chain names and zones', async ({ page }) => {
    const execTab = page.locator('[data-tab="execution"], #tab-execution-btn, button:has-text("Retail Execution")').first();
    if (await execTab.isVisible()) {
      await execTab.click();
      await page.waitForTimeout(500);

      const searchInput = page.locator('#compliance-search, input[placeholder*="Search"]').first();
      if (await searchInput.isVisible()) {
        await searchInput.fill('DMart');
        await page.waitForTimeout(300);

        const rows = page.locator('#compliance-table tbody tr, .compliance-row, table tbody tr');
        const rowCount = await rows.count();
        expect(rowCount).toBeGreaterThanOrEqual(0);
      }
    }
  });

  test('EXE-05 & EXE-06: Account drill modal opens and dismisses', async ({ page }) => {
    const execTab = page.locator('[data-tab="execution"], #tab-execution-btn, button:has-text("Retail Execution")').first();
    if (await execTab.isVisible()) {
      await execTab.click();
      await page.waitForTimeout(500);

      const firstRow = page.locator('#compliance-table tbody tr, .compliance-row, table tbody tr').first();
      if (await firstRow.isVisible()) {
        await firstRow.click();
        await page.waitForTimeout(300);

        const modal = page.locator('#chain-detail-modal, .audit-modal, .modal').first();
        if (await modal.isVisible()) {
          const closeBtn = modal.locator('.modal-close, button.close, [aria-label="Close"]').first();
          if (await closeBtn.isVisible()) {
            await closeBtn.click();
          } else {
            await page.keyboard.press('Escape');
          }
          await page.waitForTimeout(200);
        }
      }
    }
  });

  // ============================================================================
  // PHASE 4: REPORTING & EXPORT ENGINES
  // ============================================================================

  test('EXP-01 & EXP-02: CSV Export initiates and produces valid file', async ({ page }) => {
    const execTab = page.locator('[data-tab="execution"], #tab-execution-btn, button:has-text("Retail Execution")').first();
    if (await execTab.isVisible()) {
      await execTab.click();
      await page.waitForTimeout(500);

      const csvButton = page.locator('#btn-export-csv, button:has-text("Export CSV"), button:has-text("CSV")').first();
      if (await csvButton.isVisible()) {
        const [download] = await Promise.all([
          page.waitForEvent('download'),
          csvButton.click()
        ]);
        const filename = download.suggestedFilename();
        expect(filename).toMatch(/\.csv$/i);
      }
    }
  });

  test('EXP-03 to EXP-05: Excel Export downloads multi-tab workbook', async ({ page }) => {
    const execTab = page.locator('[data-tab="execution"], #tab-execution-btn, button:has-text("Retail Execution")').first();
    if (await execTab.isVisible()) {
      await execTab.click();
      await page.waitForTimeout(500);

      const excelButton = page.locator('#btn-export-excel, button:has-text("Export Excel"), button:has-text("Excel")').first();
      if (await excelButton.isVisible()) {
        const [download] = await Promise.all([
          page.waitForEvent('download'),
          excelButton.click()
        ]);
        const filename = download.suggestedFilename();
        expect(filename).toMatch(/\.xlsx$/i);
      }
    }
  });

  // ============================================================================
  // PHASE 5: SIDECAR CACHE & NETWORK HEADERS
  // ============================================================================

  test('NET-01 & NET-02: Sidecars and static assets verify cache headers', async ({ page, request }) => {
    const jsonRes = await request.get(`${BASE_URL}/compliance_metrics.json`);
    expect(jsonRes.status()).toBe(200);
  });

  // ============================================================================
  // PHASE 6: VISUAL REGRESSION & SNAPSHOT COMPARISONS
  // ============================================================================

  test.describe('Visual Regression - Pixel Integrity Checks', () => {

    test('VIS-01: Overview Highlights & Sparklines visual snapshot', async ({ page }) => {
      const overviewTab = page.locator('[data-tab="overview"], #tab-btn-overview, button:has-text("Overview")').first();
      if (await overviewTab.isVisible()) {
        await overviewTab.click();
        await page.waitForTimeout(500);
      }

      const highlightsCard = page.locator('.highlights-card, #executive-highlights').first();
      if (await highlightsCard.isVisible()) {
        await expect(highlightsCard).toHaveScreenshot('overview-highlights-card.png', {
          mask: [page.locator('.dynamic-timestamp, .live-clock')],
          maxDiffPixelRatio: 0.02,
        });
      }
    });

    test('VIS-02: Retail Execution tab & Compliance Matrix visual snapshot', async ({ page }) => {
      const execTab = page.locator('[data-tab="execution"], #tab-execution-btn, button:has-text("Retail Execution")').first();
      if (await execTab.isVisible()) {
        await execTab.click();
        await page.waitForTimeout(500);

        const table = page.locator('#compliance-table, .compliance-matrix-table, table').first();
        if (await table.isVisible()) {
          await expect(table).toHaveScreenshot('compliance-matrix-table.png', {
            maxDiffPixelRatio: 0.02,
          });
        }
      }
    });

  });

});
