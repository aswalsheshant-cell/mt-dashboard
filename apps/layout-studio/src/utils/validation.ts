import type { Page, Visual } from '@mt-dashboard/layout-schema';
import type { ValidationIssue } from '@/types';

export function validatePage(page: Page): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  page.visuals.forEach((v) => {
    // Missing accessibility label
    if (!v.accessibilityLabel?.trim()) {
      issues.push({
        visualId: v.id,
        severity: 'warning',
        message: `"${v.title || v.type}" is missing an accessibility label.`,
        field: 'accessibilityLabel',
      });
    }

    // Out of canvas bounds
    if (v.x < 0 || v.y < 0) {
      issues.push({ visualId: v.id, severity: 'error', message: `"${v.title || v.type}" is outside the canvas (negative coordinates).` });
    }
    if (v.x + v.width > page.size.width + 1 || v.y + v.height > page.size.height + 1) {
      issues.push({ visualId: v.id, severity: 'warning', message: `"${v.title || v.type}" extends beyond the canvas boundary.` });
    }

    // Missing measure on chart types
    const chartTypes: Visual['type'][] = ['bar-chart','column-chart','line-chart','combo-chart','pie-chart','donut-chart','gauge','funnel','treemap','kpi-card'];
    if (chartTypes.includes(v.type) && !v.measures.length) {
      issues.push({ visualId: v.id, severity: 'error', message: `"${v.title || v.type}" has no measure bound.`, field: 'measures' });
    }

    // Placeholder visuals
    if (v.type === 'decomposition-tree-placeholder' || v.type === 'map-placeholder') {
      issues.push({ visualId: v.id, severity: 'info', message: `"${v.title || v.type}" is a placeholder — the actual Power BI visual must be created in Power BI Desktop.` });
    }
  });

  // Overlap detection (warn on significant overlap)
  for (let i = 0; i < page.visuals.length; i++) {
    for (let j = i + 1; j < page.visuals.length; j++) {
      const a = page.visuals[i];
      const b = page.visuals[j];
      const overlapX = Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x));
      const overlapY = Math.max(0, Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y));
      const overlapArea = overlapX * overlapY;
      const minArea = Math.min(a.width * a.height, b.width * b.height);
      if (overlapArea > minArea * 0.1) {
        issues.push({
          visualId: a.id,
          severity: 'warning',
          message: `"${a.title || a.type}" overlaps with "${b.title || b.type}" by ${Math.round((overlapArea / minArea) * 100)}%.`,
        });
        break; // one warning per visual is enough
      }
    }
  }

  // No visuals at all
  if (!page.visuals.length) {
    issues.push({ visualId: null, severity: 'info', message: 'Page is empty. Add visuals to start building your layout.' });
  }

  return issues;
}
