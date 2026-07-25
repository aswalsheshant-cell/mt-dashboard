import { useEditorStore } from '@/store/editorStore';
import { exportLayoutJSON } from '@/utils/export';
import { loadSavedLayout, clearSavedLayout } from '@/utils/autosave';
import { importLayout } from '@mt-dashboard/layout-schema';
import type { EditorMode } from '@/types';

export function Toolbar() {
  const mode      = useEditorStore((s) => s.mode);
  const setMode   = useEditorStore((s) => s.setMode);
  const zoom      = useEditorStore((s) => s.zoom);
  const setZoom   = useEditorStore((s) => s.setZoom);
  const fitToCanvas = useEditorStore((s) => s.fitToCanvas);
  const showGrid  = useEditorStore((s) => s.showGrid);
  const toggleGrid = useEditorStore((s) => s.toggleGrid);
  const showValidation  = useEditorStore((s) => s.showValidation);
  const toggleValidation = useEditorStore((s) => s.toggleValidation);
  const isMobilePreview = useEditorStore((s) => s.isMobilePreview);
  const toggleMobilePreview = useEditorStore((s) => s.toggleMobilePreview);
  const isDirty   = useEditorStore((s) => s.isDirty);
  const undo      = useEditorStore((s) => s.undo);
  const redo      = useEditorStore((s) => s.redo);
  const history   = useEditorStore((s) => s.history);
  const layout    = useEditorStore((s) => s.layout);
  const loadLayout = useEditorStore((s) => s.loadLayout);
  const validationIssues = useEditorStore((s) => s.validationIssues);

  const errorCount   = validationIssues.filter((i) => i.severity === 'error').length;
  const warningCount = validationIssues.filter((i) => i.severity === 'warning').length;

  const handleExport = () => {
    try {
      exportLayoutJSON(layout);
    } catch (e) {
      alert((e as Error).message);
    }
  };

  const handleImport = () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        const text = ev.target?.result as string;
        const result = importLayout(text);
        if (!result.success) {
          alert(`Import failed:\n${result.errors.join('\n')}`);
          return;
        }
        loadLayout(result.data);
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const handleRestoreAutosave = () => {
    const saved = loadSavedLayout();
    if (!saved) { alert('No autosaved layout found.'); return; }
    if (confirm('Restore autosaved layout? Unsaved changes will be lost.')) {
      loadLayout(saved);
    }
  };

  const handleClearAutosave = () => {
    if (confirm('Clear the autosaved draft?')) clearSavedLayout();
  };

  return (
    <header className="flex items-center gap-2 px-3 h-12 bg-white border-b border-gray-200 select-none shrink-0">
      {/* Brand */}
      <span className="text-teal-600 font-semibold text-sm mr-2 whitespace-nowrap">Layout Studio</span>

      <Divider />

      {/* Mode selector */}
      <ModeButton icon="↖" label="Select (S)" active={mode === 'select'} onClick={() => setMode('select' as EditorMode)} />
      <ModeButton icon="✚" label="Add visual (A)" active={mode === 'add'}    onClick={() => setMode('add' as EditorMode)} />
      <ModeButton icon="✋" label="Pan (H)"    active={mode === 'pan'}    onClick={() => setMode('pan' as EditorMode)} />

      <Divider />

      {/* Undo / Redo */}
      <ToolBtn icon="↩" label="Undo (⌘Z)"  disabled={!history.past.length}   onClick={undo} />
      <ToolBtn icon="↪" label="Redo (⌘Y)"  disabled={!history.future.length} onClick={redo} />

      <Divider />

      {/* Zoom */}
      <ToolBtn icon="−" label="Zoom out (⌘-)" disabled={zoom <= 0.25} onClick={() => setZoom(zoom - 0.1)} />
      <span className="text-xs text-gray-600 w-12 text-center tabular-nums">{Math.round(zoom * 100)}%</span>
      <ToolBtn icon="+" label="Zoom in (⌘+)"  disabled={zoom >= 4}    onClick={() => setZoom(zoom + 0.1)} />
      <ToolBtn icon="⊡" label="Fit to canvas (⌘0)" onClick={fitToCanvas} />

      <Divider />

      {/* Toggles */}
      <ToggleBtn icon="⊞" label="Grid" active={showGrid} onClick={toggleGrid} />
      <ToggleBtn icon="📱" label="Mobile preview" active={isMobilePreview} onClick={toggleMobilePreview} />

      <Divider />

      {/* Validation badge */}
      <button
        className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
          showValidation ? 'bg-teal-50 text-teal-700 border border-teal-300' : 'text-gray-600 hover:bg-gray-100'
        }`}
        onClick={toggleValidation}
        title="Toggle validation panel"
        aria-pressed={showValidation}
      >
        {errorCount > 0 && <span className="bg-red-100 text-red-700 rounded px-1">{errorCount} err</span>}
        {warningCount > 0 && <span className="bg-yellow-100 text-yellow-700 rounded px-1">{warningCount} warn</span>}
        {errorCount === 0 && warningCount === 0 && <span className="text-green-600">✓ Valid</span>}
      </button>

      <Divider />

      {/* File operations */}
      <ToolBtn icon="📂" label="Import JSON" onClick={handleImport} />
      <ToolBtn icon="💾" label="Export JSON" onClick={handleExport} />

      {/* Autosave utilities (small dropdown-like) */}
      <div className="relative group">
        <button className="text-xs text-gray-500 hover:text-gray-700 px-1 py-1" title="Autosave options">⋯</button>
        <div className="hidden group-hover:flex absolute right-0 top-7 flex-col bg-white border border-gray-200 shadow-md rounded z-50 min-w-40 py-1">
          <DropItem label="Restore autosave" onClick={handleRestoreAutosave} />
          <DropItem label="Clear autosave"   onClick={handleClearAutosave} />
        </div>
      </div>

      <div className="flex-1" />

      {/* Dirty indicator */}
      {isDirty && (
        <span className="text-xs text-amber-600 font-medium" title="Unsaved changes">● Unsaved</span>
      )}
    </header>
  );
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function Divider() {
  return <div className="w-px h-6 bg-gray-200 mx-1" />;
}

interface ToolBtnProps {
  icon: string;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}
function ToolBtn({ icon, label, onClick, disabled }: ToolBtnProps) {
  return (
    <button
      className={`w-7 h-7 flex items-center justify-center rounded text-sm transition-colors ${
        disabled ? 'text-gray-300 cursor-not-allowed' : 'text-gray-700 hover:bg-gray-100'
      }`}
      onClick={disabled ? undefined : onClick}
      title={label}
      disabled={disabled}
      aria-label={label}
    >
      {icon}
    </button>
  );
}

interface ModeButtonProps {
  icon: string;
  label: string;
  active: boolean;
  onClick: () => void;
}
function ModeButton({ icon, label, active, onClick }: ModeButtonProps) {
  return (
    <button
      className={`w-7 h-7 flex items-center justify-center rounded text-sm font-medium transition-colors ${
        active ? 'bg-teal-50 text-teal-700 border border-teal-300' : 'text-gray-600 hover:bg-gray-100'
      }`}
      onClick={onClick}
      title={label}
      aria-pressed={active}
      aria-label={label}
    >
      {icon}
    </button>
  );
}

function ToggleBtn({ icon, label, active, onClick }: { icon: string; label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium transition-colors ${
        active ? 'bg-teal-50 text-teal-700 border border-teal-300' : 'text-gray-600 hover:bg-gray-100'
      }`}
      onClick={onClick}
      title={label}
      aria-pressed={active}
      aria-label={label}
    >
      <span>{icon}</span>
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}

function DropItem({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      className="text-xs text-left px-3 py-1.5 text-gray-700 hover:bg-gray-50 w-full"
      onClick={onClick}
    >
      {label}
    </button>
  );
}
