import type { Layout } from '@mt-dashboard/layout-schema';
import { exportLayout, validateLayout, SCHEMA_VERSION } from '@mt-dashboard/layout-schema';
import { validatePage } from './validation';

/**
 * Export layout JSON — validates, rejects secrets, downloads the file.
 * Throws on validation failure or detected secret patterns.
 */
export function exportLayoutJSON(layout: Layout): void {
  const result = validateLayout(layout);
  if (!result.success) {
    throw new Error(`Layout validation failed:\n${result.errors.join('\n')}`);
  }
  // Deterministic: sort visual IDs within each page for stable output
  const sortedLayout: Layout = {
    ...result.data,
    pages: result.data.pages.map((p) => ({
      ...p,
      visuals: [...p.visuals].sort((a, b) => a.id.localeCompare(b.id)),
    })),
  };
  const json = exportLayout(sortedLayout);
  assertNoSecrets(json);
  const filename = `${layout.projectName.replace(/[^a-z0-9_-]/gi, '_')}_layout_v${SCHEMA_VERSION}.json`;
  downloadTextFile(json, filename, 'application/json');
}

/** Generate a human-readable PDF implementation guide as text (caller renders to PDF) */
export function generateImplementationGuide(layout: Layout): string {
  const now = new Date().toISOString();
  const lines: string[] = [
    '================================================================',
    'POWER BI PAGE LAYOUT — IMPLEMENTATION GUIDE',
    `DESIGN SPECIFICATION ONLY — This is not a PBIX or PBIR file.`,
    `Generated: ${now}`,
    `Schema Version: ${SCHEMA_VERSION}`,
    `Project: ${layout.projectName} (${layout.projectId})`,
    `Author: ${layout.author ?? 'Unknown'}`,
    '================================================================',
    '',
  ];

  layout.pages.forEach((page, pi) => {
    lines.push(`PAGE ${pi + 1}: ${page.name}`);
    lines.push(`  Canvas: ${page.size.width} × ${page.size.height} ${page.size.unit}`);
    lines.push(`  Background: ${page.background.color}`);
    lines.push(`  Grid: ${page.gridSize}px, Snap: ${page.snapToGrid ? 'ON' : 'OFF'}`);
    lines.push(`  Mobile layout: ${page.mobileLayout ? 'Yes' : 'No'}`);
    lines.push('');

    lines.push(`  VISUAL INVENTORY (${page.visuals.length} visuals):`);
    page.visuals.forEach((v, vi) => {
      lines.push(`  ${vi + 1}. [${v.type}] "${v.title || '(no title)'}" (ID: ${v.id})`);
      lines.push(`     Position: x=${v.x}, y=${v.y}  Size: ${v.width}×${v.height}  z=${v.zIndex}`);
      lines.push(`     Locked: ${v.locked}  Hidden: ${v.hidden}`);
      if (v.measures.length) lines.push(`     Measures: ${v.measures.map((m) => m.field).join(', ')}`);
      if (v.categories.length) lines.push(`     Categories: ${v.categories.map((c) => c.field).join(', ')}`);
      if (v.series.length) lines.push(`     Series: ${v.series.map((s) => s.field).join(', ')}`);
      if (v.filters.length) lines.push(`     Filters: ${v.filters.map((f) => `${f.field} ${f.operator}`).join('; ')}`);
      if (v.accessibilityLabel) lines.push(`     Accessibility: "${v.accessibilityLabel}"`);
      if (v.type.includes('placeholder')) lines.push(`     ⚠ PLACEHOLDER — create actual visual in Power BI Desktop`);
      if (v.mobileOverride) {
        lines.push(`     Mobile override: hidden=${v.mobileOverride.hidden}${v.mobileOverride.order !== undefined ? `, order=${v.mobileOverride.order}` : ''}`);
      }
      lines.push('');
    });

    // Groups
    if (page.groups.length) {
      lines.push(`  GROUPS (${page.groups.length}):`);
      page.groups.forEach((g) => {
        lines.push(`    "${g.name}": [${g.visualIds.join(', ')}]`);
      });
      lines.push('');
    }

    // Page filters
    if (page.filters.length) {
      lines.push(`  PAGE-LEVEL FILTERS:`);
      page.filters.forEach((f) => {
        lines.push(`    ${f.field} ${f.operator} ${JSON.stringify(f.values)}`);
      });
      lines.push('');
    }

    // Validation issues
    const issues = validatePage(page);
    if (issues.length) {
      lines.push(`  VALIDATION (${issues.length} issues):`);
      issues.forEach((i) => {
        const icon = i.severity === 'error' ? '✕' : i.severity === 'warning' ? '⚠' : 'ℹ';
        lines.push(`    ${icon} ${i.message}`);
      });
      lines.push('');
    }

    lines.push('  IMPLEMENTATION NOTES:');
    lines.push('  • Visuals marked PLACEHOLDER must be created in Power BI Desktop.');
    lines.push('  • Coordinates are in pixels relative to the top-left canvas corner.');
    lines.push('  • Bind each measure/category to the corresponding Power BI field.');
    lines.push('  • Apply Honasa design tokens from packages/design-tokens/ for colours.');
    lines.push('  • Enable cross-filtering as specified in each visual\'s interactions.');
    lines.push('');
    lines.push('================================================================');
    lines.push('');
  });

  lines.push('DISCLAIMER: This document is a design specification created in');
  lines.push('Layout Studio. It is not an actual Power BI file (PBIX/PBIR).');
  lines.push('CM2 figures and provisional data require Finance approval before use.');
  lines.push('');
  lines.push(`Source: Layout Studio — ${layout.projectName}`);
  lines.push(`Exported: ${now}`);

  return lines.join('\n');
}

/** Download a string as a file */
export function downloadTextFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a') as HTMLAnchorElement;
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Validate that no secrets are present in the layout JSON */
export function assertNoSecrets(json: string): void {
  const secretPatterns = [/sk-[A-Za-z0-9]{20,}/, /ghp_[A-Za-z0-9]{36}/, /Bearer\s+[A-Za-z0-9+/=]{20,}/];
  for (const pattern of secretPatterns) {
    if (pattern.test(json)) {
      throw new Error('Export blocked: potential secret detected in layout data. Remove credentials before exporting.');
    }
  }
}
