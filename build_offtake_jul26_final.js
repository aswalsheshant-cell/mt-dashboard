'use strict';
const pptxgen = require('pptxgenjs');

// ── Palette ───────────────────────────────────────────────────────────────────
const C = {
  navy:    '0D1E35',
  gold:    'C49A1A',
  ink:     '1A2840',
  bg:      'F4F6FB',
  white:   'FFFFFF',
  pos:     '2E7D52',
  neg:     'CC3333',
  amber:   'E67E22',
  blue:    '3A89C9',
  muted:   '8A9BB2',
  midnavy: '1A3459',
  teal:    '1B7A6E',
  lgray:   'D8DDE8',
};

// ── Authoritative data (mt_price_volume.json + july_mt_channel_split.json) ───
const monthly = [
  { month: 'Apr-26', nsv_cr: 35.89, nsv_lakh: 3588.51, units: 1956675, asp: 171.7,  real: 41.6 },
  { month: 'May-26', nsv_cr: 40.19, nsv_lakh: 4019.42, units: 2197203, asp: 173.47, real: 41.7 },
  { month: 'Jun-26', nsv_cr: 38.40, nsv_lakh: 3840.46, units: null,    asp: null,   real: null  },
  { month: 'Jul-26', nsv_cr: 36.06, nsv_lakh: 3606.34, units: 1895052, asp: 179.21, real: 42.2 },
];
const q1Total  = 114.48;  // Q1 FY27 Apr-Jun
const fytdTotal= 150.55;  // Apr-Jul FYTD

// July zone (from article-level xlsb; zone sum = 33.95 ≈ channel-split 33.96)
const julZones = [
  { zone: 'West',    units: 497615, nsv: 8.27, asp: 166.22, aspIdx: 93,  real: 41.9 },
  { zone: 'South-1', units: 433962, nsv: 8.18, asp: 188.56, aspIdx: 105, real: 42.7 },
  { zone: 'North',   units: 377364, nsv: 6.97, asp: 184.82, aspIdx: 103, real: 41.8 },
  { zone: 'South-2', units: 278020, nsv: 4.87, asp: 175.3,  aspIdx: 98,  real: 42.9 },
  { zone: 'East',    units: 183289, nsv: 3.54, asp: 193.17, aspIdx: 108, real: 42.1 },
  { zone: 'Central', units: 124802, nsv: 2.12, asp: 169.69, aspIdx: 95,  real: 41.1 },
];

// Primary vs Offtake conversion (july_mt_channel_split.json — sorted best→worst)
const julConv = [
  { zone: 'South-1', primary: 9.48,  offtake: 8.18, conv: 86.3, gap: 1.30 },
  { zone: 'West',    primary: 9.71,  offtake: 8.27, conv: 85.2, gap: 1.44 },
  { zone: 'Central', primary: 2.62,  offtake: 2.12, conv: 80.9, gap: 0.50 },
  { zone: 'South-2', primary: 6.73,  offtake: 4.87, conv: 72.4, gap: 1.85 },
  { zone: 'North',   primary: 11.38, offtake: 6.97, conv: 61.3, gap: 4.41 },
  { zone: 'East',    primary: 7.10,  offtake: 3.54, conv: 49.9, gap: 3.56 },
];
const mtTotal = { primary: 47.02, offtake: 33.96, conv: 72.2, gap: 13.06 };
const benchmark = 85.73;  // best-zone benchmark (avg West + South-1)
const recoverable = 6.22; // gap recoverable above 25% floor

// FYTD by zone (fy27 = Apr-Jul 4 months)
const fytdZones = [
  { zone: 'West',              fy27: 3732.52, fy26: 8171.0, yoy: 31.47 },
  { zone: 'North',             fy27: 3339.92, fy26: 7060.0, yoy: 62.37 },
  { zone: 'South-1',           fy27: 3308.35, fy26: 6428.0, yoy: 56.70 },
  { zone: 'South-2',           fy27: 2063.89, fy26: 4163.0, yoy: 26.92 },
  { zone: 'East',              fy27: 1528.60, fy26: 3223.0, yoy: 53.84 },
  { zone: 'Pan India (eB2B)',  fy27:  860.01, fy26: 2040.0, yoy: 13.02 },
  { zone: 'Central',           fy27:  211.77, fy26: null,   yoy: null  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
const fmt1 = v => v == null ? '—' : v.toFixed(1);
const fmt2 = v => v == null ? '—' : v.toFixed(2);
const fmtL = v => v == null ? '—' : (v/100).toFixed(2)+'L';  // lakh to display
const fmtU = v => v == null ? '—' : (v/100000).toFixed(2)+'L';

function convColor(pct) {
  if (pct >= 85) return C.pos;
  if (pct >= 70) return C.gold;
  return C.neg;
}

function addHeader(slide, title, subtitle='', dark=true) {
  slide.background = { color: dark ? C.navy : C.bg };
  const fg   = dark ? C.white : C.ink;
  const sfg  = dark ? '8EAACF' : C.muted;
  slide.addText(title, {
    x:0.4, y:0.15, w:8.8, h:0.5,
    fontSize:22, bold:true, color:fg, fontFace:'Cambria', align:'left', margin:0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x:0.4, y:0.65, w:8.8, h:0.28,
      fontSize:11, color:sfg, fontFace:'Calibri', align:'left', margin:0,
    });
  }
  slide.addText('Honasa Consumer Ltd. · MT Analytics · FY\'26-27', {
    x:5.2, y:0.18, w:4.4, h:0.22,
    fontSize:7.5, color:sfg, align:'right', fontFace:'Calibri', margin:0,
  });
  // thin gold rule
  slide.addShape('rect', { x:0.4, y:0.62+(subtitle?0.3:0), w:1.6, h:0.035,
    fill:{color:C.gold}, line:{type:'none'} });
}

function kpiTile(slide, x, y, w, h, val, label, sub='', dark=true) {
  const bg  = dark ? C.midnavy : C.white;
  const fg  = dark ? C.white   : C.ink;
  const sfg = dark ? '8EAACF'  : C.muted;
  slide.addShape('rect', { x, y, w, h, fill:{color:bg}, line:{type:'none'},
    shadow:{type:'outer', blur:4, offset:2, angle:45, color:'8E8E8E', opacity:0.12} });
  slide.addText(val, {
    x:x+0.1, y:y+0.12, w:w-0.2, h:h*0.52,
    fontSize:26, bold:true, color:fg, fontFace:'Cambria', align:'center', margin:0,
  });
  slide.addText(label, {
    x:x+0.06, y:y+h*0.58, w:w-0.12, h:h*0.24,
    fontSize:9.5, bold:true, color:fg, fontFace:'Calibri', align:'center', margin:0,
  });
  if (sub) slide.addText(sub, {
    x:x+0.06, y:y+h*0.82, w:w-0.12, h:h*0.18,
    fontSize:8, color:sfg, fontFace:'Calibri', align:'center', margin:0,
  });
}

// ── Build ─────────────────────────────────────────────────────────────────────
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; // 10 × 5.625

// ═══════════════════════════════════════════
// Slide 1 · Cover
// ═══════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // gold left bar
  s.addShape('rect', { x:0, y:0, w:0.22, h:5.625, fill:{color:C.gold}, line:{type:'none'} });

  // confirmed badge
  s.addShape('rect', { x:0.45, y:0.48, w:2.1, h:0.3,
    fill:{color:C.pos}, line:{type:'none'} });
  s.addText('✓  All 4 Months Confirmed — Final', {
    x:0.5, y:0.5, w:2.0, h:0.26,
    fontSize:8, bold:true, color:C.white, fontFace:'Calibri', margin:0,
  });

  s.addText('MT Offtake Review\nJuly 2026 — Final', {
    x:0.45, y:0.9, w:6.8, h:1.7,
    fontSize:36, bold:true, color:C.white, fontFace:'Cambria',
    align:'left', lineSpacingMultiple:1.15, margin:0,
  });
  s.addText("FY'26-27  ·  Q1 Complete  ·  FYTD Apr–Jul", {
    x:0.45, y:2.72, w:6, h:0.45,
    fontSize:17, color:C.gold, fontFace:'Cambria', align:'left', margin:0,
  });
  s.addText('Honasa Consumer Ltd. — Modern Trade Analytics', {
    x:0.45, y:3.25, w:6, h:0.28,
    fontSize:11, color:'8EAACF', fontFace:'Calibri', align:'left', margin:0,
  });
  s.addText('Data source: Article-level xlsb (pipeline v2.4.0)\nJun-26 final file ingested 2026-08-19  ·  Brand Counter excluded', {
    x:0.45, y:4.8, w:9.1, h:0.6,
    fontSize:8.5, color:'5C7A9B', fontFace:'Calibri', align:'left', margin:0,
  });

  // right side summary strip
  s.addShape('rect', { x:7.6, y:0, w:2.4, h:5.625, fill:{color:C.midnavy}, line:{type:'none'} });
  const strip = [
    { v:'₹150.55 Cr', l:'FYTD Apr–Jul NSV' },
    { v:'₹114.48 Cr', l:'Q1 FY27 (Apr–Jun)' },
    { v:'₹36.06 Cr',  l:'Jul-26 NSV' },
    { v:'72.2%',      l:'Jul Conversion Rate' },
  ];
  strip.forEach((item, i) => {
    const ty = 0.7 + i * 1.15;
    s.addText(item.v, {
      x:7.65, y:ty, w:2.3, h:0.6,
      fontSize:20, bold:true, color:C.gold, fontFace:'Cambria', align:'center', margin:0,
    });
    s.addText(item.l, {
      x:7.65, y:ty+0.6, w:2.3, h:0.3,
      fontSize:8.5, color:'8EAACF', fontFace:'Calibri', align:'center', margin:0,
    });
    if (i < 3) s.addShape('rect', {
      x:8.1, y:ty+0.95, w:1.4, h:0.02,
      fill:{color:'2A4A6A'}, line:{type:'none'},
    });
  });
}

// ═══════════════════════════════════════════
// Slide 2 · Q1 FY27 Scorecard + Jul Snapshot
// ═══════════════════════════════════════════
{
  const s = pres.addSlide();
  addHeader(s, "Q1 FY'26-27 Complete  +  July Snapshot", "NSV in ₹ Cr · All months confirmed · Brand Counter excluded", true);

  // 4 monthly KPI tiles
  const tiles = [
    { v:'₹35.89 Cr', l:'Apr-26 Offtake',  sub:'3,588.51 L · 19.6L units · ASP ₹171.7' },
    { v:'₹40.19 Cr', l:'May-26 Offtake',  sub:'4,019.42 L · 22.0L units · ASP ₹173.5' },
    { v:'₹38.40 Cr', l:'Jun-26 Offtake',  sub:'3,840.46 L · Units TBD (article split pending)' },
    { v:'₹36.06 Cr', l:'Jul-26 Offtake',  sub:'3,606.34 L · 18.95L units · ASP ₹179.2' },
  ];
  tiles.forEach((t, i) => kpiTile(s, 0.22 + i*2.42, 1.08, 2.2, 1.45, t.v, t.l, t.sub, true));

  // Jun confirmed badge
  s.addShape('rect', { x:4.86, y:2.57, w:1.58, h:0.22,
    fill:{color:C.pos}, line:{type:'none'} });
  s.addText('✓ Jun confirmed 2026-08-19', {
    x:4.9, y:2.58, w:1.5, h:0.18,
    fontSize:7.5, bold:true, color:C.white, fontFace:'Calibri', margin:0,
  });

  // Summary row
  const sumItems = [
    { v:'₹114.48 Cr', l:"Q1 FY'26-27 (Apr–Jun)" },
    { v:'₹36.06 Cr',  l:'July-26 NSV' },
    { v:'₹150.55 Cr', l:'FYTD Apr–Jul NSV', highlight:true },
  ];
  sumItems.forEach((item, i) => {
    const x = 0.25 + i * 3.25;
    const bg = item.highlight ? C.gold : '1E3D62';
    const fg = item.highlight ? C.navy : C.white;
    const sf = item.highlight ? '2A3010' : '8EAACF';
    s.addShape('rect', { x, y:2.88, w:3.0, h:1.1,
      fill:{color:bg}, line:{type:'none'},
      shadow:{type:'outer',blur:5,offset:2,angle:45,color:'8E8E8E', opacity:0.18} });
    s.addText(item.v, {
      x:x+0.1, y:2.92, w:2.8, h:0.6,
      fontSize:24, bold:true, color:fg, fontFace:'Cambria', align:'center', margin:0,
    });
    s.addText(item.l, {
      x:x+0.08, y:3.52, w:2.84, h:0.3,
      fontSize:9.5, bold:true, color:sf, fontFace:'Calibri', align:'center', margin:0,
    });
  });

  // source footnote
  s.addText('Source: Article-level xlsb via --offtake-patch pipeline · pipeline v2.4.0 · 2026-08-19', {
    x:0.25, y:4.9, w:9.5, h:0.22,
    fontSize:7.5, color:'4A6080', fontFace:'Calibri', align:'left', margin:0,
  });
}

// ═══════════════════════════════════════════
// Slide 3 · Monthly NSV Trend Apr–Jul
// ═══════════════════════════════════════════
{
  const s = pres.addSlide();
  addHeader(s, 'Monthly Offtake Trend  —  Apr to Jul FY\'26-27',
    'NSV ₹ Cr  ·  MT only (excl. EB2B, SIS, Brand Counter)', false);

  s.addChart(pres.ChartType.bar, [
    {
      name: 'NSV (₹ Cr)',
      labels: ['Apr-26', 'May-26', 'Jun-26', 'Jul-26'],
      values: [35.89, 40.19, 38.40, 36.06],
    }
  ], {
    x:0.35, y:1.05, w:5.6, h:3.8,
    barDir: 'col',
    chartColors: [C.midnavy, C.blue, C.teal, C.navy],
    showValue: true, dataLabelFontSize: 11, dataLabelColor: C.white,
    dataLabelPosition: 'ctr',
    catAxisLabelFontSize: 11, catAxisLabelColor: C.ink,
    valAxisHidden: true,
    catGridLine: { style:'none' }, valGridLine: { style:'none' },
    showLegend: false,
    chartArea: { fill: { color:C.bg } },
    plotArea: { fill: { color:C.bg } },
    showTitle: false,
    border: { pt:0 },
  });

  // Right side commentary tiles
  const notes = [
    { icon:'↑', col:C.pos, h:'May peak: ₹40.19 Cr',     b:'Highest month of FY27 FYTD. Units at 22.0L.' },
    { icon:'✓', col:C.teal, h:'Jun confirmed: ₹38.40 Cr', b:'Final file (6.9 MB) ingested 2026-08-19. Tier 3 cleared.' },
    { icon:'↓', col:C.amber, h:'Jul: ₹36.06 Cr',           b:'72.2% conversion. North & East lag drag total down.' },
    { icon:'■', col:C.gold, h:'Q1 FY27: ₹114.48 Cr',     b:'All 3 months locked. Strong H1 base established.' },
  ];
  notes.forEach((n, i) => {
    const y = 1.08 + i * 1.1;
    s.addShape('rect', { x:6.15, y, w:3.6, h:0.95,
      fill:{color:C.white}, line:{color:C.lgray, pt:1},
      shadow:{type:'outer',blur:3,offset:1,angle:45,color:'8E8E8E', opacity:0.09} });
    s.addShape('rect', { x:6.15, y, w:0.22, h:0.95,
      fill:{color:n.col}, line:{type:'none'} });
    s.addText(n.h, {
      x:6.43, y:y+0.06, w:3.25, h:0.28,
      fontSize:11, bold:true, color:C.ink, fontFace:'Calibri', align:'left', margin:0,
    });
    s.addText(n.b, {
      x:6.43, y:y+0.34, w:3.25, h:0.45,
      fontSize:9.5, color:C.muted, fontFace:'Calibri', align:'left', margin:0,
    });
  });

  // ASP trend callout
  s.addText('ASP Trend: ₹171.7 → ₹173.5 → — → ₹179.2  (+4.4% Apr to Jul)', {
    x:0.35, y:4.95, w:9.3, h:0.22,
    fontSize:8.5, color:C.muted, fontFace:'Calibri', italic:true, align:'left', margin:0,
  });
}

// ═══════════════════════════════════════════
// Slide 4 · July Zone Snapshot
// ═══════════════════════════════════════════
{
  const s = pres.addSlide();
  addHeader(s, 'July-26 Zone Snapshot',
    'NSV ₹ Cr  ·  Units  ·  ASP ₹  ·  ASP Index vs MT avg  ·  Realisation %  ·  Article-level xlsb', false);

  // Table header
  const cols = ['Zone','NSV (₹ Cr)','Units','ASP (₹)','ASP Index','Realisation %'];
  const cw   = [1.55, 1.42, 1.42, 1.2, 1.2, 1.5];
  const tx   = [0.25, 1.8,  3.22, 4.64, 5.84, 7.04];
  const hy = 1.08;

  cols.forEach((c, i) => {
    s.addShape('rect', { x:tx[i], y:hy, w:cw[i], h:0.38,
      fill:{color:C.navy}, line:{type:'none'} });
    s.addText(c, {
      x:tx[i]+0.06, y:hy+0.05, w:cw[i]-0.1, h:0.28,
      fontSize:9.5, bold:true, color:C.white, fontFace:'Calibri', align:'center', margin:0,
    });
  });

  // Zone rows
  julZones.forEach((z, ri) => {
    const ry = hy + 0.38 + ri * 0.52;
    const bg = ri % 2 === 0 ? C.white : C.bg;
    // row bg
    s.addShape('rect', { x:0.25, y:ry, w:8.33, h:0.52,
      fill:{color:bg}, line:{color:C.lgray, pt:0.5} });

    const vals = [
      z.zone,
      '₹'+z.nsv.toFixed(2),
      (z.units/100000).toFixed(2)+'L',
      z.asp != null ? '₹'+z.asp.toFixed(0) : '—',
      z.aspIdx != null ? z.aspIdx : '—',
      z.real != null ? z.real.toFixed(1)+'%' : '—',
    ];
    vals.forEach((v, ci) => {
      const isBold = ci === 0 || ci === 1;
      const color  = ci === 4 ? (z.aspIdx >= 100 ? C.pos : (z.aspIdx >= 95 ? C.amber : C.neg)) : C.ink;
      s.addText(String(v), {
        x:tx[ci]+0.06, y:ry+0.11, w:cw[ci]-0.1, h:0.3,
        fontSize:10.5, bold:isBold, color, fontFace:'Calibri',
        align: ci===0 ? 'left':'center', margin:0,
      });
    });
  });

  // Total row
  const totalY = hy + 0.38 + julZones.length * 0.52;
  s.addShape('rect', { x:0.25, y:totalY, w:8.33, h:0.48,
    fill:{color:C.midnavy}, line:{type:'none'} });
  [
    'MT Total', '₹33.96*',
    ((497615+433962+377364+278020+183289+124802)/100000).toFixed(2)+'L',
    '—', '—', '42.0%'
  ].forEach((v, ci) => {
    s.addText(v, {
      x:tx[ci]+0.06, y:totalY+0.1, w:cw[ci]-0.1, h:0.28,
      fontSize:10.5, bold:true, color:C.white, fontFace:'Calibri',
      align:ci===0?'left':'center', margin:0,
    });
  });

  s.addText('* Zone sum = ₹33.96 Cr (MT channel, excl. EB2B ₹2.07 Cr, SIS ₹0.03 Cr). FYTD total ₹150.55 Cr includes all channels. Realisation = NSV ÷ MRP.', {
    x:0.25, y:4.88, w:9.4, h:0.35,
    fontSize:7.5, color:'5A7090', fontFace:'Calibri', italic:true, align:'left', margin:0,
  });
}

// ═══════════════════════════════════════════
// Slide 5 · Primary vs Offtake Conversion
// ═══════════════════════════════════════════
{
  const s = pres.addSlide();
  addHeader(s, 'July-26  ·  Primary vs Offtake Conversion by Zone',
    'Primary & Offtake ₹ Cr  ·  Conversion % = Offtake ÷ Primary  ·  Benchmark = 85.7% (avg West + South-1)', true);

  // Grouped bar chart
  s.addChart(pres.ChartType.bar, [
    {
      name: 'Primary (₹ Cr)',
      labels: julConv.map(r => r.zone),
      values: julConv.map(r => r.primary),
    },
    {
      name: 'Offtake (₹ Cr)',
      labels: julConv.map(r => r.zone),
      values: julConv.map(r => r.offtake),
    },
  ], {
    x:0.3, y:1.05, w:5.8, h:3.65,
    barDir: 'col', barGrouping: 'clustered',
    chartColors: [C.midnavy, C.teal],
    showValue: true, dataLabelFontSize: 9, dataLabelPosition: 'inEnd',
    catAxisLabelFontSize: 10, catAxisLabelColor: C.white,
    valAxisHidden: true,
    catGridLine:{style:'none'}, valGridLine:{style:'none'},
    showLegend: true, legendPos:'b', legendFontSize:10, legendColor:C.white,
    chartArea:{ fill:{color:C.navy} },
    plotArea: { fill:{color:C.navy} },
    showTitle: false,
  });

  // Conversion % column (right panel)
  s.addShape('rect', { x:6.3, y:1.05, w:3.45, h:0.42,
    fill:{color:'1A3459'}, line:{type:'none'} });
  ['Zone','Conv %','Gap (₹ Cr)'].forEach((h, i) => {
    s.addText(h, {
      x:6.35+i*1.1, y:1.1, w:1.05, h:0.3,
      fontSize:9, bold:true, color:C.white, fontFace:'Calibri',
      align:i===0?'left':'center', margin:0,
    });
  });

  julConv.forEach((r, i) => {
    const ry = 1.47 + i * 0.54;
    const bg = i % 2 === 0 ? C.midnavy : '162B4A';
    s.addShape('rect', { x:6.3, y:ry, w:3.45, h:0.52,
      fill:{color:bg}, line:{type:'none'} });
    s.addText(r.zone, {
      x:6.36, y:ry+0.11, w:1.05, h:0.3,
      fontSize:10, color:C.white, fontFace:'Calibri', align:'left', margin:0,
    });
    s.addText(r.conv.toFixed(1)+'%', {
      x:7.42, y:ry+0.11, w:1.05, h:0.3,
      fontSize:11, bold:true, color:convColor(r.conv), fontFace:'Calibri', align:'center', margin:0,
    });
    s.addText('₹'+r.gap.toFixed(2), {
      x:8.48, y:ry+0.11, w:1.05, h:0.3,
      fontSize:10, color:r.gap>3?C.neg:C.amber, fontFace:'Calibri', align:'center', margin:0,
    });
  });

  // Total row
  s.addShape('rect', { x:6.3, y:4.71, w:3.45, h:0.45,
    fill:{color:C.gold}, line:{type:'none'} });
  [['MT Total','left'], [mtTotal.conv+'%','center'],['₹'+mtTotal.gap.toFixed(2),'center']].forEach(([v, al], i) => {
    s.addText(v, {
      x:6.35+i*1.1, y:4.75, w:1.05, h:0.3,
      fontSize:10.5, bold:true, color:C.navy, fontFace:'Calibri', align:al, margin:0,
    });
  });

  // Recoverable callout
  s.addShape('rect', { x:0.3, y:4.76, w:5.8, h:0.4,
    fill:{color:'1E3A5A'}, line:{type:'none'} });
  s.addText(`Recoverable gap above 25% floor: ₹${recoverable} Cr  ·  North & East at <62% require immediate focus`, {
    x:0.38, y:4.8, w:5.65, h:0.28,
    fontSize:9, bold:true, color:C.gold, fontFace:'Calibri', align:'left', margin:0,
  });
}

// ═══════════════════════════════════════════
// Slide 6 · FYTD Zone Ranking
// ═══════════════════════════════════════════
{
  const s = pres.addSlide();
  addHeader(s, "FYTD Apr–Jul FY'26-27  ·  Zone-wise NSV Ranking",
    'NSV ₹ Lakh  ·  FY27 vs FY26 full-year  ·  YoY % (annualised basis, 4 months vs 12 months)', false);

  // Horizontal bar chart
  const sortedZ = fytdZones.filter(z => z.zone !== 'Pan India (eB2B)').sort((a,b)=>b.fy27-a.fy27);

  s.addChart(pres.ChartType.bar, [
    {
      name: "FY'26-27 FYTD (₹ L)",
      labels: sortedZ.map(z => z.zone),
      values: sortedZ.map(z => z.fy27),
    },
  ], {
    x:0.3, y:1.02, w:5.8, h:3.85,
    barDir: 'bar',
    chartColors: [C.navy],
    showValue: true, dataLabelFontSize: 10, dataLabelPosition: 'inEnd', dataLabelColor: C.white,
    catAxisLabelFontSize: 10, catAxisLabelColor: C.ink,
    valAxisHidden: true,
    catGridLine:{style:'none'}, valGridLine:{style:'none'},
    showLegend: false,
    chartArea:{ fill:{color:C.bg} }, plotArea:{ fill:{color:C.bg} },
    showTitle: false,
  });

  // YoY table
  s.addShape('rect', { x:6.3, y:1.02, w:3.45, h:0.42,
    fill:{color:C.navy}, line:{type:'none'} });
  ['Zone',"FY'27 (₹L)",'YoY %'].forEach((h, i) => {
    s.addText(h, {
      x:6.34+i*1.1, y:1.06, w:1.05, h:0.3,
      fontSize:9, bold:true, color:C.white, fontFace:'Calibri',
      align:i===0?'left':'center', margin:0,
    });
  });

  [...fytdZones].sort((a,b)=>b.fy27-a.fy27).forEach((z, i) => {
    const ry = 1.44 + i * 0.53;
    const bg = i % 2 === 0 ? C.bg : C.white;
    s.addShape('rect', { x:6.3, y:ry, w:3.45, h:0.51,
      fill:{color:bg}, line:{color:C.lgray, pt:0.5} });
    const yoyColor = z.yoy == null ? C.muted : (z.yoy >= 40 ? C.pos : (z.yoy >= 20 ? C.amber : C.neg));
    s.addText(z.zone, { x:6.35, y:ry+0.1, w:1.05, h:0.3,
      fontSize:9.5, color:C.ink, fontFace:'Calibri', align:'left', margin:0 });
    s.addText((z.fy27/100).toFixed(1)+'L', { x:7.42, y:ry+0.1, w:1.0, h:0.3,
      fontSize:9.5, bold:true, color:C.ink, fontFace:'Calibri', align:'center', margin:0 });
    s.addText(z.yoy != null ? '+'+z.yoy.toFixed(1)+'%' : 'New', { x:8.48, y:ry+0.1, w:1.05, h:0.3,
      fontSize:10, bold:true, color:yoyColor, fontFace:'Calibri', align:'center', margin:0 });
  });

  s.addText('YoY % = FY27 FYTD (4 months) vs FY26 full-year (12 months) — directional, not annualised. Central is new in FY27.', {
    x:0.3, y:4.93, w:9.4, h:0.25,
    fontSize:7.5, color:'5A7090', fontFace:'Calibri', italic:true, align:'left', margin:0,
  });
}

// ═══════════════════════════════════════════
// Slide 7 · Insights & Actions
// ═══════════════════════════════════════════
{
  const s = pres.addSlide();
  addHeader(s, 'Key Insights & Actions  —  July 2026', "Based on final pipeline data · FY'26-27 Q1 closed", true);

  const insights = [
    {
      icon: '01',
      color: C.gold,
      title: 'Q1 FY27 Closed at ₹114.48 Cr — All 3 Months Confirmed',
      points: [
        'Jun-26 final file (6.9 MB) ingested 2026-08-19; Tier 3 cleared.',
        'May was the peak month at ₹40.19 Cr / 22.0L units.',
        'Q1 establishes strong base for H2 target planning.',
      ],
    },
    {
      icon: '02',
      color: C.neg,
      title: 'North & East Conversion Below 62% — ₹7.97 Cr Gap',
      points: [
        'North: 61.3% conv (₹11.38 Cr primary → ₹6.97 Cr offtake, gap ₹4.41 Cr).',
        'East: 49.9% conv (₹7.10 Cr primary → ₹3.54 Cr offtake, gap ₹3.56 Cr).',
        'Recoverable gap above floor across MT: ₹6.22 Cr. Prioritise replenishment hygiene.',
      ],
    },
    {
      icon: '03',
      color: C.pos,
      title: 'West & South-1 at Benchmark (>85%) — Replicate Playbook',
      points: [
        'South-1: 86.3% conv · West: 85.2% conv — both above benchmark.',
        'ASP index East (108) and South-1 (105) highest — premium mix holding.',
        'Realisation stable 41–43% across all zones. No MRP dilution signal.',
      ],
    },
  ];

  insights.forEach((ins, i) => {
    const y = 1.08 + i * 1.42;
    s.addShape('rect', { x:0.28, y, w:9.44, h:1.32,
      fill:{color:C.midnavy}, line:{type:'none'},
      shadow:{type:'outer',blur:5,offset:2,angle:45,color:'8E8E8E', opacity:0.22} });
    s.addShape('rect', { x:0.28, y, w:0.55, h:1.32,
      fill:{color:ins.color}, line:{type:'none'} });
    s.addText(ins.icon, {
      x:0.3, y:y+0.44, w:0.51, h:0.4,
      fontSize:14, bold:true, color:C.white, fontFace:'Cambria', align:'center', margin:0,
    });
    s.addText(ins.title, {
      x:0.92, y:y+0.08, w:8.7, h:0.32,
      fontSize:12, bold:true, color:C.white, fontFace:'Calibri', align:'left', margin:0,
    });
    ins.points.forEach((pt, pi) => {
      s.addText('·  ' + pt, {
        x:0.98, y:y+0.42+pi*0.28, w:8.64, h:0.26,
        fontSize:9.5, color:'B8CADF', fontFace:'Calibri', align:'left', margin:0,
      });
    });
  });
}

// ── Write ─────────────────────────────────────────────────────────────────────
pres.writeFile({ fileName: 'MT_Offtake_Jul26_Final.pptx' })
  .then(() => console.log('✓  MT_Offtake_Jul26_Final.pptx written'))
  .catch(e => { console.error(e); process.exit(1); });
