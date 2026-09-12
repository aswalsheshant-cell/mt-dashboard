import { useEffect } from 'react';
import { useEditorStore } from '@/store/editorStore';

export function useKeyboard() {
  const store = useEditorStore();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName.toLowerCase();
      // Don't intercept keyboard in input fields
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      const ctrl = e.ctrlKey || e.metaKey;

      // Undo / Redo
      if (ctrl && e.key === 'z' && !e.shiftKey) { e.preventDefault(); store.undo(); return; }
      if (ctrl && (e.key === 'y' || (e.key === 'z' && e.shiftKey))) { e.preventDefault(); store.redo(); return; }

      // Copy / Paste / Duplicate
      if (ctrl && e.key === 'c') { e.preventDefault(); store.copySelected(); return; }
      if (ctrl && e.key === 'v') { e.preventDefault(); store.paste(); return; }
      if (ctrl && e.key === 'd') { e.preventDefault(); store.duplicateSelected(); return; }

      // Select all
      if (ctrl && e.key === 'a') { e.preventDefault(); store.selectAll(); return; }

      // Delete
      if (e.key === 'Delete' || e.key === 'Backspace') {
        // Only if not in input
        e.preventDefault();
        store.deleteSelected();
        return;
      }

      // Arrow key movement
      const step = e.shiftKey ? 10 : 1;
      switch (e.key) {
        case 'ArrowLeft':  e.preventDefault(); store.moveSelected(-step, 0); break;
        case 'ArrowRight': e.preventDefault(); store.moveSelected(step, 0); break;
        case 'ArrowUp':    e.preventDefault(); store.moveSelected(0, -step); break;
        case 'ArrowDown':  e.preventDefault(); store.moveSelected(0, step); break;
      }

      // Escape — clear selection / pan mode off
      if (e.key === 'Escape') { store.clearSelection(); store.setMode('select'); }

      // Zoom shortcuts
      if (ctrl && e.key === '=') { e.preventDefault(); store.setZoom(Math.min(4, store.zoom + 0.1)); }
      if (ctrl && e.key === '-') { e.preventDefault(); store.setZoom(Math.max(0.25, store.zoom - 0.1)); }
      if (ctrl && e.key === '0') { e.preventDefault(); store.fitToCanvas(); }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [store]);
}
