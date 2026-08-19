/**
 * MT Jul-26 Honasa — Portrait Summary (A4-ish, 7.5" × 10")
 * Key slides: Cover, Executive Summary, Zone Scorecard, Chain Deep-dive,
 *             eB2B / FSN, NPI, 90-Day Plan
 */

const pptxgen = require('pptxgenjs');

const prs = new pptxgen();
prs.layout = 'LAYOUT_4x3';   // 10 × 7.5 — flip to portrait by setting w/h on slide

// Portrait: override via CUSTOM layout (portrait: 7.5" wide × 10" tall)
prs.defineLayout({ name: 'PORTRAIT', width: 7.5, height: 10 });
prs.layout = 'PORTRAIT';

// --- Palette (Honasa teal) ---
const C = {
  teal:  '116F68',
  dteal: '183B39',
  green: '2B9A66',
  amber: 'F2B84B',
  red:   'D6544D',
  bg:    'F7FBFA',
  mint:  'DFF2ED',
  white: 'FFFFFF',
  text:  '1A2E2C',
  muted: '4A7B77',
};

const W = 7.5, H = 10;
const margin = 0.35;
const inner = W - 2 * margin;

function addSlide(title, subtitle, content) {
  const sl = prs.addSlide();
  // Background
  sl.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: C.bg }, line: { color: C.bg } });
  // Header bar
  sl.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: W, h: 1.0, fill: { color: C.teal }, line: { color: C.teal } });
  // Title
  sl.addText(title, {
    x: margin, y: 0.08, w: inner, h: 0.6,
    fontSize: 18, bold: true, color: C.white, fontFace: 'Calibri',
    valign: 'middle', wrap: true,
  });
  if (subtitle) {
    sl.addText(subtitle, {
      x: margin, y: 0.62, w: inner, h: 0.32,
      fontSize: 9, color: C.mint, fontFace: 'Calibri', italic: true,
    });
  }
  return sl;
}

function addKpiRow(sl, kpis, yTop) {
  // kpis = [{label, value, sub}]
  const n = kpis.length;
  const cellW = inner / n;
  kpis.forEach((k, i) => {
    const x = margin + i * cellW;
    sl.addShape(prs.ShapeType.rect, {
      x, y: yTop, w: cellW - 0.08, h: 0.9,
      fill: { color: C.mint }, line: { color: C.teal, pt: 1 }
    });
    sl.addText(k.label, { x: x + 0.06, y: yTop + 0.04, w: cellW - 0.18, h: 0.22, fontSize: 7, color: C.muted, bold: true, fontFace: 'Calibri' });
    sl.addText(k.value, { x: x + 0.06, y: yTop + 0.24, w: cellW - 0.18, h: 0.36, fontSize: 15, bold: true, color: C.dteal, fontFace: 'Calibri' });
    if (k.sub) {
      sl.addText(k.sub, { x: x + 0.06, y: yTop + 0.58, w: cellW - 0.18, h: 0.22, fontSize: 7, color: k.subColor || C.muted, fontFace: 'Calibri' });
    }
  });
}

function addFooter(sl, label, text) {
  sl.addShape(prs.ShapeType.rect, { x: 0, y: H - 0.8, w: W, h: 0.8, fill: { color: C.dteal }, line: { color: C.dteal } });
  sl.addText(label + '  ' + text, {
    x: margin, y: H - 0.74, w: inner, h: 0.64,
    fontSize: 7.5, color: C.white, fontFace: 'Calibri', wrap: true, valign: 'top',
  });
}

function bullet(sl, items, x, y, w, h) {
  const rows = items.map(t => ({ text: t, options: { bullet: true, breakLine: true, paraSpaceAfter: 3 } }));
  sl.addText(rows, { x, y, w, h, fontSize: 8.5, color: C.text, fontFace: 'Calibri', valign: 'top', margin: 0 });
}

// ============================================================
// SLIDE 1 — Cover
// ============================================================
{
  const sl = prs.addSlide();
  sl.addShape(prs.ShapeType.rect, { x: 0, y: 0, w: W, h: H, fill: { color: C.dteal }, line: { color: C.dteal } });
  sl.addShape(prs.ShapeType.rect, { x: 0, y: H * 0.55, w: W, h: H * 0.45, fill: { color: C.teal }, line: { color: C.teal } });
  sl.addText('MT OFFTAKE PERFORMANCE', { x: margin, y: 1.8, w: inner, h: 0.55, fontSize: 10, bold: true, color: C.mint, fontFace: 'Calibri', align: 'center' });
  sl.addText('July 2026', { x: margin, y: 2.35, w: inner, h: 1.4, fontSize: 52, bold: true, color: C.white, fontFace: 'Calibri', align: 'center' });
  sl.addText('Leadership Review', { x: margin, y: 3.75, w: inner, h: 0.45, fontSize: 13, color: C.amber, fontFace: 'Calibri', align: 'center', italic: true });
  sl.addText('Honasa Consumer Ltd  |  Modern Trade Channel', { x: margin, y: H * 0.57, w: inner, h: 0.4, fontSize: 9, color: C.mint, fontFace: 'Calibri', align: 'center' });
  sl.addText('Confidential — For internal leadership use only', { x: margin, y: H - 0.5, w: inner, h: 0.35, fontSize: 7, color: C.mint, fontFace: 'Calibri', align: 'center' });
}

// ============================================================
// SLIDE 2 — Executive Summary
// ============================================================
{
  const sl = addSlide('EXECUTIVE SUMMARY — JULY 2026', 'Modern Trade | Primary vs Offtake | ₹ Cr');

  addKpiRow(sl, [
    { label: 'MT OFFTAKE JUL', value: '₹36.06 Cr', sub: '+64.2% YoY', subColor: C.green },
    { label: 'L3M MAY–JUL', value: '₹114.66 Cr', sub: '+65.8% YoY', subColor: C.green },
    { label: 'FLOW CONV.', value: '73.4%', sub: 'vs >90% target', subColor: C.red },
    { label: 'GAP', value: '₹13.11 Cr', sub: 'North + East 70.5%', subColor: C.red },
  ], 1.1);

  const summaryBullets = [
    '₹36.06 Cr Jul offtake (+64.2% YoY); L3M ₹114.66 Cr (+65.8% YoY) — demand is growing faster than conversion is allowing.',
    'National gap: ₹13.11 Cr at 73.4% conversion. North (58.5%) and East (45.3%) hold 70.5% of gap — both are execution failures, not demand failures.',
    'Apollo 99.7% conversion proves demand is real. DMart 76.5% and Reliance 51.4% are recoverable through EAN-level action.',
    'eB2B / FSN+Nykaa: ₹2.07 Cr at 99.4% flow — outperforms MT by 26 pp. FYTD ₹8.79 Cr.',
    'NPI: ₹2.82 Cr (7.82% mix), 58/60 EANs billing. Reliance 46.3% + DMart 34.6% = 80.9% of NPI value. Two zero-sellers need audit before next load.',
    '90-Day plan: Phase 1 — field reconciliation (Aug); Phase 2 — white-space sizing (Sep); Phase 3 — controlled scale (Oct).',
  ];
  bullet(sl, summaryBullets, margin, 2.1, inner, 5.2);

  addFooter(sl, 'DECISION:', "Do not increase primary loading into North/East until EAN-level exceptions are resolved. Apollo's 99.7% is the execution benchmark. Weekly scoreboard from 22-Aug.");
}

// ============================================================
// SLIDE 3 — Zone Scorecard
// ============================================================
{
  const sl = addSlide('NORTH + EAST HOLD 70.5% OF NATIONAL GAP', 'Zone portfolio | primary vs offtake | July 2026');

  // Zone table
  const rows = [
    ['Zone', 'Primary ₹Cr', 'Offtake ₹Cr', 'Conv.', 'Gap ₹Cr', 'Status'],
    ['West',    '10.05', '8.28',  '82.3%', '1.78', 'WATCH'],
    ['South-1', '9.80',  '8.19',  '83.6%', '1.61', 'WATCH'],
    ['Central', '2.69',  '2.12',  '78.8%', '0.57', 'WATCH'],
    ['South-2', '6.89',  '4.91',  '71.3%', '1.98', 'FIX'],
    ['North',   '11.95', '6.99',  '58.5%', '4.97', 'FIX'],
    ['East',    '7.83',  '3.55',  '45.3%', '4.28', 'FIX'],
  ];
  const colW = [1.2, 1.0, 1.0, 0.8, 0.9, 0.8];
  const rowH = 0.36;
  let ty = 1.1;
  rows.forEach((row, ri) => {
    let tx = margin;
    row.forEach((cell, ci) => {
      const isHdr = ri === 0;
      const isFixRow = ['North', 'East', 'South-2'].includes(row[0]);
      const isStatus = ci === 5;
      const bg = isHdr ? C.teal : (isFixRow ? 'FFF0EF' : C.mint);
      const tc = isHdr ? C.white : (isStatus && cell === 'FIX' ? C.red : (isStatus && cell === 'WATCH' ? C.green : C.text));
      sl.addShape(prs.ShapeType.rect, { x: tx, y: ty, w: colW[ci] - 0.04, h: rowH, fill: { color: bg }, line: { color: 'D0E8E4', pt: 0.5 } });
      sl.addText(cell, { x: tx + 0.04, y: ty + 0.04, w: colW[ci] - 0.10, h: rowH - 0.06, fontSize: isHdr ? 7.5 : 8.5, bold: isHdr || isStatus, color: tc, fontFace: 'Calibri', valign: 'middle' });
      tx += colW[ci];
    });
    ty += rowH;
  });

  const actionBullets = [
    'Jul-26 MT offtake: ₹36.06 Cr (+64.2% YoY vs Jul-25 ₹21.96 Cr). L3M May–Jul: ₹114.66 Cr (+65.8% YoY vs ₹69.16 Cr LY).',
    'West + South-1 + Central: protect hero-SKU OSA; avoid unnecessary loading.',
    'North: weekly EAN-level gap closure in Reliance + DMart. Apollo 98.3% is the playbook.',
    'East: non-Hero SKU loading moratorium until Aug offtake confirmed. Reliance East 52.9% is the core problem.',
    'South-2: DMart S-2 45.1% = lowest DMart nationally. Store-level audit by 28-Aug.',
  ];
  bullet(sl, actionBullets, margin, ty + 0.12, inner, H - ty - 1.05);
  addFooter(sl, 'ACTION:', 'Weekly ZSM-owned gap closure loop: North → Reliance + DMart EANs; East → Reliance exclusively. Report to Sales Lead every Friday from 22-Aug.');
}

// ============================================================
// SLIDE 4 — Chain Deep-dive
// ============================================================
{
  const sl = addSlide('APOLLO 99.7% PROVES DEMAND IS REAL — DMART AND RELIANCE ARE EXECUTION GAPS', 'Chain deep dive | July 2026 | ₹ Cr');

  addKpiRow(sl, [
    { label: 'DMART GAP', value: '₹4.29 Cr', sub: '76.5% conversion', subColor: C.amber },
    { label: 'RELIANCE GAP', value: '₹7.61 Cr', sub: '51.4% conversion', subColor: C.red },
    { label: 'APOLLO', value: '99.7%', sub: 'Near-parity flow', subColor: C.green },
    { label: 'COMBINED GAP', value: '₹11.89 Cr', sub: 'DMart + Reliance', subColor: C.red },
  ], 1.1);

  const actionBullets = [
    'Apollo 99.7% conversion in the same assortment window confirms demand is present — DMart and Reliance gaps are execution deficits.',
    'DMart: attack South-2 first (45.1% conversion = lowest nationally), then North; review hero-SKU availability and DC-to-store fill rate.',
    'Reliance: North 44.9% is most critical nationally; East 52.9% requires EAN-store failure mapping with weekly owner review from 22-Aug.',
    'Replicate Apollo replenishment and review cadence across DMart and Reliance as the national execution playbook.',
    'Chains above 100%: treat as opening-stock timing signal; do not increase primary until stock is reconciled.',
    'Closing 50% of DMart + Reliance gap adds ~₹5.9 Cr monthly offtake.',
  ];
  bullet(sl, actionBullets, margin, 2.1, inner, 5.2);
  addFooter(sl, 'OWNER:', 'Sales Lead + Category | Apollo audit by 31-Aug. Reliance North EAN-store list by 05-Sep. DMart S-2 store audit by 28-Aug.');
}

// ============================================================
// SLIDE 5 — eB2B / FSN + Nykaa
// ============================================================
{
  const sl = addSlide('eB2B / FSN+NYKAA: 99.4% FLOW — OUTPERFORMS MT AVERAGE BY 26 PP', 'eB2B channel | FSN + Nykaa | January–July 2026 | Pan India');

  addKpiRow(sl, [
    { label: 'JUL-26 OFFTAKE', value: '₹2.07 Cr', sub: '-4.6% MoM', subColor: C.amber },
    { label: 'FLOW CONV.', value: '99.4%', sub: '+26 pp vs MT 73.4%', subColor: C.green },
    { label: 'FYTD APR–JUL', value: '₹8.79 Cr', sub: '4-month run rate', subColor: C.teal },
    { label: 'ACTIVE EANs', value: '198', sub: 'Down from 222 in Jan', subColor: C.muted },
  ], 1.1);

  const bullets = [
    '7-month trend: Jan ₹1.64 Cr → Feb ₹1.68 Cr → Mar ₹1.73 Cr → Apr ₹2.29 Cr → May ₹2.08 Cr → Jun ₹2.17 Cr → Jul ₹2.07 Cr. Absolute trend is positive.',
    'July -4.6% MoM is article-mix softness, not account deterioration. EAN count declining (222 → 198) while value holds = better productivity per EAN.',
    'Top articles: Rice FW 100ml ₹0.27 Cr, Rice FW 50ml ₹0.19 Cr, Ubtan FW ₹0.14 Cr. Top-2 (₹0.46 Cr combined) determine August recovery.',
    'Do NOT add new EANs until July sell-through is validated in the August read.',
    'Raise OSA target to 100% for Rice FW 100ml and Ubtan FW on Nykaa.',
    'Review article-level sell-through in Nykaa SS before September reorder decision.',
  ];
  bullet(sl, bullets, margin, 2.1, inner, 5.2);
  addFooter(sl, 'OWNER:', 'NKAM FSN / Nykaa + Category | 30-Aug. Supply chain to validate Nykaa SS article sell-through for September reorder.');
}

// ============================================================
// SLIDE 6 — NPI
// ============================================================
{
  const sl = addSlide('NPI: ₹2.82 CR — RELIANCE + DMART HOLD 80.9% OF NPI VALUE', 'NPI contribution | Overall, zone and chain | July 2026 | NSV basis');

  addKpiRow(sl, [
    { label: 'NPI SALES', value: '₹2.82 Cr', sub: 'July offtake (NSV)', subColor: C.teal },
    { label: 'MIX', value: '7.82%', sub: 'of total sales', subColor: C.teal },
    { label: 'SELLING EANs', value: '58 / 60', sub: '2 require audit', subColor: C.amber },
    { label: 'EAST NPI MIX', value: '10.2%', sub: 'Highest nationally', subColor: C.red },
  ], 1.1);

  // Chain share table
  const chains = [
    ['Reliance', '₹1.30 Cr', '46.3%'],
    ['DMart',    '₹0.98 Cr', '34.6%'],
    ['Lulu',     '₹0.18 Cr',  '6.4%'],
    ['FSN',      '₹0.13 Cr',  '4.6%'],
    ['H&G',      '₹0.06 Cr',  '2.1%'],
    ['Metro',    '₹0.05 Cr',  '1.8%'],
    ['Wellness', '₹0.04 Cr',  '1.3%'],
    ['Sancus',   '₹0.03 Cr',  '1.1%'],
  ];
  const cw = [1.6, 1.2, 1.0];
  let ty = 2.1;
  // Header
  ['Chain', 'NSV', 'Share%'].forEach((h, ci) => {
    const x = margin + [0, 1.6, 2.8][ci];
    sl.addShape(prs.ShapeType.rect, { x, y: ty, w: cw[ci] - 0.04, h: 0.28, fill: { color: C.teal }, line: { color: C.teal } });
    sl.addText(h, { x: x + 0.04, y: ty + 0.04, w: cw[ci] - 0.1, h: 0.2, fontSize: 7.5, bold: true, color: C.white, fontFace: 'Calibri' });
  });
  ty += 0.28;
  chains.forEach((row, ri) => {
    row.forEach((cell, ci) => {
      const x = margin + [0, 1.6, 2.8][ci];
      const bg = ri % 2 === 0 ? C.mint : C.white;
      sl.addShape(prs.ShapeType.rect, { x, y: ty, w: cw[ci] - 0.04, h: 0.3, fill: { color: bg }, line: { color: 'D0E8E4', pt: 0.5 } });
      sl.addText(cell, { x: x + 0.04, y: ty + 0.04, w: cw[ci] - 0.1, h: 0.22, fontSize: 8, color: C.text, fontFace: 'Calibri', valign: 'middle' });
    });
    ty += 0.3;
  });

  // Top NPI articles on the right
  const topArts = [
    'ME Onion Hair Fall Shampoo — ₹0.31 Cr',
    'ME Onion Hair Oil 200ml — ₹0.30 Cr',
    'ME Gentle Cleansing Shampoo — ₹0.21 Cr',
    'ME Multani Mitti FW 100ml — ₹0.20 Cr',
    'ME Vitamin C Glow Sunscreen — ₹0.20 Cr',
    'ME Lemon Anti-Dandruff Shampoo — ₹0.19 Cr',
    'Rosemary Anti-Hair Fall Shampoo — ₹0.18 Cr',
    'ME Rice Water Dewy Sunscreen — ₹0.18 Cr',
  ];
  sl.addText('TOP NPI ARTICLES', { x: margin + 3.3, y: 2.1, w: 3.8, h: 0.25, fontSize: 7.5, bold: true, color: C.teal, fontFace: 'Calibri' });
  const artItems = topArts.map(t => ({ text: t, options: { bullet: true, breakLine: true, paraSpaceAfter: 2 } }));
  sl.addText(artItems, { x: margin + 3.3, y: 2.38, w: 3.8, h: 2.6, fontSize: 7.5, color: C.text, fontFace: 'Calibri', valign: 'top', margin: 0 });

  sl.addText('ZERO-SALE EANs:', { x: margin + 3.3, y: 4.95, w: 3.8, h: 0.22, fontSize: 7.5, bold: true, color: C.red, fontFace: 'Calibri' });
  sl.addText('• BBLUNT Cherry Red Hair Colour 130g\n• TDC Peptide–Stem Cell Hair Serum\nAudit store receipt, shelf visibility and scheme support by 28-Aug.', {
    x: margin + 3.3, y: 5.16, w: 3.8, h: 0.9, fontSize: 7.5, color: C.text, fontFace: 'Calibri', valign: 'top',
  });

  addFooter(sl, 'OWNER:', 'Trade Marketing + Supply | 28-Aug. Prioritize Reliance + DMart NPI visibility (80.9% of NPI value). No new NPI loading until zero-sellers are cleared.');
}

// ============================================================
// SLIDE 7 — 90-Day Plan
// ============================================================
{
  const sl = addSlide('90-DAY EXECUTION PLAN: RECONCILE → SIZE → SCALE', 'Sales uplift roadmap | owners, actions and proof points | Aug–Oct 2026');

  const phases = [
    {
      label: '0–30 DAYS (AUG)', color: C.teal,
      items: ['Reconcile SAH / WD / PDO / OOS fields', 'Publish state × chain × hero-EAN gaps', 'Weekly ZSM scoreboard live from 22-Aug', 'NPI zero-seller audit by 28-Aug'],
    },
    {
      label: '31–60 DAYS (SEP)', color: C.green,
      items: ['Size white space in ₹ using productive stores × PDO', 'Run Shampoo pack pilots — DMart + Apollo (top 3 formats)', 'Restore Reliance North top-20 declining EANs by 05-Sep', 'Nykaa September reorder based on July sell-through'],
    },
    {
      label: '61–90 DAYS (OCT)', color: C.dteal,
      items: ['Scale only proven state-chain-SKU cells', 'Reset load rules by verified conversion', 'Rationalize dead/low-productivity packs', 'Embed weekly owner and action receipts'],
    },
  ];
  let py = 1.1;
  phases.forEach(ph => {
    sl.addShape(prs.ShapeType.rect, { x: margin, y: py, w: inner, h: 0.28, fill: { color: ph.color }, line: { color: ph.color } });
    sl.addText(ph.label, { x: margin + 0.1, y: py + 0.04, w: inner - 0.2, h: 0.2, fontSize: 8, bold: true, color: C.white, fontFace: 'Calibri' });
    py += 0.28;
    ph.items.forEach(item => {
      sl.addShape(prs.ShapeType.rect, { x: margin, y: py, w: inner, h: 0.32, fill: { color: C.mint }, line: { color: 'D0E8E4', pt: 0.5 } });
      sl.addText('• ' + item, { x: margin + 0.1, y: py + 0.04, w: inner - 0.2, h: 0.24, fontSize: 8.5, color: C.text, fontFace: 'Calibri', valign: 'middle' });
      py += 0.32;
    });
    py += 0.12;
  });

  // Scoreboard
  sl.addText('WEEKLY MANAGEMENT SCOREBOARD', { x: margin, y: py, w: inner, h: 0.25, fontSize: 8, bold: true, color: C.teal, fontFace: 'Calibri' });
  py += 0.25;
  const scoreboard = [
    ['Flow conversion', '>90%', 'Sales Lead'],
    ['North gap', '↓ weekly', 'North ZSM'],
    ['East gap', '↓ weekly', 'East ZSM'],
    ['Hero-SKU OSA', '>95%', 'KAM + Supply'],
    ['DMart/Reliance gap', 'Close 50%', 'KAMs'],
  ];
  scoreboard.forEach(row => {
    const bw = [2.5, 1.5, 2.3];
    const bx = [margin, margin+2.5, margin+4.0];
    row.forEach((cell, ci) => {
      sl.addShape(prs.ShapeType.rect, { x: bx[ci], y: py, w: bw[ci]-0.04, h: 0.26, fill: { color: ci===0?C.bg:C.mint }, line: { color: 'D0E8E4', pt:0.5 }});
      sl.addText(cell, { x: bx[ci]+0.04, y: py+0.03, w: bw[ci]-0.1, h: 0.2, fontSize: 7.5, color: C.text, fontFace:'Calibri', valign:'middle', bold: ci===1 });
    });
    py += 0.26;
  });

  addFooter(sl, 'CHAIR:', 'Sales Lead — first review 22-Aug. No exceptions to owner-date accountability. Analytics on data exceptions with zero unresolved by each cycle.');
}

// Write files
prs.writeFile({ fileName: '/home/user/mt-dashboard/MT_Jul26_Honasa_Portrait.pptx' })
   .then(() => console.log('Done: MT_Jul26_Honasa_Portrait.pptx'))
   .catch(e => { console.error(e); process.exit(1); });
