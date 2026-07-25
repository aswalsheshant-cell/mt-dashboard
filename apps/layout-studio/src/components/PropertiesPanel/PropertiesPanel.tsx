import React, { useState } from 'react';
import { useEditorStore } from '@/store/editorStore';
import type { Visual, Formatting } from '@mt-dashboard/layout-schema';
import { tokens } from '@mt-dashboard/design-tokens';

export function PropertiesPanel() {
  const selectedIds   = useEditorStore((s) => s.selectedIds);
  const activePage    = useEditorStore((s) => s.activePage());
  const updateVisual  = useEditorStore((s) => s.updateVisual);
  const bringForward  = useEditorStore((s) => s.bringForward);
  const sendBackward  = useEditorStore((s) => s.sendBackward);
  const lockVisuals   = useEditorStore((s) => s.lockVisuals);
  const unlockVisuals = useEditorStore((s) => s.unlockVisuals);
  const toggleVisibility = useEditorStore((s) => s.toggleVisibility);
  const deleteSelected = useEditorStore((s) => s.deleteSelected);
  const align         = useEditorStore((s) => s.align);
  const distribute    = useEditorStore((s) => s.distribute);
  const groupSelected = useEditorStore((s) => s.groupSelected);
  const ungroupSelected = useEditorStore((s) => s.ungroupSelected);

  const [activeTab, setActiveTab] = useState<'position' | 'format' | 'data' | 'interaction'>('position');

  const selected = activePage.visuals.filter((v) => selectedIds.includes(v.id));
  const single = selected.length === 1 ? selected[0] : null;

  const updateSingle = (patch: Partial<Visual>) => {
    if (single) updateVisual(single.id, patch);
  };

  const updateFormatting = (patch: Partial<Formatting>) => {
    if (single) updateVisual(single.id, { formatting: { ...single.formatting, ...patch } });
  };

  return (
    <aside
      className="w-60 bg-white border-l border-gray-200 flex flex-col shrink-0 overflow-hidden"
      role="complementary"
      aria-label="Properties panel"
    >
      {/* Header */}
      <div className="px-3 py-2 border-b border-gray-100 shrink-0">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          {selected.length === 0 ? 'Properties' : selected.length === 1 ? single!.type.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : `${selected.length} selected`}
        </p>
      </div>

      {selected.length === 0 && <EmptyState />}

      {selected.length > 0 && (
        <>
          {/* Multi-select actions */}
          {selected.length > 1 && (
            <MultiSelectActions
              onAlign={align}
              onDistribute={distribute}
              onGroup={groupSelected}
              onUngroup={ungroupSelected}
              onDelete={deleteSelected}
              count={selected.length}
            />
          )}

          {/* Single-select tabs */}
          {single && (
            <>
              <div className="flex border-b border-gray-100 shrink-0">
                {(['position', 'format', 'data', 'interaction'] as const).map((tab) => (
                  <button
                    key={tab}
                    className={`flex-1 py-1.5 text-xs font-medium capitalize transition-colors ${
                      activeTab === tab ? 'text-teal-600 border-b-2 border-teal-500' : 'text-gray-500 hover:text-gray-700'
                    }`}
                    onClick={() => setActiveTab(tab)}
                    aria-selected={activeTab === tab}
                  >
                    {tab === 'interaction' ? 'Interact' : tab}
                  </button>
                ))}
              </div>

              <div className="flex-1 overflow-y-auto">
                {activeTab === 'position' && (
                  <PositionTab
                    visual={single}
                    onChange={updateSingle}
                    onBringForward={() => bringForward([single.id])}
                    onSendBackward={() => sendBackward([single.id])}
                    onToggleLock={() => single.locked ? unlockVisuals([single.id]) : lockVisuals([single.id])}
                    onToggleHide={() => toggleVisibility([single.id])}
                    onDelete={deleteSelected}
                  />
                )}
                {activeTab === 'format' && (
                  <FormatTab visual={single} onChange={updateFormatting} />
                )}
                {activeTab === 'data' && (
                  <DataTab visual={single} onChange={updateSingle} />
                )}
                {activeTab === 'interaction' && (
                  <InteractionTab visual={single} onChange={updateSingle} />
                )}
              </div>
            </>
          )}
        </>
      )}
    </aside>
  );
}

// ── Tabs ───────────────────────────────────────────────────────────────────────

function PositionTab({
  visual, onChange, onBringForward, onSendBackward, onToggleLock, onToggleHide, onDelete,
}: {
  visual: Visual;
  onChange: (p: Partial<Visual>) => void;
  onBringForward: () => void;
  onSendBackward: () => void;
  onToggleLock: () => void;
  onToggleHide: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="p-3 space-y-4">
      <Section title="Position & Size">
        <div className="grid grid-cols-2 gap-2">
          <NumField label="X" value={visual.x} onChange={(v) => onChange({ x: Math.max(0, v) })} />
          <NumField label="Y" value={visual.y} onChange={(v) => onChange({ y: Math.max(0, v) })} />
          <NumField label="W" value={visual.width} onChange={(v) => onChange({ width: Math.max(10, v) })} />
          <NumField label="H" value={visual.height} onChange={(v) => onChange({ height: Math.max(10, v) })} />
        </div>
      </Section>

      <Section title="Title">
        <input
          type="text"
          className="field"
          value={visual.title}
          onChange={(e) => onChange({ title: e.target.value })}
          placeholder="Visual title"
          aria-label="Visual title"
        />
        <input
          type="text"
          className="field mt-1"
          value={visual.subtitle}
          onChange={(e) => onChange({ subtitle: e.target.value })}
          placeholder="Subtitle (optional)"
          aria-label="Subtitle"
        />
      </Section>

      <Section title="Accessibility">
        <input
          type="text"
          className="field"
          value={visual.accessibilityLabel}
          onChange={(e) => onChange({ accessibilityLabel: e.target.value })}
          placeholder="Describe this visual for screen readers"
          aria-label="Accessibility label"
        />
      </Section>

      <Section title="Layer">
        <div className="flex gap-2 mb-2">
          <ActionBtn label="Bring Forward ↑" onClick={onBringForward} />
          <ActionBtn label="Send Backward ↓" onClick={onSendBackward} />
        </div>
        <NumField label="Z-Index" value={visual.zIndex} onChange={(v) => onChange({ zIndex: Math.max(0, Math.min(9999, Math.round(v))) })} />
      </Section>

      <Section title="State">
        <div className="space-y-1">
          <ToggleRow label={visual.locked ? '🔒 Locked' : '🔓 Unlocked'} active={visual.locked} onClick={onToggleLock} />
          <ToggleRow label={visual.hidden ? '🚫 Hidden' : '👁 Visible'}  active={visual.hidden}  onClick={onToggleHide} />
        </div>
      </Section>

      <button
        className="w-full text-xs text-red-500 hover:text-red-700 py-1 border border-red-200 hover:border-red-400 rounded transition-colors mt-2"
        onClick={onDelete}
        aria-label="Delete visual"
      >
        Delete visual
      </button>
    </div>
  );
}

function FormatTab({ visual, onChange }: { visual: Visual; onChange: (p: Partial<Formatting>) => void }) {
  const f = visual.formatting;
  return (
    <div className="p-3 space-y-4">
      <Section title="Background">
        <ColorField label="Fill" value={f.backgroundColor ?? '#FFFFFF'} onChange={(v) => onChange({ backgroundColor: v })} />
        <ColorField label="Border" value={f.borderColor ?? '#E5E7EB'} onChange={(v) => onChange({ borderColor: v })} />
        <NumField label="Border width (px)" value={f.borderWidth ?? 0} min={0} max={10} onChange={(v) => onChange({ borderWidth: v })} />
        <NumField label="Border radius (px)" value={f.borderRadius ?? 4} min={0} max={24} onChange={(v) => onChange({ borderRadius: v })} />
        <NumField label="Padding (px)" value={f.padding ?? 8} min={0} max={40} onChange={(v) => onChange({ padding: v })} />
      </Section>

      <Section title="Title style">
        <CheckboxRow
          label="Show title"
          checked={f.titleVisible !== false}
          onChange={(v) => onChange({ titleVisible: v })}
        />
        <NumField label="Title font size" value={f.titleFontSize ?? 14} min={8} max={32} onChange={(v) => onChange({ titleFontSize: v })} />
        <ColorField label="Title colour" value={f.titleFontColor ?? tokens.color.textPrimary} onChange={(v) => onChange({ titleFontColor: v })} />
        <SelectField
          label="Weight"
          value={f.fontWeight ?? 'normal'}
          options={[{ value: 'normal', label: 'Normal' }, { value: '600', label: 'Semi-bold' }, { value: 'bold', label: 'Bold' }]}
          onChange={(v) => onChange({ fontWeight: v as Formatting['fontWeight'] })}
        />
      </Section>

      <Section title="Chart options">
        <CheckboxRow label="Show legend" checked={f.legendVisible !== false} onChange={(v) => onChange({ legendVisible: v })} />
        <CheckboxRow label="Show data labels" checked={!!f.dataLabelsVisible} onChange={(v) => onChange({ dataLabelsVisible: v })} />
        <CheckboxRow label="X axis" checked={f.xAxisVisible !== false} onChange={(v) => onChange({ xAxisVisible: v })} />
        <CheckboxRow label="Y axis" checked={f.yAxisVisible !== false} onChange={(v) => onChange({ yAxisVisible: v })} />
        <CheckboxRow label="Grid lines" checked={f.gridLinesVisible !== false} onChange={(v) => onChange({ gridLinesVisible: v })} />
      </Section>
    </div>
  );
}

function DataTab({ visual, onChange: _onChange }: { visual: Visual; onChange: (p: Partial<Visual>) => void }) {
  return (
    <div className="p-3 space-y-3">
      <p className="text-xs text-gray-500">
        Measure and category bindings are defined here for reference. Actual data binding is configured in Power BI Desktop.
      </p>
      <Section title="Measures">
        {visual.measures.length === 0
          ? <p className="text-xs text-gray-400 italic">No measures bound</p>
          : visual.measures.map((m, i) => (
            <div key={i} className="text-xs bg-gray-50 rounded px-2 py-1 font-mono text-gray-700">{m.table ? `${m.table}[${m.field}]` : m.field}</div>
          ))
        }
      </Section>
      <Section title="Categories">
        {visual.categories.length === 0
          ? <p className="text-xs text-gray-400 italic">No categories bound</p>
          : visual.categories.map((c, i) => (
            <div key={i} className="text-xs bg-gray-50 rounded px-2 py-1 font-mono text-gray-700">{c.table ? `${c.table}[${c.field}]` : c.field}</div>
          ))
        }
      </Section>
      <Section title="Filters">
        {visual.filters.length === 0
          ? <p className="text-xs text-gray-400 italic">No visual-level filters</p>
          : visual.filters.map((f, i) => (
            <div key={i} className="text-xs bg-gray-50 rounded px-2 py-1 font-mono text-gray-700">{f.field} {f.operator} {JSON.stringify(f.values)}</div>
          ))
        }
      </Section>
    </div>
  );
}

function InteractionTab({ visual, onChange }: { visual: Visual; onChange: (p: Partial<Visual>) => void }) {
  const ia = visual.interactions;
  return (
    <div className="p-3 space-y-4">
      <Section title="Cross-filter">
        <CheckboxRow
          label="Enable cross-filter"
          checked={ia.crossFilterEnabled}
          onChange={(v) => onChange({ interactions: { ...ia, crossFilterEnabled: v } })}
        />
      </Section>
      <Section title="Drillthrough">
        <CheckboxRow
          label="Enable drillthrough"
          checked={ia.drillthroughEnabled}
          onChange={(v) => onChange({ interactions: { ...ia, drillthroughEnabled: v } })}
        />
      </Section>
      <Section title="Tooltip">
        <CheckboxRow
          label="Enable tooltip"
          checked={visual.tooltip.enabled}
          onChange={(v) => onChange({ tooltip: { ...visual.tooltip, enabled: v } })}
        />
      </Section>
    </div>
  );
}

// ── Multi-select actions ───────────────────────────────────────────────────────

function MultiSelectActions({
  count, onAlign, onDistribute, onGroup, onUngroup, onDelete,
}: {
  count: number;
  onAlign: (d: import('@/types').AlignDirection) => void;
  onDistribute: (d: import('@/types').DistributeDirection) => void;
  onGroup: () => void;
  onUngroup: () => void;
  onDelete: () => void;
}) {
  return (
    <div className="p-3 space-y-3 border-b border-gray-100">
      <p className="text-xs text-gray-500">{count} visuals selected</p>
      <Section title="Align">
        <div className="grid grid-cols-3 gap-1">
          {([['left','←L'],['center-h','—H'],['right','R→'],['top','↑T'],['center-v','|V'],['bottom','B↓']] as const).map(([dir, lbl]) => (
            <button key={dir} className="text-xs py-1 border border-gray-200 rounded hover:bg-teal-50 hover:border-teal-300 transition-colors" onClick={() => onAlign(dir)}>{lbl}</button>
          ))}
        </div>
      </Section>
      <Section title="Distribute">
        <div className="flex gap-2">
          <ActionBtn label="Horizontal" onClick={() => onDistribute('horizontal')} />
          <ActionBtn label="Vertical" onClick={() => onDistribute('vertical')} />
        </div>
      </Section>
      <Section title="Group">
        <div className="flex gap-2">
          <ActionBtn label="Group" onClick={onGroup} />
          <ActionBtn label="Ungroup" onClick={onUngroup} />
        </div>
      </Section>
      <button className="w-full text-xs text-red-500 hover:text-red-700 py-1 border border-red-200 hover:border-red-400 rounded transition-colors" onClick={onDelete}>
        Delete selected
      </button>
    </div>
  );
}

// ── Primitive form controls ────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">{title}</p>
      {children}
    </div>
  );
}

function NumField({ label, value, onChange, min, max }: { label: string; value: number; onChange: (v: number) => void; min?: number; max?: number }) {
  return (
    <label className="flex items-center justify-between gap-2">
      <span className="text-xs text-gray-600 shrink-0">{label}</span>
      <input
        type="number"
        className="field w-20 text-right"
        value={Math.round(value)}
        min={min}
        max={max}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-label={label}
      />
    </label>
  );
}

function ColorField({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <label className="flex items-center justify-between gap-2">
      <span className="text-xs text-gray-600 shrink-0">{label}</span>
      <div className="flex items-center gap-1">
        <input type="color" className="w-6 h-6 border border-gray-200 rounded cursor-pointer p-0" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label} />
        <input type="text" className="field w-20 font-mono text-xs" value={value} onChange={(e) => onChange(e.target.value)} aria-label={`${label} hex`} />
      </div>
    </label>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value: string; options: { value: string; label: string }[]; onChange: (v: string) => void }) {
  return (
    <label className="flex items-center justify-between gap-2">
      <span className="text-xs text-gray-600 shrink-0">{label}</span>
      <select className="field text-xs" value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </label>
  );
}

function CheckboxRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" className="accent-teal-500" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="text-xs text-gray-700">{label}</span>
    </label>
  );
}

function ActionBtn({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      className="flex-1 text-xs py-1 border border-gray-200 rounded hover:bg-teal-50 hover:border-teal-300 transition-colors text-gray-700"
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function ToggleRow({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      className={`w-full text-left text-xs px-2 py-1.5 rounded border transition-colors ${
        active ? 'bg-gray-50 border-gray-300 text-gray-700' : 'border-transparent text-gray-600 hover:bg-gray-50'
      }`}
      onClick={onClick}
      aria-pressed={active}
    >
      {label}
    </button>
  );
}

function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center text-gray-400 p-4 text-center">
      <div className="text-3xl mb-2">⬜</div>
      <p className="text-xs">Select a visual to edit its properties.</p>
    </div>
  );
}
