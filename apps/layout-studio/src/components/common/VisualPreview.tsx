import React from 'react';
import type { Visual } from '@mt-dashboard/layout-schema';
import { tokens } from '@mt-dashboard/design-tokens';
import { getVisualMeta } from '@/constants/visuals';

interface Props {
  visual: Visual;
  zoom: number;
}

// Renders a lightweight placeholder inside the canvas at design time.
// All previews are illustrative only — final rendering happens in Power BI.
export function VisualPreview({ visual, zoom }: Props) {
  const meta = getVisualMeta(visual.type);
  const bg = visual.formatting.backgroundColor ?? tokens.color.bgPanel;
  const titleColor = visual.formatting.titleFontColor ?? tokens.color.textPrimary;
  const titleVisible = visual.formatting.titleVisible !== false;
  const borderRadius = Math.max(0, visual.formatting.borderRadius ?? 4);
  const borderWidth = visual.formatting.borderWidth ?? 0;
  const borderColor = visual.formatting.borderColor ?? tokens.color.gray200;
  const padding = visual.formatting.padding ?? 8;

  const containerStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    background: bg,
    borderRadius,
    border: borderWidth > 0 ? `${borderWidth}px solid ${borderColor}` : 'none',
    padding,
    boxSizing: 'border-box',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    userSelect: 'none',
  };

  const scaledFontSize = Math.max(9, (visual.formatting.titleFontSize ?? 14) * zoom);

  return (
    <div style={containerStyle}>
      {titleVisible && visual.title && (
        <div
          style={{
            fontSize: scaledFontSize,
            fontWeight: visual.formatting.fontWeight === 'bold' ? '700' : '600',
            color: titleColor,
            marginBottom: 4 * zoom,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            lineHeight: 1.3,
            flexShrink: 0,
          }}
        >
          {visual.title}
        </div>
      )}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2 * zoom }}>
        <PreviewBody visual={visual} zoom={zoom} icon={meta.icon} />
      </div>
    </div>
  );
}

// ── Per-type preview bodies ────────────────────────────────────────────────────

function PreviewBody({ visual, zoom, icon }: { visual: Visual; zoom: number; icon: string }) {
  const fontSize = Math.max(10, 11 * zoom);
  const iconSize = Math.max(14, 28 * zoom);
  const subtitleColor = tokens.color.textSecondary;

  switch (visual.type) {
    case 'kpi-card':
      return <KpiPreview visual={visual} zoom={zoom} />;

    case 'bar-chart':
    case 'column-chart':
      return <BarPreview isColumn={visual.type === 'column-chart'} palette={tokens.color.chart1} />;

    case 'line-chart':
      return <LinePreview />;

    case 'combo-chart':
      return <ComboPreview />;

    case 'pie-chart':
    case 'donut-chart':
      return <PiePreview isDonut={visual.type === 'donut-chart'} />;

    case 'gauge':
      return <GaugePreview />;

    case 'table':
    case 'matrix':
      return <TablePreview isMatrix={visual.type === 'matrix'} />;

    case 'slicer':
      return <SlicerPreview />;

    case 'text':
      return (
        <div style={{ fontSize, color: subtitleColor, textAlign: 'center', padding: '0 4px', wordBreak: 'break-word' }}>
          {visual.subtitle || 'Text box'}
        </div>
      );

    case 'image-placeholder':
      return (
        <div style={{ textAlign: 'center', color: subtitleColor }}>
          <div style={{ fontSize: iconSize }}>{icon}</div>
          <div style={{ fontSize, marginTop: 2 }}>Image</div>
        </div>
      );

    default:
      return (
        <div style={{ textAlign: 'center', color: subtitleColor }}>
          <div style={{ fontSize: iconSize }}>{icon}</div>
          <div style={{ fontSize, marginTop: 2 }}>Power BI Desktop required</div>
        </div>
      );
  }
}

// ── Mini chart previews ────────────────────────────────────────────────────────

function KpiPreview({ visual, zoom }: { visual: Visual; zoom: number }) {
  const val = visual.measures[0]?.displayName ?? '—';
  const fontSize = Math.max(16, 32 * zoom);
  const subSize = Math.max(9, 11 * zoom);
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize, fontWeight: '700', color: tokens.color.teal500, lineHeight: 1 }}>{val}</div>
      <div style={{ fontSize: subSize, color: tokens.color.textSecondary, marginTop: 2 }}>
        {visual.subtitle || 'Measure'}
      </div>
    </div>
  );
}

function BarPreview({ isColumn, palette }: { isColumn: boolean; palette: string }) {
  const bars = [0.6, 1, 0.45, 0.8, 0.35];
  if (isColumn) {
    return (
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: '70%', paddingBottom: 2 }}>
        {bars.map((h, i) => (
          <div key={i} style={{ flex: 1, background: palette, height: `${h * 100}%`, borderRadius: '2px 2px 0 0', opacity: 0.7 + i * 0.06 }} />
        ))}
      </div>
    );
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, width: '85%' }}>
      {bars.map((w, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
          <div style={{ width: `${w * 100}%`, height: 8, background: palette, borderRadius: '0 2px 2px 0', opacity: 0.7 + i * 0.06 }} />
        </div>
      ))}
    </div>
  );
}

function LinePreview() {
  return (
    <svg viewBox="0 0 80 40" width="80%" height="60%" style={{ overflow: 'visible' }}>
      <polyline points="0,35 15,25 30,30 45,15 60,20 75,8" fill="none" stroke={tokens.color.chart1} strokeWidth="2" strokeLinejoin="round" />
      <polyline points="0,38 15,32 30,36 45,28 60,30 75,22" fill="none" stroke={tokens.color.chart2} strokeWidth="2" strokeLinejoin="round" strokeDasharray="3 2" />
    </svg>
  );
}

function ComboPreview() {
  const bars = [0.5, 0.8, 0.6, 0.9];
  return (
    <svg viewBox="0 0 80 48" width="80%" height="70%">
      {bars.map((h, i) => (
        <rect key={i} x={i * 20 + 2} y={48 - h * 40} width="14" height={h * 40} fill={tokens.color.chart1} opacity={0.5} />
      ))}
      <polyline points="9,28 29,18 49,24 69,10" fill="none" stroke={tokens.color.chart3} strokeWidth="2.5" strokeLinejoin="round" />
    </svg>
  );
}

function PiePreview({ isDonut }: { isDonut: boolean }) {
  const r = isDonut ? 16 : 20;
  const inner = isDonut ? 9 : 0;
  const colors = [tokens.color.chart1, tokens.color.chart2, tokens.color.chart3, tokens.color.chart4];
  const slices = [0.4, 0.25, 0.2, 0.15];
  let angle = -Math.PI / 2;
  const cx = 24, cy = 24;

  const paths = slices.map((pct, i) => {
    const start = angle;
    const end = angle + pct * 2 * Math.PI;
    const x1 = cx + r * Math.cos(start), y1 = cy + r * Math.sin(start);
    const x2 = cx + r * Math.cos(end),   y2 = cy + r * Math.sin(end);
    const xi1 = cx + inner * Math.cos(start), yi1 = cy + inner * Math.sin(start);
    const xi2 = cx + inner * Math.cos(end),   yi2 = cy + inner * Math.sin(end);
    const large = pct > 0.5 ? 1 : 0;
    const d = isDonut
      ? `M${xi1},${yi1} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} L${xi2},${yi2} A${inner},${inner} 0 ${large} 0 ${xi1},${yi1} Z`
      : `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} Z`;
    angle = end;
    return <path key={i} d={d} fill={colors[i]} opacity={0.8} />;
  });

  return (
    <svg viewBox="0 0 48 48" width="60%" height="60%">
      {paths}
    </svg>
  );
}

function GaugePreview() {
  const pct = 0.65;
  const r = 18, cx = 24, cy = 28;
  const startA = Math.PI, endA = startA + pct * Math.PI;
  const x1 = cx + r * Math.cos(startA), y1 = cy + r * Math.sin(startA);
  const x2 = cx + r * Math.cos(endA),   y2 = cy + r * Math.sin(endA);
  return (
    <svg viewBox="0 0 48 36" width="70%" height="70%">
      <path d={`M${cx - r},${cy} A${r},${r} 0 0 1 ${cx + r},${cy}`} fill="none" stroke={tokens.color.gray200} strokeWidth="6" strokeLinecap="round" />
      <path d={`M${x1},${y1} A${r},${r} 0 0 1 ${x2},${y2}`} fill="none" stroke={tokens.color.chart1} strokeWidth="6" strokeLinecap="round" />
      <text x={cx} y={cy + 2} textAnchor="middle" fontSize="8" fill={tokens.color.textPrimary} fontWeight="bold">{Math.round(pct * 100)}%</text>
    </svg>
  );
}

function TablePreview({ isMatrix: _isMatrix }: { isMatrix: boolean }) {
  const rows = 3;
  const cols = 3;
  return (
    <div style={{ width: '90%', fontSize: 8, color: tokens.color.textSecondary }}>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 1 }}>
        {Array.from({ length: cols }).map((_, c) => (
          <div key={c} style={{ background: tokens.color.teal500, color: '#fff', padding: '2px 3px', borderRadius: 1, fontSize: 7, fontWeight: 600, textAlign: 'center' }}>
            {['Brand', 'Primary', 'Offtake'][c] ?? `Col ${c + 1}`}
          </div>
        ))}
        {Array.from({ length: rows }).flatMap((_, r) =>
          Array.from({ length: cols }).map((__, c) => (
            <div key={`${r}-${c}`} style={{ background: r % 2 === 0 ? tokens.color.gray50 : '#fff', padding: '2px 3px', borderRadius: 1, textAlign: 'center', fontSize: 7 }}>
              {'—'}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function SlicerPreview() {
  const items = ['All', 'Brand A', 'Brand B', 'Brand C'];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, width: '85%' }}>
      {items.map((label, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 4, fontSize: 9,
          color: i === 0 ? tokens.color.teal500 : tokens.color.textSecondary,
        }}>
          <div style={{
            width: 10, height: 10, borderRadius: 2, flexShrink: 0,
            border: `1.5px solid ${i === 0 ? tokens.color.teal500 : tokens.color.gray300}`,
            background: i === 0 ? tokens.color.teal500 : 'transparent',
          }} />
          {label}
        </div>
      ))}
    </div>
  );
}
