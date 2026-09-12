import type { Page } from '@mt-dashboard/layout-schema';

export interface TemplateMetadata {
  id: string;
  name: string;
  description: string;
  audience: string;
  businessQuestion: string;
  recommendedKPIs: string[];
  requiredDataFields: string[];
  unavailableDataBehavior: string;
  mobileLayoutGuidance: string;
  implementationNotes: string;
  tags: string[];
  thumbnail?: string;
}

export interface DashboardTemplate {
  metadata: TemplateMetadata;
  page: Omit<Page, 'id'>;
}

// Helper: standard filter slicer at top-left
const filterSlicer = (id: string, title: string, field: string, x: number, y: number) => ({
  id,
  type: 'slicer' as const,
  title,
  subtitle: '',
  x, y,
  width: 160, height: 180,
  zIndex: 1, locked: false, hidden: false,
  measures: [], categories: [{ field, aggregation: 'none' as const }], series: [],
  filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true },
  tooltip: { enabled: true, fields: [], reportPage: undefined },
  drillthrough: { enabled: false, passFilters: [] },
  formatting: { titleVisible: true, titleFontSize: 12, fontWeight: 'normal' as const, padding: 8, borderWidth: 0, borderRadius: 4, legendVisible: false, legendPosition: 'bottom' as const, dataLabelsVisible: false, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: [] },
  accessibilityLabel: `${title} filter slicer`,
});

const kpiCard = (id: string, title: string, field: string, x: number, y: number) => ({
  id,
  type: 'kpi-card' as const,
  title,
  subtitle: '[Placeholder — bind measure]',
  x, y,
  width: 220, height: 100,
  zIndex: 2, locked: false, hidden: false,
  measures: [{ field, aggregation: 'sum' as const }], categories: [], series: [],
  filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true },
  tooltip: { enabled: true, fields: [] },
  drillthrough: { enabled: false, passFilters: [] },
  formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'bold' as const, padding: 12, borderWidth: 1, borderRadius: 8, legendVisible: false, legendPosition: 'bottom' as const, dataLabelsVisible: true, xAxisVisible: false, yAxisVisible: false, gridLinesVisible: false, colorPalette: [] },
  accessibilityLabel: `${title} KPI value`,
});

// ── 1. Executive Overview ─────────────────────────────────────────────────────
export const executiveOverview: DashboardTemplate = {
  metadata: {
    id: 'executive-overview',
    name: 'Executive Overview',
    description: 'High-level MT performance dashboard for leadership. Single-page summary of revenue, distribution, and growth vs. plan.',
    audience: 'MT Leadership / CXO',
    businessQuestion: 'Are we on track against plan this month/quarter/FY?',
    recommendedKPIs: ['NSV (Lacs)', 'Primary Sales (Lacs)', 'Offtake (Lacs)', 'Store Count', 'SKU Fill Rate', 'vs Plan %'],
    requiredDataFields: ['Month', 'FY', 'NSV', 'Primary', 'Offtake', 'Plan', 'BrandName'],
    unavailableDataBehavior: 'Show "Data unavailable for [period]" in each card. Do not show zero or blank values that imply data exists.',
    mobileLayoutGuidance: 'Stack KPI cards vertically. Hide trend charts on mobile to prioritise current-period values. Use mobile override to order: total → brand cards → trend.',
    implementationNotes: 'Link FY slicer to all visuals. Provisional CM2 must show warning banner if cm2.provisional=true in data.js.',
    tags: ['overview', 'executive', 'leadership'],
  },
  page: {
    name: 'Executive Overview',
    size: { width: 1280, height: 720, unit: 'px' },
    background: { color: '#F8FAFC', imageTransparency: 0 },
    gridSize: 10, snapToGrid: true, mobileLayout: false,
    filters: [],
    groups: [],
    visuals: [
      filterSlicer('s1', 'FY', 'FY', 20, 20),
      filterSlicer('s2', 'Month', 'Month', 190, 20),
      filterSlicer('s3', 'Brand', 'BrandName', 360, 20),
      kpiCard('k1', 'NSV (Lacs)', 'NSV', 550, 20),
      kpiCard('k2', 'Primary (Lacs)', 'Primary', 780, 20),
      kpiCard('k3', 'Offtake (Lacs)', 'Offtake', 1010, 20),
      { id: 'c1', type: 'line-chart', title: 'Monthly NSV vs Plan', subtitle: 'FY trend', x: 20, y: 220, width: 580, height: 280, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'NSV', aggregation: 'sum' }, { field: 'Plan', aggregation: 'sum' }], categories: [{ field: 'Month', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: true, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#00A896', '#9CA3AF'] }, accessibilityLabel: 'Monthly NSV trend versus plan', mobileOverride: { hidden: false, order: 3 } },
      { id: 'c2', type: 'bar-chart', title: 'Brand Split — Offtake', subtitle: 'Current month', x: 620, y: 220, width: 620, height: 280, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Offtake', aggregation: 'sum' }], categories: [{ field: 'BrandName', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: true, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#00A896'] }, accessibilityLabel: 'Offtake by brand', mobileOverride: { hidden: true } },
      { id: 't1', type: 'table', title: 'KPI Summary — All Brands', subtitle: 'Current FY', x: 20, y: 520, width: 1220, height: 180, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Primary', aggregation: 'sum' }, { field: 'Offtake', aggregation: 'sum' }, { field: 'NSV', aggregation: 'sum' }, { field: 'Plan', aggregation: 'sum' }], categories: [{ field: 'BrandName', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: true, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: true, targetPage: 'Primary Sales', passFilters: ['BrandName'] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 8, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: false, yAxisVisible: false, gridLinesVisible: true, colorPalette: [] }, accessibilityLabel: 'KPI summary table by brand' },
    ],
  },
};

// ── 2. Primary Sales ──────────────────────────────────────────────────────────
export const primarySales: DashboardTemplate = {
  metadata: {
    id: 'primary-sales',
    name: 'Primary Sales',
    description: 'Distributor-to-retailer primary billing analysis by brand, category, and channel.',
    audience: 'MT Sales Team / Trade Marketing',
    businessQuestion: 'What are primary billing volumes by brand and channel this month/FY?',
    recommendedKPIs: ['Primary (Lacs)', 'MRP (Lacs)', 'NSV (Lacs)', 'vs LY %', 'Billing Count'],
    requiredDataFields: ['Month', 'FY', 'BrandName', 'Category', 'Channel', 'Primary', 'MRP', 'NSV'],
    unavailableDataBehavior: 'Show months with no data as empty rows in table. Trend line breaks at missing months.',
    mobileLayoutGuidance: 'Show KPIs and channel table only. Hide the brand trend chart on mobile.',
    implementationNotes: 'Excluded brands (Pure Origin, Lumineve, Staze) must not appear. FY derived from month+year using THE ONE FY RULE.',
    tags: ['primary', 'sales', 'billing'],
  },
  page: {
    name: 'Primary Sales',
    size: { width: 1280, height: 720, unit: 'px' },
    background: { color: '#F8FAFC', imageTransparency: 0 },
    gridSize: 10, snapToGrid: true, mobileLayout: false,
    filters: [],
    groups: [],
    visuals: [
      filterSlicer('s1', 'FY', 'FY', 20, 20),
      filterSlicer('s2', 'Month', 'Month', 190, 20),
      filterSlicer('s3', 'Brand', 'BrandName', 360, 20),
      filterSlicer('s4', 'Category', 'Category', 530, 20),
      kpiCard('k1', 'Primary (Lacs)', 'Primary', 720, 20),
      kpiCard('k2', 'MRP (Lacs)', 'MRP', 950, 20),
      { id: 'c1', type: 'column-chart', title: 'Primary by Brand — Monthly', subtitle: 'Lacs', x: 20, y: 220, width: 620, height: 300, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Primary', aggregation: 'sum' }], categories: [{ field: 'Month', aggregation: 'none' }], series: [{ field: 'BrandName', aggregation: 'none' }], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: true, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#00A896', '#2196F3', '#FF9800', '#9C27B0'] }, accessibilityLabel: 'Primary billing by brand per month' },
      { id: 'c2', type: 'bar-chart', title: 'Primary by Category', subtitle: 'Current filter selection', x: 660, y: 220, width: 580, height: 300, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Primary', aggregation: 'sum' }], categories: [{ field: 'Category', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: true, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#00A896'] }, accessibilityLabel: 'Primary billing by category' },
      { id: 't1', type: 'matrix', title: 'Primary Matrix — Brand × Month', subtitle: 'Lacs', x: 20, y: 540, width: 1220, height: 160, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Primary', aggregation: 'sum' }], categories: [{ field: 'BrandName', aggregation: 'none' }], series: [{ field: 'Month', aggregation: 'none' }], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: true, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 8, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: false, yAxisVisible: false, gridLinesVisible: true, colorPalette: [] }, accessibilityLabel: 'Primary sales matrix by brand and month' },
    ],
  },
};

// ── 3. Offtake Sales ──────────────────────────────────────────────────────────
export const offtakeSales: DashboardTemplate = {
  metadata: {
    id: 'offtake-sales',
    name: 'Offtake Sales',
    description: 'Store-level consumer offtake (sell-out) analysis by chain, brand, and category.',
    audience: 'MT Sales Team / Category Management',
    businessQuestion: 'What are consumers buying at store level and which SKUs are moving?',
    recommendedKPIs: ['Offtake (Lacs)', 'Store Count', 'Avg Offtake per Store', 'SKU Velocity', 'vs LY %'],
    requiredDataFields: ['Month', 'FY', 'BrandName', 'Category', 'Chain', 'EAN', 'Offtake', 'StoreCount'],
    unavailableDataBehavior: 'Show "Offtake data not available for [month/chain]". Do not extrapolate missing months.',
    mobileLayoutGuidance: 'Show top-5 SKU table and total offtake KPI only on mobile.',
    implementationNotes: 'Net-negative offtake (returns) must be preserved — do not drop. Excluded brands must not appear.',
    tags: ['offtake', 'sell-out', 'consumer'],
  },
  page: {
    name: 'Offtake Sales',
    size: { width: 1280, height: 720, unit: 'px' },
    background: { color: '#F8FAFC', imageTransparency: 0 },
    gridSize: 10, snapToGrid: true, mobileLayout: false,
    filters: [],
    groups: [],
    visuals: [
      filterSlicer('s1', 'FY', 'FY', 20, 20),
      filterSlicer('s2', 'Month', 'Month', 190, 20),
      filterSlicer('s3', 'Chain', 'Chain', 360, 20),
      filterSlicer('s4', 'Brand', 'BrandName', 530, 20),
      kpiCard('k1', 'Offtake (Lacs)', 'Offtake', 720, 20),
      kpiCard('k2', 'Store Count', 'StoreCount', 950, 20),
      { id: 'c1', type: 'line-chart', title: 'Monthly Offtake Trend', subtitle: 'Lacs by brand', x: 20, y: 220, width: 620, height: 300, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Offtake', aggregation: 'sum' }], categories: [{ field: 'Month', aggregation: 'none' }], series: [{ field: 'BrandName', aggregation: 'none' }], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [{ field: 'StoreCount', aggregation: 'sum' }] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: true, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#00A896', '#2196F3', '#FF9800'] }, accessibilityLabel: 'Monthly offtake trend by brand' },
      { id: 'c2', type: 'bar-chart', title: 'Top Chains by Offtake', subtitle: 'Current selection', x: 660, y: 220, width: 580, height: 300, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Offtake', aggregation: 'sum' }], categories: [{ field: 'Chain', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: true, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#00A896'] }, accessibilityLabel: 'Offtake by chain' },
      { id: 't1', type: 'table', title: 'Offtake Detail — Top SKUs', subtitle: 'Sorted by offtake desc', x: 20, y: 540, width: 1220, height: 160, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Offtake', aggregation: 'sum' }, { field: 'StoreCount', aggregation: 'sum' }], categories: [{ field: 'EAN', aggregation: 'none' }, { field: 'BrandName', aggregation: 'none' }, { field: 'Category', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 8, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: false, yAxisVisible: false, gridLinesVisible: true, colorPalette: [] }, accessibilityLabel: 'SKU-level offtake detail table' },
    ],
  },
};

// ── 4–12 remaining templates (abbreviated for size; full structure mirrors above) ──

export const primaryVsOfftake: DashboardTemplate = {
  metadata: {
    id: 'primary-vs-offtake',
    name: 'Primary vs Offtake',
    description: 'Side-by-side comparison of distributor billing versus consumer sell-out to identify trade loading vs. genuine demand.',
    audience: 'MT Sales / Category Management',
    businessQuestion: 'Where is sell-in exceeding sell-out? Which channels are over-stocked?',
    recommendedKPIs: ['Primary (Lacs)', 'Offtake (Lacs)', 'Fill Rate %', 'Primary–Offtake Gap', 'Weeks of Cover'],
    requiredDataFields: ['Month', 'FY', 'BrandName', 'Chain', 'Primary', 'Offtake'],
    unavailableDataBehavior: 'Show "—" for channels where offtake data is not available. Do not infer offtake from primary.',
    mobileLayoutGuidance: 'Stack combo chart above gap table. Hide secondary trend on mobile.',
    implementationNotes: 'Gap = Primary − Offtake. Negative gap (offtake > primary) is valid and must be shown.',
    tags: ['comparison', 'fill-rate', 'gap-analysis'],
  },
  page: {
    name: 'Primary vs Offtake',
    size: { width: 1280, height: 720, unit: 'px' },
    background: { color: '#F8FAFC', imageTransparency: 0 },
    gridSize: 10, snapToGrid: true, mobileLayout: false,
    filters: [], groups: [],
    visuals: [
      filterSlicer('s1', 'FY', 'FY', 20, 20),
      filterSlicer('s2', 'Brand', 'BrandName', 190, 20),
      kpiCard('k1', 'Primary (Lacs)', 'Primary', 380, 20),
      kpiCard('k2', 'Offtake (Lacs)', 'Offtake', 610, 20),
      kpiCard('k3', 'Gap (Lacs)', 'Gap', 840, 20),
      { id: 'c1', type: 'combo-chart', title: 'Primary vs Offtake — Monthly', subtitle: 'Bars = Primary, Line = Offtake', x: 20, y: 220, width: 820, height: 320, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Primary', aggregation: 'sum' }, { field: 'Offtake', aggregation: 'sum' }], categories: [{ field: 'Month', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: true, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#00A896', '#2196F3'] }, accessibilityLabel: 'Primary billing versus offtake monthly combo chart' },
      { id: 'c2', type: 'bar-chart', title: 'Gap by Chain', subtitle: 'Primary − Offtake', x: 860, y: 220, width: 400, height: 320, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Gap', aggregation: 'sum' }], categories: [{ field: 'Chain', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: true, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#FF9800'] }, accessibilityLabel: 'Primary-offtake gap by chain' },
      { id: 't1', type: 'table', title: 'Brand × Chain Gap Analysis', subtitle: 'Lacs', x: 20, y: 560, width: 1220, height: 140, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'Primary', aggregation: 'sum' }, { field: 'Offtake', aggregation: 'sum' }, { field: 'Gap', aggregation: 'sum' }], categories: [{ field: 'BrandName', aggregation: 'none' }, { field: 'Chain', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 8, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: false, yAxisVisible: false, gridLinesVisible: true, colorPalette: [] }, accessibilityLabel: 'Gap analysis matrix by brand and chain' },
    ],
  },
};

// Templates 5–12 use the same structural pattern; defined here as stubs to keep file size manageable.
// Each contains full metadata and a representative page layout with slicers, KPIs, charts, and tables.

const stubTemplate = (id: string, name: string, audience: string, question: string, kpis: string[], fields: string[], tags: string[]): DashboardTemplate => ({
  metadata: {
    id, name,
    description: `${name} template for the Honasa MT Analytics Platform.`,
    audience, businessQuestion: question,
    recommendedKPIs: kpis,
    requiredDataFields: fields,
    unavailableDataBehavior: `Show "Data unavailable" placeholder for missing ${name.toLowerCase()} data.`,
    mobileLayoutGuidance: 'Stack KPI cards on top, show one primary chart below, table last.',
    implementationNotes: `Configure ${name} visuals against the governed data model. Excluded brands must not appear.`,
    tags,
  },
  page: {
    name,
    size: { width: 1280, height: 720, unit: 'px' },
    background: { color: '#F8FAFC', imageTransparency: 0 },
    gridSize: 10, snapToGrid: true, mobileLayout: false,
    filters: [], groups: [],
    visuals: [
      filterSlicer('s1', 'FY', 'FY', 20, 20),
      filterSlicer('s2', 'Month', 'Month', 190, 20),
      kpiCard('k1', kpis[0] || 'KPI', fields[2] || 'Measure', 380, 20),
      kpiCard('k2', kpis[1] || 'KPI 2', fields[3] || 'Measure2', 610, 20),
      { id: 'c1', type: 'line-chart', title: `${name} Trend`, subtitle: 'Monthly', x: 20, y: 220, width: 820, height: 300, zIndex: 2, locked: false, hidden: false, measures: [{ field: fields[2] || 'Value', aggregation: 'sum' }], categories: [{ field: 'Month', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: true, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#00A896'] }, accessibilityLabel: `${name} monthly trend` },
      { id: 't1', type: 'table', title: `${name} Detail`, subtitle: '', x: 20, y: 540, width: 1220, height: 160, zIndex: 2, locked: false, hidden: false, measures: fields.slice(2).map(f => ({ field: f, aggregation: 'sum' as const })), categories: [{ field: fields[0] || 'Dim1', aggregation: 'none' as const }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 8, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: false, yAxisVisible: false, gridLinesVisible: true, colorPalette: [] }, accessibilityLabel: `${name} detail table` },
    ],
  },
});

export const performanceComparison = stubTemplate(
  'performance-comparison', 'Performance & Comparison', 'MT Sales Leadership',
  'How does performance compare across brands, periods, and channels?',
  ['vs LY %', 'vs Plan %', 'CAGR', 'Growth Index'],
  ['Month', 'FY', 'BrandName', 'Primary', 'PrimaryLY', 'Plan'],
  ['performance', 'comparison', 'growth']
);

export const categoryPack = stubTemplate(
  'category-pack', 'Category & Pack', 'Category Management',
  'Which pack sizes and categories are driving growth?',
  ['Category Share %', 'Pack Contribution %', 'Volume (Lacs)', 'Unit Count'],
  ['Month', 'FY', 'Category', 'PackSize', 'BrandName', 'Volume', 'NSV'],
  ['category', 'pack', 'mix']
);

export const forecast = stubTemplate(
  'forecast', 'Forecast', 'Sales Planning / Finance',
  'What is the forecast versus actuals and how is accuracy tracking?',
  ['Forecast (Lacs)', 'Actuals (Lacs)', 'Forecast Accuracy %', 'Bias %'],
  ['Month', 'FY', 'BrandName', 'Forecast', 'Actual', 'Plan'],
  ['forecast', 'planning', 'accuracy']
);

export const distribution = stubTemplate(
  'distribution', 'Distribution', 'Field Sales / Key Accounts',
  'How many stores are billing and what is numeric distribution?',
  ['Billing Stores', 'Total Universe', 'Numeric Distribution %', 'SKU per Store'],
  ['Month', 'FY', 'Chain', 'BrandName', 'BillingStores', 'Universe', 'SKUperStore'],
  ['distribution', 'stores', 'numeric-distribution']
);

export const pandl = stubTemplate(
  'pandl', 'P&L', 'Finance / MT Leadership',
  'What is the profitability picture across gross margin components?',
  ['Gross Sales (Lacs)', 'NSV (Lacs)', 'Gross Margin %', 'EBITDA %'],
  ['Month', 'FY', 'BrandName', 'GrossSales', 'NSV', 'GrossMargin', 'EBITDA'],
  ['pnl', 'profitability', 'margin']
);

export const cm2Provisional: DashboardTemplate = {
  metadata: {
    id: 'cm2-provisional',
    name: 'CM2 Provisional',
    description: 'PROVISIONAL CM2 dashboard page — for internal use only pending Finance approval of D1 (COGS) and D9 (allocation rules). CM2 figures are estimates and must not be shared externally.',
    audience: 'Internal MT Finance / Data Engineering (NOT for external sharing)',
    businessQuestion: 'What is the estimated CM2 by brand/chain? (PROVISIONAL — formula approval pending)',
    recommendedKPIs: ['CM2 Provisional (Lacs)', 'CM2 % of NSV', 'COGS (Provisional)', 'Logistics (Provisional)'],
    requiredDataFields: ['Month', 'FY', 'BrandName', 'NSV', 'CM2Provisional', 'COGS', 'Logistics', 'FormulaStatus'],
    unavailableDataBehavior: 'Show "CM2 PROVISIONAL — FORMULA APPROVAL PENDING" banner when formula_status=DRAFT.',
    mobileLayoutGuidance: 'Show provisional warning banner prominently at top. Stack KPIs below banner.',
    implementationNotes: 'CRITICAL: Show warning banner when cm2.provisional=true. Approved CM2 measure must return BLANK when D1/D9 pending. Do not show approved CM2 alongside provisional values.',
    tags: ['cm2', 'provisional', 'internal-only', 'pending-approval'],
  },
  page: {
    name: 'CM2 Provisional',
    size: { width: 1280, height: 720, unit: 'px' },
    background: { color: '#FEF3C7', imageTransparency: 0 },
    gridSize: 10, snapToGrid: true, mobileLayout: false,
    filters: [], groups: [],
    visuals: [
      { id: 'banner', type: 'text', title: '⚠ CM2 PROVISIONAL — FORMULA APPROVAL PENDING (D1, D9) — INTERNAL USE ONLY — NOT FOR EXTERNAL DISTRIBUTION', subtitle: '', x: 20, y: 10, width: 1240, height: 50, zIndex: 10, locked: true, hidden: false, measures: [], categories: [], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: false }, tooltip: { enabled: false, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 12, fontWeight: 'bold', backgroundColor: '#FCD34D', fontColor: '#92400E', padding: 10, borderWidth: 2, borderColor: '#F59E0B', borderRadius: 4, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: false, yAxisVisible: false, gridLinesVisible: false, colorPalette: [] }, accessibilityLabel: 'Provisional CM2 warning banner — formula approval pending' },
      filterSlicer('s1', 'FY', 'FY', 20, 70),
      filterSlicer('s2', 'Brand', 'BrandName', 190, 70),
      kpiCard('k1', 'CM2 Provisional (Lacs)', 'CM2Provisional', 380, 70),
      kpiCard('k2', 'CM2 % NSV', 'CM2PctNSV', 610, 70),
      { id: 'c1', type: 'bar-chart', title: 'CM2 Provisional by Brand', subtitle: 'PROVISIONAL — not for external use', x: 20, y: 200, width: 620, height: 300, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'CM2Provisional', aggregation: 'sum' }], categories: [{ field: 'BrandName', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 12, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: true, xAxisVisible: true, yAxisVisible: true, gridLinesVisible: true, colorPalette: ['#F59E0B'] }, accessibilityLabel: 'Provisional CM2 by brand — estimates only' },
      { id: 't1', type: 'table', title: 'CM2 Component Detail (Provisional)', subtitle: 'COGS basis: GMV/MRP | Logistics basis: NSV', x: 20, y: 520, width: 1220, height: 180, zIndex: 2, locked: false, hidden: false, measures: [{ field: 'NSV', aggregation: 'sum' }, { field: 'COGS', aggregation: 'sum' }, { field: 'Logistics', aggregation: 'sum' }, { field: 'CM2Provisional', aggregation: 'sum' }], categories: [{ field: 'BrandName', aggregation: 'none' }], series: [], filters: [], interactions: { filterTargets: [], highlightTargets: [], drillthroughEnabled: false, crossFilterEnabled: true }, tooltip: { enabled: true, fields: [] }, drillthrough: { enabled: false, passFilters: [] }, formatting: { titleVisible: true, titleFontSize: 14, fontWeight: 'semibold', padding: 8, borderWidth: 0, borderRadius: 8, legendVisible: false, legendPosition: 'bottom', dataLabelsVisible: false, xAxisVisible: false, yAxisVisible: false, gridLinesVisible: true, colorPalette: [] }, accessibilityLabel: 'CM2 component detail table — provisional values' },
    ],
  },
};

export const dataQcReconciliation = stubTemplate(
  'data-qc-reconciliation', 'Data QC & Reconciliation', 'Data Engineering / Finance',
  'Are the numbers in the dashboard complete, consistent, and reconciled against source?',
  ['Unmapped EANs', 'Blank Brand Count', 'Primary vs Source Diff', 'Last Refresh'],
  ['Month', 'FY', 'EAN', 'BrandName', 'SourceValue', 'DashboardValue', 'DiffValue'],
  ['data-quality', 'reconciliation', 'qc']
);

export const insightsActions = stubTemplate(
  'insights-actions', 'Insights & Actions', 'MT Leadership / Sales',
  'What are the top opportunities and risks and what actions should be taken?',
  ['Top Opportunity (Lacs)', 'Top Risk (Lacs)', 'Action Items', 'Owner'],
  ['Month', 'FY', 'Insight', 'Category', 'Value', 'Priority', 'Owner'],
  ['insights', 'actions', 'narrative']
);

// ── Template registry ─────────────────────────────────────────────────────────
export const TEMPLATES: DashboardTemplate[] = [
  executiveOverview,
  primarySales,
  offtakeSales,
  primaryVsOfftake,
  performanceComparison,
  categoryPack,
  forecast,
  distribution,
  pandl,
  cm2Provisional,
  dataQcReconciliation,
  insightsActions,
];

export const TEMPLATE_INDEX: Record<string, DashboardTemplate> = Object.fromEntries(
  TEMPLATES.map((t) => [t.metadata.id, t])
);

export function getTemplate(id: string): DashboardTemplate | undefined {
  return TEMPLATE_INDEX[id];
}

export function listTemplates(): TemplateMetadata[] {
  return TEMPLATES.map((t) => t.metadata);
}
