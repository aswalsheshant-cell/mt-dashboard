import { test, expect } from '@playwright/test';

test.describe('Layout Studio smoke tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Dismiss autosave restore dialog if it appears
    page.on('dialog', (d) => d.dismiss());
  });

  test('page title and app structure', async ({ page }) => {
    await expect(page).toHaveTitle(/Layout Studio/i);
    await expect(page.getByRole('region', { name: /Layout canvas workspace/i })).toBeVisible();
  });

  test('toolbar is present with undo/redo', async ({ page }) => {
    await expect(page.getByRole('banner')).toBeVisible();
    await expect(page.getByLabel('Undo (⌘Z)')).toBeVisible();
    await expect(page.getByLabel('Redo (⌘Y)')).toBeVisible();
  });

  test('visual picker lists visuals', async ({ page }) => {
    await expect(page.getByRole('complementary', { name: /Visual picker/i })).toBeVisible();
    await expect(page.getByLabel('Add KPI Card')).toBeVisible();
  });

  test('adding a visual via picker', async ({ page }) => {
    // Dismiss any dialogs
    page.on('dialog', (d) => d.dismiss());
    await page.getByLabel('Add KPI Card').click();
    await expect(page.getByTestId(/^visual-/)).toBeVisible({ timeout: 5000 });
  });

  test('template gallery opens and closes', async ({ page }) => {
    await page.getByLabel('Open template gallery').click();
    await expect(page.getByRole('dialog', { name: /Template gallery/i })).toBeVisible();
    await page.getByLabel('Close gallery').click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('validation panel toggles', async ({ page }) => {
    await page.getByTitle('Toggle validation panel').click();
    await expect(page.getByRole('region', { name: /Validation panel/i })).toBeVisible();
    await page.getByLabel('Close validation panel').click();
    await expect(page.getByRole('region', { name: /Validation panel/i })).not.toBeVisible();
  });

  test('keyboard shortcut Ctrl+Z triggers undo without error', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
    await page.keyboard.press('Control+z');
    expect(errors).toHaveLength(0);
  });

  test('canvas is empty state initially', async ({ page }) => {
    await expect(page.getByText('Empty canvas')).toBeVisible();
  });
});
