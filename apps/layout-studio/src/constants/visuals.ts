import type { VisualType } from '@mt-dashboard/layout-schema';

export interface VisualMeta {
  type: VisualType;
  label: string;
  icon: string;
  category: 'kpi' | 'chart' | 'data' | 'filter' | 'layout';
  description: string;
}

export const VISUAL_CATALOG: VisualMeta[] = [
  // KPI
  { type: 'kpi-card',    label: 'KPI Card',     icon: '📊', category: 'kpi',    description: 'Single metric with trend indicator' },
  // Charts
  { type: 'bar-chart',   label: 'Bar Chart',    icon: '📉', category: 'chart',  description: 'Horizontal bar comparison' },
  { type: 'column-chart',label: 'Column Chart', icon: '📈', category: 'chart',  description: 'Vertical column comparison' },
  { type: 'line-chart',  label: 'Line Chart',   icon: '〰️', category: 'chart',  description: 'Trend over time' },
  { type: 'combo-chart', label: 'Combo Chart',  icon: '📊', category: 'chart',  description: 'Bar + line on same axis' },
  { type: 'pie-chart',   label: 'Pie Chart',    icon: '🥧', category: 'chart',  description: 'Part-to-whole distribution' },
  { type: 'donut-chart', label: 'Donut Chart',  icon: '🍩', category: 'chart',  description: 'Donut variant with centre metric' },
  { type: 'gauge',       label: 'Gauge',        icon: '🎯', category: 'chart',  description: 'Single metric vs. target' },
  { type: 'funnel',      label: 'Funnel',       icon: '⬇️', category: 'chart',  description: 'Stage-to-stage conversion' },
  { type: 'treemap',     label: 'Treemap',      icon: '🗂️', category: 'chart',  description: 'Hierarchical proportional area' },
  // Data
  { type: 'table',       label: 'Table',        icon: '📋', category: 'data',   description: 'Flat tabular data grid' },
  { type: 'matrix',      label: 'Matrix',       icon: '🧮', category: 'data',   description: 'Cross-tab with row/column totals' },
  // Filters
  { type: 'slicer',      label: 'Slicer',       icon: '🔪', category: 'filter', description: 'Interactive filter control' },
  // Layout
  { type: 'text',        label: 'Text Box',     icon: '📝', category: 'layout', description: 'Static label or annotation' },
  { type: 'image-placeholder', label: 'Image',  icon: '🖼️', category: 'layout', description: 'Image or logo placeholder' },
  // Placeholders (require Power BI Desktop)
  { type: 'decomposition-tree-placeholder', label: 'Decomp Tree', icon: '🌳', category: 'chart', description: 'Decomposition tree — placeholder only' },
  { type: 'map-placeholder',                label: 'Map',         icon: '🗺️', category: 'chart', description: 'Map visual — placeholder only' },
];

export const VISUAL_CATALOG_BY_CATEGORY = VISUAL_CATALOG.reduce<Record<string, VisualMeta[]>>(
  (acc, v) => {
    if (!acc[v.category]) acc[v.category] = [];
    acc[v.category].push(v);
    return acc;
  },
  {}
);

export function getVisualMeta(type: VisualType): VisualMeta {
  return VISUAL_CATALOG.find((v) => v.type === type) ?? {
    type,
    label: type,
    icon: '⬜',
    category: 'layout',
    description: '',
  };
}
