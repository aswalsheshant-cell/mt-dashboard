import { describe, it, expect, vi } from 'vitest';
import { exportLayoutJSON, assertNoSecrets } from '@/utils/export';
import { createEmptyLayout, validateLayout } from '@mt-dashboard/layout-schema';

describe('export', () => {
  it('assertNoSecrets passes for clean text', () => {
    expect(() => assertNoSecrets('hello world clean data')).not.toThrow();
  });

  it('assertNoSecrets rejects OpenAI key pattern', () => {
    expect(() => assertNoSecrets('sk-abcdefghijklmnopqrstu')).toThrow(/secret/i);
  });

  it('assertNoSecrets rejects GitHub token pattern', () => {
    expect(() => assertNoSecrets('ghp_' + 'a'.repeat(36))).toThrow(/secret/i);
  });

  it('exportLayoutJSON triggers a download without error', () => {
    // Mock the DOM anchor click — jsdom doesn't navigate
    const clickMock = vi.fn();
    const realCreate = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'a') {
        const el = realCreate('a') as HTMLAnchorElement;
        el.click = clickMock;
        return el;
      }
      return realCreate(tag);
    });

    const layout = createEmptyLayout('export-test', 'Export Test');
    exportLayoutJSON(layout);
    expect(clickMock).toHaveBeenCalled();
  });

  it('exportLayoutJSON rejects layout containing a secret-like string', () => {
    const layout = { ...createEmptyLayout('x', 'x'), projectName: 'sk-abcdefghijklmnopqrstu' };
    expect(() => exportLayoutJSON(layout)).toThrow(/secret/i);
  });
});
