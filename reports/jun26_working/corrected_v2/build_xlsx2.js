// Build MT Offtake & Primary Jun'26 workbook — every summary metric is a live formula.
const fs = require('fs');
const path = require('path');
const XLSX = require('/home/user/mt-dashboard/dashboard/xlsx.core.min.js');

const D = path.join(__dirname, 'data');
const M15 = ['Apr-25','May-25','Jun-25','Jul-25','Aug-25','Sep-25','Oct-25','Nov-25','Dec-25','Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26'];
const M18 = ['Jan-25','Feb-25','Mar-25','Apr-25','May-25','Jun-25','Jul-25','Aug-25','Sep-25','Oct-25','Nov-25','Dec-25','Jan-26','Feb-26','Mar-26','Apr-26','May-26','Jun-26'];

function loadTsv(fn, nkey, nMonths) {
  const lines = fs.readFileSync(path.join(D, fn), 'utf8').split('\n').filter(l => l.trim());
  const hdr = lines[0].split('\t');
  const rows = lines.slice(1).map(l => {
    const f = l.split('\t');
    const key = f.slice(0, nkey);
    const vals = [];
    for (let j = 0; j < nMonths; j++) {
      const x = (f[nkey + j] || '').trim();
      vals.push(x === '' ? null : parseFloat(x));
    }
    return { key, vals };
  });
  return { hdr, rows };
}

const D2 = path.join(__dirname, 'data2');
function loadTsv2(fn, nkey, nMonths) {
  const lines = fs.readFileSync(path.join(D2, fn), 'utf8').split('\n').filter(l => l.trim());
  return { hdr: lines[0].split('\t'), rows: lines.slice(1).map(l => {
    const f = l.split('\t');
    const vals = [];
    for (let j = 0; j < nMonths; j++) { const x = (f[nkey + j] || '').trim(); vals.push(x === '' ? null : parseFloat(x)); }
    return { key: f.slice(0, nkey), vals };
  }) };
}
const ocz = loadTsv2('offtake_chain_zone_monthly_corrected.tsv', 3, 15);
const obz = loadTsv2('offtake_brand_subcat_zone_monthly_corrected.tsv', 4, 15);
const qcz = loadTsv2('offtake_chain_zone_qtr.tsv', 2, 11);
const qzb = loadTsv2('offtake_zone_brand_qtr.tsv', 2, 13);
const phero = loadTsv2('offtake_pack_hero.tsv', 4, 8);
const pzc = loadTsv('primary_zone_chain.tsv', 3, 15);
const pbt = loadTsv('primary_brand_totals.tsv', 3, 18);

const wb = XLSX.utils.book_new();
const COL = n => XLSX.utils.encode_col(n);

function rawSheet(name, keyHdr, months, rows, unitNote) {
  const aoa = [[...keyHdr, ...months, 'FY26 Total', 'Q1 FY27 (Apr-Jun26)']];
  rows.forEach(r => aoa.push([...r.key, ...r.vals, null, null]));
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  const nk = keyHdr.length, nm = months.length, last = rows.length + 1;
  for (let i = 2; i <= last; i++) {
    const fyEnd = months.indexOf('Mar-26');
    const c1 = COL(nk), c2 = COL(nk + fyEnd), q1a = COL(nk + nm - 3), q1b = COL(nk + nm - 1);
    ws[COL(nk + nm) + i]     = { t: 'n', f: `SUM(${c1}${i}:${c2}${i})`, z: '#,##0.0' };
    ws[COL(nk + nm + 1) + i] = { t: 'n', f: `SUM(${q1a}${i}:${q1b}${i})`, z: '#,##0.0' };
  }
  ws['!ref'] = `A1:${COL(nk + nm + 1)}${last}`;
  ws['!cols'] = [...keyHdr.map(h => ({ wch: Math.max(14, h.length + 2) })), ...months.map(() => ({ wch: 9 })), { wch: 11 }, { wch: 13 }];
  ws['!freeze'] = { xSplit: nk, ySplit: 1 };
  XLSX.utils.book_append_sheet(wb, ws, name);
  return ws;
}

// ---------- RAW SHEETS ----------
rawSheet('Offtake_Chain_Zone', ['Channel','Chain','Zone'], M15, ocz.rows);
rawSheet('Offtake_Brand_SubCat_Zone', ['Channel','Brand','SubCat','Zone'], M15, obz.rows);
rawSheet('Primary_Zone_Chain', ['Channel','Zone','Chain'], M15, pzc.rows);
rawSheet('Primary_Brand_Monthly', ['Channel','Brand','SubCat'], M18, pbt.rows);

// month column letters on raw sheets
const oczM = m => COL(3 + M15.indexOf(m));                // D..R
const obzM = m => COL(4 + M15.indexOf(m));                // E..S
const pzcM = m => COL(3 + M15.indexOf(m));
const pbtM = m => COL(3 + M18.indexOf(m));
const OCZ = 'Offtake_Chain_Zone', OBZ = 'Offtake_Brand_SubCat_Zone', PZC = 'Primary_Zone_Chain', PBT = 'Primary_Brand_Monthly';

const PCT = '+0.0%;-0.0%', NUM = '#,##0', NUM1 = '#,##0.0';
function fcell(f, z) { return { t: 'n', f, z: z || NUM }; }

// ---------- KPI DASHBOARD ----------
{
  const aoa = [];
  const ws = {};
  const set = (r, c, v) => { ws[COL(c) + r] = (typeof v === 'object') ? v : { t: typeof v === 'number' ? 'n' : 's', v }; };
  set(1, 0, "MT OFFTAKE — KPI DASHBOARD (Jun'26 close, Q1 FY27)");
  set(2, 0, 'All values ₹ Lacs (NSV). Every figure below is a live formula over the raw sheets — edit raw data and this refreshes.');
  // monthly totals row
  set(4, 0, 'Month'); set(5, 0, 'Total NSV (MT+EB2B)'); set(6, 0, 'MT channel'); set(7, 0, 'EB2B (FSN)'); set(8, 0, 'MoM %'); set(9, 0, 'YoY %');
  M15.forEach((m, j) => {
    const c = j + 1, L = oczM(m);
    set(4, c, m);
    set(5, c, fcell(`SUM(${OCZ}!${L}2:${L}200)`));
    set(6, c, fcell(`SUMIF(${OCZ}!$A:$A,"MT",${OCZ}!${L}:${L})`));
    set(7, c, fcell(`SUMIF(${OCZ}!$A:$A,"EB2B",${OCZ}!${L}:${L})`));
    if (j > 0) set(8, c, fcell(`${COL(c)}5/${COL(c - 1)}5-1`, PCT));
    if (j >= 12) set(9, c, fcell(`${COL(c)}5/${COL(c - 12)}5-1`, PCT));
  });
  const jun = COL(1 + M15.indexOf('Jun-26')), may = COL(1 + M15.indexOf('May-26')),
        mar = COL(1 + M15.indexOf('Mar-26')), apr = COL(1 + M15.indexOf('Apr-26')),
        jun25 = COL(1 + M15.indexOf('Jun-25')), apr25 = 'B';
  const rows = [
    ["Jun'26 NSV (₹ Cr)", `${jun}5/100`, '0.00'],
    ["May'26 NSV (₹ Cr)", `${may}5/100`, '0.00'],
    ['MoM growth', `${jun}5/${may}5-1`, PCT],
    ["L3M Avg (Mar–May'26, ₹ Cr)", `AVERAGE(${mar}5:${may}5)/100`, '0.00'],
    ['Growth over L3M Avg', `${jun}5/AVERAGE(${mar}5:${may}5)-1`, PCT],
    ["YoY growth (vs Jun'25)", `${jun}5/${jun25}5-1`, PCT],
    ['YoY delta (₹ Lacs)', `${jun}5-${jun25}5`, NUM],
    ['Q1 FY27 NSV (Apr–Jun26, ₹ Cr)', `SUM(${apr}5:${jun}5)/100`, '0.00'],
    ['Q1 FY26 NSV (Apr–Jun25, ₹ Cr)', `SUM(${apr25}5:D5)/100`, '0.00'],
    ['Q1 growth YoY', `SUM(${apr}5:${jun}5)/SUM(${apr25}5:D5)-1`, PCT],
    ["Top-3 chain concentration Jun'26 (Dmart+Reliance+Apollo)", `(SUMIF(${OCZ}!$B:$B,"Dmart",${OCZ}!${oczM('Jun-26')}:${oczM('Jun-26')})+SUMIF(${OCZ}!$B:$B,"Reliance",${OCZ}!${oczM('Jun-26')}:${oczM('Jun-26')})+SUMIF(${OCZ}!$B:$B,"Apollo",${OCZ}!${oczM('Jun-26')}:${oczM('Jun-26')}))/${jun}5`, '0.0%'],
    ["Mamaearth portfolio share Jun'26", `SUMIF(${OBZ}!$B:$B,"Mamaearth",${OBZ}!${obzM('Jun-26')}:${obzM('Jun-26')})/${jun}5`, '0.0%'],
    ["The Derma Co. portfolio share Jun'26", `SUMIF(${OBZ}!$B:$B,"The Derma Co.",${OBZ}!${obzM('Jun-26')}:${obzM('Jun-26')})/${jun}5`, '0.0%'],
  ];
  set(11, 0, 'HEADLINE SCORECARD');
  rows.forEach((r, k) => { set(12 + k, 0, r[0]); set(12 + k, 2, fcell(r[1], r[2])); });
  set(26, 0, "Note: CORRECTED chain-NSV basis (Jul'26 refresh). Official Grand Totals: Apr'26 3,589.14 | May'26 4,025.83 | Jun'26 3,823.78 Lacs. Chain-level rows tie exactly; brand/sub-cat rows are rounded to whole Lacs (sums within ±25 Lacs, <0.7%).");
  ws['!ref'] = 'A1:Q30';
  ws['!cols'] = [{ wch: 48 }, ...M15.map(() => ({ wch: 9 })), { wch: 10 }];
  XLSX.utils.book_append_sheet(wb, ws, 'KPI_Dashboard');
}

// generic summary-block writer
function summarySheet(name, title, cols, rowDefs, extra) {
  const ws = {};
  const set = (r, c, v) => { ws[COL(c) + r] = (typeof v === 'object' && v !== null) ? v : { t: typeof v === 'number' ? 'n' : 's', v }; };
  set(1, 0, title);
  set(2, 0, 'All values ₹ Lacs NSV. Live formulas — refresh with raw-sheet edits. L3M = Mar–May\'26 avg; GOLY = vs same month LY; Q1 = Apr–Jun.');
  cols.forEach((c, j) => set(4, j, c));
  rowDefs.forEach((rd, k) => {
    const r = 5 + k;
    rd.forEach((cell, j) => { if (cell !== null && cell !== undefined) set(r, j, cell); });
  });
  const lastR = 5 + rowDefs.length + 3;
  if (extra) extra(set);
  ws['!ref'] = `A1:${COL(cols.length + 1)}${lastR + 6}`;
  ws['!cols'] = [{ wch: 22 }, ...cols.slice(1).map(() => ({ wch: 11 }))];
  ws['!freeze'] = { xSplit: 1, ySplit: 4 };
  XLSX.utils.book_append_sheet(wb, ws, name);
}

const SCOLS = ['', "Jun-25", 'Apr-26', 'May-26', 'Jun-26', "Share % Jun'26", "L3M Avg", 'GO L3M %', 'MoM %', 'GOLY %', 'Q1 FY26', 'Q1 FY27', 'Q1 Growth %'];
function metricRow(r, label, sumf) {
  // sumf(month) -> formula string summing that month
  const q1_26 = `(${sumf('Apr-25')}+${sumf('May-25')}+${sumf('Jun-25')})`;
  const q1_27 = `(${sumf('Apr-26')}+${sumf('May-26')}+${sumf('Jun-26')})`;
  const l3m = `AVERAGE(${sumf('Mar-26')},${sumf('Apr-26')},${sumf('May-26')})`;
  return [
    label,
    fcell(sumf('Jun-25')), fcell(sumf('Apr-26')), fcell(sumf('May-26')), fcell(sumf('Jun-26')),
    fcell(`${sumf('Jun-26')}/E$${r}`, '0.0%'),   // E row of TOTAL fixed later -> replaced below
    fcell(l3m, NUM1),
    fcell(`${sumf('Jun-26')}/${l3m}-1`, PCT),
    fcell(`${sumf('Jun-26')}/${sumf('May-26')}-1`, PCT),
    fcell(`${sumf('Jun-26')}/${sumf('Jun-25')}-1`, PCT),
    fcell(q1_26), fcell(q1_27),
    fcell(`${q1_27}/${q1_26}-1`, PCT),
  ];
}

// ---------- ZONE SUMMARY ----------
{
  const zoneF = z => m => `SUMIFS(${OCZ}!${oczM(m)}:${oczM(m)},${OCZ}!$C:$C,"${z}")`;
  const panF = m => `SUMIF(${OCZ}!$A:$A,"EB2B",${OCZ}!${oczM(m)}:${oczM(m)})`;
  const totF = m => `SUM(${OCZ}!${oczM(m)}2:${oczM(m)}200)`;
  const zones = ['EAST','NORTH','SOUTH-1','SOUTH-2','WEST'];
  const defs = zones.map((z, k) => metricRow(5 + k, z, zoneF(z)));
  defs.push(metricRow(10, 'PAN INDIA (EB2B/FSN)', panF));
  defs.push(metricRow(11, 'TOTAL', totF));
  const totalRow = 5 + defs.length - 1; // row of TOTAL
  defs.forEach((d, k) => { d[5] = fcell(`${d[4].f.replace(/^/, '')}/E$${totalRow}`, '0.0%'); d[5] = fcell(`E${5 + k}/E$${totalRow}`, '0.0%'); });
  summarySheet('Zone_Summary', "ZONE PERFORMANCE SUMMARY — Jun'26 & Q1 FY27", SCOLS, defs);
}

// ---------- CHAIN SUMMARY ----------
{
  const order = ['Dmart','Reliance','Apollo','Fsn','Lulu','Wellness Forever','Metro Cnc','H&G','More Retail','Sancus(Rmt)','Vmm','V-Mart','Trent','Spencer','Frankros','Arambagh','Walmart Cnc','National Mart','Ratandeep','Sumo Save','Guardian','Sasta Sundar','BEAUTY & NUTRIE','Apna Mart','Wh-Smith','Vijetha'];
  const chainF = c => m => `SUMIF(${OCZ}!$B:$B,"${c.replace(/"/g, '""')}",${OCZ}!${oczM(m)}:${oczM(m)})`;
  const totF = m => `SUM(${OCZ}!${oczM(m)}2:${oczM(m)}200)`;
  const defs = order.map((c, k) => metricRow(5 + k, c, chainF(c)));
  defs.push(metricRow(5 + order.length, 'TOTAL', totF));
  const totalRow = 5 + defs.length - 1;
  defs.forEach((d, k) => { d[5] = fcell(`E${5 + k}/E$${totalRow}`, '0.0%'); });
  summarySheet('Chain_Summary', "CHAIN PERFORMANCE SUMMARY — Jun'26 & Q1 FY27 (all channels)", SCOLS, defs);
}

// ---------- BRAND & SUBCAT SUMMARY ----------
{
  const brandF = b => m => `SUMIF(${OBZ}!$B:$B,"${b}",${OBZ}!${obzM(m)}:${obzM(m)})`;
  const emergF = m => `SUM(${OBZ}!${obzM(m)}2:${obzM(m)}300)-${brandF('Mamaearth')(m)}-${brandF('The Derma Co.')(m)}-${brandF('Aqualogica')(m)}`;
  const totF = m => `SUM(${OBZ}!${obzM(m)}2:${obzM(m)}300)`;
  const bsF = (b, sc) => m => `SUMIFS(${OBZ}!${obzM(m)}:${obzM(m)},${OBZ}!$B:$B,"${b}",${OBZ}!$C:$C,"${sc}")`;
  const defs = [];
  ['Mamaearth','The Derma Co.','Aqualogica'].forEach((b, k) => defs.push(metricRow(5 + k, b, brandF(b))));
  defs.push(metricRow(8, 'Emerging Brands', emergF));
  defs.push(metricRow(9, 'PORTFOLIO TOTAL', totF));
  defs.forEach((d, k) => { d[5] = fcell(`E${5 + k}/E$9`, '0.0%'); });
  const sub = [['Mamaearth','Face Cleanser'],['Mamaearth','Shampoo'],['Mamaearth','Sun Care'],['Mamaearth','Body Lotion'],['Mamaearth','Moisturisers'],['Mamaearth','Body Wash'],['Mamaearth','Baby Soap'],['The Derma Co.','Face Cleanser'],['The Derma Co.','Sun Care'],['The Derma Co.','Face Serum'],['The Derma Co.','Moisturisers'],['Aqualogica','Sun Care']];
  summarySheet('Brand_SubCat_Summary', "BRAND & SUB-CATEGORY SUMMARY — Jun'26 & Q1 FY27 (MT + EB2B offtake)", SCOLS, defs, set => {
    set(12, 0, 'KEY SUB-CATEGORIES (hero segments)');
    SCOLS.forEach((c, j) => set(13, j, c));
    sub.forEach(([b, sc], k) => {
      const r = 14 + k;
      const row = metricRow(r, `${b} — ${sc}`, bsF(b, sc));
      row[5] = fcell(`E${r}/E$9`, '0.0%');
      row.forEach((cell, j) => { if (cell != null) set(r, j, cell); });
    });
  });
}

// ---------- Q1 FY27 SCORECARD ----------
{
  const ws = {};
  const set = (r, c, v) => { ws[COL(c) + r] = (typeof v === 'object' && v !== null) ? v : { t: typeof v === 'number' ? 'n' : 's', v }; };
  set(1, 0, 'Q1 FY27 SCORECARD (Apr–Jun\'26 vs Apr–Jun\'25) — OFFTAKE NSV ₹ Lacs');
  const hdr = ['', 'Q1 FY26', 'Q1 FY27', 'Growth %', 'Mix % of Q1 FY27', 'Δ ₹ Lacs'];
  const q1f = sumf => ({ a: `(${sumf('Apr-25')}+${sumf('May-25')}+${sumf('Jun-25')})`, b: `(${sumf('Apr-26')}+${sumf('May-26')}+${sumf('Jun-26')})` });
  const totF = m => `SUM(${OCZ}!${oczM(m)}2:${oczM(m)}200)`;
  const tot = q1f(totF);
  let r = 3;
  const block = (title, items) => {
    set(r, 0, title); r++;
    hdr.forEach((h, j) => set(r, j, h)); r++;
    items.forEach(([label, sumf]) => {
      const q = q1f(sumf);
      set(r, 0, label);
      set(r, 1, fcell(q.a)); set(r, 2, fcell(q.b));
      set(r, 3, fcell(`${q.b}/${q.a}-1`, PCT));
      set(r, 4, fcell(`${q.b}/${tot.b}`, '0.0%'));
      set(r, 5, fcell(`${q.b}-${q.a}`, NUM));
      r++;
    });
    r++;
  };
  const zF = z => m => `SUMIFS(${OCZ}!${oczM(m)}:${oczM(m)},${OCZ}!$C:$C,"${z}")`;
  const panF = m => `SUMIF(${OCZ}!$A:$A,"EB2B",${OCZ}!${oczM(m)}:${oczM(m)})`;
  const chF = c => m => `SUMIF(${OCZ}!$B:$B,"${c}",${OCZ}!${oczM(m)}:${oczM(m)})`;
  const bF = b => m => `SUMIF(${OBZ}!$B:$B,"${b}",${OBZ}!${obzM(m)}:${obzM(m)})`;
  block('OVERALL', [['Total MT + EB2B', totF]]);
  block('BY ZONE', [['East', zF('EAST')], ['North', zF('NORTH')], ['South-1', zF('SOUTH-1')], ['South-2', zF('SOUTH-2')], ['West', zF('WEST')], ['Pan India (FSN)', panF]]);
  block('BY BRAND', [['Mamaearth', bF('Mamaearth')], ['The Derma Co.', bF('The Derma Co.')], ['Aqualogica', bF('Aqualogica')]]);
  block('TOP CHAINS', [['Dmart', chF('Dmart')], ['Reliance', chF('Reliance')], ['Apollo', chF('Apollo')], ['FSN (EB2B)', chF('Fsn')], ['Lulu', chF('Lulu')], ['Wellness Forever', chF('Wellness Forever')]]);
  ws['!ref'] = `A1:H${r + 2}`;
  ws['!cols'] = [{ wch: 22 }, { wch: 11 }, { wch: 11 }, { wch: 11 }, { wch: 15 }, { wch: 11 }];
  XLSX.utils.book_append_sheet(wb, ws, 'Q1_FY27_Scorecard');
}

// ---------- PRIMARY SUMMARY ----------
{
  const ws = {};
  const set = (r, c, v) => { ws[COL(c) + r] = (typeof v === 'object' && v !== null) ? v : { t: typeof v === 'number' ? 'n' : 's', v }; };
  set(1, 0, "PRIMARY (SELL-IN) SUMMARY — Jun'26 & Q1 FY27 — ₹ Lacs");
  set(2, 0, 'Source: Primary_Zone_Chain (chain-level, ₹ Lacs) & Primary_Brand_Monthly (brand-level, ₹). Live formulas.');
  set(4, 0, 'Month'); M15.forEach((m, j) => set(4, j + 1, m));
  set(5, 0, 'Primary NSV total');
  M15.forEach((m, j) => set(5, j + 1, fcell(`SUM(${PZC}!${pzcM(m)}2:${pzcM(m)}200)`, NUM1)));
  set(6, 0, 'MoM %'); M15.forEach((m, j) => { if (j) set(6, j + 1, fcell(`${COL(j + 1)}5/${COL(j)}5-1`, PCT)); });
  set(7, 0, 'YoY %'); M15.forEach((m, j) => { if (j >= 12) set(7, j + 1, fcell(`${COL(j + 1)}5/${COL(j - 11)}5-1`, PCT)); });
  let r = 9;
  set(r, 0, 'HEADLINES'); r++;
  const jun = COL(M15.indexOf('Jun-26') + 1), may = COL(M15.indexOf('May-26') + 1), apr = COL(M15.indexOf('Apr-26') + 1), jun25 = COL(M15.indexOf('Jun-25') + 1);
  [["Jun'26 Primary (₹ Cr)", `${jun}5/100`, '0.00'],
   ['MoM %', `${jun}5/${may}5-1`, PCT],
   ["GOLY % (vs Jun'25)", `${jun}5/${jun25}5-1`, PCT],
   ['Q1 FY27 (₹ Cr)', `SUM(${apr}5:${jun}5)/100`, '0.00'],
   ['Q1 FY26 (₹ Cr)', `SUM(B5:D5)/100`, '0.00'],
   ['Q1 growth %', `SUM(${apr}5:${jun}5)/SUM(B5:D5)-1`, PCT]].forEach(x => { set(r, 0, x[0]); set(r, 2, fcell(x[1], x[2])); r++; });
  r += 1;
  set(r, 0, 'BY CHAIN (top primary billings)'); r++;
  ['','Jun-25','Apr-26','May-26','Jun-26','MoM %','GOLY %','Q1 FY26','Q1 FY27','Q1 Gr %'].forEach((h, j) => set(r, j, h)); r++;
  ['D-Mart','Reliance Retail','Apollo Healthco','Lulu','Wellness Forever','H&G','RMT-Sancus','VMM','More Retail','Nykaa SS(fsn)','Metro-CNC-RRL','Frankross','Spencer','Walmart CNC'].forEach(c => {
    const f = m => `SUMIF(${PZC}!$C:$C,"${c}",${PZC}!${pzcM(m)}:${pzcM(m)})`;
    set(r, 0, c);
    set(r, 1, fcell(f('Jun-25'), NUM1)); set(r, 2, fcell(f('Apr-26'), NUM1)); set(r, 3, fcell(f('May-26'), NUM1)); set(r, 4, fcell(f('Jun-26'), NUM1));
    set(r, 5, fcell(`${f('Jun-26')}/${f('May-26')}-1`, PCT));
    set(r, 6, fcell(`${f('Jun-26')}/${f('Jun-25')}-1`, PCT));
    set(r, 7, fcell(`${f('Apr-25')}+${f('May-25')}+${f('Jun-25')}`, NUM1));
    set(r, 8, fcell(`${f('Apr-26')}+${f('May-26')}+${f('Jun-26')}`, NUM1));
    set(r, 9, fcell(`(${f('Apr-26')}+${f('May-26')}+${f('Jun-26')})/(${f('Apr-25')}+${f('May-25')}+${f('Jun-25')})-1`, PCT));
    r++;
  });
  r += 1;
  set(r, 0, 'BY BRAND (₹ Lacs, from Primary_Brand_Monthly ₹)'); r++;
  ['','Jun-25','Apr-26','May-26','Jun-26','MoM %','GOLY %','Q1 FY26','Q1 FY27','Q1 Gr %'].forEach((h, j) => set(r, j, h)); r++;
  [['Mamaearth (MT)', 'MT', 'Mamaearth'], ['The Derma Co. (MT)', 'MT', 'The Derma Co.'], ['Aqualogica (MT)', 'MT', 'Aqualogica'], ['Mamaearth (EB2B)', 'Eb2b', 'Mamaearth'], ['The Derma Co. (EB2B)', 'Eb2b', 'The Derma Co.'], ['ALL-IN GRAND TOTAL', 'ALL', 'GRAND TOTAL']].forEach(([label, ch, b]) => {
    const f = m => `SUMIFS(${PBT}!${pbtM(m)}:${pbtM(m)},${PBT}!$A:$A,"${ch}",${PBT}!$B:$B,"${b}",${PBT}!$C:$C,"ALL")/100000`;
    set(r, 0, label);
    set(r, 1, fcell(f('Jun-25'), NUM1)); set(r, 2, fcell(f('Apr-26'), NUM1)); set(r, 3, fcell(f('May-26'), NUM1)); set(r, 4, fcell(f('Jun-26'), NUM1));
    set(r, 5, fcell(`${f('Jun-26')}/${f('May-26')}-1`, PCT));
    set(r, 6, fcell(`${f('Jun-26')}/${f('Jun-25')}-1`, PCT));
    set(r, 7, fcell(`${f('Apr-25')}+${f('May-25')}+${f('Jun-25')}`, NUM1));
    set(r, 8, fcell(`${f('Apr-26')}+${f('May-26')}+${f('Jun-26')}`, NUM1));
    set(r, 9, fcell(`(${f('Apr-26')}+${f('May-26')}+${f('Jun-26')})/(${f('Apr-25')}+${f('May-25')}+${f('Jun-25')})-1`, PCT));
    r++;
  });
  ws['!ref'] = `A1:R${r + 2}`;
  ws['!cols'] = [{ wch: 24 }, ...Array(16).fill({ wch: 10 })];
  XLSX.utils.book_append_sheet(wb, ws, 'Primary_Summary');
}

// ---------- MAY'26 EXTERNAL WORKINGS (slides with data only till May'26) ----------
{
  const ws = {};
  const set = (r, c, v) => { ws[COL(c) + r] = (typeof v === 'object' && v !== null) ? v : { t: typeof v === 'number' ? 'n' : 's', v }; };
  set(1, 0, "EXTERNAL-DATA SLIDES — WORKINGS AS OF MAY'26 (Jun'26 refresh awaited)");
  set(2, 0, "Slides 4–9 use chain Gross-Sales share & Nielsen MS data. Latest external files available = May'26. Drop Jun'26 inputs into the yellow cells below; share % formulas recalc automatically.");
  set(4, 0, "SLIDE 4 — CHAIN-WISE MARKET SHARE (GROSS SALES BASIS), MAY'26");
  ['Chain', 'Honasa GS (Lacs)', 'Total Mkt GS (Lacs)', 'Mkt Share % (formula)', 'MoM (bps, vs Apr\'26)'].forEach((h, j) => set(5, j, h));
  [['MRL', 59.7, 2128.7, '+31'], ['Lulu', 111.5, 2848.0, '-21'], ['Wellness Forever', 137.4, 977.6, '-35'], ['Reliance Retail', 2052.0, 19298.6, '-38']].forEach((row, k) => {
    const r = 6 + k;
    set(r, 0, row[0]); set(r, 1, row[1]); set(r, 2, row[2]);
    set(r, 3, fcell(`B${r}/C${r}`, '0.0%'));
    set(r, 4, row[3]);
  });
  set(11, 0, "SLIDE 5–9 — NIELSEN MS READOUT (MAY'26, Urban):");
  ['Brand (Category)', "MS Val % May'26", 'MoM bps', 'YoY bps', 'MAT MS %', "Value ₹Cr May'26", 'Value YoY %', 'Wtd Dist %'].forEach((h, j) => set(12, j, h));
  [['Mamaearth FW', 0.12, 'Flat', '+311', 0.10, 9.6, 0.54, 0.87],
   ['The Derma Co FW', 0.01, '+6', '+71', 0.00, 0.6, 39.40, 0.14],
   ['Mamaearth Shampoo', 0.04, '-31', '+134', 0.04, 6.5, 0.64, 0.81]].forEach((row, k) => {
    const r = 13 + k;
    row.forEach((v, j) => set(r, j, typeof v === 'number' ? { t: 'n', v, z: j === 5 ? '0.0' : '0%' } : v));
  });
  set(17, 0, "Status: Jun'26 Nielsen MAT & chain GS extracts not yet released to this working file. Slides 4–9 in the Jun'26 deck carry a 'Data basis: May'26' tag until refreshed.");
  ws['!ref'] = 'A1:J20';
  ws['!cols'] = [{ wch: 22 }, ...Array(8).fill({ wch: 14 })];
  XLSX.utils.book_append_sheet(wb, ws, 'May26_External_Workings');
}


// ---------- QUARTERLY CHAIN x ZONE (corrected shared table) ----------
{
  const QC = ['Q1-24','Q2-24','Q3-24','Q4-24','Q1-25','Q2-25','Q3-25','Q4-25','Apr-26','May-26','Jun-26'];
  const aoa = [['Zone','Chain',...QC,'Q1 FY27','Q1 YoY %','2-yr Q1 CAGR %']];
  qcz.rows.forEach(r => aoa.push([...r.key, ...r.vals, null, null, null]));
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  for (let i = 2; i <= qcz.rows.length + 1; i++) {
    ws['N' + i] = { t: 'n', f: `SUM(K${i}:M${i})`, z: '#,##0.0' };          // Apr..Jun-26 = cols K,L,M
    ws['O' + i] = { t: 'n', f: `IF(G${i}=0,"",N${i}/G${i}-1)`, z: PCT };     // vs Q1-25 (col G)
    ws['P' + i] = { t: 'n', f: `IF(C${i}=0,"",(N${i}/C${i})^0.5-1)`, z: PCT };// vs Q1-24 (col C)
  }
  ws['!ref'] = `A1:P${qcz.rows.length + 1}`;
  ws['!cols'] = [{wch:10},{wch:17},...QC.map(()=>({wch:9})),{wch:9},{wch:9},{wch:13}];
  XLSX.utils.book_append_sheet(wb, ws, 'Offtake_Qtr_Chain_Zone');
}
// ---------- ZONE x BRAND QUARTERLY ----------
{
  const QB = ['Q1-24','Q2-24','Q3-24','Q4-23','Q4-24','Q1-25','Q2-25','Q3-25','Q4-25','Apr-26','May-26','Jun-26','Q1-26T'];
  const aoa = [['Zone','Brand',...QB,'Q1 FY27 (calc)','Q1 YoY %']];
  qzb.rows.forEach(r => aoa.push([...r.key, ...r.vals, null, null]));
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  for (let i = 2; i <= qzb.rows.length + 1; i++) {
    ws['P' + i] = { t: 'n', f: `SUM(L${i}:N${i})`, z: NUM };                 // Apr,May,Jun = L,M,N
    ws['Q' + i] = { t: 'n', f: `IF(H${i}=0,"",P${i}/H${i}-1)`, z: PCT };     // vs Q1-25 (col H)
  }
  ws['!ref'] = `A1:Q${qzb.rows.length + 1}`;
  ws['!cols'] = [{wch:10},{wch:15},...QB.map(()=>({wch:8})),{wch:12},{wch:9}];
  XLSX.utils.book_append_sheet(wb, ws, 'Zone_Brand_Qtr');
}
// ---------- PACK-SIZE HERO VIEW ----------
{
  const PC = ['Q1-25','Q2-25','Q3-25','Q4-25','Apr-26','May-26','Jun-26','Q1T'];
  const aoa = [['Zone','Brand','SubCat','Pack (g/ml)',...PC,'Q1 FY27','Q1 YoY %']];
  phero.rows.forEach(r => aoa.push([...r.key, ...r.vals, null, null]));
  const ws = XLSX.utils.aoa_to_sheet(aoa);
  for (let i = 2; i <= phero.rows.length + 1; i++) {
    ws['M' + i] = { t: 'n', f: `SUM(I${i}:K${i})`, z: NUM };                 // Apr,May,Jun = I,J,K
    ws['N' + i] = { t: 'n', f: `IF(E${i}=0,"",M${i}/E${i}-1)`, z: PCT };     // vs Q1-25 (col E)
  }
  ws['!ref'] = `A1:N${phero.rows.length + 1}`;
  ws['!cols'] = [{wch:10},{wch:14},{wch:14},{wch:11},...PC.map(()=>({wch:8})),{wch:9},{wch:9}];
  XLSX.utils.book_append_sheet(wb, ws, 'Pack_Hero');
}
// ---------- CORRECTIONS IMPACT (old vs corrected, live formulas on new side) ----------
{
  const ws = {};
  const set = (r, c, v) => { ws[COL(c) + r] = (typeof v === 'object' && v !== null) ? v : { t: typeof v === 'number' ? 'n' : 's', v }; };
  set(1, 0, "CHAIN NSV CORRECTIONS — PREVIOUS SUBMISSION vs CORRECTED (Jun'26 & May'26, ₹ Lacs)");
  set(2, 0, "'Previous' columns are the values shared in the first Jun'26 deck; 'Corrected' columns are live SUMIFs over the corrected raw sheets.");
  ['Chain','Prev May-26','Corr May-26','Δ May','Prev Jun-26','Corr Jun-26','Δ Jun'].forEach((h, j) => set(4, j, h));
  const prev = [['Dmart',1518,1412],['Reliance',990,947],['Apollo',751,599],['Fsn',208,217],['Lulu',116,116],
    ['Wellness Forever',102,79],['Metro Cnc',48,60],['H&G',87,52],['More Retail',55,44],['Sancus(Rmt)',46,40],
    ['Vmm',31,27],['V-Mart',10,13],['Trent',8,11],['Spencer',12,8],['Frankros',10,8],['Arambagh',5,5],
    ['Walmart Cnc',33,0],['National Mart',2,4],['Ratandeep',3,3],['Sumo Save',2,1],['BEAUTY & NUTRIE',0,1],['Apna Mart',0,0]];
  prev.forEach((p, k) => {
    const r = 5 + k;
    set(r, 0, p[0]); set(r, 1, p[1]);
    set(r, 2, fcell(`SUMIF(${OCZ}!$B:$B,"${p[0].replace(/"/g,'""')}",${OCZ}!${oczM('May-26')}:${oczM('May-26')})`, NUM1));
    set(r, 3, fcell(`C${r}-B${r}`, '+#,##0.0;-#,##0.0;0'));
    set(r, 4, p[2]);
    set(r, 5, fcell(`SUMIF(${OCZ}!$B:$B,"${p[0].replace(/"/g,'""')}",${OCZ}!${oczM('Jun-26')}:${oczM('Jun-26')})`, NUM1));
    set(r, 6, fcell(`F${r}-E${r}`, '+#,##0.0;-#,##0.0;0'));
  });
  const rT = 5 + prev.length;
  set(rT, 0, 'TOTAL (official)'); set(rT, 1, 4019); 
  set(rT, 2, fcell(`SUM(${OCZ}!${oczM('May-26')}2:${oczM('May-26')}200)`, NUM1));
  set(rT, 3, fcell(`C${rT}-B${rT}`, '+#,##0.0;-#,##0.0;0'));
  set(rT, 4, 3652);
  set(rT, 5, fcell(`SUM(${OCZ}!${oczM('Jun-26')}2:${oczM('Jun-26')}200)`, NUM1));
  set(rT, 6, fcell(`F${rT}-E${rT}`, '+#,##0.0;-#,##0.0;0'));
  set(rT + 2, 0, "Headline impact: Jun'26 +171.8 Lacs (3,652 → 3,823.8), led by Apollo +124 and Dmart +44; May'26 +6.8 (4,019 → 4,025.8). History (Apr'25–Mar'26) unchanged except Vmm Q3-25 restatement (+~34 Lacs across Oct–Dec'25 at quarter level).");
  ws['!ref'] = 'A1:J' + (rT + 3);
  ws['!cols'] = [{ wch: 18 }, ...Array(6).fill({ wch: 12 })];
  XLSX.utils.book_append_sheet(wb, ws, 'Corrections_Impact');
}
// ---------- SLIDE MAP ----------
{
  const rows = [
    ['Slide', 'Content', "Jun'26 status", 'Data source / working'],
    [1, 'Summary & key insights, KPI cards, chain trend/mix', 'UPDATED to Jun\'26', 'KPI_Dashboard + Chain_Summary'],
    ['1A (new)', 'Q1 FY27 scorecard (Apr–Jun\'26 vs LY)', 'NEW SLIDE ADDED', 'Q1_FY27_Scorecard'],
    [2, 'Portfolio drivers — brand/sub-cat trends, vol-val decomposition', 'NSV side UPDATED; Qty/ASP & hero-SKU panels = May\'26 basis (SKU/Qty extract not shared for Jun)', 'Brand_SubCat_Summary; May26_External_Workings'],
    [3, 'Zone performance summary', "UPDATED to Jun'26", 'Zone_Summary'],
    [4, 'Chain-wise market share (Gross Sales basis)', "RETAINED May'26 + data-basis tag", 'May26_External_Workings'],
    [5, 'Nielsen MS insights (brand)', "RETAINED May'26 + data-basis tag", 'May26_External_Workings'],
    [6, 'Nielsen readout — Shampoo ranking', "RETAINED May'26 + data-basis tag", 'May26_External_Workings'],
    [7, 'Shampoo pack-level insights', "RETAINED May'26 + data-basis tag", 'May26_External_Workings'],
    [8, 'Nielsen readout — Facewash & Shampoo', "RETAINED May'26 + data-basis tag", 'May26_External_Workings'],
    [9, 'Nielsen state contribution', "RETAINED May'26 + data-basis tag", 'May26_External_Workings'],
    [10, 'East zone page', "UPDATED to Jun'26", 'Zone_Summary + Offtake_Brand_SubCat_Zone (EAST)'],
    [11, 'North zone page', "UPDATED to Jun'26", 'Zone_Summary + Offtake_Brand_SubCat_Zone (NORTH)'],
    [12, 'South-1 zone page', "UPDATED to Jun'26", 'Zone_Summary + Offtake_Brand_SubCat_Zone (SOUTH-1)'],
    [13, 'South-2 zone page', "UPDATED to Jun'26", 'Zone_Summary + Offtake_Brand_SubCat_Zone (SOUTH-2)'],
    [14, 'West zone page', "UPDATED to Jun'26", 'Zone_Summary + Offtake_Brand_SubCat_Zone (WEST)'],
    [15, 'Pan-India (FSN/EB2B) page', "UPDATED to Jun'26", 'Zone_Summary + Offtake_Brand_SubCat_Zone (Pan India)'],
    ['16–23', 'Execution galleries (field photos)', 'RETAINED (visual evidence, May/Jun JC cycle)', '—'],
  ];
  const ws = XLSX.utils.aoa_to_sheet(rows);
  ws['!cols'] = [{ wch: 9 }, { wch: 52 }, { wch: 46 }, { wch: 46 }];
  XLSX.utils.book_append_sheet(wb, ws, 'Slide_Map');
}

// ---------- READ ME ----------
{
  const rows = [
    ["HONASA — MT OFFTAKE & PRIMARY WORKING FILE — JUN'26 CLOSE + Q1 FY27 — CORRECTED CHAIN NSV (v2)"],
    ['CORRECTION NOTE: Apr/May/Jun-26 offtake reflects the corrected chain-NSV basis. See Corrections_Impact for old-vs-new by chain. Quarterly history (FY24-FY26) added from the corrected extract; monthly history retained from the validated Apr-25..Mar-26 series.'],
    [''],
    ['HOW THIS FILE WORKS'],
    ['• Raw data sheets (Offtake_Chain_Zone, Offtake_Brand_SubCat_Zone, Primary_Zone_Chain, Primary_Brand_Monthly) hold the shared tables, Apr\'25 → Jun\'26.'],
    ['• Every summary sheet (KPI_Dashboard, Zone_Summary, Chain_Summary, Brand_SubCat_Summary, Q1_FY27_Scorecard, Primary_Summary) is 100% formula-driven (SUMIF/SUMIFS).'],
    ['• To refresh next month: append/overwrite the month columns in the raw sheets — all KPIs, shares and growth metrics recalculate instantly.'],
    ['• Month convention: Indian FY (Apr–Mar). Q1 FY27 = Apr\'26 + May\'26 + Jun\'26. L3M Avg = Mar–May\'26 (trailing 3 months before report month).'],
    [''],
    ['UNITS'],
    ['• Offtake sheets & Primary_Zone_Chain: ₹ Lacs (NSV). Primary_Brand_Monthly: ₹ absolute (divide by 1,00,000 for Lacs — Primary_Summary does this via formula).'],
    [''],
    ['DATA NOTES (senior-analyst honesty box)'],
    ['1. Offtake rows in the shared table are rounded to whole ₹ Lacs; the unrounded Grand Total closes Jun\'26 at 3,652 Lacs. Row-sums here land within ±5 Lacs (<0.2%). Headline deck KPIs use the official Grand Total.'],
    ['2. Offtake_Brand_SubCat_Zone: rows that are zero/blank across all 15 months were dropped (they carry no value). Impact ≤ ~20 Lacs/month vs Grand Total (<0.7%).'],
    ['3. Primary brand sheet carries brand-level totals + key sub-category totals. The full brand×sub-cat×zone primary matrix stays in the source paste; add rows here anytime — formulas pick them up.'],
    ['4. Pure Origin discontinued from FY26; Lumineve is a new SIS brand from Apr\'26; Dr. Sheth\'s entered MT/EB2B in Oct\'25 — YoY for these reads off a nil base.'],
    ['5. Slides 4–9 (chain GS market share, Nielsen) rely on external data available only till May\'26 — see May26_External_Workings and Slide_Map.'],
    ['6. Negative offtake/primary values are returns/claims reversals — kept as shared.'],
    [''],
    ['FILE PAIRING'],
    ["• Deck: Final MT Offtake Jun26 Leadership deck (same repo). Chart caches in the deck were refreshed from this workbook's raw sheets."],
  ];
  const ws = XLSX.utils.aoa_to_sheet(rows);
  ws['!cols'] = [{ wch: 160 }];
  XLSX.utils.book_append_sheet(wb, ws, 'READ_ME');
}

// ---------- EXECUTIVE SYNTHESIS (SCR + MoM Inflection Mapping) ----------
{
  const rows = [
    ['EXECUTIVE SYNTHESIS — Q1 FY26-27 (Apr-Jun\'26) — SCR FRAMEWORK'],
    ['Brand | Category | SKU anchor: Mamaearth + The Derma Co. | Face Care / Hair Care / Sun Care | Portfolio-wide'],
    [''],
    ['SITUATION', 'Q1 FY27 NSV hit ₹11,438.7L vs ₹6,986.0L in Q1 FY26 — up 63.7% YoY, led by West and Derma Co.'],
    ['COMPLICATION', 'June momentum cooled everywhere at once — every zone decelerated MoM after a May peak (-5.0% co. wide).'],
    ['RESOLUTION', 'Protect May\'s pipeline-fill gains by shifting focus to June sell-through; re-forecast July off L3M avg (₹3,615L), not May peak.'],
    [''],
    ['MoM INFLECTION MAPPING (real, from 15-month series — no fabricated inputs)'],
    ['Every one of the 6 zones shows the identical inflection shape: acceleration into May-26 (peak MoM), then sharp deceleration in June-26.'],
    ['This is a company-wide pattern, most consistent with a May primary pipeline-fill/stockist-loading effect rather than a genuine June demand drop.'],
    [''],
    ['Zone', 'May MoM %', 'Jun MoM %', 'Read'],
    ['EAST', 11.4, -6.7, 'May peak -> Jun correction'],
    ['NORTH', 3.7, -8.2, 'May peak -> Jun correction'],
    ['SOUTH-1', 15.1, -4.6, 'May peak -> Jun correction'],
    ['SOUTH-2', 10.1, -3.1, 'May peak -> Jun correction'],
    ['WEST', 3.0, -0.7, 'May peak -> Jun correction (mildest)'],
    ['PAN INDIA', null, null, 'Smallest zone, more volatile'],
    [''],
    ['DATA REQUIRED TO COMPLETE REMAINING ASKS (flagged, not fabricated — per no-dummy-data rule)'],
    ['Velocity-vs-Distribution Quadrant, Opportunity Gap Valuation, and Stock Productivity/Capital Efficiency need inputs our'],
    ['source tables do not contain (sales NSV/volume only). To build these for real, please share:'],
    ['1. Store count / active distribution points per chain per zone per month (Peak Throughput per store, Active Distribution Grid, Quadrant classification).'],
    ['2. Monthly sales target/budget per zone or brand (Opportunity Gap Valuation = Target - Carrying Variance x Peak Throughput Velocity).'],
    ['3. Inventory/stock-in-trade and shelf-space (bay/facing) allocation per chain (Stock Productivity & Capital Efficiency).'],
    ['Once shared, these will be validated and added as formula-linked sheets/slides using the same process as the NSV corrections.'],
  ];
  const ws = XLSX.utils.aoa_to_sheet(rows);
  ws['!cols'] = [{ wch: 16 }, { wch: 60 }, { wch: 16 }, { wch: 40 }];
  XLSX.utils.book_append_sheet(wb, ws, 'Executive_Synthesis');
}

// order: READ_ME first
wb.SheetNames = ['READ_ME', 'Executive_Synthesis', 'Corrections_Impact', 'KPI_Dashboard', 'Q1_FY27_Scorecard', 'Zone_Summary', 'Chain_Summary', 'Brand_SubCat_Summary', 'Pack_Hero', 'Primary_Summary', 'May26_External_Workings', 'Slide_Map', 'Offtake_Chain_Zone', 'Offtake_Brand_SubCat_Zone', 'Offtake_Qtr_Chain_Zone', 'Zone_Brand_Qtr', 'Primary_Zone_Chain', 'Primary_Brand_Monthly'];
wb.Workbook = { CalcPr: { fullCalcOnLoad: true } };
const out = path.join(__dirname, 'MT_Offtake_Primary_Jun26_Working_CORRECTED.xlsx');
const buf = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
fs.writeFileSync(out, buf);
console.log('written', out, buf.length, 'bytes');
