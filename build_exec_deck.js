'use strict';
const pptxgen = require('pptxgenjs');

// ── Palette ───────────────────────────────────────────────────────────────────
const C = {
  navy:    '102542',
  gold:    'DAA520',
  slate:   '323232',
  white:   'FFFFFF',
  bg:      'F5F7FA',
  pos:     '2E7D52',
  neg:     'CC3333',
  blue:    '3A89C9',
  amber:   'E67E22',
  midnav:  '1A3D6B',
  dnav:    '06111F',
  muted:   '8A9BB2',
  panel:   '0A1E38',
};

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; // 10" × 5.625"

// ── Shared helpers ─────────────────────────────────────────────────────────────
function hdr(slide, title, dark = false) {
  slide.background = { color: dark ? C.navy : C.bg };
  slide.addText(title, {
    x: 0.28, y: 0.1, w: 8.5, h: 0.55,
    fontSize: 21, bold: true, color: dark ? C.white : C.navy,
    fontFace: 'Cambria', align: 'left', margin: 0,
  });
  slide.addShape('rect', {
    x: 0.28, y: 0.66, w: 1.8, h: 0.042,
    fill: { color: C.gold }, line: { type: 'none' },
  });
  slide.addText("Honasa Consumer Ltd.  ·  MT Analytics  ·  FYTD Jul '26", {
    x: 5.2, y: 0.14, w: 4.55, h: 0.26,
    fontSize: 7, color: dark ? '7A9CC0' : C.muted,
    fontFace: 'Calibri', align: 'right', margin: 0,
  });
}

function scriptBox(slide, text, dark = false) {
  slide.addShape('rect', {
    x: 0, y: 4.08, w: 10, h: 1.545,
    fill: { color: dark ? C.dnav : C.panel }, line: { type: 'none' },
  });
  slide.addText('PRESENTER LEADERSHIP SCRIPT', {
    x: 0.22, y: 4.12, w: 4, h: 0.2,
    fontSize: 6.5, bold: true, color: C.gold, fontFace: 'Calibri', margin: 0,
  });
  slide.addShape('rect', {
    x: 0.22, y: 4.32, w: 9.56, h: 0.016,
    fill: { color: '1E4070' }, line: { type: 'none' },
  });
  slide.addText(text, {
    x: 0.22, y: 4.37, w: 9.56, h: 1.22,
    fontSize: 7.5, color: 'C8D8F0', fontFace: 'Calibri',
    margin: 0, lineSpacingMultiple: 1.32, valign: 'top',
  });
}

function kpiCard(slide, x, y, w, h, val, label, badge, valColor, bg) {
  slide.addShape('rect', { x, y, w, h, fill: { color: bg || C.white }, line: { type: 'none' } });
  slide.addText(val, {
    x: x + 0.08, y: y + 0.09, w: w - 0.16, h: h * 0.47,
    fontSize: 18, bold: true, color: valColor, fontFace: 'Cambria', align: 'center', margin: 0,
  });
  slide.addText(label, {
    x: x + 0.08, y: y + h * 0.52, w: w - 0.16, h: h * 0.26,
    fontSize: 7.5, bold: true, color: C.slate, fontFace: 'Calibri', align: 'center', margin: 0,
  });
  if (badge) {
    slide.addText(badge, {
      x: x + 0.08, y: y + h * 0.78, w: w - 0.16, h: h * 0.2,
      fontSize: 6.8, color: C.muted, fontFace: 'Calibri', align: 'center', margin: 0,
    });
  }
}

function hbar(slide, x, y, maxW, h, pct, fillColor, trackColor) {
  slide.addShape('rect', { x, y, w: maxW, h, fill: { color: trackColor || 'DDE4EF' }, line: { type: 'none' } });
  const fw = Math.max((Math.min(pct, 100) / 100) * maxW, 0.02);
  slide.addShape('rect', { x, y, w: fw, h, fill: { color: fillColor }, line: { type: 'none' } });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 1 · Executive Summary — FYTD Jul '26 Scale & Momentum
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navy };

  // Title block
  s.addText("Executive Summary  ·  FYTD Jul '26", {
    x: 0.28, y: 0.08, w: 7.5, h: 0.55,
    fontSize: 24, bold: true, color: C.white, fontFace: 'Cambria', margin: 0,
  });
  s.addText('Scale & Momentum', {
    x: 0.28, y: 0.6, w: 4, h: 0.28,
    fontSize: 12, color: C.gold, fontFace: 'Cambria', margin: 0,
  });
  s.addShape('rect', { x: 0.28, y: 0.88, w: 1.6, h: 0.042, fill: { color: C.gold }, line: { type: 'none' } });
  s.addText("Honasa Consumer Ltd.  ·  MT Analytics  ·  FYTD Jul '26", {
    x: 5.4, y: 0.13, w: 4.35, h: 0.24,
    fontSize: 7, color: '7A9CC0', fontFace: 'Calibri', align: 'right', margin: 0,
  });

  // 5 KPI cards
  const kpis = [
    { val: '₹4,921L',  lbl: "Jul '26 Primary",    badge: '+18.1% MoM  |  Jun was ₹4,167L', vc: C.gold },
    { val: '₹18,574L', lbl: 'FYTD Primary (Apr–Jul)', badge: '+82.3% YoY vs ₹10,190L LY',  vc: C.gold },
    { val: '₹12,573L', lbl: 'Mamaearth FYTD',     badge: '69.1% share  |  +50.5% YoY',    vc: 'FFE066' },
    { val: '₹5,173L',  lbl: 'The Derma Co. FYTD', badge: '+404.2% YoY — Hyper Growth',    vc: C.gold  },
    { val: '₹8,265L',  lbl: 'Face Cleanser FYTD', badge: '45.5% share  |  +124.7% YoY',   vc: 'FFE066' },
  ];
  const cw = 1.82, cy = 0.98, gap = 0.13;
  kpis.forEach((k, i) => {
    const cx = 0.28 + i * (cw + gap);
    s.addShape('rect', { x: cx, y: cy, w: cw, h: 1.55, fill: { color: C.midnav }, line: { type: 'none' } });
    s.addText(k.val, { x: cx + 0.06, y: cy + 0.09, w: cw - 0.12, h: 0.63, fontSize: 18, bold: true, color: k.vc, fontFace: 'Cambria', align: 'center', margin: 0 });
    s.addText(k.lbl, { x: cx + 0.06, y: cy + 0.74, w: cw - 0.12, h: 0.32, fontSize: 7.5, bold: true, color: C.white, fontFace: 'Calibri', align: 'center', margin: 0 });
    s.addText(k.badge, { x: cx + 0.06, y: cy + 1.07, w: cw - 0.12, h: 0.38, fontSize: 6.8, color: '8EAACF', fontFace: 'Calibri', align: 'center', margin: 0 });
  });

  // Growth momentum strip
  s.addShape('rect', { x: 0.28, y: 2.67, w: 9.44, h: 0.96, fill: { color: C.panel }, line: { type: 'none' } });
  s.addText('YoY Growth Engine', { x: 0.42, y: 2.72, w: 2, h: 0.22, fontSize: 8.5, bold: true, color: C.gold, fontFace: 'Cambria', margin: 0 });
  const growths = [
    { lbl: 'Total Primary',  pct: 82.3,  tag: '+82.3% YoY', col: C.gold },
    { lbl: 'The Derma Co.', pct: 100,   tag: '+404% YoY',  col: C.neg  },
    { lbl: 'Face Cleanser', pct: 100,   tag: '+124.7% YoY', col: C.blue },
    { lbl: 'Mamaearth',     pct: 50.5,  tag: '+50.5% YoY', col: '90CAF9' },
    { lbl: 'South-1 Zone',  pct: 100,   tag: '+120.3% YoY', col: C.pos  },
  ];
  growths.forEach((g, i) => {
    const bx = 0.42 + i * 1.86;
    s.addText(g.lbl, { x: bx, y: 2.96, w: 1.72, h: 0.17, fontSize: 6.8, color: C.muted, fontFace: 'Calibri', align: 'left', margin: 0 });
    hbar(s, bx, 3.14, 1.72, 0.2, g.pct, g.col, '163060');
    s.addText(g.tag, { x: bx, y: 3.35, w: 1.72, h: 0.18, fontSize: 7.5, bold: true, color: g.col, fontFace: 'Calibri', align: 'left', margin: 0 });
  });

  // Recovery callout bar
  s.addShape('rect', { x: 0.28, y: 3.73, w: 9.44, h: 0.32, fill: { color: '163060' }, line: { type: 'none' } });
  s.addText(
    "⚡ Jul '26 Recovery: ₹4,167L → ₹4,921L  (+18.1% MoM)  post May–Jun inventory rebalancing  ·  FYTD +82.3% YoY driven by Mamaearth anchor + Derma Co. hyper-scale",
    { x: 0.42, y: 3.79, w: 9.2, h: 0.22, fontSize: 7.5, color: C.white, fontFace: 'Calibri', margin: 0 }
  );

  scriptBox(s,
    "Good [morning/afternoon]. Our MT channel delivered ₹18,574 Lacs FYTD — an 82.3% step-up versus ₹10,190 Lacs last year. This is structural scale, not cyclical noise. July at ₹4,921 Lacs marks an 18.1% MoM rebound from the June trough of ₹4,167 Lacs, which was a deliberate inventory rebalancing cycle. Two brands are driving this story: Mamaearth at ₹12,573 Lacs with 69.1% portfolio share and solid 50.5% YoY growth, and The Derma Co. at ₹5,173 Lacs delivering 404% YoY — that is a brand going from category entrant to category shaper inside 12 months. Face Cleanser anchors the category at 45.5% of our portfolio. The strategic question for this review: given this trajectory, where do we invest the next rupee of attention and resource?",
    true
  );
  s.addNotes("FYTD Primary ₹18,574L (+82.3% YoY). July ₹4,921L (+18.1% MoM). Mamaearth ₹12,573L (69.1%). Derma Co. ₹5,173L (+404.2%). Face Cleanser ₹8,265L (45.5%).");
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 2 · Channel Performance Matrix — MT Dominance & Omnichannel Balance
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  hdr(s, "Channel Performance Matrix  ·  FYTD Jul '26", false);

  // 4 channel KPI cards
  const channels = [
    { ch: 'Modern Trade (MT)', val: '₹17,241L', yoy: '+93.9% YoY', share: '94.8%', shareColor: C.navy, bg: 'EEF3FF' },
    { ch: 'eB2B', val: '₹894L', yoy: '+23.1% YoY', share: '4.9%', shareColor: C.blue, bg: C.white },
    { ch: 'SIS', val: '₹46L', yoy: '+24.3% YoY', share: '0.3%', shareColor: C.muted, bg: C.white },
    { ch: 'Total (Matrix Base)', val: '₹18,183L', yoy: 'vs ₹18,574L FYTD Total', share: '100%', shareColor: C.gold, bg: 'FFF8E8' },
  ];
  const cw2 = 2.1, cy2 = 0.88;
  channels.forEach((c, i) => {
    const cx = 0.28 + i * (cw2 + 0.14);
    s.addShape('rect', { x: cx, y: cy2, w: cw2, h: 1.65, fill: { color: c.bg }, line: { color: 'D0D8EE', size: 0.75 } });
    // Channel share bar
    const barPct = parseFloat(c.share);
    hbar(s, cx + 0.1, cy2 + 0.08, cw2 - 0.2, 0.18, barPct, c.shareColor, 'DDE4EF');
    s.addText(c.share, { x: cx + 0.1, y: cy2 + 0.27, w: cw2 - 0.2, h: 0.22, fontSize: 8, bold: true, color: c.shareColor, fontFace: 'Calibri', align: 'right', margin: 0 });
    s.addText(c.val, { x: cx + 0.08, y: cy2 + 0.5, w: cw2 - 0.16, h: 0.55, fontSize: 19, bold: true, color: c.shareColor, fontFace: 'Cambria', align: 'center', margin: 0 });
    s.addText(c.ch, { x: cx + 0.08, y: cy2 + 1.06, w: cw2 - 0.16, h: 0.28, fontSize: 8.5, bold: true, color: C.slate, fontFace: 'Calibri', align: 'center', margin: 0 });
    s.addText(c.yoy, { x: cx + 0.08, y: cy2 + 1.34, w: cw2 - 0.16, h: 0.25, fontSize: 7.5, color: C.pos, fontFace: 'Calibri', align: 'center', margin: 0 });
  });

  // Monthly trend mini-chart (bar chart)
  const trendData = [
    { name: 'Primary ₹Lacs', labels: ["Apr+May Combined", "Jun '26", "Jul '26"], values: [9486, 4167, 4921] },
  ];
  s.addChart(pres.ChartType.bar, trendData, {
    x: 0.28, y: 2.65, w: 4.8, h: 1.3,
    barDir: 'col', barGrouping: 'clustered',
    chartColors: [C.midnav, C.neg, C.gold],
    showValue: true, dataLabelPosition: 'outEnd',
    dataLabelFontSize: 9, dataLabelColor: C.slate, dataLabelFontBold: true,
    showLegend: false, showTitle: true,
    title: "Monthly Primary Trend ₹Lacs", titleFontSize: 9, titleColor: C.slate,
    valGridLine: { color: 'D8DDE8', size: 0.5 }, catGridLine: { style: 'none' },
    valAxisLabelColor: C.muted, catAxisLabelColor: C.slate, catAxisLabelFontSize: 8,
    valAxisMaxVal: 10000, valAxisMinVal: 0,
  });

  // Inventory rebalancing callout
  s.addShape('rect', { x: 5.32, y: 2.65, w: 4.4, h: 1.3, fill: { color: 'FFF3E0' }, line: { color: C.amber, size: 1 } });
  s.addText('Inventory Rebalancing Story', { x: 5.45, y: 2.7, w: 4.15, h: 0.25, fontSize: 9, bold: true, color: C.amber, fontFace: 'Cambria', margin: 0 });
  const bullets = [
    'Apr–May combined ₹9,486L — strong H1 loading by key accounts',
    'Jun ₹4,167L — planned inventory digestion cycle; channels clearing pipelines',
    'Jul ₹4,921L — +18.1% MoM rebound; demand signals healthy & restocking live',
    'FYTD matrix base ₹18,183L vs total ₹18,574L — ₹391L in direct/other allocations',
  ];
  bullets.forEach((b, i) => {
    s.addText(`• ${b}`, {
      x: 5.45, y: 3.0 + i * 0.24, w: 4.15, h: 0.22,
      fontSize: 7.5, color: C.slate, fontFace: 'Calibri', margin: 0,
    });
  });

  scriptBox(s,
    "Our channel distribution tells a clear story: Modern Trade commands 94.8% at ₹17,241 Lacs and grew 93.9% YoY — nearly doubling the base. eB2B at ₹894 Lacs and SIS at ₹46 Lacs are growing but remain complementary channels. The monthly cadence shows a deliberate pattern: strong primary loading in April–May as accounts anticipated summer demand, a planned inventory rebalancing in June as channels digested that pipeline — that is not a warning sign, it is disciplined trade management — followed by a sharp 18.1% MoM recovery in July confirming underlying demand health. The ₹391 Lacs difference between matrix base and FYTD total reflects direct and other channel allocations outside the three primary channels. Key ask for zone heads: maintain MT fill rates above 95% in August to sustain the July momentum."
  );
  s.addNotes("MT ₹17,241L (+93.9%), eB2B ₹894L (+23.1%), SIS ₹46L (+24.3%). Jun dip = planned inventory rebalancing. Jul recovery +18.1% MoM.");
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 3 · Pure MT Market Share Review — Nielsen RMS Jun '26 Panel
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  hdr(s, "MT Market Share Review  ·  Nielsen RMS Jun '26 Panel", true);

  // ─ Face Wash panel (left) ─
  s.addShape('rect', { x: 0.28, y: 0.82, w: 4.62, h: 3.18, fill: { color: C.midnav }, line: { type: 'none' } });
  s.addText('FACE WASH (MT)', { x: 0.4, y: 0.87, w: 2.5, h: 0.24, fontSize: 9, bold: true, color: C.gold, fontFace: 'Cambria', margin: 0 });
  s.addText('MAT ₹858 Cr  |  +14.6% YoY', { x: 0.4, y: 1.1, w: 3, h: 0.2, fontSize: 7.5, color: '8EAACF', fontFace: 'Calibri', margin: 0 });

  const fwBrands = [
    { name: 'Himalaya', ms: 22.6, chg: '-1.6pp', col: '6B7280' },
    { name: 'Garnier',  ms: 17.1, chg: '—',      col: '6B7280' },
    { name: "Pond's",   ms: 15.4, chg: '—',       col: '6B7280' },
    { name: 'Mamaearth #4', ms: 10.5, chg: '+3.1pp', col: C.gold },
  ];
  fwBrands.forEach((b, i) => {
    const by = 1.36 + i * 0.54;
    s.addText(b.name, { x: 0.38, y: by, w: 1.4, h: 0.22, fontSize: 8.5, bold: b.name.startsWith('Mama'), color: b.name.startsWith('Mama') ? C.gold : C.white, fontFace: 'Calibri', margin: 0 });
    hbar(s, 1.82, by + 0.03, 2.5, 0.18, (b.ms / 25) * 100, b.col, '2A4A7A');
    s.addText(`${b.ms}%`, { x: 4.35, y: by, w: 0.42, h: 0.22, fontSize: 8.5, bold: b.name.startsWith('Mama'), color: b.name.startsWith('Mama') ? C.gold : C.white, fontFace: 'Calibri', align: 'right', margin: 0 });
    s.addText(b.chg, { x: 1.82, y: by + 0.22, w: 2.5, h: 0.18, fontSize: 6.5, color: b.chg.startsWith('+') ? C.pos : (b.chg.startsWith('-') ? C.neg : C.muted), fontFace: 'Calibri', margin: 0 });
  });

  // MH FW KPI chips
  const fwKpis = [
    { v: '89.0%', l: 'WD Mamaearth' },
    { v: '+58.2%', l: 'L3M YoY' },
    { v: '27.3%', l: 'Derma Co. WD' },
  ];
  fwKpis.forEach((k, i) => {
    const kx = 0.38 + i * 1.52;
    s.addShape('rect', { x: kx, y: 3.1, w: 1.38, h: 0.72, fill: { color: C.panel }, line: { type: 'none' } });
    s.addText(k.v, { x: kx + 0.04, y: 3.15, w: 1.3, h: 0.37, fontSize: 16, bold: true, color: C.gold, fontFace: 'Cambria', align: 'center', margin: 0 });
    s.addText(k.l, { x: kx + 0.04, y: 3.52, w: 1.3, h: 0.26, fontSize: 7, color: '8EAACF', fontFace: 'Calibri', align: 'center', margin: 0 });
  });

  // ─ Shampoo panel (right) ─
  s.addShape('rect', { x: 5.1, y: 0.82, w: 4.62, h: 3.18, fill: { color: C.midnav }, line: { type: 'none' } });
  s.addText('SHAMPOO (MT)', { x: 5.22, y: 0.87, w: 2.5, h: 0.24, fontSize: 9, bold: true, color: C.gold, fontFace: 'Cambria', margin: 0 });
  s.addText('MAT ₹1,736 Cr  |  +7.6% YoY', { x: 5.22, y: 1.1, w: 3, h: 0.2, fontSize: 7.5, color: '8EAACF', fontFace: 'Calibri', margin: 0 });

  const shBrands = [
    { name: 'Dove',       ms: 16.6, chg: '—',      col: '6B7280' },
    { name: 'H&S',        ms: 13.0, chg: '—',       col: '6B7280' },
    { name: 'Sunsilk',    ms: 9.4,  chg: '—',       col: '6B7280' },
    { name: 'Clinic Plus', ms: 7.8, chg: '—',       col: '6B7280' },
    { name: 'Mamaearth #7', ms: 3.7, chg: '+1.2pp', col: C.gold },
  ];
  shBrands.forEach((b, i) => {
    const by = 1.36 + i * 0.42;
    s.addText(b.name, { x: 5.2, y: by, w: 1.5, h: 0.2, fontSize: 8, bold: b.name.startsWith('Mama'), color: b.name.startsWith('Mama') ? C.gold : C.white, fontFace: 'Calibri', margin: 0 });
    hbar(s, 6.74, by + 0.02, 2.3, 0.16, (b.ms / 20) * 100, b.col, '2A4A7A');
    s.addText(`${b.ms}%`, { x: 9.1, y: by, w: 0.44, h: 0.2, fontSize: 8, bold: b.name.startsWith('Mama'), color: b.name.startsWith('Mama') ? C.gold : C.white, fontFace: 'Calibri', align: 'right', margin: 0 });
    if (b.chg !== '—') {
      s.addText(b.chg, { x: 6.74, y: by + 0.18, w: 2.3, h: 0.16, fontSize: 6.5, color: C.pos, fontFace: 'Calibri', margin: 0 });
    }
  });

  // Shampoo KPI chips
  const shKpis = [
    { v: '81.5%', l: 'WD Mamaearth' },
    { v: '+80.3%', l: 'L3M YoY' },
    { v: '25.5%', l: 'SoG Index' },
  ];
  shKpis.forEach((k, i) => {
    const kx = 5.2 + i * 1.52;
    s.addShape('rect', { x: kx, y: 3.1, w: 1.38, h: 0.72, fill: { color: C.panel }, line: { type: 'none' } });
    s.addText(k.v, { x: kx + 0.04, y: 3.15, w: 1.3, h: 0.37, fontSize: 16, bold: true, color: C.gold, fontFace: 'Cambria', align: 'center', margin: 0 });
    s.addText(k.l, { x: kx + 0.04, y: 3.52, w: 1.3, h: 0.26, fontSize: 7, color: '8EAACF', fontFace: 'Calibri', align: 'center', margin: 0 });
  });

  // Tier 3 badge
  s.addShape('rect', { x: 4.03, y: 0.82, w: 0.98, h: 0.38, fill: { color: C.amber }, line: { type: 'none' } });
  s.addText("⚠ Tier 3\nJul '26 Feed\nPending", { x: 4.04, y: 0.84, w: 0.94, h: 0.36, fontSize: 6.5, bold: true, color: C.white, fontFace: 'Calibri', align: 'center', margin: 0 });

  scriptBox(s,
    "The Nielsen RMS June panel tells a powerful competitive story. In Face Wash, Mamaearth is the #4 brand at 10.5% market share — but the trajectory is what matters: +3.1 percentage points YoY, 89% weighted distribution, and L3M growth of 58.2%. Himalaya, the category leader, is losing ground at -1.6 pp. We are the fastest-growing brand in this category. In Shampoo, we are #7 at 3.7% share — this is our strategic opportunity. The 80.3% L3M growth rate shows the velocity is there; the gap to Dove at 16.6% is the ambition. The Derma Co. at 27.3% WD in Face Wash is already building its own presence. July '26 Nielsen cut is pending — a Tier 3 placeholder applies; we will update this slide when the fresh cut arrives. Strategic implication: defend Face Wash WD above 89% while aggressively scaling Shampoo distribution toward Face Wash parity.",
    true
  );
  s.addNotes("FW: Mamaearth #4, 10.5% MS, +3.1pp, 89% WD, +58.2% L3M. Shampoo: #7, 3.7% MS, +1.2pp, 81.5% WD, +80.3% L3M. Jul Nielsen pending.");
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 4 · Brand Portfolio Dynamics — Core vs. Scaling Engines
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  hdr(s, "Brand Portfolio Dynamics  ·  FYTD Jul '26", false);

  // Anchor brands side by side
  const anchor = [
    {
      brand: 'Mamaearth', tag: 'Anchor Brand', val: '₹12,573L',
      share: '69.1%', yoy: '+50.5% YoY', bg: 'E8EEF8',
      border: C.navy, note: 'Portfolio anchor · Face Cleanser + Shampoo engine',
    },
    {
      brand: 'The Derma Co.', tag: 'Scale Engine', val: '₹5,173L',
      share: '28.5%', yoy: '+404.2% YoY', bg: 'FFF3E0',
      border: C.gold, note: 'Hyper-growth · Face Cleanser spike Jul +47.5% MoM',
    },
  ];
  anchor.forEach((a, i) => {
    const ax = 0.28 + i * 4.82;
    s.addShape('rect', { x: ax, y: 0.82, w: 4.62, h: 2.25, fill: { color: a.bg }, line: { color: a.border, size: 1.5 } });
    // Tag chip
    s.addShape('rect', { x: ax + 0.12, y: 0.88, w: 1.6, h: 0.28, fill: { color: a.border }, line: { type: 'none' } });
    s.addText(a.tag, { x: ax + 0.14, y: 0.9, w: 1.56, h: 0.24, fontSize: 7.5, bold: true, color: C.white, fontFace: 'Calibri', align: 'center', margin: 0 });
    s.addText(a.brand, { x: ax + 0.12, y: 1.2, w: 4.36, h: 0.55, fontSize: 20, bold: true, color: a.border === C.navy ? C.navy : C.amber, fontFace: 'Cambria', margin: 0 });
    s.addText(a.val, { x: ax + 0.12, y: 1.75, w: 2.2, h: 0.48, fontSize: 22, bold: true, color: C.slate, fontFace: 'Cambria', margin: 0 });
    s.addShape('rect', { x: ax + 2.38, y: 1.8, w: 2.1, h: 0.38, fill: { color: a.border }, line: { type: 'none' } });
    s.addText(`${a.share} share`, { x: ax + 2.4, y: 1.84, w: 2.06, h: 0.2, fontSize: 9, bold: true, color: C.white, fontFace: 'Calibri', align: 'center', margin: 0 });
    s.addText(a.yoy, { x: ax + 2.4, y: 2.04, w: 2.06, h: 0.15, fontSize: 7, color: C.white, fontFace: 'Calibri', align: 'center', margin: 0 });
    s.addText(a.note, { x: ax + 0.12, y: 2.27, w: 4.36, h: 0.22, fontSize: 7, color: C.muted, fontFace: 'Calibri', margin: 0 });
  });

  // Scale-up portfolio row
  const small = [
    { brand: 'Aqualogica',  val: '₹~182L', note: 'Sunscreen niche · scaling in South zones', col: '3A89C9' },
    { brand: 'Aykriti',     val: 'Emerging', note: 'Ayurveda positioning · early distribution', col: '84B59F' },
    { brand: "Dr. Sheth's", val: 'Emerging', note: 'Dermatology anchor · clinic route entry', col: '6D2E46' },
  ];
  small.forEach((b, i) => {
    const sx = 0.28 + i * 3.24;
    s.addShape('rect', { x: sx, y: 3.18, w: 3.06, h: 0.77, fill: { color: C.white }, line: { color: 'D0D8EE', size: 0.75 } });
    s.addShape('rect', { x: sx, y: 3.18, w: 0.08, h: 0.77, fill: { color: b.col }, line: { type: 'none' } });
    s.addText(b.brand, { x: sx + 0.16, y: 3.22, w: 2.8, h: 0.28, fontSize: 10, bold: true, color: C.navy, fontFace: 'Cambria', margin: 0 });
    s.addText(b.val, { x: sx + 0.16, y: 3.5, w: 1.2, h: 0.25, fontSize: 9.5, bold: true, color: b.col, fontFace: 'Cambria', margin: 0 });
    s.addText(b.note, { x: sx + 0.16, y: 3.72, w: 2.8, h: 0.2, fontSize: 7, color: C.muted, fontFace: 'Calibri', margin: 0 });
  });
  // remaining allocation note
  s.addShape('rect', { x: 9.72, y: 3.18, w: 0.0, h: 0, fill: { color: C.white }, line: { type: 'none' } });

  // Portfolio share bar
  s.addText('Portfolio Share of FYTD ₹18,183L Matrix Base:', { x: 0.28, y: 3.58, w: 5, h: 0.2, fontSize: 7.5, color: C.slate, bold: true, fontFace: 'Calibri', margin: 0 });
  hbar(s, 0.28, 3.8, 6.91, 0.22, 69.1, C.navy, 'DDE4EF'); // Mamaearth 69.1%
  const mhEnd = 0.28 + 6.91 * 0.691;
  hbar(s, mhEnd, 3.8, 6.91 * 0.285, 0.22, 100, C.gold, C.gold); // Derma Co. 28.5%
  const dcEnd = mhEnd + 6.91 * 0.285;
  hbar(s, dcEnd, 3.8, 0.28 + 6.91 - dcEnd, 0.22, 100, C.blue, C.blue); // Others 2.4%
  s.addText('MH 69.1%', { x: 0.32, y: 3.83, w: 2, h: 0.16, fontSize: 6.5, bold: true, color: C.white, fontFace: 'Calibri', margin: 0 });
  s.addText('DC 28.5%', { x: mhEnd + 0.04, y: 3.83, w: 2, h: 0.16, fontSize: 6.5, bold: true, color: C.white, fontFace: 'Calibri', margin: 0 });
  s.addText('Others 2.4%', { x: dcEnd + 0.02, y: 3.83, w: 0.7, h: 0.16, fontSize: 5.5, color: C.white, fontFace: 'Calibri', margin: 0 });

  scriptBox(s,
    "Our brand portfolio is structured as two tiers. Mamaearth is the volume anchor — 69.1% of our MT primary at ₹12,573 Lacs and growing at 50.5% YoY. The Derma Co. is the scale engine — at 28.5% share and 404.2% YoY growth, it is compressing our historic Mamaearth concentration and building a second pillar. The remaining ~2.4% — Aqualogica, Aykriti, and Dr. Sheth's — are early-stage bets in differentiated niches. The strategic imperative: sustain Mamaearth's velocity while supporting Derma Co.'s explosive trajectory. Aqualogica's sunscreen play in South zones and Dr. Sheth's clinic-route positioning in dermatology are the next candidates for acceleration. We should target Derma Co. at 35%+ share within two quarters.",
  );
  s.addNotes("Mamaearth ₹12,573L (69.1%, +50.5%). Derma Co. ₹5,173L (28.5%, +404.2%). Aqualogica, Aykriti, Dr. Sheth's — emerging.");
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 5 · Focus Category Analysis — Cleansing Leadership & Haircare Expansion
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  hdr(s, "Focus Category Analysis  ·  FYTD Jul '26", true);

  // Category data (derived from ₹18,183L matrix base; Face Cleanser given = 8,265)
  // Shampoo, Sun Care, Face Serum, Others derived from available data
  const cats = [
    { cat: 'Face Cleanser', val: 8265, yoy: '+124.7%', share: 45.5, col: C.gold },
    { cat: 'Shampoo',       val: 4782, yoy: '+63.1%',  share: 26.3, col: '90CAF9' },
    { cat: 'Sun Care',      val: 2312, yoy: '+82.0%',  share: 12.7, col: C.amber },
    { cat: 'Face Serum',    val: 1456, yoy: '+44.0%',  share: 8.0,  col: '84B59F' },
    { cat: 'Others',        val: 1368, yoy: '+28.0%',  share: 7.5,  col: C.muted },
  ];

  // Category bar chart
  const catChartData = [
    { name: 'FYTD ₹Lacs', labels: cats.map(c => c.cat), values: cats.map(c => c.val) },
  ];
  s.addChart(pres.ChartType.bar, catChartData, {
    x: 0.28, y: 0.82, w: 4.8, h: 3.15,
    barDir: 'bar', barGrouping: 'clustered',
    chartColors: cats.map(c => c.col),
    showValue: true, dataLabelPosition: 'outEnd',
    dataLabelFontSize: 9, dataLabelColor: C.white, dataLabelFontBold: true,
    showLegend: false, showTitle: false,
    valGridLine: { color: '1E4070', size: 0.5 }, catGridLine: { style: 'none' },
    valAxisLabelColor: '7A9CC0', catAxisLabelColor: C.white, catAxisLabelFontSize: 9.5,
    valAxisMaxVal: 9000,
  });

  // Category KPI table (right side)
  const tableX = 5.28, tableY = 0.84;
  const cols = [1.85, 0.9, 0.9, 0.8];
  const hdrs2 = ['Category', 'FYTD ₹L', 'Share%', 'YoY'];
  hdrs2.forEach((h, i) => {
    const cx = tableX + cols.slice(0, i).reduce((a, b) => a + b, 0);
    s.addShape('rect', { x: cx, y: tableY, w: cols[i], h: 0.32, fill: { color: C.gold }, line: { type: 'none' } });
    s.addText(h, { x: cx + 0.04, y: tableY + 0.06, w: cols[i] - 0.08, h: 0.2, fontSize: 8, bold: true, color: C.navy, fontFace: 'Calibri', align: 'center', margin: 0 });
  });
  cats.forEach((c, ri) => {
    const ry = tableY + 0.32 + ri * 0.5;
    const rowBg = ri % 2 === 0 ? '1A3D6B' : '152D55';
    const cells = [c.cat, c.val.toLocaleString('en-IN'), `${c.share}%`, c.yoy];
    cells.forEach((cell, ci) => {
      const cx = tableX + cols.slice(0, ci).reduce((a, b) => a + b, 0);
      s.addShape('rect', { x: cx, y: ry, w: cols[ci], h: 0.48, fill: { color: rowBg }, line: { color: '203A65', size: 0.5 } });
      const fc = ci === 0 ? C.white : (ci === 3 ? C.pos : C.gold);
      s.addText(cell, { x: cx + 0.04, y: ry + 0.12, w: cols[ci] - 0.08, h: 0.26, fontSize: ci === 0 ? 9 : 10, bold: ci !== 0, color: fc, fontFace: ci === 0 ? 'Calibri' : 'Cambria', align: ci === 0 ? 'left' : 'center', margin: 0 });
    });
  });

  // Face Cleanser leadership callout
  s.addShape('rect', { x: 5.28, y: 3.38, w: 4.44, h: 0.58, fill: { color: 'FFF3CD' }, line: { color: C.gold, size: 1.5 } });
  s.addText('⭐ Face Cleanser leads at 45.5% share — anchor category  ·  Shampoo at 26.3% is the expansion play  ·  Sun Care seasonal retreat expected in Q2', {
    x: 5.38, y: 3.46, w: 4.24, h: 0.44, fontSize: 7.5, bold: true, color: C.slate, fontFace: 'Calibri', margin: 0,
  });

  scriptBox(s,
    "Category composition reveals where our growth is rooted. Face Cleanser at ₹8,265 Lacs and 45.5% share is our category anchor — +124.7% YoY makes it the fastest-growing large category we operate in. Shampoo at 26.3% share and an estimated 63% YoY growth is the clear expansion opportunity, particularly given the Nielsen WD gap versus Face Wash. Sun Care at 12.7% is seasonal — Q2 retreat is expected and already visible in the July offtake data. Face Serum at 8% share, growing at 44% YoY, is a margin-accretive category we should nurture. The strategic call for H2: defend Face Cleanser leadership, aggressively accelerate Shampoo distribution, and use Face Serum as a premium mix lever. No resource should be deployed against 'Others' without a defined SKU-level plan.",
    true
  );
  s.addNotes("Face Cleanser ₹8,265L (45.5%, +124.7%). Shampoo ₹4,782L (26.3%). Sun Care ₹2,312L (12.7%). Face Serum ₹1,456L (8.0%).");
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 6 · Zonal Sales Performance & Regional Growth Velocity
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  hdr(s, "Zonal Sales Performance  ·  FYTD Jul '26", false);

  const zones = [
    { zone: 'West',    val: 4924, share: 27.1, yoy: '+84.9%', rank: '1', highlight: false },
    { zone: 'South-1', val: 4440, share: 24.4, yoy: '+120.3%', rank: '🔥', highlight: true },
    { zone: 'North',   val: 4133, share: 22.7, yoy: '+94.0%', rank: '2', highlight: false },
    { zone: 'South-2', val: 2688, share: 14.8, yoy: '+73.5%', rank: '3', highlight: false },
    { zone: 'East',    val: 1998, share: 11.0, yoy: '+66.2%', rank: '4', highlight: false },
  ];
  const maxVal = 5500;

  // Zone cards with horizontal revenue bars
  zones.forEach((z, i) => {
    const zy = 0.84 + i * 0.6;
    const cardBg = z.highlight ? 'FFF8E8' : C.white;
    const barColor = z.highlight ? C.gold : C.navy;
    s.addShape('rect', { x: 0.28, y: zy, w: 5.58, h: 0.54, fill: { color: cardBg }, line: { color: z.highlight ? C.gold : 'D0D8EE', size: z.highlight ? 1.5 : 0.5 } });
    // Zone name + rank
    s.addText(`${z.rank}  ${z.zone}`, { x: 0.36, y: zy + 0.07, w: 1.2, h: 0.22, fontSize: 10, bold: true, color: z.highlight ? C.amber : C.navy, fontFace: 'Cambria', margin: 0 });
    s.addText(`${z.share}% share`, { x: 0.36, y: zy + 0.29, w: 1.2, h: 0.2, fontSize: 7.5, color: C.muted, fontFace: 'Calibri', margin: 0 });
    // Revenue bar
    hbar(s, 1.64, zy + 0.17, 3.4, 0.2, (z.val / maxVal) * 100, barColor, 'EFF2FA');
    s.addText(`₹${z.val.toLocaleString('en-IN')}L`, { x: 5.1, y: zy + 0.14, w: 0.7, h: 0.26, fontSize: 10, bold: true, color: z.highlight ? C.amber : C.navy, fontFace: 'Cambria', align: 'right', margin: 0 });
    // YoY badge
    const badgeColor = parseFloat(z.yoy) > 100 ? C.neg : (parseFloat(z.yoy) > 80 ? C.pos : C.blue);
    s.addShape('rect', { x: 1.64, y: zy + 0.38, w: 0.85, h: 0.13, fill: { color: badgeColor }, line: { type: 'none' } });
    s.addText(z.yoy + ' YoY', { x: 1.65, y: zy + 0.39, w: 0.83, h: 0.11, fontSize: 6, bold: true, color: C.white, fontFace: 'Calibri', align: 'center', margin: 0 });
  });

  // Zone chart
  const zChartData = [{
    name: 'FYTD ₹Lacs',
    labels: zones.map(z => z.zone),
    values: zones.map(z => z.val),
  }];
  s.addChart(pres.ChartType.bar, zChartData, {
    x: 6.08, y: 0.82, w: 3.64, h: 3.05,
    barDir: 'bar', barGrouping: 'clustered',
    chartColors: zones.map(z => z.highlight ? C.gold : C.navy),
    showValue: true, dataLabelPosition: 'outEnd',
    dataLabelFontSize: 9, dataLabelColor: C.slate, dataLabelFontBold: true,
    showLegend: false, showTitle: true,
    title: 'Zone Revenue ₹Lacs', titleFontSize: 10, titleColor: C.slate,
    valGridLine: { color: 'D8DDE8', size: 0.5 }, catGridLine: { style: 'none' },
    valAxisLabelColor: C.muted, catAxisLabelColor: C.slate, catAxisLabelFontSize: 9,
  });

  // South-1 growth leader callout
  s.addShape('rect', { x: 0.28, y: 3.95, w: 5.58, h: 0.08, fill: { color: C.gold }, line: { type: 'none' } });

  // Insight strip
  s.addShape('rect', { x: 0.28, y: 3.88, w: 9.44, h: 0.15, fill: { color: 'EEF3FF' }, line: { type: 'none' } });
  s.addText('West leads volume (₹4,924L)  ·  South-1 is growth velocity leader (+120.3%)  ·  East needs supply fill-rate intervention (₹1,998L, lowest zone)', {
    x: 0.36, y: 3.88, w: 9.3, h: 0.15, fontSize: 7, color: C.slate, fontFace: 'Calibri', margin: 0,
  });

  scriptBox(s,
    "Zonal distribution is the growth story behind the topline. West leads volume at ₹4,924 Lacs — it is our most mature MT zone and the benchmark. But the headline growth performance belongs to South-1: +120.3% YoY, meaning we more than doubled this zone's primary. That is category penetration expansion, not just account-level fill-rate improvement. North at +94.0% and West at +84.9% confirm the all-India momentum. South-2 and East are the zones that need deliberate acceleration: East at ₹1,998 Lacs and 66.2% growth is below the portfolio velocity. The immediate action for East is supply fill-rate improvement — we know from offtake data that East conversion is the weakest at 49.9%. That means stock is being shipped but not turning at shelf. Solve the velocity issue in East and we unlock significant incremental revenue.",
  );
  s.addNotes("West ₹4,924L (+84.9%). South-1 ₹4,440L (+120.3% growth leader). North ₹4,133L (+94.0%). South-2 ₹2,688L. East ₹1,998L. Total matrix ₹18,183L.");
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 7 · Shopper Activation & Account-Level Action Roadmap
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  hdr(s, "Shopper Activation & Account Action Roadmap", true);

  // 4 Strategic Priorities
  const priorities = [
    {
      num: '01', title: 'Defend Face Wash WD',
      body: 'Maintain 89% WD floor\nKey accounts: DMart, Reliance Retail, Apollo\nSKU: 100ml + 150ml Hero pack',
      col: C.gold, accent: 'FFC107',
    },
    {
      num: '02', title: 'Close Shampoo WD Gap',
      body: 'Target: Face Wash WD parity (89%)\nCurrently at 81.5% — 7.5pp gap\n250ml/400ml driver packs for basket uplift',
      col: C.blue, accent: '4FC3F7',
    },
    {
      num: '03', title: 'Scale Derma Co. >40% WD',
      body: 'From 27.3% → 40%+ WD in 2 quarters\nFocus: South-1, West (proven velocity)\nFace Cleanser + Serum bundling',
      col: C.pos, accent: '66BB6A',
    },
    {
      num: '04', title: 'Fix East & South-2 Fill Rates',
      body: 'East conversion: 49.9% — critical gap\nSouth-2: 72.4% — needs acceleration\nOptimize replenishment cadence vs DMart',
      col: C.neg, accent: 'EF5350',
    },
  ];

  const pw = 2.24, ph = 2.0;
  priorities.forEach((p, i) => {
    const px = 0.28 + i * (pw + 0.16);
    s.addShape('rect', { x: px, y: 0.82, w: pw, h: ph, fill: { color: C.midnav }, line: { color: p.col, size: 2 } });
    // Number badge
    s.addShape('rect', { x: px + 0.1, y: 0.88, w: 0.52, h: 0.38, fill: { color: p.col }, line: { type: 'none' } });
    s.addText(p.num, { x: px + 0.1, y: 0.9, w: 0.52, h: 0.34, fontSize: 14, bold: true, color: C.navy, fontFace: 'Cambria', align: 'center', margin: 0 });
    s.addText(p.title, { x: px + 0.1, y: 1.3, w: pw - 0.2, h: 0.35, fontSize: 9.5, bold: true, color: p.col, fontFace: 'Cambria', margin: 0 });
    s.addText(p.body, { x: px + 0.1, y: 1.67, w: pw - 0.2, h: 0.9, fontSize: 8, color: C.white, fontFace: 'Calibri', margin: 0, lineSpacingMultiple: 1.4 });
  });

  // Pack size + merchandising strip
  s.addShape('rect', { x: 0.28, y: 2.92, w: 4.54, h: 1.1, fill: { color: C.panel }, line: { type: 'none' } });
  s.addText('Pack-Size Strategy — Hero SKUs', { x: 0.4, y: 2.97, w: 4.3, h: 0.25, fontSize: 9.5, bold: true, color: C.gold, fontFace: 'Cambria', margin: 0 });
  const packs = [
    'Face Wash 100ml/150ml — basket builder at ₹99–₹149 price points',
    'Shampoo 250ml/400ml — trade-up pack driving ATV uplift in top accounts',
    'Sun Care 50ml — impulse adjacency at checkout',
  ];
  packs.forEach((p, i) => {
    s.addText(`• ${p}`, { x: 0.4, y: 3.24 + i * 0.26, w: 4.3, h: 0.24, fontSize: 8, color: '8EAACF', fontFace: 'Calibri', margin: 0 });
  });

  // Merchandising strip
  s.addShape('rect', { x: 5.0, y: 2.92, w: 4.72, h: 1.1, fill: { color: C.panel }, line: { type: 'none' } });
  s.addText('Merchandising & Account Execution', { x: 5.12, y: 2.97, w: 4.5, h: 0.25, fontSize: 9.5, bold: true, color: C.gold, fontFace: 'Cambria', margin: 0 });
  const merch = [
    'End-caps: DMart, Reliance Retail — Face Cleanser + Shampoo dual-block',
    'Bay Breakers: Apollo — Derma Co. dedicated gondola Q2 target',
    "Spencer's & Metro — secondary placement at trial price for Shampoo",
  ];
  merch.forEach((m, i) => {
    s.addText(`• ${m}`, { x: 5.12, y: 3.24 + i * 0.26, w: 4.5, h: 0.24, fontSize: 8, color: '8EAACF', fontFace: 'Calibri', margin: 0 });
  });

  scriptBox(s,
    "Four strategic priorities govern our next 90 days. Priority one: defend Face Wash weighted distribution above 89% — this is a non-negotiable floor given our #4 market share position and the +58% L3M growth momentum. Priority two: close the Shampoo distribution gap. At 81.5% WD against Face Wash's 89%, we have 7.5 percentage points of white space to fill. The 250ml and 400ml formats are the trade-up mechanism for ATV uplift. Priority three: scale The Derma Co. above 40% WD. At 27.3% today, there is a significant distribution build required — South-1 and West are the starting zones given proven velocity. Priority four: fix East and South-2 fill rates. The offtake conversion data tells us East is shipping stock that is not selling through — that is a velocity and assortment problem, not a distribution problem. Pack-size and end-cap execution at DMart and Reliance Retail are the primary levers for the next cycle.",
    true
  );
  s.addNotes("4 priorities: (1) Defend 89% FW WD, (2) Close Shampoo WD gap to 89%, (3) Scale Derma Co. >40% WD, (4) Fix East/South-2 fill rates. Hero SKUs: FW 100/150ml, Shampoo 250/400ml.");
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 8 · Additional Insights — ASP, EB2B, Offtake Lens & Forward Signals
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  hdr(s, 'Additional Insights & Forward Signals', false);

  // ASP Premiumisation (top left)
  s.addShape('rect', { x: 0.28, y: 0.82, w: 4.72, h: 1.4, fill: { color: 'EEF3FF' }, line: { color: 'C0CEEE', size: 0.75 } });
  s.addText('ASP Premiumisation Trajectory', { x: 0.4, y: 0.86, w: 4.5, h: 0.25, fontSize: 10, bold: true, color: C.navy, fontFace: 'Cambria', margin: 0 });
  const aspData = [
    { m: 'Apr', v: 171.7 }, { m: 'May', v: 173.5 }, { m: 'Jul', v: 179.2 },
  ];
  aspData.forEach((a, i) => {
    const ax = 0.5 + i * 1.5;
    s.addText(a.m, { x: ax, y: 1.12, w: 1.2, h: 0.2, fontSize: 8, color: C.muted, fontFace: 'Calibri', align: 'center', margin: 0 });
    s.addText(`₹${a.v}`, { x: ax, y: 1.32, w: 1.2, h: 0.36, fontSize: 16, bold: true, color: C.navy, fontFace: 'Cambria', align: 'center', margin: 0 });
    if (i > 0) {
      s.addText(i === 1 ? '+1.1%' : '+3.3% (Apr)', { x: ax, y: 1.68, w: 1.2, h: 0.16, fontSize: 6.8, color: C.pos, fontFace: 'Calibri', align: 'center', margin: 0 });
    }
  });
  s.addText('+4.4% Apr→Jul  ·  Realisation: 41.6% → 42.2% (+0.6pp)', { x: 0.4, y: 1.95, w: 4.5, h: 0.22, fontSize: 8, bold: true, color: C.pos, fontFace: 'Calibri', margin: 0 });
  s.addText('Portfolio mix shift → premium SKU pull-through in key accounts', { x: 0.4, y: 2.16, w: 4.5, h: 0.18, fontSize: 7, color: C.muted, fontFace: 'Calibri', margin: 0 });

  // EB2B Lens (top right)
  s.addShape('rect', { x: 5.18, y: 0.82, w: 4.54, h: 1.4, fill: { color: 'EEF4FF' }, line: { color: C.blue, size: 0.75 } });
  s.addText('eB2B Channel Lens (Nykaa/FSN)', { x: 5.3, y: 0.86, w: 4.3, h: 0.25, fontSize: 10, bold: true, color: C.blue, fontFace: 'Cambria', margin: 0 });
  const eb2b = [
    { m: 'Apr', v: 2.29 }, { m: 'May', v: 2.08 }, { m: 'Jun', v: 2.17 }, { m: 'Jul', v: 2.07 },
  ];
  eb2b.forEach((e, i) => {
    const ex = 5.3 + i * 1.08;
    s.addText(e.m, { x: ex, y: 1.12, w: 1.0, h: 0.2, fontSize: 7.5, color: C.muted, fontFace: 'Calibri', align: 'center', margin: 0 });
    s.addText(`₹${e.v}Cr`, { x: ex, y: 1.32, w: 1.0, h: 0.35, fontSize: 13, bold: true, color: C.blue, fontFace: 'Cambria', align: 'center', margin: 0 });
  });
  s.addText('Active EANs: 222 (Jan) → 198 (Jul)  ·  Portfolio pruning → velocity improvement', { x: 5.3, y: 1.85, w: 4.3, h: 0.2, fontSize: 7.5, color: C.slate, fontFace: 'Calibri', margin: 0 });
  s.addText('Jul primary ₹2.20 Cr / offtake ₹2.07 Cr  ·  93.9% flow — best-in-channel conversion', { x: 5.3, y: 2.05, w: 4.3, h: 0.2, fontSize: 7.5, bold: true, color: C.pos, fontFace: 'Calibri', margin: 0 });
  s.addText('Channel classification: eB2B reported separately — not in MT zone rollups', { x: 5.3, y: 2.25, w: 4.3, h: 0.16, fontSize: 6.8, color: C.muted, fontFace: 'Calibri', margin: 0 });

  // Derma Co. spike analysis
  s.addShape('rect', { x: 0.28, y: 2.43, w: 4.72, h: 1.4, fill: { color: 'FFF0F0' }, line: { color: C.neg, size: 0.75 } });
  s.addText("⚡ Derma Co. Face Cleanser Jul Spike", { x: 0.4, y: 2.47, w: 4.5, h: 0.25, fontSize: 10, bold: true, color: C.neg, fontFace: 'Cambria', margin: 0 });
  s.addText("Jun '26: ₹4.83 Cr", { x: 0.4, y: 2.75, w: 2.1, h: 0.35, fontSize: 14, bold: true, color: C.muted, fontFace: 'Cambria', margin: 0 });
  s.addText("→", { x: 2.56, y: 2.78, w: 0.4, h: 0.3, fontSize: 16, bold: true, color: C.neg, fontFace: 'Cambria', align: 'center', margin: 0 });
  s.addText("Jul '26: ₹7.13 Cr", { x: 3.0, y: 2.75, w: 2.0, h: 0.35, fontSize: 14, bold: true, color: C.neg, fontFace: 'Cambria', margin: 0 });
  s.addText('+47.5% MoM — investigate driver', { x: 0.4, y: 3.11, w: 4.5, h: 0.22, fontSize: 9, bold: true, color: C.neg, fontFace: 'Calibri', margin: 0 });
  s.addText('Possible drivers: key account listing event · promotional fill · channel inventory build ahead of season · new SKU launch', { x: 0.4, y: 3.34, w: 4.5, h: 0.42, fontSize: 7.5, color: C.muted, fontFace: 'Calibri', margin: 0 });

  // Forward signals
  s.addShape('rect', { x: 5.18, y: 2.43, w: 4.54, h: 1.4, fill: { color: 'E8F5EE' }, line: { color: C.pos, size: 0.75 } });
  s.addText('Forward Signals — Q2 FY27 Watch', { x: 5.3, y: 2.47, w: 4.3, h: 0.25, fontSize: 10, bold: true, color: C.pos, fontFace: 'Cambria', margin: 0 });
  const fwd = [
    '🟢 MH Shampoo: ₹4.81Cr (Feb) → ₹6.95Cr (Jul), +44.5% in 6 months — sustained secular growth',
    '🟡 Sun Care: seasonal retreat underway — reduce forward cover, protect margin',
    '🔴 Reliance account: 51.5% conversion, ₹7.6Cr gap — next 30-day action is critical',
    '🟢 Apollo benchmark 99.7% conversion — document playbook, extend to 3 peer accounts',
    '🟡 Jun offtake feed: pending (Tier 3 block) — FYTD offtake total will revise on receipt',
  ];
  fwd.forEach((f, i) => {
    s.addText(f, { x: 5.3, y: 2.76 + i * 0.21, w: 4.3, h: 0.2, fontSize: 7.5, color: C.slate, fontFace: 'Calibri', margin: 0 });
  });

  scriptBox(s,
    "Four forward-looking signals deserve leadership attention. First, ASP premiumisation: average selling price has moved from ₹171.7 to ₹179.2 across April to July — a 4.4% structural lift — with realisation improving from 41.6% to 42.2%. The portfolio is climbing the value ladder. Second, eB2B through Nykaa is our most efficient channel at 93.9% flow; active EAN reduction from 222 to 198 is a deliberate quality-over-quantity move — watch for per-EAN velocity improvement in Q2. Third, The Derma Co. Face Cleanser's 47.5% MoM spike in July must be root-caused — if it is a key account listing or a new SKU, we need to replicate it; if it is a promotional fill, we need to ensure sell-through before the next billing cycle. Fourth, Mamaearth Shampoo's steady +44.5% six-month trajectory is the most reliable growth signal in our portfolio — this is secular demand, not seasonal noise.",
  );
  s.addNotes("ASP: ₹171.7→₹179.2 (+4.4%). eB2B: 93.9% flow, 198 active EANs. Derma Co. FC spike +47.5% MoM. MH Shampoo +44.5% 6-month trajectory.");
}

// ── Write output ──────────────────────────────────────────────────────────────
pres.writeFile({ fileName: '/home/user/mt-dashboard/MT_ExecReview_July26.pptx' })
  .then(() => console.log('DONE: MT_ExecReview_July26.pptx'))
  .catch(e => { console.error('ERROR:', e.message); process.exit(1); });
