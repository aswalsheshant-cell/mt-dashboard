import { useEffect } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { scheduleAutosave, saveLayout } from '@/utils/autosave';

export function useAutosave() {
  const layout = useEditorStore((s) => s.layout);
  const isDirty = useEditorStore((s) => s.isDirty);
  const markClean = useEditorStore((s) => s.markClean);

  useEffect(() => {
    if (!isDirty) return;
    scheduleAutosave(layout);
  }, [layout, isDirty]);

  // Force-save on beforeunload
  useEffect(() => {
    const handler = () => {
      if (isDirty) {
        saveLayout(layout);
        markClean();
      }
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [layout, isDirty, markClean]);
}
