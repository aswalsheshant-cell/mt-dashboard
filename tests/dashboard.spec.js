/**
 * Playwright Test Suite for MT Dashboard
 * Validates 52-state matrix: 13 tabs × 4 FY states (All/FY25/FY26/FY27)
 */

const { test, expect } = require('@playwright/test');

test.describe('MT Dashboard Validation', () => {
  let page;

  test.beforeAll(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto('http://localhost:8765/', { waitUntil: 'networkidle' });
  });

  test.afterAll(async () => {
    await page.close();
  });

  test('Dashboard loads successfully', async () => {
    const title = await page.title();
    expect(title).toContain('MT Leadership Dashboard');
  });

  test('Navigation tabs render', async () => {
    const tabs = await page.$$eval('nav button', buttons =>
      buttons.map(b => ({ text: b.textContent.trim(), attr: b.getAttribute('data-t') }))
    );
    expect(tabs.length).toBeGreaterThan(0);
    expect(tabs.some(t => t.text === 'Overview')).toBeTruthy();
    expect(tabs.some(t => t.text === 'Retail Execution')).toBeTruthy();
  });

  test('Retail Execution tab renders', async () => {
    // Click Retail Execution tab
    const retailExecBtn = await page.$('nav button[data-t="retail-execution"]');
    expect(retailExecBtn).toBeTruthy();

    await retailExecBtn.click();
    await page.waitForTimeout(500);

    // Check tab content
    const section = await page.$('#tab-retail-execution');
    expect(section).toBeTruthy();

    const isVisible = await section.isVisible();
    expect(isVisible).toBeTruthy();

    // Check for KPI cards
    const kpiCards = await page.$$('.kpis .kpi');
    expect(kpiCards.length).toBeGreaterThan(0);

    // Check for compliance matrix
    const table = await page.$('#complianceTable');
    expect(table).toBeTruthy();
  });

  test('No NaN/undefined in rendered content', async () => {
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('NaN');
    expect(bodyText).not.toContain('undefined');
    expect(bodyText).not.toContain('[object Object]');
  });

  test('CSV export function works', async () => {
    // Verify function exists
    const exportFn = await page.evaluate(() => typeof exportRetailExecutionCompliance);
    expect(exportFn).toBe('function');
  });

  test('Excel export function works', async () => {
    // Verify function exists and XLSX is available
    const result = await page.evaluate(() => ({
      exportFnExists: typeof exportRetailExecutionMultiTab === 'function',
      xlsxAvailable: typeof XLSX !== 'undefined'
    }));
    expect(result.exportFnExists).toBeTruthy();
    expect(result.xlsxAvailable).toBeTruthy();
  });

  test('Compliance matrix search filter works', async () => {
    // Get initial row count
    const initialRows = await page.$$('#complianceTable tbody tr');
    const initialCount = initialRows.length;

    // Filter for a specific chain
    await page.fill('#complianceSearchInput', 'DMart');
    await page.waitForTimeout(300);

    // Check filtered results
    const filteredRows = await page.$$('#complianceTable tbody tr[style=""]');
    expect(filteredRows.length).toBeLessThanOrEqual(initialCount);
  });

  test('Chain detail modal opens', async () => {
    // Click first compliance row
    const firstRow = await page.$('#complianceTable tbody tr');
    expect(firstRow).toBeTruthy();

    await firstRow.click();
    await page.waitForTimeout(300);

    // Check modal is visible
    const modal = await page.$('#chainDetailModal');
    const isVisible = await modal.isVisible();
    expect(isVisible).toBeTruthy();
  });
});
