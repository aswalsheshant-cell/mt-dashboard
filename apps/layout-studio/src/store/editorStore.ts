import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';
import type { Layout, Page, Visual, VisualType, VisualGroup } from '@mt-dashboard/layout-schema';
import {
  createEmptyLayout,
  createVisualId,
} from '@mt-dashboard/layout-schema';
import { visualDefaults } from '@mt-dashboard/design-tokens';
import type {
  AlignDirection,
  DistributeDirection,
  ClipboardEntry,
  ValidationIssue,
  EditorMode,
} from '@/types';
import { validatePage } from '@/utils/validation';

const DEFAULT_VISUAL_SIZE: Record<VisualType, { width: number; height: number }> = {
  'kpi-card':                      visualDefaults.kpiCard,
  'text':                          visualDefaults.text,
  'image-placeholder':             visualDefaults.imagePlaceholder,
  'bar-chart':                     visualDefaults.barChart,
  'column-chart':                  visualDefaults.columnChart,
  'line-chart':                    visualDefaults.lineChart,
  'combo-chart':                   visualDefaults.comboChart,
  'pie-chart':                     visualDefaults.pieChart,
  'donut-chart':                   visualDefaults.donutChart,
  'table':                         visualDefaults.table,
  'matrix':                        visualDefaults.matrix,
  'slicer':                        visualDefaults.slicer,
  'gauge':                         visualDefaults.gauge,
  'funnel':                        visualDefaults.funnel,
  'treemap':                       visualDefaults.treemap,
  'decomposition-tree-placeholder':visualDefaults.decompositionTree,
  'map-placeholder':               visualDefaults.mapPlaceholder,
};

// ── History ───────────────────────────────────────────────────────────────────
const MAX_HISTORY = 100;

interface HistorySlice {
  past: Page[];
  future: Page[];
}

// ── Main editor state ─────────────────────────────────────────────────────────
interface EditorState {
  layout: Layout;
  activePageIndex: number;
  selectedIds: string[];
  clipboard: ClipboardEntry | null;
  zoom: number;
  panX: number;
  panY: number;
  mode: EditorMode;
  history: HistorySlice;
  isDirty: boolean;
  validationIssues: ValidationIssue[];
  showGrid: boolean;
  showValidation: boolean;
  isMobilePreview: boolean;

  // Page helpers
  activePage: () => Page;

  // Selection
  setSelectedIds: (ids: string[]) => void;
  selectAll: () => void;
  clearSelection: () => void;

  // Mode
  setMode: (mode: EditorMode) => void;

  // Zoom
  setZoom: (zoom: number) => void;
  fitToCanvas: () => void;

  // Visual CRUD
  addVisual: (type: VisualType, x?: number, y?: number) => string;
  deleteSelected: () => void;
  duplicateSelected: () => void;
  copySelected: () => void;
  paste: () => void;
  updateVisual: (id: string, patch: Partial<Visual>) => void;
  bringForward: (ids: string[]) => void;
  sendBackward: (ids: string[]) => void;
  lockVisuals: (ids: string[]) => void;
  unlockVisuals: (ids: string[]) => void;
  toggleVisibility: (ids: string[]) => void;
  moveSelected: (dx: number, dy: number) => void;

  // Alignment & distribution
  align: (direction: AlignDirection) => void;
  distribute: (direction: DistributeDirection) => void;

  // Groups
  groupSelected: () => void;
  ungroupSelected: () => void;

  // Template
  applyTemplate: (page: Omit<Page, 'id'>) => void;

  // History
  undo: () => void;
  redo: () => void;
  pushHistory: (description: string) => void;

  // Layout persistence
  loadLayout: (layout: Layout) => void;
  setLayout: (layout: Layout) => void;
  setActivePageIndex: (index: number) => void;
  markClean: () => void;

  // Validation
  runValidation: () => void;
  toggleValidation: () => void;

  // Grid
  toggleGrid: () => void;
  setGridSize: (size: number) => void;
  setSnapToGrid: (snap: boolean) => void;

  // Mobile preview
  toggleMobilePreview: () => void;

  // Page management
  addPage: () => void;
  renamePage: (index: number, name: string) => void;
}

const snapToGrid = (value: number, gridSize: number) =>
  Math.round(value / gridSize) * gridSize;

export const useEditorStore = create<EditorState>()(
  subscribeWithSelector((set, get) => {
    const initialLayout = createEmptyLayout('layout-studio-default', 'Untitled Layout');

    // Mutate current page and push to history
    const mutatePage = (
      description: string,
      mutator: (page: Page) => Page
    ) => {
      set((state) => {
        const { layout, activePageIndex, history } = state;
        const oldPage = layout.pages[activePageIndex];
        const newPage = mutator({ ...oldPage });
        const newPages = layout.pages.map((p, i) =>
          i === activePageIndex ? newPage : p
        );
        const newPast = [...history.past, oldPage].slice(-MAX_HISTORY);
        return {
          layout: { ...layout, pages: newPages, updatedAt: new Date().toISOString() },
          history: { past: newPast, future: [] },
          isDirty: true,
          // description stored implicitly in length
        };
      });
      // Validation re-runs after any mutation
      get().runValidation();
      void description;
    };

    return {
      layout: initialLayout,
      activePageIndex: 0,
      selectedIds: [],
      clipboard: null,
      zoom: 1,
      panX: 0,
      panY: 0,
      mode: 'select',
      history: { past: [], future: [] },
      isDirty: false,
      validationIssues: [],
      showGrid: true,
      showValidation: false,
      isMobilePreview: false,

      activePage: () => {
        const { layout, activePageIndex } = get();
        return layout.pages[activePageIndex];
      },

      setSelectedIds: (ids) => set({ selectedIds: ids }),
      selectAll: () => set({ selectedIds: get().activePage().visuals.map((v) => v.id) }),
      clearSelection: () => set({ selectedIds: [] }),

      setMode: (mode) => set({ mode }),
      setZoom: (zoom) => set({ zoom: Math.max(0.25, Math.min(4, zoom)) }),
      fitToCanvas: () => set({ zoom: 1, panX: 0, panY: 0 }),

      addVisual: (type, x = 40, y = 40) => {
        const page = get().activePage();
        const snap = page.snapToGrid ? page.gridSize : 1;
        const dims = DEFAULT_VISUAL_SIZE[type];
        const id = createVisualId();
        const visual: Visual = {
          id,
          type,
          title: type.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
          subtitle: '',
          x: snapToGrid(x, snap),
          y: snapToGrid(y, snap),
          width: dims.width,
          height: dims.height,
          zIndex: Math.max(0, ...page.visuals.map((v) => v.zIndex)) + 1,
          locked: false,
          hidden: false,
          measures: [],
          categories: [],
          series: [],
          filters: [],
          interactions: {
            filterTargets: [],
            highlightTargets: [],
            drillthroughEnabled: false,
            crossFilterEnabled: true,
          },
          tooltip: { enabled: true, fields: [] },
          drillthrough: { enabled: false, passFilters: [] },
          formatting: {
            fontWeight: 'normal',
            padding: 8,
            borderWidth: 0,
            borderRadius: 4,
            legendVisible: true,
            legendPosition: 'bottom',
            dataLabelsVisible: false,
            xAxisVisible: true,
            yAxisVisible: true,
            gridLinesVisible: true,
            colorPalette: [],
            titleVisible: true,
            titleFontSize: 14,
          },
          accessibilityLabel: '',
        };
        mutatePage(`Add ${type}`, (p) => ({ ...p, visuals: [...p.visuals, visual] }));
        set({ selectedIds: [id] });
        return id;
      },

      deleteSelected: () => {
        const { selectedIds } = get();
        if (!selectedIds.length) return;
        mutatePage('Delete visuals', (p) => ({
          ...p,
          visuals: p.visuals.filter((v) => !selectedIds.includes(v.id)),
        }));
        set({ selectedIds: [] });
      },

      duplicateSelected: () => {
        const { selectedIds } = get();
        const page = get().activePage();
        const toDuplicate = page.visuals.filter((v) => selectedIds.includes(v.id));
        const newIds: string[] = [];
        const newVisuals = toDuplicate.map((v) => {
          const id = createVisualId();
          newIds.push(id);
          return { ...v, id, x: v.x + 20, y: v.y + 20 };
        });
        mutatePage('Duplicate visuals', (p) => ({
          ...p,
          visuals: [...p.visuals, ...newVisuals],
        }));
        set({ selectedIds: newIds });
      },

      copySelected: () => {
        const { selectedIds } = get();
        const page = get().activePage();
        const visuals = page.visuals.filter((v) => selectedIds.includes(v.id));
        if (!visuals.length) return;
        const minX = Math.min(...visuals.map((v) => v.x));
        const minY = Math.min(...visuals.map((v) => v.y));
        set({ clipboard: { visuals, offsetX: minX, offsetY: minY } });
      },

      paste: () => {
        const { clipboard } = get();
        if (!clipboard) return;
        const newIds: string[] = [];
        const newVisuals = clipboard.visuals.map((v) => {
          const id = createVisualId();
          newIds.push(id);
          return { ...v, id, x: v.x - clipboard.offsetX + 40, y: v.y - clipboard.offsetY + 40 };
        });
        mutatePage('Paste visuals', (p) => ({
          ...p,
          visuals: [...p.visuals, ...newVisuals],
        }));
        set({ selectedIds: newIds });
      },

      updateVisual: (id, patch) => {
        mutatePage('Update visual', (p) => ({
          ...p,
          visuals: p.visuals.map((v) => (v.id === id ? { ...v, ...patch } : v)),
        }));
      },

      bringForward: (ids) => {
        mutatePage('Bring forward', (p) => ({
          ...p,
          visuals: p.visuals.map((v) =>
            ids.includes(v.id) ? { ...v, zIndex: Math.min(9999, v.zIndex + 1) } : v
          ),
        }));
      },

      sendBackward: (ids) => {
        mutatePage('Send backward', (p) => ({
          ...p,
          visuals: p.visuals.map((v) =>
            ids.includes(v.id) ? { ...v, zIndex: Math.max(0, v.zIndex - 1) } : v
          ),
        }));
      },

      lockVisuals: (ids) =>
        mutatePage('Lock', (p) => ({
          ...p,
          visuals: p.visuals.map((v) => (ids.includes(v.id) ? { ...v, locked: true } : v)),
        })),

      unlockVisuals: (ids) =>
        mutatePage('Unlock', (p) => ({
          ...p,
          visuals: p.visuals.map((v) => (ids.includes(v.id) ? { ...v, locked: false } : v)),
        })),

      toggleVisibility: (ids) =>
        mutatePage('Toggle visibility', (p) => ({
          ...p,
          visuals: p.visuals.map((v) =>
            ids.includes(v.id) ? { ...v, hidden: !v.hidden } : v
          ),
        })),

      moveSelected: (dx, dy) => {
        const { selectedIds } = get();
        const page = get().activePage();
        const snap = page.snapToGrid ? page.gridSize : 1;
        mutatePage('Move visuals', (p) => ({
          ...p,
          visuals: p.visuals.map((v) =>
            selectedIds.includes(v.id) && !v.locked
              ? {
                  ...v,
                  x: snapToGrid(Math.max(0, v.x + dx), snap),
                  y: snapToGrid(Math.max(0, v.y + dy), snap),
                }
              : v
          ),
        }));
      },

      align: (direction) => {
        const { selectedIds } = get();
        const page = get().activePage();
        const targets = page.visuals.filter(
          (v) => selectedIds.includes(v.id) && !v.locked
        );
        if (targets.length < 2) return;
        mutatePage(`Align ${direction}`, (p) => {
          const minX = Math.min(...targets.map((v) => v.x));
          const maxX = Math.max(...targets.map((v) => v.x + v.width));
          const midX = (minX + maxX) / 2;
          const minY = Math.min(...targets.map((v) => v.y));
          const maxY = Math.max(...targets.map((v) => v.y + v.height));
          const midY = (minY + maxY) / 2;
          return {
            ...p,
            visuals: p.visuals.map((v) => {
              if (!selectedIds.includes(v.id) || v.locked) return v;
              switch (direction) {
                case 'left':     return { ...v, x: minX };
                case 'right':    return { ...v, x: maxX - v.width };
                case 'center-h': return { ...v, x: midX - v.width / 2 };
                case 'top':      return { ...v, y: minY };
                case 'bottom':   return { ...v, y: maxY - v.height };
                case 'center-v': return { ...v, y: midY - v.height / 2 };
                default:         return v;
              }
            }),
          };
        });
      },

      distribute: (direction) => {
        const { selectedIds } = get();
        const page = get().activePage();
        const targets = page.visuals
          .filter((v) => selectedIds.includes(v.id) && !v.locked)
          .sort((a, b) => direction === 'horizontal' ? a.x - b.x : a.y - b.y);
        if (targets.length < 3) return;
        mutatePage(`Distribute ${direction}`, (p) => {
          const positions =
            direction === 'horizontal'
              ? {
                  start: targets[0].x,
                  end: targets[targets.length - 1].x + targets[targets.length - 1].width,
                  totalSize: targets.reduce((s, v) => s + v.width, 0),
                }
              : {
                  start: targets[0].y,
                  end: targets[targets.length - 1].y + targets[targets.length - 1].height,
                  totalSize: targets.reduce((s, v) => s + v.height, 0),
                };
          const gap = (positions.end - positions.start - positions.totalSize) / (targets.length - 1);
          let cursor = positions.start;
          const distributed = new Map<string, Partial<typeof targets[0]>>();
          for (const t of targets) {
            distributed.set(t.id, direction === 'horizontal' ? { x: cursor } : { y: cursor });
            cursor += (direction === 'horizontal' ? t.width : t.height) + gap;
          }
          return {
            ...p,
            visuals: p.visuals.map((v) => ({ ...v, ...(distributed.get(v.id) ?? {}) })),
          };
        });
      },

      groupSelected: () => {
        const { selectedIds } = get();
        if (selectedIds.length < 2) return;
        const groupId = `g-${Date.now()}`;
        const group: VisualGroup = { id: groupId, name: 'Group', visualIds: selectedIds };
        mutatePage('Group visuals', (p) => ({
          ...p,
          visuals: p.visuals.map((v) => (selectedIds.includes(v.id) ? { ...v, groupId } : v)),
          groups: [...p.groups, group],
        }));
      },

      ungroupSelected: () => {
        const { selectedIds } = get();
        const page = get().activePage();
        const groupIds = new Set(
          page.visuals.filter((v) => selectedIds.includes(v.id)).map((v) => v.groupId).filter(Boolean)
        );
        mutatePage('Ungroup visuals', (p) => ({
          ...p,
          visuals: p.visuals.map((v) =>
            v.groupId && groupIds.has(v.groupId) ? { ...v, groupId: undefined } : v
          ),
          groups: p.groups.filter((g) => !groupIds.has(g.id)),
        }));
      },

      applyTemplate: (pageTemplate) => {
        const { layout, activePageIndex } = get();
        const currentPage = layout.pages[activePageIndex];
        mutatePage('Apply template', () => ({
          ...pageTemplate,
          id: currentPage.id,
          name: currentPage.name,
        }));
        set({ selectedIds: [] });
      },

      pushHistory: (_description) => {
        const page = get().activePage();
        set((state) => ({
          history: {
            past: [...state.history.past, page].slice(-MAX_HISTORY),
            future: [],
          },
        }));
      },

      undo: () => {
        set((state) => {
          const { history, layout, activePageIndex } = state;
          if (!history.past.length) return state;
          const previous = history.past[history.past.length - 1];
          const current = layout.pages[activePageIndex];
          const newPages = layout.pages.map((p, i) =>
            i === activePageIndex ? previous : p
          );
          return {
            layout: { ...layout, pages: newPages, updatedAt: new Date().toISOString() },
            history: {
              past: history.past.slice(0, -1),
              future: [current, ...history.future].slice(0, MAX_HISTORY),
            },
            isDirty: true,
            selectedIds: [],
          };
        });
        get().runValidation();
      },

      redo: () => {
        set((state) => {
          const { history, layout, activePageIndex } = state;
          if (!history.future.length) return state;
          const next = history.future[0];
          const current = layout.pages[activePageIndex];
          const newPages = layout.pages.map((p, i) =>
            i === activePageIndex ? next : p
          );
          return {
            layout: { ...layout, pages: newPages, updatedAt: new Date().toISOString() },
            history: {
              past: [...history.past, current].slice(-MAX_HISTORY),
              future: history.future.slice(1),
            },
            isDirty: true,
            selectedIds: [],
          };
        });
        get().runValidation();
      },

      loadLayout: (layout) => {
        set({
          layout,
          activePageIndex: 0,
          selectedIds: [],
          history: { past: [], future: [] },
          isDirty: false,
          clipboard: null,
          zoom: 1,
          panX: 0,
          panY: 0,
        });
        get().runValidation();
      },

      setLayout: (layout) => {
        set({ layout, isDirty: true });
      },

      setActivePageIndex: (index) => {
        set({ activePageIndex: index, selectedIds: [] });
        get().runValidation();
      },

      markClean: () => set({ isDirty: false }),

      runValidation: () => {
        const page = get().activePage();
        const issues = validatePage(page);
        set({ validationIssues: issues });
      },

      toggleValidation: () => set((s) => ({ showValidation: !s.showValidation })),
      toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),

      setGridSize: (size) => {
        mutatePage('Set grid size', (p) => ({ ...p, gridSize: size }));
      },

      setSnapToGrid: (snap) => {
        mutatePage('Set snap to grid', (p) => ({ ...p, snapToGrid: snap }));
      },

      toggleMobilePreview: () =>
        set((s) => ({ isMobilePreview: !s.isMobilePreview })),

      addPage: () => {
        const { layout } = get();
        const newPage: Page = {
          id: `page-${Date.now()}`,
          name: `Page ${layout.pages.length + 1}`,
          size: { width: 1280, height: 720, unit: 'px' },
          background: { color: '#F8FAFC', imageTransparency: 0 },
          visuals: [],
          groups: [],
          filters: [],
          gridSize: 10,
          snapToGrid: true,
          mobileLayout: false,
        };
        set((s) => ({
          layout: {
            ...s.layout,
            pages: [...s.layout.pages, newPage],
            updatedAt: new Date().toISOString(),
          },
          activePageIndex: s.layout.pages.length,
          isDirty: true,
        }));
      },

      renamePage: (index, name) => {
        set((s) => ({
          layout: {
            ...s.layout,
            pages: s.layout.pages.map((p, i) => (i === index ? { ...p, name } : p)),
            updatedAt: new Date().toISOString(),
          },
          isDirty: true,
        }));
      },
    };
  })
);
