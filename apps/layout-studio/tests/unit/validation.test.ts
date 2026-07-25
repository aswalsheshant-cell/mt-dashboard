import { describe, it, expect } from 'vitest';
import { validatePage } from '@/utils/validation';
import type { Page } from '@mt-dashboard/layout-schema';

const basePage = (): Page => ({
  id: 'p1',
  name: 'Page 1',
  size: { width: 1280, height: 720, unit: 'px' },
  background: { color: '#FFFFFF', imageTransparency: 0 },
  visuals: [],
  groups: [],
  filters: [],
  gridSize: 10,
  snapToGrid: true,
  mobileLayout: false,
});

const baseVisual = () => ({
  id: 'v1',
  type: 'kpi-card' as const,
  title: 'Revenue',
  subtitle: '',
  x: 10, y: 10,
  width: 220, height: 100,
  zIndex: 0,
  locked: false, hidden: false,
  measures: [{ field: 'Revenue', aggregation: 'sum' as const }],
  categories: [], series: [], filters: [],
  interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true },
  tooltip: { enabled: true, fields: [] },
  drillthrough: { enabled: false, passFilters: [] },
  formatting: {
    fontWeight: 'normal' as const, padding: 8, borderWidth: 0, borderRadius: 4,
    legendVisible: true, legendPosition: 'bottom' as const,
    dataLabelsVisible: false, xAxisVisible: true, yAxisVisible: true,
    gridLinesVisible: true, colorPalette: [], titleVisible: true, titleFontSize: 14,
  },
  accessibilityLabel: 'Revenue KPI',
});

describe('validatePage', () => {
  it('returns info issue for empty page', () => {
    const issues = validatePage(basePage());
    expect(issues).toHaveLength(1);
    expect(issues[0].severity).toBe('info');
  });

  it('no issues for a fully specified valid visual', () => {
    const page = { ...basePage(), visuals: [baseVisual()] };
    const issues = validatePage(page);
    expect(issues.filter((i) => i.severity === 'error')).toHaveLength(0);
  });

  it('warns on missing accessibility label', () => {
    const visual = { ...baseVisual(), accessibilityLabel: '' };
    const page = { ...basePage(), visuals: [visual] };
    const issues = validatePage(page);
    expect(issues.some((i) => i.field === 'accessibilityLabel' && i.severity === 'warning')).toBe(true);
  });

  it('errors on missing measure for kpi-card', () => {
    const visual = { ...baseVisual(), measures: [] };
    const page = { ...basePage(), visuals: [visual] };
    const issues = validatePage(page);
    expect(issues.some((i) => i.field === 'measures' && i.severity === 'error')).toBe(true);
  });

  it('warns when visual extends beyond canvas', () => {
    const visual = { ...baseVisual(), x: 1200, width: 500 }; // exceeds 1280
    const page = { ...basePage(), visuals: [visual] };
    const issues = validatePage(page);
    expect(issues.some((i) => i.severity === 'warning' && /beyond/.test(i.message))).toBe(true);
  });

  it('info for placeholder visuals', () => {
    const visual = { ...baseVisual(), id: 'v2', type: 'map-placeholder' as const, measures: [], accessibilityLabel: 'Map' };
    const page = { ...basePage(), visuals: [visual] };
    const issues = validatePage(page);
    expect(issues.some((i) => i.severity === 'info' && /placeholder/.test(i.message))).toBe(true);
  });
});
