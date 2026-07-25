import { z } from 'zod';

export const SCHEMA_VERSION = '1.0.0';

// ── Visual types supported by the Layout Studio ──────────────────────────────
export const VisualTypeSchema = z.enum([
  'kpi-card',
  'text',
  'image-placeholder',
  'bar-chart',
  'column-chart',
  'line-chart',
  'combo-chart',
  'pie-chart',
  'donut-chart',
  'table',
  'matrix',
  'slicer',
  'gauge',
  'funnel',
  'treemap',
  'decomposition-tree-placeholder',
  'map-placeholder',
]);
export type VisualType = z.infer<typeof VisualTypeSchema>;

// ── Measure / category binding ────────────────────────────────────────────────
export const BindingSchema = z.object({
  field: z.string().min(1),
  table: z.string().optional(),
  aggregation: z.enum(['sum', 'avg', 'count', 'min', 'max', 'none']).default('sum'),
  displayName: z.string().optional(),
});
export type Binding = z.infer<typeof BindingSchema>;

// ── Filter ────────────────────────────────────────────────────────────────────
export const FilterSchema = z.object({
  field: z.string().min(1),
  table: z.string().optional(),
  operator: z.enum(['eq', 'neq', 'gt', 'gte', 'lt', 'lte', 'in', 'notIn', 'contains', 'all']),
  values: z.array(z.union([z.string(), z.number(), z.boolean()])).default([]),
});
export type Filter = z.infer<typeof FilterSchema>;

// ── Interaction config ────────────────────────────────────────────────────────
export const InteractionSchema = z.object({
  filterTargets: z.array(z.string()).default([]),
  highlightTargets: z.array(z.string()).default([]),
  drillthroughEnabled: z.boolean().default(false),
  crossFilterEnabled: z.boolean().default(true),
});
export type Interaction = z.infer<typeof InteractionSchema>;

// ── Tooltip ───────────────────────────────────────────────────────────────────
export const TooltipSchema = z.object({
  enabled: z.boolean().default(true),
  fields: z.array(BindingSchema).default([]),
  reportPage: z.string().optional(),
});
export type Tooltip = z.infer<typeof TooltipSchema>;

// ── Drillthrough ──────────────────────────────────────────────────────────────
export const DrillthroughSchema = z.object({
  enabled: z.boolean().default(false),
  targetPage: z.string().optional(),
  passFilters: z.array(z.string()).default([]),
});
export type Drillthrough = z.infer<typeof DrillthroughSchema>;

// ── Formatting ────────────────────────────────────────────────────────────────
export const FormattingSchema = z.object({
  backgroundColor: z.string().optional(),
  borderColor: z.string().optional(),
  borderWidth: z.number().min(0).max(10).default(0),
  borderRadius: z.number().min(0).max(24).default(4),
  fontFamily: z.string().optional(),
  fontSize: z.number().min(8).max(72).optional(),
  fontColor: z.string().optional(),
  fontWeight: z.enum(['normal', 'bold', '600', 'semibold']).default('normal'),
  padding: z.number().min(0).max(40).default(8),
  titleVisible: z.boolean().default(true),
  titleFontSize: z.number().min(8).max(32).default(14),
  titleFontColor: z.string().optional(),
  legendVisible: z.boolean().default(true),
  legendPosition: z.enum(['top', 'bottom', 'left', 'right', 'none']).default('bottom'),
  dataLabelsVisible: z.boolean().default(false),
  xAxisVisible: z.boolean().default(true),
  yAxisVisible: z.boolean().default(true),
  gridLinesVisible: z.boolean().default(true),
  colorPalette: z.array(z.string()).default([]),
}).passthrough();
export type Formatting = z.infer<typeof FormattingSchema>;

// ── Mobile override ───────────────────────────────────────────────────────────
export const MobileOverrideSchema = z.object({
  hidden: z.boolean().default(false),
  x: z.number().optional(),
  y: z.number().optional(),
  width: z.number().optional(),
  height: z.number().optional(),
  order: z.number().int().optional(),
});
export type MobileOverride = z.infer<typeof MobileOverrideSchema>;

// ── Visual (core element) ─────────────────────────────────────────────────────
export const VisualSchema = z.object({
  id: z.string().min(1).regex(/^[a-zA-Z0-9_-]+$/, 'Visual ID must be alphanumeric with - or _'),
  type: VisualTypeSchema,
  title: z.string().default(''),
  subtitle: z.string().default(''),
  x: z.number().min(0),
  y: z.number().min(0),
  width: z.number().min(10),
  height: z.number().min(10),
  zIndex: z.number().int().min(0).max(9999).default(0),
  locked: z.boolean().default(false),
  hidden: z.boolean().default(false),
  groupId: z.string().optional(),
  measures: z.array(BindingSchema).default([]),
  categories: z.array(BindingSchema).default([]),
  series: z.array(BindingSchema).default([]),
  filters: z.array(FilterSchema).default([]),
  interactions: InteractionSchema.default({}),
  tooltip: TooltipSchema.default({}),
  drillthrough: DrillthroughSchema.default({}),
  formatting: FormattingSchema.default({}),
  accessibilityLabel: z.string().default(''),
  mobileOverride: MobileOverrideSchema.optional(),
  // Reject arbitrary executable content
  _raw: z.undefined().describe('Reserved — must not appear in valid layouts'),
}).strict();
export type Visual = z.infer<typeof VisualSchema>;

// ── Page size ─────────────────────────────────────────────────────────────────
export const PageSizeSchema = z.object({
  width: z.number().min(100).max(7680).default(1280),
  height: z.number().min(100).max(4320).default(720),
  unit: z.enum(['px', 'mm', 'in']).default('px'),
});
export type PageSize = z.infer<typeof PageSizeSchema>;

// ── Canvas background ─────────────────────────────────────────────────────────
export const CanvasBackgroundSchema = z.object({
  color: z.string().default('#FFFFFF'),
  imageUrl: z.string().optional(),
  imageTransparency: z.number().min(0).max(100).default(0),
});
export type CanvasBackground = z.infer<typeof CanvasBackgroundSchema>;

// ── Group ─────────────────────────────────────────────────────────────────────
export const VisualGroupSchema = z.object({
  id: z.string().min(1),
  name: z.string().default('Group'),
  visualIds: z.array(z.string()).min(2),
});
export type VisualGroup = z.infer<typeof VisualGroupSchema>;

// ── Page ──────────────────────────────────────────────────────────────────────
export const PageSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1).max(100),
  size: PageSizeSchema.default({}),
  background: CanvasBackgroundSchema.default({}),
  visuals: z.array(VisualSchema).default([]),
  groups: z.array(VisualGroupSchema).default([]),
  filters: z.array(FilterSchema).default([]),
  gridSize: z.number().min(1).max(100).default(10),
  snapToGrid: z.boolean().default(true),
  mobileLayout: z.boolean().default(false),
});
export type Page = z.infer<typeof PageSchema>;

// ── Root layout ───────────────────────────────────────────────────────────────
export const LayoutSchema = z.object({
  schemaVersion: z.literal(SCHEMA_VERSION),
  projectId: z.string().min(1),
  projectName: z.string().default('Untitled Layout'),
  pages: z.array(PageSchema).min(1).max(50),
  theme: z.string().default('honasa-teal'),
  author: z.string().optional(),
  source: z.string().optional(),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});
export type Layout = z.infer<typeof LayoutSchema>;

// ── Validation utilities ──────────────────────────────────────────────────────

export type ValidationResult =
  | { success: true; data: Layout }
  | { success: false; errors: string[] };

export function validateLayout(raw: unknown): ValidationResult {
  const result = LayoutSchema.safeParse(raw);
  if (result.success) {
    return { success: true, data: result.data };
  }
  const errors = result.error.issues.map(
    (issue) => `${issue.path.join('.')}: ${issue.message}`
  );
  return { success: false, errors };
}

export function validateVisual(raw: unknown): { success: boolean; errors: string[] } {
  const result = VisualSchema.safeParse(raw);
  if (result.success) return { success: true, errors: [] };
  return {
    success: false,
    errors: result.error.issues.map((i) => `${i.path.join('.')}: ${i.message}`),
  };
}

// ── Schema migration ──────────────────────────────────────────────────────────
export const MIGRATION_REGISTRY: Record<string, (old: Record<string, unknown>) => Record<string, unknown>> = {
  // When a new schema version is introduced, add a migration here:
  // '0.9.0': (old) => ({ ...old, schemaVersion: '1.0.0', newField: defaultValue })
};

export function migrateLayout(raw: Record<string, unknown>): Record<string, unknown> {
  const version = typeof raw.schemaVersion === 'string' ? raw.schemaVersion : '';
  if (version === SCHEMA_VERSION) return raw;
  const migrator = MIGRATION_REGISTRY[version];
  if (!migrator) {
    throw new Error(
      `Unsupported schema version "${version}". Expected "${SCHEMA_VERSION}". No migration available.`
    );
  }
  return migrator(raw);
}

// ── Safe import ───────────────────────────────────────────────────────────────
export function importLayout(jsonString: string): ValidationResult {
  let raw: unknown;
  try {
    raw = JSON.parse(jsonString);
  } catch {
    return { success: false, errors: ['Invalid JSON: could not parse input'] };
  }
  if (typeof raw !== 'object' || raw === null) {
    return { success: false, errors: ['Layout must be a JSON object'] };
  }
  let migrated: Record<string, unknown>;
  try {
    migrated = migrateLayout(raw as Record<string, unknown>);
  } catch (e) {
    return { success: false, errors: [(e as Error).message] };
  }
  return validateLayout(migrated);
}

// ── Export helpers ────────────────────────────────────────────────────────────
export function exportLayout(layout: Layout): string {
  return JSON.stringify(layout, null, 2);
}

export function createEmptyLayout(projectId: string, projectName: string): Layout {
  const now = new Date().toISOString();
  return {
    schemaVersion: SCHEMA_VERSION,
    projectId,
    projectName,
    pages: [
      {
        id: 'page-1',
        name: 'Page 1',
        size: { width: 1280, height: 720, unit: 'px' },
        background: { color: '#FFFFFF', imageTransparency: 0 },
        visuals: [],
        groups: [],
        filters: [],
        gridSize: 10,
        snapToGrid: true,
        mobileLayout: false,
      },
    ],
    theme: 'honasa-teal',
    createdAt: now,
    updatedAt: now,
  };
}

export function createVisualId(): string {
  return `v-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}
