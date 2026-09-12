import { describe, it, expect, beforeEach } from 'vitest';
import { saveLayout, loadSavedLayout, clearSavedLayout, hasSavedLayout } from '@/utils/autosave';
import { createEmptyLayout } from '@mt-dashboard/layout-schema';

describe('autosave', () => {
  beforeEach(() => { clearSavedLayout(); });

  it('saves and loads a layout', () => {
    const layout = createEmptyLayout('save-test', 'Save Test');
    const r = saveLayout(layout);
    expect(r.ok).toBe(true);
    expect(hasSavedLayout()).toBe(true);
    const loaded = loadSavedLayout();
    expect(loaded?.projectId).toBe('save-test');
  });

  it('rejects layout containing a secret-like string', () => {
    const layout = createEmptyLayout('secret-test', 'sk-abcdefghij12345678901234');
    const r = saveLayout(layout);
    expect(r.ok).toBe(false);
    expect(r.error).toMatch(/secret/i);
  });

  it('clearSavedLayout removes saved data', () => {
    const layout = createEmptyLayout('clear-test', 'Clear');
    saveLayout(layout);
    clearSavedLayout();
    expect(hasSavedLayout()).toBe(false);
    expect(loadSavedLayout()).toBeNull();
  });

  it('returns null when nothing is saved', () => {
    expect(loadSavedLayout()).toBeNull();
    expect(hasSavedLayout()).toBe(false);
  });
});
