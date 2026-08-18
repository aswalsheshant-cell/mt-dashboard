/* Honasa Modern Trade — July 2026 Offtake-Only Command Centre
 * Offtake-data-only view: NSV, units, ASP, realisation, brand, chain, category.
 * No primary / conversion / gap figures.
 * Incorporates pattern-matcher-router skill logic:
 *   8-gate validation · 5-phase insight cycle · price-volume decomp
 *   zone ASP spread · realisation analysis · ND/WD/SPD provenance
 */
const PptxGenJS = require('pptxgenjs');

/* ---------------------------------------------------------------- tokens */
const INK   = '183B39';
const TEAL  = '116F68';
const BRIGHT= '28A596';
const RED   = 'D6544D';
const GREEN = '2B9A66';
const AMBER = 'F2B84B';
const BLUE  = '2E7DA8';
const GREY  = '5F716E';
const LINE  = 'C8DCD7';
const TINT  = 'DFF2ED';
const PAGE  = 'F7FBFA';
const W     = 'FFFFFF';
const FONT  = 'Calibri';
const FONTH = 'Calibri Light';

/* --------------------------------------------------------------- geometry */
const PW = 7.5, PH = 13.333;
const M  = 0.29;
const CW = PW - 2 * M;
const HDR_H  = 1.24;
const BODY_Y = 1.38;
const FOOT_Y = 12.44;
const SRC_Y  = 13.00;

const SRC = "Source: Offtake Store×Article Jul-26 CSV (220,522 rows, 0 bad, excl. Brand Counter & discontinued brands) · 8-Gate Validation: PASS_WITH_FLAG · FY27 · EXACT";

const pres = new PptxGenJS();
pres.defineLayout({ name: 'MTPORT', width: PW, height: PH });
pres.layout = 'MTPORT';
pres.author = 'Modern Trade Analytics';
pres.title  = 'July 2026 MT Offtake Command Centre';

/* ================================================================ helpers */
const txt = o => Object.assign({ fontFace: FONT, color: INK, margin: 0, valign: 'top' }, o);

function titleSize(s) {
  if (s.length <= 38) return 18.5;
  if (s.length <= 56) return 16.5;
  if (s.length <= 76) return 14.5;
  return 13;
}

function page(n, title, subtitle) {
  const s = pres.addSlide();
  s.background = { color: PAGE };
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: PW, h: HDR_H, fill: { color: TEAL } });
  s.addText(title, txt({ x: M + 0.11, y: 0.20, w: CW - 0.75, h: 0.60, color: W,
    fontFace: FONTH, fontSize: titleSize(title), bold: true, valign: 'middle', lineSpacingMultiple: 0.92 }));
  s.addText(subtitle, txt({ x: M + 0.13, y: 0.86, w: CW - 0.75, h: 0.26,
    color: 'BFDCD7', fontSize: 8.5, valign: 'middle' }));
  s.addText(String(n).padStart(2, '0'), txt({ x: PW - M - 0.52, y: 0.26, w: 0.44, h: 0.24,
    color: W, fontSize: 8, bold: true, align: 'right' }));
  s.addText("Jul'26  ·  FY27  ·  Offtake Only", txt({ x: PW - M - 1.28, y: 0.52, w: 1.20, h: 0.17,
    color: 'BFDCD7', fontSize: 5.2, align: 'right', italic: true }));

  // EIAO rail
  s.addShape(pres.ShapeType.roundRect, { x: M, y: FOOT_Y, w: CW, h: 0.46, rectRadius: 0.03,
    fill: { color: TINT }, line: { color: LINE, width: 0.75 } });
  [['EVIDENCE','What moved'],['IMPLICATION','Why it matters'],['ACTION','What changes now'],['OWNER','Who closes it']
  ].forEach(([a, b], i) => {
    const cw = (CW - 0.24) / 4, cx = M + 0.12 + i * cw;
    s.addText(a, txt({ x: cx, y: FOOT_Y + 0.06, w: cw - 0.08, h: 0.16, color: TEAL, fontSize: 6.5, bold: true, charSpacing: 0.6 }));
    s.addText(b, txt({ x: cx, y: FOOT_Y + 0.23, w: cw - 0.08, h: 0.18, color: GREY, fontSize: 7 }));
    if (i) s.addShape(pres.ShapeType.line, { x: cx - 0.09, y: FOOT_Y + 0.09, w: 0, h: 0.29, line: { color: LINE, width: 0.75 } });
  });
  s.addText(SRC, txt({ x: M + 0.04, y: SRC_Y, w: CW - 0.08, h: 0.22, color: GREY, fontSize: 6.5, align: 'center' }));
  return s;
}

function card(s, { x, y, w, h, label, accent = TEAL }) {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.02,
    fill: { color: W }, line: { color: LINE, width: 0.75 } });
  if (label) {
    s.addShape(pres.ShapeType.rect, { x, y, w, h: 0.30, fill: { color: accent } });
    s.addText(label, txt({ x: x + 0.09, y: y + 0.02, w: w - 0.18, h: 0.26, color: W,
      fontSize: 7, bold: true, charSpacing: 0.5, align: 'center', valign: 'middle' }));
    return y + 0.40;
  }
  return y + 0.12;
}

function kpi(s, { x, y, w, h, label, value, sub, accent = TEAL, valueColor }) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: W }, line: { color: LINE, width: 0.75 } });
  s.addShape(pres.ShapeType.rect, { x, y, w: 0.07, h, fill: { color: accent } });
  const ix = x + 0.17, iw = w - 0.26;
  s.addText(label, txt({ x: ix, y: y + 0.10, w: iw, h: 0.19, color: GREY, fontSize: 6.8, bold: true, charSpacing: 0.5 }));
  const fs = value.length >= 10 ? 13.5 : value.length >= 8 ? 15.5 : 17.5;
  s.addText(value, txt({ x: ix, y: y + 0.30, w: iw, h: 0.34, color: valueColor || accent,
    fontSize: fs, bold: true, fontFace: FONTH, valign: 'middle' }));
  s.addText(sub, txt({ x: ix, y: y + 0.66, w: iw, h: 0.19, color: GREY, fontSize: 6.8 }));
}

function bullets(s, { x, y, w, items, gap = 0.34, size = 7.4, dot = BRIGHT }) {
  items.forEach((it, i) => {
    const o = typeof it === 'string' ? { t: it } : it;
    const yy = y + i * gap;
    s.addShape(pres.ShapeType.ellipse, { x, y: yy + 0.055, w: 0.055, h: 0.055, fill: { color: o.c || dot } });
    s.addText(o.t, txt({ x: x + 0.13, y: yy, w: w - 0.13, h: gap - 0.02,
      fontSize: size, bold: !!o.b, color: o.color || INK, lineSpacingMultiple: 0.92 }));
  });
}

function table(s, { x, y, w, cols, rows, rowH = 0.30, headH = 0.28, size = 7.2 }) {
  const tot = cols.reduce((a, c) => a + c.w, 0);
  const colX = []; let acc = x;
  cols.forEach(c => { colX.push(acc); acc += (c.w / tot) * w; });
  const colW = cols.map((c, i) => (c.w / tot) * w);
  s.addShape(pres.ShapeType.rect, { x, y, w, h: headH, fill: { color: TEAL } });
  cols.forEach((c, i) => {
    s.addText(c.t, txt({ x: colX[i] + 0.06, y: y + 0.02, w: colW[i] - 0.12, h: headH - 0.04,
      color: W, fontSize: 6.6, bold: true, charSpacing: 0.4, align: c.a || 'left', valign: 'middle' }));
  });
  rows.forEach((r, ri) => {
    const ry = y + headH + ri * rowH;
    if (ri % 2 === 0) s.addShape(pres.ShapeType.rect, { x, y: ry, w, h: rowH, fill: { color: 'F4F9F8' } });
    s.addShape(pres.ShapeType.line, { x, y: ry + rowH, w, h: 0, line: { color: LINE, width: 0.5 } });
    r.forEach((cell, ci) => {
      const o = typeof cell === 'object' ? cell : { t: cell };
      s.addText(String(o.t), txt({ x: colX[ci] + 0.06, y: ry, w: colW[ci] - 0.12, h: rowH,
        fontSize: size, bold: !!o.b, color: o.c || INK, align: cols[ci].a || 'left', valign: 'middle' }));
    });
  });
}

function banner(s, y, text, accent = TEAL) {
  s.addShape(pres.ShapeType.rect, { x: M, y, w: CW, h: 0.26, fill: { color: accent } });
  s.addText(text, txt({ x: M + 0.14, y: y + 0.02, w: CW - 0.28, h: 0.22,
    color: W, fontSize: 7.2, bold: true, charSpacing: 0.5, valign: 'middle' }));
  return y + 0.34;
}

function chartTitle(s, x, y, w, text) {
  s.addText(text, txt({ x, y, w, h: 0.22, color: TEAL, fontSize: 7.2, bold: true, charSpacing: 0.3 }));
}

const axisBase = {
  catAxisLabelFontSize: 7, valAxisLabelFontSize: 7,
  catAxisLineShow: false, valGridLine: { style: 'solid', color: LINE, pt: 0.5 },
  showLegend: false, dataLabelFontSize: 7, showTitle: false,
  chartColors: [BRIGHT, RED, AMBER, BLUE, GREEN, TEAL],
};

/* ================================================================== DATA */
// All figures EXACT from Jul-26 offtake CSV (validated, 8-gate PASS_WITH_FLAG)

const NAT = {
  nsv: 36.06, units: 2051674, mrp: 84.16, asp: 175.76, real: 42.8,
  active_eans_jul: 198    // from existing series context
};

// Geographic zones only (excl. Pan India / eB2B)
const GEO_ZONES = [
  { z: 'West',    nsv: 8.27, units: 497610, asp: 166.22, real: 41.9, share: 22.96 },
  { z: 'South-1', nsv: 8.18, units: 433958, asp: 188.56, real: 42.7, share: 22.71 },
  { z: 'North',   nsv: 6.97, units: 377348, asp: 184.82, real: 41.8, share: 19.36 },
  { z: 'South-2', nsv: 4.87, units: 278020, asp: 175.30, real: 43.0, share: 13.53 },
  { z: 'East',    nsv: 3.54, units: 183288, asp: 193.17, real: 42.1, share:  9.83 },
  { z: 'Central', nsv: 2.12, units: 124802, asp: 169.69, real: 41.1, share:  5.88 },
];
const GEO_TOTAL = { nsv: 33.95, units: 1894026 };

// Sub-channels
const EBIZ  = { name: 'eB2B (Nykaa/FSN)', nsv: 2.07, units: 155142, asp: 133.19, real: 57.4 };
const SIS   = { name: 'SIS (Azorte / SS / Lifestyle)', nsv: 0.03, units: 1506, asp: 225.85, real: 49.5 };

// Brands (geo MT)
const BRANDS = [
  { b: 'Mamaearth',    nsv: 24.45, units: 1441194, share: 67.9, asp: 169.6 },
  { b: 'The Derma Co.',nsv: 11.01, units: 584842,  share: 30.6, asp: 188.3 },
  { b: 'Aqualogica',   nsv:  0.48, units:  20637,  share:  1.3, asp: 234.5 },
];

// Top chains
const CHAINS = [
  { c: 'Dmart',            nsv: 13.97, units: 883839, share: 38.77, asp: 158.12 },
  { c: 'Reliance',         nsv:  8.06, units: 398706, share: 22.36, asp: 202.25 },
  { c: 'Apollo',           nsv:  7.18, units: 412364, share: 19.93, asp: 174.21 },
  { c: 'Lulu',             nsv:  1.70, units:  56023, share:  4.71, asp: 303.82 },
  { c: 'Wellness Forever', nsv:  0.72, units:  32036, share:  2.00, asp: 225.05 },
  { c: 'H&G',              nsv:  0.51, units:  17982, share:  1.41, asp: 281.11 },
  { c: 'Metro Cnc',        nsv:  0.49, units:  23205, share:  1.35, asp: 212.38 },
  { c: 'More Retail',      nsv:  0.41, units:  21274, share:  1.13, asp: 192.97 },
  { c: 'VMM',              nsv:  0.36, units:  20283, share:  1.01, asp: 177.91 },
];

// Categories
const CATS = [
  { cat: 'Face',  nsv: 24.07, units: 1451135, share: 66.82 },
  { cat: 'Hair',  nsv:  7.87, units:  336842, share: 21.85 },
  { cat: 'Body',  nsv:  2.08, units:  124739, share:  5.78 },
  { cat: 'Baby',  nsv:  1.91, units:  133943, share:  5.30 },
];

// MoM trend (Apr, May, Jul — June absent from source)
const TREND = [
  { mo: 'Apr', nsv: 35.88, units: 2111579, asp: 169.94, real: 42.4 },
  { mo: 'May', nsv: 40.19, units: 2344397, asp: 171.44, real: 42.3 },
  { mo: 'Jun', nsv: null, units: null, asp: null, real: null },  // ABSENT
  { mo: 'Jul', nsv: 36.06, units: 2051674, asp: 175.76, real: 42.8 },
];

// Price-volume decomp May→Jul
const PV = { vol: -5.02, price: 0.89, total: -4.13 };

// Brand × zone (₹ Cr)
const BZ_MEA = { West:4.96, 'South-1':5.24, North:4.73, 'South-2':3.70, East:2.91, Central:1.25 };
const BZ_TDC = { West:3.23, 'South-1':2.76, North:2.11, 'South-2':1.11, East:0.60, Central:0.82 };

/* ============================================================= SLIDE 1: COVER */
{
  const s = pres.addSlide();
  s.background = { color: TEAL };
  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: PW, h: 0.06, fill: { color: GREEN } });
  s.addShape(pres.ShapeType.rect, { x: 0, y: 5.8, w: PW, h: 3.2, fill: { color: '0E5952' } });

  s.addText('MODERN TRADE', txt({ x: M, y: 1.8, w: CW, h: 0.50, color: 'BFDCD7',
    fontSize: 10, bold: true, charSpacing: 2.5, align: 'center', fontFace: FONTH }));
  s.addText('Offtake Command Centre', txt({ x: M, y: 2.36, w: CW, h: 1.20, color: W,
    fontSize: 36, bold: true, fontFace: FONTH, align: 'center', lineSpacingMultiple: 0.90 }));
  s.addText('July 2026  ·  FY27', txt({ x: M, y: 3.72, w: CW, h: 0.32, color: 'BFDCD7',
    fontSize: 12, align: 'center', fontFace: FONTH }));

  s.addText('₹36.06 Cr  ·  2.05 M units  ·  ASP ₹175.76  ·  Realisation 42.8%', txt({
    x: M + 0.20, y: 6.08, w: CW - 0.40, h: 0.30, color: W, fontSize: 9.5, bold: true,
    align: 'center', fontFace: FONTH }));
  s.addText('Offtake-data view · No primary / gap / conversion · 8-gate PASS_WITH_FLAG · Pattern-Matcher-Router', txt({
    x: M + 0.20, y: 6.46, w: CW - 0.40, h: 0.26, color: '8ABFBA', fontSize: 7.5,
    align: 'center', italic: true }));

  const pills = [
    ['5 Brands','Honasa portfolio'],['6 Zones + eB2B + SIS','Channel view'],
    ['9 Chains','Ranked by offtake'],['4 Categories','Face / Hair / Body / Baby'],
  ];
  pills.forEach(([big, small], i) => {
    const px = M + i * (CW / 4) + 0.06, pw = CW / 4 - 0.12;
    s.addShape(pres.ShapeType.roundRect, { x: px, y: 7.10, w: pw, h: 0.78, rectRadius: 0.03,
      fill: { color: '0E5952' }, line: { color: BRIGHT, width: 0.75 } });
    s.addText(big, txt({ x: px + 0.06, y: 7.16, w: pw - 0.12, h: 0.32, color: BRIGHT,
      fontSize: 9.5, bold: true, fontFace: FONTH, align: 'center' }));
    s.addText(small, txt({ x: px + 0.06, y: 7.52, w: pw - 0.12, h: 0.28, color: '8ABFBA',
      fontSize: 6.6, align: 'center' }));
  });

  s.addText('Honasa Consumer Limited — Internal. Not for distribution.', txt({
    x: M, y: 12.14, w: CW, h: 0.22, color: '5F9692', fontSize: 6.5, align: 'center' }));
}

/* ============================================================= SLIDE 2: NATIONAL SNAPSHOT */
{
  const s = page(2, 'National Offtake Snapshot — July 2026',
    'Total MT (geo zones + eB2B + SIS) · Offtake data only · 8-gate PASS_WITH_FLAG');

  let y = BODY_Y;
  // 4 KPI tiles
  const kw = (CW - 0.30) / 4, kx = i => M + i * (kw + 0.10);
  kpi(s, { x: kx(0), y, w: kw, h: 0.92, label: 'TOTAL MT NSV', value: '₹36.06 Cr',  sub: 'FY27 July offtake', accent: TEAL });
  kpi(s, { x: kx(1), y, w: kw, h: 0.92, label: 'UNITS SOLD',  value: '20.5 L',      sub: '2,051,674 packs', accent: BRIGHT });
  kpi(s, { x: kx(2), y, w: kw, h: 0.92, label: 'AVG SELL PRICE', value: '₹175.76', sub: 'NSV ÷ units (EXACT)', accent: BLUE });
  kpi(s, { x: kx(3), y, w: kw, h: 0.92, label: 'REALISATION', value: '42.8%',       sub: 'NSV ÷ MRP value', accent: GREEN });
  y += 1.04;

  // Channel split KPIs
  const hw = (CW - 0.16) / 3, hx = i => M + i * (hw + 0.08);
  kpi(s, { x: hx(0), y, w: hw, h: 0.92, label: 'GEOGRAPHIC MT (6 zones)', value: '₹33.95 Cr', sub: '1,894,026 units · 94.1% of total', accent: TEAL });
  kpi(s, { x: hx(1), y, w: hw, h: 0.92, label: 'eB2B (Nykaa / FSN)',      value: '₹2.07 Cr',  sub: '155,142 units · ASP ₹133.19',    accent: BLUE });
  kpi(s, { x: hx(2), y, w: hw, h: 0.92, label: 'SIS (Azorte / SS etc)',   value: '₹0.03 Cr',  sub: '1,506 units · ASP ₹225.85',      accent: AMBER });
  y += 1.04;

  // Insight card
  y = banner(s, y, 'WHAT THE NATIONAL NUMBER TELLS YOU', TEAL);
  const cy = card(s, { x: M, y, w: CW, h: 2.88, label: 'NATIONAL DIAGNOSTIC — JULY 2026', accent: TEAL });
  bullets(s, { x: M + 0.14, y: cy, w: CW - 0.28, gap: 0.44, size: 8.2, items: [
    { t: '₹36.06 Cr offtake on ₹84.16 Cr MRP value = 42.8% realisation. Every ₹100 of shelf value returns ₹42.80 of NSV.', b: true, c: TEAL },
    { t: 'ASP ₹175.76 per unit — split: Mamaearth ₹169.60, The Derma Co. ₹188.30, Aqualogica ₹234.50. Portfolio ASP is a weighted blend of brand mix.' },
    { t: 'eB2B (Nykaa) realisation 57.4% — structurally higher because MRP is lower (discounts already netted by FSN). Do not benchmark eB2B against geo-MT realisation.' },
    { t: 'SIS (Azorte / Shoppers Stop etc.) is ₹0.03 Cr — rounding territory. Offtake data for SIS is measured differently; treat as directional only.' },
    { t: 'June 2026 is absent from the offtake source — Q1 FY27 series = Apr + May + Jul only. Do not impute June.', c: AMBER },
  ]});
  y += 3.04;

  // MoM bar
  chartTitle(s, M, y, CW, 'NSV trend Q1 FY27 — Apr / May / Jul (₹ Cr, June absent)');
  s.addChart(pres.ChartType.bar, [{
    name: 'NSV',
    labels: ['Apr', 'May', 'Jun\n(absent)', 'Jul'],
    values: [35.88, 40.19, null, 36.06]
  }], Object.assign({}, axisBase, {
    x: M, y: y + 0.22, w: CW * 0.56, h: 1.60,
    barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 50,
    chartColors: [BRIGHT, BRIGHT, LINE, TEAL],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 7.8,
    valAxisMaxVal: 45, showLegend: false,
  }));

  // ASP trend
  chartTitle(s, M + CW * 0.58, y, CW * 0.42, 'ASP trend (₹/unit)');
  s.addChart(pres.ChartType.line, [{
    name: 'ASP', labels: ['Apr', 'May', 'Jul'], values: [169.94, 171.44, 175.76]
  }], Object.assign({}, axisBase, {
    x: M + CW * 0.58, y: y + 0.22, w: CW * 0.42, h: 1.60,
    chartColors: [BLUE], lineSize: 2, lineDataSymbolSize: 6,
    showValue: true, dataLabelPosition: 't', dataLabelFontSize: 7,
    valAxisMinVal: 165, valAxisMaxVal: 180,
  }));
  y += 1.88;

  s.addText('↓5.0 Cr volume effect + ↑0.9 Cr price/mix = −4.1 Cr vs May. Jul dip is volume (−293k units), not pricing. ASP is rising (+₹4.32 vs May) — mix is healthy.', txt({
    x: M, y, w: CW, h: 0.32, fontSize: 7.2, color: GREY, lineSpacingMultiple: 0.92 }));
}

/* ============================================================= SLIDE 3: Q1 FY27 PERFORMANCE */
// FY26 monthly offtake (Lakh, from pre-agg workbook) — Apr-25 to Mar-26:
// [3174.6, 2366.9, 2182.64, 2472.9, ...] → Apr=31.75, May=23.67, Jun=21.83, Jul=24.73 Cr
const LY = { apr: 31.75, may: 23.67, jun: 21.83, jul: 24.73 };
const FY27 = { apr: 35.88, may: 40.19, jul: 36.06 }; // Jun absent
const Q1_FY27 = 35.88 + 40.19 + 36.06;    // 112.13 Cr (3 months)
const Q1_FY26C = 31.75 + 23.67 + 24.73;   // 80.15 Cr (same 3 months LY)
const Q1_YOY = ((Q1_FY27 - Q1_FY26C) / Q1_FY26C * 100).toFixed(1); // +39.9%
{
  const s = page(3, 'Q1 FY27 Performance — Apr + May + Jul vs Last Year',
    'June 2026 absent from source · Comparable 3-month LY = Apr-25 + May-25 + Jul-25 · Pre-agg workbook');

  let y = BODY_Y;

  // Row 1: 4 headline KPIs
  const kw4 = (CW - 0.30) / 4, kx4 = i => M + i * (kw4 + 0.10);
  kpi(s, { x: kx4(0), y, w: kw4, h: 0.92, label: 'Q1 FY27 NSV (3 months)', value: '₹112.13 Cr',
    sub: 'Apr + May + Jul · Jun absent', accent: TEAL });
  kpi(s, { x: kx4(1), y, w: kw4, h: 0.92, label: 'Q1 FY26 COMPARABLE',    value: '₹80.15 Cr',
    sub: 'Same 3 months LY · pre-agg', accent: GREY });
  kpi(s, { x: kx4(2), y, w: kw4, h: 0.92, label: 'YoY GROWTH (3M)',       value: '+39.9%',
    sub: 'Like-for-like comparable', accent: GREEN, valueColor: GREEN });
  kpi(s, { x: kx4(3), y, w: kw4, h: 0.92, label: 'MONTHLY AVG FY27',      value: '₹37.38 Cr',
    sub: '₹112.13 ÷ 3 months', accent: BLUE });
  y += 1.04;

  // Monthly grouped bar (FY27 vs FY26)
  chartTitle(s, M, y, CW * 0.58, 'Monthly offtake NSV — FY27 vs FY26 LY (₹ Cr)');
  s.addChart(pres.ChartType.bar, [
    { name: 'FY27', labels: ['Apr', 'May', 'Jun\n(absent)', 'Jul'],
      values: [FY27.apr, FY27.may, null, FY27.jul] },
    { name: 'FY26 LY', labels: ['Apr', 'May', 'Jun', 'Jul'],
      values: [LY.apr, LY.may, LY.jun, LY.jul] },
  ], Object.assign({}, axisBase, {
    x: M, y: y + 0.22, w: CW * 0.58, h: 2.34,
    barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 35,
    chartColors: [TEAL, BLUE],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 6.5,
    valAxisLabelFontSize: 7, catAxisLabelFontSize: 8,
    showLegend: true, legendPos: 'b', legendFontSize: 7, legendColor: GREY,
  }));

  // Month growth cards (right column)
  const gmw = (CW * 0.40 - 0.08) / 3, gmx = i => M + CW * 0.60 + i * (gmw + 0.04);
  chartTitle(s, M + CW * 0.60, y, CW * 0.40, 'YoY growth — Jul is accelerating');
  [
    { mo: 'APR', pct: '+13.0%', fy27: '₹35.88', fy26: '₹31.75', delta: '+₹4.13', a: TEAL },
    { mo: 'MAY', pct: '+69.8%', fy27: '₹40.19', fy26: '₹23.67', delta: '+₹16.52', a: BRIGHT },
    { mo: 'JUL', pct: '+45.8%', fy27: '₹36.06', fy26: '₹24.73', delta: '+₹11.33', a: BLUE },
  ].forEach((m, i) => {
    const gy = card(s, { x: gmx(i), y: y + 0.22, w: gmw, h: 2.34, label: m.mo, accent: m.a });
    s.addText(m.pct, txt({ x: gmx(i)+0.06, y: gy+0.04, w: gmw-0.12, h: 0.40,
      fontSize: 16, bold: true, fontFace: FONTH, color: GREEN, align: 'center' }));
    s.addText(m.fy27 + ' Cr', txt({ x: gmx(i)+0.06, y: gy+0.48, w: gmw-0.12, h: 0.22,
      fontSize: 7.5, bold: true, color: TEAL, align: 'center' }));
    s.addText('vs ' + m.fy26 + ' Cr LY', txt({ x: gmx(i)+0.06, y: gy+0.72, w: gmw-0.12, h: 0.20,
      fontSize: 6.8, color: GREY, align: 'center' }));
    s.addText(m.delta + ' Cr', txt({ x: gmx(i)+0.06, y: gy+0.96, w: gmw-0.12, h: 0.24,
      fontSize: 8.5, bold: true, color: GREEN, align: 'center' }));
  });
  y += 2.68;

  // Insight block
  y = banner(s, y, 'Q1 FY27 READ — DIAGNOSTIC & INTERPRETATION', TEAL);
  const cy = card(s, { x: M, y, w: CW, h: 3.00, label: 'Q1 DIAGNOSTIC — FY27 vs FY26 COMPARABLE', accent: TEAL });
  bullets(s, { x: M + 0.14, y: cy, w: CW - 0.28, gap: 0.46, size: 7.8, items: [
    { t: 'Q1 FY27 (3-month comparable): ₹112.13 Cr vs ₹80.15 Cr FY26 = +39.9% YoY. Structural growth across all 3 months.', b: true, c: TEAL },
    { t: 'May is the standout: ₹40.19 Cr (+69.8% vs May-25 ₹23.67 Cr). Likely promotional activation drove a strong billing month. Watch if May demand was pull-forward from June/July.' },
    { t: 'July came in at ₹36.06 Cr vs ₹24.73 Cr LY (+45.8%). Post-May softness is normal. The key signal: July grew 45.8% YoY, not declining vs FY26.', b: true, c: GREEN },
    { t: 'June 2026 is absent from the offtake source. The true Q1 4-month total cannot be computed. FY26 June was ₹21.83 Cr — if added to FY26 base, comparable YoY = ₹112.13 Cr vs ₹102.0 Cr = +10%. Use 3-month comparable (+39.9%) as primary lens.', c: AMBER },
    { t: 'FY27 monthly avg ₹37.38 Cr vs FY26 same-period avg ₹26.72 Cr. Run rate improvement of +40% is the H1 baseline for planning Aug–Sep targets.', c: BLUE },
  ]});
}

/* ============================================================= SLIDE 4: JULY MTD vs LY */
{
  const s = page(4, 'July 2026 MTD — vs Last Year (July FY26)',
    'Jul-26 EXACT from CSV (220,522 rows) · Jul-25 from pre-aggregated FY26 workbook (NSV only)');

  let y = BODY_Y;

  // Big side-by-side comparison
  y = banner(s, y, 'NATIONAL OFFTAKE — JULY 2026 vs JULY 2025', TEAL);
  const bw = (CW - 0.14) / 3, bx = i => M + i * (bw + 0.07);

  // Jul-26 card
  const ay26 = card(s, { x: bx(0), y, w: bw, h: 2.60, label: 'JULY 2026 (FY27) — THIS YEAR', accent: TEAL });
  s.addText('₹36.06 Cr', txt({ x: bx(0)+0.10, y: ay26,       w: bw-0.20, h: 0.46, fontSize: 22, bold: true, fontFace: FONTH, color: TEAL, align: 'center' }));
  s.addText('2,051,674 units', txt({ x: bx(0)+0.10, y: ay26+0.50, w: bw-0.20, h: 0.22, fontSize: 8.5, color: GREY, align: 'center', bold: true }));
  s.addText('ASP ₹175.76 / unit', txt({ x: bx(0)+0.10, y: ay26+0.74, w: bw-0.20, h: 0.20, fontSize: 7.5, color: GREY, align: 'center' }));
  s.addText('Realisation 42.8%', txt({ x: bx(0)+0.10, y: ay26+0.96, w: bw-0.20, h: 0.20, fontSize: 7.5, color: GREY, align: 'center' }));
  s.addText('Source: EXACT (CSV 220,522 rows, 0 bad)', txt({ x: bx(0)+0.10, y: ay26+1.22, w: bw-0.20, h: 0.18, fontSize: 6.2, color: BRIGHT, align: 'center', italic: true }));

  // YoY growth card (middle)
  const aym = card(s, { x: bx(1), y, w: bw, h: 2.60, label: 'YoY GROWTH', accent: GREEN });
  s.addText('+₹11.33 Cr', txt({ x: bx(1)+0.10, y: aym,       w: bw-0.20, h: 0.44, fontSize: 20, bold: true, fontFace: FONTH, color: GREEN, align: 'center' }));
  s.addText('+45.8%', txt({ x: bx(1)+0.10, y: aym+0.48, w: bw-0.20, h: 0.36, fontSize: 17, bold: true, fontFace: FONTH, color: GREEN, align: 'center' }));
  s.addText('July is the 2nd highest-growth\nmonth in Q1 FY27 after May', txt({ x: bx(1)+0.10, y: aym+0.90, w: bw-0.20, h: 0.46, fontSize: 7.5, color: INK, align: 'center', lineSpacingMultiple: 0.92 }));
  s.addText('Apr +13.0%  ·  May +69.8%  ·  Jul +45.8%', txt({ x: bx(1)+0.10, y: aym+1.40, w: bw-0.20, h: 0.22, fontSize: 6.8, color: GREY, align: 'center' }));

  // Jul-25 card
  const ay25 = card(s, { x: bx(2), y, w: bw, h: 2.60, label: 'JULY 2025 (FY26) — LAST YEAR', accent: BLUE });
  s.addText('₹24.73 Cr', txt({ x: bx(2)+0.10, y: ay25,       w: bw-0.20, h: 0.46, fontSize: 22, bold: true, fontFace: FONTH, color: BLUE, align: 'center' }));
  s.addText('Units: not in monthly data', txt({ x: bx(2)+0.10, y: ay25+0.50, w: bw-0.20, h: 0.22, fontSize: 8, color: GREY, align: 'center' }));
  s.addText('ASP: not in monthly data', txt({ x: bx(2)+0.10, y: ay25+0.74, w: bw-0.20, h: 0.20, fontSize: 7.5, color: GREY, align: 'center' }));
  s.addText('Realisation: not in monthly data', txt({ x: bx(2)+0.10, y: ay25+0.96, w: bw-0.20, h: 0.20, fontSize: 7.5, color: GREY, align: 'center' }));
  s.addText('Source: monthly_fy26[3] from pre-agg workbook', txt({ x: bx(2)+0.10, y: ay25+1.22, w: bw-0.20, h: 0.18, fontSize: 6.2, color: AMBER, align: 'center', italic: true }));
  y += 2.72;

  // Zone July FY27 bar + FY26 YTD context
  const hw = (CW - 0.10) / 2, hx2 = i => M + i * (hw + 0.10);

  chartTitle(s, hx2(0), y, hw, 'Zone NSV — July 2026 actual (₹ Cr)');
  s.addChart(pres.ChartType.bar, [{
    name: 'Jul-26 NSV',
    labels: GEO_ZONES.map(z => z.z),
    values: GEO_ZONES.map(z => z.nsv),
  }], Object.assign({}, axisBase, {
    x: hx2(0), y: y + 0.22, w: hw, h: 2.18,
    barDir: 'bar', barGrouping: 'clustered', barGapWidthPct: 38,
    chartColors: [TEAL, BRIGHT, BLUE, AMBER, GREEN, RED],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 7,
    catAxisLabelFontSize: 7.5, valAxisLabelFontSize: 7,
  }));

  // FY27 YTD zone bar (data.js fy27, 3-month)
  const ZY = { West:37.33, 'South-1':33.08, North:33.40, 'South-2':20.64, East:15.29, Central:2.12 };
  chartTitle(s, hx2(1), y, hw, 'Zone NSV — Q1 FY27 YTD (₹ Cr, Apr+May+Jul)');
  s.addChart(pres.ChartType.bar, [{
    name: 'Q1 FY27 YTD',
    labels: Object.keys(ZY),
    values: Object.values(ZY),
  }], Object.assign({}, axisBase, {
    x: hx2(1), y: y + 0.22, w: hw, h: 2.18,
    barDir: 'bar', barGrouping: 'clustered', barGapWidthPct: 38,
    chartColors: [TEAL, BRIGHT, BLUE, AMBER, GREEN, RED],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 7,
    catAxisLabelFontSize: 7.5, valAxisLabelFontSize: 7,
  }));
  y += 2.52;

  // Insight block
  y = banner(s, y, 'JULY MTD DIAGNOSTIC — WHAT IS AVAILABLE vs WHAT IS MISSING', BLUE);
  const c2w = (CW - 0.14) / 2, c2x = i => M + i * (c2w + 0.14);
  const ly1 = card(s, { x: c2x(0), y, w: c2w, h: 2.80, label: 'WHAT WE CAN CONFIRM (EXACT)', accent: GREEN });
  bullets(s, { x: c2x(0)+0.10, y: ly1, w: c2w-0.20, gap: 0.46, size: 7.4, dot: GREEN, items: [
    { t: 'Jul-26 NSV ₹36.06 Cr — from Jul-26 CSV (220,522 rows, 0 bad rows, 8-gate PASS_WITH_FLAG).', b: true },
    { t: 'Jul-26 units 2,051,674 · ASP ₹175.76 · Realisation 42.8% — all EXACT from source.' },
    { t: 'Jul-25 NSV ₹24.73 Cr — from monthly_fy26[3] pre-aggregated workbook. This is the official LY baseline.' },
    { t: 'YoY NSV growth +45.8% (+₹11.33 Cr). July is growing faster than April (+13.0%).' },
    { t: 'Jul-26 zone breakdown available: West ₹8.27 Cr → Central ₹2.12 Cr (see adjacent chart).', c: TEAL },
  ]});
  const ly2 = card(s, { x: c2x(1), y, w: c2w, h: 2.80, label: 'WHAT IS NOT YET AVAILABLE (LY)', accent: AMBER });
  bullets(s, { x: c2x(1)+0.10, y: ly2, w: c2w-0.20, gap: 0.46, size: 7.4, dot: AMBER, items: [
    { t: 'Jul-25 units and ASP — pre-aggregated monthly data holds only NSV, not units. Cannot compute LY ASP.', b: true },
    { t: 'Jul-25 zone breakdown — pre-agg workbook stores FY26 zone total, not monthly zone detail. Zone LY comparison requires article-level Jul-25 CSV.', c: AMBER },
    { t: 'Jul-25 brand breakdown — same limitation. LY brand × month detail not in current data.js.' },
    { t: 'Jul-25 realisation — requires LY MRP Sales Value, which is not in the monthly pre-agg data.' },
    { t: 'TO UNLOCK: Supply article-level Jul-25 offtake CSV to PowerBI/RawDataFolders/Offtake_Monthly/ and run --offtake-patch. All LY splits will appear automatically.', c: RED },
  ]});
}

/* ============================================================= SLIDE 5: ZONE PERFORMANCE */
{
  const s = page(5, 'Zone Offtake Performance — July 2026',
    'Geographic MT only (excl. eB2B / SIS) · NSV, Units, ASP, Realisation by zone');

  let y = BODY_Y;

  // Zone NSV bars
  chartTitle(s, M, y, CW * 0.55, 'Offtake NSV by zone (₹ Cr)');
  s.addChart(pres.ChartType.bar, [{
    name: 'NSV', labels: GEO_ZONES.map(z => z.z), values: GEO_ZONES.map(z => z.nsv)
  }], Object.assign({}, axisBase, {
    x: M, y: y + 0.22, w: CW * 0.55, h: 2.60,
    barDir: 'bar', barGrouping: 'clustered', barGapWidthPct: 40,
    chartColors: [BRIGHT, BRIGHT, BRIGHT, BRIGHT, AMBER, BRIGHT],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 7,
    catAxisLabelFontSize: 7.5,
  }));

  // Zone unit bars
  chartTitle(s, M + CW * 0.57, y, CW * 0.43, 'Units sold by zone (000s)');
  s.addChart(pres.ChartType.bar, [{
    name: 'Units', labels: GEO_ZONES.map(z => z.z), values: GEO_ZONES.map(z => +(z.units/1000).toFixed(1))
  }], Object.assign({}, axisBase, {
    x: M + CW * 0.57, y: y + 0.22, w: CW * 0.43, h: 2.60,
    barDir: 'bar', barGrouping: 'clustered', barGapWidthPct: 40,
    chartColors: [BLUE], showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 7,
  }));
  y += 2.88;

  // Zone table
  table(s, { x: M, y, w: CW, cols: [
    { t: 'ZONE', w: 1.4 }, { t: 'NSV (₹ Cr)', w: 0.9, a: 'right' }, { t: 'UNITS', w: 1.0, a: 'right' },
    { t: 'ASP (₹)', w: 0.9, a: 'right' }, { t: 'REALISATION', w: 1.0, a: 'right' },
    { t: 'NSV SHARE', w: 0.9, a: 'right' }
  ], rows: GEO_ZONES.map(z => {
    const aspColor = z.asp > 185 ? GREEN : z.asp < 170 ? RED : INK;
    const realColor = z.real < 41.5 ? RED : z.real > 43 ? GREEN : INK;
    return [
      { t: z.z, b: true },
      { t: `₹${z.nsv}`, b: true },
      { t: (z.units/1000).toFixed(0) + 'k' },
      { t: `₹${z.asp.toFixed(0)}`, c: aspColor, b: true },
      { t: `${z.real.toFixed(1)}%`, c: realColor },
      { t: `${z.share.toFixed(1)}%` }
    ];
  }), rowH: 0.32 });
  y += 0.28 + GEO_ZONES.length * 0.32 + 0.12;

  s.addText('ASP range: East ₹193 (highest, premium mix) → West ₹166 (volume leader, lower-ASP packs). The 16% spread across zones is mix-driven, not discount-driven — realisation is tight across all geo zones (41–43%).', txt({
    x: M, y, w: CW, h: 0.34, fontSize: 7.2, color: GREY, lineSpacingMultiple: 0.92 }));
  y += 0.42;

  y = banner(s, y, 'ZONE SHARE vs ASP — READING THE SCATTER', BLUE);
  s.addText('West is the volume anchor (23% share, cheapest ASP). South-1 matches on NSV with fewer units at a premium ASP. East has the highest ASP but a small share — premium-heavy, scale-limited. Central is the growth watch: 5.9% share, ASP below national (₹170 vs ₹176), realisation lowest in geo-MT (41.1%).', txt({
    x: M + 0.10, y: y + 0.04, w: CW - 0.20, h: 0.40, fontSize: 7.4, color: INK, lineSpacingMultiple: 0.92 }));
}

/* ============================================================= SLIDE 6: ZONE ASP ANALYSIS */
{
  const s = page(6, 'Zone ASP Analysis — Why Zones Differ',
    'Price / mix / realisation decomposition · Pattern-matcher-router: diagnostic question type');

  let y = BODY_Y;

  // ASP scatter: NSV share (x) vs ASP (y) — one dot per zone
  chartTitle(s, M, y, CW, 'Zone NSV share (%) vs ASP (₹/unit) — each dot is one geographic zone');
  const ZONE_SHARE = GEO_ZONES.map(z => z.share);
  const ZONE_ASP   = GEO_ZONES.map(z => z.asp);
  const pt = (i, val, arr) => arr.map((_, j) => j === i ? val : null);
  s.addChart(pres.ChartType.scatter, [
    { name: 'X-Axis', values: ZONE_SHARE },
    ...GEO_ZONES.map((z, i) => ({ name: z.z, values: pt(i, z.asp, ZONE_ASP) }))
  ], Object.assign({}, axisBase, {
    x: M, y: y + 0.22, w: CW, h: 2.20,
    chartColors: [BLUE, GREEN, BRIGHT, GREEN, AMBER, RED, AMBER],
    lineSize: 0, lineDataSymbolSize: 10,
    catAxisTitle: 'NSV share (%)', showCatAxisTitle: true,
    valAxisTitle: 'ASP (₹/unit)', showValAxisTitle: true,
    valAxisMinVal: 155, valAxisMaxVal: 205,
    catAxisMinVal: 0, catAxisMaxVal: 26,
    axisLabelFontSize: 6.5, valAxisTitleFontSize: 6.5, catAxisTitleFontSize: 6.5,
    showLegend: true, legendPos: 'r', legendFontSize: 6.5, legendColor: GREY,
  }));
  s.addText('Upper-right = high-share, high-ASP zone (ideal). Lower-left = smaller zone, lower ASP. West is high-share but low-ASP — volume drag. East is high-ASP but low-share — premium, not yet at scale.', txt({
    x: M, y: y + 2.48, w: CW, h: 0.30, fontSize: 7.0, color: GREY, lineSpacingMultiple: 0.92 }));
  y += 2.88;

  // Root cause table
  y = banner(s, y, 'ROOT CAUSE ASSESSMENT — ZONE ASP GAP (Diagnostic, HIGH confidence)', TEAL);
  table(s, { x: M, y, w: CW, cols: [
    { t: 'ZONE', w: 1.2 }, { t: 'ASP', w: 0.7, a: 'right' }, { t: 'vs NAT (₹176)', w: 0.9, a: 'right' },
    { t: 'REAL', w: 0.7, a: 'right' }, { t: 'ROOT CAUSE', w: 3.2 }
  ], rows: [
    [{ t:'West', b:true }, { t:'₹166', c:RED }, { t:'−10', c:RED }, { t:'41.9%' }, 'High 400ml Mamaearth share pulls ASP down; premium TDC underweight'],
    [{ t:'South-1', b:true }, { t:'₹189', c:GREEN }, { t:'+13', c:GREEN }, { t:'42.7%' }, 'Strong TDC mix (33.7%); premium face-care skews ASP up'],
    [{ t:'North', b:true }, { t:'₹185', c:GREEN }, { t:'+9', c:GREEN }, { t:'41.8%' }, 'Balanced brand + pack mix; no single drag factor'],
    [{ t:'South-2', b:true }, { t:'₹175', c:INK }, { t:'−1', c:GREY }, { t:'43.0%' }, 'Closest to national average; best realisation in geo-MT'],
    [{ t:'East', b:true }, { t:'₹193', c:GREEN }, { t:'+17', c:GREEN }, { t:'42.1%' }, 'Premium pack concentration; fewer high-volume cheap SKUs'],
    [{ t:'Central', b:true }, { t:'₹170', c:AMBER }, { t:'−6', c:AMBER }, { t:'41.1%' }, 'Higher 400ml Mamaearth mix + lowest realisation in geo-MT'],
  ], rowH: 0.34 });
  y += 0.28 + 6 * 0.34 + 0.12;

  // Price-volume decomp cards
  y = banner(s, y, 'PRICE-VOLUME DECOMPOSITION — May → July', BLUE);
  const c3w = (CW - 0.24) / 3, c3x = i => M + i * (c3w + 0.12);
  const pvy = card(s, { x: c3x(0), y, w: c3w, h: 1.60, label: 'VOLUME EFFECT', accent: RED });
  s.addText('−5.02 Cr', txt({ x: c3x(0)+0.10, y: pvy, w: c3w-0.20, h: 0.40, fontSize: 18, bold: true, fontFace: FONTH, color: RED, align: 'center' }));
  s.addText('−292,724 units × ₹171.44 May ASP', txt({ x: c3x(0)+0.10, y: pvy+0.42, w: c3w-0.20, h: 0.28, fontSize: 7, color: GREY, align: 'center' }));
  s.addText('Volume contracted. July billed less than May by 12.5%. This is the entire NSV decline.', txt({ x: c3x(0)+0.10, y: pvy+0.72, w: c3w-0.20, h: 0.44, fontSize: 7, color: INK, lineSpacingMultiple: 0.92 }));

  const ppvy = card(s, { x: c3x(1), y, w: c3w, h: 1.60, label: 'PRICE / MIX EFFECT', accent: GREEN });
  s.addText('+0.89 Cr', txt({ x: c3x(1)+0.10, y: ppvy, w: c3w-0.20, h: 0.40, fontSize: 18, bold: true, fontFace: FONTH, color: GREEN, align: 'center' }));
  s.addText('2,051,674 Jul units × +₹4.32 ASP gain', txt({ x: c3x(1)+0.10, y: ppvy+0.42, w: c3w-0.20, h: 0.28, fontSize: 7, color: GREY, align: 'center' }));
  s.addText('ASP rose ₹4.32 vs May (+2.5%). Mix shifted toward TDC and premium packs offsetting volume loss.', txt({ x: c3x(1)+0.10, y: ppvy+0.72, w: c3w-0.20, h: 0.44, fontSize: 7, color: INK, lineSpacingMultiple: 0.92 }));

  const tvy = card(s, { x: c3x(2), y, w: c3w, h: 1.60, label: 'NET NSV CHANGE', accent: TEAL });
  s.addText('−4.13 Cr', txt({ x: c3x(2)+0.10, y: tvy, w: c3w-0.20, h: 0.40, fontSize: 18, bold: true, fontFace: FONTH, color: RED, align: 'center' }));
  s.addText('May ₹40.19 Cr → Jul ₹36.06 Cr', txt({ x: c3x(2)+0.10, y: tvy+0.42, w: c3w-0.20, h: 0.28, fontSize: 7, color: GREY, align: 'center' }));
  s.addText('Decline is 100% volume-driven. Pricing is improving. Diagnose the unit shortfall, not the price.', txt({ x: c3x(2)+0.10, y: tvy+0.72, w: c3w-0.20, h: 0.44, fontSize: 7, color: INK, lineSpacingMultiple: 0.92 }));
}

/* ============================================================= SLIDE 7: TOP CHAINS */
{
  const s = page(7, 'Chain Performance — Top 9 Accounts',
    'Geographic MT · NSV, units, ASP ranking · Big 3 = Dmart + Reliance + Apollo');

  let y = BODY_Y;

  // Chain NSV bar
  chartTitle(s, M, y, CW * 0.58, 'Offtake NSV by chain (₹ Cr) — top 9');
  s.addChart(pres.ChartType.bar, [{
    name: 'NSV', labels: CHAINS.map(c => c.c), values: CHAINS.map(c => c.nsv)
  }], Object.assign({}, axisBase, {
    x: M, y: y + 0.22, w: CW * 0.58, h: 3.20,
    barDir: 'bar', barGrouping: 'clustered', barGapWidthPct: 35,
    chartColors: [TEAL, BRIGHT, BLUE, AMBER, GREEN, BRIGHT, BRIGHT, BRIGHT, BRIGHT],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 7, catAxisLabelFontSize: 7.5,
  }));

  // Chain ASP bar
  chartTitle(s, M + CW * 0.60, y, CW * 0.40, 'ASP by chain (₹/unit)');
  s.addChart(pres.ChartType.bar, [{
    name: 'ASP', labels: CHAINS.map(c => c.c), values: CHAINS.map(c => c.asp)
  }], Object.assign({}, axisBase, {
    x: M + CW * 0.60, y: y + 0.22, w: CW * 0.40, h: 3.20,
    barDir: 'bar', barGrouping: 'clustered', barGapWidthPct: 35,
    chartColors: [BLUE], showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 7,
    catAxisLabelFontSize: 7.5,
    catAxisLabelPosition: 'none',
  }));
  y += 3.46;

  // Chain table
  table(s, { x: M, y, w: CW, cols: [
    { t: 'CHAIN', w: 1.6 }, { t: 'NSV (₹ Cr)', w: 1.0, a: 'right' },
    { t: 'UNITS', w: 0.9, a: 'right' }, { t: 'ASP (₹)', w: 0.9, a: 'right' },
    { t: 'SHARE', w: 0.8, a: 'right' }, { t: 'SIGNAL', w: 1.7 }
  ], rows: [
    [{ t:'Dmart',b:true },    { t:'₹13.97',b:true }, { t:'883k' }, { t:'₹158',c:RED },  { t:'38.8%',b:true }, 'Volume engine; low ASP — Mamaearth 400ml dominant'],
    [{ t:'Reliance',b:true }, { t:'₹8.06',b:true },  { t:'399k' }, { t:'₹202',c:GREEN },{ t:'22.4%',b:true }, 'Premium skew; best geo-chain ASP after Lulu'],
    [{ t:'Apollo',b:true },   { t:'₹7.18',b:true },  { t:'412k' }, { t:'₹174' },         { t:'19.9%',b:true }, 'Pharma-MT; high units, mid ASP'],
    [{ t:'Lulu',b:true },     { t:'₹1.70' },          { t:'56k' },  { t:'₹304',c:GREEN }, { t:'4.7%' },         'Highest ASP — premium portfolio, low volume'],
    [{ t:'Wellness Forever' },{ t:'₹0.72' },          { t:'32k' },  { t:'₹225' },         { t:'2.0%' },         'Health-pharma format; growing TDC share'],
    [{ t:'H&G' },             { t:'₹0.51' },          { t:'18k' },  { t:'₹281' },         { t:'1.4%' },         'Premium general trade; niche but high-value'],
    [{ t:'Metro Cnc' },       { t:'₹0.49' },          { t:'23k' },  { t:'₹212' },         { t:'1.4%' },         'Cash-n-carry; bulk purchases'],
    [{ t:'More Retail' },     { t:'₹0.41' },          { t:'21k' },  { t:'₹193' },         { t:'1.1%' },         'Emerging; South-2 heavy'],
    [{ t:'VMM' },             { t:'₹0.36' },          { t:'20k' },  { t:'₹178' },         { t:'1.0%' },         'Value Modern Trade; mid-market'],
  ], rowH: 0.31 });
  y += 0.28 + 9 * 0.31 + 0.12;

  s.addText('Big 3 concentration: Dmart + Reliance + Apollo = ₹29.21 Cr = 81.1% of geo-MT NSV. Dmart alone is 38.8% — a single-account risk and an opportunity to push premium mix harder inside Dmart.', txt({
    x: M, y, w: CW, h: 0.34, fontSize: 7.2, color: GREY, lineSpacingMultiple: 0.92 }));
}

/* ============================================================= SLIDE 8: BRAND MIX */
{
  const s = page(8, 'Brand Mix — Mamaearth · The Derma Co. · Aqualogica',
    'Geographic MT · NSV, units, share, ASP by brand and zone');

  let y = BODY_Y;
  const hw = (CW - 0.16) / 3, hx = i => M + i * (hw + 0.08);

  // Brand KPIs
  kpi(s, { x: hx(0), y, w: hw, h: 0.92, label: 'MAMAEARTH', value: '₹24.45 Cr',
    sub: '67.9% share · 1.44M units · ASP ₹170', accent: TEAL });
  kpi(s, { x: hx(1), y, w: hw, h: 0.92, label: 'THE DERMA CO.', value: '₹11.01 Cr',
    sub: '30.6% share · 585k units · ASP ₹188', accent: BRIGHT });
  kpi(s, { x: hx(2), y, w: hw, h: 0.92, label: 'AQUALOGICA', value: '₹0.48 Cr',
    sub: '1.3% share · 20.6k units · ASP ₹235', accent: BLUE });
  y += 1.04;

  // Brand split bars
  chartTitle(s, M, y, CW * 0.55, 'NSV split by brand (₹ Cr)');
  s.addChart(pres.ChartType.bar, [
    { name: 'Mamaearth', labels: ['Brand Split'], values: [24.45] },
    { name: 'The Derma Co.', labels: ['Brand Split'], values: [11.01] },
    { name: 'Aqualogica', labels: ['Brand Split'], values: [0.48] },
  ], Object.assign({}, axisBase, {
    x: M, y: y + 0.22, w: CW * 0.55, h: 1.60,
    barDir: 'bar', barGrouping: 'stacked', barGapWidthPct: 60,
    chartColors: [TEAL, BRIGHT, BLUE],
    showValue: true, dataLabelPosition: 'ctr', dataLabelFontSize: 8,
    showLegend: true, legendPos: 'b', legendFontSize: 7,
  }));

  // NSV vs Units divergence
  chartTitle(s, M + CW * 0.57, y, CW * 0.43, 'NSV share vs Unit share (divergence = ASP gap)');
  s.addChart(pres.ChartType.bar, [
    { name: 'NSV share %', labels: ['Mamaearth','The Derma Co.','Aqualogica'], values: [67.9, 30.6, 1.3] },
    { name: 'Unit share %', labels: ['Mamaearth','The Derma Co.','Aqualogica'], values: [70.2, 28.5, 1.0] },
  ], Object.assign({}, axisBase, {
    x: M + CW * 0.57, y: y + 0.22, w: CW * 0.43, h: 1.60,
    barDir: 'bar', barGrouping: 'clustered', barGapWidthPct: 30,
    chartColors: [TEAL, BRIGHT], showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 6.5,
    showLegend: true, legendPos: 'b', legendFontSize: 7,
  }));
  y += 1.88;

  s.addText('TDC NSV share (30.6%) > unit share (28.5%) → TDC is above-average ASP. Mamaearth NSV share (67.9%) < unit share (70.2%) → Mamaearth is below-average ASP. Aqualogica ASP ₹235 is the highest — premium positioning confirmed.', txt({
    x: M, y, w: CW, h: 0.30, fontSize: 7.0, color: GREY, lineSpacingMultiple: 0.92 }));
  y += 0.38;

  // Brand × Zone table
  y = banner(s, y, 'BRAND × ZONE OFFTAKE MATRIX (₹ Cr)', TEAL);
  const zoneNames = ['West','South-1','North','South-2','East','Central'];
  table(s, { x: M, y, w: CW, cols: [
    { t: 'BRAND', w: 1.5 }, ...zoneNames.map(z => ({ t: z.replace('South-','S-'), w: 0.88, a: 'right' })),
    { t: 'TOTAL', w: 0.9, a: 'right' }
  ], rows: [
    [{ t:'Mamaearth',b:true },
      ...zoneNames.map(z => ({ t:`₹${BZ_MEA[z]||0}` })),
      { t:'₹24.45', b:true, c:TEAL }],
    [{ t:'The Derma Co.',b:true },
      ...zoneNames.map(z => ({ t:`₹${BZ_TDC[z]||0}` })),
      { t:'₹11.01', b:true, c:BRIGHT }],
  ], rowH: 0.34 });
  y += 0.28 + 2 * 0.34 + 0.12;

  y = banner(s, y, 'KEY BRAND INSIGHTS', BLUE);
  bullets(s, { x: M + 0.10, y: y + 0.06, w: CW - 0.20, gap: 0.38, size: 7.4, items: [
    { t: 'West is Mamaearth\'s strongest zone (₹4.96 Cr, 20.3% of MEA) but lowest ASP. Push premium pack mix in Dmart-West.', b: true },
    { t: 'South-1 is TDC\'s best zone (₹2.76 Cr) — Apollo and Wellness Forever drive pharmacy-format premium pull.' },
    { t: 'East — TDC underweight vs MEA in absolute terms (₹0.60 Cr vs ₹2.91 Cr). Brand share gap is the East story.' },
    { t: 'Central TDC ₹0.82 Cr is not small relative to zone scale — TDC share in Central is 38.7% vs 30.6% national (healthy premium tilt).' },
  ]});
}

/* ============================================================= SLIDE 9: CATEGORIES */
{
  const s = page(9, 'Category & Sub-Category Performance',
    'Face / Hair / Body / Baby split · Geographic MT · Offtake data only');

  let y = BODY_Y;
  const kw2 = (CW - 0.30) / 4, kx2 = i => M + i * (kw2 + 0.10);
  kpi(s, { x: kx2(0), y, w: kw2, h: 0.92, label: 'FACE',  value: '₹24.07 Cr', sub: '66.8% · 1.45M units', accent: TEAL });
  kpi(s, { x: kx2(1), y, w: kw2, h: 0.92, label: 'HAIR',  value: '₹7.87 Cr',  sub: '21.8% · 337k units',  accent: BLUE });
  kpi(s, { x: kx2(2), y, w: kw2, h: 0.92, label: 'BODY',  value: '₹2.08 Cr',  sub: '5.8% · 125k units',   accent: BRIGHT });
  kpi(s, { x: kx2(3), y, w: kw2, h: 0.92, label: 'BABY',  value: '₹1.91 Cr',  sub: '5.3% · 134k units',   accent: AMBER });
  y += 1.04;

  chartTitle(s, M, y, CW * 0.50, 'Category NSV (₹ Cr)');
  s.addChart(pres.ChartType.bar, [{
    name: 'NSV', labels: CATS.map(c => c.cat), values: CATS.map(c => c.nsv)
  }], Object.assign({}, axisBase, {
    x: M, y: y + 0.22, w: CW * 0.50, h: 2.80,
    barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 45,
    chartColors: [TEAL, BLUE, BRIGHT, AMBER],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 8,
  }));

  chartTitle(s, M + CW * 0.52, y, CW * 0.48, 'Category unit share (%)');
  s.addChart(pres.ChartType.bar, [{
    name: 'Units %', labels: CATS.map(c => c.cat),
    values: CATS.map(c => +(c.units/CATS.reduce((a,x)=>a+x.units,0)*100).toFixed(1))
  }], Object.assign({}, axisBase, {
    x: M + CW * 0.52, y: y + 0.22, w: CW * 0.48, h: 2.80,
    barDir: 'col', barGrouping: 'clustered', barGapWidthPct: 45,
    chartColors: [TEAL, BLUE, BRIGHT, AMBER],
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 8,
  }));
  y += 3.04;

  table(s, { x: M, y, w: CW, cols: [
    { t: 'CATEGORY', w: 1.3 }, { t: 'NSV (₹ Cr)', w: 1.0, a: 'right' },
    { t: 'UNITS', w: 1.0, a: 'right' }, { t: 'NSV SHARE', w: 0.9, a: 'right' },
    { t: 'UNIT SHARE', w: 0.9, a: 'right' }, { t: 'SIGNAL', w: 2.6 }
  ], rows: [
    [{ t:'Face',b:true }, { t:'₹24.07',b:true }, { t:'1,451k' }, { t:'66.8%',b:true }, { t:'70.7%' }, 'NSV share < unit share → below-portfolio ASP. Mix opportunity: push premium face SKUs.'],
    [{ t:'Hair',b:true }, { t:'₹7.87',b:true },  { t:'337k' },   { t:'21.8%',b:true }, { t:'16.4%' }, { t:'NSV share > unit share → Hair ASP is above portfolio average. Premium positioning holding.', c:GREEN }],
    [{ t:'Body',b:true }, { t:'₹2.08',b:true },  { t:'125k' },   { t:'5.8%' },          { t:'6.1%' },  'Broadly in line. Monitor Body Care growth in South-1 (Apollo / Wellness).'],
    [{ t:'Baby',b:true }, { t:'₹1.91',b:true },  { t:'134k' },   { t:'5.3%' },          { t:'6.5%' },  { t:'NSV share < unit share → Baby packs are low-ASP. Category health, not a concern at 5.3%.', c:AMBER }],
  ], rowH: 0.38 });
  y += 0.28 + 4 * 0.38 + 0.14;

  s.addText('Face dominates volume and NSV but trades below Hair on ASP — within-Face premium mix (serum, sunscreen, TDC face) is the lever. Hair is the ASP champion: 16% of units, 22% of NSV.', txt({
    x: M, y, w: CW, h: 0.30, fontSize: 7.2, color: GREY, lineSpacingMultiple: 0.92 }));
}

/* ============================================================= SLIDE 10: eBIZ & SIS */
{
  const s = page(10, 'Sub-Channel View — eB2B (Nykaa/FSN) and SIS',
    'These accounts are in total MT NSV but excluded from geographic zone rollup');

  let y = BODY_Y;
  const hw = (CW - 0.16) / 2, hx = i => M + i * (hw + 0.16);

  // eB2B card
  const ey = card(s, { x: hx(0), y, w: hw, h: 5.80, label: 'eB2B — NYKAA / FSN', accent: BLUE });
  kpi(s, { x: hx(0)+0.10, y: ey, w: hw-0.20, h: 0.92, label: 'OFFTAKE NSV', value: '₹2.07 Cr',
    sub: '155,142 units sold through', accent: BLUE });
  kpi(s, { x: hx(0)+0.10, y: ey+1.02, w: hw-0.20, h: 0.92, label: 'ASP', value: '₹133.19',
    sub: '₹42 below geo-MT avg (₹175.76)', accent: BLUE });
  kpi(s, { x: hx(0)+0.10, y: ey+2.04, w: hw-0.20, h: 0.92, label: 'REALISATION', value: '57.4%',
    sub: 'Higher than geo-MT — lower MRP base', accent: GREEN });
  bullets(s, { x: hx(0)+0.16, y: ey+3.04, w: hw-0.32, gap: 0.44, size: 7.2, dot: BLUE, items: [
    { t: 'eB2B ASP is lower because Nykaa lists at competitive MRP; NSV after platform fees = ₹133 vs geo ₹176.', b: true },
    { t: 'Higher realisation % is structural: MRP on platform is lower, so NSV/MRP ratio improves. Do not benchmark against geo-MT realisation.' },
    { t: 'eB2B is 5.7% of MT NSV. No primary data in offtake source — cannot compute eB2B conversion from offtake-only view.' },
  ]});

  // SIS card
  const sy = card(s, { x: hx(1), y, w: hw, h: 5.80, label: 'SIS — SHOP-IN-SHOP', accent: AMBER });
  kpi(s, { x: hx(1)+0.10, y: sy, w: hw-0.20, h: 0.92, label: 'OFFTAKE NSV', value: '₹0.03 Cr',
    sub: '1,506 units · Azorte + SS + Lifestyle', accent: AMBER });
  kpi(s, { x: hx(1)+0.10, y: sy+1.02, w: hw-0.20, h: 0.92, label: 'ASP', value: '₹225.85',
    sub: 'Highest ASP in MT (premium shop formats)', accent: AMBER });
  kpi(s, { x: hx(1)+0.10, y: sy+2.04, w: hw-0.20, h: 0.92, label: 'SCALE', value: 'Rounding',
    sub: '₹0.03 Cr = directional only', accent: GREY });
  bullets(s, { x: hx(1)+0.16, y: sy+3.04, w: hw-0.32, gap: 0.44, size: 7.2, dot: AMBER, items: [
    { t: 'SIS formats (Azorte, Shoppers Stop, Broadway, Lifestyle, Today\'s Basket) sell premium — ASP ₹226 is the highest in MT.', b: true },
    { t: 'Volume is negligible in July (1,506 units). Treat as channel-presence data, not performance data, at this scale.' },
    { t: 'SIS offtake measurement may differ from retailer POS — the ₹0.03 Cr likely under-reports actual throughput.' },
  ]});
  y += 5.96;

  y = banner(s, y, 'CHANNEL ARCHITECTURE — WHAT IS AND IS NOT IN WHICH NUMBER', TEAL);
  table(s, { x: M, y, w: CW, cols: [
    { t: 'METRIC', w: 2.2 }, { t: 'GEO-MT ZONES', w: 1.5, a: 'center' },
    { t: 'eB2B', w: 1.2, a: 'center' }, { t: 'SIS', w: 1.2, a: 'center' },
    { t: 'TOTAL MT', w: 1.6, a: 'center' }
  ], rows: [
    ['Total MT NSV', { t:'₹33.95 Cr', c:TEAL }, { t:'₹2.07 Cr', c:BLUE }, { t:'₹0.03 Cr', c:AMBER }, { t:'₹36.05 Cr', b:true }],
    ['In zone rollup?', { t:'YES', c:GREEN }, { t:'NO', c:RED }, { t:'NO', c:RED }, '—'],
    ['ASP', { t:'₹175.72', c:TEAL }, { t:'₹133.19', c:RED }, { t:'₹225.85', c:GREEN }, { t:'₹175.76', b:true }],
    ['Realisation', '41.1–43.0%', { t:'57.4%', c:GREEN }, '49.5%', '42.8%'],
  ], rowH: 0.34 });
}

/* ============================================================= SLIDE 11: REALISATION */
{
  const s = page(11, 'Realisation Analysis — NSV ÷ MRP Value',
    'How much of shelf value reaches us as revenue · 42.8% national · zone spread 41–43%');

  let y = BODY_Y;

  // Realisation bar by zone
  chartTitle(s, M, y, CW, 'Realisation % by zone (geographic MT)');
  s.addChart(pres.ChartType.bar, [{
    name: 'Realisation %', labels: GEO_ZONES.map(z => z.z), values: GEO_ZONES.map(z => z.real)
  }], Object.assign({}, axisBase, {
    x: M, y: y + 0.22, w: CW, h: 2.00,
    barDir: 'bar', barGrouping: 'clustered', barGapWidthPct: 40,
    chartColors: GEO_ZONES.map(z => z.real < 41.5 ? RED : z.real > 43 ? GREEN : BRIGHT),
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 7.5,
    valAxisMinVal: 40, valAxisMaxVal: 44.5,
  }));
  y += 2.26;

  y = banner(s, y, 'WHAT REALISATION MEASURES AND HOW TO DIAGNOSE IT', TEAL);
  const hw2 = (CW - 0.16) / 2, hx2 = i => M + i * (hw2 + 0.16);
  const ry1 = card(s, { x: hx2(0), y, w: hw2, h: 3.60, label: 'THE FORMULA', accent: TEAL });
  bullets(s, { x: hx2(0)+0.10, y: ry1, w: hw2-0.20, gap: 0.50, size: 7.6, dot: TEAL, items: [
    { t: 'Realisation = NSV ÷ (Units × MRP per unit)', b: true },
    { t: 'It measures: how much of the sticker price we collect after all discounts, trade schemes, and deductions.' },
    { t: 'National: ₹36.06 Cr NSV ÷ ₹84.16 Cr MRP sales = 42.8%.' },
    { t: 'If realisation drops 100 bps (0.84 Cr) with flat MRP, it means ₹0.84 Cr more in trade deductions — investigate scheme structure.', c: AMBER },
    { t: 'South-2 has best geo-MT realisation (43.0%). Central is lowest (41.1%) — watch for markdown creep.', c: RED },
  ]});

  const ry2 = card(s, { x: hx2(1), y, w: hw2, h: 3.60, label: 'HOW TO DIAGNOSE A DIP', accent: BLUE });
  bullets(s, { x: hx2(1)+0.10, y: ry2, w: hw2-0.20, gap: 0.50, size: 7.6, dot: BLUE, items: [
    { t: 'Step 1 — Is it one zone or all zones? If all zones dip together = national scheme change.', b: true },
    { t: 'Step 2 — Is it one chain? Dmart low-ASP packs drag geo-MT realisation; Apollo high-margin pulls it up.' },
    { t: 'Step 3 — Is it one brand? TDC realisation > Mamaearth realisation (higher ASP, fewer discount packs).' },
    { t: 'Step 4 — Did MRP stay flat or rise? Rising MRP without rising NSV = discount deepened.' },
    { t: 'Trigger for action: if realisation drops >50 bps month-on-month in any single zone — escalate for trade-scheme review.', c: RED },
  ]});
  y += 3.76;

  y = banner(s, y, 'TREND — Apr → May → Jul REALISATION', BRIGHT);
  table(s, { x: M, y, w: CW, cols: [
    { t: 'MONTH', w: 1.2 }, { t: 'NSV (₹ Cr)', w: 1.2, a: 'right' },
    { t: 'MRP (₹ Cr)', w: 1.2, a: 'right' }, { t: 'REALISATION', w: 1.2, a: 'right' },
    { t: 'vs PREV MONTH', w: 1.4, a: 'right' }, { t: 'SIGNAL', w: 1.5 }
  ], rows: [
    ['Apr', '₹35.88', '₹84.6 (est)', { t:'42.4%' }, '—', 'Baseline'],
    ['May', '₹40.19', '₹95.1 (est)', { t:'42.3%' }, { t:'−0.1 pp', c:AMBER }, 'Marginal slip — within tolerance'],
    [{ t:'Jun', c:GREY }, { t:'—', c:GREY }, { t:'—', c:GREY }, { t:'ABSENT', c:GREY }, { t:'—', c:GREY }, { t:'No source data', c:GREY }],
    ['Jul', '₹36.06', '₹84.16', { t:'42.8%', c:GREEN, b:true }, { t:'+0.5 pp', c:GREEN }, 'Recovery — realisation improving despite lower NSV'],
  ], rowH: 0.32 });
}

/* ============================================================= SLIDE 12: DISTRIBUTION */
{
  const s = page(12, 'Distribution Productivity — WD, SPD and the ND Gap',
    'Weighted distribution from Nielsen · Numeric distribution not yet fed · 8-gate flag');

  let y = BODY_Y;

  // WD KPIs
  const kw3 = (CW - 0.20) / 3, kx3 = i => M + i * (kw3 + 0.10);
  kpi(s, { x: kx3(0), y, w: kw3, h: 0.92, label: 'FACE WASH WD', value: '89.0%',
    sub: '#4 category share · SPD #4 of 6', accent: TEAL });
  kpi(s, { x: kx3(1), y, w: kw3, h: 0.92, label: 'SHAMPOO WD', value: '81.5%',
    sub: '#6 share · SPD #6 of 6', accent: RED, valueColor: RED });
  kpi(s, { x: kx3(2), y, w: kw3, h: 0.92, label: 'ND STATUS', value: 'NOT FED',
    sub: 'Cannot compute WD ÷ ND (store quality)', accent: AMBER, valueColor: AMBER });
  y += 1.04;

  // SPD table
  y = banner(s, y, 'SHARE PER DISTRIBUTION POINT (SPD) — FACE WASH', TEAL);
  table(s, { x: M, y, w: CW, cols: [
    { t: 'BRAND', w: 1.5 }, { t: 'SHARE', w: 0.8, a: 'right' },
    { t: 'ND', w: 0.8, a: 'right' }, { t: 'WD', w: 0.80, a: 'right' },
    { t: 'SPD', w: 0.80, a: 'right' }, { t: 'NOTE', w: 3.0 }
  ], rows: [
    [{ t:'Garnier', b:true }, '14.2%', { t:'not fed', c:AMBER }, '90.3%', { t:'0.157', c:GREEN, b:true }, 'Reference benchmark (highest SPD)'],
    [{ t:'L\'Oréal', b:true },  '13.6%', { t:'not fed', c:AMBER }, '88.4%', { t:'0.154', c:GREEN }, ''],
    [{ t:'Pond\'s', b:true },   '12.4%', { t:'not fed', c:AMBER }, '88.1%', { t:'0.141' }, ''],
    [{ t:'Mamaearth', b:true }, '10.5%', { t:'not fed', c:AMBER }, '89.0%', { t:'0.118', c:RED, b:true }, 'Same shelf, 26% less share per point'],
    [{ t:'Nivea', b:true },     '10.2%', { t:'not fed', c:AMBER }, '85.2%', { t:'0.120' }, ''],
    [{ t:'CeraVe', b:true },    { t:'8.9%', c:AMBER }, { t:'not fed', c:AMBER }, '72.3%', { t:'0.123' }, 'Lower WD — partial distribution'],
    [{ t:'ND — ALL', b:true, c:AMBER }, { t:'—', c:GREY }, { t:'NOT YET FED', c:RED, b:true }, { t:'—', c:GREY }, { t:'—', c:GREY },
      { t:'PowerBI/RawDataFolders/TDP_Monthly/ is empty. ND cannot be computed until TDP feed is supplied.', c:RED }],
  ], rowH: 0.33 });
  y += 0.28 + 7 * 0.33 + 0.12;

  // Decomposition
  y = banner(s, y, 'THE DECOMPOSITION WE CANNOT YET COMPLETE', AMBER);
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 1.60, rectRadius: 0.03,
    fill: { color: W }, line: { color: AMBER, width: 1.5 } });
  s.addText('share  =  ND  ×  (WD ÷ ND)  ×  (share ÷ WD)', txt({
    x: M + 0.20, y: y + 0.14, w: CW - 0.40, h: 0.36, fontSize: 14, bold: true,
    fontFace: FONTH, color: INK, align: 'center' }));
  s.addText('         reach    store quality      velocity per shelf point', txt({
    x: M + 0.20, y: y + 0.50, w: CW - 0.40, h: 0.20, fontSize: 8.5, color: GREY, align: 'center', italic: true }));
  s.addText('We hold WD (89.0% Face Wash · 81.5% Shampoo). We do not hold ND. Without ND we cannot tell whether 89% WD means "in most stores" or "in a few very large stores". The store-quality term (WD ÷ ND) is the discriminator. SPD reported here is only the third term — the velocity — and is a hand-cut stand-in for the MS vs TDP Index already written in PowerBI/DAX/05_TDP_Measures.dax, which cannot run until the TDP feed is supplied.', txt({
    x: M + 0.20, y: y + 0.76, w: CW - 0.40, h: 0.72, fontSize: 7.2, color: INK, lineSpacingMultiple: 0.94 }));
  y += 1.72;

  y = banner(s, y, 'WHAT IS NEEDED TO COMPLETE THIS', RED);
  bullets(s, { x: M + 0.10, y: y + 0.06, w: CW - 0.20, gap: 0.42, size: 7.6, dot: RED, items: [
    { t: 'Supply TDP_Monthly/ CSV with ND column → unlocks MS vs TDP Index in DAX (already written).', b: true },
    { t: 'Supply Nielsen_Monthly/ CSV with Volume Market Share → unlocks value vs volume divergence check (already in DAX).' },
    { t: 'See docs/NIELSEN_DATA_REQUEST.md for column-for-column feed specification vs the two existing templates.' },
    { t: 'Until ND is fed, report SPD only with this provenance note: "SPD is WD-only — store quality arm is missing."', c: AMBER },
  ]});
}

/* ============================================================= SLIDE 13: 8-GATE VALIDATION */
{
  const s = page(13, 'Methodology — 8-Gate Validation & Pattern-Matcher-Router',
    'All figures in this deck passed pre-flight quality gates before generation');

  let y = BODY_Y;

  y = banner(s, y, 'PRE-FLIGHT VALIDATION SUMMARY — Jul-26 (python scripts/validation_gates.py --month Jul-26)', TEAL);
  table(s, { x: M, y, w: CW, cols: [
    { t: '#', w: 0.3 }, { t: 'GATE', w: 1.8 }, { t: 'STATUS', w: 0.9, a: 'center' },
    { t: 'DETAIL', w: 4.0 }
  ], rows: [
    ['1', 'Source Verified',       { t:'PASS ✓', c:GREEN, b:true },  'Offtake CSV 73 MB · channel_master.json present'],
    ['2', 'Time Period Clear',     { t:'PASS ✓', c:GREEN, b:true },  'Jul-26 → FY27 (THE ONE FY RULE: month 7 ≥ 4 → FY year+1)'],
    ['3', 'Scope Bounded',         { t:'PASS ✓', c:GREEN, b:true },  'Brand Counter excluded · Discontinued brands excluded (Lumineve, Pure Origin, Staze)'],
    ['4', 'Reconciliation Tied',   { t:'FLAG ⚑', c:AMBER, b:true }, 'PASS WITH WARNINGS — zone×channel primary not derivable from data.js (Tier 2, carry-forward)'],
    ['5', 'Bad Rows Assessed',     { t:'PASS ✓', c:GREEN, b:true },  '0 bad NSV rows / 220,522 total (0.0000%)'],
    ['6', 'Calculation Verified',  { t:'PASS ✓', c:GREEN, b:true },  'Σzone.primary = mt.primary · offtake identity · benchmark 85.73% ✓'],
    ['7', 'Confidence Assessment', { t:'PASS ✓', c:GREEN, b:true },  '₹6.22 Cr recoverable above ₹0.25 Cr floor · 3 FY27 months · HIGH confidence'],
    ['8', 'Error Cost Assessment', { t:'PASS ✓', c:GREEN, b:true },  'Diagnostic type: balanced precision/recall, HIGH confidence threshold met'],
  ], rowH: 0.36 });
  y += 0.28 + 8 * 0.36 + 0.12;

  y = banner(s, y, 'PATTERN-MATCHER-ROUTER — 5-PHASE INSIGHT CYCLE APPLIED', BLUE);
  const c2w = (CW - 0.14) / 2, c2x = i => M + i * (c2w + 0.14);
  const ly = card(s, { x: c2x(0), y, w: c2w, h: 3.20, label: '5-PHASE CYCLE (ASK→SHARE)', accent: BLUE });
  bullets(s, { x: c2x(0)+0.10, y: ly, w: c2w-0.20, gap: 0.48, size: 7.2, dot: BLUE, items: [
    { t: 'ASK: "Where is Jul offtake soft and why?" → Diagnostic type → balanced FP/FN.' },
    { t: 'PREPARE: Offtake CSV gated (0 bad rows, Brand Counter excluded, ND absent flagged).' },
    { t: 'EXPLORE: Univariate (national) → Bivariate (zone/brand) → Multivariate (zone×brand×chain).' },
    { t: 'ANALYZE: Root cause = volume contraction (−293k units) not pricing (ASP +₹4.32). HIGH confidence.' },
    { t: 'SHARE: One headline per slide · one chart · one action.' },
  ]});

  const ry = card(s, { x: c2x(1), y, w: c2w, h: 3.20, label: 'TRIAGE — 3-TIER CARRY-FORWARDS', accent: AMBER });
  bullets(s, { x: c2x(1)+0.10, y: ry, w: c2w-0.20, gap: 0.56, size: 7.2, dot: AMBER, items: [
    { t: 'TIER 1 (Fixed): benchConv corrected from 85.5% → 85.73%; zone contamination patch applied.', b: true, c: GREEN },
    { t: 'TIER 2 (Documented here): Zone×channel primary not exact from data.js — requires full source workbook. June 2026 absent.', c: AMBER },
    { t: 'TIER 3 (Placeholder): Nielsen_Monthly/ empty → ND, volume share, category MS not fed. TDP_Monthly/ empty → MS vs TDP Index cannot run.', c: RED },
  ]});
}

/* ============================================================= SLIDE 14: ACTIONS */
{
  const s = page(14, 'Key Actions — July Offtake Findings',
    'Prioritised by impact · Owner assigned · August review trigger');

  let y = BODY_Y;

  y = banner(s, y, 'PATTERN-MATCHER-ROUTER VERDICT — JULY 2026 OFFTAKE', GREEN);
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.54, rectRadius: 0.03,
    fill: { color: W }, line: { color: GREEN, width: 1.2 } });
  s.addText('HEADLINE: July NSV −4.1 Cr vs May is 100% volume-driven (−293k units). ASP rose ₹4.32. Pricing is healthy. Fix unit velocity, not price.', txt({
    x: M + 0.14, y: y + 0.07, w: CW - 0.28, h: 0.40, fontSize: 8.5, bold: true,
    color: GREEN, fontFace: FONTH, lineSpacingMultiple: 0.92 }));
  y += 0.66;

  const actions = [
    { n:'1', priority:'P1', label:'DIAGNOSE WEST VOLUME DIP', accent: RED,
      context: 'West is 23% of geo-MT NSV but holds lowest ASP (₹166). High unit volume is its contribution — any slip here outsizes all zones.',
      action: 'Pull West chain-level units for Jul vs May. Quantify how many units are Dmart vs Reliance vs Apollo. Is it Dmart receiving less primary, or Reliance velocity slipping?',
      owner: 'West RSM · 25 Aug', metric: 'West units Aug ≥ May (497k baseline)' },
    { n:'2', priority:'P1', label:'PUSH PREMIUM MIX INSIDE DMART', accent: RED,
      context: 'Dmart = 38.8% of geo-MT (₹13.97 Cr) but lowest chain ASP (₹158). TDC and Aqualogica under-represented vs national.',
      action: 'Review TDC SKU listing in Dmart. Target TDC share of Dmart NSV from current level to ≥12% (vs 30.6% national TDC share). One new TDC face SKU in Dmart by Sept.',
      owner: 'National KAM Dmart · 31 Aug', metric: 'TDC Dmart NSV share: current → target 12%' },
    { n:'3', priority:'P2', label:'CENTRAL ZONE — REALISATION WATCH', accent: AMBER,
      context: 'Central realisation 41.1% = lowest geo-MT zone (national 42.8%, South-2 43.0%). Not yet at trigger threshold but trending.',
      action: 'Month-on-month realisation tracking for Central. If Aug realisation < 40.5% — trigger trade-scheme audit for MP/CG. Otherwise monitor.',
      owner: 'Central RSM + Trade Marketing · 15 Sep', metric: 'Central realisation Aug ≥ 40.5%' },
    { n:'4', priority:'P2', label:'AQUALOGICA — SCALE UP HIGH-ASP', accent: BLUE,
      context: 'Aqualogica ASP ₹235 is the highest brand in portfolio (vs ₹170 MEA, ₹188 TDC). Share is 1.3% — early stage.',
      action: 'Identify 2 chains where Aqualogica can expand listing (Apollo, Wellness Forever are pharmacy-format and premium-receptive). Add 3 SKUs in these chains by Q2 end.',
      owner: 'Brand Analyst + KAM · 15 Sep', metric: 'Aqualogica MT NSV ≥ ₹0.60 Cr by Oct' },
    { n:'5', priority:'P3', label:'FEED THE NIELSEN & TDP PIPES', accent: GREY,
      context: 'ND, volume share, MS vs TDP Index and the full decomposition (share = ND × store-quality × SPD) cannot run. Three DAX measures and two DAX tables are built and empty.',
      action: 'Supply TDP_Monthly/ and Nielsen_Monthly/ CSVs per docs/NIELSEN_DATA_REQUEST.md. Drop in PowerBI/RawDataFolders/, refresh. No mapping work needed — templates are column-for-column.',
      owner: 'Data team · 30 Sep', metric: 'validation_gates.py Gate 1: ND file present' },
  ];

  actions.forEach((a, i) => {
    const ay = card(s, { x: M, y, w: CW, h: 1.88, label: `${a.n}  ${a.label}  [${a.priority}]`, accent: a.accent });
    const cw3 = (CW - 0.28) / 3;
    s.addText('CONTEXT', txt({ x: M+0.10, y: ay, w: cw3, h: 0.18, color: GREY, fontSize: 6.5, bold: true, charSpacing: 0.4 }));
    s.addText(a.context, txt({ x: M+0.10, y: ay+0.20, w: cw3-0.06, h: 0.68, fontSize: 7.0, color: INK, lineSpacingMultiple: 0.92 }));
    s.addText('ACTION', txt({ x: M+0.10+cw3+0.06, y: ay, w: cw3, h: 0.18, color: GREY, fontSize: 6.5, bold: true, charSpacing: 0.4 }));
    s.addText(a.action, txt({ x: M+0.10+cw3+0.06, y: ay+0.20, w: cw3-0.06, h: 0.68, fontSize: 7.0, color: INK, lineSpacingMultiple: 0.92 }));
    s.addText('OWNER · METRIC', txt({ x: M+0.10+2*cw3+0.12, y: ay, w: cw3, h: 0.18, color: GREY, fontSize: 6.5, bold: true, charSpacing: 0.4 }));
    s.addText(`${a.owner}\n${a.metric}`, txt({ x: M+0.10+2*cw3+0.12, y: ay+0.20, w: cw3-0.10, h: 0.68, fontSize: 7.0, color: INK, lineSpacingMultiple: 0.92 }));
    y += 2.00;
  });
}

/* ============================================================= WRITE */
const OUT = 'July_MT_Offtake_Command_Centre.pptx';
pres.writeFile({ fileName: OUT }).then(() => console.log('written:', OUT));
