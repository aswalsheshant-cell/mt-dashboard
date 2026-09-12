import React, { useRef, useCallback } from 'react';
import {
  DndContext,
  useSensor,
  useSensors,
  PointerSensor,
  type DragEndEvent,
} from '@dnd-kit/core';
import { useEditorStore } from '@/store/editorStore';
import { CanvasVisual } from './CanvasVisual';
import { tokens } from '@mt-dashboard/design-tokens';

export function Canvas() {
  const activePage = useEditorStore((s) => s.activePage());
  const selectedIds = useEditorStore((s) => s.selectedIds);
  const zoom = useEditorStore((s) => s.zoom);
  const showGrid = useEditorStore((s) => s.showGrid);
  const isMobilePreview = useEditorStore((s) => s.isMobilePreview);
  const mode = useEditorStore((s) => s.mode);
  const setSelectedIds = useEditorStore((s) => s.setSelectedIds);
  const clearSelection = useEditorStore((s) => s.clearSelection);
  const addVisual = useEditorStore((s) => s.addVisual);
  const updateVisual = useEditorStore((s) => s.updateVisual);

  const canvasRef = useRef<HTMLDivElement>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const canvasWidth = isMobilePreview ? tokens.canvas.mobileWidth : activePage.size.width;
  const canvasHeight = isMobilePreview ? tokens.canvas.mobileHeight : activePage.size.height;

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, delta } = event;
      if (!active || !delta) return;
      const visual = activePage.visuals.find((v) => v.id === active.id);
      if (!visual || visual.locked) return;

      const snap = activePage.snapToGrid ? activePage.gridSize : 1;
      const newX = Math.max(0, Math.round((visual.x + delta.x / zoom) / snap) * snap);
      const newY = Math.max(0, Math.round((visual.y + delta.y / zoom) / snap) * snap);
      updateVisual(visual.id as string, { x: newX, y: newY });
    },
    [activePage, zoom, updateVisual]
  );

  const handleCanvasClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === canvasRef.current) {
        clearSelection();
      }
    },
    [clearSelection]
  );

  const handleCanvasDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      if (mode !== 'add') return;
      const rect = canvasRef.current?.getBoundingClientRect();
      if (!rect) return;
      const x = (e.clientX - rect.left) / zoom;
      const y = (e.clientY - rect.top) / zoom;
      addVisual('kpi-card', x, y);
    },
    [mode, zoom, addVisual]
  );

  const gridBg = showGrid
    ? `linear-gradient(${tokens.color.gray200} 1px, transparent 1px), linear-gradient(90deg, ${tokens.color.gray200} 1px, transparent 1px)`
    : 'none';

  const visuals = isMobilePreview
    ? activePage.visuals
        .filter((v) => !v.mobileOverride?.hidden)
        .sort((a, b) => (a.mobileOverride?.order ?? 0) - (b.mobileOverride?.order ?? 0))
    : [...activePage.visuals].sort((a, b) => a.zIndex - b.zIndex);

  return (
    <div
      className="flex-1 overflow-auto bg-gray-100 flex items-start justify-center p-8"
      role="region"
      aria-label="Layout canvas workspace"
    >
      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <div
          ref={canvasRef}
          className="relative shadow-lg cursor-default select-none"
          style={{
            width: canvasWidth * zoom,
            height: canvasHeight * zoom,
            background: activePage.background.color,
            backgroundImage: gridBg,
            backgroundSize: `${activePage.gridSize * zoom}px ${activePage.gridSize * zoom}px`,
            transform: `scale(1)`,
            transformOrigin: 'top left',
          }}
          onClick={handleCanvasClick}
          onDoubleClick={handleCanvasDoubleClick}
          data-testid="canvas"
          aria-label={`Canvas: ${activePage.name}, ${canvasWidth}×${canvasHeight}`}
        >
          {/* Empty state */}
          {!visuals.length && (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-400 pointer-events-none">
              <div className="text-4xl mb-3">🎨</div>
              <p className="text-lg font-medium">Empty canvas</p>
              <p className="text-sm mt-1">Add visuals from the toolbar, or apply a template to get started.</p>
            </div>
          )}

          {visuals.map((visual) => (
            <CanvasVisual
              key={visual.id}
              visual={isMobilePreview ? {
                ...visual,
                x: visual.mobileOverride?.x ?? visual.x,
                y: visual.mobileOverride?.y ?? visual.y,
                width: visual.mobileOverride?.width ?? visual.width,
                height: visual.mobileOverride?.height ?? visual.height,
              } : visual}
              selected={selectedIds.includes(visual.id)}
              zoom={zoom}
              onSelect={(id, multi) => {
                if (multi) {
                  setSelectedIds(selectedIds.includes(id)
                    ? selectedIds.filter((s) => s !== id)
                    : [...selectedIds, id]);
                } else {
                  setSelectedIds([id]);
                }
              }}
            />
          ))}
        </div>
      </DndContext>
    </div>
  );
}
