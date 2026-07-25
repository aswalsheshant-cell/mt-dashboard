import { useState } from 'react';
import { useEditorStore } from '@/store/editorStore';

export function PageNavigator() {
  const layout          = useEditorStore((s) => s.layout);
  const activePageIndex = useEditorStore((s) => s.activePageIndex);
  const setActivePageIndex = useEditorStore((s) => s.setActivePageIndex);
  const addPage         = useEditorStore((s) => s.addPage);
  const renamePage      = useEditorStore((s) => s.renamePage);

  const [editingIndex, setEditingIndex] = useState<number | null>(null);
  const [editValue, setEditValue] = useState('');

  const startRename = (i: number, name: string) => {
    setEditingIndex(i);
    setEditValue(name);
  };

  const commitRename = () => {
    if (editingIndex !== null && editValue.trim()) {
      renamePage(editingIndex, editValue.trim());
    }
    setEditingIndex(null);
  };

  return (
    <div
      className="flex items-center gap-1 px-3 h-9 border-t border-gray-200 bg-gray-50 overflow-x-auto shrink-0"
      role="tablist"
      aria-label="Report pages"
    >
      {layout.pages.map((page, i) => (
        <div key={page.id} className="flex-shrink-0">
          {editingIndex === i ? (
            <input
              className="text-xs px-2 py-0.5 border border-teal-400 rounded focus:outline-none bg-white w-28"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              onBlur={commitRename}
              onKeyDown={(e) => { if (e.key === 'Enter') commitRename(); if (e.key === 'Escape') setEditingIndex(null); }}
              autoFocus
              aria-label={`Rename page ${i + 1}`}
            />
          ) : (
            <button
              className={`text-xs px-3 py-1 rounded-t border-t border-x transition-colors whitespace-nowrap ${
                i === activePageIndex
                  ? 'bg-white border-gray-200 text-teal-600 font-semibold -mb-px shadow-sm'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-100'
              }`}
              role="tab"
              aria-selected={i === activePageIndex}
              onClick={() => setActivePageIndex(i)}
              onDoubleClick={() => startRename(i, page.name)}
              title="Double-click to rename"
            >
              {page.name}
            </button>
          )}
        </div>
      ))}

      {layout.pages.length < 50 && (
        <button
          className="text-xs px-2 py-0.5 text-gray-400 hover:text-teal-600 hover:bg-teal-50 rounded transition-colors flex-shrink-0"
          onClick={addPage}
          title="Add page"
          aria-label="Add page"
        >
          + Add page
        </button>
      )}
    </div>
  );
}
