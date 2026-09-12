import React, { useCallback } from 'react';
import { useDraggable } from '@dnd-kit/core';
import type { Visual } from '@mt-dashboard/layout-schema';
import { useEditorStore } from '@/store/editorStore';
import { VisualPreview } from '../common/VisualPreview';

interface Props {
  visual: Visual;
  selected: boolean;
  zoom: number;
  onSelect: (id: string, multi: boolean) => void;
}

export function CanvasVisual({ visual, selected, zoom, onSelect }: Props) {
  const updateVisual = useEditorStore((s) => s.updateVisual);

  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: visual.id,
    disabled: visual.locked,
  });

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onSelect(visual.id, e.shiftKey || e.ctrlKey || e.metaKey);
    },
    [visual.id, onSelect]
  );

  const style: React.CSSProperties = {
    position: 'absolute',
    left: visual.x * zoom + (transform?.x ?? 0),
    top: visual.y * zoom + (transform?.y ?? 0),
    width: visual.width * zoom,
    height: visual.height * zoom,
    zIndex: visual.zIndex + (selected ? 1000 : 0),
    opacity: visual.hidden ? 0.3 : isDragging ? 0.7 : 1,
    cursor: visual.locked ? 'not-allowed' : isDragging ? 'grabbing' : 'grab',
    outline: selected ? '2px solid #00A896' : 'none',
    outlineOffset: 1,
    boxSizing: 'border-box',
    userSelect: 'none',
    overflow: 'hidden',
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={handleClick}
      {...listeners}
      {...attributes}
      aria-label={visual.accessibilityLabel || `${visual.type}: ${visual.title}`}
      aria-selected={selected}
      role="listitem"
      data-testid={`visual-${visual.id}`}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(visual.id, false);
        }
      }}
    >
      <VisualPreview visual={visual} zoom={zoom} />

      {/* Resize handles (SE corner) */}
      {selected && !visual.locked && (
        <ResizeHandle
          onResize={(dw, dh) => {
            updateVisual(visual.id, {
              width: Math.max(10, visual.width + Math.round(dw / zoom)),
              height: Math.max(10, visual.height + Math.round(dh / zoom)),
            });
          }}
        />
      )}

      {/* Lock indicator */}
      {visual.locked && (
        <div className="absolute top-1 right-1 text-xs bg-black/30 text-white px-1 rounded" aria-label="Locked">
          🔒
        </div>
      )}
    </div>
  );
}

// Simple SE resize handle
function ResizeHandle({ onResize }: { onResize: (dw: number, dh: number) => void }) {
  const handleMouseDown = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    const startX = e.clientX;
    const startY = e.clientY;

    const onMouseMove = (me: MouseEvent) => {
      onResize(me.clientX - startX, me.clientY - startY);
    };
    const onMouseUp = () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
  };

  return (
    <div
      className="absolute bottom-0 right-0 w-3 h-3 cursor-se-resize bg-teal-500 rounded-tl"
      onMouseDown={handleMouseDown}
      aria-label="Resize handle"
      role="button"
      tabIndex={-1}
    />
  );
}
