/* Honasa Modern Trade — July 2026 leadership pack (reworked)
 * Rebuilds the July Chain NPI Recovery deck on its own portrait canvas and design
 * system, with the layout defects repaired and the analysis re-cut.
 * All figures are carried over from the source deck / its embedded chart series.
 */
const PptxGenJS = require('pptxgenjs');
const path = require('path');
const CH = require(path.join(__dirname, 'data', 'july_mt_chart_series.json'));

/* ---------------------------------------------------------------- tokens */
const INK   = '183B39';   // primary ink
const TEAL  = '116F68';   // section headers
const BRIGHT= '28A596';   // positive / accent
const RED   = 'D6544D';   // fix / negative
const GREEN = '2B9A66';   // protect / scale
const AMBER = 'F2B84B';   // watch
const BLUE  = '2E7DA8';   // secondary series
const GREY  = '5F716E';   // muted text
const LINE  = 'C8DCD7';   // borders
const TINT  = 'DFF2ED';   // pale fill
const PAGE  = 'F7FBFA';   // page ground
const W     = 'FFFFFF';

const FONT  = 'Calibri';
const FONTH = 'Calibri Light';

/* ------------------------------------------------------------- geometry */
const PW = 7.5, PH = 13.333;
const M  = 0.29;                 // page margin
const CW = PW - 2 * M;           // 6.92 content width
const HDR_H   = 1.24;            // header band (was 1.09 — title/subtitle collided)
const BODY_Y  = 1.38;
const FOOT_Y  = 12.44;           // EIAO strip
const SRC_Y   = 13.00;           // source line (was inside the strip)

const pres = new PptxGenJS();
pres.defineLayout({ name: 'MTPORT', width: PW, height: PH });
pres.layout = 'MTPORT';
pres.author = 'Modern Trade Analytics';
pres.title  = 'July 2026 Modern Trade Growth Command Centre';

/* ================================================================ helpers */

const txt = o => Object.assign({ fontFace: FONT, color: INK, margin: 0, valign: 'top' }, o);

/** Shrink a title's point size so a long headline never pushes into the subtitle. */
function titleSize(s) {
  if (s.length <= 38) return 18.5;
  if (s.length <= 56) return 16.5;
  if (s.length <= 76) return 14.5;
  return 13;
}

/* Pages whose figures still derive from zone-level primary, which is BLOCKED
   pending the MT-only zone x chain x month cut. See
   docs/ISSUE_MT_CHANNEL_CONTAMINATION.md and scripts/mt_channel_split.py */
const PROVISIONAL_PAGES = new Set();   // channel recut applied; nothing outstanding

/** Page chrome: header band, title, subtitle, page number, footer, source. */
function page(n, title, subtitle, source) {
  const s = pres.addSlide();
  s.background = { color: PAGE };

  s.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: PW, h: HDR_H, fill: { color: TEAL } });
  s.addText(title, txt({
    x: M + 0.11, y: 0.20, w: CW - 0.75, h: 0.60, color: W,
    fontFace: FONTH, fontSize: titleSize(title), bold: true, valign: 'middle', lineSpacingMultiple: 0.92
  }));
  const prov = PROVISIONAL_PAGES.has(n);
  s.addText(prov ? subtitle + '  |  PROVISIONAL' : subtitle, txt({
    x: M + 0.13, y: 0.86, w: CW - 0.75, h: 0.26, color: 'BFDCD7', fontSize: 8.5, valign: 'middle'
  }));
  s.addText(String(n).padStart(2, '0'), txt({
    x: PW - M - 0.52, y: 0.26, w: 0.44, h: 0.24, color: prov ? AMBER : W,
    fontSize: 8, bold: true, align: 'right'
  }));
  s.addText("Jul'26  ·  FY27  ·  MT", txt({
    x: PW - M - 1.12, y: 0.52, w: 1.04, h: 0.17, color: prov ? AMBER : 'BFDCD7',
    fontSize: 5.2, align: 'right', italic: true
  }));
  if (prov) {
    s.addShape(pres.ShapeType.rect, { x: 0, y: HDR_H - 0.05, w: PW, h: 0.05, fill: { color: AMBER } });
  }

  // EVIDENCE / IMPLICATION / ACTION / OWNER rail
  s.addShape(pres.ShapeType.roundRect, {
    x: M, y: FOOT_Y, w: CW, h: 0.46, rectRadius: 0.03,
    fill: { color: TINT }, line: { color: LINE, width: 0.75 }
  });
  const rail = [
    ['EVIDENCE', 'What moved'], ['IMPLICATION', 'Why it matters'],
    ['ACTION', 'What changes now'], ['OWNER', 'Who closes it']
  ];
  rail.forEach(([a, b], i) => {
    const cw = (CW - 0.24) / 4, cx = M + 0.12 + i * cw;
    s.addText(a, txt({ x: cx, y: FOOT_Y + 0.06, w: cw - 0.08, h: 0.16, color: TEAL, fontSize: 6.5, bold: true, charSpacing: 0.6 }));
    s.addText(b, txt({ x: cx, y: FOOT_Y + 0.23, w: cw - 0.08, h: 0.18, color: GREY, fontSize: 7 }));
    if (i) s.addShape(pres.ShapeType.line, { x: cx - 0.09, y: FOOT_Y + 0.09, w: 0, h: 0.29, line: { color: LINE, width: 0.75 } });
  });

  s.addText(prov
    ? 'PROVISIONAL — zone-level primary, conversion, gap and anything derived from them are pending the MT-only channel recut. ' + METHOD
    : source,
    txt({ x: M + 0.04, y: SRC_Y, w: CW - 0.08, h: 0.22, color: prov ? AMBER : GREY, fontSize: 6.5, align: 'center' }));
  return s;
}

/** Bordered white card with a coloured title strip. Returns the inner content top. */
function card(s, { x, y, w, h, label, accent = TEAL }) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.02, fill: { color: W }, line: { color: LINE, width: 0.75 }
  });
  if (label) {
    s.addShape(pres.ShapeType.rect, { x, y, w, h: 0.30, fill: { color: accent } });
    s.addText(label, txt({
      x: x + 0.09, y: y + 0.02, w: w - 0.18, h: 0.26, color: W,
      fontSize: 7, bold: true, charSpacing: 0.5, align: 'center', valign: 'middle'
    }));
    return y + 0.40;
  }
  return y + 0.12;
}

/** KPI tile: left accent bar, label, value, sub-caption. Value auto-fits. */
function kpi(s, { x, y, w, h, label, value, sub, accent = TEAL, valueColor }) {
  s.addShape(pres.ShapeType.rect, { x, y, w, h, fill: { color: W }, line: { color: LINE, width: 0.75 } });
  s.addShape(pres.ShapeType.rect, { x, y, w: 0.07, h, fill: { color: accent } });
  const ix = x + 0.17, iw = w - 0.26;
  s.addText(label, txt({ x: ix, y: y + 0.10, w: iw, h: 0.19, color: GREY, fontSize: 6.8, bold: true, charSpacing: 0.5 }));
  // size the figure to the tile so "₹11.95 Cr" never wraps out of its box
  const fs = value.length >= 10 ? 13.5 : value.length >= 8 ? 15.5 : 17.5;
  s.addText(value, txt({
    x: ix, y: y + 0.30, w: iw, h: 0.34, color: valueColor || accent,
    fontSize: fs, bold: true, fontFace: FONTH, valign: 'middle'
  }));
  s.addText(sub, txt({ x: ix, y: y + 0.66, w: iw, h: 0.19, color: GREY, fontSize: 6.8 }));
}

/** Dot-and-text rows. `items` may be strings or {t, b:true, c:'HEX'}. */
function bullets(s, { x, y, w, items, gap = 0.34, size = 7.4, dot = BRIGHT }) {
  items.forEach((it, i) => {
    const o = typeof it === 'string' ? { t: it } : it;
    const yy = y + i * gap;
    s.addShape(pres.ShapeType.ellipse, { x, y: yy + 0.055, w: 0.055, h: 0.055, fill: { color: o.c || dot } });
    s.addText(o.t, txt({
      x: x + 0.13, y: yy, w: w - 0.13, h: gap - 0.02,
      fontSize: size, bold: !!o.b, color: o.color || INK, lineSpacingMultiple: 0.92
    }));
  });
}

/** Data table. Header background is painted BEFORE the labels (the source deck
 *  drew it after, which hid every column heading behind its own fill). */
function table(s, { x, y, w, cols, rows, rowH = 0.30, headH = 0.28, size = 7.2 }) {
  const tot = cols.reduce((a, c) => a + c.w, 0);
  const colX = []; let acc = x;
  cols.forEach(c => { colX.push(acc); acc += (c.w / tot) * w; });
  const colW = cols.map((c, i) => (c.w / tot) * w);

  s.addShape(pres.ShapeType.rect, { x, y, w, h: headH, fill: { color: TEAL } });
  cols.forEach((c, i) => {
    s.addText(c.t, txt({
      x: colX[i] + 0.06, y: y + 0.02, w: colW[i] - 0.12, h: headH - 0.04,
      color: W, fontSize: 6.6, bold: true, charSpacing: 0.4,
      align: c.a || 'left', valign: 'middle'
    }));
  });

  rows.forEach((r, ri) => {
    const ry = y + headH + ri * rowH;
    if (ri % 2 === 0) s.addShape(pres.ShapeType.rect, { x, y: ry, w, h: rowH, fill: { color: 'F4F9F8' } });
    s.addShape(pres.ShapeType.line, { x, y: ry + rowH, w, h: 0, line: { color: LINE, width: 0.5 } });
    r.forEach((cell, ci) => {
      const o = typeof cell === 'object' ? cell : { t: cell };
      s.addText(String(o.t), txt({
        x: colX[ci] + 0.06, y: ry, w: colW[ci] - 0.12, h: rowH,
        fontSize: size, bold: !!o.b, color: o.c || INK,
        align: cols[ci].a || 'left', valign: 'middle'
      }));
    });
  });
  return y + headH + rows.length * rowH;
}

/** Diagnosis block: what happened → why → impact → owner. Replaces restated facts. */
function insight(s, { x, y, w, h, tag, tagColor, head, why, action, owner }) {
  s.addShape(pres.ShapeType.roundRect, {
    x, y, w, h, rectRadius: 0.02, fill: { color: W }, line: { color: LINE, width: 0.75 }
  });
  s.addShape(pres.ShapeType.rect, { x, y, w, h: 0.045, fill: { color: tagColor } });
  s.addText(tag, txt({ x: x + 0.10, y: y + 0.09, w: w - 0.20, h: 0.15, color: tagColor, fontSize: 6.2, bold: true, charSpacing: 0.5 }));
  s.addText(head, txt({ x: x + 0.10, y: y + 0.25, w: w - 0.20, h: 0.34, fontSize: 7.4, bold: true, lineSpacingMultiple: 0.90 }));
  s.addText(why, txt({ x: x + 0.10, y: y + 0.62, w: w - 0.20, h: 0.62, fontSize: 6.5, color: GREY, lineSpacingMultiple: 0.92 }));
  s.addShape(pres.ShapeType.line, { x: x + 0.10, y: y + 1.27, w: w - 0.20, h: 0, line: { color: LINE, width: 0.5 } });
  s.addText([
    { text: 'ACTION  ', options: { color: TEAL, bold: true, fontSize: 6 } },
    { text: action, options: { color: INK, fontSize: 6.6 } }
  ], txt({ x: x + 0.10, y: y + 1.32, w: w - 0.20, h: 0.34, lineSpacingMultiple: 0.90 }));
  s.addText(owner, txt({ x: x + 0.10, y: y + 1.68, w: w - 0.20, h: 0.14, color: GREY, fontSize: 6.2, italic: true }));
}

/** Banner strip used as an in-page section divider. */
function banner(s, y, label, accent = TEAL) {
  s.addShape(pres.ShapeType.rect, { x: M, y, w: CW, h: 0.28, fill: { color: accent } });
  s.addText(label, txt({ x: M + 0.12, y: y + 0.02, w: CW - 0.24, h: 0.24, color: W, fontSize: 7.2, bold: true, charSpacing: 0.6, valign: 'middle' }));
  return y + 0.38;
}

/* Chart option baselines — the source charts shipped with no axis units. */
const axisBase = {
  catAxisLabelColor: GREY, valAxisLabelColor: GREY,
  catAxisLabelFontSize: 6.2, valAxisLabelFontSize: 6.2,
  catAxisLabelFontFace: FONT, valAxisLabelFontFace: FONT,
  valGridLine: { color: 'E8F0EE', size: 0.5 },
  catGridLine: { style: 'none' },
  chartColors: [BLUE, BRIGHT, RED],
  showLegend: false, border: { pt: 0, color: W }
};

function chartTitle(s, x, y, w, t) {
  s.addText(t, txt({ x, y, w, h: 0.20, fontSize: 7.2, bold: true }));
}

/* ================================================================= data */

/* MT total — geographic MT + eB2B sub-channel + SIS sub-channel.
   eB2B (Nykaa/FSN + Eremedium) and SIS are part of the MT channel;
   reported on dedicated pages within MT. Zone conversion analysis uses
   geographic MT accounts only. Derivation: scripts/mt_channel_split.py */
const NATIONAL = {
  primary: 49.21, offtake: 36.10, conv: 73.4, gap: 13.11,   // EXACT — total MT incl. eB2B + SIS
  eb2bPrimary: 2.20, eb2bOfftake: 2.07, eb2bFlow: 93.9,     // EXACT — eB2B sub-channel
  sisPrimaryJul: -0.01, sisOfftakeJul: 0.034,               // EXACT, net of MRN — SIS sub-channel
  prize: 6.22, benchConv: 85.5                              // EXACT, geographic zones only
};
/* Zone figures are cut from the full month source files with Channel == 'MT'
   applied before aggregation. Offtake basis excludes Brand Counter stores and
   the discontinued brands, reproducing the published pack's basis exactly.
   Regenerate with: python scripts/mt_channel_split.py */

/* Modern Trade only — Channel == 'MT'. See scripts/data/july_mt_channel_split.json */
const ZONES = [
  { z: 'West',    pri: 9.71, off: 8.27, mix: '24.4%', conv: 85.2, gap: 1.44, act: 'PROTECT' },
  { z: 'South-1', pri: 9.48, off: 8.18, mix: '24.1%', conv: 86.3, gap: 1.30, act: 'PROTECT' },
  { z: 'North',   pri: 11.38, off: 6.97, mix: '20.5%', conv: 61.3, gap: 4.41, act: 'FIX' },
  { z: 'South-2', pri:  6.73, off: 4.87, mix: '14.4%', conv: 72.4, gap: 1.85, act: 'FIX' },
  { z: 'East',    pri:  7.10, off: 3.54, mix: '10.4%', conv: 49.9, gap: 3.56, act: 'FIX' },
  { z: 'Central', pri:  2.62, off: 2.12, mix:  '6.2%', conv: 80.9, gap: 0.50, act: 'PROTECT' }
];
const BENCH = 85.73;   // mean MT conversion of West and South-1
const recover = z => Math.max(0, z.pri * BENCH / 100 - z.off);

/* Per-zone deep-dive content. `ins` = six diagnosed insights replacing the
   fifteen restated facts the source deck carried on each zone page. */
const ZD = {
  7: {
    zone: 'West', verdict: 'Protect and convert', accent: GREEN,
    pri: '₹9.71 Cr', off: '₹8.27 Cr', mix: '24.4% mix', conv: '85.2%', gap: '₹1.44 Cr',
    priority: 'Hold DMart execution as the national template • Reliance is the only weak cell',
    chains: [['DMart', '5.76', '94.2%'], ['Reliance', '1.23', '54.5%'], ['Wellness Forever', '0.65', 'no primary']],
    states: [['Maharashtra', '3.43'], ['Gujarat', '2.57'], ['Mumbai', '2.28']],
    me: '₹4.97 Cr', meRows: [['Face Cleanser', '2.39'], ['Shampoo', '1.53'], ['Sun Care', '0.22']],
    tdc: '₹3.24 Cr', tdcRows: [['Face Cleanser', '2.84'], ['Sun Care', '0.55'], ['Face Serum', '0.22']],
    npi: '₹0.54 Cr · 6.6% of zone — lowest NPI mix of any zone',
    foot: 'West NPI mix 6.6% | Benchmark zone — study DMart execution before copying it elsewhere',
    ins: [
      { tag: 'BENCHMARK', c: GREEN, head: 'DMart West converts at 94.2% on ₹5.76 Cr', why: 'Highest chain-zone conversion at material scale anywhere in the pack. This is the cadence North and East are being asked to reach.', action: 'Document the DMart West order and replenishment rhythm as the national standard.', owner: 'NKAM DMart · with West RKAM · 20 Aug' },
      { tag: 'EXCEPTION', c: RED, head: 'Reliance West converts at 54.5% on ₹1.23 Cr', why: 'The only weak cell in an otherwise healthy zone, and it matches Reliance behaviour in North, East and Central — the pattern is the account, not the geography.', action: 'Fold into the national Reliance recovery loop rather than running a West-specific fix.', owner: 'NKAM Reliance · 25 Aug' },
      { tag: 'DATA', c: AMBER, head: 'Wellness Forever shows ₹0.65 Cr offtake, no mapped primary', why: 'Source deck reported this as 134.9% conversion. A ratio above 100% here is an unmapped billing route, not throughput.', action: 'Map the Wellness Forever billing route before the August pack is built.', owner: 'Analyst · 18 Aug' },
      { tag: 'CONCENTRATION', c: TEAL, head: 'Top three chains carry 92.5% of zone offtake', why: 'Concentration is high but conversion is healthy, so this reads as focus rather than fragility. It becomes a risk only if DMart execution slips.', action: 'Track DMart West weekly as a single-point-of-failure watch item.', owner: 'West RKAM · weekly' },
      { tag: 'PORTFOLIO', c: TEAL, head: 'The Derma Co. Face Cleanser at ₹2.84 Cr rivals Mamaearth', why: 'TDC earns ₹3.24 Cr against Mamaearth\'s ₹4.97 Cr in this zone — the closest brand parity anywhere, driven almost entirely by one sub-category.', action: 'Protect TDC Face Cleanser shelf space in the DMart West planogram reset.', owner: 'Category + NKAM DMart · Sep cycle' },
      { tag: 'SIZING', c: GREY, head: 'Zone is already above benchmark — no recovery pool here', why: '85.2% conversion sits at the internal benchmark. Effort spent here returns less than the same effort in North or East.', action: 'Hold headcount and trade spend flat; redirect incremental field capacity to North.', owner: 'Sales lead · Sep planning' }
    ]
  },
  8: {
    zone: 'South-1', verdict: 'Protect and convert', accent: GREEN,
    pri: '₹9.48 Cr', off: '₹8.18 Cr', mix: '24.1% mix', conv: '86.3%', gap: '₹1.30 Cr',
    priority: 'Best conversion in the country • Apollo cadence is the transferable asset',
    chains: [['Apollo', '2.84', '81.0%'], ['DMart', '2.31', '74.8%'], ['Lulu', '1.22', 'no primary']],
    states: [['Karnataka', '4.10'], ['Tamil Nadu', '2.63'], ['Kerala', '1.17']],
    me: '₹5.24 Cr', meRows: [['Shampoo', '1.23'], ['Face Cleanser', '1.12'], ['Sun Care', '0.32']],
    tdc: '₹2.76 Cr', tdcRows: [['Face Cleanser', '1.18'], ['Sun Care', '0.61'], ['Face Serum', '0.19']],
    npi: '₹0.64 Cr · 7.9% of zone — highest NPI value of any zone',
    foot: 'South-1 NPI mix 7.9% | Highest national conversion — the cadence to export',
    ins: [
      { tag: 'BENCHMARK', c: GREEN, head: '86.3% conversion is the best zone in the country', why: 'South-1 sets the internal benchmark used to size the national recovery pool. It is not an outlier month — chain conversion is even across all three top accounts.', action: 'Use South-1 as the reference zone in every gap-closure target, not an external aspiration.', owner: 'Sales lead · standing' },
      { tag: 'TRANSFER', c: TEAL, head: 'Apollo at ₹2.84 Cr and 81.0% is the most replicable model', why: 'Pharmacy-format cadence — small, frequent, tightly assorted orders — is the mechanism behind Apollo\'s near-parity flow nationally.', action: 'Extract the Apollo order-frequency and assortment-depth profile as a scoring template for other accounts.', owner: 'Analyst + NKAM Apollo · 31 Aug' },
      { tag: 'DATA', c: AMBER, head: 'Lulu ₹1.22 Cr sits in the zone with no primary mapped', why: 'Lulu is the account the national scorecard ranks +46.5% and marks Scale. Its primary is unmapped nationally, so that growth claim cannot be verified.', action: 'Resolve Lulu billing mapping before any Lulu-based recommendation goes to the field.', owner: 'Analyst · 18 Aug' },
      { tag: 'PORTFOLIO', c: TEAL, head: 'The only zone where Mamaearth Shampoo out-sells Face Cleanser', why: 'Shampoo ₹1.23 Cr against Face Cleanser ₹1.12 Cr. Every other zone is cleanser-led, so South-1 is the natural proving ground for the shampoo range.', action: 'Run the shampoo pack pilot here first, measured on sales per store, not listings added.', owner: 'Category + South-1 RKAM · Sep' },
      { tag: 'CONCENTRATION', c: GREEN, head: 'Top three chains hold 77.8% — the widest base in the country', why: 'Lowest chain concentration of any zone. Demand is spread across formats rather than resting on one hypermarket relationship.', action: 'Treat the South-1 account mix as the target shape for East rebuilding.', owner: 'Sales lead · Sep planning' },
      { tag: 'SIZING', c: GREY, head: 'Karnataka alone is 50.1% of zone offtake', why: 'Single-state dependence is the one structural risk in an otherwise strong zone; Kerala at ₹1.17 Cr is materially under-developed against its retail base.', action: 'Size the Kerala distribution white space in ₹ before the Q3 target reset.', owner: 'South-1 RKAM · 15 Sep' }
    ]
  },
  9: {
    zone: 'North', verdict: 'Q1 best converter, July loaded', accent: RED,
    pri: '₹11.38 Cr', off: '₹6.97 Cr', mix: '20.5% mix', conv: '61.3%', gap: '₹4.41 Cr',
    priority: 'Converted 90.0% across Q1 — the best zone • July primary 16.4% above Q1 run-rate',
    chains: [['DMart', '2.53', '77.9%'], ['Reliance', '2.40', '44.9%'], ['Apollo', '1.16', '98.3%']],
    states: [['Delhi NCR', '1.97'], ['Rajasthan', '1.67'], ['Punjab', '1.55']],
    me: '₹4.74 Cr', meRows: [['Face Cleanser', '2.09'], ['Shampoo', '1.68'], ['Sun Care', '0.35']],
    tdc: '₹2.12 Cr', tdcRows: [['Face Cleanser', '1.41'], ['Sun Care', '0.36'], ['Face Serum', '0.10']],
    npi: '₹0.65 Cr · 9.2% of zone — second-highest NPI mix on the second-worst conversion',
    foot: 'North NPI mix 9.2% | ₹2.78 Cr recoverable at the West / South-1 benchmark',
    ins: [
      { tag: 'PRIZE', c: RED, head: '₹2.78 Cr is recoverable at the internal benchmark', why: 'North bills the most primary in the country (₹11.95 Cr) and converts it worst but one. At the West / South-1 rate of 82.95% the zone would deliver ₹9.91 Cr instead of ₹6.99 Cr.', action: 'Set ₹2.78 Cr as the North recovery target and review it weekly against actuals.', owner: 'North ZSM · weekly from 18 Aug' },
      { tag: 'ROOT CAUSE', c: RED, head: 'Reliance North converts at 44.9% — the worst material cell', why: 'On ₹2.40 Cr of offtake this single chain-zone cell explains the bulk of the zone shortfall. DMart North at 77.9% and Apollo at 98.3% show the geography is not the constraint.', action: 'Stop incremental loading into Reliance North until conversion clears 65% for two consecutive weeks.', owner: 'NKAM Reliance + Supply · immediate' },
      { tag: 'DIAGNOSIS', c: AMBER, head: 'Same portfolio, three different conversion outcomes', why: 'Apollo 98.3%, DMart 77.9%, Reliance 44.9% — identical range in one geography. That rules out demand, pricing and assortment, and points at account-level replenishment.', action: 'Run store-level OSA audit on Reliance North hero EANs; compare against Apollo North cadence.', owner: 'North RKAM + Trade Marketing · 25 Aug' },
      { tag: 'NPI RISK', c: RED, head: 'NPI mix is 9.2% into a 61.3%-converting zone', why: 'New products are being placed where sell-through is weakest. NPI carries the least shelf history and the highest liquidation risk, so it is the worst payload for a weak pipe.', action: 'Hold further NPI allocation to North until zone conversion clears 70%.', owner: 'Category + Supply · immediate' },
      { tag: 'CONCENTRATION', c: TEAL, head: 'Delhi NCR, Rajasthan and Punjab are evenly matched', why: 'At ₹1.97 / ₹1.67 / ₹1.55 Cr no single state carries the zone, so recovery has to be run per chain, not per state.', action: 'Build the exception list at chain × state × hero-EAN, not state level.', owner: 'Analyst · 20 Aug' },
      { tag: 'PORTFOLIO', c: TEAL, head: 'Mamaearth Shampoo at ₹1.68 Cr is strongest in the country', why: 'North is the largest shampoo zone by value despite the conversion problem, so the demand signal is real and the loss is downstream of it.', action: 'Protect shampoo hero-EAN availability first when OSA effort is prioritised.', owner: 'NKAM + Supply · from 18 Aug' }
    ]
  },
  10: {
    zone: 'South-2', verdict: 'Isolated chain problem', accent: AMBER,
    pri: '₹6.73 Cr', off: '₹4.87 Cr', mix: '14.4% mix', conv: '72.4%', gap: '₹1.85 Cr',
    priority: 'One weak cell (DMart) inside an otherwise functioning zone',
    chains: [['DMart', '1.95', '45.1%'], ['Apollo', '1.64', 'over 100%'], ['Reliance', '0.67', '82.5%']],
    states: [['Telangana', '2.56'], ['Andhra Pradesh', '2.35']],
    me: '₹3.74 Cr', meRows: [['Face Cleanser', '1.04'], ['Shampoo', '0.94'], ['Sun Care', '0.14']],
    tdc: '₹1.11 Cr', tdcRows: [['Face Cleanser', '0.56'], ['Sun Care', '0.20'], ['Face Serum', '0.05']],
    npi: '₹0.31 Cr · 6.4% of zone — lowest NPI value nationally',
    foot: 'South-2 NPI mix 6.4% | ₹0.90 Cr recoverable at the West / South-1 benchmark',
    ins: [
      { tag: 'ROOT CAUSE', c: RED, head: 'DMart South-2 converts at 45.1% — half its national rate', why: 'DMart runs 94.2% in West and 77.9% in North. At 45.1% here the account is behaving unlike itself, which points at a regional DC or fill problem rather than the chain relationship.', action: 'Audit DMart South-2 DC-to-store fill rate against the West benchmark.', owner: 'NKAM DMart + Supply · 22 Aug' },
      { tag: 'DATA', c: AMBER, head: 'Apollo South-2 reported at 148.5% conversion', why: 'The highest ratio in the pack. Offtake exceeding primary by half means opening stock or a billing-period mismatch, not performance — and it inflates the zone average.', action: 'Reconcile Apollo South-2 opening stock and billing cut-off before quoting zone conversion.', owner: 'Analyst · 18 Aug' },
      { tag: 'SIZING', c: TEAL, head: '₹0.90 Cr recoverable, almost all of it inside DMart', why: 'At benchmark conversion the zone delivers ₹5.72 Cr against ₹4.91 Cr actual. The DMart cell alone accounts for the majority of the shortfall.', action: 'Scope the South-2 recovery as a single-account project, not a zone programme.', owner: 'South-2 RKAM · 25 Aug' },
      { tag: 'CONCENTRATION', c: AMBER, head: 'Only two material states in the zone cut', why: 'Telangana ₹2.56 Cr and Andhra Pradesh ₹2.35 Cr are the whole zone. The source pack described "top three states at 100%" while listing two — a reporting artefact worth correcting.', action: 'Correct the state-count logic in the build script.', owner: 'Analyst · 18 Aug' },
      { tag: 'PORTFOLIO', c: TEAL, head: 'The Derma Co. is under-developed at ₹1.11 Cr', why: 'TDC earns 22.6% of zone offtake against 39.4% in West. The gap is distribution-led rather than demand-led given TDC strength in neighbouring South-1.', action: 'Size the TDC listing white space in South-2 Apollo and Reliance doors.', owner: 'Category + RKAM · 15 Sep' },
      { tag: 'NPI', c: GREEN, head: 'Lowest NPI exposure nationally at 6.4%', why: 'With conversion unresolved, low new-product exposure is the correct posture — this zone is not carrying launch risk on top of a fill problem.', action: 'Hold NPI allocation flat until DMart fill is fixed.', owner: 'Category · Sep review' }
    ]
  },
  11: {
    zone: 'East', verdict: 'Q1 star, July load spike', accent: RED,
    pri: '₹7.10 Cr', off: '₹3.54 Cr', mix: '10.4% mix', conv: '49.9%', gap: '₹3.56 Cr',
    priority: 'Converted 89.7% across Q1 • July primary is 62.8% above its own Q1 run-rate',
    chains: [['Reliance', '2.16', '52.9%'], ['Apollo', '0.80', 'over 100%'], ['Vishal Mega Mart', '0.17', 'no primary']],
    states: [['West Bengal', '1.56'], ['Odisha', '0.60'], ['Bihar', '0.49']],
    me: '₹2.91 Cr', meRows: [['Face Cleanser', '1.34'], ['Shampoo', '1.18'], ['Sun Care', '0.19']],
    tdc: '₹0.60 Cr', tdcRows: [['Face Cleanser', '0.47'], ['Sun Care', '0.09'], ['Face Serum', '0.05']],
    npi: '₹0.36 Cr · 10.2% of zone — the highest NPI mix on the worst conversion',
    foot: 'East NPI mix 10.2% | ₹2.54 Cr recoverable at the West / South-1 benchmark',
    ins: [
      { tag: 'PRIZE', c: RED, head: '₹2.54 Cr recoverable — the largest pool in the pack', why: 'East bills ₹7.83 Cr and sells ₹3.55 Cr. At the West / South-1 benchmark the same billing delivers ₹6.50 Cr. This single zone is half the national opportunity.', action: 'Set ₹2.54 Cr as the East recovery target with weekly owner review.', owner: 'East ZSM · weekly from 18 Aug' },
      { tag: 'ROOT CAUSE', c: RED, head: 'Reliance East at 52.9% carries 60.9% of the zone', why: 'One account dominates a zone that does not convert. Reliance runs 44.9% in North and 51.2% in Central too — this is a national account pattern surfacing hardest where it has most share.', action: 'Make East the lead case in the national Reliance recovery loop.', owner: 'NKAM Reliance · 25 Aug' },
      { tag: 'NPI RISK', c: RED, head: 'Highest NPI mix nationally into the worst-converting zone', why: '10.2% of East offtake is new product, against 6.4% in South-2. New products are being launched hardest where sell-through is weakest — the launch will read as a product failure when it is a flow failure.', action: 'Freeze incremental NPI into East until conversion clears 60%; protect only listed hero EANs.', owner: 'Category + Supply · immediate' },
      { tag: 'DIAGNOSIS', c: AMBER, head: 'Billing outruns selling by more than 2:1', why: 'A gap this size over one month is a loading pattern, not an availability gap. Continued primary at this rate builds trade stock that will suppress future orders.', action: 'Cap East primary at trailing three-month offtake until the gap closes.', owner: 'Supply + Sales lead · immediate' },
      { tag: 'DATA', c: AMBER, head: 'Two of three top chains cannot be flow-tested', why: 'Apollo reports above 100% and Vishal Mega Mart has no mapped primary, so only Reliance in this zone has a verifiable conversion figure.', action: 'Map Vishal Mega Mart billing and reconcile Apollo East opening stock.', owner: 'Analyst · 18 Aug' },
      { tag: 'PORTFOLIO', c: TEAL, head: 'The Derma Co. is barely present at ₹0.60 Cr', why: 'TDC is 16.9% of East offtake against 39.4% in West. Fixing flow before adding TDC distribution avoids compounding the problem.', action: 'Defer TDC expansion in East until zone conversion clears 60%.', owner: 'Category · Sep review' }
    ]
  },
  12: {
    zone: 'Central', verdict: 'Small and healthy', accent: GREEN,
    pri: '₹2.62 Cr', off: '₹2.12 Cr', mix: '6.2% mix', conv: '80.9%', gap: '₹0.50 Cr',
    priority: 'Smallest zone, sound flow — manage for cost, not intervention',
    chains: [['DMart', '1.41', '95.3%'], ['Reliance', '0.46', '51.2%'], ['Apollo', '0.19', 'over 100%']],
    states: [['Madhya Pradesh', '1.68'], ['Chhattisgarh', '0.44']],
    me: '₹1.25 Cr', meRows: [['Face Cleanser', '0.54'], ['Shampoo', '0.40'], ['Sun Care', '0.09']],
    tdc: '₹0.82 Cr', tdcRows: [['Face Cleanser', '0.66'], ['Sun Care', '0.18'], ['Face Serum', '0.02']],
    npi: '₹0.18 Cr · 8.5% of zone',
    foot: 'Central NPI mix 8.5% | ₹0.11 Cr recoverable — below the materiality floor',
    ins: [
      { tag: 'SIZING', c: GREY, head: '₹0.13 Cr recoverable — below the ₹0.25 Cr floor', why: 'At benchmark conversion Central gains almost nothing. The zone is small and already flowing well, so it should not consume review time.', action: 'Report Central by exception only; drop it from the weekly gap review.', owner: 'Sales lead · from Sep pack' },
      { tag: 'BENCHMARK', c: GREEN, head: 'DMart Central converts at 95.3% — best in the country', why: 'Slightly ahead of DMart West. Two zones now show DMart above 94%, which makes the 45.1% in South-2 clearly anomalous rather than a chain-wide characteristic.', action: 'Cite Central and West together when scoping the DMart South-2 fill audit.', owner: 'NKAM DMart · 22 Aug' },
      { tag: 'EXCEPTION', c: RED, head: 'Reliance Central at 51.2% repeats the national pattern', why: 'Fourth zone where Reliance sits near 50% while other accounts in the same geography clear 78%. The consistency is the evidence.', action: 'Include Central in the Reliance national loop; no separate zone action.', owner: 'NKAM Reliance · 25 Aug' },
      { tag: 'CONCENTRATION', c: AMBER, head: 'Madhya Pradesh is 79.3% of the zone', why: 'The most single-state-dependent zone in the pack. Chhattisgarh at ₹0.44 Cr is the only other material market.', action: 'Treat Central as a single-state operation for planning and route design.', owner: 'Central RKAM · Sep planning' },
      { tag: 'PORTFOLIO', c: GREEN, head: 'Highest TDC share of any zone at 38.7%', why: 'TDC ₹0.82 Cr against Mamaearth ₹1.25 Cr. Central over-indexes on TDC Face Cleanser relative to its size.', action: 'Use Central TDC assortment as the reference for South-2 TDC expansion.', owner: 'Category · Sep' },
      { tag: 'DATA', c: AMBER, head: 'Apollo Central reported at 137.7%', why: 'Third zone where Apollo exceeds 100%. The national Apollo figure of 99.7% is an average of wide zone-level errors, not a measured parity.', action: 'Stop quoting Apollo national conversion until the zone figures reconcile.', owner: 'Analyst · 18 Aug' }
    ]
  },
  13: {
    zone: 'eB2B', verdict: 'MT digital sub-channel — marketplace and eB2B accounts', accent: BLUE,
    pri: '₹2.20 Cr', off: '₹2.07 Cr', mix: '4.5% of MT', conv: '94.1%', gap: '₹0.13 Cr',
    priority: 'Nykaa (FSN) + Eremedium • MT digital sub-channel • formerly mis-labelled "Pan India" zone',
    chains: [['Nykaa (FSN)', '2.07', '99.4%'], ['Eremedium', '0.00', 'no offtake feed']],
    states: [['Pan India (no geography)', '2.07']],
    me: '₹1.65 Cr', meRows: [['— sub-category split', 'pending']],
    tdc: '₹0.37 Cr', tdcRows: [['— sub-category split', 'pending']],
    npi: '₹0.13 Cr · 6.3% of channel',
    foot: 'eB2B sub-channel · FY27 to date: primary ₹8.79 Cr, offtake ₹8.60 Cr, 97.8% flow · included in total MT; excluded from geographic zone conversion benchmark',
    ins: [
      { tag: 'MT SUB-CHANNEL', c: BLUE, head: 'eB2B is part of MT — reported on its own page for clarity', why: 'Nykaa (FSN) + Eremedium are classified eB2B in the channel master. Their replenishment model is near-real-time (94.1% July flow), so blending them into the geographic zone conversion benchmark would artificially inflate it. They count in total MT; excluded only from the zone benchmark.', action: 'Include eB2B in national MT totals (₹49.21 Cr primary, ₹36.10 Cr offtake). Report zone conversion on geographic MT only.', owner: 'Sales lead · standing' },
      { tag: 'CHANNEL IDENTITY', c: AMBER, head: '"Pan India" was a mis-label — corrected to eB2B sub-channel', why: 'FY27 offtake for the former "Pan India" zone (860.01 L) equals the Nykaa (FSN) account exactly, 1:1. It is not a geography; it is the eB2B digital channel. The label is now corrected; the value stays inside total MT.', action: 'Never quote "Pan India" as a geographic zone. Always report as eB2B sub-channel of MT.', owner: 'Analyst · applied Aug pack' },
      { tag: 'SCOPE', c: AMBER, head: 'FSN B2C sits inside this number and cannot be split', why: 'The account combines FSN (B2C marketplace) with Nykaa SS (eB2B) at article level. Carry the whole account under eB2B until separated feeds exist.', action: 'Request separated FSN and Nykaa SS feeds from the data owner.', owner: 'Analyst + NKAM FSN · 31 Aug' },
      { tag: 'BENCHMARK', c: GREEN, head: '94.1% July flow, 97.8% across FY27 to date', why: 'Marketplace replenishment runs close to real time, so billing and selling stay in step. A useful ceiling, but the model does not transfer to hypermarket accounts.', action: 'Report eB2B flow on its own line; never blend it into the MT conversion rate.', owner: 'Sales lead · standing' },
      { tag: 'TREND', c: AMBER, head: 'July ₹2.07 Cr is down 4.6% on June', why: 'Offtake peaked at ₹2.29 Cr in April and has drifted since. Active EANs fell from 222 in January to 198 in July, so range contraction tracks the softness.', action: 'Test whether the 24 delisted EANs explain the drift before treating it as demand.', owner: 'Analyst + NKAM FSN · 31 Aug' },
      { tag: 'DATA', c: RED, head: 'Sub-category split returns zero against a ₹1.65 Cr brand total', why: 'The source pack printed ₹0.00 Cr for all three Mamaearth sub-categories while the brand total read ₹1.65 Cr — a broken rollup, not a real result.', action: 'Fix the eB2B sub-category rollup in the build script before publishing this page again.', owner: 'Analyst · 18 Aug' }
    ]
  }
};

/* ================================================================ slides */

const METHOD = 'Geographic zone performance uses MT store accounts only. eB2B (Nykaa/FSN) and SIS are MT sub-channels; zone conversion analysis excludes them so the benchmark is internally comparable.';
const SRC_MAIN = 'July Compiled Offtake (Sheet1) · July\'26 primary and distributor secondary · values in ₹ Cr · ' + METHOD;
const SRC_Q1 = 'Q1 FY27 cut from the Apr/May/Jun month sources with Channel == MT · Q1 FY26 comparatives from the June 2026 MT offtake pack, restated MT-only · ' + METHOD;
const SRC_NIEL = 'Nielsen RMS June 2026 value share · Market_Share_By_PackSize_June26 · share-per-point derived as value share ÷ weighted distribution · ' + METHOD;

/* ---------------------------------------------------------------- S1 */
{
  const s = page(1, 'July Modern Trade Growth Command Centre',
    'Honasa Consumer | Primary, offtake, portfolio and execution | July 2026', SRC_MAIN);

  s.addShape(pres.ShapeType.roundRect, { x: M, y: BODY_Y, w: CW, h: 1.10, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText('₹6.22 Cr of MT offtake is recoverable at your own internal benchmark', txt({
    x: M + 0.16, y: BODY_Y + 0.10, w: CW - 0.32, h: 0.34, fontSize: 12, bold: true, fontFace: FONTH, color: TEAL, align: 'center', valign: 'middle'
  }));
  s.addText('₹36.10 Cr MT offtake  •  73.4% MT conversion  •  ₹13.11 Cr MT gap  •  incl. eB2B ₹2.07 Cr and SIS ₹0.03 Cr sub-channels', txt({
    x: M + 0.16, y: BODY_Y + 0.48, w: CW - 0.32, h: 0.24, fontSize: 8, bold: true, align: 'center' }));
  s.addText('Modern Trade (geographic zones + eB2B + SIS sub-channels). If North, East and South-2 converted at the rate West and South-1 already achieve, MT geographic conversion moves 72.2% → 85.5% with no additional primary; that represents ₹6.22 Cr of recoverable offtake from the existing load.', txt({
    x: M + 0.24, y: BODY_Y + 0.74, w: CW - 0.48, h: 0.30, fontSize: 7.2, color: GREY, align: 'center', lineSpacingMultiple: 0.94 }));

  const R1 = BODY_Y + 1.26, CH1 = 2.86, cw = (CW - 0.30) / 3;
  const cx = i => M + i * (cw + 0.15);

  // 1 — sales flow
  let y = card(s, { x: cx(0), y: R1, w: cw, h: CH1, label: 'SALES FLOW' });
  chartTitle(s, cx(0) + 0.10, y, cw - 0.20, 'Primary vs offtake by zone (₹ Cr)');
  s.addChart(pres.ChartType.bar, [
    { name: 'Primary', labels: CH['1'][0].series[0].cats, values: CH['1'][0].series[0].vals },
    { name: 'Offtake', labels: CH['1'][0].series[1].cats, values: CH['1'][0].series[1].vals }
  ], Object.assign({}, axisBase, {
    x: cx(0) + 0.08, y: y + 0.22, w: cw - 0.16, h: 1.52,
    barGapWidthPct: 40, chartColors: [BLUE, BRIGHT], showLegend: true, legendPos: 'b',
    legendFontSize: 6, legendColor: GREY, valAxisMaxVal: 12
  }));
  s.addText('West and South-1 convert 82–84%. North and East convert 46–59% on more primary.', txt({
    x: cx(0) + 0.10, y: R1 + 2.32, w: cw - 0.20, h: 0.44, fontSize: 6.8, color: GREY, lineSpacingMultiple: 0.92 }));

  // 2 — the gap, gross
  y = card(s, { x: cx(1), y: R1, w: cw, h: CH1, label: 'THE MT GAP', accent: RED });
  s.addText('₹13.06 Cr billed and not yet sold through', txt({
    x: cx(1) + 0.10, y, w: cw - 0.20, h: 0.24, fontSize: 7.4, bold: true, color: RED, align: 'center' }));
  /* Waterfall: pptxgenjs has no native form, so it is a stacked bar with an
     invisible riser. Each visible step is its own series to keep per-step colour;
     stacked bars require dataLabelPosition ctr/inEnd/inBase — outEnd corrupts. */
  const STEP = ['Primary', 'Gap', 'Offtake'];
  s.addChart(pres.ChartType.bar, [
    { name: 'riser', labels: STEP, values: [0, 33.96, 0] },
    { name: 'MT primary', labels: STEP, values: [47.02, null, null] },
    { name: 'not converted', labels: STEP, values: [null, 13.06, null] },
    { name: 'MT offtake', labels: STEP, values: [null, null, 33.96] }
  ], Object.assign({}, axisBase, {
    x: cx(1) + 0.04, y: y + 0.26, w: cw - 0.08, h: 1.62,
    barDir: 'col', barGrouping: 'stacked', barGapWidthPct: 45,
    chartColors: [W, BLUE, RED, BRIGHT],
    showValue: true, dataLabelPosition: 'ctr', dataLabelFontSize: 6.4,
    dataLabelColor: W, dataLabelFormatCode: '0.00;;',
    valAxisMaxVal: 50, showLegend: false
  }));
  s.addText('North and East hold ₹7.97 Cr of the gap — 61% of it in two zones. eB2B (₹2.20 Cr) and SIS are MT sub-channels with their own pages; zone benchmark uses geographic accounts only.', txt({
    x: cx(1) + 0.12, y: y + 1.94, w: cw - 0.24, h: 0.52, fontSize: 6.8, color: GREY, lineSpacingMultiple: 0.92 }));

  // 3 — the prize
  y = card(s, { x: cx(2), y: R1, w: cw, h: CH1, label: 'THE PRIZE', accent: GREEN });
  s.addText('₹6.22 Cr', txt({ x: cx(2) + 0.10, y, w: cw - 0.20, h: 0.40, fontSize: 19, bold: true, fontFace: FONTH, color: GREEN, align: 'center' }));
  s.addText('one month, no extra primary', txt({ x: cx(2) + 0.10, y: y + 0.42, w: cw - 0.20, h: 0.18, fontSize: 6.8, color: GREY, align: 'center' }));
  chartTitle(s, cx(2) + 0.10, y + 0.66, cw - 0.20, 'Recoverable by zone (₹ Cr)');
  const recZones = ZONES.filter(z => recover(z) >= 0.25).sort((a, b) => recover(a) - recover(b));
  s.addChart(pres.ChartType.bar, [{
    name: 'Recoverable', labels: recZones.map(z => z.z), values: recZones.map(z => +recover(z).toFixed(2))
  }], Object.assign({}, axisBase, {
    x: cx(2) + 0.02, y: y + 0.88, w: cw - 0.08, h: 1.10, barDir: 'bar',
    chartColors: [GREEN], showValue: true, dataLabelPosition: 'outEnd',
    dataLabelFontSize: 6, dataLabelColor: INK, dataLabelFormatCode: '0.00',
    valAxisMaxVal: 3.4, barGapWidthPct: 45
  }));
  s.addText('West +0.05 and Central +0.13 are below the ₹0.25 Cr floor.', txt({
    x: cx(2) + 0.10, y: y + 2.02, w: cw - 0.20, h: 0.22, fontSize: 6.2, color: GREY, lineSpacingMultiple: 0.92 }));

  // row 2
  const R2 = R1 + CH1 + 0.16;
  y = card(s, { x: cx(0), y: R2, w: cw, h: CH1, label: 'A ONE-ACCOUNT MONTH', accent: RED });
  s.addText('−₹1.42 Cr', txt({ x: cx(0) + 0.10, y, w: cw - 0.20, h: 0.36, fontSize: 17, bold: true, fontFace: FONTH, color: RED, align: 'center' }));
  s.addText('Reliance June → July', txt({ x: cx(0) + 0.10, y: y + 0.38, w: cw - 0.20, h: 0.18, fontSize: 6.8, color: GREY, align: 'center' }));
  bullets(s, {
    x: cx(0) + 0.12, y: y + 0.64, w: cw - 0.24, gap: 0.42, size: 6.9, items: [
      { t: 'Modern Trade fell ₹1.29 Cr month on month.', b: true },
      { t: 'Every other comparable chain, combined, grew ₹0.13 Cr.', c: GREEN },
      { t: 'This is not a broad softening — it is one account.', b: true, c: RED }
    ]
  });

  y = card(s, { x: cx(1), y: R2, w: cw, h: CH1, label: 'NPI IS MIS-TARGETED', accent: AMBER });
  s.addText('82.4%', txt({ x: cx(1) + 0.10, y, w: cw - 0.20, h: 0.36, fontSize: 17, bold: true, fontFace: FONTH, color: AMBER, align: 'center' }));
  s.addText('of NPI value sits in the two worst-converting accounts', txt({
    x: cx(1) + 0.12, y: y + 0.38, w: cw - 0.24, h: 0.30, fontSize: 6.8, color: GREY, align: 'center', lineSpacingMultiple: 0.92 }));
  bullets(s, {
    x: cx(1) + 0.12, y: y + 0.74, w: cw - 0.24, gap: 0.40, size: 6.9, items: [
      { t: 'Reliance alone holds 47.1% of NPI at 51.4% conversion.', c: RED },
      { t: 'East runs the highest NPI mix (10.2%) on the worst flow (49.9%).', c: RED },
      { t: 'Launches will read as product failure when they are flow failure.', b: true }
    ]
  });

  y = card(s, { x: cx(2), y: R2, w: cw, h: CH1, label: 'GEOGRAPHIC ENGINES' });
  bullets(s, {
    x: cx(2) + 0.12, y: y + 0.04, w: cw - 0.24, gap: 0.40, size: 7, items: [
      { t: 'West ₹8.27 Cr at 85.2% — national benchmark.', c: GREEN },
      { t: 'South-1 ₹8.18 Cr at 86.3% — best flow in the country.', c: GREEN },
      { t: 'North ₹4.41 Cr gap — largest recovery pool.', c: RED },
      { t: 'East 49.9% conversion — weakest flow, highest NPI mix.', c: RED },
      { t: 'South-2 now clears the floor at +₹0.90 Cr recoverable.', c: AMBER }
    ]
  });

  // row 3
  const R3 = R2 + CH1 + 0.16;
  y = card(s, { x: cx(0), y: R3, w: cw, h: CH1, label: '90-DAY MOVES' });
  bullets(s, {
    x: cx(0) + 0.12, y: y + 0.04, w: cw - 0.24, gap: 0.42, size: 7, items: [
      { t: '0–30d: map Lulu, Wellness and H&G primary — ₹2.23 Cr blind.', b: true },
      { t: '0–30d: cap East and North primary at trailing 3-month offtake.' },
      { t: '31–60d: Reliance recovery loop across North, East and Central.' },
      { t: '61–90d: reset loading rules by verified conversion, not by target.' },
      { t: 'Scale only what offtake has already proven.' }
    ]
  });

  y = card(s, { x: cx(1), y: R3, w: cw, h: CH1, label: 'LEADERSHIP SCOREBOARD' });
  bullets(s, {
    x: cx(1) + 0.12, y: y + 0.04, w: cw - 0.24, gap: 0.42, size: 7, items: [
      { t: 'MT flow conversion — the one metric. 72.2% → 85.5%.', b: true },
      { t: 'North gap −₹2.78 Cr and East −₹2.54 Cr against benchmark, weekly.' },
      { t: 'Hero-SKU OSA above 95% in priority stores.' },
      { t: 'Unmapped chains: zero before the August pack ships.' },
      { t: 'Channel purity: no eB2B or SIS value inside any MT zone.', c: GREEN }
    ]
  });

  y = card(s, { x: cx(2), y: R3, w: cw, h: CH1, label: 'DECISION SAFEGUARDS', accent: GREY });
  bullets(s, {
    x: cx(2) + 0.12, y: y + 0.04, w: cw - 0.24, gap: 0.42, size: 7, dot: GREY, items: [
      { t: 'Flow gap is not inventory or stock cover — it is unconverted billing.' },
      { t: 'Conversion above 100% is a timing or stock signal, never a success.' },
      { t: 'No % is shown below a ₹0.25 Cr materiality floor.' },
      { t: 'Apollo national 99.7% averages 121–149% zone errors — do not quote it.' },
      { t: 'No YoY or target claim without a matched comparator.' }
    ]
  });
}

/* ------------------------------------------------ S2  Q1 FY27 scorecard */
{
  const s = page(2, 'Q1 FY27: Modern Trade grew 66.6% to ₹107.75 Cr',
    'Quarter in review | Apr–Jun 2026 vs Apr–Jun 2025 | Modern Trade accounts only | ₹ Cr', SRC_Q1);

  const kw = (CW - 0.36) / 4, kx = i => M + i * (kw + 0.12);
  kpi(s, { x: kx(0), y: BODY_Y, w: kw, h: 0.94, label: 'Q1 MT OFFTAKE', value: '₹107.75 Cr', sub: 'vs ₹64.69 Cr in Q1 FY26', accent: BRIGHT });
  kpi(s, { x: kx(1), y: BODY_Y, w: kw, h: 0.94, label: 'Q1 GROWTH', value: '+66.6%', sub: 'blended read was +63.6%', accent: GREEN });
  kpi(s, { x: kx(2), y: BODY_Y, w: kw, h: 0.94, label: 'Q1 MT PRIMARY', value: '₹129.73 Cr', sub: 'Channel == MT, three months', accent: BLUE });
  kpi(s, { x: kx(3), y: BODY_Y, w: kw, h: 0.94, label: 'Q1 CONVERSION', value: '83.1%', sub: 'July fell to 72.2%', accent: GREEN });

  let y = BODY_Y + 1.06;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.66, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText([
    { text: "eB2B IS PART OF MT — Q1 NOTE ON THE BASE   ", options: { color: TEAL, bold: true, fontSize: 7 } },
    { text: "The June pack reported Q1 at ₹114.39 Cr and +63.6% on a total MT base. Nykaa (FSN) (eB2B sub-channel) grew only 25% against the network’s 67%, dragging the blended headline. The geographic zone base grew 66.6%. Both bases are valid; quote the total MT (₹107.75 Cr, 66.6%) for zone-improvement commentary.", options: { fontSize: 7.2, color: INK } }
  ], txt({ x: M + 0.14, y: y + 0.08, w: CW - 0.28, h: 0.52, lineSpacingMultiple: 0.94 }));

  y += 0.82;
  y = banner(s, y, 'ZONE — Q1 FY27 vs Q1 FY26 (MODERN TRADE ONLY)');
  y = table(s, {
    x: M, y, w: CW, rowH: 0.34, size: 7.4, cols: [
      { t: 'ZONE', w: 1.3 }, { t: 'Q1 FY26', w: 1.0, a: 'right' }, { t: 'Q1 FY27', w: 1.0, a: 'right' },
      { t: 'GROWTH', w: 0.95, a: 'right' }, { t: 'MIX', w: 0.75, a: 'right' },
      { t: 'Q1 CONV.', w: 0.95, a: 'right' }, { t: 'JUL CONV.', w: 0.95, a: 'right' }
    ],
    rows: [
      [{ t: 'West', b: true }, '18.77', { t: '29.05', b: true }, { t: '+55%', c: GREEN }, '27.0%', '80.3%', { t: '85.2%', c: GREEN }],
      [{ t: 'North', b: true }, '15.83', { t: '26.41', b: true }, { t: '+67%', c: GREEN }, '24.5%', { t: '90.0%', c: GREEN }, { t: '61.2%', b: true, c: RED }],
      [{ t: 'South-1', b: true }, '13.56', { t: '24.89', b: true }, { t: '+84%', b: true, c: GREEN }, '23.1%', '78.3%', { t: '86.3%', c: GREEN }],
      [{ t: 'South-2', b: true }, '9.52', { t: '15.76', b: true }, { t: '+66%', c: GREEN }, '14.6%', '81.4%', { t: '72.4%', c: AMBER }],
      [{ t: 'East', b: true }, '7.01', { t: '11.73', b: true }, { t: '+67%', c: GREEN }, '10.9%', { t: '89.7%', c: GREEN }, { t: '49.9%', b: true, c: RED }],
      [{ t: 'TOTAL MT', b: true }, { t: '64.69', b: true }, { t: '107.75', b: true }, { t: '+66.6%', b: true, c: GREEN }, '100%', { t: '83.1%', b: true }, { t: '72.2%', b: true, c: RED }]
    ]
  });
  s.addText('Central carried no primary in Apr–Jun and appears from July, so it has no Q1 comparative. eB2B (FSN) grew 25% to ₹6.53 Cr and is reported on page 13.', txt({
    x: M, y: y + 0.06, w: CW, h: 0.24, fontSize: 6.6, color: GREY, lineSpacingMultiple: 0.94 }));

  y += 0.40;
  const hw = (CW - 0.16) / 2;
  const ya = card(s, { x: M, y, w: hw, h: 2.34, label: 'CHAIN — Q1 FY27 (₹ Cr)', accent: TEAL });
  const chains = [['D-Mart', '26.00', '42.32', '+63%'], ['Reliance', '19.08', '28.06', '+47%'],
                  ['Apollo', '7.93', '21.73', '+174%'], ['Lulu', '1.24', '3.33', '+169%'],
                  ['Wellness Forever', '2.49', '2.91', '+17%']];
  chains.forEach((c, i) => {
    const yy = ya + i * 0.33;
    s.addText(c[0], txt({ x: M + 0.12, y: yy, w: hw - 1.70, h: 0.30, fontSize: 7.2, bold: i < 3 }));
    s.addText(c[1], txt({ x: M + hw - 1.62, y: yy, w: 0.50, h: 0.30, fontSize: 7, align: 'right', color: GREY }));
    s.addText(c[2], txt({ x: M + hw - 1.06, y: yy, w: 0.52, h: 0.30, fontSize: 7.2, align: 'right', bold: true }));
    s.addText(c[3], txt({ x: M + hw - 0.50, y: yy, w: 0.40, h: 0.30, fontSize: 7, align: 'right', color: GREEN, bold: true }));
  });
  s.addText('Apollo added ₹13.80 Cr — the largest absolute gain of any account, off a base a third of DMart’s.', txt({
    x: M + 0.12, y: ya + 1.66, w: hw - 0.24, h: 0.30, fontSize: 6.6, color: GREY, lineSpacingMultiple: 0.90 }));

  const bx = M + hw + 0.16;
  const yb = card(s, { x: bx, y, w: hw, h: 2.34, label: 'BRAND — Q1 FY27 (₹ Cr)', accent: BRIGHT });
  const brands = [['Mamaearth', '61.42', '82.54', '+34%'], ['The Derma Co.', '6.34', '29.51', '+365%'],
                  ['Aqualogica', '1.69', '1.96', '+16%'], ['Other brands', '0.44', '0.36', '−18%']];
  brands.forEach((c, i) => {
    const yy = yb + i * 0.33;
    s.addText(c[0], txt({ x: bx + 0.12, y: yy, w: hw - 1.70, h: 0.30, fontSize: 7.2, bold: i < 2 }));
    s.addText(c[1], txt({ x: bx + hw - 1.62, y: yy, w: 0.50, h: 0.30, fontSize: 7, align: 'right', color: GREY }));
    s.addText(c[2], txt({ x: bx + hw - 1.06, y: yy, w: 0.52, h: 0.30, fontSize: 7.2, align: 'right', bold: true }));
    s.addText(c[3], txt({ x: bx + hw - 0.50, y: yy, w: 0.40, h: 0.30, fontSize: 7, align: 'right', color: i === 3 ? RED : GREEN, bold: true }));
  });
  s.addText('The Derma Co. added ₹23.17 Cr — 54% of all Q1 growth — off a base one tenth of Mamaearth’s. Its scale-up is the quarter’s biggest commercial event.', txt({
    x: bx + 0.12, y: yb + 1.42, w: hw - 0.24, h: 0.50, fontSize: 6.8, color: GREY, lineSpacingMultiple: 0.92 }));

  y += 2.50;
  y = banner(s, y, 'Q1 READOUT');
  bullets(s, { x: M + 0.10, y: y + 0.02, w: CW - 0.20, gap: 0.42, size: 7.4, items: [
    { t: 'Every zone grew more than 55% and South-1 led at +84%. Growth is broad-based, not carried by one geography.', b: true },
    { t: 'The Derma Co. at +365% supplied 54% of the quarter’s growth on a tenth of Mamaearth’s base — the portfolio is genuinely widening.' },
    { t: 'Apollo at +174% is the fastest material account, now ₹21.73 Cr and ahead of its Q1 FY26 position by ₹13.80 Cr.' },
    { t: 'Q1 converted at 83.1%; July converted at 72.2% — and the two zones that led Q1 conversion fell hardest. Page 3 explains why.', b: true, c: RED }
  ]});
}

/* --------------------------------------- S3  the quarter-opening load */
{
  const s = page(3, 'July did not break — it is the quarter-opening load, and April did the same',
    'Why July conversion fell | monthly Modern Trade flow, Apr–Jul 2026 | ₹ Cr', SRC_Q1);

  s.addShape(pres.ShapeType.roundRect, { x: M, y: BODY_Y, w: CW, h: 1.06, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText('Conversion collapses in the first month of every quarter, then recovers', txt({
    x: M + 0.16, y: BODY_Y + 0.10, w: CW - 0.32, h: 0.32, fontSize: 11.5, bold: true, fontFace: FONTH, color: TEAL, align: 'center', valign: 'middle' }));
  s.addText('Apr 70.0%   →   May 90.1%   →   Jun 91.4%   →   Jul 72.2%', txt({
    x: M + 0.16, y: BODY_Y + 0.46, w: CW - 0.32, h: 0.24, fontSize: 9, bold: true, align: 'center' }));
  s.addText('April opened Q1 with ₹48.00 Cr of primary against ₹33.60 Cr of offtake. July opened Q2 with ₹47.02 Cr against ₹33.96 Cr. The two months are the same event, one quarter apart. Reading July on its own turns a billing rhythm into a performance crisis.', txt({
    x: M + 0.24, y: BODY_Y + 0.72, w: CW - 0.48, h: 0.28, fontSize: 7.2, color: GREY, align: 'center', lineSpacingMultiple: 0.94 }));

  let y = BODY_Y + 1.22;
  const hw = (CW - 0.16) / 2;
  chartTitle(s, M, y, hw, 'MT primary vs offtake by month (₹ Cr)');
  s.addChart(pres.ChartType.bar, [
    { name: 'Primary', labels: ['Apr', 'May', 'Jun', 'Jul'], values: [48.00, 42.32, 39.41, 47.02] },
    { name: 'Offtake', labels: ['Apr', 'May', 'Jun', 'Jul'], values: [33.60, 38.11, 36.04, 33.96] }
  ], Object.assign({}, axisBase, {
    x: M - 0.02, y: y + 0.22, w: hw, h: 1.66, barGapWidthPct: 45,
    chartColors: [BLUE, BRIGHT], showLegend: true, legendPos: 'b', legendFontSize: 6.2, legendColor: GREY,
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 6, dataLabelColor: INK, dataLabelFormatCode: '0.0',
    valAxisMaxVal: 55
  }));
  chartTitle(s, M + hw + 0.16, y, hw, 'MT flow conversion by month (%)');
  s.addChart(pres.ChartType.line, [{ name: 'Conversion', labels: ['Apr', 'May', 'Jun', 'Jul'], values: [70.0, 90.1, 91.4, 72.2] }],
    Object.assign({}, axisBase, {
      x: M + hw + 0.14, y: y + 0.22, w: hw, h: 1.66, chartColors: [RED], lineSize: 2.5, lineSmooth: false,
      showValue: true, dataLabelPosition: 't', dataLabelFontSize: 6.6, dataLabelColor: INK, dataLabelFormatCode: '0.0',
      valAxisMinVal: 60, valAxisMaxVal: 100
    }));

  y += 2.06;
  y = banner(s, y, 'THE ZONES THAT LOADED HARDEST CONVERTED WORST', RED);
  y = table(s, {
    x: M, y, w: CW, rowH: 0.32, size: 7.4, cols: [
      { t: 'ZONE', w: 1.2 }, { t: 'Q1 MONTHLY AVG PRIMARY', w: 1.8, a: 'right' },
      { t: 'JULY PRIMARY', w: 1.2, a: 'right' }, { t: 'LOAD vs Q1', w: 1.1, a: 'right' },
      { t: 'Q1 CONV.', w: 0.95, a: 'right' }, { t: 'JUL CONV.', w: 0.95, a: 'right' }
    ],
    rows: [
      [{ t: 'East', b: true }, '4.36', '7.10', { t: '+62.8%', b: true, c: RED }, '89.7%', { t: '49.9%', b: true, c: RED }],
      [{ t: 'North', b: true }, '9.78', '11.38', { t: '+16.4%', b: true, c: RED }, '90.0%', { t: '61.2%', b: true, c: RED }],
      [{ t: 'South-2', b: true }, '6.45', '6.73', { t: '+4.3%', c: AMBER }, '81.4%', { t: '72.4%', c: AMBER }],
      [{ t: 'South-1', b: true }, '10.59', '9.48', { t: '−10.5%', c: GREEN }, '78.3%', { t: '86.3%', c: GREEN }],
      [{ t: 'West', b: true }, '12.06', '9.71', { t: '−19.5%', c: GREEN }, '80.3%', { t: '85.2%', c: GREEN }]
    ]
  });
  s.addText('Ranked by July load against each zone’s own Q1 run-rate. The order is monotonic: every zone that billed above its Q1 average lost conversion, every zone that billed below it gained. Assortment, pricing and execution do not move that cleanly.', txt({
    x: M, y: y + 0.06, w: CW, h: 0.30, fontSize: 6.8, color: GREY, lineSpacingMultiple: 0.94 }));

  y += 0.42;
  chartTitle(s, M, y, CW, 'July load against each zone\u2019s own Q1 run-rate (x) versus July conversion (y)');
  /* one point per zone, each its own series so the legend names them */
  const LOAD = [-19.5, -10.5, 4.3, 16.4, 62.8];
  const pt = (i, v) => LOAD.map((_, j) => (j === i ? v : null));
  s.addChart(pres.ChartType.scatter, [
    { name: 'X-Axis', values: LOAD },
    { name: 'West', values: pt(0, 85.2) },
    { name: 'South-1', values: pt(1, 86.3) },
    { name: 'South-2', values: pt(2, 72.4) },
    { name: 'North', values: pt(3, 61.2) },
    { name: 'East', values: pt(4, 49.9) }
  ], Object.assign({}, axisBase, {
    x: M - 0.02, y: y + 0.22, w: CW, h: 1.66,
    chartColors: [GREEN, GREEN, AMBER, RED, RED],
    lineSize: 0, lineDataSymbolSize: 9,
    valAxisMinVal: 40, valAxisMaxVal: 95,
    catAxisMinVal: -30, catAxisMaxVal: 70,
    valAxisTitle: 'July conversion %', showValAxisTitle: true,
    catAxisTitle: 'July primary vs Q1 monthly run-rate, %', showCatAxisTitle: true,
    axisLabelFontSize: 6.2, valAxisTitleFontSize: 6.4, catAxisTitleFontSize: 6.4,
    showLegend: true, legendPos: 'r', legendFontSize: 6.4, legendColor: GREY
  }));
  s.addText('Five points, one per zone. The downward slope is the finding: conversion falls as the zone bills further above its own quarterly rate.', txt({
    x: M, y: y + 1.92, w: CW, h: 0.24, fontSize: 6.6, color: GREY, lineSpacingMultiple: 0.92 }));

  y += 2.26;
  const c3 = (CW - 0.24) / 3, cx3 = i => M + i * (c3 + 0.12);
  const cards = [
    { l: 'WHAT THIS CHANGES', a: RED, big: 'East is not broken', items: [
      { t: 'East converted at 89.7% across Q1 — second best in the country.', b: true },
      { t: 'Its July primary is 62.8% above its own Q1 monthly run-rate.' },
      { t: 'A 49.9% read on a 63% load spike is arithmetic, not an execution failure.' } ] },
    { l: 'WHAT STAYS TRUE', a: AMBER, big: 'The stock is real', items: [
      { t: '₹13.06 Cr is billed and not yet sold through, whatever caused it.', b: true },
      { t: 'It either sells in August or it suppresses the next order.' },
      { t: 'The ₹6.22 Cr benchmark gap stands as an August recovery target.' } ] },
    { l: 'WHAT TO DO DIFFERENTLY', a: GREEN, big: 'Phase the quarter', items: [
      { t: 'Judge conversion on a rolling quarter, never on the opening month.', b: true },
      { t: 'Cap month-1 primary at the trailing quarterly run-rate, by zone.' },
      { t: 'Re-read East and North in the August pack before funding any intervention.' } ] }
  ];
  cards.forEach((t, i) => {
    const y0 = card(s, { x: cx3(i), y, w: c3, h: 1.88, label: t.l, accent: t.a });
    s.addText(t.big, txt({ x: cx3(i) + 0.10, y: y0, w: c3 - 0.20, h: 0.30, fontSize: 11.5, bold: true, fontFace: FONTH, color: t.a, align: 'center', valign: 'middle' }));
    bullets(s, { x: cx3(i) + 0.12, y: y0 + 0.38, w: c3 - 0.24, gap: 0.38, size: 6.9, items: t.items, dot: t.a });
  });

  y += 2.04;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.66, rectRadius: 0.03, fill: { color: 'FBEDEC' }, line: { color: RED, width: 1 } });
  s.addText([
    { text: 'READ THE REST OF THIS PACK WITH THIS IN MIND   ', options: { color: RED, bold: true, fontSize: 7 } },
    { text: 'The zone pages that follow report July on its own, because that is the month under review. Every July conversion figure in them is depressed by the quarter-opening load shown above. Use them to locate where the billed stock sits — not to rank zone capability. Q1 already did that, and it ranked North and East first.', options: { fontSize: 7.2, color: INK } }
  ], txt({ x: M + 0.14, y: y + 0.08, w: CW - 0.28, h: 0.52, lineSpacingMultiple: 0.94 }));
}

/* ---------------------------------------------------------------- S2 */
{
  const s = page(4, 'Convert reporting into a State × Chain × SKU growth engine',
    'Decision framework | measures in force now, and the fields still to be reconciled', SRC_MAIN);

  s.addShape(pres.ShapeType.roundRect, { x: M, y: BODY_Y, w: CW, h: 0.92, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText('The decision is not "push more primary" — it is "find proven demand constrained by execution."', txt({
    x: M + 0.18, y: BODY_Y + 0.12, w: CW - 0.36, h: 0.36, fontSize: 10.5, bold: true, fontFace: FONTH, color: TEAL, align: 'center', valign: 'middle' }));
  s.addText('Six rules below are live on July data. SAH, PDO, OOS and stock fields join only after reconciliation — they are named as gaps, not quoted as findings.', txt({
    x: M + 0.24, y: BODY_Y + 0.52, w: CW - 0.48, h: 0.30, fontSize: 7.2, color: GREY, align: 'center', lineSpacingMultiple: 0.94 }));

  const CH2 = 2.66, cw = (CW - 0.30) / 3, cx = i => M + i * (cw + 0.15);
  const rows = [BODY_Y + 1.06, BODY_Y + 1.06 + CH2 + 0.16, BODY_Y + 1.06 + 2 * (CH2 + 0.16)];

  const panels = [
    { label: 'THE ONE METRIC', accent: TEAL, big: 'Flow conversion', items: [
      { t: 'Offtake ÷ primary on comparable mapped cuts.', b: true },
      { t: 'Every other KPI is supporting, not equal.' },
      { t: 'Target: 73.4% → above 85% this quarter.' },
      { t: 'Read it by zone and chain — never as a national average alone.' } ] },
    { label: 'MATERIALITY FLOOR', accent: AMBER, big: '₹0.25 Cr', items: [
      { t: 'No growth % is shown, ranked or coloured below this base.', b: true },
      { t: 'Below the floor, report the absolute ₹ change only.' },
      { t: 'Removes 8 of 13 rows from the chain scorecard.' },
      { t: 'Stops a ₹1 lakh move outranking a ₹1.42 Cr decline.' } ] },
    { label: 'DISTRIBUTION PRODUCTIVITY', accent: TEAL, big: 'SPD = share ÷ WD', items: [
      { t: 'Share per point of weighted distribution.', b: true },
      { t: 'Face Wash 0.118 · Shampoo 0.045 · TDC FW 0.015.' },
      { t: 'Low SPD on wide WD means fix the shelf, not add doors.' },
      { t: 'Pair with PDO once store-count fields reconcile.' } ] },
    { label: 'GROSS, NEVER NET', accent: RED, big: 'Two gap lines', items: [
      { t: 'Positive gap = billed but unsold. ₹13.27 Cr.', b: true },
      { t: 'Negative gap = sold but unmapped. ₹2.23 Cr.' },
      { t: 'Netting them hid ₹2.06 Cr of recoverable value.' },
      { t: 'Chain and zone gaps must share one stated base.' } ] },
    { label: 'MARKET × FLOW RULE', accent: TEAL, big: 'Scale / Fix / Hold', items: [
      { t: 'Share up + offtake up → scale.', b: true },
      { t: 'Primary up + offtake weak → stop loading.' },
      { t: 'Offtake up + supply weak → replenish.' },
      { t: 'Share down → validate competitor or OOS transfer first.' } ] },
    { label: 'SIZE BEFORE YOU ACT', accent: GREEN, big: 'Expected value', items: [
      { t: 'Rank every action by ₹ at stake × likelihood × cost.', b: true },
      { t: 'Benchmark against a zone that already performs, not a target.' },
      { t: 'State the do-nothing baseline so an action can be killed.' },
      { t: 'Annualise only after a controlled pilot.' } ] },
    { label: 'HERO-SKU AVAILABILITY', accent: TEAL, big: 'Must-stock first', items: [
      { t: 'Measure hero availability %, not SKU count.', b: true },
      { t: 'A missing #1 hero should fail the assortment score outright.' },
      { t: 'Long tail follows proven heroes — never leads them.' },
      { t: 'Protect availability before any discounting.' } ] },
    { label: 'PACK ARCHITECTURE', accent: TEAL, big: '4 pack roles', items: [
      { t: 'Traffic · core-volume · premium upgrade · dead.', b: true },
      { t: 'Not every format gets every pack.' },
      { t: 'Retire dead packs before adding new ones.' },
      { t: 'Judge a pack on sales per store, not listings won.' } ] },
    { label: 'THE FIELDS STILL MISSING', accent: GREY, big: 'Reconcile first', items: [
      { t: 'SAH, weighted distribution by chain, PDO, OOS, closing stock.', b: true },
      { t: 'Without them, cause is inferred and not measured.' },
      { t: 'A factless store × article × month table supplies the denominator.' },
      { t: 'No causal claim until these tie to source.' } ] }
  ];

  panels.forEach((p, i) => {
    const r = Math.floor(i / 3), c = i % 3;
    const y0 = card(s, { x: cx(c), y: rows[r], w: cw, h: CH2, label: p.label, accent: p.accent });
    s.addText(p.big, txt({ x: cx(c) + 0.10, y: y0, w: cw - 0.20, h: 0.34, fontSize: 11.5, bold: true, fontFace: FONTH, color: p.accent, align: 'center', valign: 'middle' }));
    bullets(s, { x: cx(c) + 0.12, y: y0 + 0.42, w: cw - 0.24, gap: 0.40, size: 6.9, items: p.items, dot: p.accent });
  });
}

/* ------------------------------------- S5  share per distribution point */
{
  const s = page(5, 'The shelf is already wide — Mamaearth is under-earning on it',
    'Nielsen MT | share and weighted distribution, MAT Jun 2026 | pack detail May 2026', SRC_NIEL);

  const kw = (CW - 0.36) / 4, kx = i => M + i * (kw + 0.12);
  kpi(s, { x: kx(0), y: BODY_Y, w: kw, h: 0.94, label: 'FACE WASH', value: '10.5%', sub: '#4 share · 89.0% WD · SPD #4 of 6', accent: BRIGHT });
  kpi(s, { x: kx(1), y: BODY_Y, w: kw, h: 0.94, label: 'SHAMPOO', value: '3.7%', sub: '#6 share · 81.5% WD · SPD #6 of 6', accent: RED, valueColor: RED });
  kpi(s, { x: kx(2), y: BODY_Y, w: kw, h: 0.94, label: 'THE DERMA CO. FW', value: '0.4%', sub: '27.3% WD — a genuine width gap', accent: AMBER });
  kpi(s, { x: kx(3), y: BODY_Y, w: kw, h: 0.94, label: 'AVAILABLE AT PEER RATE', value: '+7.9 pts', sub: 'both categories, no new doors', accent: GREEN });

  let y = BODY_Y + 1.06;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.78, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText('Garnier holds the same shelf we do and earns 3.7 share points more from it', txt({
    x: M + 0.16, y: y + 0.10, w: CW - 0.32, h: 0.30, fontSize: 11, bold: true, fontFace: FONTH, color: TEAL, align: 'center', valign: 'middle' }));
  s.addText('Garnier 90.3% weighted distribution → 14.2% share.  Mamaearth 89.0% → 10.5%. Distribution is not the constraint in Face Wash, and it is not the constraint in Shampoo either — we hold 81.5% of the shelf and earn the lowest share per point of the top six brands.', txt({
    x: M + 0.24, y: y + 0.40, w: CW - 0.48, h: 0.34, fontSize: 7, color: GREY, align: 'center', lineSpacingMultiple: 0.94 }));

  y += 0.94;
  y = banner(s, y, 'SHARE PER POINT OF DISTRIBUTION — RANKED (MAT JUN 2026)', TEAL);
  const hw = (CW - 0.16) / 2;
  const cols = [{ t: 'BRAND', w: 1.5 }, { t: 'SHARE', w: 0.66, a: 'right' },
                { t: 'ND', w: 0.60, a: 'right' }, { t: 'WD', w: 0.66, a: 'right' },
                { t: 'SPD', w: 0.68, a: 'right' }];
  const nd = { t: '—', c: GREY };   // numeric distribution: not fed anywhere in the repo
  chartTitle(s, M, y, hw, 'Face Wash');
  const yA = table(s, {
    x: M, y: y + 0.20, w: hw, rowH: 0.26, size: 7, cols,
    rows: [
      ['Himalaya', '22.6%', nd, '99.8%', { t: '0.226', b: true }],
      ['Garnier', '14.2%', nd, '90.3%', { t: '0.157', b: true }],
      ["Pond's", '13.8%', nd, '98.8%', { t: '0.140', b: true }],
      [{ t: 'Mamaearth', b: true }, { t: '10.5%', b: true }, nd, { t: '89.0%', b: true }, { t: '0.118', b: true, c: AMBER }],
      ['Clean & Clear', '7.5%', nd, '98.3%', { t: '0.076', b: true }],
      [{ t: 'The Derma Co.', c: GREY }, { t: '0.4%', c: GREY }, nd, { t: '27.3%', c: GREY }, { t: '0.015', b: true, c: GREY }]
    ]
  });
  chartTitle(s, M + hw + 0.16, y, hw, 'Shampoo');
  table(s, {
    x: M + hw + 0.16, y: y + 0.20, w: hw, rowH: 0.26, size: 7, cols,
    rows: [
      ['Dove', '16.6%', nd, '99.7%', { t: '0.166', b: true }],
      ["L'Oréal Paris", '12.8%', nd, '91.6%', { t: '0.140', b: true }],
      ['Head & Shoulders', '13.0%', nd, '99.6%', { t: '0.131', b: true }],
      ['Sunsilk', '9.6%', nd, '99.4%', { t: '0.097', b: true }],
      ['Clinic Plus', '9.6%', nd, '99.4%', { t: '0.097', b: true }],
      [{ t: 'Mamaearth', b: true }, { t: '3.7%', b: true }, nd, { t: '81.5%', b: true }, { t: '0.045', b: true, c: RED }]
    ]
  });
  s.addText('SPD = value share ÷ weighted distribution: the share each point of shelf presence earns. Numeric distribution (ND) is not supplied in any source we hold, so share = ND × (WD ÷ ND) × SPD can only be read on its last term — we cannot yet tell whether 89.0% WD means most stores or a few very large ones. SPD here is a hand-cut stand-in for the MS vs TDP Index already written in PowerBI/DAX/05_TDP_Measures.dax, which cannot run until the TDP feed exists.', txt({
    x: M, y: yA + 0.06, w: CW, h: 0.40, fontSize: 6.5, color: GREY, lineSpacingMultiple: 0.94 }));

  y = yA + 0.50;
  const oA = card(s, { x: M, y, w: hw, h: 1.58, label: 'FACE WASH — CLOSE TO GARNIER', accent: AMBER });
  s.addText('+3.7 pts  ·  ~₹3.0 Cr / month', txt({ x: M + 0.10, y: oA, w: hw - 0.20, h: 0.30, fontSize: 12.5, bold: true, fontFace: FONTH, color: AMBER, align: 'center', valign: 'middle' }));
  s.addText('Nielsen MT Face Wash ≈ ₹81 Cr / month, so one share point is worth ₹0.81 Cr', txt({
    x: M + 0.10, y: oA + 0.32, w: hw - 0.20, h: 0.16, fontSize: 6.3, color: GREY, align: 'center' }));
  bullets(s, { x: M + 0.12, y: oA + 0.54, w: hw - 0.24, gap: 0.31, size: 6.9, dot: AMBER, items: [
    { t: 'Garnier earns 14.2% on 90.3% WD; we earn 10.5% on 89.0%.', b: true },
    { t: 'Same shelf, 26% less share per point. The gap is velocity, not reach.' }
  ]});
  const oB = card(s, { x: M + hw + 0.16, y, w: hw, h: 1.58, label: 'SHAMPOO — REACH THE WEAKEST PEER', accent: RED });
  s.addText('+4.2 pts  ·  ~₹6.9 Cr / month', txt({ x: M + hw + 0.26, y: oB, w: hw - 0.20, h: 0.30, fontSize: 12.5, bold: true, fontFace: FONTH, color: RED, align: 'center', valign: 'middle' }));
  s.addText('Nielsen MT Shampoo ≈ ₹164 Cr / month, so one share point is worth ₹1.64 Cr', txt({
    x: M + hw + 0.26, y: oB + 0.32, w: hw - 0.20, h: 0.16, fontSize: 6.3, color: GREY, align: 'center' }));
  bullets(s, { x: M + hw + 0.28, y: oB + 0.54, w: hw - 0.24, gap: 0.31, size: 6.9, dot: RED, items: [
    { t: 'At Sunsilk\'s 0.097 — the weakest of the five peers — 81.5% WD yields 7.9%.', b: true },
    { t: 'A conservative benchmark; the peer median is 0.131.' }
  ]});

  y += 1.72;
  y = banner(s, y, 'PACK ARCHITECTURE — WHERE THE VOLUME ACTUALLY SITS (MAY 2026)', TEAL);
  const pcols = [{ t: 'PACK', w: 1.0 }, { t: 'MIX', w: 0.62, a: 'right' },
                 { t: '₹ Cr', w: 0.72, a: 'right' }, { t: 'YoY', w: 0.74, a: 'right' }];
  chartTitle(s, M, y, hw, 'Mamaearth Face Wash');
  const yP = table(s, {
    x: M, y: y + 0.20, w: hw, rowH: 0.26, size: 7, cols: pcols,
    rows: [
      [{ t: '150 ml', b: true }, { t: '58%', b: true }, { t: '5.53', b: true }, { t: '+98%', b: true, c: GREEN }],
      [{ t: '100 ml', b: true }, { t: '21%', b: true }, { t: '1.96', b: true }, { t: '−11%', b: true, c: RED }],
      ['200 ml', '11%', '1.06', { t: 'new', c: GREY }],
      ['50 ml', '11%', '1.01', { t: '+80%', c: GREEN }]
    ]
  });
  chartTitle(s, M + hw + 0.16, y, hw, 'Mamaearth Shampoo');
  table(s, {
    x: M + hw + 0.16, y: y + 0.20, w: hw, rowH: 0.26, size: 7, cols: pcols,
    rows: [
      [{ t: '400 ml', b: true }, { t: '76%', b: true, c: AMBER }, { t: '4.96', b: true }, { t: '+71%', b: true, c: GREEN }],
      [{ t: '250 ml', b: true }, { t: '13%', b: true }, { t: '0.82', b: true }, { t: '−7%', b: true, c: RED }],
      ['650 ml', '7%', '0.43', { t: 'new', c: GREY }],
      ['600 ml', '2%', '0.12', { t: '+151%', c: GREEN }]
    ]
  });

  y = yP + 0.32;
  const pr = card(s, { x: M, y, w: CW, h: 1.26, label: 'PACK READ — ONE HERO, TWO DECLINING PACKS, ONE CONCENTRATION RISK', accent: TEAL });
  bullets(s, { x: M + 0.12, y: pr + 0.02, w: CW - 0.24, gap: 0.30, size: 7.2, items: [
    { t: 'Protect 150 ml: 58% of Mamaearth Face Wash at +98% YoY. A chain-level delisting or stock gap on this one pack is a brand-level event, so it leads the hero-SKU OSA target.', b: true },
    { t: 'Fix 100 ml and Shampoo 250 ml: 21% and 13% of their brands, both declining on value and share. Check availability and promo cover before reading either as demand.', c: RED },
    { t: 'Watch the 400 ml concentration: 76% of Mamaearth Shampoo sits in a single pack. 650 ml is the only credible second pack and it is new.', c: AMBER }
  ]});

  y += 1.38;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.84, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText([
    { text: 'DECISION — RATE BEFORE REACH   ', options: { color: TEAL, bold: true, fontSize: 7 } },
    { text: 'Fix the two declining packs first, then run the shampoo velocity pilot in South-1 — the only zone where shampoo out-sells cleanser. Expand The Derma Co. Face Wash, where 27.3% WD is the one genuine width gap in the portfolio. Hold the large-format entry: 340 ml (₹261 Cr), 1000 ml (₹216 Cr) and 580 ml (₹64 Cr) are ₹541 Cr of pool we do not touch, but Dove covers 250/340/400/1000 ml and Head & Shoulders 180/250/400/580 ml — these pools are contested, not empty. Entering them is a slow share-steal against an entrenched leader, and adding formats while under-earning per point spends listing fees to dilute a thin rate further.', options: { fontSize: 7, color: INK } }
  ], txt({ x: M + 0.14, y: y + 0.06, w: CW - 0.28, h: 0.74, lineSpacingMultiple: 0.94 }));
}

/* ---------------------------------------------------------------- S4 */
{
  const s = page(6, 'Two zones convert at 86% — that rate is worth ₹6.22 Cr applied to the other three',
    'Zone portfolio | contribution, conversion and recoverable value at the internal benchmark', SRC_MAIN);

  let y = banner(s, BODY_Y, 'ZONE SCORECARD — RANKED BY RECOVERABLE VALUE, NOT BY SIZE');
  const sorted = [...ZONES].sort((a, b) => recover(b) - recover(a));
  y = table(s, {
    x: M, y, w: CW, rowH: 0.38, size: 7.4, cols: [
      { t: 'ZONE', w: 1.15 }, { t: 'PRIMARY', w: 0.9, a: 'right' }, { t: 'OFFTAKE', w: 0.9, a: 'right' },
      { t: 'MIX', w: 0.72, a: 'right' }, { t: 'CONV.', w: 0.78, a: 'right' },
      { t: 'GAP', w: 0.78, a: 'right' }, { t: 'AT BENCHMARK', w: 1.15, a: 'right' }, { t: 'CALL', w: 0.86 }
    ],
    rows: sorted.map(z => {
      const rec = recover(z);
      const cc = z.conv >= 82 ? GREEN : z.conv >= 70 ? AMBER : RED;
      return [
        { t: z.z, b: true }, z.pri.toFixed(2), z.off.toFixed(2), z.mix,
        { t: z.conv.toFixed(1) + '%', b: true, c: cc },
        z.gap.toFixed(2),
        { t: rec >= 0.25 ? '+' + rec.toFixed(2) + ' Cr' : 'below floor', b: rec >= 0.25, c: rec >= 0.25 ? GREEN : GREY },
        { t: z.act, b: true, c: z.act === 'FIX' ? RED : GREEN }
      ];
    })
  });
  s.addText('Benchmark = 85.73%, the mean MT conversion of West (85.2%) and South-1 (86.3%). Recoverable = primary × benchmark − actual offtake, holding primary flat; components are rounded to two decimals while the ₹6.22 Cr pool is computed on unrounded values. Zone gaps sum to ₹13.06 Cr. The previous pack headlined ₹13.11 Cr on a blended base that carried the Nykaa (FSN) eB2B account inside MT zone sales; that account is now reported as its own channel.', txt({
    x: M, y: y + 0.08, w: CW, h: 0.40, fontSize: 6.6, color: GREY, lineSpacingMultiple: 0.94 }));

  y += 0.58;
  const cw3 = (CW - 0.30) / 3, cx = i => M + i * (cw3 + 0.15);
  const tiles = [
    { l: 'FIX — THE POOL', a: RED, big: '₹6.22 Cr', sub: 'North, East and South-2 at benchmark', items: [
      { t: 'North ₹2.78 Cr — highest primary, third-worst flow.' },
      { t: 'East ₹2.54 Cr — worst flow, highest NPI mix.' },
      { t: 'South-2 ₹0.90 Cr — newly above the floor once eB2B left its primary.' } ] },
    { l: 'PROTECT — THE ENGINES', a: GREEN, big: '₹16.45 Cr', sub: 'West + South-1 offtake', items: [
      { t: '48.4% of national MT offtake at 85–86% conversion.' },
      { t: 'No recovery pool here — the rate is already the benchmark.' },
      { t: 'Hold spend flat; redirect field capacity to North.' } ] },
    { l: 'ISOLATE — ONE CELL', a: AMBER, big: '₹0.90 Cr', sub: 'South-2, almost all DMart', items: [
      { t: 'DMart South-2 converts 45.1% against 94–95% in West and Central.' },
      { t: 'A DC or fill problem, not a chain relationship problem.' },
      { t: 'Scope as a single-account audit, not a zone programme.' } ] }
  ];
  tiles.forEach((t, i) => {
    const y0 = card(s, { x: cx(i), y, w: cw3, h: 2.10, label: t.l, accent: t.a });
    s.addText(t.big, txt({ x: cx(i) + 0.10, y: y0, w: cw3 - 0.20, h: 0.36, fontSize: 16, bold: true, fontFace: FONTH, color: t.a, align: 'center' }));
    s.addText(t.sub, txt({ x: cx(i) + 0.10, y: y0 + 0.38, w: cw3 - 0.20, h: 0.18, fontSize: 6.8, color: GREY, align: 'center' }));
    bullets(s, { x: cx(i) + 0.12, y: y0 + 0.62, w: cw3 - 0.24, gap: 0.38, size: 6.9, items: t.items, dot: t.a });
  });

  y += 2.26;
  y = banner(s, y, 'PORTFOLIO ACTIONS');
  bullets(s, { x: M + 0.10, y: y + 0.02, w: CW - 0.20, gap: 0.42, size: 7.6, items: [
    { t: 'Fix — North and East: weekly chain × state × hero-EAN gap closure against a ₹2.78 Cr and ₹2.54 Cr target. Owner: zone ZSMs.', b: true, c: INK },
    { t: 'Fix — South-2: now clears the floor at ₹0.90 Cr. Audit DMart DC-to-store fill against the West benchmark. Owner: NKAM DMart + Supply, 22 Aug.' },
    { t: 'Protect — West, South-1: hold hero-SKU OSA, avoid unnecessary loading, document DMart West cadence as the national template.' },
    { t: 'Exception-report — Central and West: ₹0.13 Cr and ₹0.05 Cr recoverable are below the ₹0.25 Cr floor; keep them out of the weekly review.', c: GREY },
    { t: 'Separate — eB2B (₹2.20 Cr) and SIS now report as their own channels on pages 13 and 14, outside every MT zone figure.', c: BLUE }
  ]});

  y += 2.20;
  y = banner(s, y, 'WHY THIS IS A CONVERSION PROBLEM AND NOT A DEMAND PROBLEM', RED);
  const bw = (CW - 0.16) / 2;
  let yq = card(s, { x: M, y, w: bw, h: 1.66, label: 'THE SAME PORTFOLIO, SIX DIFFERENT OUTCOMES', accent: RED });
  bullets(s, { x: M + 0.12, y: yq + 0.04, w: bw - 0.24, gap: 0.38, size: 7.1, dot: RED, items: [
    { t: 'Every zone sells the same brands, packs and price list.', b: true },
    { t: 'Conversion still ranges from 49.9% to 86.3% — a 38-point spread.' },
    { t: 'That rules out product, pricing and proposition, and leaves execution.' }
  ]});
  let yr = card(s, { x: M + bw + 0.16, y, w: bw, h: 1.66, label: 'WHAT WOULD CHANGE THIS READ', accent: GREY });
  bullets(s, { x: M + bw + 0.28, y: yr + 0.04, w: bw - 0.24, gap: 0.38, size: 7.1, dot: GREY, items: [
    { t: 'Closing stock by chain — a gap can also be trade inventory in transit.', b: true },
    { t: 'OOS and OSA by store — the direct test of the execution hypothesis.' },
    { t: 'Until both reconcile, this page sizes an opportunity; it does not prove a cause.' }
  ]});
}

/* ------------------------------------------------------- S5–S11 zones */
[7, 8, 9, 10, 11, 12, 13].forEach(n => {
  const d = ZD[n];
  const isChannel = (n === 13);
  const s = page(n, `${d.zone}: ${d.verdict}`,
    isChannel ? 'Channel view | July 2026 | ₹ Cr | reported outside Modern Trade'
              : 'MT zone deep dive | July 2026 | ₹ Cr | Modern Trade accounts only', SRC_MAIN);

  const kw = (CW - 0.36) / 4;
  const kx = i => M + i * (kw + 0.12);
  kpi(s, { x: kx(0), y: BODY_Y, w: kw, h: 0.94, label: 'PRIMARY', value: d.pri, sub: 'July billing', accent: BLUE });
  kpi(s, { x: kx(1), y: BODY_Y, w: kw, h: 0.94, label: 'OFFTAKE', value: d.off, sub: d.mix, accent: BRIGHT });
  kpi(s, { x: kx(2), y: BODY_Y, w: kw, h: 0.94, label: 'CONVERSION', value: d.conv, sub: 'flow', accent: d.accent });
  kpi(s, { x: kx(3), y: BODY_Y, w: kw, h: 0.94, label: 'GAP', value: d.gap, sub: 'primary − offtake', accent: d.accent });

  let y = BODY_Y + 1.06;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.42, rectRadius: 0.02, fill: { color: TINT }, line: { color: LINE, width: 0.75 } });
  s.addText('PRIORITY', txt({ x: M + 0.12, y: y + 0.06, w: 0.72, h: 0.30, color: TEAL, fontSize: 6.6, bold: true, charSpacing: 0.4, valign: 'middle' }));
  s.addText(d.priority, txt({ x: M + 0.90, y: y + 0.06, w: CW - 1.02, h: 0.30, fontSize: 7.4, bold: true, valign: 'middle' }));

  y += 0.56;
  const halfW = (CW - 0.16) / 2;
  const cd = CH[String(n - 2)] || [];   // charts.json is keyed by the original slide order
  const CHT = 1.64;
  if (n === 11) {
    chartTitle(s, M, y, halfW, 'FSN/Nykaa offtake, Jan–Jul 2026 (₹ Cr)');
    s.addChart(pres.ChartType.line, [{ name: 'Offtake', labels: cd[0].series[0].cats, values: cd[0].series[0].vals }],
      Object.assign({}, axisBase, { x: M - 0.02, y: y + 0.22, w: halfW, h: CHT, chartColors: [BRIGHT], lineSize: 2, lineSmooth: false }));
    chartTitle(s, M + halfW + 0.16, y, halfW, 'Active FSN/Nykaa EANs — range is contracting');
    s.addChart(pres.ChartType.line, [{ name: 'Active EANs', labels: cd[1].series[0].cats, values: cd[1].series[0].vals }],
      Object.assign({}, axisBase, { x: M + halfW + 0.14, y: y + 0.22, w: halfW, h: CHT, chartColors: [AMBER], lineSize: 2, lineSmooth: false }));
  } else {
    chartTitle(s, M, y, halfW, 'Mamaearth — top 3 sub-categories (₹ Cr, Feb–Jul)');
    s.addChart(pres.ChartType.line, cd[0].series.map(se => ({ name: se.name, labels: se.cats, values: se.vals })),
      Object.assign({}, axisBase, {
        x: M - 0.02, y: y + 0.22, w: halfW, h: CHT, chartColors: [BRIGHT, BLUE, RED],
        lineSize: 1.75, lineSmooth: false, showLegend: true, legendPos: 'b', legendFontSize: 5.8, legendColor: GREY
      }));
    chartTitle(s, M + halfW + 0.16, y, halfW, 'The Derma Co. — top 3 sub-categories (₹ Cr, Feb–Jul)');
    s.addChart(pres.ChartType.line, cd[1].series.map(se => ({ name: se.name, labels: se.cats, values: se.vals })),
      Object.assign({}, axisBase, {
        x: M + halfW + 0.14, y: y + 0.22, w: halfW, h: CHT, chartColors: [BRIGHT, BLUE, RED],
        lineSize: 1.75, lineSmooth: false, showLegend: true, legendPos: 'b', legendFontSize: 5.8, legendColor: GREY
      }));
  }

  /* chains / states / brands — each list gets its own labelled card so a state
     can never be mistaken for a chain, which the stacked source list allowed */
  y += CHT + 0.34;
  const LISTH = 1.94;
  const c3 = (CW - 0.24) / 3, cx3 = i => M + i * (c3 + 0.12);
  let a = card(s, { x: cx3(0), y, w: c3, h: LISTH, label: 'TOP CHAINS', accent: TEAL });
  d.chains.forEach((c, i) => {
    s.addText(`${i + 1}. ${c[0]}`, txt({ x: cx3(0) + 0.10, y: a + i * 0.38, w: c3 - 0.85, h: 0.34, fontSize: 7, bold: true, lineSpacingMultiple: 0.9 }));
    s.addText('₹' + c[1] + ' Cr', txt({ x: cx3(0) + c3 - 0.78, y: a + i * 0.38, w: 0.68, h: 0.17, fontSize: 7, align: 'right', color: TEAL, bold: true }));
    const bad = c[2] === 'no primary' || c[2] === 'over 100%';
    s.addText(c[2], txt({ x: cx3(0) + c3 - 0.78, y: a + i * 0.38 + 0.17, w: 0.68, h: 0.16, fontSize: 6.2, align: 'right', color: bad ? AMBER : GREY }));
  });

  let b = card(s, { x: cx3(1), y, w: c3, h: LISTH, label: 'TOP STATES', accent: BLUE });
  d.states.forEach((c, i) => {
    s.addText(`${i + 1}. ${c[0]}`, txt({ x: cx3(1) + 0.10, y: b + i * 0.36, w: c3 - 0.80, h: 0.32, fontSize: 7, bold: true, lineSpacingMultiple: 0.9 }));
    s.addText('₹' + c[1] + ' Cr', txt({ x: cx3(1) + c3 - 0.74, y: b + i * 0.36, w: 0.64, h: 0.20, fontSize: 7, align: 'right', color: BLUE, bold: true }));
  });

  let c = card(s, { x: cx3(2), y, w: c3, h: LISTH, label: 'BRAND × SUB-CATEGORY', accent: BRIGHT });
  s.addText('Mamaearth ' + d.me, txt({ x: cx3(2) + 0.10, y: c, w: c3 - 0.20, h: 0.17, fontSize: 6.8, bold: true, color: BRIGHT }));
  d.meRows.forEach((r, i) => {
    s.addText(r[0], txt({ x: cx3(2) + 0.14, y: c + 0.19 + i * 0.17, w: c3 - 0.72, h: 0.16, fontSize: 6.3 }));
    s.addText(r[1] === 'pending' ? 'pending' : '₹' + r[1], txt({ x: cx3(2) + c3 - 0.64, y: c + 0.19 + i * 0.17, w: 0.54, h: 0.16, fontSize: 6.3, align: 'right', color: GREY }));
  });
  const ty = c + 0.24 + d.meRows.length * 0.17;
  s.addText('The Derma Co. ' + d.tdc, txt({ x: cx3(2) + 0.10, y: ty, w: c3 - 0.20, h: 0.17, fontSize: 6.8, bold: true, color: BLUE }));
  d.tdcRows.forEach((r, i) => {
    s.addText(r[0], txt({ x: cx3(2) + 0.14, y: ty + 0.19 + i * 0.17, w: c3 - 0.72, h: 0.16, fontSize: 6.3 }));
    s.addText(r[1] === 'pending' ? 'pending' : '₹' + r[1], txt({ x: cx3(2) + c3 - 0.64, y: ty + 0.19 + i * 0.17, w: 0.54, h: 0.16, fontSize: 6.3, align: 'right', color: GREY }));
  });

  y += LISTH + 0.12;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.30, rectRadius: 0.02, fill: { color: 'FDF6E6' }, line: { color: AMBER, width: 0.75 } });
  s.addText([
    { text: 'NPI   ', options: { color: AMBER, bold: true, fontSize: 6.6 } },
    { text: d.npi, options: { fontSize: 7, color: INK } }
  ], txt({ x: M + 0.12, y: y + 0.04, w: CW - 0.24, h: 0.24, valign: 'middle' }));

  y += 0.42;
  y = banner(s, y, 'SIX DIAGNOSED EXCEPTIONS — CAUSE, ACTION AND OWNER', d.accent);
  const iw = (CW - 0.24) / 3, ih = 1.86;
  d.ins.forEach((it, i) => {
    const r = Math.floor(i / 3), cc = i % 3;
    insight(s, {
      x: M + cc * (iw + 0.12), y: y + r * (ih + 0.12), w: iw, h: ih,
      tag: it.tag, tagColor: it.c, head: it.head, why: it.why, action: it.action, owner: it.owner
    });
  });

  s.addText(d.foot, txt({ x: M, y: y + 2 * (ih + 0.12) + 0.06, w: CW, h: 0.20, fontSize: 6.8, color: GREY, align: 'center', italic: true }));
});

/* ------------------------------------------------- S12  SIS channel page */
{
  const s = page(14, 'SIS: MT shop-in-shop sub-channel',
    'Channel view | Shop-in-Shop | FY27 to date | ₹ Lakh | MT sub-channel — reported separately from geographic zones', SRC_MAIN);

  const kw = (CW - 0.36) / 4, kx = i => M + i * (kw + 0.12);
  kpi(s, { x: kx(0), y: BODY_Y, w: kw, h: 0.94, label: 'NET SIS PRIMARY', value: '₹26.52 L', sub: 'FY27 to date, net of returns', accent: BLUE });
  kpi(s, { x: kx(1), y: BODY_Y, w: kw, h: 0.94, label: 'GROSS SALES', value: '₹29.64 L', sub: 'before MRN returns', accent: GREY });
  kpi(s, { x: kx(2), y: BODY_Y, w: kw, h: 0.94, label: 'MRN RETURNS', value: '−₹4.55 L', sub: '15.3% of gross', accent: RED, valueColor: RED });
  kpi(s, { x: kx(3), y: BODY_Y, w: kw, h: 0.94, label: 'SHARE OF PRIMARY', value: '0.14%', sub: 'of FY27 all-channel', accent: GREY });

  let y = BODY_Y + 1.06;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.42, rectRadius: 0.02, fill: { color: TINT }, line: { color: LINE, width: 0.75 } });
  s.addText('PRIORITY', txt({ x: M + 0.12, y: y + 0.06, w: 0.72, h: 0.30, color: TEAL, fontSize: 6.6, bold: true, charSpacing: 0.4, valign: 'middle' }));
  s.addText('Small but real — report on its own line, never inside an MT zone figure', txt({ x: M + 0.90, y: y + 0.06, w: CW - 1.02, h: 0.30, fontSize: 7.4, bold: true, valign: 'middle' }));

  y += 0.58;
  const halfW = (CW - 0.16) / 2;
  chartTitle(s, M, y, halfW, 'SIS primary by month (₹ Lakh, FY27)');
  s.addChart(pres.ChartType.bar, [{ name: 'SIS primary', labels: ['April', 'May', 'June', 'July'], values: [6.43, 1.42, 19.30, -0.64] }],
    Object.assign({}, axisBase, {
      x: M - 0.02, y: y + 0.22, w: halfW, h: 1.86, chartColors: [BLUE, BLUE, BLUE, RED], varyColors: true,
      showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 6.4, dataLabelColor: INK, dataLabelFormatCode: '0.0', barGapWidthPct: 55
    }));
  chartTitle(s, M + halfW + 0.16, y, halfW, 'SIS primary by brand (₹ Lakh, FY27)');
  s.addChart(pres.ChartType.bar, [{ name: 'SIS primary', labels: ['BBlunt', 'Aqualogica', 'Mamaearth', 'Lumineve', 'The Derma Co'], values: [-0.40, 3.79, 3.87, 7.69, 11.57] }],
    Object.assign({}, axisBase, {
      x: M + halfW + 0.14, y: y + 0.22, w: halfW, h: 1.86, barDir: 'bar', chartColors: [RED, BRIGHT, BRIGHT, AMBER, BRIGHT], varyColors: true,
      showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 6.4, dataLabelColor: INK, dataLabelFormatCode: '0.0',
      barGapWidthPct: 40, valAxisMinVal: -4, valAxisMaxVal: 14
    }));

  y += 2.24;
  y = banner(s, y, 'SIS ACCOUNTS — FY27 TO DATE', BLUE);
  y = table(s, {
    x: M, y, w: CW, rowH: 0.36, size: 7.4, cols: [
      { t: 'ACCOUNT', w: 2.0 }, { t: 'PRIMARY (₹ L)', w: 1.3, a: 'right' },
      { t: 'OFFTAKE (₹ L)', w: 1.3, a: 'right' }, { t: 'READ', w: 2.4 }
    ],
    rows: [
      [{ t: 'Azorte', b: true }, { t: '23.38', b: true }, { t: '0.00', c: AMBER }, { t: 'Largest SIS account; no offtake feed', c: AMBER }],
      [{ t: 'Shoppers Stop', b: true }, '4.87', '2.00', 'Only account with both sides mapped'],
      [{ t: 'Broadway', b: true }, { t: '−1.73', c: RED }, '0.48', { t: 'Net negative — returns exceed billing', c: RED }],
      [{ t: 'Lifestyle', b: true }, { t: 'not billed', c: GREY }, '1.13', { t: 'Offtake with no SIS primary', c: AMBER }],
      [{ t: "Today's Basket", b: true }, { t: 'nil in FY27', c: GREY }, { t: '—', c: GREY }, { t: 'FY26 account, dormant in FY27', c: GREY }]
    ]
  });

  y += 0.20;
  const c3 = (CW - 0.24) / 3, cx3 = i => M + i * (c3 + 0.12);
  const cards = [
    { l: 'SIS IN MT TOTAL', a: BLUE, big: '₹0.04 Cr', sub: 'SIS offtake within MT — immaterial', items: [
      { t: 'Shoppers Stop, Lifestyle and Broadway offtake sits inside the six geographic zones.', b: true },
      { t: 'SIS is 0.02% of total MT offtake — included in ₹36.10 Cr national MT figure.' },
      { t: 'Reported on this page for transparency; zone conversion benchmark excludes SIS accounts.' } ] },
    { l: 'READ RETURNS FIRST', a: AMBER, big: '15.3%', sub: 'MRN as a share of gross', items: [
      { t: 'Gross ₹29.64 L becomes ₹26.52 L net of ₹4.55 L returns.', b: true },
      { t: 'July is net negative (−₹0.64 L): returns exceeded billing that month.' },
      { t: 'Always quote SIS net; the gross figure overstates by 11.8%.' } ] },
    { l: 'DATA QUALITY', a: GREY, big: '662 rows', sub: 'full source, not row-capped', items: [
      { t: '206 exact-duplicate invoice lines detected, not deduplicated.', b: true },
      { t: 'Impact ₹2.48 L — checked and judged negligible, but unresolved.' },
      { t: 'Azorte has primary and no offtake; Lifestyle the reverse.' } ] }
  ];
  cards.forEach((t, i) => {
    const y0 = card(s, { x: cx3(i), y, w: c3, h: 2.30, label: t.l, accent: t.a });
    s.addText(t.big, txt({ x: cx3(i) + 0.10, y: y0, w: c3 - 0.20, h: 0.36, fontSize: 15, bold: true, fontFace: FONTH, color: t.a, align: 'center' }));
    s.addText(t.sub, txt({ x: cx3(i) + 0.10, y: y0 + 0.38, w: c3 - 0.20, h: 0.18, fontSize: 6.6, color: GREY, align: 'center' }));
    bullets(s, { x: cx3(i) + 0.12, y: y0 + 0.62, w: c3 - 0.24, gap: 0.42, size: 6.9, items: t.items, dot: t.a });
  });

  y += 2.46;
  y = banner(s, y, 'MT CHANNEL STRUCTURE');
  bullets(s, { x: M + 0.10, y: y + 0.02, w: CW - 0.20, gap: 0.32, size: 7.0, items: [
    { t: 'Modern Trade (total) → geographic zones + eB2B sub-channel + SIS sub-channel = ₹49.21 Cr primary, ₹36.10 Cr offtake.', b: true },
    { t: 'Geographic zones (6) → MT store accounts. Used for zone conversion benchmark and gap analysis. Primary ₹47.02 Cr, offtake ₹33.96 Cr.', c: TEAL },
    { t: 'eB2B sub-channel → Nykaa (FSN) and Eremedium. FY27 primary ₹8.79 Cr, offtake ₹8.60 Cr. Formerly mis-labelled "Pan India" zone.', c: BLUE },
    { t: 'SIS sub-channel → Azorte, Shoppers Stop, Broadway, Lifestyle. FY27 net primary ₹0.27 Cr. Included in total MT.', c: BLUE },
    { t: 'Classification held in scripts/data/channel_master.json. No channel is merged or rolled into another without a business decision.', c: GREY }
  ]});

}

/* ---------------------------------------------------------------- S12 */
{
  const s = page(15, 'July is a Reliance problem — every other chain combined grew',
    'Chain growth and risk | June–July 2026 | ranked by ₹ change above a ₹0.25 Cr materiality floor', SRC_MAIN);

  s.addShape(pres.ShapeType.roundRect, { x: M, y: BODY_Y, w: CW, h: 1.16, rectRadius: 0.03, fill: { color: 'FBEDEC' }, line: { color: RED, width: 1 } });
  s.addText('Modern Trade fell ₹1.29 Cr month on month. Reliance accounts for ₹1.42 Cr of it.', txt({
    x: M + 0.18, y: BODY_Y + 0.12, w: CW - 0.36, h: 0.34, fontSize: 11, bold: true, fontFace: FONTH, color: RED, align: 'center', valign: 'middle' }));
  s.addText('Every other comparable chain, added together, grew ₹0.13 Cr.', txt({
    x: M + 0.18, y: BODY_Y + 0.50, w: CW - 0.36, h: 0.24, fontSize: 8.5, bold: true, align: 'center' }));
  s.addText('The source pack ranked this table by MoM %, which put Sasta Sundar (+127.8% on a ₹1 lakh base) at the top and a ₹1.42 Cr decline in mid-table. Ranked by rupee change, the month has one story.', txt({
    x: M + 0.26, y: BODY_Y + 0.76, w: CW - 0.52, h: 0.32, fontSize: 7, color: GREY, align: 'center', lineSpacingMultiple: 0.94 }));

  let y = BODY_Y + 1.32;
  y = banner(s, y, 'MATERIAL CHAINS — ₹0.25 Cr FLOOR, RANKED BY RUPEE CHANGE', RED);
  y = table(s, {
    x: M, y, w: CW, rowH: 0.40, size: 7.6, cols: [
      { t: 'CHAIN', w: 1.7 }, { t: 'JUN', w: 1.0, a: 'right' }, { t: 'JUL', w: 1.0, a: 'right' },
      { t: '₹ CHANGE', w: 1.1, a: 'right' }, { t: 'MoM %', w: 0.9, a: 'right' }, { t: 'CALL', w: 1.22 }
    ],
    rows: [
      [{ t: 'Reliance', b: true }, '₹9.48 Cr', '₹8.06 Cr', { t: '−1.42', b: true, c: RED }, { t: '−15.0%', c: RED }, { t: 'RECOVER — lead case', b: true, c: RED }],
      [{ t: 'Lulu', b: true }, '₹1.16 Cr', '₹1.70 Cr', { t: '+0.54', b: true, c: AMBER }, { t: '+46.5%', c: AMBER }, { t: 'VERIFY — no mapped primary', b: true, c: AMBER }],
      [{ t: 'DMart', b: true }, '₹14.56 Cr', '₹14.33 Cr', { t: '−0.23', c: GREY }, { t: '−1.5%', c: GREY }, { t: 'STABLE — largest account', c: GREEN }]
    ]
  });

  y += 0.14;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.44, rectRadius: 0.02, fill: { color: 'F4F9F8' }, line: { color: LINE, width: 0.75 } });
  s.addText([
    { text: 'BELOW THE FLOOR   ', options: { color: GREY, bold: true, fontSize: 6.6 } },
    { text: 'Ten chains moved less than ₹0.25 Cr and are excluded from ranking: Wellness Forever −0.08, Metro −0.12, Vishal Mega Mart +0.05, More Retail −0.03, Health & Glow −0.01, V-Mart −0.01, Spencer +0.01, Arambagh −0.01, Ratandeep 0.00, Sasta Sundar +0.01, Sumo Save +0.01. Combined they moved −₹0.19 Cr.', options: { fontSize: 6.8, color: INK } }
  ], txt({ x: M + 0.12, y: y + 0.05, w: CW - 0.24, h: 0.36, lineSpacingMultiple: 0.94 }));

  y += 0.60;
  const c3 = (CW - 0.24) / 3, cx3 = i => M + i * (c3 + 0.12);
  const cards = [
    { l: 'THE DECLINE', a: RED, big: '−₹1.42 Cr', sub: 'Reliance, June → July', items: [
      { t: 'Mamaearth Shampoo and Sun Care carry most of the fall.' },
      { t: 'Reliance converts 51.4% nationally — 44.9% in North, 52.9% in East.' },
      { t: 'The account is the pattern; the zones are where it shows.' } ] },
    { l: 'THE UNVERIFIED GROWTH', a: AMBER, big: '+₹0.54 Cr', sub: 'Lulu, on ₹0 mapped primary', items: [
      { t: 'Ranked "Scale" in the source pack on a +46.5% MoM read.' },
      { t: 'No primary is joined to this account, so flow cannot be tested.' },
      { t: 'Hold the recommendation until the billing route is mapped.' } ] },
    { l: 'THE REST OF THE BOOK', a: GREEN, big: '+₹0.13 Cr', sub: 'all chains except Reliance', items: [
      { t: 'DMart −₹0.23 Cr on a ₹14.33 Cr base is normal variation.' },
      { t: 'No second account shows a material decline.' },
      { t: 'Do not launch a broad recovery programme for a single-account month.' } ] }
  ];
  cards.forEach((t, i) => {
    const y0 = card(s, { x: cx3(i), y, w: c3, h: 2.46, label: t.l, accent: t.a });
    s.addText(t.big, txt({ x: cx3(i) + 0.10, y: y0, w: c3 - 0.20, h: 0.38, fontSize: 16, bold: true, fontFace: FONTH, color: t.a, align: 'center' }));
    s.addText(t.sub, txt({ x: cx3(i) + 0.10, y: y0 + 0.40, w: c3 - 0.20, h: 0.18, fontSize: 6.8, color: GREY, align: 'center' }));
    bullets(s, { x: cx3(i) + 0.12, y: y0 + 0.66, w: c3 - 0.24, gap: 0.44, size: 7, items: t.items, dot: t.a });
  });

  y += 2.62;
  y = banner(s, y, 'LEADERSHIP READOUT');
  bullets(s, { x: M + 0.10, y: y + 0.02, w: CW - 0.20, gap: 0.44, size: 7.4, items: [
    { t: 'One account explains the month. Run a Reliance recovery loop, not a Modern Trade recovery programme.', b: true },
    { t: 'The comparable set covers ₹26.90 Cr of ₹33.96 Cr national MT offtake — 79.2%. Chains with missing July feeds are data gaps, not de-growth, and stay outside the ranking.' },
    { t: 'Three chains — Lulu, Wellness Forever, Health & Glow — show offtake against unmapped primary. Their growth reads cannot be verified and must not drive field action.', c: AMBER },
    { t: 'Reinstate percentage ranking only above the ₹0.25 Cr floor; below it, report absolute change.', c: GREY }
  ]});

  y += 2.00;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.66, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText([
    { text: 'BEFORE ACTING ON THIS   ', options: { color: TEAL, bold: true, fontSize: 7 } },
    { text: 'One month is not a trend. Reliance −15.0% is measured against June alone, and a single extreme month partly reverts on its own. Re-run this comparison against a rolling three-month base before committing trade spend, so the recovery programme is sized against the underlying rate rather than against one month of noise.', options: { fontSize: 7.2, color: INK } }
  ], txt({ x: M + 0.14, y: y + 0.09, w: CW - 0.28, h: 0.50, lineSpacingMultiple: 0.94 }));
}

/* ---------------------------------------------------------------- S13 */
{
  const s = page(16, 'Fix the specific commercial loophole — not the whole account',
    'Chain recovery plan | evidence, action, success KPI and value at stake', SRC_MAIN);

  let y = banner(s, BODY_Y, 'CHAIN-WISE RECOVERY LOOP — ORDERED BY VALUE AT STAKE');

  const loops = [
    { n: 'RELIANCE', a: RED, stake: '₹3.92 Cr', head: 'Flow failure, not demand failure',
      ev: 'Converts 51.4% nationally — 44.9% North, 52.9% East, 51.2% Central. Same weakness in every zone it operates.',
      rec: 'Halt incremental loading until conversion clears 65%; run hero-EAN OSA audit against the Apollo cadence.',
      kpi: 'Conversion 51.4% → 76.5% (DMart parity)', own: 'NKAM Reliance + Supply · 25 Aug' },
    { n: 'DMART SOUTH-2', a: RED, stake: '₹0.90 Cr', head: 'One region behaving unlike the account',
      ev: 'DMart converts 94.2% in West and 95.3% in Central, but 45.1% in South-2 — a regional break, not a chain issue.',
      rec: 'Audit DC-to-store fill rate and top-SKU store availability against the West benchmark.',
      kpi: 'South-2 conversion to 80%+', own: 'NKAM DMart + Supply · 22 Aug' },
    { n: 'LULU', a: AMBER, stake: 'unverified', head: 'Growth claim without a primary join',
      ev: '+46.5% MoM on ₹1.70 Cr offtake with zero mapped primary. The growth may be real or a mapping artefact.',
      rec: 'Map the Lulu billing route before any field instruction is issued on this account.',
      kpi: 'Primary mapped and flow computable', own: 'Analyst · 18 Aug' },
    { n: 'METRO', a: AMBER, stake: '₹0.12 Cr', head: 'Range dilution below the floor',
      ev: 'Down 20.5% MoM but only ₹0.12 Cr in absolute terms — more SKUs on lower sales per SKU.',
      rec: 'Pause range expansion and remove non-productive EANs; no separate recovery programme.',
      kpi: 'Sales per SKU and per store', own: 'NKAM Metro · Sep cycle' },
    { n: 'APOLLO', a: GREEN, stake: 'benchmark', head: 'The cadence worth exporting',
      ev: 'Near-parity flow nationally. Zone figures read 121–149%, so the model is sound but the stock reconciliation is not.',
      rec: 'Extract order frequency and assortment depth as a scoring template; reconcile opening stock.',
      kpi: 'Template published and applied to 2 accounts', own: 'Analyst + NKAM Apollo · 31 Aug' },
    { n: 'WELLNESS / H&G', a: AMBER, stake: '₹0.53 Cr', head: 'Offtake above unmapped primary',
      ev: 'Both show more offtake than mapped primary — ₹0.24 Cr and ₹0.29 Cr of negative gap that nets against real shortfalls.',
      rec: 'Map both billing routes; report gross positive and gross negative gap separately.',
      kpi: 'Zero unmapped material chains', own: 'Analyst · 18 Aug' },
    { n: 'FSN / NYKAA', a: GREEN, stake: '₹2.07 Cr', head: 'Protect, and stop netting it',
      ev: '99.4% flow, but July down 4.6% on June and active EANs down from 222 to 198 since January.',
      rec: 'Test whether the 24 delisted EANs explain the softness; report outside geographic gap arithmetic.',
      kpi: 'Flow above 95%, return to ₹2.17 Cr', own: 'NKAM FSN + Analyst · 31 Aug' },
    { n: 'VISHAL MEGA MART', a: AMBER, stake: '₹0.05 Cr', head: 'Expansion outrunning execution',
      ev: 'Sites up 10.2% and offtake up 18.2%, but the account carries no mapped primary in the East cut.',
      rec: 'Protect fill rate before adding doors; map primary.',
      kpi: 'OSA and sales per new door', own: 'RKAM East · Sep cycle' },
    { n: 'THE REST', a: GREY, stake: 'below floor', head: 'Nine chains, ₹0.19 Cr combined',
      ev: 'Every remaining chain moved less than ₹0.25 Cr. Percentage swings here are arithmetic, not commercial signal.',
      rec: 'Report by exception only; no named recovery action.',
      kpi: 'Excluded from weekly review', own: 'Analyst · standing' }
  ];

  const cw = (CW - 0.24) / 3, chh = 2.92;
  loops.forEach((L, i) => {
    const r = Math.floor(i / 3), c = i % 3;
    const x = M + c * (cw + 0.12), yy = y + r * (chh + 0.14);
    const y0 = card(s, { x, y: yy, w: cw, h: chh, label: L.n, accent: L.a });
    s.addText(L.head, txt({ x: x + 0.10, y: y0, w: cw - 0.20, h: 0.32, fontSize: 8, bold: true, align: 'center', lineSpacingMultiple: 0.9 }));
    s.addText([
      { text: 'AT STAKE  ', options: { color: GREY, bold: true, fontSize: 6 } },
      { text: L.stake, options: { color: L.a, bold: true, fontSize: 8 } }
    ], txt({ x: x + 0.10, y: y0 + 0.34, w: cw - 0.20, h: 0.20, align: 'center' }));
    s.addText('EVIDENCE', txt({ x: x + 0.10, y: y0 + 0.60, w: cw - 0.20, h: 0.14, color: TEAL, fontSize: 6, bold: true, charSpacing: 0.4 }));
    s.addText(L.ev, txt({ x: x + 0.10, y: y0 + 0.75, w: cw - 0.20, h: 0.46, fontSize: 6.8, color: GREY, lineSpacingMultiple: 0.92 }));
    s.addText('RECOVERY', txt({ x: x + 0.10, y: y0 + 1.24, w: cw - 0.20, h: 0.14, color: TEAL, fontSize: 6, bold: true, charSpacing: 0.4 }));
    s.addText(L.rec, txt({ x: x + 0.10, y: y0 + 1.39, w: cw - 0.20, h: 0.46, fontSize: 6.8, lineSpacingMultiple: 0.92 }));
    s.addText([
      { text: 'KPI  ', options: { color: TEAL, bold: true, fontSize: 6 } },
      { text: L.kpi, options: { fontSize: 6.6, bold: true } }
    ], txt({ x: x + 0.10, y: yy + chh - 0.50, w: cw - 0.20, h: 0.26, lineSpacingMultiple: 0.9 }));
    s.addText(L.own, txt({ x: x + 0.10, y: yy + chh - 0.22, w: cw - 0.20, h: 0.15, fontSize: 6.2, color: GREY, italic: true }));
  });

  const yEnd = y + 3 * (chh + 0.14);
  s.addShape(pres.ShapeType.roundRect, { x: M, y: yEnd, w: CW, h: 0.44, rectRadius: 0.02, fill: { color: TINT }, line: { color: LINE, width: 0.75 } });
  s.addText([
    { text: 'SEQUENCING   ', options: { color: TEAL, bold: true, fontSize: 6.8 } },
    { text: 'Reliance and DMart South-2 carry ₹4.73 Cr of the ₹6.22 Cr recovery pool between them — 81%. Both are single-account audits that can start this week. The three mapping fixes cost analyst time only and unblock everything else, so they run first.', options: { fontSize: 7, color: INK } }
  ], txt({ x: M + 0.12, y: yEnd + 0.06, w: CW - 0.24, h: 0.34, lineSpacingMultiple: 0.94 }));
}

/* ---------------------------------------------------------------- S14 */
{
  const s = page(17, 'eB2B account detail: Nykaa (FSN) holds 99.4% flow on a contracting range',
    'eB2B sub-channel | account deep dive | January–July 2026 | MT sub-channel — see page 13', SRC_MAIN);

  const kw = (CW - 0.24) / 3;
  kpi(s, { x: M, y: BODY_Y, w: kw, h: 0.94, label: 'JUL PRIMARY', value: '₹2.08 Cr', sub: 'FSN + Nykaa SS, eB2B', accent: BLUE });
  kpi(s, { x: M + kw + 0.12, y: BODY_Y, w: kw, h: 0.94, label: 'JUL OFFTAKE', value: '₹2.07 Cr', sub: 'reported outside MT', accent: BRIGHT });
  kpi(s, { x: M + 2 * (kw + 0.12), y: BODY_Y, w: kw, h: 0.94, label: 'FLOW', value: '99.4%', sub: '+27.0 pp vs MT (72.4%)', accent: GREEN });

  let y = BODY_Y + 1.08;
  const halfW = (CW - 0.16) / 2;
  chartTitle(s, M, y, halfW, 'Offtake, Jan–Jul 2026 (₹ Cr)');
  s.addChart(pres.ChartType.line, [{ name: 'Offtake', labels: CH['14'][0].series[0].cats, values: CH['14'][0].series[0].vals }],
    Object.assign({}, axisBase, {
      x: M - 0.02, y: y + 0.22, w: halfW, h: 1.90, chartColors: [BRIGHT], lineSize: 2.25, lineSmooth: false,
      showValue: true, dataLabelFontSize: 6, dataLabelColor: GREY, dataLabelPosition: 't', dataLabelFormatCode: '0.00'
    }));
  chartTitle(s, M + halfW + 0.16, y, halfW, 'Active EANs — 222 in January, 198 in July');
  s.addChart(pres.ChartType.line, [{ name: 'Active EANs', labels: CH['11'][1].series[0].cats, values: CH['11'][1].series[0].vals }],
    Object.assign({}, axisBase, {
      x: M + halfW + 0.14, y: y + 0.22, w: halfW, h: 1.90, chartColors: [AMBER], lineSize: 2.25, lineSmooth: false,
      showValue: true, dataLabelFontSize: 6, dataLabelColor: GREY, dataLabelPosition: 't'
    }));

  y += 2.26;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.60, rectRadius: 0.03, fill: { color: 'FDF6E6' }, line: { color: AMBER, width: 1 } });
  s.addText('Offtake peaked at ₹2.29 Cr in April and has drifted to ₹2.07 Cr. Across the same period the active range fell from 222 EANs to 198 — a 10.8% contraction. Test delisting before calling this a demand decline.', txt({
    x: M + 0.16, y: y + 0.08, w: CW - 0.32, h: 0.46, fontSize: 7.6, bold: true, color: INK, align: 'center', valign: 'middle', lineSpacingMultiple: 0.94 }));

  y += 0.74;
  y = banner(s, y, 'ARTICLE ENGINES — TOP EIGHT BY JULY OFFTAKE');
  y = table(s, {
    x: M, y, w: CW, rowH: 0.34, size: 7.2, cols: [
      { t: '#', w: 0.3, a: 'right' }, { t: 'ARTICLE', w: 4.7 }, { t: 'JULY OFFTAKE', w: 1.2, a: 'right' }, { t: 'ROLE', w: 1.5 }
    ],
    rows: [
      ['1', { t: 'Rice Face Wash 100 ml', b: true }, { t: '₹0.27 Cr', b: true }, { t: 'Hero — protect OSA', c: GREEN }],
      ['2', { t: 'Rice Face Wash 50 ml', b: true }, { t: '₹0.19 Cr', b: true }, { t: 'Hero — protect OSA', c: GREEN }],
      ['3', 'Ubtan Natural Glow Face Wash with Turmeric', '₹0.14 Cr', 'Core volume'],
      ['4', 'Vitamin C Face Wash with Vitamin C', '₹0.09 Cr', 'Core volume'],
      ['5', 'Vitamin C Daily Glow Face Wash', '₹0.08 Cr', 'Core volume'],
      ['6', 'Ubtan Natural Glow Face Wash 50 ml', '₹0.08 Cr', 'Traffic pack'],
      ['7', 'Vitamin C Daily Glow Sunscreen 50 g', '₹0.08 Cr', 'Seasonal'],
      ['8', 'Onion Hair Fall Control Shampoo', '₹0.07 Cr', 'Cross-category entry']
    ]
  });

  y += 0.20;
  const bw = (CW - 0.16) / 2;
  let ya = card(s, { x: M, y, w: bw, h: 1.46, label: 'LEADERSHIP CALL', accent: GREEN });
  bullets(s, { x: M + 0.12, y: ya + 0.02, w: bw - 0.24, gap: 0.34, size: 7.2, dot: GREEN, items: [
    { t: 'Protect the two Rice Face Wash SKUs — 22% of account offtake.', b: true },
    { t: 'Reverse the 4.6% June–July softness back to ₹2.17 Cr.' },
    { t: 'Hold flow above 95% as the account benchmark.' }
  ]});
  let yb = card(s, { x: M + bw + 0.16, y, w: bw, h: 1.46, label: 'READ THIS ACCOUNT CAREFULLY', accent: AMBER });
  bullets(s, { x: M + bw + 0.28, y: yb + 0.02, w: bw - 0.24, gap: 0.34, size: 7.2, dot: AMBER, items: [
    { t: 'FSN and Nykaa SS are combined at article level — neither can be attributed.', b: true },
    { t: 'Marketplace replenishment is near real-time; 99.4% is not transferable to hypermarkets.' },
    { t: 'This ₹2.07 Cr is eB2B and sits outside MT zone sales entirely.' }
  ]});
}

/* ---------------------------------------------------------------- S15 */
{
  const s = page(18, 'NPI is ₹2.82 Cr — and 82% of it sits in the two accounts that convert worst',
    'New product introduction | contribution by zone and chain | July 2026', SRC_MAIN);

  const kw = (CW - 0.24) / 3;
  kpi(s, { x: M, y: BODY_Y, w: kw, h: 0.94, label: 'NPI OFFTAKE', value: '₹2.82 Cr', sub: '7.82% of July offtake', accent: BRIGHT });
  kpi(s, { x: M + kw + 0.12, y: BODY_Y, w: kw, h: 0.94, label: 'IN TWO ACCOUNTS', value: '82.4%', sub: 'Reliance 47.1% + DMart 35.3%', accent: RED, valueColor: RED });
  kpi(s, { x: M + 2 * (kw + 0.12), y: BODY_Y, w: kw, h: 0.94, label: 'SELLING EANs', value: '58 / 60', sub: '2 finalised with zero sale', accent: AMBER });

  s.addShape(pres.ShapeType.roundRect, { x: M, y: BODY_Y + 1.06, w: CW, h: 0.78, rectRadius: 0.03, fill: { color: 'FBEDEC' }, line: { color: RED, width: 1 } });
  s.addText('New products are being launched through the weakest pipes in the network.', txt({
    x: M + 0.16, y: BODY_Y + 1.14, w: CW - 0.32, h: 0.28, fontSize: 10, bold: true, fontFace: FONTH, color: RED, align: 'center', valign: 'middle' }));
  s.addText('Reliance holds 47.1% of all NPI value and converts at 51.4%. East runs the highest NPI mix in the country (10.2%) on the worst flow (49.9%). A launch that fails here will be read as a product failure when it is a flow failure.', txt({
    x: M + 0.24, y: BODY_Y + 1.44, w: CW - 0.48, h: 0.32, fontSize: 7.2, align: 'center', color: INK, lineSpacingMultiple: 0.94 }));

  let y = BODY_Y + 2.00;
  const halfW = (CW - 0.16) / 2;
  chartTitle(s, M, y, halfW, 'NPI mix by zone (%), coloured by zone flow conversion');
  // reversed so the highest NPI mix reads at the top of the horizontal bars
  s.addChart(pres.ChartType.bar, [{
    name: 'NPI mix %', labels: ['South-2', 'West', 'South-1', 'Central', 'North', 'East'],
    values: [6.37, 6.58, 7.88, 8.54, 9.24, 10.23]
  }], Object.assign({}, axisBase, {
    x: M - 0.02, y: y + 0.22, w: halfW, h: 2.16, barDir: 'bar',
    chartColors: [AMBER, GREEN, GREEN, GREEN, RED, RED], varyColors: true,
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 6.2, dataLabelColor: INK,
    dataLabelFormatCode: '0.0', valAxisMaxVal: 12, barGapWidthPct: 40
  }));
  s.addText('Bar colour is zone flow conversion: green above 78%, amber 70–78%, red below 60%. The two red zones carry the highest NPI exposure.', txt({
    x: M, y: y + 2.42, w: halfW, h: 0.26, fontSize: 6.4, color: GREY, lineSpacingMultiple: 0.92 }));

  chartTitle(s, M + halfW + 0.16, y, halfW, 'NPI offtake by chain (₹ Cr)');
  // source series was in ₹ lakh while the rest of the pack is in ₹ Cr; horizontal
  // bars plot bottom-up, so the list is reversed to read largest-first
  const npiChains = ['Sancus', 'Wellness', 'Metro', 'Health & Glow', 'FSN / Nykaa', 'Lulu', 'DMart', 'Reliance'];
  const npiVals = CH['15'][1].series[0].vals.map(v => +(v / 100).toFixed(2)).reverse();
  s.addChart(pres.ChartType.bar, [{ name: 'NPI offtake', labels: npiChains, values: npiVals }],
    Object.assign({}, axisBase, {
      x: M + halfW + 0.10, y: y + 0.22, w: halfW + 0.04, h: 2.16, barDir: 'bar',
      chartColors: [GREY, GREY, GREY, GREY, GREY, GREY, AMBER, RED], varyColors: true,
      showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 6.2, dataLabelColor: INK,
      dataLabelFormatCode: '0.00', valAxisMaxVal: 1.6, barGapWidthPct: 40
    }));
  s.addText('Reliance ₹1.30 Cr and DMart ₹0.98 Cr together are 82.4% of all NPI value. Converted from a source series reported in ₹ lakh.', txt({
    x: M + halfW + 0.16, y: y + 2.42, w: halfW, h: 0.26, fontSize: 6.4, color: GREY, lineSpacingMultiple: 0.92 }));

  y += 2.76;
  y = banner(s, y, 'TOP NPI ARTICLES — FULL NAMES, JULY OFFTAKE');
  y = table(s, {
    x: M, y, w: CW, rowH: 0.30, size: 7, cols: [
      { t: '#', w: 0.28, a: 'right' }, { t: 'ARTICLE', w: 3.1 }, { t: '₹ Cr', w: 0.66, a: 'right' },
      { t: '#', w: 0.28, a: 'right' }, { t: 'ARTICLE', w: 3.1 }, { t: '₹ Cr', w: 0.66, a: 'right' }
    ],
    rows: [
      ['1', { t: 'ME Onion Hair Fall Control Shampoo', b: true }, { t: '0.31', b: true }, '2', { t: 'ME Onion Hair Oil 200 ml', b: true }, { t: '0.30', b: true }],
      ['3', 'ME Gentle Cleansing Shampoo 400 ml', '0.21', '4', 'ME Multani Mitti Face Wash 100 ml', '0.20'],
      ['5', 'ME Vitamin C Daily Glow Sunscreen', '0.20', '6', 'ME Lemon Anti-Dandruff Shampoo', '0.19'],
      ['7', 'ME Rosemary Anti-Hair Fall Shampoo', '0.18', '8', 'ME Rice Water Dewy Sunscreen 80 g', '0.18']
    ]
  });

  y += 0.20;
  const bw = (CW - 0.16) / 2;
  let ya = card(s, { x: M, y, w: bw, h: 1.62, label: 'ZERO-SALE FINALISED EANs', accent: RED });
  bullets(s, { x: M + 0.12, y: ya + 0.04, w: bw - 0.24, gap: 0.36, size: 7.2, dot: RED, items: [
    { t: 'BBLUNT Cherry Red Hair Colour 130 g', b: true },
    { t: 'TDC 20% Actives Peptide–Stem Cell Hair Serum', b: true },
    { t: 'Audit listing, stock receipt, OSA and launch visibility before any further loading.' }
  ]});
  let yb = card(s, { x: M + bw + 0.16, y, w: bw, h: 1.62, label: 'ALLOCATION RULE', accent: TEAL });
  bullets(s, { x: M + bw + 0.28, y: yb + 0.04, w: bw - 0.24, gap: 0.36, size: 7.2, dot: TEAL, items: [
    { t: 'Freeze incremental NPI into East until conversion clears 60%.', b: true },
    { t: 'Hold North NPI allocation until conversion clears 70%.' },
    { t: 'Route new launches through West, South-1 and Apollo first — the pipes that already convert.' }
  ]});

  y += 1.76;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.62, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText([
    { text: 'THE TEST THAT IS MISSING   ', options: { color: TEAL, bold: true, fontSize: 7 } },
    { text: 'NPI is currently judged on offtake alone, which cannot separate a weak product from a weak pipe. Report every launch as offtake per selling store against the zone conversion it was placed into. Until that split exists, a slow NPI in East and a slow NPI in West look identical on this page — and they need opposite decisions.', options: { fontSize: 7.2, color: INK } }
  ], txt({ x: M + 0.14, y: y + 0.08, w: CW - 0.28, h: 0.48, lineSpacingMultiple: 0.94 }));
}

/* ---------------------------------------------------------------- S16 */
{
  const s = page(19, 'Three chains hold ₹13.27 Cr of gap; three more hide ₹2.23 Cr behind unmapped primary',
    'Chain deep dive | gross positive and gross negative gap | July 2026 | ₹ Cr', SRC_MAIN);

  chartTitle(s, M, BODY_Y, CW, 'Primary vs offtake by chain (₹ Cr) — Lulu bills through an unmapped route');
  s.addChart(pres.ChartType.bar, [
    { name: 'Primary', labels: CH['16'][0].series[0].cats, values: CH['16'][0].series[0].vals },
    { name: 'Offtake', labels: CH['16'][0].series[1].cats, values: CH['16'][0].series[1].vals }
  ], Object.assign({}, axisBase, {
    x: M - 0.02, y: BODY_Y + 0.24, w: CW, h: 2.30, barGapWidthPct: 45,
    chartColors: [BLUE, BRIGHT], showLegend: true, legendPos: 'b', legendFontSize: 6.4, legendColor: GREY
  }));

  let y = BODY_Y + 2.66;
  const c3 = (CW - 0.24) / 3, cx3 = i => M + i * (c3 + 0.12);
  const sig = [
    { l: 'RELIANCE', a: RED, big: '₹7.61 Cr', sub: '51.4% conversion — largest single gap' },
    { l: 'DMART', a: AMBER, big: '₹4.29 Cr', sub: '76.5% conversion — concentrated in South-2' },
    { l: 'APOLLO', a: GREEN, big: '99.7%', sub: 'near parity, but zone figures need reconciling' }
  ];
  sig.forEach((t, i) => {
    const y0 = card(s, { x: cx3(i), y, w: c3, h: 1.02, label: t.l, accent: t.a });
    s.addText(t.big, txt({ x: cx3(i) + 0.10, y: y0, w: c3 - 0.20, h: 0.34, fontSize: 16, bold: true, fontFace: FONTH, color: t.a, align: 'center' }));
    s.addText(t.sub, txt({ x: cx3(i) + 0.10, y: y0 + 0.36, w: c3 - 0.20, h: 0.22, fontSize: 6.6, color: GREY, align: 'center', lineSpacingMultiple: 0.92 }));
  });

  y += 1.18;
  y = banner(s, y, 'GROSS GAP — POSITIVE AND NEGATIVE REPORTED SEPARATELY', RED);
  y = table(s, {
    x: M, y, w: CW, rowH: 0.34, size: 7.2, cols: [
      { t: 'CHAIN', w: 1.8 }, { t: 'PRIMARY', w: 1.0, a: 'right' }, { t: 'OFFTAKE', w: 1.0, a: 'right' },
      { t: 'GAP', w: 0.95, a: 'right' }, { t: 'CONV.', w: 0.85, a: 'right' }, { t: 'READ', w: 2.3 }
    ],
    rows: [
      [{ t: 'Reliance', b: true }, '15.66', '8.06', { t: '+7.61', b: true, c: RED }, { t: '51.4%', c: RED }, { t: 'Billed and unsold — recover', c: RED }],
      [{ t: 'DMart', b: true }, '18.25', '13.97', { t: '+4.29', b: true, c: AMBER }, { t: '76.5%', c: AMBER }, 'Recover, concentrated in South-2'],
      [{ t: 'Metro', b: true }, '1.84', '0.49', { t: '+1.36', b: true, c: AMBER }, { t: '26.5%', c: RED }, 'Range dilution, small base'],
      [{ t: 'Lulu', b: true }, { t: '0.00', c: AMBER }, '1.70', { t: '−1.70', b: true, c: AMBER }, { t: 'n/a', c: AMBER }, { t: 'Primary not mapped — cannot test', c: AMBER }],
      [{ t: 'Health & Glow', b: true }, '0.22', '0.51', { t: '−0.29', c: AMBER }, { t: 'n/a', c: AMBER }, { t: 'Primary route incomplete', c: AMBER }],
      [{ t: 'Wellness Forever', b: true }, '0.49', '0.72', { t: '−0.24', c: AMBER }, { t: 'n/a', c: AMBER }, { t: 'Primary route incomplete', c: AMBER }]
    ]
  });

  y += 0.16;
  const bw = (CW - 0.16) / 2;
  let ya = card(s, { x: M, y, w: bw, h: 1.16, label: 'GROSS POSITIVE GAP', accent: RED });
  s.addText('₹13.27 Cr', txt({ x: M + 0.10, y: ya, w: bw - 0.20, h: 0.34, fontSize: 16, bold: true, fontFace: FONTH, color: RED, align: 'center' }));
  s.addText('Billed but not yet sold through, in three chains. This is the recoverable pool — 90.7% of it in DMart and Reliance alone.', txt({
    x: M + 0.14, y: ya + 0.38, w: bw - 0.28, h: 0.36, fontSize: 6.8, color: GREY, align: 'center', lineSpacingMultiple: 0.92 }));
  let yb = card(s, { x: M + bw + 0.16, y, w: bw, h: 1.16, label: 'GROSS NEGATIVE GAP', accent: AMBER });
  s.addText('₹2.23 Cr', txt({ x: M + bw + 0.26, y: yb, w: bw - 0.20, h: 0.34, fontSize: 16, bold: true, fontFace: FONTH, color: AMBER, align: 'center' }));
  s.addText('Sold with no primary joined, in three chains. Not performance — a mapping defect that was previously netted against the pool above.', txt({
    x: M + bw + 0.30, y: yb + 0.38, w: bw - 0.28, h: 0.36, fontSize: 6.8, color: GREY, align: 'center', lineSpacingMultiple: 0.92 }));

  y += 1.32;
  y = banner(s, y, 'ACCOUNT PLAN');
  bullets(s, { x: M + 0.10, y: y + 0.02, w: CW - 0.20, gap: 0.40, size: 7.4, items: [
    { t: 'Reliance: attack North and East first — ₹3.92 Cr recoverable at DMart parity. Convert billed inventory through hero-SKU visibility and replenishment, not new loading.', b: true },
    { t: 'DMart: attack South-2 first, then North. Review top-SKU store availability and DC-to-store fill; West and Central prove the account can run above 94%.' },
    { t: 'Apollo: protect the cadence and reconcile zone-level opening stock so the 99.7% national figure becomes quotable.' },
    { t: 'Lulu, Health & Glow, Wellness Forever: map primary before any commercial conclusion. Three chains and ₹2.23 Cr are currently unreadable.', c: AMBER }
  ]});
}

/* ---------------------------------------------------------------- S17 */
{
  const s = page(20, 'Two brands carry 98.4% of offtake; Face Cleanser alone carries a third',
    'Brand and sub-category architecture | July 2026', SRC_MAIN);

  const chW = 4.20;
  chartTitle(s, M, BODY_Y, chW, 'Primary vs offtake, the two engine brands (₹ Cr)');
  s.addChart(pres.ChartType.bar, [
    { name: 'Primary', labels: ['Mamaearth', 'The Derma Co.'], values: [33.38, 15.19] },
    { name: 'Offtake', labels: ['Mamaearth', 'The Derma Co.'], values: [24.49, 11.03] }
  ], Object.assign({}, axisBase, {
    x: M - 0.02, y: BODY_Y + 0.24, w: chW, h: 1.86, barGapWidthPct: 70,
    chartColors: [BLUE, BRIGHT], showLegend: true, legendPos: 'b', legendFontSize: 6.4, legendColor: GREY,
    showValue: true, dataLabelPosition: 'outEnd', dataLabelFontSize: 6.6, dataLabelColor: INK,
    dataLabelFormatCode: '0.00', valAxisMaxVal: 40
  }));
  {
    const sx = M + chW + 0.16, sw = CW - chW - 0.16;
    const y0 = card(s, { x: sx, y: BODY_Y, w: sw, h: 2.26, label: 'THE SAME GAP, TWICE', accent: RED });
    s.addText('₹13.05 Cr', txt({ x: sx + 0.10, y: y0, w: sw - 0.20, h: 0.36, fontSize: 16, bold: true, fontFace: FONTH, color: RED, align: 'center' }));
    s.addText('combined gap across both engines', txt({ x: sx + 0.10, y: y0 + 0.38, w: sw - 0.20, h: 0.18, fontSize: 6.8, color: GREY, align: 'center' }));
    bullets(s, { x: sx + 0.12, y: y0 + 0.62, w: sw - 0.24, gap: 0.40, size: 7, dot: RED, items: [
      { t: 'Mamaearth ₹8.89 Cr at 73.4% conversion.' },
      { t: 'The Derma Co. ₹4.16 Cr at 72.6%.' },
      { t: 'Within 0.8 pp of each other — the constraint is the channel, not the brand.', b: true }
    ]});
  }

  let y = BODY_Y + 2.40;
  y = table(s, {
    x: M, y, w: CW, rowH: 0.30, size: 7, cols: [
      { t: 'BRAND', w: 1.8 }, { t: 'PRIMARY', w: 1.0, a: 'right' }, { t: 'OFFTAKE', w: 1.0, a: 'right' },
      { t: 'CONV.', w: 0.85, a: 'right' }, { t: 'SHARE OF OFFTAKE', w: 1.3, a: 'right' }, { t: 'READ', w: 2.0 }
    ],
    rows: [
      [{ t: 'Mamaearth', b: true }, '33.38', '24.49', { t: '73.4%', b: true, c: AMBER }, { t: '67.8%', b: true }, 'Engine — protect hero EANs'],
      [{ t: 'The Derma Co.', b: true }, '15.19', '11.03', { t: '72.6%', b: true, c: AMBER }, { t: '30.6%', b: true }, '₹4.16 Cr gap — same flow problem'],
      ['Aqualogica', '0.41', '0.48', { t: 'over 100%', c: AMBER }, '1.3%', { t: 'Stock or timing — validate', c: AMBER }],
      ['BBLUNT', '0.18', '0.06', { t: '35.2%', c: RED }, '0.2%', { t: 'Below materiality floor', c: GREY }],
      ["Dr. Sheth's", '0.00', '0.03', { t: 'n/a', c: AMBER }, '0.1%', { t: 'No mapped primary', c: AMBER }]
    ]
  });

  y += 0.20;
  const halfW = (CW - 0.16) / 2;
  chartTitle(s, M, y, halfW, 'Mamaearth top 3 sub-categories (₹ Cr, Feb–Jul)');
  s.addChart(pres.ChartType.line, CH['17'][1].series.map(se => ({ name: se.name, labels: se.cats, values: se.vals })),
    Object.assign({}, axisBase, {
      x: M - 0.02, y: y + 0.22, w: halfW, h: 1.52, chartColors: [BRIGHT, BLUE, RED],
      lineSize: 2, lineSmooth: false, showLegend: true, legendPos: 'b', legendFontSize: 6, legendColor: GREY
    }));
  chartTitle(s, M + halfW + 0.16, y, halfW, 'The Derma Co. top 3 sub-categories (₹ Cr, Feb–Jul)');
  s.addChart(pres.ChartType.line, CH['17'][2].series.map(se => ({ name: se.name, labels: se.cats, values: se.vals })),
    Object.assign({}, axisBase, {
      x: M + halfW + 0.14, y: y + 0.22, w: halfW, h: 1.52, chartColors: [BRIGHT, BLUE, RED],
      lineSize: 2, lineSmooth: false, showLegend: true, legendPos: 'b', legendFontSize: 6, legendColor: GREY
    }));

  y += 1.86;
  y = banner(s, y, 'PORTFOLIO IMPLICATIONS');
  bullets(s, { x: M + 0.10, y: y + 0.02, w: CW - 0.20, gap: 0.40, size: 7.4, items: [
    { t: 'Both engines convert at the same rate — 73.4% and 72.6%. The flow problem is channel-wide, not brand-specific, so it will not be fixed by brand-level action.', b: true },
    { t: 'Mamaearth Face Cleanser closed July at ₹8.53 Cr and The Derma Co. Face Cleanser at ₹7.13 Cr. One sub-category is ₹15.66 Cr — 43% of all Modern Trade offtake.' },
    { t: 'The Derma Co. Face Cleanser has climbed every month since February and accelerated sharply into July; Mamaearth Sun Care has turned down since May.' },
    { t: 'Aqualogica shows offtake above primary and Dr. Sheth\'s has no mapped primary; BBLUNT at ₹0.06 Cr sits below the materiality floor. All three are exception-report only.', c: AMBER }
  ]});

  y += 4 * 0.40 + 0.14;   // clears the four bullets above
  y = banner(s, y, 'CONCENTRATION — WHAT THIS PORTFOLIO SHAPE MEANS', AMBER);
  const c3c = (CW - 0.24) / 3, cxc = i => M + i * (c3c + 0.12);
  const conc = [
    { l: 'TWO BRANDS', a: AMBER, big: '98.4%', sub: 'of offtake', items: [
      { t: 'The three remaining brands total ₹0.57 Cr — 1.6%.', b: true },
      { t: 'Any shock to either engine is a channel-level shock.' } ] },
    { l: 'ONE SUB-CATEGORY', a: RED, big: '43%', sub: 'Face Cleanser share of offtake', items: [
      { t: '₹15.66 Cr across both brands in one sub-category.', b: true },
      { t: 'Category risk is higher than the brand split suggests.' } ] },
    { l: 'THE DIVERGENCE TO WATCH', a: TEAL, big: 'Opposite ways', sub: 'since May', items: [
      { t: 'TDC Face Cleanser has accelerated every month to ₹7.13 Cr.', b: true },
      { t: 'Confirm Mamaearth Sun Care\'s fall is seasonal before cutting range.' } ] }
  ];
  conc.forEach((t, i) => {
    const y0 = card(s, { x: cxc(i), y, w: c3c, h: 1.74, label: t.l, accent: t.a });
    s.addText(t.big, txt({ x: cxc(i) + 0.10, y: y0, w: c3c - 0.20, h: 0.34, fontSize: 15, bold: true, fontFace: FONTH, color: t.a, align: 'center' }));
    s.addText(t.sub, txt({ x: cxc(i) + 0.10, y: y0 + 0.36, w: c3c - 0.20, h: 0.18, fontSize: 6.6, color: GREY, align: 'center' }));
    bullets(s, { x: cxc(i) + 0.12, y: y0 + 0.58, w: c3c - 0.24, gap: 0.38, size: 6.7, items: t.items, dot: t.a });
  });
}

/* ---------------------------------------------------------------- S18 */
{
  const s = page(21, 'A 90-day cadence that converts ₹6.22 Cr without loading a single extra case',
    'Sales uplift plan | actions ranked by value at stake, with owners and proof points', SRC_MAIN);

  s.addShape(pres.ShapeType.roundRect, { x: M, y: BODY_Y, w: CW, h: 0.72, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText('Every action below is priced. Anything that cannot be priced is a hygiene task, not a growth action.', txt({
    x: M + 0.16, y: BODY_Y + 0.08, w: CW - 0.32, h: 0.28, fontSize: 9.5, bold: true, fontFace: FONTH, color: TEAL, align: 'center', valign: 'middle' }));
  s.addText('Baseline: do nothing and July repeats — ₹36.10 Cr offtake at 73.4% conversion, with ₹13.27 Cr billed and unsold.', txt({
    x: M + 0.16, y: BODY_Y + 0.40, w: CW - 0.32, h: 0.24, fontSize: 7.2, color: GREY, align: 'center' }));

  let y = BODY_Y + 0.88;
  y = banner(s, y, 'ACTIONS RANKED BY VALUE AT STAKE', RED);
  y = table(s, {
    x: M, y, w: CW, rowH: 0.40, size: 7.2, cols: [
      { t: '#', w: 0.26, a: 'right' }, { t: 'ACTION', w: 3.5 }, { t: 'AT STAKE', w: 0.9, a: 'right' },
      { t: 'WINDOW', w: 0.8 }, { t: 'OWNER', w: 1.6 }
    ],
    rows: [
      ['1', { t: 'Reliance recovery loop — halt loading, hero-EAN OSA audit across North, East, Central', b: true }, { t: '₹3.92 Cr', b: true, c: RED }, '0–30d', 'NKAM Reliance + Supply'],
      ['2', { t: 'DMart South-2 DC-to-store fill audit against the West benchmark', b: true }, { t: '₹0.90 Cr', b: true, c: RED }, '0–30d', 'NKAM DMart + Supply'],
      ['3', 'Cap East and North primary at trailing three-month offtake until gaps close', { t: '₹2.54 Cr', b: true, c: AMBER }, '0–30d', 'Supply + Sales lead'],
      ['4', 'Map Lulu, Wellness Forever and Health & Glow primary routes', { t: '₹2.23 Cr', b: true, c: AMBER }, '0–15d', 'Analyst'],
      ['5', 'Freeze incremental NPI into East and North until conversion thresholds clear', { t: '₹0.65 Cr', c: AMBER }, '0–30d', 'Category + Supply'],
      ['6', 'Publish the chain × state × hero-EAN exception list weekly', { t: 'enabler', c: GREY }, '0–30d', 'Analyst'],
      ['7', 'Extract the Apollo order-cadence template and score two accounts against it', { t: 'enabler', c: GREY }, '31–60d', 'Analyst + NKAM Apollo'],
      ['8', 'Shampoo rate-recovery pilot in South-1 — velocity per store, not listings added', { t: 'test', c: GREY }, '31–60d', 'Category + South-1 RKAM'],
      ['9', 'Reset loading rules by verified conversion; retire dead packs before adding new', { t: 'structural', c: GREY }, '61–90d', 'Sales lead + Category']
    ]
  });

  y += 0.20;
  const c3 = (CW - 0.24) / 3, cx3 = i => M + i * (c3 + 0.12);
  const phases = [
    { l: '0–30 DAYS', a: RED, big: 'Stop the leak', items: [
      { t: 'Halt Reliance loading below 65% conversion.', b: true },
      { t: 'Cap North and East primary at trailing offtake.' },
      { t: 'Close the three primary-mapping gaps.' },
      { t: 'Publish the first exception list.' } ] },
    { l: '31–60 DAYS', a: AMBER, big: 'Prove the fix', items: [
      { t: 'Score accounts against the Apollo cadence template.', b: true },
      { t: 'Run the South-1 shampoo rate pilot.' },
      { t: 'Size distribution white space in ₹ using stores × PDO.' },
      { t: 'Test the FSN delisting hypothesis.' } ] },
    { l: '61–90 DAYS', a: GREEN, big: 'Lock it in', items: [
      { t: 'Reset loading rules by verified conversion.', b: true },
      { t: 'Rationalise dead and low-productivity packs.' },
      { t: 'Scale only what offtake has proven.' },
      { t: 'Embed weekly owner and action receipts.' } ] }
  ];
  phases.forEach((p, i) => {
    const y0 = card(s, { x: cx3(i), y, w: c3, h: 2.48, label: p.l, accent: p.a });
    s.addText(p.big, txt({ x: cx3(i) + 0.10, y: y0, w: c3 - 0.20, h: 0.30, fontSize: 11.5, bold: true, fontFace: FONTH, color: p.a, align: 'center' }));
    bullets(s, { x: cx3(i) + 0.12, y: y0 + 0.40, w: c3 - 0.24, gap: 0.40, size: 6.9, items: p.items, dot: p.a });
  });

  y += 2.64;
  y = banner(s, y, 'WEEKLY MANAGEMENT SCOREBOARD');
  y = table(s, {
    x: M, y, w: CW, rowH: 0.36, size: 7.2, cols: [
      { t: 'MEASURE', w: 2.6 }, { t: 'TARGET', w: 1.6, a: 'right' }, { t: 'OWNER', w: 1.7 }, { t: 'STATUS AT JULY', w: 1.4, a: 'right' }
    ],
    rows: [
      [{ t: 'Flow conversion — the one metric', b: true }, { t: 'above 85%', b: true, c: GREEN }, 'Sales lead', { t: '73.4%', c: RED }],
      ['North gap vs benchmark', { t: 'falling weekly', c: GREEN }, 'North ZSM', { t: '−₹2.78 Cr', c: RED }],
      ['East gap vs benchmark', { t: 'falling weekly', c: GREEN }, 'East ZSM', { t: '−₹2.54 Cr', c: RED }],
      ['Hero-SKU OSA, priority stores', { t: 'above 95%', c: GREEN }, 'KAM + Supply', { t: 'not measured', c: AMBER }],
      ['Reliance conversion', { t: 'above 65%', c: GREEN }, 'NKAM Reliance', { t: '51.4%', c: RED }],
      ['Chains with unmapped primary', { t: 'zero', c: GREEN }, 'Analyst', { t: '3 chains', c: RED }]
    ]
  });
}

/* ---------------------------------------------------------------- S19 */
{
  const s = page(22, 'Decision-safe definitions, quality gates and authority boundaries',
    'Audit command centre | grain, conformity, coverage and controlled execution', SRC_MAIN);

  s.addShape(pres.ShapeType.roundRect, { x: M, y: BODY_Y, w: CW, h: 0.86, rectRadius: 0.03, fill: { color: TINT }, line: { color: BRIGHT, width: 1 } });
  s.addText('Use this pack to prioritise investigation and owner action — not to infer inventory, causality or autonomous execution.', txt({
    x: M + 0.18, y: BODY_Y + 0.10, w: CW - 0.36, h: 0.36, fontSize: 9.5, bold: true, fontFace: FONTH, color: TEAL, align: 'center', valign: 'middle' }));
  s.addText('Every consequential commercial change remains subject to named human approval.', txt({
    x: M + 0.18, y: BODY_Y + 0.50, w: CW - 0.36, h: 0.24, fontSize: 7.2, color: GREY, align: 'center' }));

  let y = BODY_Y + 1.02;
  y = banner(s, y, 'THE GRAIN — ONE STATED BASE, NO NETTING', RED);
  y = table(s, {
    x: M, y, w: CW, rowH: 0.34, size: 7.2, cols: [
      { t: 'MEASURE', w: 2.1 }, { t: 'VALUE', w: 1.1, a: 'right' }, { t: 'GRAIN', w: 1.9 }, { t: 'RULE', w: 2.5 }
    ],
    rows: [
      [{ t: 'Primary', b: true }, '₹49.21 Cr', 'invoice net value, zone', 'July primary sheet, converted to ₹ Cr'],
      [{ t: 'Offtake', b: true }, '₹36.10 Cr', 'transaction NSV, store', 'Consumer-facing flow measure'],
      [{ t: 'Gross positive gap', b: true }, { t: '₹13.27 Cr', b: true, c: RED }, 'chain, mapped only', 'Billed and unsold — the recoverable pool'],
      [{ t: 'Gross negative gap', b: true }, { t: '₹2.23 Cr', b: true, c: AMBER }, 'chain, unmapped primary', 'A join defect — never netted against the pool'],
      [{ t: 'Zone gap, summed', b: true }, { t: '₹13.06 Cr', b: true, c: RED }, 'six geographic zones', 'Excludes Pan India, which has no primary'],
      [{ t: 'Flow conversion', b: true }, '73.4%', 'non-additive ratio', 'Recompute from sums — never average zones']
    ]
  });

  y += 0.18;
  const c3 = (CW - 0.24) / 3, cx3 = i => M + i * (c3 + 0.12);
  const gates = [
    { l: 'CONFORMED DIMENSIONS', a: RED, big: '3 breaks', items: [
      { t: 'Lulu, Wellness Forever, Health & Glow appear in offtake, not in primary.', b: true },
      { t: 'FSN and Nykaa SS are combined at article level and cannot be separated.' },
      { t: 'Pan India carries no geographic primary by design.' },
      { t: 'A validated outer merge surfaces all of these automatically.' } ] },
    { l: 'NON-ADDITIVE FACTS', a: AMBER, big: 'Ratios never sum', items: [
      { t: 'Apollo national reads 99.7%; zones read 121%, 138% and 149%.', b: true },
      { t: 'The national figure is averaging error, not measured parity.' },
      { t: 'Any conversion above 100% is stock or timing, never performance.' },
      { t: 'Do not quote a ratio without stating its denominator.' } ] },
    { l: 'COVERAGE', a: TEAL, big: '79.2%', items: [
      { t: 'Chain scorecard covers ₹26.90 Cr of ₹33.96 Cr national MT offtake.', b: true },
      { t: '31,355 of 1,97,740 primary and offtake rows are matched.' },
      { t: 'Missing zone rows: 0. Period: July 2026.' },
      { t: 'Chains with missing July feeds are data gaps, not de-growth.' } ] },
    { l: 'MATERIALITY FLOOR', a: AMBER, big: '₹0.25 Cr', items: [
      { t: 'No % shown, ranked or coloured below this base.', b: true },
      { t: 'Removes 10 of 13 chains from the scorecard ranking.' },
      { t: 'Central zone recovery (₹0.11 Cr) falls below it.' },
      { t: 'Below the floor, report the absolute ₹ change only.' } ] },
    { l: 'STILL TO RECONCILE', a: GREY, big: 'Five fields', items: [
      { t: 'SAH, weighted distribution by chain, PDO, OOS, closing stock.', b: true },
      { t: 'Until these tie, cause is inferred and not measured.' },
      { t: 'No SAH × share diagnosis is claimed in this pack.' },
      { t: 'Stock pressure and turnover remain out of scope.' } ] },
    { l: 'AUTHORITY', a: TEAL, big: 'Ask first', items: [
      { t: 'Analysis recommends and sizes; it does not decide.', b: true },
      { t: 'NKAM, RKAM and KAM approve loading, range and distribution.' },
      { t: 'Record what changed, the evidence, the owner and the date.' },
      { t: 'Revoke or stop when the proof point fails.' } ] }
  ];
  gates.forEach((g, i) => {
    const r = Math.floor(i / 3), c = i % 3;
    const yy = y + r * (2.62 + 0.14);
    const y0 = card(s, { x: cx3(c), y: yy, w: c3, h: 2.62, label: g.l, accent: g.a });
    s.addText(g.big, txt({ x: cx3(c) + 0.10, y: y0, w: c3 - 0.20, h: 0.34, fontSize: 13, bold: true, fontFace: FONTH, color: g.a, align: 'center', valign: 'middle' }));
    bullets(s, { x: cx3(c) + 0.12, y: y0 + 0.42, w: c3 - 0.24, gap: 0.40, size: 6.9, items: g.items, dot: g.a });
  });

  y += 2 * (2.62 + 0.14) + 0.06;
  s.addShape(pres.ShapeType.roundRect, { x: M, y, w: CW, h: 0.52, rectRadius: 0.02, fill: { color: 'FBEDEC' }, line: { color: RED, width: 0.75 } });
  s.addText([
    { text: 'CHANGED SINCE THE PREVIOUS PACK   ', options: { color: RED, bold: true, fontSize: 6.8 } },
    { text: 'Zone sales are now Modern Trade only. eB2B (₹2.20 Cr primary) and SIS are reported as their own channels, cut from the full July source with Channel == MT applied before aggregation. MT primary ₹47.02 Cr, MT offtake ₹33.96 Cr, gap ₹13.06 Cr — and national MT offtake now ties exactly to the sum of the six MT zones.', options: { fontSize: 7, color: INK } }
  ], txt({ x: M + 0.12, y: y + 0.06, w: CW - 0.24, h: 0.42, lineSpacingMultiple: 0.94 }));
}

/* ---------------------------------------------------------------- write */
const OUT = process.argv[2] ||
  path.join(__dirname, '..', 'July_MT_Command_Centre_REWORKED.pptx');
pres.writeFile({ fileName: OUT })
  .then(f => console.log('written:', f));
