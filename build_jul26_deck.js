'use strict';
const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33" × 7.5"

const C = {
  headerBg: '14401A', accent: '43A047', mamGreen: '81C784',
  kpiTile: 'EAF3EA', kpiPos: '2E7D32', kpiNeg: 'C62828',
  kpiNeutral: '1B2A1B', kpiLabel: '5C6B5C', sectionHdr: '2E7D32',
  white: 'FFFFFF', bodyText: '1A2E1A', tdc: '1565C0',
};

function addHeader(slide, title) {
  slide.addShape(pres.ShapeType.rect, { x:0,y:0,w:13.33,h:0.92, fill:{color:C.headerBg}, line:{color:C.headerBg} });
  slide.addShape(pres.ShapeType.rect, { x:0,y:0.92,w:13.33,h:0.06, fill:{color:C.accent}, line:{color:C.accent} });
  slide.addText('MAMAEARTH', { x:0.30,y:0.08,w:2.5,h:0.28, fontSize:10,bold:true,color:C.mamGreen,fontFace:'Calibri' });
  slide.addText("MODERN TRADE  |  JULY '26", { x:0.30,y:0.36,w:5,h:0.20, fontSize:8,color:'A5D6A7',fontFace:'Calibri' });
  slide.addText(title, { x:0.30,y:0.56,w:12.40,h:0.32, fontSize:15,bold:true,color:C.white,fontFace:'Calibri' });
}

function sectionHdr(slide, x, y, w, text) {
  slide.addShape(pres.ShapeType.rect, { x,y,w,h:0.28, fill:{color:C.sectionHdr}, line:{color:C.sectionHdr} });
  slide.addText(text, { x:x+0.08,y,w:w-0.10,h:0.28, fontSize:8.5,bold:true,color:C.white,fontFace:'Calibri',valign:'middle',margin:0 });
}

function takeaway(slide, text) {
  slide.addShape(pres.ShapeType.rect, { x:0.30,y:6.30,w:12.73,h:0.88, fill:{color:'F0F7F0'}, line:{color:C.accent,width:1} });
  slide.addShape(pres.ShapeType.rect, { x:0.30,y:6.30,w:0.18,h:0.88, fill:{color:C.accent}, line:{color:C.accent} });
  slide.addText('KEY TAKEAWAY', { x:0.55,y:6.32,w:1.80,h:0.20, fontSize:7,bold:true,color:C.sectionHdr,fontFace:'Calibri' });
  slide.addText(text, { x:0.55,y:6.52,w:12.40,h:0.62, fontSize:9,color:C.bodyText,fontFace:'Calibri',valign:'top' });
}

// ── SLIDE 1: COVER ────────────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  s.addShape(pres.ShapeType.rect, { x:0,y:0,w:13.33,h:7.50, fill:{color:C.headerBg}, line:{color:C.headerBg} });
  s.addShape(pres.ShapeType.rect, { x:0,y:5.50,w:13.33,h:2.0, fill:{color:'0D2E12'}, line:{color:'0D2E12'} });
  s.addShape(pres.ShapeType.rect, { x:0,y:5.46,w:13.33,h:0.07, fill:{color:C.accent}, line:{color:C.accent} });
  s.addShape(pres.ShapeType.rect, { x:0.60,y:4.58,w:5.0,h:0.06, fill:{color:C.accent}, line:{color:C.accent} });
  s.addText('MAMAEARTH', { x:0.60,y:1.10,w:9,h:0.60, fontSize:38,bold:true,color:C.mamGreen,fontFace:'Calibri' });
  s.addText('MODERN TRADE', { x:0.60,y:1.80,w:10,h:0.72, fontSize:44,bold:true,color:C.white,fontFace:'Calibri' });
  s.addText("OFFTAKE REVIEW — JULY '26", { x:0.60,y:2.60,w:10,h:0.60, fontSize:30,color:C.white,fontFace:'Calibri' });
  s.addText('Channel: Modern Trade (MT)  |  Scope: All Chains — Offtake & Primary\nPeriod: July 2026 vs July 2025 (YoY)  |  Data validated 20-Aug-26', {
    x:0.60,y:3.50,w:8,h:0.85, fontSize:12,color:'A5D6A7',fontFace:'Calibri' });
  s.addText('₹36.10 Cr Offtake', { x:0.60,y:4.68,w:5.5,h:0.55, fontSize:28,bold:true,color:C.white,fontFace:'Calibri' });
  s.addText('+64.2% YoY', { x:6.20,y:4.75,w:2.5,h:0.40, fontSize:20,bold:true,color:C.mamGreen,fontFace:'Calibri' });
  s.addText('Honasa Consumer Brands  |  MT Analytics  |  20 August 2026', { x:0.60,y:5.65,w:9,h:0.30, fontSize:10,color:'81C784',fontFace:'Calibri' });
  s.addNotes("Cover. July '26 MT executive review. Offtake ₹36.10 Cr +64.2% YoY.");
}

// ── SLIDE 2: EXECUTIVE SUMMARY ────────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "EXECUTIVE SUMMARY — JULY '26: 5 THINGS LEADERSHIP MUST KNOW");
  s.addShape(pres.ShapeType.rect, { x:0.30,y:1.05,w:12.73,h:5.55, fill:{color:C.white}, line:{color:'E8F5E9',width:0.5} });

  const bullets = [
    { n:'01', title:'MT Offtake ₹36.10 Cr — +64.2% YoY — strongest July on record.',
      body:'Total primary ₹49.16 Cr. Sell-through 73.4%. Three chains (Reliance, DMart, Metro) account for ₹13.25 Cr of pipeline gap. L3M offtake ₹114.66 Cr.' },
    { n:'02', title:'Reliance: ₹15.66 Cr loaded, ₹8.06 Cr sold — 51.4% sell-through. Paisa Vasool risk.',
      body:'₹7.61 Cr gap. Loading was scheme-driven; sell-out activation did not follow. NKAM to review store-wise sell-out and initiate liquidation plan by Aug-25.' },
    { n:'03', title:'Apollo benchmarks the channel at 99.7% sell-through — replicable playbook.',
      body:'Primary ₹7.20 Cr, Offtake ₹7.18 Cr. Demand-led ordering + pharmacist engagement + tight SKU discipline. Chain team to document and adapt for Reliance by Sep-15.' },
    { n:'04', title:"The Derma Co. Face Wash ₹7.13 Cr — +47.6% MoM. New monthly record.",
      body:'Up from ₹2.25 Cr in Feb — +217% in 5 months. Now the fastest-growing MT category. Ensure ≥21-day DOI across all MT chains before Aug-10 to prevent OOS.' },
    { n:'05', title:'East Zone 45.3% conversion — ₹4.28 Cr unsold. NPI highest at 10.23%.',
      body:'Primary ₹7.83 Cr, Offtake ₹3.55 Cr. Root cause: listing gaps + no pharmacist activation. RKAM East to table a store-by-store recovery plan by Aug-22.' },
  ];

  bullets.forEach((b, i) => {
    const y = 1.14 + i * 0.94;
    s.addShape(pres.ShapeType.rect, { x:0.38,y,w:0.38,h:0.38, fill:{color:C.kpiPos}, line:{color:C.kpiPos} });
    s.addText(b.n, { x:0.38,y,w:0.38,h:0.38, fontSize:11,bold:true,color:C.white,fontFace:'Calibri',align:'center',valign:'middle',margin:0 });
    s.addText(b.title, { x:0.85,y:y+0.01,w:12.10,h:0.24, fontSize:10,bold:true,color:C.kpiPos,fontFace:'Calibri' });
    s.addText(b.body, { x:0.85,y:y+0.27,w:12.10,h:0.58, fontSize:9,color:C.bodyText,fontFace:'Calibri',valign:'top' });
    if (i < 4) s.addShape(pres.ShapeType.line, { x:0.38,y:y+0.88,w:12.55,h:0, line:{color:'E8F5E9',width:0.5} });
  });

  s.addNotes(`SAY: Strongest July ever — ₹36 Cr out, ₹49 Cr loaded. ₹13 Cr gap needs action now.
PROVE: Reliance ₹7.6 Cr gap. East 45% conversion. Apollo 99.7% — that is the benchmark.
EXPECT: What is the Reliance liquidation plan?
ANSWER: NKAM reviews Aug-25. Trade Marketing provides scheme support. Six-week window before stock ages.`);
}

// ── SLIDE 3: HEADLINE PERFORMANCE ────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "HEADLINE PERFORMANCE — JULY '26");

  const kpis = [
    { lbl:'MT OFFTAKE', val:'₹36.10 Cr', badge:'+64.2% YoY', col:C.kpiPos },
    { lbl:'MT PRIMARY', val:'₹49.16 Cr', badge:'+58.3% YoY', col:C.kpiNeutral },
    { lbl:'SELL-THROUGH', val:'73.4%', badge:'vs ~89% Jun', col:C.kpiNeg },
    { lbl:'PIPELINE GAP', val:'₹13.11 Cr', badge:'Rel+DM+Metro', col:C.kpiNeg },
    { lbl:'L3M OFFTAKE', val:'₹114.66 Cr', badge:'May–Jul 26', col:C.kpiNeutral },
  ];
  kpis.forEach((k, i) => {
    const x = 0.30 + i * 2.56;
    s.addShape(pres.ShapeType.rect, { x,y:1.07,w:2.42,h:0.92, fill:{color:C.kpiTile}, line:{color:'C8E6C9',width:0.5} });
    s.addShape(pres.ShapeType.rect, { x:x+0.05,y:1.12,w:2.32,h:0.42, fill:{color:k.col}, line:{color:k.col} });
    s.addText(k.val, { x:x+0.05,y:1.12,w:2.32,h:0.42, fontSize:15,bold:true,color:C.white,fontFace:'Calibri',align:'center',valign:'middle',margin:0 });
    s.addText(k.lbl, { x:x+0.05,y:1.57,w:2.32,h:0.18, fontSize:7,color:C.kpiLabel,fontFace:'Calibri',align:'center' });
    s.addText(k.badge, { x:x+0.05,y:1.76,w:2.32,h:0.18, fontSize:7,bold:true,color:k.col,fontFace:'Calibri',align:'center' });
  });

  sectionHdr(s, 0.30, 2.12, 6.20, 'PRIMARY vs OFFTAKE BY ZONE (₹ Cr)');
  sectionHdr(s, 6.80, 2.12, 6.23, 'PIPELINE GAP BY CHAIN (₹ Cr)');

  s.addChart(pres.ChartType.bar, [
    { name:'Primary', labels:['North','West','S-1','S-2','East','Central'], values:[11.95,10.05,9.80,6.89,7.83,2.69] },
    { name:'Offtake', labels:['North','West','S-1','S-2','East','Central'], values:[6.99,8.28,8.19,4.91,3.55,2.12] },
  ], {
    x:0.30,y:2.44,w:6.20,h:3.75, barDir:'col', barGrouping:'clustered',
    chartColors:['1B5E20','81C784'], showValue:true, dataLabelFontSize:7,
    showLegend:true, legendPos:'b', legendFontSize:8,
    catAxisLabelColor:'5C6B5C', catAxisLabelFontSize:8,
    valAxisLabelColor:'5C6B5C', valAxisLabelFontSize:8,
    valGridLine:{color:'E8F5E9',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
  });

  s.addChart(pres.ChartType.bar, [
    { name:'Gap (₹ Cr)', labels:['Reliance','DMart','Metro'], values:[7.61,4.29,1.36] },
  ], {
    x:6.80,y:2.44,w:6.23,h:3.75, barDir:'bar', barGrouping:'clustered',
    chartColors:['C62828'], showValue:true, dataLabelFontSize:10,
    dataLabelColor:C.white, dataLabelPosition:'inEnd',
    showLegend:false, catAxisLabelColor:'1A2E1A', catAxisLabelFontSize:10,
    valAxisLabelColor:'5C6B5C', valAxisLabelFontSize:8,
    valGridLine:{color:'FFEBEE',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
  });

  takeaway(s, "July '26 MT offtake ₹36.10 Cr (+64.2% YoY) is the strongest July on record. However 26.6% of primary remains unsold — concentrated in Reliance (₹7.61 Cr), DMart (₹4.29 Cr), and Metro (₹1.36 Cr). Sell-through must reach ≥85% by Aug-31 to protect Q2 FY27 primary planning.");
  s.addNotes(`SAY: Strongest July ever — ₹36 Cr out, ₹49 Cr loaded. ₹13 Cr gap must close before Aug-31.
PROVE: Reliance ₹7.61 Cr unsold. East 45% conversion. Apollo 99.7% proves demand exists.
EXPECT: Is this a demand problem or a loading problem?
ANSWER: Loading. Apollo at 99.7% on ₹7.2 Cr proves demand exists where execution is tight.`);
}

// ── SLIDE 4: ZONE PERFORMANCE ─────────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "ZONE PERFORMANCE — PRIMARY vs OFFTAKE & CONVERSION (JULY '26)");

  const zones = [
    { name:'NORTH', p:11.95, o:6.99, conv:58.5, npi:9.24 },
    { name:'WEST',  p:10.05, o:8.28, conv:82.4, npi:6.58 },
    { name:'S-1',   p:9.80,  o:8.19, conv:83.6, npi:7.88 },
    { name:'S-2',   p:6.89,  o:4.91, conv:71.3, npi:6.37 },
    { name:'EAST',  p:7.83,  o:3.55, conv:45.3, npi:10.23 },
    { name:'CENTRAL',p:2.69, o:2.12, conv:78.8, npi:8.54 },
  ];

  zones.forEach((z, i) => {
    const x = 0.30 + (i % 3) * 4.34;
    const y = 1.08 + Math.floor(i / 3) * 2.55;
    const convCol = z.conv >= 80 ? C.kpiPos : z.conv >= 65 ? 'E65100' : C.kpiNeg;
    const npiCol  = z.npi >= 10 ? C.kpiNeg : 'E65100';

    s.addShape(pres.ShapeType.rect, { x,y,w:4.10,h:2.40, fill:{color:'F9FBF9'}, line:{color:'D0E8D0',width:0.5} });
    s.addShape(pres.ShapeType.rect, { x,y,w:4.10,h:0.28, fill:{color:C.sectionHdr}, line:{color:C.sectionHdr} });
    s.addText(z.name, { x:x+0.08,y,w:4.0,h:0.28, fontSize:9,bold:true,color:C.white,fontFace:'Calibri',valign:'middle',margin:0 });

    const tiles = [
      { lbl:'PRIMARY', val:`₹${z.p.toFixed(2)} Cr`, col:C.kpiNeutral },
      { lbl:'OFFTAKE',  val:`₹${z.o.toFixed(2)} Cr`, col:C.kpiPos },
      { lbl:'CONV %',   val:`${z.conv}%`,             col:convCol },
      { lbl:'NPI %',    val:`${z.npi}%`,              col:npiCol },
    ];
    tiles.forEach((t, ti) => {
      const tx = x + 0.05 + ti * 1.00;
      s.addShape(pres.ShapeType.rect, { x:tx,y:y+0.35,w:0.95,h:0.75, fill:{color:t.col}, line:{color:t.col} });
      s.addText(t.val, { x:tx,y:y+0.35,w:0.95,h:0.44, fontSize:10,bold:true,color:C.white,fontFace:'Calibri',align:'center',valign:'middle',margin:0 });
      s.addText(t.lbl, { x:tx,y:y+0.79,w:0.95,h:0.22, fontSize:6.5,color:'D0E8D0',fontFace:'Calibri',align:'center' });
    });

    const gap = z.p - z.o;
    s.addText(`Gap: ₹${gap.toFixed(2)} Cr  |  Unsold inventory risk`, {
      x:x+0.08,y:y+1.18,w:3.90,h:0.22, fontSize:8,bold:gap>3,color:gap>3?C.kpiNeg:C.kpiLabel,fontFace:'Calibri' });

    // Mini bar in zone box
    s.addChart(pres.ChartType.bar, [
      { name:'Primary', labels:[z.name], values:[z.p] },
      { name:'Offtake',  labels:[z.name], values:[z.o] },
    ], {
      x:x+0.08,y:y+1.42,w:3.90,h:0.85,
      barDir:'col', barGrouping:'clustered',
      chartColors:['1B5E20','81C784'],
      showValue:true, dataLabelFontSize:7,
      showLegend:false, showTitle:false,
      catAxisLabelColor:'FFFFFF', valAxisLabelColor:'5C6B5C',
      valGridLine:{style:'none'}, catGridLine:{style:'none'},
    });
  });

  takeaway(s, "S-1 (83.6%) and West (82.4%) are the execution benchmark. East (45.3%) and North (58.5%) are critical — over ₹11 Cr sitting unsold across two zones. East NPI 10.23% is the highest in MT. RKAM East + North to present recovery plans by Aug-22.");
  s.addNotes(`SAY: Two zones benchmark, two are on fire. S-1 and West show what 83% looks like. East at 45% with ₹7.83 Cr loaded is the red flag.
PROVE: East gap ₹4.28 Cr. North gap ₹4.96 Cr. East NPI 10.23%.
EXPECT: What is driving East underperformance?
ANSWER: Listing gaps in smaller towns + no pharmacist activation. RKAM needs a store-by-store plan by Aug-22.`);
}

// ── SLIDE 5: CHAIN PERFORMANCE ────────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "CHAIN PERFORMANCE — PRIMARY vs OFFTAKE (JULY '26)");

  const chains = [
    { n:'DMart',    p:18.25, o:13.97, conv:76.6 },
    { n:'Reliance', p:15.66, o:8.06,  conv:51.4 },
    { n:'Apollo',   p:7.20,  o:7.18,  conv:99.7 },
    { n:'FSN',      p:2.08,  o:2.07,  conv:99.5 },
    { n:'Lulu',     p:0.00,  o:1.70,  conv:null },
    { n:'Wellness', p:0.49,  o:0.72,  conv:null },
    { n:'H&G',      p:0.22,  o:0.51,  conv:null },
    { n:'Metro',    p:1.84,  o:0.49,  conv:26.4 },
  ];

  s.addChart(pres.ChartType.bar, [
    { name:'Primary (₹ Cr)', labels:chains.map(c=>c.n), values:chains.map(c=>c.p) },
    { name:'Offtake (₹ Cr)', labels:chains.map(c=>c.n), values:chains.map(c=>c.o) },
  ], {
    x:0.30,y:1.08,w:7.80,h:5.10, barDir:'bar', barGrouping:'clustered',
    chartColors:['1B5E20','81C784'], showValue:true, dataLabelFontSize:8,
    showLegend:true, legendPos:'t', legendFontSize:8,
    catAxisLabelColor:'1A2E1A', catAxisLabelFontSize:9,
    valAxisLabelColor:'5C6B5C', valAxisLabelFontSize:8,
    valGridLine:{color:'E8F5E9',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
  });

  sectionHdr(s, 8.30, 1.08, 4.73, 'SELL-THROUGH SUMMARY');

  s.addTable([
    [
      {text:'Chain',   options:{bold:true,color:C.white,fill:C.sectionHdr,fontSize:8}},
      {text:'Primary', options:{bold:true,color:C.white,fill:C.sectionHdr,fontSize:8,align:'center'}},
      {text:'Offtake', options:{bold:true,color:C.white,fill:C.sectionHdr,fontSize:8,align:'center'}},
      {text:'Conv%',   options:{bold:true,color:C.white,fill:C.sectionHdr,fontSize:8,align:'center'}},
    ],
    ...chains.map(c => {
      const convStr = c.conv !== null ? `${c.conv.toFixed(0)}%` : '—';
      const convCol = c.conv === null ? '1A2E1A' : c.conv >= 85 ? C.kpiPos : c.conv >= 65 ? 'E65100' : C.kpiNeg;
      const fillCol = c.conv === null ? C.white : c.conv >= 85 ? 'E8F5E9' : c.conv >= 65 ? 'FFF8E1' : 'FFEBEE';
      return [
        {text:c.n,    options:{fontSize:8,bold:true}},
        {text:`₹${c.p.toFixed(2)}`, options:{fontSize:8,align:'center'}},
        {text:`₹${c.o.toFixed(2)}`, options:{fontSize:8,align:'center'}},
        {text:convStr, options:{fontSize:8,bold:true,align:'center',color:convCol,fill:fillCol}},
      ];
    }),
  ], { x:8.30,y:1.40,w:4.73,h:3.30, rowH:0.30, border:{type:'solid',color:'D0E8D0',pt:0.5}, fontFace:'Calibri' });

  // Alert box
  s.addShape(pres.ShapeType.rect, { x:8.30,y:4.85,w:4.73,h:1.35, fill:{color:'FFEBEE'}, line:{color:C.kpiNeg,width:0.5} });
  s.addText('RELIANCE ALERT', { x:8.40,y:4.90,w:4.50,h:0.22, fontSize:9,bold:true,color:C.kpiNeg,fontFace:'Calibri' });
  s.addText('₹7.61 Cr primary loaded; only ₹8.06 Cr sold out. 51.4% sell-through vs Apollo at 99.7%. Risk of returns and primary cut in Aug planning if unsold stock is not liquidated before Aug-31.', {
    x:8.40,y:5.14,w:4.50,h:0.98, fontSize:8.5,color:'7B0000',fontFace:'Calibri',valign:'top' });

  takeaway(s, "Apollo (99.7%) and FSN/Nykaa (99.5%) prove near-perfect sell-through is achievable. Reliance (51.4%) and Metro (26.4%) are the outliers. DMart at ₹18.25 Cr primary is the largest chain — closing ₹4.3 Cr gap requires targeted in-store activation and sell-out monitoring before Aug-31.");
  s.addNotes(`SAY: Apollo 99.7% sets the standard. Reliance at 51.4% — half of what was loaded is still in the pipeline.
PROVE: Apollo gap ₹0.02 Cr. Reliance gap ₹7.61 Cr. Metro 26.4%.
EXPECT: Why is Reliance so low?
ANSWER: Paisa Vasool loading drove high primary. Sell-out activation did not follow. NKAM must close the loop by Aug-25.`);
}

// ── SLIDE 6: BRAND PERFORMANCE ────────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "BRAND PERFORMANCE — PRIMARY vs OFFTAKE (JULY '26)");

  const brands = [
    { n:'Mamaearth',    p:33.38, o:24.49, conv:73.4 },
    { n:'The Derma Co.',p:15.19, o:11.03, conv:72.6 },
    { n:'Aqualogica',   p:0.41,  o:0.48,  conv:null },
    { n:'BBlunt',       p:0.18,  o:0.06,  conv:36.1 },
    { n:"Dr. Sheth's",  p:0.00,  o:0.03,  conv:null },
  ];

  s.addChart(pres.ChartType.bar, [
    { name:'Primary (₹ Cr)', labels:brands.map(b=>b.n), values:brands.map(b=>b.p) },
    { name:'Offtake (₹ Cr)', labels:brands.map(b=>b.n), values:brands.map(b=>b.o) },
  ], {
    x:0.30,y:1.08,w:6.50,h:4.40, barDir:'bar', barGrouping:'clustered',
    chartColors:['1B5E20','81C784'], showValue:true, dataLabelFontSize:9,
    showLegend:true, legendPos:'t', legendFontSize:8,
    catAxisLabelColor:'1A2E1A', catAxisLabelFontSize:9,
    valAxisLabelColor:'5C6B5C', valAxisLabelFontSize:8,
    valGridLine:{color:'E8F5E9',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
  });

  sectionHdr(s, 7.00, 1.08, 6.03, 'BRAND INSIGHTS — JULY \'26');

  const insights = [
    { brand:'MAMAEARTH', col:C.kpiPos,
      text:'₹33.38 Cr primary | ₹24.49 Cr offtake | 73.4% conversion. Largest MT brand. Face Cleanser ₹8.53 Cr and Shampoo ₹6.95 Cr carry the volume. Sun Care ₹1.30 Cr — seasonal decline (monsoon), expect rebound Oct.' },
    { brand:'THE DERMA CO.', col:C.tdc,
      text:'₹15.19 Cr primary | ₹11.03 Cr offtake | 72.6% conversion. Face Wash ₹7.13 Cr — new monthly record, +47.6% MoM. Fastest-growing MT category in portfolio. Ensure ≥21-day DOI for FW SKUs across all chains by Aug-10.' },
    { brand:'AQUALOGICA', col:'00838F',
      text:'₹0.41 Cr primary | ₹0.48 Cr offtake. Sell-through >100% — drawing from pipeline stock. Demand outpacing supply for key SKUs. Check DOI and raise next primary order.' },
    { brand:'BBLUNT', col:'D84315',
      text:'₹0.18 Cr primary | ₹0.06 Cr offtake | 36.1% conversion. Hair-care loading not translating to sell-out in MT. Category team to review SKU relevance and recommend rationalisation before next QBR.' },
  ];

  insights.forEach((ins, i) => {
    const y = 1.42 + i * 1.30;
    s.addShape(pres.ShapeType.rect, { x:7.00,y,w:0.09,h:1.15, fill:{color:ins.col}, line:{color:ins.col} });
    s.addText(ins.brand, { x:7.16,y:y+0.04,w:5.76,h:0.24, fontSize:9.5,bold:true,color:ins.col,fontFace:'Calibri' });
    s.addText(ins.text, { x:7.16,y:y+0.30,w:5.76,h:0.82, fontSize:8.5,color:C.bodyText,fontFace:'Calibri',valign:'top' });
  });

  takeaway(s, "Mamaearth (73.4%) and TDC (72.6%) mirror channel sell-through — pipeline discipline is consistent. TDC acceleration is the standout: Face Wash ₹7.13 Cr is a new record and signals capacity build in FW supply. BBlunt 36% — category team to review MT SKU relevance.");
  s.addNotes(`SAY: Two brands, one conversion rate — good discipline. TDC Face Wash at ₹7.13 Cr is the signal of the month.
PROVE: TDC FW up 47.6% MoM. Aqualogica sell-through >100% — stock constrained. BBlunt at 36% — flag for category.
EXPECT: Should we prioritise TDC over Mamaearth in MT?
ANSWER: Not zero-sum — ME volume is 3× TDC. But TDC trajectory demands more primary supply and shelf space.`);
}

// ── SLIDE 7: MAMAEARTH CATEGORIES ────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "MAMAEARTH — CATEGORY OFFTAKE TRENDS (FEB–JUL '26)");

  const months = ['Feb','Mar','Apr','May','Jun','Jul'];

  s.addChart(pres.ChartType.line, [
    { name:'Face Cleanser', labels:months, values:[7.03,8.17,8.55,9.63,9.65,8.53] },
    { name:'Shampoo',       labels:months, values:[4.81,5.38,6.11,6.68,6.87,6.95] },
    { name:'Sun Care',      labels:months, values:[1.55,2.73,3.10,2.95,1.99,1.30] },
  ], {
    x:0.30,y:1.08,w:8.20,h:5.40,
    chartColors:['1B5E20','1565C0','E65100'],
    showValue:true, dataLabelFontSize:8,
    lineDataSymbol:'circle', lineDataSymbolSize:6,
    showLegend:true, legendPos:'b', legendFontSize:9,
    catAxisLabelColor:'5C6B5C', catAxisLabelFontSize:9,
    valAxisLabelColor:'5C6B5C', valAxisLabelFontSize:8,
    valGridLine:{color:'E8F5E9',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
  });

  sectionHdr(s, 8.70, 1.08, 4.33, 'CATEGORY CALLOUTS');

  const callouts = [
    { cat:'Face Cleanser', val:'₹8.53 Cr', trend:'-11.6% MoM', col:C.kpiNeg,
      note:'Post-peak correction after Jun ₹9.65 Cr high. Monsoon seasonality expected. YTD trajectory strong — up from ₹7.03 Cr in Feb. Category team to monitor Jul stock vs Aug offtake.' },
    { cat:'Shampoo', val:'₹6.95 Cr', trend:'+1.2% MoM', col:C.kpiPos,
      note:'Consistent 5-month ascent — now #2 category. Growth resilience through monsoon is noteworthy. Volume sustained by S-1 and West activation. Target ₹8 Cr by Sep.' },
    { cat:'Sun Care', val:'₹1.30 Cr', trend:'-34.7% MoM', col:C.kpiNeg,
      note:'Seasonal monsoon decline expected — peaked Apr at ₹3.10 Cr. Category will recover Oct-Nov with winter-UV demand. Do not over-primary through Aug; avoid ageing stock risk.' },
  ];

  callouts.forEach((c, i) => {
    const y = 1.45 + i * 1.75;
    s.addShape(pres.ShapeType.rect, { x:8.70,y,w:4.33,h:1.60, fill:{color:'F9FBF9'}, line:{color:'D0E8D0',width:0.5} });
    s.addText(c.cat, { x:8.80,y:y+0.06,w:3.0,h:0.24, fontSize:9.5,bold:true,color:C.sectionHdr,fontFace:'Calibri' });
    s.addText(c.val, { x:8.80,y:y+0.32,w:1.80,h:0.35, fontSize:18,bold:true,color:C.kpiNeutral,fontFace:'Calibri' });
    s.addText(c.trend, { x:10.65,y:y+0.38,w:2.25,h:0.24, fontSize:10,bold:true,color:c.col,fontFace:'Calibri',align:'right' });
    s.addText(c.note, { x:8.80,y:y+0.70,w:4.10,h:0.86, fontSize:8,color:C.bodyText,fontFace:'Calibri',valign:'top' });
  });

  s.addNotes(`SAY: Shampoo is the resilience story — only ME category still growing through monsoon. Face Cleanser corrected from the Jun peak but stays healthy at ₹8.53 Cr.
PROVE: Shampoo 5 consecutive months of growth. Face Cleanser still #1 at ₹8.53 Cr.
EXPECT: Will Sun Care stay flat through Q2?
ANSWER: Yes — monsoon seasonality. Rebound Oct-Nov. Do not load inventory through Aug.`);
}

// ── SLIDE 8: TDC CATEGORIES ───────────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "THE DERMA CO. — CATEGORY OFFTAKE TRENDS (FEB–JUL '26)");

  const months = ['Feb','Mar','Apr','May','Jun','Jul'];

  s.addChart(pres.ChartType.line, [
    { name:'Face Cleanser', labels:months, values:[2.25,2.75,3.24,4.63,4.83,7.13] },
    { name:'Sun Care',      labels:months, values:[1.04,1.81,2.27,3.18,2.05,1.99] },
    { name:'Face Serum',    labels:months, values:[0.56,0.57,0.69,0.66,0.66,0.63] },
  ], {
    x:0.30,y:1.08,w:8.20,h:5.40,
    chartColors:['1565C0','E65100','6A1B9A'],
    showValue:true, dataLabelFontSize:8,
    lineDataSymbol:'circle', lineDataSymbolSize:6,
    showLegend:true, legendPos:'b', legendFontSize:9,
    catAxisLabelColor:'5C6B5C', catAxisLabelFontSize:9,
    valAxisLabelColor:'5C6B5C', valAxisLabelFontSize:8,
    valGridLine:{color:'E3F2FD',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
  });

  sectionHdr(s, 8.70, 1.08, 4.33, 'CATEGORY CALLOUTS');

  const callouts = [
    { cat:'Face Cleanser (FW)', val:'₹7.13 Cr', trend:'+47.6% MoM', col:C.kpiPos,
      note:'Breakthrough month — new all-time record. Up from ₹2.25 Cr in Feb (+217% in 5 months). Fastest-growing MT category in portfolio. Ensure ≥21-day DOI across all MT chains before Aug-10.' },
    { cat:'Sun Care', val:'₹1.99 Cr', trend:'-3.0% MoM', col:C.kpiNeg,
      note:'Holding well despite monsoon — Jun was ₹3.18 Cr peak. Mild Jul-Aug correction expected. Do not over-primary — risk of ageing stock if loaded ahead of Oct rebound.' },
    { cat:'Face Serum', val:'₹0.63 Cr', trend:'-4.5% MoM', col:C.kpiNeg,
      note:'Flat-to-mildly declining trend. Serum penetration in MT is low vs pharmacy. Consider serum sampling in Apollo/Wellness to seed demand before Diwali push.' },
  ];

  callouts.forEach((c, i) => {
    const y = 1.45 + i * 1.75;
    s.addShape(pres.ShapeType.rect, { x:8.70,y,w:4.33,h:1.60, fill:{color:'F0F7FF'}, line:{color:'B0C4DE',width:0.5} });
    s.addText(c.cat, { x:8.80,y:y+0.06,w:4.10,h:0.24, fontSize:9.5,bold:true,color:C.tdc,fontFace:'Calibri' });
    s.addText(c.val, { x:8.80,y:y+0.32,w:1.80,h:0.35, fontSize:18,bold:true,color:C.kpiNeutral,fontFace:'Calibri' });
    s.addText(c.trend, { x:10.65,y:y+0.38,w:2.25,h:0.24, fontSize:10,bold:true,color:c.col,fontFace:'Calibri',align:'right' });
    s.addText(c.note, { x:8.80,y:y+0.70,w:4.10,h:0.86, fontSize:8,color:C.bodyText,fontFace:'Calibri',valign:'top' });
  });

  takeaway(s, "TDC Face Wash ₹7.13 Cr is the most important number this month — 3× its Feb base in 5 months. +47.6% MoM acceleration through monsoon signals structural demand, not seasonality. Immediate action: secure 21-day DOI on FW SKUs and pilot pharmacist sampling in Apollo from Aug-15.");
  s.addNotes(`SAY: TDC Face Wash at ₹7.13 Cr — 3× February in 5 months. No other category has this trajectory.
PROVE: Feb ₹2.25 → Jul ₹7.13 = +217% in 5 months. Sun Care holding at ₹1.99 Cr despite monsoon.
EXPECT: How do we sustain Face Wash momentum?
ANSWER: Stock discipline first — 21-day DOI by Aug-10. Then demand amplification in Apollo from Aug-15.`);
}

// ── SLIDE 9: NPI ANALYSIS ─────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "NON-PERFORMING INVENTORY (NPI) — JULY '26 ALERT");

  s.addShape(pres.ShapeType.rect, { x:0.30,y:1.07,w:12.73,h:0.55, fill:{color:'FFEBEE'}, line:{color:C.kpiNeg,width:0.5} });
  s.addText('NPI TOTAL ≈ ₹270 Lacs  |  Highest zone: East 10.23%  |  Top chains: Reliance ₹130.47 L + DMart ₹97.71 L = 84% of chain NPI', {
    x:0.40,y:1.07,w:12.50,h:0.55, fontSize:9.5,bold:true,color:C.kpiNeg,fontFace:'Calibri',valign:'middle' });

  sectionHdr(s, 0.30, 1.70, 5.80, 'NPI BY CHAIN (₹ Lacs)');
  sectionHdr(s, 6.40, 1.70, 6.23, 'NPI% BY ZONE');

  s.addChart(pres.ChartType.bar, [
    { name:'NPI (₹ Lacs)', labels:['Reliance','DMart','Lulu','FSN','H&G','Metro'], values:[130.47,97.71,18.02,12.93,5.95,5.02] },
  ], {
    x:0.30,y:2.02,w:5.80,h:4.25, barDir:'bar', barGrouping:'clustered',
    chartColors:['C62828'], showValue:true, dataLabelFontSize:9,
    dataLabelColor:C.white, dataLabelPosition:'inEnd',
    showLegend:false, catAxisLabelColor:'1A2E1A', catAxisLabelFontSize:9,
    valAxisLabelColor:'5C6B5C', valAxisLabelFontSize:8,
    valGridLine:{color:'FFEBEE',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
  });

  s.addChart(pres.ChartType.bar, [
    { name:'NPI%', labels:['East','Central','North','S-1','West','S-2'], values:[10.23,8.54,9.24,7.88,6.58,6.37] },
  ], {
    x:6.40,y:2.02,w:6.23,h:4.25, barDir:'bar', barGrouping:'clustered',
    chartColors:['E65100'], showValue:true, dataLabelFontSize:9,
    dataLabelColor:C.white, dataLabelPosition:'inEnd',
    showLegend:false, catAxisLabelColor:'1A2E1A', catAxisLabelFontSize:9,
    valAxisLabelColor:'5C6B5C', valAxisLabelFontSize:8,
    valGridLine:{color:'FFF3E0',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
  });

  takeaway(s, "₹270 Lacs of non-performing inventory is the forward risk. Reliance (₹130 L) and DMart (₹98 L) together = ₹228 L. If not cleared by Sep, primary will be cut in Oct planning. NKAM + Supply to initiate liquidation drives — scheme support, store activations — before Aug-31. Six-week window.");
  s.addNotes(`SAY: ₹270 Lacs of non-performing inventory — this is what happens when primary is loaded without matching sell-out.
PROVE: Reliance ₹130 L alone is half the NPI. East zone 10.23% — highest nationally.
EXPECT: Will this affect Q2 targets?
ANSWER: Yes, unless cleared in Aug. A primary cut in Oct planning starts here. Window is 6 weeks.`);
}

// ── SLIDE 10: FSN / NYKAA DEEP DIVE ──────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "FSN / NYKAA — OFFTAKE TREND & ASSORTMENT HEALTH (JAN–JUL '26)");

  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul'];
  const offtake = [1.64,1.68,1.73,2.29,2.08,2.17,2.07];
  const eans    = [222,217,203,196,190,200,198];

  // Combo chart: bar (offtake) + line (EAN count) with secondary axis
  s.addChart([
    {
      type: pres.ChartType.bar,
      data: [{ name:'Offtake (₹ Cr)', labels:months, values:offtake }],
      options: { chartColors:['1B5E20'], barDir:'col', barGrouping:'clustered' },
    },
    {
      type: pres.ChartType.line,
      data: [{ name:'EAN Count', labels:months, values:eans }],
      options: { chartColors:['C62828'], secondaryValAxis:true, secondaryCatAxis:true, lineDataSymbol:'circle', lineDataSymbolSize:6 },
    },
  ], {
    x:0.30,y:1.08,w:7.50,h:5.40,
    showValue:true, dataLabelFontSize:8,
    showLegend:true, legendPos:'b', legendFontSize:9,
    catAxisLabelColor:'5C6B5C', catAxisLabelFontSize:9,
    valAxisLabelColor:'1B5E20', valAxisLabelFontSize:8,
    valGridLine:{color:'E8F5E9',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
    valAxes:[
      { showValAxisTitle:false, valAxisLabelColor:'1B5E20' },
      { showValAxisTitle:false, valAxisLabelColor:'C62828', valAxisOrientation:'minMax' },
    ],
    catAxes:[
      { catAxisLabelColor:'5C6B5C' },
      { catAxisHidden:true },
    ],
  });

  sectionHdr(s, 8.00, 1.08, 5.03, 'NYKAA DEEP DIVE');

  const nykaaInsights = [
    { title:'OFFTAKE TREND',
      text:'Apr spike to ₹2.29 Cr was Nykaa sale-event driven. Jun-Jul settling at ₹2.07–2.17 Cr — structural base is firm. YoY comparison turns strongly positive from Q3 FY27.' },
    { title:'EAN COUNT — CONCERN',
      text:'Active EANs dropped from 222 (Jan) to 190 (May) — 14.4% reduction. Partial recovery to 198 in Jul. Delisted SKUs driving the contraction. NKAM to audit returns and reinstate top EANs.' },
    { title:'RISK: SKU CONCENTRATION',
      text:'Fewer EANs at higher per-SKU velocity is healthy short-term but leaves the chain exposed. Single-SKU OOS or delisting could materially impact monthly offtake.' },
    { title:'ACTION — DIWALI PREP',
      text:'(1) Recover 10+ EANs lost since Jan. (2) Ensure 30-day DOI on top-10 EANs. (3) Negotiate shelf-space expansion before Oct-15 Diwali window. Owner: NKAM-FSN.' },
  ];

  nykaaInsights.forEach((ins, i) => {
    const y = 1.45 + i * 1.30;
    sectionHdr(s, 8.00, y, 5.03, ins.title);
    s.addText(ins.text, { x:8.00,y:y+0.31,w:5.03,h:0.92, fontSize:8.5,color:C.bodyText,fontFace:'Calibri',valign:'top' });
  });

  s.addNotes(`SAY: Nykaa is a ₹2 Cr/month account — structurally solid. EAN erosion from 222 to 190 is the story to watch.
PROVE: 14.4% fewer SKUs since Jan. Offtake held — per-SKU velocity up. That's fragile concentration.
EXPECT: Is Nykaa a growth account?
ANSWER: Yes — but EAN recovery is needed. Target 210 active EANs by Oct. Diwali shelf negotiations start now.`);
}

// ── SLIDE 11: APOLLO BENCHMARK ───────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "APOLLO PHARMACY — THE 99.7% BENCHMARK: WHAT GOOD LOOKS LIKE");

  // Apollo spotlight left
  s.addShape(pres.ShapeType.rect, { x:0.30,y:1.08,w:4.50,h:5.60, fill:{color:'F3E5F5'}, line:{color:'6A1B9A',width:1} });
  s.addText('APOLLO', { x:0.40,y:1.18,w:4.30,h:0.55, fontSize:30,bold:true,color:'6A1B9A',fontFace:'Calibri',align:'center' });

  const aTiles = [
    { lbl:'Primary Loaded', val:'₹7.20 Cr' },
    { lbl:'Offtake Sold',   val:'₹7.18 Cr' },
    { lbl:'Sell-Through',   val:'99.7%' },
    { lbl:'Pipeline Gap',   val:'₹0.02 Cr' },
  ];
  aTiles.forEach((t, i) => {
    const ay = 1.92 + i * 0.88;
    s.addShape(pres.ShapeType.rect, { x:0.55,y:ay,w:4.00,h:0.65, fill:{color:'6A1B9A'}, line:{color:'6A1B9A'} });
    s.addText(t.val, { x:0.55,y:ay,w:4.00,h:0.40, fontSize:18,bold:true,color:C.white,fontFace:'Calibri',align:'center',valign:'middle',margin:0 });
    s.addText(t.lbl, { x:0.55,y:ay+0.42,w:4.00,h:0.21, fontSize:7.5,color:'CE93D8',fontFace:'Calibri',align:'center' });
  });

  s.addText('WHY APOLLO WORKS', { x:0.40,y:5.48,w:4.30,h:0.24, fontSize:9,bold:true,color:'6A1B9A',fontFace:'Calibri',align:'center' });
  s.addText('Demand-led primary orders → no loading pressure\nPharmacist engagement drives throughput\nTight SKU discipline — zero deadwood\nStrong field team accountability', {
    x:0.40,y:5.74,w:4.30,h:0.86, fontSize:8.5,color:'4A148C',fontFace:'Calibri',valign:'top' });

  // Comparison chart right
  sectionHdr(s, 4.98, 1.08, 8.05, 'SELL-THROUGH % — ALL CHAINS vs APOLLO BENCHMARK');

  s.addChart(pres.ChartType.bar, [
    {
      name:'Sell-Through %',
      labels:['Apollo','FSN/Nykaa','S-1 (zone avg)','West (zone avg)','MT Average','DMart','Reliance','Metro'],
      values:[99.7,99.5,83.6,82.4,73.4,76.6,51.4,26.4],
    },
  ], {
    x:4.98,y:1.40,w:8.05,h:5.28, barDir:'bar', barGrouping:'clustered',
    chartColors:['1565C0'], showValue:true, dataLabelFontSize:9,
    dataLabelColor:C.white, dataLabelPosition:'inEnd',
    showLegend:false, catAxisLabelColor:'1A2E1A', catAxisLabelFontSize:9,
    valAxisLabelColor:'5C6B5C', valAxisLabelFontSize:8,
    valGridLine:{color:'E3F2FD',size:0.5}, catGridLine:{style:'none'}, showTitle:false,
  });

  s.addNotes(`SAY: Apollo at 99.7% is the answer to "what is possible?" Every chain is measured against this.
PROVE: Reliance 48 points below Apollo. DMart 23 points below. MT avg 26 points below benchmark.
EXPECT: Can we force Reliance to match this?
ANSWER: Apollo playbook — demand-led ordering, pharmacist activation, tight SKU set — can be adapted for Reliance. NKAM must shift the conversation from "how much to load" to "what is the pull-through plan."`);
}

// ── SLIDE 12: ACTION PLAN ─────────────────────────────────────────────────────
{
  const s = pres.addSlide();
  addHeader(s, "AUGUST '26 ACTION PLAN — OWNERS, DATES & ACCOUNTABILITY");

  const actions = [
    { p:'P1', col:C.kpiNeg, fillCol:'FFEBEE',
      issue:'Reliance pipeline gap — ₹7.61 Cr unsold (51.4%)',
      action:'NKAM to review Reliance store-wise sell-out; activate liquidation scheme',
      owner:'NKAM-Reliance + Trade Mktg', by:'25-Aug' },
    { p:'P1', col:C.kpiNeg, fillCol:'FFEBEE',
      issue:'East Zone — 45.3% conversion, NPI 10.23%',
      action:'RKAM East to submit store-by-store recovery plan; target 70%+ by Sep-30',
      owner:'RKAM East', by:'22-Aug' },
    { p:'P1', col:C.kpiNeg, fillCol:'FFEBEE',
      issue:'TDC Face Wash — OOS risk at ₹7.13 Cr velocity',
      action:'Ensure ≥21-day DOI across all MT chains for FW SKUs',
      owner:'Supply + Category', by:'10-Aug' },
    { p:'P2', col:'E65100', fillCol:'FFF8E1',
      issue:'Metro sell-through 26.4% — ₹1.36 Cr gap',
      action:'NKAM to audit Metro listing; agree monthly sell-out target with chain',
      owner:'NKAM-Metro', by:'31-Aug' },
    { p:'P2', col:'E65100', fillCol:'FFF8E1',
      issue:'FSN/Nykaa EAN count 198 vs 222 (Jan)',
      action:'Recover 10+ EANs; secure 30-day DOI on top-10; negotiate Diwali shelf space',
      owner:'NKAM-FSN', by:'15-Oct' },
    { p:'P3', col:C.kpiPos, fillCol:'E8F5E9',
      issue:"Apollo 99.7% playbook — replicate across Reliance",
      action:'Chain team to document Apollo best practices and adapt for Reliance format',
      owner:'Category + NKAM-Reliance', by:'15-Sep' },
    { p:'P3', col:C.kpiPos, fillCol:'E8F5E9',
      issue:'BBlunt MT relevance — 36% sell-through',
      action:'Category to review BBlunt SKU-set for MT; recommend rationalisation',
      owner:'Category Team', by:'30-Sep' },
  ];

  s.addTable([
    [
      {text:'P',       options:{bold:true,color:C.white,fill:C.headerBg,fontSize:8,align:'center'}},
      {text:'Issue',   options:{bold:true,color:C.white,fill:C.headerBg,fontSize:8}},
      {text:'Action',  options:{bold:true,color:C.white,fill:C.headerBg,fontSize:8}},
      {text:'Owner',   options:{bold:true,color:C.white,fill:C.headerBg,fontSize:8}},
      {text:'By',      options:{bold:true,color:C.white,fill:C.headerBg,fontSize:8,align:'center'}},
    ],
    ...actions.map(a => [
      {text:a.p,      options:{fontSize:8,bold:true,color:C.white,fill:a.col,align:'center'}},
      {text:a.issue,  options:{fontSize:8,fill:a.fillCol}},
      {text:a.action, options:{fontSize:8}},
      {text:a.owner,  options:{fontSize:8,italic:true}},
      {text:a.by,     options:{fontSize:8,bold:true,align:'center',color:a.col}},
    ]),
  ], {
    x:0.30,y:1.08,w:12.73,h:5.80,
    rowH:0.68,
    border:{type:'solid',color:'D0E8D0',pt:0.5},
    fontFace:'Calibri',
    colW:[0.42,3.30,4.60,2.50,1.00],
  });

  s.addNotes(`SAY: Seven actions, three priority levels, one window — Aug-31 for P1s. Reliance and East are non-negotiable.
PROVE: Reliance ₹7.6 Cr gap. East 45%. TDC FW OOS risk — all addressable in 6 weeks.
EXPECT: Who is accountable for Reliance liquidation?
ANSWER: NKAM-Reliance presents a sell-through plan by Aug-25. Trade Marketing provides scheme support. No plan = escalation.`);
}

// ── WRITE FILE ────────────────────────────────────────────────────────────────
const outPath = '/home/user/mt-dashboard/MT_Jul26_Honasa_Executive_Review.pptx';
pres.writeFile({ fileName: outPath })
  .then(() => console.log('DONE:', outPath))
  .catch(err => { console.error('ERROR:', err); process.exit(1); });
