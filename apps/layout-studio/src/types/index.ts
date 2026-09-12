export type {
  Layout,
  Page,
  Visual,
  VisualType,
  Binding,
  Filter,
  Formatting,
  MobileOverride,
  VisualGroup,
  PageSize,
  CanvasBackground,
  ValidationResult,
} from '@mt-dashboard/layout-schema';

// Editor-only types (not persisted in the schema)

export interface SelectionState {
  selectedIds: string[];
}

export interface DragState {
  isDragging: boolean;
  draggedIds: string[];
  originX: number;
  originY: number;
}

export interface ClipboardEntry {
  visuals: import('@mt-dashboard/layout-schema').Visual[];
  offsetX: number;
  offsetY: number;
}

export interface ZoomState {
  zoom: number;
  panX: number;
  panY: number;
}

export type AlignDirection =
  | 'left' | 'center-h' | 'right'
  | 'top' | 'center-v' | 'bottom';

export type DistributeDirection = 'horizontal' | 'vertical';

export interface ValidationIssue {
  visualId: string | null;
  severity: 'error' | 'warning' | 'info';
  message: string;
  field?: string;
}

export interface HistoryEntry {
  description: string;
  pageSnapshot: import('@mt-dashboard/layout-schema').Page;
}

export type EditorMode = 'select' | 'pan' | 'add';
