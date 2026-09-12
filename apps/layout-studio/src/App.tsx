import { useState, useEffect } from 'react';
import { Toolbar } from './components/Toolbar/Toolbar';
import { Canvas } from './components/Canvas/Canvas';
import { VisualPicker } from './components/VisualPicker/VisualPicker';
import { PropertiesPanel } from './components/PropertiesPanel/PropertiesPanel';
import { ValidationPanel } from './components/ValidationPanel/ValidationPanel';
import { TemplateGallery } from './components/TemplateGallery/TemplateGallery';
import { PageNavigator } from './components/PageNavigator/PageNavigator';
import { useKeyboard } from './hooks/useKeyboard';
import { useAutosave } from './hooks/useAutosave';
import { useEditorStore } from './store/editorStore';
import { loadSavedLayout } from './utils/autosave';

export function App() {
  useKeyboard();
  useAutosave();

  const showValidation = useEditorStore((s) => s.showValidation);
  const loadLayout     = useEditorStore((s) => s.loadLayout);
  const [showTemplateGallery, setShowTemplateGallery] = useState(false);
  const [restoredAutosave, setRestoredAutosave] = useState(false);

  // Offer to restore autosave on first mount
  useEffect(() => {
    if (restoredAutosave) return;
    setRestoredAutosave(true);
    const saved = loadSavedLayout();
    if (!saved) return;
    const accept = window.confirm(
      'A previous unsaved layout was found. Restore it?'
    );
    if (accept) loadLayout(saved);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex flex-col h-full overflow-hidden" role="application" aria-label="Layout Studio">
      {/* Top toolbar */}
      <Toolbar />

      {/* Template gallery quick-access button (inside toolbar area via a floating badge) */}
      <div className="absolute top-2 right-36 z-10">
        <button
          className="text-xs text-teal-600 hover:text-teal-700 px-2 py-1 bg-teal-50 hover:bg-teal-100 border border-teal-200 rounded transition-colors"
          onClick={() => setShowTemplateGallery(true)}
          aria-label="Open template gallery"
          title="Browse and apply page templates"
        >
          📐 Templates
        </button>
      </div>

      {/* Main editor area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Visual picker */}
        <VisualPicker />

        {/* Centre: canvas + page nav + validation */}
        <div className="flex flex-col flex-1 overflow-hidden">
          <Canvas />
          <PageNavigator />
          {showValidation && <ValidationPanel />}
        </div>

        {/* Right: Properties panel */}
        <PropertiesPanel />
      </div>

      {/* Template gallery modal */}
      {showTemplateGallery && (
        <TemplateGallery onClose={() => setShowTemplateGallery(false)} />
      )}
    </div>
  );
}
