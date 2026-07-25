import { useState } from 'react';
import { useEditorStore } from '@/store/editorStore';
import { VISUAL_CATALOG, VISUAL_CATALOG_BY_CATEGORY } from '@/constants/visuals';
import type { VisualType } from '@mt-dashboard/layout-schema';

const CATEGORY_LABELS: Record<string, string> = {
  kpi:    'KPI',
  chart:  'Charts',
  data:   'Data',
  filter: 'Filters',
  layout: 'Layout',
};

export function VisualPicker() {
  const addVisual = useEditorStore((s) => s.addVisual);
  const setMode   = useEditorStore((s) => s.setMode);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const filtered = VISUAL_CATALOG.filter((v) => {
    const matchesSearch = !search || v.label.toLowerCase().includes(search.toLowerCase()) || v.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !activeCategory || v.category === activeCategory;
    return matchesSearch && matchesCategory;
  });

  const handleAdd = (type: VisualType) => {
    addVisual(type, 40, 40);
    setMode('select');
  };

  const categories = Object.keys(VISUAL_CATALOG_BY_CATEGORY);

  return (
    <aside
      className="w-52 bg-white border-r border-gray-200 flex flex-col shrink-0 overflow-hidden"
      role="complementary"
      aria-label="Visual picker"
    >
      <div className="px-3 py-2 border-b border-gray-100">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Add Visual</p>
        <input
          type="search"
          placeholder="Search…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full text-xs px-2 py-1 border border-gray-200 rounded focus:outline-none focus:border-teal-400"
          aria-label="Search visuals"
        />
      </div>

      {/* Category tabs */}
      {!search && (
        <div className="flex flex-wrap gap-1 px-2 pt-2">
          <CategoryChip
            label="All"
            active={activeCategory === null}
            onClick={() => setActiveCategory(null)}
          />
          {categories.map((cat) => (
            <CategoryChip
              key={cat}
              label={CATEGORY_LABELS[cat] ?? cat}
              active={activeCategory === cat}
              onClick={() => setActiveCategory(cat)}
            />
          ))}
        </div>
      )}

      {/* Visual list */}
      <div className="flex-1 overflow-y-auto py-1" role="list">
        {filtered.length === 0 && (
          <p className="text-xs text-gray-400 text-center py-4">No visuals match.</p>
        )}
        {filtered.map((meta) => (
          <button
            key={meta.type}
            role="listitem"
            className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-teal-50 focus:outline-none focus:bg-teal-50 transition-colors group"
            onClick={() => handleAdd(meta.type)}
            title={meta.description}
            aria-label={`Add ${meta.label}`}
          >
            <span className="text-base w-6 text-center shrink-0">{meta.icon}</span>
            <div className="min-w-0">
              <div className="text-xs font-medium text-gray-800 truncate">{meta.label}</div>
              <div className="text-xs text-gray-400 truncate leading-tight">{meta.description}</div>
            </div>
          </button>
        ))}
      </div>
    </aside>
  );
}

function CategoryChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      className={`text-xs px-2 py-0.5 rounded-full border transition-colors ${
        active
          ? 'bg-teal-500 text-white border-teal-500'
          : 'text-gray-600 border-gray-200 hover:border-teal-300 hover:text-teal-600'
      }`}
      onClick={onClick}
      aria-pressed={active}
    >
      {label}
    </button>
  );
}
