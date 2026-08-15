#!/usr/bin/env node
/**
 * scripts/export_slides.js
 * Generates MT_Leadership_Report.pptx from dashboard/data.js
 * Usage: node scripts/export_slides.js [--out <path>]
 */
'use strict';
const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');

const outIdx = process.argv.indexOf('--out');
const OUT = outIdx >= 0 ? process.argv[outIdx + 1]
  : path.join(__dirname, '../MT_Leadership_Report.pptx');

// Load data.js — replace bare NaN/Infinity which aren't valid JSON
const raw = fs.readFileSync(path.join(__dirname, '../dashboard/data.js'), 'utf8');
const s0 = raw.indexOf('{'), s1 = raw.lastIndexOf('}');
const jsonStr = raw.slice(s0, s1 + 1)
  .replace(/\bNaN\b/g, 'null')
  .replace(/\bInfinity\b/g, 'null')
  .replace(/-null/g, 'null');
const D = JSON.parse(jsonStr);

// Formatters
const cr  = v => '₹' + (v / 100).toFixed(1) + ' Cr';
const sgn = v => (v >= 0 ? '+' : '') + v.toFixed(1) + '%';
const pct = v => v.toFixed(1) + '%';
const fmt = (v, dec) => v.toLocaleString('en-IN', { maximumFractionDigits: dec || 0 });

// Palette — no # prefix (pptxgenjs requirement)
const P = {
  navy:    '0D1F2D',
  teal:    '028090',
  tealLt:  'E0F3F5',
  amber:   'D97706',
  amberLt: 'FEF3C7',
  green:   '1E8E3E',
  greenLt: 'D1FAE5',
  red:     'C0392B',
  redLt:   'FDE8E8',
  white:   'FFFFFF',
  offW:    'F8FAFB',
  charcoal:'2D3748',
  grey:    '718096',
  lgrey:   'E2E8F0',
  mgrey:   '9AA4AD',
  icegrey: 'CADCFC',
  navyMid: '162736',
};

// ── Data extraction ──────────────────────────────────────────────────────────
const pr     = D.primary   || {};
const tot    = D.tot       || {};
const fc     = D.forecast  || {};
const fcDet  = fc.detail   || {};
const promo  = D.promo     || {};
const promoD = promo.detail || {};
const ins    = (D.insights || []).slice(0, 6);

const nsv26    = pr.nsv_fy26 || 0;
const yoy      = pr.yoy      != null ? pr.yoy : null;
const fy27Fc   = fc.fy27_forecast || 0;
const growth   = fc.growth_assumption_pct || 0;
const totPass  = tot.total_passon_value   || 0;
const blTot    = tot.blended_tot_pct      || 0;

// Q2-Q3 pipeline
const q2q3 = (() => {
  const q2q3Months = ['Sep-26','Oct-26','Nov-26','Dec-26'];
  const byMonth = fcDet.by_month || [];
  const sum = byMonth.filter(m => q2q3Months.includes(m.month)).reduce((a,m) => a + (m.total||0), 0);
  return sum || (fcDet.q2_q3_total || 0);
})();

// Brand data
const allBrands = (pr.by_brand || []);
const brandsSig = allBrands.filter(b => (b.fy26||0) > 20).slice(0, 6);

// Chain data
const topChains = (tot.by_chain || [])
  .sort((a,b) => (b.passon_value||0) - (a.passon_value||0))
  .slice(0, 8);

// Category waterfall
const catWf = (tot.by_category || [])
  .filter(c => (c.mrp||0) > 0)
  .map(c => ({
    name: c.name,
    nsv_pct: +(c.nsv / c.mrp * 100).toFixed(1),
    tax_pct: +(c.tax / c.mrp * 100).toFixed(1),
    tot_pct: c.tot_pct || 0,
    nsv: c.nsv || 0,
  }))
  .sort((a,b) => b.tot_pct - a.tot_pct);

// Forecast by month — data is stored in parallel arrays
const fcMonthLabels = fcDet.months || [];
const fcMonthVals   = fcDet.monthly_forecast || fcDet.monthly_target || [];
const fcBrands = (fcDet.by_brand || []).filter(b => (b.total||0) > 10).slice(0, 6);

// Promo
const promoSkus    = promoD.total_skus    || 0;
const promoBrands  = promoD.brands_in_promo || 0;
const promoChainIn = promoD.chains_in_promo || 0;
const promoRecvd   = promoD.chains_received || 0;
const promoPend    = promoD.chains_pending  || 0;
const promoMonth   = promoD.month          || 'Aug-26';
const kamStatus    = promoD.kam_status     || {};
const byBrand      = promoD.by_brand       || [];
const meaEarth     = byBrand.find(b => b.name === 'Mamaearth');
const pendingChains= Array.isArray(kamStatus.pending) ? kamStatus.pending : [];

// Insight cards
const insCards = ins.length > 0 ? ins : [
  { title: 'FY26 Record NSV', text: 'Primary NSV reached ₹329 Cr, growing 41% YoY driven by Mamaearth and TDC.' },
  { title: 'TOT Efficiency Risk', text: 'Blended TOT at 50% — Dmart and Apollo accounts above category average.' },
  { title: 'FY27 Runway', text: 'Target ₹441 Cr requires 42% growth. Q2-Q3 pipeline at ₹107 Cr.' },
  { title: 'TDC Scale Opportunity', text: 'The Derma Co +161% YoY in FY26 — largest growth brand in MT channel.' },
  { title: 'Promo Sheet Gaps', text: '7 chains yet to submit Aug-26 promo sheets — KAM escalation needed.' },
  { title: 'Category Mix', text: 'Face and Body drive 60%+ NSV. Baby fastest growing at lowest TOT%.' },
];

// ── PPTX init ────────────────────────────────────────────────────────────────
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.3" × 7.5"
pres.author = 'Honasa Consumer Ltd. — MT Analytics';
pres.title  = 'Modern Trade Leadership Report';

// ── Shared helpers ───────────────────────────────────────────────────────────
function kpiBox(slide, x, y, w, h, val, label, sub, bg, fg) {
  slide.addShape(pres.ShapeType.roundRect, {
    x, y, w, h,
    fill: { color: bg },
    line: { color: bg, width: 0 },
    rectRadius: 0.08,
  });
  slide.addText(val, {
    x, y: y + 0.06, w, h: h * 0.52,
    fontSize: 22, bold: true, color: fg,
    align: 'center', valign: 'middle', margin: 0,
  });
  slide.addText(label, {
    x, y: y + h * 0.52, w, h: h * 0.28,
    fontSize: 9.5, bold: false, color: fg,
    align: 'center', valign: 'top', margin: 0,
  });
  if (sub) {
    slide.addText(sub, {
      x, y: y + h * 0.76, w, h: h * 0.24,
      fontSize: 8.5, bold: true, color: fg,
      align: 'center', valign: 'middle', margin: 0,
    });
  }
}

function sectionLabel(slide, x, y, w, text) {
  slide.addText(text.toUpperCase(), {
    x, y, w, h: 0.22,
    fontSize: 8, bold: true, color: P.grey,
    align: 'left', margin: 0,
    charSpacing: 1.5,
  });
}

function slideHeader(slide, title, subtitle) {
  slide.addText(title, {
    x: 0.4, y: 0.15, w: 12.5, h: 0.5,
    fontSize: 22, bold: true, color: P.navy,
    align: 'left', margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.4, y: 0.65, w: 12.5, h: 0.25,
      fontSize: 11, bold: false, color: P.grey,
      align: 'left', margin: 0,
    });
  }
  // Thin separator line
  slide.addShape(pres.ShapeType.line, {
    x: 0.4, y: 0.94, w: 12.5, h: 0,
    line: { color: P.lgrey, width: 1.2 },
  });
}

function addFooter(slide, pageNum) {
  slide.addText('Honasa Consumer Ltd. — Modern Trade Analytics  |  Confidential', {
    x: 0.4, y: 7.22, w: 11, h: 0.2,
    fontSize: 7.5, color: P.mgrey, align: 'left', margin: 0,
  });
  slide.addText(String(pageNum), {
    x: 12.6, y: 7.22, w: 0.5, h: 0.2,
    fontSize: 7.5, color: P.mgrey, align: 'right', margin: 0,
  });
}

// ── SLIDE 1: Cover ───────────────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  // Dark navy background
  sl.addShape(pres.ShapeType.rect, {
    x: 0, y: 0, w: 13.3, h: 7.5,
    fill: { color: P.navy },
    line: { color: P.navy, width: 0 },
  });

  // Decorative teal circle (partially off-slide, bottom-right)
  sl.addShape(pres.ShapeType.ellipse, {
    x: 10.8, y: 5.2, w: 4.2, h: 4.2,
    fill: { color: P.teal, transparency: 82 },
    line: { color: P.teal, width: 0 },
  });
  sl.addShape(pres.ShapeType.ellipse, {
    x: 11.9, y: 5.9, w: 2.6, h: 2.6,
    fill: { color: P.teal, transparency: 70 },
    line: { color: P.teal, width: 0 },
  });

  // Small teal accent bar (top-left)
  sl.addShape(pres.ShapeType.rect, {
    x: 0.5, y: 1.8, w: 0.06, h: 2.2,
    fill: { color: P.teal },
    line: { color: P.teal, width: 0 },
  });

  // Eyebrow
  sl.addText('HONASA CONSUMER LTD.', {
    x: 0.75, y: 1.82, w: 9, h: 0.3,
    fontSize: 10, bold: true, color: P.teal,
    align: 'left', margin: 0, charSpacing: 2,
  });

  // Main title
  sl.addText('Modern Trade', {
    x: 0.75, y: 2.18, w: 10, h: 0.9,
    fontSize: 54, bold: true, color: P.white,
    align: 'left', margin: 0,
  });
  sl.addText('Leadership Report', {
    x: 0.75, y: 3.08, w: 10.5, h: 0.9,
    fontSize: 48, bold: false, color: P.icegrey,
    align: 'left', margin: 0,
  });

  // Subtitle
  sl.addText('Category Margins · Trade Spend Efficiency · Forecast Highlights', {
    x: 0.75, y: 4.1, w: 10, h: 0.32,
    fontSize: 14, bold: false, color: P.mgrey,
    align: 'left', margin: 0,
  });

  // Date & FY
  const today = new Date();
  const dateStr = today.toLocaleDateString('en-IN', { year: 'numeric', month: 'long', day: 'numeric' });
  sl.addText('FY26 Actuals · FY27 Pipeline  ·  ' + dateStr, {
    x: 0.75, y: 6.7, w: 9, h: 0.28,
    fontSize: 10, bold: false, color: P.mgrey,
    align: 'left', margin: 0,
  });
}

// ── SLIDE 2: FY26 Performance Overview ───────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: P.offW };
  slideHeader(sl, 'FY26 Performance Overview', 'Primary NSV · Channel Economics · Brand Contribution');
  addFooter(sl, 2);

  // 4 KPI boxes
  const kpiY = 1.05, kpiH = 1.28, kpiW = 2.95, kpiGap = 0.12;
  const nsvYoy = yoy != null ? sgn(yoy) : '';
  kpiBox(sl, 0.4,           kpiY, kpiW, kpiH, cr(nsv26),  'Primary NSV FY26',     nsvYoy ? nsvYoy + ' YoY' : '', P.teal,    P.white);
  kpiBox(sl, 0.4 + (kpiW + kpiGap),     kpiY, kpiW, kpiH, cr(fy27Fc),  'FY27 Target',          growth ? '+' + growth.toFixed(0) + '% growth' : '', P.navy, P.white);
  kpiBox(sl, 0.4 + 2*(kpiW + kpiGap),   kpiY, kpiW, kpiH, cr(totPass), 'Channel Passon',       pct(blTot) + ' blended TOT', P.amber, P.white);
  kpiBox(sl, 0.4 + 3*(kpiW + kpiGap),   kpiY, kpiW, kpiH, cr(q2q3),    'Q2–Q3 Pipeline',  'Sep–Dec-26', P.green, P.white);

  // Brand comparison chart
  if (brandsSig.length > 0) {
    sectionLabel(sl, 0.4, 2.5, 12.5, 'Brand NSV Contribution — FY25 vs FY26 (₹ Lakhs)');
    const bNames = brandsSig.map(b => b.name);
    const bFy25  = brandsSig.map(b => Math.round(b.fy25 || 0));
    const bFy26  = brandsSig.map(b => Math.round(b.fy26 || 0));
    sl.addChart(pres.ChartType.bar, [
      { name: 'FY25', labels: bNames, values: bFy25 },
      { name: 'FY26', labels: bNames, values: bFy26 },
    ], {
      x: 0.4, y: 2.72, w: 12.5, h: 4.45,
      barDir: 'col',
      barGrouping: 'clustered',
      chartColors: [P.icegrey, P.teal],
      showLegend: true, legendPos: 't',
      legendFontSize: 9,
      showValue: true, dataLabelFontSize: 8,
      dataLabelPosition: 'outEnd',
      dataLabelColor: P.charcoal,
      valAxisMaxVal: Math.ceil(Math.max(...bFy26) * 1.3 / 500) * 500,
      valAxisLabelFontSize: 9, catAxisLabelFontSize: 9,
      valGridLine: { color: P.lgrey, style: 'solid', size: 0.8 },
      catGridLine: { style: 'none' },
      valAxisLabelColor: P.grey,
      catAxisLabelColor: P.charcoal,
      showTitle: false,
      plotAreaBorderColor: P.offW,
      chartAreaBorderColor: P.offW,
      fill: P.offW,
    });
  }
}

// ── SLIDE 3: Category Margin Analysis ────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: P.offW };
  slideHeader(sl, 'Category Margin Waterfall', 'MRP split: NSV% + Tax% + TOT% — sorted by trade discount (TOT%)');
  addFooter(sl, 3);

  if (catWf.length > 0) {
    // Stacked horizontal bar chart (left 8.2")
    sectionLabel(sl, 0.4, 1.05, 8.0, 'MRP Composition by Category (% of face MRP)');
    const cNames = catWf.map(c => c.name);
    sl.addChart(pres.ChartType.bar, [
      { name: 'NSV%',  labels: cNames, values: catWf.map(c => c.nsv_pct) },
      { name: 'Tax%',  labels: cNames, values: catWf.map(c => c.tax_pct) },
      { name: 'TOT%',  labels: cNames, values: catWf.map(c => c.tot_pct) },
    ], {
      x: 0.4, y: 1.28, w: 8.2, h: 5.9,
      barDir: 'bar',
      barGrouping: 'stacked',
      chartColors: [P.teal, P.mgrey, P.amber],
      showLegend: true, legendPos: 't', legendFontSize: 9,
      showValue: true, dataLabelFontSize: 7.5,
      dataLabelPosition: 'ctr',
      dataLabelColor: P.white,
      valAxisMaxVal: 100,
      valAxisLabelFontSize: 9, catAxisLabelFontSize: 9,
      valGridLine: { color: P.lgrey, style: 'solid', size: 0.8 },
      catGridLine: { style: 'none' },
      valAxisLabelColor: P.grey,
      catAxisLabelColor: P.charcoal,
      showTitle: false,
      plotAreaBorderColor: P.offW,
      chartAreaBorderColor: P.offW,
      fill: P.offW,
    });

    // Right column callout boxes
    sectionLabel(sl, 8.8, 1.05, 4.3, 'Key Observations');
    const highest = catWf[0];
    const lowest  = catWf[catWf.length - 1];
    const byNSV   = [...catWf].sort((a,b) => b.nsv - a.nsv);
    const obsBoxes = [
      { icon: '⚠', color: P.amber, bg: P.amberLt, title: 'Highest TOT%', text: (highest?.name || '') + ' at ' + pct(highest?.tot_pct || 0) + ' — review trade terms' },
      { icon: '✔', color: P.teal,  bg: P.tealLt,  title: 'Largest NSV',  text: (byNSV[0]?.name || '') + ' ' + cr(byNSV[0]?.nsv || 0) + ' — core revenue driver' },
      { icon: '✔', color: P.green, bg: P.greenLt, title: 'Most Efficient',text: (lowest?.name || '') + ' lowest TOT at ' + pct(lowest?.tot_pct || 0) },
      { icon: 'ℹ', color: P.grey,  bg: P.lgrey,   title: 'Blended TOT',   text: 'Portfolio blended TOT ' + pct(blTot) + ' — significant margin leakage' },
    ];
    obsBoxes.forEach((o, i) => {
      const bx = 8.8, by = 1.3 + i * 1.55, bw = 4.3, bh = 1.42;
      sl.addShape(pres.ShapeType.roundRect, {
        x: bx, y: by, w: bw, h: bh,
        fill: { color: o.bg }, line: { color: o.bg, width: 0 }, rectRadius: 0.07,
      });
      sl.addText(o.icon, {
        x: bx + 0.12, y: by + 0.08, w: 0.38, h: 0.38,
        fontSize: 16, bold: true, color: o.color, align: 'center', margin: 0,
      });
      sl.addText(o.title, {
        x: bx + 0.56, y: by + 0.08, w: bw - 0.68, h: 0.35,
        fontSize: 10, bold: true, color: P.charcoal, align: 'left', margin: 0,
      });
      sl.addText(o.text, {
        x: bx + 0.12, y: by + 0.5, w: bw - 0.24, h: 0.84,
        fontSize: 9, bold: false, color: P.charcoal, align: 'left', margin: 0,
        wrap: true,
      });
    });
  }
}

// ── SLIDE 4: Trade Spend Analysis ────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: P.offW };
  slideHeader(sl, 'Trade Spend & Channel Economics', 'Passon value by chain · TOT% benchmarking · Efficiency matrix');
  addFooter(sl, 4);

  if (topChains.length > 0) {
    // Horizontal bar — passon value
    sectionLabel(sl, 0.4, 1.05, 8.0, 'Passon Value by Chain (₹ Lakhs)');
    const chn = topChains.map(c => c.chain || c.name || '');
    const pv  = topChains.map(c => Math.round(c.passon_value || 0));
    sl.addChart(pres.ChartType.bar, [
      { name: 'Passon (₹L)', labels: chn, values: pv },
    ], {
      x: 0.4, y: 1.28, w: 8.2, h: 5.9,
      barDir: 'bar',
      barGrouping: 'clustered',
      chartColors: [P.teal],
      showLegend: false,
      showValue: true, dataLabelFontSize: 8.5,
      dataLabelPosition: 'inEnd',
      dataLabelColor: P.white,
      valAxisLabelFontSize: 9, catAxisLabelFontSize: 9.5,
      valGridLine: { color: P.lgrey, style: 'solid', size: 0.8 },
      catGridLine: { style: 'none' },
      valAxisLabelColor: P.grey,
      catAxisLabelColor: P.charcoal,
      showTitle: false,
      plotAreaBorderColor: P.offW,
      chartAreaBorderColor: P.offW,
      fill: P.offW,
    });

    // Right: KPI + chain table
    sectionLabel(sl, 8.8, 1.05, 4.3, 'TOT% Benchmarking');

    // Blended TOT KPI box
    kpiBox(sl, 8.8, 1.28, 4.3, 1.2, pct(blTot), 'Blended TOT%', cr(totPass) + ' total passon', P.amber, P.white);

    // Chain table header
    const tblX = 8.8, tblY = 2.6, tblW = 4.3;
    sectionLabel(sl, tblX, tblY, tblW, 'Chain  |  TOT%  |  Passon (₹L)');
    sl.addShape(pres.ShapeType.line, {
      x: tblX, y: tblY + 0.22, w: tblW, h: 0,
      line: { color: P.lgrey, width: 0.9 },
    });

    const rowH = 0.44;
    const startY = tblY + 0.26;
    topChains.forEach((c, i) => {
      const ry = startY + i * rowH;
      if (ry + rowH > 7.1) return;
      const bg = i % 2 === 0 ? P.white : P.offW;
      sl.addShape(pres.ShapeType.rect, {
        x: tblX, y: ry, w: tblW, h: rowH,
        fill: { color: bg }, line: { color: bg, width: 0 },
      });
      const totPct  = c.tot_pct  != null ? pct(c.tot_pct)  : '—';
      const pv2     = c.passon_value != null ? fmt(Math.round(c.passon_value)) : '—';
      const label   = (c.chain || c.name || '').slice(0, 18);
      sl.addText(label, {
        x: tblX + 0.08, y: ry + 0.04, w: 1.9, h: rowH - 0.08,
        fontSize: 8.5, color: P.charcoal, align: 'left', margin: 0,
      });
      sl.addText(totPct, {
        x: tblX + 2.0, y: ry + 0.04, w: 0.85, h: rowH - 0.08,
        fontSize: 8.5, color: P.amber, bold: true, align: 'right', margin: 0,
      });
      sl.addText(pv2, {
        x: tblX + 2.87, y: ry + 0.04, w: 1.35, h: rowH - 0.08,
        fontSize: 8.5, color: P.charcoal, align: 'right', margin: 0,
      });
    });
  }
}

// ── SLIDE 5: Aug-26 Promo Calendar ───────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: P.offW };
  slideHeader(sl, promoMonth + ' Promo Calendar', 'SKU counts · chain coverage · KAM status');
  addFooter(sl, 5);

  // 4 KPI boxes
  const kpiY = 1.05, kpiH = 1.2, kpiW = 2.95, kpiGap = 0.12;
  const meaAvgOff = meaEarth ? (meaEarth.avg_offer_pct != null ? pct(meaEarth.avg_offer_pct) : '') : '';
  kpiBox(sl, 0.4,                         kpiY, kpiW, kpiH, String(promoSkus),    'SKUs in Promo',       promoMonth, P.teal, P.white);
  kpiBox(sl, 0.4 + (kpiW + kpiGap),       kpiY, kpiW, kpiH, String(promoBrands),  'Brands Participating', '', P.navy, P.white);
  kpiBox(sl, 0.4 + 2*(kpiW + kpiGap),     kpiY, kpiW, kpiH, promoRecvd + '/' + promoChainIn, 'KAM Responses',  'of chains in promo', P.green, P.white);
  kpiBox(sl, 0.4 + 3*(kpiW + kpiGap),     kpiY, kpiW, kpiH, meaAvgOff || pct(blTot), meaEarth ? 'Mamaearth Avg Offer' : 'Blended TOT%', '', P.amber, P.white);

  // Brand participation table (left)
  sectionLabel(sl, 0.4, 2.4, 7.8, 'Brand Participation  —  ' + promoMonth);
  const bTblX = 0.4, bTblY = 2.62;
  // header row
  sl.addShape(pres.ShapeType.rect, {
    x: bTblX, y: bTblY, w: 7.8, h: 0.36,
    fill: { color: P.navy }, line: { color: P.navy, width: 0 },
  });
  ['Brand', 'SKUs', 'Chains', 'Avg Offer%'].forEach((h, i) => {
    const xs = [0.08, 2.5, 3.9, 5.5];
    const ws = [2.35, 1.3, 1.5, 2.2];
    const aligns = ['left', 'right', 'right', 'right'];
    sl.addText(h, {
      x: bTblX + xs[i], y: bTblY + 0.04, w: ws[i], h: 0.28,
      fontSize: 8.5, bold: true, color: P.white, align: aligns[i], margin: 0,
    });
  });
  const bRows = byBrand.length > 0 ? byBrand : [];
  bRows.slice(0, 7).forEach((b, i) => {
    const ry = bTblY + 0.36 + i * 0.44;
    const bg = i % 2 === 0 ? P.white : P.offW;
    sl.addShape(pres.ShapeType.rect, {
      x: bTblX, y: ry, w: 7.8, h: 0.44,
      fill: { color: bg }, line: { color: bg, width: 0 },
    });
    const cells = [
      { x: 0.08, w: 2.35, v: (b.name||'').slice(0,22), align: 'left', bold: true, color: P.charcoal },
      { x: 2.5,  w: 1.3,  v: String(b.skus||0),        align: 'right', bold: false, color: P.teal },
      { x: 3.9,  w: 1.5,  v: String(b.chains||0),      align: 'right', bold: false, color: P.charcoal },
      { x: 5.5,  w: 2.2,  v: b.avg_offer_pct != null ? pct(b.avg_offer_pct) : '—', align: 'right', bold: false, color: P.amber },
    ];
    cells.forEach(cell => {
      sl.addText(cell.v, {
        x: bTblX + cell.x, y: ry + 0.06, w: cell.w, h: 0.32,
        fontSize: 9, bold: cell.bold, color: cell.color, align: cell.align, margin: 0,
      });
    });
  });

  // Pending chains warning (right)
  if (pendingChains.length > 0) {
    sectionLabel(sl, 8.4, 2.4, 4.7, '⚠️  KAM Escalation Required');
    sl.addShape(pres.ShapeType.roundRect, {
      x: 8.4, y: 2.62, w: 4.7, h: 4.6,
      fill: { color: P.amberLt }, line: { color: P.amber, width: 1.4 }, rectRadius: 0.08,
    });
    sl.addText('Pending Promo Sheets', {
      x: 8.56, y: 2.72, w: 4.38, h: 0.34,
      fontSize: 10.5, bold: true, color: P.amber, align: 'left', margin: 0,
    });
    sl.addText(String(promoPend) + ' chains yet to confirm ' + promoMonth + ' promotions', {
      x: 8.56, y: 3.06, w: 4.38, h: 0.28,
      fontSize: 9, color: P.charcoal, align: 'left', margin: 0,
    });
    pendingChains.slice(0, 8).forEach((chain, i) => {
      sl.addText('•  ' + chain, {
        x: 8.56, y: 3.44 + i * 0.36, w: 4.38, h: 0.32,
        fontSize: 9.5, color: P.charcoal, align: 'left', margin: 0,
      });
    });
  } else {
    // All confirmed
    sl.addShape(pres.ShapeType.roundRect, {
      x: 8.4, y: 2.62, w: 4.7, h: 1.6,
      fill: { color: P.greenLt }, line: { color: P.green, width: 1.4 }, rectRadius: 0.08,
    });
    sl.addText('✔  All Chains Confirmed', {
      x: 8.56, y: 2.72, w: 4.38, h: 0.38,
      fontSize: 11, bold: true, color: P.green, align: 'left', margin: 0,
    });
    sl.addText('All ' + promoChainIn + ' chains submitted ' + promoMonth + ' promo sheets.', {
      x: 8.56, y: 3.14, w: 4.38, h: 0.8,
      fontSize: 9.5, color: P.charcoal, align: 'left', margin: 0, wrap: true,
    });
  }
}

// ── SLIDE 6: FY27 Forecast ───────────────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: P.offW };
  slideHeader(sl, 'FY27 Forecast & Pipeline', 'Monthly targets · Q2–Q3 highlights · brand phasing');
  addFooter(sl, 6);

  // Month chart — pipeline months only (Sep-Nov data available)
  const hasMonthData = fcMonthLabels.length > 0 && fcMonthVals.length > 0;

  if (hasMonthData) {
    sectionLabel(sl, 0.4, 1.05, 8.2, 'Monthly NSV Target FY27 (₹ Lakhs) — Q2-Q3 Pipeline (Sep–Nov)');
    sl.addChart(pres.ChartType.bar, [
      { name: 'Target (₹L)', labels: fcMonthLabels, values: fcMonthVals.map(v => Math.round(v || 0)) },
    ], {
      x: 0.4, y: 1.28, w: 8.2, h: 4.3,
      barDir: 'col',
      barGrouping: 'clustered',
      chartColors: [P.teal],
      showLegend: false,
      showValue: true, dataLabelFontSize: 10,
      dataLabelPosition: 'outEnd',
      dataLabelColor: P.charcoal,
      valAxisLabelFontSize: 9, catAxisLabelFontSize: 11,
      valGridLine: { color: P.lgrey, style: 'solid', size: 0.8 },
      catGridLine: { style: 'none' },
      valAxisLabelColor: P.grey,
      catAxisLabelColor: P.charcoal,
      showTitle: false,
      plotAreaBorderColor: P.offW,
      chartAreaBorderColor: P.offW,
      fill: P.offW,
    });
  }

  // Q2-Q3 KPI summary box
  kpiBox(sl, 0.4, 5.72, 8.2, 1.55, cr(q2q3), 'Q2–Q3 Pipeline Total (Sep–Dec)', 'FY27 critical growth window', P.teal, P.white);

  // Right: Brand targets
  if (fcBrands.length > 0) {
    sectionLabel(sl, 8.8, 1.05, 4.3, 'Brand Targets — Q2-Q3 NSV (₹L)');
    const bTblX = 8.8, bTblY = 1.28;
    sl.addShape(pres.ShapeType.rect, {
      x: bTblX, y: bTblY, w: 4.3, h: 0.36,
      fill: { color: P.navy }, line: { color: P.navy, width: 0 },
    });
    ['Brand', 'Sep', 'Oct', 'Nov'].forEach((h, i) => {
      const xs = [0.08, 1.65, 2.55, 3.45];
      const ws = [1.5,  0.85, 0.85, 0.82];
      const als = ['left','right','right','right'];
      sl.addText(h, {
        x: bTblX + xs[i], y: bTblY + 0.04, w: ws[i], h: 0.28,
        fontSize: 8.5, bold: true, color: P.white, align: als[i], margin: 0,
      });
    });
    fcBrands.forEach((b, i) => {
      const ry = bTblY + 0.36 + i * 0.44;
      if (ry + 0.44 > 7.1) return;
      const bg = i % 2 === 0 ? P.white : P.offW;
      sl.addShape(pres.ShapeType.rect, {
        x: bTblX, y: ry, w: 4.3, h: 0.44,
        fill: { color: bg }, line: { color: bg, width: 0 },
      });
      const sepV = Math.round(b.sep_26 || 0);
      const octV = Math.round(b.oct_26 || 0);
      const novV = Math.round(b.nov_26 || 0);
      [
        { x: 0.08, w: 1.5,  v: (b.name||'').slice(0,16), align:'left',  bold:true,  color:P.charcoal },
        { x: 1.65, w: 0.85, v: fmt(sepV), align:'right', bold:false, color:P.mgrey },
        { x: 2.55, w: 0.85, v: fmt(octV), align:'right', bold:false, color:P.mgrey },
        { x: 3.45, w: 0.82, v: fmt(novV), align:'right', bold:true,  color:P.teal },
      ].forEach(cell => {
        sl.addText(cell.v, {
          x: bTblX + cell.x, y: ry + 0.06, w: cell.w, h: 0.32,
          fontSize: 9, bold: cell.bold, color: cell.color, align: cell.align, margin: 0,
        });
      });
    });

    // FY27 total KPI
    const fy27Y = bTblY + 0.36 + Math.min(fcBrands.length, 10) * 0.44 + 0.2;
    if (fy27Y + 1.3 < 7.2) {
      kpiBox(sl, bTblX, fy27Y, 4.3, 1.3, cr(fy27Fc), 'FY27 Full-Year Target', growth ? sgn(growth) + ' growth assumption' : '', P.navy, P.white);
    }
  }
}

// ── SLIDE 7: Insights & Priorities ───────────────────────────────────────────
{
  const sl = pres.addSlide();
  sl.background = { color: P.offW };
  slideHeader(sl, 'Key Insights & Strategic Priorities', 'Win zones · risk areas · action owners');
  addFooter(sl, 7);

  // 6 insight cards in 3×2 grid
  const cardW = 4.05, cardH = 2.4, gap = 0.1;
  const startX = 0.4, startY = 1.1;
  const iconColors = [P.green, P.red, P.teal, P.amber, P.green, P.navy];
  const bgColors   = [P.greenLt, P.redLt, P.tealLt, P.amberLt, P.greenLt, P.offW];
  const icons = ['✔','⚠','ℹ','⚠','✔','▶'];

  insCards.forEach((card, i) => {
    const col = i % 3;
    const row = Math.floor(i / 3);
    const cx = startX + col * (cardW + gap);
    const cy = startY + row * (cardH + gap);
    sl.addShape(pres.ShapeType.roundRect, {
      x: cx, y: cy, w: cardW, h: cardH,
      fill: { color: bgColors[i] || P.offW },
      line: { color: bgColors[i] || P.lgrey, width: 0 },
      rectRadius: 0.08,
    });
    // Icon circle
    sl.addShape(pres.ShapeType.ellipse, {
      x: cx + 0.15, y: cy + 0.14, w: 0.46, h: 0.46,
      fill: { color: iconColors[i] || P.teal },
      line: { color: iconColors[i] || P.teal, width: 0 },
    });
    sl.addText(icons[i] || '•', {
      x: cx + 0.15, y: cy + 0.14, w: 0.46, h: 0.46,
      fontSize: 12, bold: true, color: P.white,
      align: 'center', valign: 'middle', margin: 0,
    });
    // Title
    sl.addText((card.title || '').slice(0, 40), {
      x: cx + 0.7, y: cy + 0.14, w: cardW - 0.85, h: 0.44,
      fontSize: 10.5, bold: true, color: P.charcoal,
      align: 'left', valign: 'middle', margin: 0, wrap: true,
    });
    // Body text
    sl.addText(card.text || '', {
      x: cx + 0.15, y: cy + 0.66, w: cardW - 0.3, h: cardH - 0.82,
      fontSize: 9, bold: false, color: P.charcoal,
      align: 'left', valign: 'top', margin: 0, wrap: true,
    });
  });
}

// ── SLIDE 8: Closing / Next Actions ──────────────────────────────────────────
{
  const sl = pres.addSlide();
  // Dark navy background
  sl.addShape(pres.ShapeType.rect, {
    x: 0, y: 0, w: 13.3, h: 7.5,
    fill: { color: P.navy }, line: { color: P.navy, width: 0 },
  });

  // Decorative shape (top-right quadrant)
  sl.addShape(pres.ShapeType.ellipse, {
    x: 9.8, y: -1.0, w: 5.5, h: 5.5,
    fill: { color: P.teal, transparency: 88 },
    line: { color: P.teal, width: 0 },
  });

  // Accent bar
  sl.addShape(pres.ShapeType.rect, {
    x: 0.5, y: 0.9, w: 0.06, h: 5.7,
    fill: { color: P.teal }, line: { color: P.teal, width: 0 },
  });

  // Title
  sl.addText('Priority Actions', {
    x: 0.78, y: 0.9, w: 9, h: 0.6,
    fontSize: 32, bold: true, color: P.white, align: 'left', margin: 0,
  });
  sl.addText('MT Leadership — Next 90 Days', {
    x: 0.78, y: 1.5, w: 9, h: 0.32,
    fontSize: 13, bold: false, color: P.icegrey, align: 'left', margin: 0,
  });

  // 5 numbered action items
  const actions = [
    { n: '01', color: P.teal,  text: 'Accelerate mid-tier chain penetration — activate Lifestyle, Shopper Stop, Nykaa channels with dedicated MT SKUs.' },
    { n: '02', color: P.amber, text: 'Reset Dmart trade economics — current TOT >' + (topChains.find(c=>(c.chain||c.name||'').toLowerCase().includes('dmart'))?.tot_pct?.toFixed(1)||'53') + '% above portfolio average; renegotiate shelf terms.' },
    { n: '03', color: P.green, text: 'Scale The Derma Co in MT — leverage +161% FY26 growth momentum; extend to 3 new chains in Q2.' },
    { n: '04', color: P.amber, text: 'Close ' + (promoPend || 7) + ' pending promo sheets for ' + promoMonth + ' — escalate via KAM leads before month-end execution.' },
    { n: '05', color: P.teal,  text: 'Achieve Q2–Q3 NSV target of ' + cr(q2q3) + ' — weekly pipeline reviews with regional heads; flag at-risk SKUs.' },
  ];

  actions.forEach((a, i) => {
    const ay = 2.06 + i * 1.0;
    // Number circle
    sl.addShape(pres.ShapeType.ellipse, {
      x: 0.78, y: ay, w: 0.48, h: 0.48,
      fill: { color: a.color }, line: { color: a.color, width: 0 },
    });
    sl.addText(a.n, {
      x: 0.78, y: ay, w: 0.48, h: 0.48,
      fontSize: 10.5, bold: true, color: P.white,
      align: 'center', valign: 'middle', margin: 0,
    });
    sl.addText(a.text, {
      x: 1.42, y: ay + 0.01, w: 10.5, h: 0.46,
      fontSize: 10, bold: false, color: P.white,
      align: 'left', valign: 'middle', margin: 0, wrap: false,
    });
  });

  // Footer (on dark)
  sl.addText('Honasa Consumer Ltd. — Modern Trade Analytics  |  Confidential', {
    x: 0.78, y: 7.12, w: 11, h: 0.22,
    fontSize: 8, color: P.mgrey, align: 'left', margin: 0,
  });
}

// ── Write file ───────────────────────────────────────────────────────────────
pres.writeFile({ fileName: OUT }).then(() => {
  console.log('Wrote: ' + OUT);
}).catch(err => {
  console.error('Error writing PPTX:', err);
  process.exit(1);
});
