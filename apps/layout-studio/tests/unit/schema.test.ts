import { describe, it, expect } from 'vitest';
import {
  validateLayout,
  importLayout,
  exportLayout,
  createEmptyLayout,
  createVisualId,
  SCHEMA_VERSION,
} from '@mt-dashboard/layout-schema';

describe('layout-schema', () => {
  it('createEmptyLayout produces a valid layout', () => {
    const layout = createEmptyLayout('test-proj', 'Test');
    const result = validateLayout(layout);
    expect(result.success).toBe(true);
  });

  it('createVisualId returns alphanumeric ids', () => {
    const id = createVisualId();
    expect(id).toMatch(/^[a-zA-Z0-9_-]+$/);
  });

  it('importLayout round-trips through exportLayout', () => {
    const layout = createEmptyLayout('round-trip', 'Round Trip');
    const json   = exportLayout(layout);
    const result = importLayout(json);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.projectId).toBe('round-trip');
      expect(result.data.schemaVersion).toBe(SCHEMA_VERSION);
    }
  });

  it('rejects unknown schemaVersion', () => {
    const layout = createEmptyLayout('x', 'x');
    const broken = JSON.stringify({ ...layout, schemaVersion: '0.0.1' });
    const result = importLayout(broken);
    expect(result.success).toBe(false);
  });

  it('rejects layout with _raw field', () => {
    const layout = createEmptyLayout('x', 'x');
    const withRaw = {
      ...layout,
      pages: [{ ...layout.pages[0], visuals: [{ ...( {
        id: 'v1', type: 'kpi-card', title: 'KPI', subtitle: '', x: 0, y: 0,
        width: 220, height: 100, zIndex: 0, locked: false, hidden: false,
        measures: [], categories: [], series: [], filters: [],
        interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true },
        tooltip: { enabled: true, fields: [] },
        drillthrough: { enabled: false, passFilters: [] },
        formatting: { fontWeight: 'normal', padding: 8, borderWidth: 0, borderRadius: 4, legendVisible: true, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: [], titleVisible: true, titleFontSize: 14 },
        accessibilityLabel: 'KPI',
        _raw: 'exploit',
      } ) }] }]
    };
    const result = importLayout(JSON.stringify(withRaw));
    expect(result.success).toBe(false);
  });

  it('rejects non-JSON input', () => {
    const result = importLayout('not json');
    expect(result.success).toBe(false);
  });
});
