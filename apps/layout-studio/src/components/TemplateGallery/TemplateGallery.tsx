import { useState } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { TEMPLATES, type DashboardTemplate } from '@mt-dashboard/dashboard-templates';

interface Props {
  onClose: () => void;
}

export function TemplateGallery({ onClose }: Props) {
  const applyTemplate = useEditorStore((s) => s.applyTemplate);
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  const filtered = TEMPLATES.filter((t) =>
    !search ||
    t.metadata.name.toLowerCase().includes(search.toLowerCase()) ||
    (t.metadata.description ?? '').toLowerCase().includes(search.toLowerCase())
  );

  const handleApply = () => {
    const tpl = TEMPLATES.find((t) => t.metadata.id === selected);
    if (!tpl) return;
    if (!confirm(`Apply template "${tpl.metadata.name}"? This will replace all visuals on the current page.`)) return;
    applyTemplate(tpl.page);
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-label="Template gallery"
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-base font-semibold text-gray-900">Template Gallery</h2>
            <p className="text-xs text-gray-500 mt-0.5">Choose a starting layout for this page</p>
          </div>
          <button className="text-gray-400 hover:text-gray-600 text-xl" onClick={onClose} aria-label="Close gallery">✕</button>
        </div>

        {/* Search */}
        <div className="px-6 py-3 border-b border-gray-100">
          <input
            type="search"
            placeholder="Search templates…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full text-sm px-3 py-1.5 border border-gray-200 rounded-md focus:outline-none focus:border-teal-400"
            aria-label="Search templates"
          />
        </div>

        {/* Grid */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {filtered.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-8">No templates match your search.</p>
          )}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            {filtered.map((tpl) => (
              <TemplateCard
                key={tpl.metadata.id}
                tpl={tpl}
                selected={selected === tpl.metadata.id}
                onSelect={() => setSelected(tpl.metadata.id)}
              />
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
          <p className="text-xs text-gray-500">
            {selected ? `Selected: ${TEMPLATES.find((t) => t.metadata.id === selected)?.metadata.name}` : 'Select a template to apply it'}
          </p>
          <div className="flex gap-3">
            <button className="text-sm text-gray-600 hover:text-gray-800 px-4 py-1.5 border border-gray-200 rounded-md hover:bg-gray-100 transition-colors" onClick={onClose}>Cancel</button>
            <button
              className={`text-sm px-5 py-1.5 rounded-md font-medium transition-colors ${
                selected ? 'bg-teal-500 hover:bg-teal-600 text-white' : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
              onClick={selected ? handleApply : undefined}
              disabled={!selected}
              aria-disabled={!selected}
            >
              Apply Template
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function TemplateCard({ tpl, selected, onSelect }: { tpl: DashboardTemplate; selected: boolean; onSelect: () => void }) {
  const visualCount = tpl.page.visuals.length;
  const hasProvisionalWarning = tpl.metadata.id === 'cm2-provisional';

  return (
    <button
      className={`text-left rounded-lg border-2 p-3 transition-all focus:outline-none ${
        selected
          ? 'border-teal-500 bg-teal-50 shadow-md'
          : 'border-gray-200 bg-white hover:border-teal-300 hover:shadow-sm'
      }`}
      onClick={onSelect}
      aria-pressed={selected}
      aria-label={`Template: ${tpl.metadata.name}`}
    >
      {/* Thumbnail */}
      <div className={`rounded h-24 mb-2 flex items-center justify-center text-3xl relative ${
        hasProvisionalWarning ? 'bg-amber-50 border border-amber-200' : 'bg-gray-50 border border-gray-100'
      }`}>
        {tpl.metadata.thumbnail ?? '📐'}
        {hasProvisionalWarning && (
          <span className="absolute top-1 right-1 text-xs bg-amber-100 text-amber-700 px-1 rounded">⚠ Provisional</span>
        )}
      </div>

      {/* Info */}
      <div className="font-medium text-xs text-gray-900 truncate">{tpl.metadata.name}</div>
      {tpl.metadata.description && (
        <div className="text-xs text-gray-500 mt-0.5 line-clamp-2 leading-tight">{tpl.metadata.description}</div>
      )}
      <div className="flex items-center justify-between mt-1.5">
        <span className="text-xs text-gray-400">{visualCount} visual{visualCount !== 1 ? 's' : ''}</span>
        {selected && <span className="text-xs text-teal-600 font-medium">✓ Selected</span>}
      </div>
    </button>
  );
}
