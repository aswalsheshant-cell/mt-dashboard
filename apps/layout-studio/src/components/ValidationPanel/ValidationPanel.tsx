import { useEditorStore } from '@/store/editorStore';
import type { ValidationIssue } from '@/types';
import { tokens } from '@mt-dashboard/design-tokens';

export function ValidationPanel() {
  const issues    = useEditorStore((s) => s.validationIssues);
  const toggle    = useEditorStore((s) => s.toggleValidation);
  const setSelectedIds = useEditorStore((s) => s.setSelectedIds);

  const errors   = issues.filter((i) => i.severity === 'error');
  const warnings = issues.filter((i) => i.severity === 'warning');
  const infos    = issues.filter((i) => i.severity === 'info');

  return (
    <div
      className="border-t border-gray-200 bg-white shrink-0"
      style={{ maxHeight: 200, overflowY: 'auto' }}
      role="region"
      aria-label="Validation panel"
    >
      {/* Header row */}
      <div className="flex items-center gap-3 px-3 py-1.5 bg-gray-50 border-b border-gray-100 sticky top-0">
        <span className="text-xs font-semibold text-gray-600">Validation</span>
        {errors.length > 0   && <Badge count={errors.length}   color="red"    label="errors" />}
        {warnings.length > 0 && <Badge count={warnings.length} color="yellow" label="warnings" />}
        {infos.length > 0    && <Badge count={infos.length}    color="blue"   label="info" />}
        {issues.length === 0 && <span className="text-xs text-green-600 font-medium">✓ No issues</span>}
        <div className="flex-1" />
        <button className="text-gray-400 hover:text-gray-600 text-sm" onClick={toggle} aria-label="Close validation panel">✕</button>
      </div>

      {/* Issue list */}
      {issues.length > 0 && (
        <ul className="divide-y divide-gray-50" role="list">
          {[...errors, ...warnings, ...infos].map((issue, idx) => (
            <IssueRow
              key={idx}
              issue={issue}
              onClick={() => { if (issue.visualId) setSelectedIds([issue.visualId]); }}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

function Badge({ count, color, label }: { count: number; color: 'red' | 'yellow' | 'blue'; label: string }) {
  const cls = {
    red:    'bg-red-100 text-red-700',
    yellow: 'bg-yellow-100 text-yellow-700',
    blue:   'bg-blue-100 text-blue-700',
  }[color];
  return (
    <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${cls}`}>
      {count} {label}
    </span>
  );
}

function IssueRow({ issue, onClick }: { issue: ValidationIssue; onClick: () => void }) {
  const cfg = {
    error:   { icon: '✕', textColor: tokens.color.red700,    bg: '#FFF5F5' },
    warning: { icon: '⚠', textColor: tokens.color.yellow700, bg: '#FFFBEB' },
    info:    { icon: 'ℹ', textColor: tokens.color.blue700,   bg: '#EFF6FF' },
  }[issue.severity];

  return (
    <li>
      <button
        className="w-full flex items-start gap-2 px-3 py-2 text-left hover:brightness-95 transition-all text-xs"
        style={{ background: cfg.bg }}
        onClick={onClick}
        title={issue.visualId ? `Click to select visual ${issue.visualId}` : undefined}
      >
        <span className="shrink-0 mt-0.5" style={{ color: cfg.textColor }}>{cfg.icon}</span>
        <span style={{ color: tokens.color.textPrimary }}>{issue.message}</span>
        {issue.visualId && (
          <span className="ml-auto shrink-0 text-gray-400" title="Click to locate">→</span>
        )}
      </button>
    </li>
  );
}
