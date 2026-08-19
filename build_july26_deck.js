'use strict';
const pptxgen = require('pptxgenjs');

// ── Palette ──────────────────────────────────────────────────────────────────
const C = {
  navy:    '0D1E35',
  gold:    'C49A1A',
  ink:     '1A2840',
  bg:      'F4F6FB',
  white:   'FFFFFF',
  pos:     '2E7D52',
  neg:     'CC3333',
  blue:    '3A89C9',
  muted:   '8A9BB2',
  midnavy: '1A3459',
  amber:   'E67E22',
};

// ── Data ─────────────────────────────────────────────────────────────────────
const pv = {
  months: ['Apr', 'May', 'Jul'],
  units:  [1956675, 2197203, 1895052],
  nsv:    [33.60, 38.11, 33.96],
  asp:    [171.7, 173.47, 179.21],
  real:   [41.6, 41.7, 42.2],
};

const zoneRows = [
  { zone: 'South-1', primary: 9.48,  offtake: 8.18,  conv: 86.3, gap: 1.30 },
  { zone: 'West',    primary: 9.71,  offtake: 8.27,  conv: 85.2, gap: 1.44 },
  { zone: 'Central', primary: 2.62,  offtake: 2.12,  conv: 80.9, gap: 0.50 },
  { zone: 'South-2', primary: 6.73,  offtake: 4.87,  conv: 72.4, gap: 1.85 },
  { zone: 'North',   primary: 11.38, offtake: 6.97,  conv: 61.3, gap: 4.41 },
  { zone: 'East',    primary: 7.10,  offtake: 3.54,  conv: 49.9, gap: 3.56 },
];

const accountRows = [
  { acct: 'DMart',     primary: 18.25, offtake: 13.97 },
  { acct: 'Reliance',  primary: 15.66, offtake: 8.06  },
  { acct: 'Apollo',    primary: 7.20,  offtake: 7.18  },
  { acct: 'FSN/Nykaa', primary: 2.08,  offtake: 2.07  },
  { acct: 'Lulu',      primary: 0,     offtake: 1.70  },
  { acct: 'Wellness',  primary: 0.49,  offtake: 0.72  },
  { acct: 'H&G',       primary: 0.22,  offtake: 0.51  },
  { acct: 'Metro',     primary: 1.84,  offtake: 0.49  },
];

const brandRows = [
  { brand: 'Mamaearth',     primary: 33.38, offtake: 24.49 },
  { brand: 'The Derma Co.', primary: 15.19, offtake: 11.03 },
  { brand: 'Aqualogica',    primary: 0.41,  offtake: 0.48  },
  { brand: 'BBlunt',        primary: 0.18,  offtake: 0.06  },
  { brand: "Dr. Sheth's",   primary: 0,     offtake: 0.03  },
];

// Trend months label
const trendMonths = ['Feb','Mar','Apr','May','Jun','Jul'];
const mhTrend = {
  'Face Cleanser': [7.03, 8.17, 8.55, 9.63, 9.65, 8.53],
  'Shampoo':       [4.81, 5.38, 6.11, 6.68, 6.87, 6.95],
  'Sun Care':      [1.55, 2.73, 3.10, 2.95, 1.99, 1.30],
};
const dcTrend = {
  'Face Cleanser': [2.25, 2.75, 3.24, 4.63, 4.83, 7.13],
  'Sun Care':      [1.04, 1.81, 2.27, 3.18, 2.05, 1.99],
  'Face Serum':    [0.56, 0.57, 0.69, 0.66, 0.66, 0.63],
};

const eb2bMonths = ['Jan','Feb','Mar','Apr','May','Jun','Jul'];
const eb2bVals  = [1.64, 1.68, 1.73, 2.29, 2.08, 2.17, 2.07];

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmt(v, dec=2) { return v.toFixed(dec); }

function addSlideHeader(slide, title, light=false) {
  const bg   = light ? C.bg    : C.navy;
  const fg   = light ? C.ink   : C.white;
  const sub  = light ? C.muted : '8EAACF';
  slide.background = { color: bg };
  // title
  slide.addText(title, {
    x: 0.4, y: 0.18, w: 9.2, h: 0.55,
    fontSize: 24, bold: true, color: fg,
    fontFace: 'Cambria', align: 'left', margin: 0,
  });
  // thin gold accent line below title
  slide.addShape('rect', {
    x: 0.4, y: 0.75, w: 1.8, h: 0.04,
    fill: { color: C.gold }, line: { type: 'none' },
  });
  // right watermark
  slide.addText('Honasa Consumer Ltd. · MT Analytics', {
    x: 5.5, y: 0.22, w: 4.1, h: 0.25,
    fontSize: 8, color: sub, align: 'right', fontFace: 'Calibri', margin: 0,
  });
}

function tier3Badge(slide, x, y) {
  slide.addShape('rect', {
    x, y, w: 1.55, h: 0.28,
    fill: { color: C.amber }, line: { type: 'none' }, rectRadius: 0.04,
  });
  slide.addText('⚠ Tier 3 · Jun source absent', {
    x: x+0.04, y: y+0.02, w: 1.47, h: 0.24,
    fontSize: 7.5, bold: true, color: C.white, fontFace: 'Calibri', margin: 0,
  });
}

function convColor(pct) {
  if (pct >= 85)   return C.pos;
  if (pct >= 70)   return C.gold;
  return C.neg;
}

// ── Presentation ──────────────────────────────────────────────────────────────
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; // 10 × 5.625

// ══════════════════════════════════════════════════════════════════════════════
// Slide 1 · Cover
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // big brand bar
  s.addShape('rect', { x: 0, y: 0, w: 0.18, h: 5.625, fill: { color: C.gold }, line: { type: 'none' } });

  s.addText('MT Performance &\nMarket Share Review', {
    x: 0.42, y: 0.8, w: 6.5, h: 1.6,
    fontSize: 34, bold: true, color: C.white, fontFace: 'Cambria',
    align: 'left', lineSpacingMultiple: 1.15, margin: 0,
  });
  s.addText('July 2026  ·  Q1 FY27 Context', {
    x: 0.42, y: 2.55, w: 5.5, h: 0.45,
    fontSize: 18, color: C.gold, fontFace: 'Cambria', align: 'left', margin: 0,
  });
  s.addText('Honasa Consumer Ltd. — Modern Trade Analytics', {
    x: 0.42, y: 3.1, w: 6, h: 0.3,
    fontSize: 11, color: '8EAACF', fontFace: 'Calibri', align: 'left', margin: 0,
  });

  // channels box
  s.addShape('rect', {
    x: 0.42, y: 3.6, w: 3.5, h: 0.85,
    fill: { color: C.midnavy }, line: { type: 'none' }, rectRadius: 0.06,
  });
  s.addText('Channels: MT Zones · eB2B (Nykaa/FSN) · SIS\nData governance: 3-Tier Pre-Flight Protocol active', {
    x: 0.56, y: 3.68, w: 3.3, h: 0.7,
    fontSize: 9, color: C.white, fontFace: 'Calibri', margin: 0, lineSpacingMultiple: 1.4,
  });

  // June badge
  s.addShape('rect', {
    x: 0.42, y: 4.6, w: 3.1, h: 0.28,
    fill: { color: C.amber }, line: { type: 'none' }, rectRadius: 0.04,
  });
  s.addText('⚠ Tier 3 · Jun offtake source file absent — Q1 partial (Apr+May)', {
    x: 0.52, y: 4.62, w: 2.95, h: 0.24,
    fontSize: 7.5, bold: true, color: C.white, fontFace: 'Calibri', margin: 0,
  });

  // right KPI panel
  const kpis = [
    { label: 'MT Offtake Jul',  val: '₹33.96 Cr', color: C.gold },
    { label: 'MT Primary Jul',  val: '₹47.02 Cr', color: C.white },
    { label: 'Conversion',      val: '72.2%',      color: C.gold },
    { label: 'Gap to Primary',  val: '₹13.06 Cr',  color: C.neg  },
  ];
  s.addShape('rect', { x: 7.3, y: 0.6, w: 2.3, h: 4.5, fill: { color: C.midnavy }, line: { type: 'none' }, rectRadius: 0.08 });
  kpis.forEach((k, i) => {
    const yy = 0.85 + i * 1.05;
    s.addText(k.val, { x: 7.4, y: yy, w: 2.1, h: 0.5, fontSize: 22, bold: true, color: k.color, fontFace: 'Cambria', align: 'center', margin: 0 });
    s.addText(k.label, { x: 7.4, y: yy + 0.52, w: 2.1, h: 0.25, fontSize: 8.5, color: '8EAACF', fontFace: 'Calibri', align: 'center', margin: 0 });
  });

  s.addNotes('Welcome to the MT Performance Review for July 2026 with Q1 FY27 context. This deck covers Modern Trade zones, eB2B (Nykaa/FSN), and SIS channels. Note that June offtake source is absent — Q1 figures are partial (Apr+May only) per Tier 3 governance. All numbers are exact from source files; no estimates or fabricated data.');
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 2 · Q1 FY27 Offtake Snapshot (Apr–Jun + Jul as Q2 opener)
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addSlideHeader(s, 'Q1 FY27 Offtake Snapshot  ·  Apr – Jun \'26', true);

  // Month KPI cards  (Apr, May, Jun[missing], Jul)
  const cards = [
    { month: 'Apr \'26', nsv: '₹33.60 Cr', units: '19.6 L', asp: '₹171.7', real: '41.6%', missing: false },
    { month: 'May \'26', nsv: '₹38.11 Cr', units: '22.0 L', asp: '₹173.5', real: '41.7%', missing: false },
    { month: 'Jun \'26', nsv: '—',          units: '—',      asp: '—',      real: '—',      missing: true  },
    { month: 'Jul \'26', nsv: '₹33.96 Cr', units: '18.9 L', asp: '₹179.2', real: '42.2%', missing: false, q2: true },
  ];

  const cw = 2.12, cx0 = 0.35, cy = 0.97;
  cards.forEach((c, i) => {
    const cx = cx0 + i * (cw + 0.12);
    const fill = c.missing ? 'F0E8D0' : (c.q2 ? 'EAF0FB' : C.white);
    const border = c.missing ? { color: C.amber, size: 1.5, type: 'solid' } : { color: c.q2 ? C.blue : 'D0D8E8', size: 1, type: 'solid' };
    s.addShape('rect', { x: cx, y: cy, w: cw, h: 2.65, fill: { color: fill }, line: border, rectRadius: 0.08 });
    // month header
    const mhBg = c.missing ? C.amber : (c.q2 ? C.blue : C.navy);
    s.addShape('rect', { x: cx, y: cy, w: cw, h: 0.35, fill: { color: mhBg }, line: { type: 'none' }, rectRadius: 0.08 });
    s.addText(c.month + (c.q2 ? ' (Q2)' : ''), {
      x: cx+0.05, y: cy+0.04, w: cw-0.1, h: 0.27,
      fontSize: 10, bold: true, color: C.white, fontFace: 'Cambria', align: 'center', margin: 0,
    });
    if (c.missing) {
      s.addText('Source file\nabsent', { x: cx+0.1, y: cy+0.55, w: cw-0.2, h: 0.6, fontSize: 11, bold: true, color: C.amber, fontFace: 'Calibri', align: 'center', margin: 0 });
      s.addText('Tier 3 — awaiting\nJun offtake feed', { x: cx+0.1, y: cy+1.25, w: cw-0.2, h: 0.5, fontSize: 8.5, color: '6B5B00', fontFace: 'Calibri', align: 'center', margin: 0 });
    } else {
      const rows = [
        { lbl: 'NSV',         val: c.nsv  },
        { lbl: 'Volume',      val: c.units },
        { lbl: 'ASP',         val: c.asp   },
        { lbl: 'Realisation', val: c.real  },
      ];
      rows.forEach((r, ri) => {
        const ry = cy + 0.42 + ri * 0.54;
        s.addText(r.lbl, { x: cx+0.1, y: ry, w: cw-0.2, h: 0.22, fontSize: 7.5, color: C.muted, fontFace: 'Calibri', align: 'left', margin: 0 });
        s.addText(r.val, { x: cx+0.1, y: ry+0.21, w: cw-0.2, h: 0.28, fontSize: 13, bold: true, color: C.ink, fontFace: 'Cambria', align: 'left', margin: 0 });
      });
    }
  });

  // ASP premiumisation arrow note
  s.addText('ASP Premiumisation: ₹171.7 → ₹173.5 → ₹179.2  (+4.4% Apr–Jul)  ·  Realisation: 41.6% → 42.2%', {
    x: 0.35, y: 3.75, w: 9.3, h: 0.3,
    fontSize: 9.5, color: C.pos, bold: true, fontFace: 'Calibri', align: 'left', margin: 0,
  });
  s.addText('Q1 partial basis: Apr + May only (Jun absent). Jul shown as Q2 reference month.', {
    x: 0.35, y: 4.1, w: 9.3, h: 0.25,
    fontSize: 8, color: C.muted, fontFace: 'Calibri', align: 'left', margin: 0,
  });

  // Q1 partial sum
  const q1nsv = 33.60 + 38.11;
  s.addShape('rect', { x: 0.35, y: 4.42, w: 4.2, h: 0.62, fill: { color: C.midnavy }, line: { type: 'none' }, rectRadius: 0.06 });
  s.addText(`Q1 Partial (Apr+May): ₹${q1nsv.toFixed(2)} Cr NSV  ·  40.9 L units  ·  Q1 full unavailable (Jun missing)`, {
    x: 0.48, y: 4.5, w: 3.95, h: 0.45,
    fontSize: 8.5, color: C.white, fontFace: 'Calibri', align: 'left', margin: 0,
  });

  s.addNotes('Q1 FY27 offtake: April delivered ₹33.6 Cr on 19.6 lakh units; May grew to ₹38.11 Cr on 22 lakh units — a strong 13% month-on-month. June source file is absent (Tier 3 pipeline block), so Q1 is only partial. July at ₹33.96 Cr opens Q2. The ASP premiumisation story is the standout: from ₹171.7 in April to ₹179.2 in July, a 4.4% appreciation reflecting portfolio mix shift. Realisation also crept up from 41.6% to 42.2%.');
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 3 · July '26 MT Overview KPIs
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };
  addSlideHeader(s, 'July \'26  ·  MT Channel Overview', false);

  // 4 headline KPIs
  const kpis = [
    { label: 'Primary (MT)',    val: '₹47.02 Cr', sub: 'Jul \'26',       color: C.white },
    { label: 'Offtake (MT)',    val: '₹33.96 Cr', sub: 'Jul \'26',       color: C.gold  },
    { label: 'Conversion',      val: '72.2%',      sub: 'vs 85.7% bmk',  color: C.amber },
    { label: 'Primary–Offtake Gap', val: '₹13.06 Cr', sub: 'Recoverable ₹6.22 Cr above floor', color: C.neg },
  ];
  const kw = 2.1, ky = 1.0;
  kpis.forEach((k, i) => {
    const kx = 0.35 + i * (kw + 0.22);
    s.addShape('rect', { x: kx, y: ky, w: kw, h: 1.45, fill: { color: C.midnavy }, line: { type: 'none' }, rectRadius: 0.08 });
    s.addText(k.val, { x: kx+0.08, y: ky+0.12, w: kw-0.16, h: 0.65, fontSize: 26, bold: true, color: k.color, fontFace: 'Cambria', align: 'center', margin: 0 });
    s.addText(k.label, { x: kx+0.08, y: ky+0.78, w: kw-0.16, h: 0.28, fontSize: 9, color: '8EAACF', fontFace: 'Calibri', align: 'center', margin: 0 });
    s.addText(k.sub, { x: kx+0.08, y: ky+1.08, w: kw-0.16, h: 0.25, fontSize: 8, color: C.muted, fontFace: 'Calibri', align: 'center', margin: 0 });
  });

  // eB2B + SIS strip
  const strip = [
    { ch: 'eB2B (Nykaa/FSN)', primary: '₹2.20 Cr', offtake: '₹2.07 Cr', flow: '93.9% flow', note: 'Separate channel · not in MT zones' },
    { ch: 'SIS (Azorte etc.)', primary: '–₹0.006 Cr', offtake: '₹0.034 Cr', flow: 'Net of MRN', note: 'Separate channel · not in MT zones' },
  ];
  strip.forEach((c, i) => {
    const sx = 0.35 + i * 4.65;
    s.addShape('rect', { x: sx, y: 2.65, w: 4.3, h: 0.72, fill: { color: '0A1628' }, line: { color: C.blue, size: 0.75, type: 'solid' }, rectRadius: 0.06 });
    s.addText(c.ch, { x: sx+0.12, y: 2.72, w: 2, h: 0.25, fontSize: 9.5, bold: true, color: C.blue, fontFace: 'Calibri', margin: 0 });
    s.addText(`P: ${c.primary}  O: ${c.offtake}  ${c.flow}`, { x: sx+0.12, y: 2.97, w: 4, h: 0.22, fontSize: 8.5, color: C.white, fontFace: 'Calibri', margin: 0 });
    s.addText(c.note, { x: sx+0.12, y: 3.17, w: 4, h: 0.18, fontSize: 7, color: C.muted, fontFace: 'Calibri', margin: 0 });
  });

  // Benchmark note
  s.addText('Benchmark conversion: 85.7% (West + South-1 average)  ·  Recoverable gap above ₹0.25 Cr floor: ₹6.22 Cr', {
    x: 0.35, y: 3.5, w: 9.3, h: 0.3,
    fontSize: 8.5, color: C.muted, fontFace: 'Calibri', align: 'left', margin: 0,
  });

  s.addText('ASP: ₹179.21  ·  Volume: 18.95 L units  ·  Realisation: 42.2%', {
    x: 0.35, y: 3.88, w: 9.3, h: 0.3,
    fontSize: 9, color: C.white, bold: false, fontFace: 'Calibri', align: 'left', margin: 0,
  });

  s.addNotes('July MT channel overview. MT primary at ₹47.02 Cr, offtake at ₹33.96 Cr — a 72.2% conversion, 13.5 percentage points below the West+South-1 benchmark of 85.7%. The ₹13.06 Cr gap is partly structural and partly recoverable: ₹6.22 Cr sits above the ₹0.25 Cr floor and is actionable. eB2B (Nykaa/FSN) at 93.9% flow is the best-converting channel. SIS is small and net-of-returns. Neither eB2B nor SIS is included in zone figures per the channel master.');
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 4 · Zone Conversion Analysis
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addSlideHeader(s, 'Zone Conversion Analysis  ·  July \'26', true);

  // Bar chart
  const chartData = [{
    name: 'Conversion %',
    labels: zoneRows.map(r => r.zone),
    values: zoneRows.map(r => r.conv),
  }];
  s.addChart(pres.ChartType.bar, chartData, {
    x: 0.35, y: 0.9, w: 4.6, h: 3.5,
    barDir: 'bar',
    barGrouping: 'clustered',
    chartColors: zoneRows.map(r => convColor(r.conv)),
    showValue: true,
    dataLabelPosition: 'outEnd',
    dataLabelFontSize: 9,
    dataLabelColor: C.ink,
    dataLabelFontBold: true,
    catAxisLabelFontSize: 10,
    valAxisMaxVal: 100,
    valAxisMinVal: 0,
    showLegend: false,
    showTitle: true,
    title: 'Conv. % by Zone',
    titleFontSize: 11,
    titleColor: C.ink,
    valGridLine: { color: 'D8DDE8', size: 0.5 },
    catGridLine: { style: 'none' },
    valAxisLabelColor: C.muted,
    catAxisLabelColor: C.ink,
  });

  // Reference line label (manual — chart doesn't support ref lines)
  s.addText('⬅ Benchmark 85.7%', {
    x: 0.38, y: 1.42, w: 1.9, h: 0.22,
    fontSize: 7.5, color: C.pos, bold: true, fontFace: 'Calibri', margin: 0,
  });

  // Table
  const tblW = [1.4, 0.88, 0.88, 0.88, 0.88];
  const tblX = 5.2;
  const tblY = 0.88;
  const headers = ['Zone', 'Primary', 'Offtake', 'Conv %', 'Gap'];
  // header row
  headers.forEach((h, i) => {
    const cx = tblX + tblW.slice(0, i).reduce((a, b) => a+b, 0);
    s.addShape('rect', { x: cx, y: tblY, w: tblW[i], h: 0.35, fill: { color: C.navy }, line: { type: 'none' } });
    s.addText(h, { x: cx+0.04, y: tblY+0.06, w: tblW[i]-0.08, h: 0.23, fontSize: 8.5, bold: true, color: C.white, fontFace: 'Calibri', align: 'center', margin: 0 });
  });
  zoneRows.forEach((r, ri) => {
    const ry = tblY + 0.35 + ri * 0.46;
    const rowBg = ri % 2 === 0 ? C.white : 'EFF2F8';
    const cells = [r.zone, `₹${r.primary.toFixed(2)}`, `₹${r.offtake.toFixed(2)}`, `${r.conv}%`, `₹${r.gap.toFixed(2)}`];
    cells.forEach((cell, ci) => {
      const cx = tblX + tblW.slice(0, ci).reduce((a, b) => a+b, 0);
      s.addShape('rect', { x: cx, y: ry, w: tblW[ci], h: 0.44, fill: { color: rowBg }, line: { color: 'D0D8E8', size: 0.5 } });
      const isBold = ci === 3;
      const textColor = ci === 3 ? convColor(r.conv) : C.ink;
      s.addText(cell, { x: cx+0.04, y: ry+0.1, w: tblW[ci]-0.08, h: 0.26, fontSize: 9, bold: isBold, color: textColor, fontFace: ci === 0 ? 'Cambria' : 'Calibri', align: ci === 0 ? 'left' : 'center', margin: 0 });
    });
  });

  // Insight callouts
  s.addText('South-1 & West above benchmark · North & East critical', {
    x: 0.35, y: 4.55, w: 9.3, h: 0.28,
    fontSize: 9, color: C.ink, bold: true, fontFace: 'Calibri', align: 'left', margin: 0,
  });

  s.addNotes('Zone conversion analysis for July. South-1 (86.3%) and West (85.2%) are the only zones at or above the 85.7% benchmark — these are the model zones. Central (80.9%) and South-2 (72.4%) are in the middle. North (61.3%) and East (49.9%) are critical — East is below 50% conversion, meaning more than half its primary has not moved to shelf offtake. North has the largest absolute gap at ₹4.41 Cr.');
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 5 · Account Gap + Benchmark
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addSlideHeader(s, 'Account Gap Analysis  ·  July \'26', true);

  // Top 3 gap accounts
  const gapAccts = [
    { name: 'Reliance', gap: 7.61, conv: 51.5, note: 'Largest contributor · 58% of total gap' },
    { name: 'DMart',    gap: 4.29, conv: 76.5, note: 'Stocking lag likely — moderate risk' },
    { name: 'Metro',    gap: 1.36, conv: 73.6, note: 'Manageable; monitor replenishment' },
  ];
  gapAccts.forEach((a, i) => {
    const gx = 0.35 + i * 3.12;
    const fill = i === 0 ? 'FFF0F0' : (i === 1 ? 'FFF8E8' : C.white);
    const border = { color: i === 0 ? C.neg : (i === 1 ? C.amber : 'D0D8E8'), size: 1.5, type: 'solid' };
    s.addShape('rect', { x: gx, y: 0.92, w: 2.85, h: 1.65, fill: { color: fill }, line: border, rectRadius: 0.08 });
    s.addText(`#${i+1}  ${a.name}`, { x: gx+0.1, y: 0.97, w: 2.65, h: 0.32, fontSize: 11, bold: true, color: C.ink, fontFace: 'Cambria', align: 'left', margin: 0 });
    s.addText(`Gap: ₹${a.gap.toFixed(2)} Cr`, { x: gx+0.1, y: 1.3, w: 1.5, h: 0.35, fontSize: 14, bold: true, color: C.neg, fontFace: 'Cambria', align: 'left', margin: 0 });
    s.addText(`Conv: ${a.conv}%`, { x: gx+1.65, y: 1.3, w: 1.1, h: 0.35, fontSize: 12, bold: true, color: convColor(a.conv), fontFace: 'Cambria', align: 'right', margin: 0 });
    s.addText(a.note, { x: gx+0.1, y: 1.7, w: 2.65, h: 0.35, fontSize: 7.5, color: C.muted, fontFace: 'Calibri', align: 'left', margin: 0 });
  });

  // Star account
  s.addShape('rect', { x: 0.35, y: 2.72, w: 2.85, h: 0.85, fill: { color: 'E8F5EE' }, line: { color: C.pos, size: 1.5 }, rectRadius: 0.08 });
  s.addText('⭐ Apollo — Star Account', { x: 0.45, y: 2.77, w: 2.65, h: 0.3, fontSize: 10, bold: true, color: C.pos, fontFace: 'Cambria', margin: 0 });
  s.addText('P: ₹7.20 Cr  O: ₹7.18 Cr  Conv: 99.7%', { x: 0.45, y: 3.08, w: 2.65, h: 0.26, fontSize: 9, color: C.ink, fontFace: 'Calibri', margin: 0 });

  // Lulu anomaly
  s.addShape('rect', { x: 3.45, y: 2.72, w: 2.85, h: 0.85, fill: { color: 'EEF4FF' }, line: { color: C.blue, size: 1.5 }, rectRadius: 0.08 });
  s.addText('⚑ Lulu — Consignment Pattern', { x: 3.55, y: 2.77, w: 2.65, h: 0.3, fontSize: 10, bold: true, color: C.blue, fontFace: 'Cambria', margin: 0 });
  s.addText('P: ₹0  O: ₹1.70 Cr  Billing lag / stock draw', { x: 3.55, y: 3.08, w: 2.65, h: 0.26, fontSize: 9, color: C.ink, fontFace: 'Calibri', margin: 0 });

  // Benchmark + recoverable
  s.addShape('rect', { x: 6.5, y: 0.92, w: 3.1, h: 2.65, fill: { color: C.navy }, line: { type: 'none' }, rectRadius: 0.08 });
  s.addText('Benchmark', { x: 6.65, y: 1.02, w: 2.8, h: 0.32, fontSize: 11, bold: true, color: C.gold, fontFace: 'Cambria', align: 'center', margin: 0 });
  s.addText('85.73%', { x: 6.65, y: 1.36, w: 2.8, h: 0.5, fontSize: 28, bold: true, color: C.white, fontFace: 'Cambria', align: 'center', margin: 0 });
  s.addText('West + South-1 average', { x: 6.65, y: 1.88, w: 2.8, h: 0.22, fontSize: 8, color: '8EAACF', fontFace: 'Calibri', align: 'center', margin: 0 });
  s.addShape('rect', { x: 6.75, y: 2.18, w: 2.6, h: 0.05, fill: { color: '2A4068' }, line: { type: 'none' } });
  s.addText('Recoverable Gap', { x: 6.65, y: 2.3, w: 2.8, h: 0.25, fontSize: 9, color: C.gold, fontFace: 'Calibri', align: 'center', bold: true, margin: 0 });
  s.addText('₹6.22 Cr', { x: 6.65, y: 2.57, w: 2.8, h: 0.4, fontSize: 22, bold: true, color: C.pos, fontFace: 'Cambria', align: 'center', margin: 0 });
  s.addText('above ₹0.25 Cr floor', { x: 6.65, y: 2.98, w: 2.8, h: 0.22, fontSize: 8, color: '8EAACF', fontFace: 'Calibri', align: 'center', margin: 0 });

  // Action note
  s.addText('Priority: Accelerate Reliance conversion — closing to 75% recovers ~₹3.7 Cr in July equivalent.', {
    x: 0.35, y: 3.72, w: 9.3, h: 0.28,
    fontSize: 9, color: C.ink, bold: true, fontFace: 'Calibri', margin: 0,
  });

  s.addNotes('Account gap analysis. Reliance is the critical account: ₹7.61 Cr gap at 51.5% conversion — 58% of the total MT gap is in one account. Closing Reliance to benchmark would recover roughly ₹5 Cr alone. DMart at ₹4.29 Cr gap is likely a stocking lag. Apollo is the model account at 99.7% conversion — whatever process drives Apollo should be replicated. Lulu shows a consignment/billing lag pattern: zero primary but ₹1.70 Cr offtake, meaning shelf draw without fresh billing. The recoverable gap above the ₹0.25 Cr floor is ₹6.22 Cr — this is the addressable number for the next 30 days.');
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 6 · Market Share — Nielsen RMS
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addSlideHeader(s, 'Market Share  ·  Nielsen RMS', true);

  // Tier 3 badge for July MS
  tier3Badge(s, 7.8, 0.88);
  s.addText('Jul MS pending Nielsen cut', { x: 7.8, y: 1.2, w: 1.8, h: 0.2, fontSize: 7.5, color: C.muted, fontFace: 'Calibri', margin: 0, align: 'center' });

  // Face Wash chart
  const fwData = [{
    name: 'Market Share %',
    labels: ['Himalaya', 'Garnier', "Pond's", 'Mamaearth'],
    values: [22.6, 14.2, 13.8, 10.5],
  }];
  s.addChart(pres.ChartType.bar, fwData, {
    x: 0.35, y: 0.88, w: 3.6, h: 2.9,
    barDir: 'bar',
    barGrouping: 'clustered',
    chartColors: ['6B7280', '6B7280', '6B7280', C.gold],
    showValue: true,
    dataLabelPosition: 'outEnd',
    dataLabelFontSize: 9,
    dataLabelColor: C.ink,
    dataLabelFontBold: true,
    valAxisMaxVal: 30,
    valAxisMinVal: 0,
    showLegend: false,
    showTitle: true,
    title: 'Face Wash — MT MS %',
    titleFontSize: 11,
    titleColor: C.ink,
    valGridLine: { color: 'D8DDE8', size: 0.5 },
    catGridLine: { style: 'none' },
    valAxisLabelColor: C.muted,
    catAxisLabelColor: C.ink,
    catAxisLabelFontSize: 10,
  });

  // Shampoo chart
  const shData = [{
    name: 'Market Share %',
    labels: ['Dove', 'H&S', 'Mamaearth'],
    values: [16.6, 13.0, 3.7],
  }];
  s.addChart(pres.ChartType.bar, shData, {
    x: 4.0, y: 0.88, w: 3.6, h: 2.9,
    barDir: 'bar',
    barGrouping: 'clustered',
    chartColors: ['6B7280', '6B7280', C.gold],
    showValue: true,
    dataLabelPosition: 'outEnd',
    dataLabelFontSize: 9,
    dataLabelColor: C.ink,
    dataLabelFontBold: true,
    valAxisMaxVal: 25,
    valAxisMinVal: 0,
    showLegend: false,
    showTitle: true,
    title: 'Shampoo — MT MS %',
    titleFontSize: 11,
    titleColor: C.ink,
    valGridLine: { color: 'D8DDE8', size: 0.5 },
    catGridLine: { style: 'none' },
    valAxisLabelColor: C.muted,
    catAxisLabelColor: C.ink,
    catAxisLabelFontSize: 10,
  });

  // Notes
  s.addText('Face Wash: Mamaearth #4 at 10.5% | Shampoo: Mamaearth at 3.7% vs Dove 16.6% — significant gap in haircare', {
    x: 0.35, y: 3.9, w: 9.3, h: 0.28,
    fontSize: 9, color: C.ink, bold: true, fontFace: 'Calibri', margin: 0,
  });
  s.addText('MS data: latest available Nielsen RMS cut (Jun or earlier). Jul cut pending — Tier 3 badge applied.', {
    x: 0.35, y: 4.22, w: 9.3, h: 0.22,
    fontSize: 7.5, color: C.muted, fontFace: 'Calibri', margin: 0,
  });

  s.addNotes('Market share from Nielsen RMS. In Face Wash (MT), Mamaearth is ranked #4 at 10.5% behind Himalaya (22.6%), Garnier (14.2%), and Ponds (13.8%). In Shampoo, Mamaearth is at 3.7% against Dove at 16.6% and H&S at 13.0% — a much larger gap to close. July Nielsen cut is pending; Tier 3 badge applied. Opportunity area: shampoo MS is an order of magnitude behind face wash; the gap to Dove alone is 4x our current share.');
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 7 · Brand P vs O
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addSlideHeader(s, 'Brand Primary vs Offtake  ·  July \'26', true);

  const bLabels = brandRows.map(r => r.brand);
  const bChartData = [
    { name: 'Primary ₹Cr', labels: bLabels, values: brandRows.map(r => r.primary) },
    { name: 'Offtake ₹Cr', labels: bLabels, values: brandRows.map(r => r.offtake) },
  ];
  s.addChart(pres.ChartType.bar, bChartData, {
    x: 0.35, y: 0.88, w: 6.0, h: 3.7,
    barDir: 'col',
    barGrouping: 'clustered',
    chartColors: [C.navy, C.gold],
    showValue: true,
    dataLabelPosition: 'outEnd',
    dataLabelFontSize: 8,
    dataLabelColor: C.ink,
    showLegend: true,
    legendPos: 't',
    legendFontSize: 9,
    legendColor: C.ink,
    showTitle: false,
    valGridLine: { color: 'D8DDE8', size: 0.5 },
    catGridLine: { style: 'none' },
    valAxisLabelColor: C.muted,
    catAxisLabelColor: C.ink,
    catAxisLabelFontSize: 9,
  });

  // brand conversion table
  const btx = 6.55, bty = 0.88;
  const btw = [1.6, 0.9, 0.9];
  const bHdrs = ['Brand', 'Conv %', 'Gap ₹Cr'];
  bHdrs.forEach((h, i) => {
    const cx = btx + btw.slice(0, i).reduce((a, b) => a+b, 0);
    s.addShape('rect', { x: cx, y: bty, w: btw[i], h: 0.35, fill: { color: C.navy }, line: { type: 'none' } });
    s.addText(h, { x: cx+0.04, y: bty+0.06, w: btw[i]-0.08, h: 0.23, fontSize: 8, bold: true, color: C.white, fontFace: 'Calibri', align: 'center', margin: 0 });
  });
  brandRows.forEach((r, ri) => {
    const ry = bty + 0.35 + ri * 0.45;
    const rowBg = ri % 2 === 0 ? C.white : 'EFF2F8';
    const conv = r.primary > 0 ? (r.offtake / r.primary * 100) : null;
    const gap = r.primary - r.offtake;
    const cells = [r.brand, conv !== null ? `${conv.toFixed(1)}%` : 'N/A', gap >= 0 ? `₹${gap.toFixed(2)}` : `+₹${Math.abs(gap).toFixed(2)}`];
    cells.forEach((cell, ci) => {
      const cx = btx + btw.slice(0, ci).reduce((a, b) => a+b, 0);
      s.addShape('rect', { x: cx, y: ry, w: btw[ci], h: 0.43, fill: { color: rowBg }, line: { color: 'D0D8E8', size: 0.5 } });
      const textColor = ci === 1 && conv !== null ? convColor(conv) : C.ink;
      s.addText(cell, { x: cx+0.04, y: ry+0.1, w: btw[ci]-0.08, h: 0.26, fontSize: 9, bold: ci === 1, color: textColor, fontFace: ci === 0 ? 'Cambria' : 'Calibri', align: ci === 0 ? 'left' : 'center', margin: 0 });
    });
  });

  s.addText('Mamaearth leads at ₹33.4 Cr primary. Derma Co. at 72.6% conversion — gap ₹4.16 Cr. Aqualogica offtake > primary.', {
    x: 0.35, y: 4.65, w: 9.3, h: 0.28,
    fontSize: 9, color: C.ink, bold: true, fontFace: 'Calibri', margin: 0,
  });

  s.addNotes('Brand P vs O for July. Mamaearth is the volume leader at ₹33.4 Cr primary / ₹24.5 Cr offtake, 73.4% conversion. The Derma Co. at ₹15.2 Cr primary / ₹11.0 Cr offtake, 72.6% conversion — ₹4.16 Cr gap. Aqualogica shows offtake slightly above primary (₹0.48 vs ₹0.41) — a stock draw pattern. BBlunt and Dr. Sheth\'s are very small volumes. Combined primary ₹49.17 Cr, offtake ₹36.09 Cr — note this includes eB2B/SIS which are in the account data but branded P vs O aggregates all channel billing.');
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 8 · Account P vs O
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addSlideHeader(s, 'Account Primary vs Offtake  ·  July \'26', true);

  const aLabels = accountRows.map(r => r.acct);
  const aChartData = [
    { name: 'Primary ₹Cr', labels: aLabels, values: accountRows.map(r => r.primary) },
    { name: 'Offtake ₹Cr', labels: aLabels, values: accountRows.map(r => r.offtake) },
  ];
  s.addChart(pres.ChartType.bar, aChartData, {
    x: 0.35, y: 0.88, w: 6.0, h: 3.7,
    barDir: 'col',
    barGrouping: 'clustered',
    chartColors: [C.navy, C.gold],
    showValue: true,
    dataLabelPosition: 'outEnd',
    dataLabelFontSize: 8,
    dataLabelColor: C.ink,
    showLegend: true,
    legendPos: 't',
    legendFontSize: 9,
    legendColor: C.ink,
    showTitle: false,
    valGridLine: { color: 'D8DDE8', size: 0.5 },
    catGridLine: { style: 'none' },
    valAxisLabelColor: C.muted,
    catAxisLabelColor: C.ink,
    catAxisLabelFontSize: 9,
  });

  // annotation callouts
  const callouts = [
    { x: 6.55, y: 0.92, w: 3.1, h: 0.72, bg: 'E8F5EE', border: C.pos, label: '⭐ Apollo · 99.7% conv', body: 'P ₹7.20 Cr / O ₹7.18 Cr — gold standard' },
    { x: 6.55, y: 1.72, w: 3.1, h: 0.72, bg: 'FFF0F0', border: C.neg, label: '⚠ Reliance · 51.5% conv', body: 'P ₹15.66 Cr / O ₹8.06 Cr — ₹7.6 Cr gap' },
    { x: 6.55, y: 2.52, w: 3.1, h: 0.72, bg: 'EEF4FF', border: C.blue, label: '⚑ Lulu · Billing lag', body: 'P ₹0 / O ₹1.70 Cr — consignment draw' },
    { x: 6.55, y: 3.32, w: 3.1, h: 0.72, bg: 'FFF8E8', border: C.amber, label: 'DMart · 76.5% conv', body: 'P ₹18.25 Cr / O ₹13.97 Cr — stocking lag' },
  ];
  callouts.forEach(c => {
    s.addShape('rect', { x: c.x, y: c.y, w: c.w, h: c.h, fill: { color: c.bg }, line: { color: c.border, size: 1.5 }, rectRadius: 0.06 });
    s.addText(c.label, { x: c.x+0.1, y: c.y+0.07, w: c.w-0.2, h: 0.26, fontSize: 9.5, bold: true, color: C.ink, fontFace: 'Cambria', margin: 0 });
    s.addText(c.body,  { x: c.x+0.1, y: c.y+0.36, w: c.w-0.2, h: 0.26, fontSize: 8.5, color: C.muted, fontFace: 'Calibri', margin: 0 });
  });

  s.addNotes('Account P vs O for July. DMart is the largest primary account at ₹18.25 Cr but offtake at ₹13.97 Cr (76.5%) — stocking lag is likely. Reliance at 51.5% is critical: half the primary stock has not converted to shelf sales. Apollo is the gold standard at 99.7%. FSN/Nykaa at 99.5% — eB2B channel, included here for visibility. Lulu is a structural anomaly: zero primary billing but ₹1.70 Cr offtake, meaning stores are drawing from existing consignment stock. Wellness Forward and H&G both have offtake exceeding primary — consignment or inventory draw patterns.');
}

// ══════════════════════════════════════════════════════════════════════════════
// Slide 9 · Category Offtake Trends
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  addSlideHeader(s, 'Category Offtake Trends  ·  Feb – Jul \'26', true);

  // Mamaearth trends
  const mhSeries = Object.entries(mhTrend).map(([name, values]) => ({
    name, labels: trendMonths, values,
  }));
  s.addChart(pres.ChartType.line, mhSeries, {
    x: 0.35, y: 0.88, w: 4.55, h: 3.0,
    chartColors: [C.gold, C.navy, C.blue],
    lineSize: 2.5,
    showMarker: true,
    markerSize: 5,
    showValue: false,
    showLegend: true,
    legendPos: 'b',
    legendFontSize: 8,
    legendColor: C.ink,
    showTitle: true,
    title: 'Mamaearth Category Offtake ₹Cr',
    titleFontSize: 10,
    titleColor: C.ink,
    valGridLine: { color: 'D8DDE8', size: 0.5 },
    catGridLine: { style: 'none' },
    valAxisLabelColor: C.muted,
    catAxisLabelColor: C.ink,
    catAxisLabelFontSize: 9,
  });

  // Derma Co. trends
  const dcSeries = Object.entries(dcTrend).map(([name, values]) => ({
    name, labels: trendMonths, values,
  }));
  s.addChart(pres.ChartType.line, dcSeries, {
    x: 5.1, y: 0.88, w: 4.55, h: 3.0,
    chartColors: [C.neg, C.amber, C.blue],
    lineSize: 2.5,
    showMarker: true,
    markerSize: 5,
    showValue: false,
    showLegend: true,
    legendPos: 'b',
    legendFontSize: 8,
    legendColor: C.ink,
    showTitle: true,
    title: 'The Derma Co. Category Offtake ₹Cr',
    titleFontSize: 10,
    titleColor: C.ink,
    valGridLine: { color: 'D8DDE8', size: 0.5 },
    catGridLine: { style: 'none' },
    valAxisLabelColor: C.muted,
    catAxisLabelColor: C.ink,
    catAxisLabelFontSize: 9,
  });

  // Derma Co. spike callout
  s.addShape('rect', { x: 5.1, y: 3.98, w: 4.55, h: 0.48, fill: { color: 'FFF0F0' }, line: { color: C.neg, size: 1 }, rectRadius: 0.06 });
  s.addText('⚡ Derma Co. Face Cleanser: Jul ₹7.13 Cr vs Jun ₹4.83 Cr  (+47.5% MoM) — investigate spike driver', {
    x: 5.18, y: 4.06, w: 4.38, h: 0.32, fontSize: 8.5, bold: true, color: C.neg, fontFace: 'Calibri', margin: 0,
  });

  // MH shampoo callout
  s.addShape('rect', { x: 0.35, y: 3.98, w: 4.55, h: 0.48, fill: { color: 'E8F5EE' }, line: { color: C.pos, size: 1 }, rectRadius: 0.06 });
  s.addText('MH Shampoo growing steadily: ₹4.81 Cr (Feb) → ₹6.95 Cr (Jul)  +44.5% in 6 months', {
    x: 0.43, y: 4.06, w: 4.38, h: 0.32, fontSize: 8.5, bold: true, color: C.pos, fontFace: 'Calibri', margin: 0,
  });

  // eB2B context
  s.addText('eB2B (Nykaa): Apr spike ₹2.29 Cr → stable ₹2.07 Cr Jul  ·  Active EANs: Jan 222 → Jul 198 (pruning)', {
    x: 0.35, y: 4.56, w: 9.3, h: 0.28,
    fontSize: 8, color: C.muted, fontFace: 'Calibri', margin: 0,
  });

  s.addNotes('Category offtake trend analysis Feb–July. Mamaearth: Face Cleanser peaked in May/Jun at ₹9.65 Cr and dipped to ₹8.53 Cr in July — likely a seasonal normalisation after summer peak. Shampoo is the growth story: ₹4.81 to ₹6.95 Cr, up 44.5% in 6 months, showing sustained momentum. Sun Care is in seasonal retreat as expected post-summer. For The Derma Co., the Face Cleanser spike to ₹7.13 Cr in July from ₹4.83 Cr is striking — +47.5% in one month. This warrants investigation: could be a key account listing, a promotional fill, or a channel event. eB2B through Nykaa spiked in April (₹2.29 Cr) then stabilised; active EAN count declining from 222 to 198 suggests portfolio pruning.');
}

// ── Write output ──────────────────────────────────────────────────────────────
pres.writeFile({ fileName: '/home/user/mt-dashboard/MT_July26_Performance_Review.pptx' })
  .then(() => console.log('DONE: MT_July26_Performance_Review.pptx'))
  .catch(e => { console.error('ERROR:', e.message); process.exit(1); });
