'use strict';
const pptxgen = require('pptxgenjs');

// ── Palette ───────────────────────────────────────────────────────────────────
const C = {
  navy:    '0D1E35', gold:    'C49A1A', ink:     '1A2840',
  bg:      'F4F6FB', white:   'FFFFFF', pos:     '2E7D52',
  neg:     'CC3333', amber:   'E67E22', blue:    '3A89C9',
  muted:   '8A9BB2', midnavy: '1A3459', teal:    '1B7A6E',
  lgray:   'D8DDE8', plum:    '5C3370', coral:   'C0392B',
};

// ── Authoritative data ────────────────────────────────────────────────────────
// Channel: MT zone-sum 33.96, eB2B 2.07, SIS 0.034 → total 36.06 Cr
const jul = {
  mt:   { offtake: 33.96, primary: 47.02, conv: 72.2, gap: 13.06 },
  eb2b: { offtake: 2.07, primary: 2.20, flow: 93.9 },
  sis:  { offtake: 0.034 },
  total:{ offtake: 36.06, nsv_lakh: 3606.34, units: 1895052, asp: 179.21, real: 42.2 },
};
const fytd = { nsv_cr: 150.55, nsv_lakh: 15054.73 };
const q1   = { nsv_cr: 114.48 };
const eb2bFytd = 860.01; // lakh Apr-Jul

// Monthly MT trend
const monthly = {
  labels: ['Apr-26','May-26','Jun-26','Jul-26'],
  nsv:    [35.89, 40.19, 38.40, 36.06],
};
// Monthly eB2B Jan-Jul (chart17 series)
const eb2bMonthly = {
  labels: ['Jan','Feb','Mar','Apr','May','Jun','Jul'],
  vals:   [1.64, 1.68, 1.73, 2.29, 2.08, 2.17, 2.07],
};

// July zones
const julZones = [
  { zone:'West',    nsv:8.27, units:497615, asp:166.22, aspIdx:93,  real:41.9, conv:85.2, gap:1.44 },
  { zone:'South-1', nsv:8.18, units:433962, asp:188.56, aspIdx:105, real:42.7, conv:86.3, gap:1.30 },
  { zone:'North',   nsv:6.97, units:377364, asp:184.82, aspIdx:103, real:41.8, conv:61.3, gap:4.41 },
  { zone:'South-2', nsv:4.87, units:278020, asp:175.3,  aspIdx:98,  real:42.9, conv:72.4, gap:1.85 },
  { zone:'East',    nsv:3.54, units:183289, asp:193.17, aspIdx:108, real:42.1, conv:49.9, gap:3.56 },
  { zone:'Central', nsv:2.12, units:124802, asp:169.69, aspIdx:95,  real:41.1, conv:80.9, gap:0.50 },
];
const fytdZones = [
  { zone:'West',    fy27:3732.52, fy26:8171.0, yoy:31.47 },
  { zone:'North',   fy27:3339.92, fy26:7060.0, yoy:62.37 },
  { zone:'South-1', fy27:3308.35, fy26:6428.0, yoy:56.70 },
  { zone:'South-2', fy27:2063.89, fy26:4163.0, yoy:26.92 },
  { zone:'East',    fy27:1528.60, fy26:3223.0, yoy:53.84 },
  { zone:'Central', fy27: 211.77, fy26: null,  yoy: null },
];

// Market share (chart series "3")
const mktShare = {
  faceWash: [
    { brand:'Himalaya', share:22.6, yoy:-1.6, rank:1 },
    { brand:'Garnier',  share:14.2, yoy:+0.8, rank:2 },
    { brand:"Pond's",   share:13.8, yoy:-0.4, rank:3 },
    { brand:'Mamaearth',share:10.5, yoy:+1.2, rank:4 },
  ],
  shampoo: [
    { brand:'Dove',      share:16.6, rank:1 },
    { brand:'H&S',       share:13.0, rank:2 },
    { brand:'Mamaearth', share: 3.7, rank:7 },
  ],
};

// Brand portfolio (chart series "17")
const brands = [
  { brand:'Mamaearth',     primary:33.38, offtake:24.49, conv:73.4 },
  { brand:'The Derma Co.', primary:15.19, offtake:11.03, conv:72.6 },
  { brand:'Aqualogica',    primary: 0.41, offtake: 0.48, conv:null },
  { brand:'BBlunt',        primary: 0.18, offtake: 0.06, conv:null },
  { brand:"Dr. Sheth's",   primary: 0.00, offtake: 0.03, conv:null },
];

// Category trends (chart series "17" → chart24/25)
// Mamaearth: Feb-Jul values
const mhCat = {
  labels:       ['Feb','Mar','Apr','May','Jun','Jul'],
  faceCleaner:  [7.03, 8.17, 8.55, 9.63, 9.65, 8.53],
  shampoo:      [4.81, 5.38, 6.11, 6.68, 6.87, 6.95],
  sunCare:      [1.55, 2.73, 3.10, 2.95, 1.99, 1.30],
};
// Derma Co.: Feb-Jul values
const dcCat = {
  labels:      ['Feb','Mar','Apr','May','Jun','Jul'],
  faceCleaner: [2.25, 2.75, 3.24, 4.63, 4.83, 7.13],
  sunCare:     [1.04, 1.81, 2.27, 3.18, 2.05, 1.99],
  faceSerum:   [0.56, 0.57, 0.69, 0.66, 0.66, 0.63],
};

// Account breakdown (chart series "16")
const accounts = [
  { acct:'DMart',          primary:18.25, offtake:13.97, gap:4.28, conv:76.5 },
  { acct:'Reliance',       primary:15.66, offtake: 8.06, gap:7.60, conv:51.5 },
  { acct:'Apollo',         primary: 7.20, offtake: 7.18, gap:0.02, conv:99.7 },
  { acct:'FSN/Nykaa',      primary: 2.08, offtake: 2.07, gap:0.01, conv:99.5 },
  { acct:'Lulu',           primary: 0.00, offtake: 1.70, gap:0,    conv:null },
  { acct:'Wellness',       primary: 0.49, offtake: 0.72, gap:0,    conv:null },
  { acct:'H&G',            primary: 0.22, offtake: 0.51, gap:0,    conv:null },
  { acct:'Metro',          primary: 1.84, offtake: 0.49, gap:1.35, conv:26.6 },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
function convColor(p){ return p>=85?C.pos:p>=70?C.gold:C.neg; }
function yoyColor(y) { return y==null?C.muted:y>=50?C.pos:y>=25?C.teal:y>=0?C.gold:C.neg; }

function hdr(s, title, sub='', dark=true){
  s.background={color:dark?C.navy:C.bg};
  const fg=dark?C.white:C.ink, sf=dark?'8EAACF':C.muted;
  s.addText(title,{x:0.38,y:0.13,w:8.9,h:0.48,fontSize:21,bold:true,color:fg,fontFace:'Cambria',align:'left',margin:0});
  if(sub) s.addText(sub,{x:0.38,y:0.62,w:9.1,h:0.26,fontSize:10,color:sf,fontFace:'Calibri',align:'left',margin:0});
  s.addText("Honasa Consumer · MT Analytics · FY'26-27 · Data: pipeline v2.4.0",{x:4.8,y:0.16,w:4.8,h:0.2,fontSize:7,color:sf,align:'right',fontFace:'Calibri',margin:0});
  s.addShape('rect',{x:0.38,y:0.6+(sub?0.32:0),w:1.5,h:0.03,fill:{color:C.gold},line:{type:'none'}});
}

function kpi(s,x,y,w,h,val,lbl,sub='',vColor=null,dark=true){
  const bg=dark?C.midnavy:C.white, fg=dark?C.white:C.ink, sf=dark?'8EAACF':C.muted;
  s.addShape('rect',{x,y,w,h,fill:{color:bg},line:{type:'none'},shadow:{type:'outer',blur:4,offset:2,angle:45,color:'8E8E8E'}});
  s.addText(val,{x:x+0.08,y:y+0.1,w:w-0.16,h:h*0.5,fontSize:22,bold:true,color:vColor||fg,fontFace:'Cambria',align:'center',margin:0});
  s.addText(lbl,{x:x+0.06,y:y+h*0.58,w:w-0.12,h:h*0.24,fontSize:8.5,bold:true,color:fg,fontFace:'Calibri',align:'center',margin:0});
  if(sub) s.addText(sub,{x:x+0.06,y:y+h*0.82,w:w-0.12,h:h*0.18,fontSize:7.5,color:sf,fontFace:'Calibri',align:'center',margin:0});
}

function pill(s,x,y,label,color,textColor=C.white){
  const w=label.length*0.085+0.28;
  s.addShape('rect',{x,y,w,h:0.25,fill:{color},line:{type:'none'}});
  s.addText(label,{x:x+0.06,y:y+0.03,w:w-0.1,h:0.19,fontSize:8,bold:true,color:textColor,fontFace:'Calibri',margin:0});
  return w;
}

function shareBar(s,x,y,w,pct,color,label=''){
  const bw=w*(pct/100);
  s.addShape('rect',{x,y,w,h:0.16,fill:{color:'D8DDE8'},line:{type:'none'}});
  s.addShape('rect',{x,y,w:bw,h:0.16,fill:{color},line:{type:'none'}});
  if(label) s.addText(label,{x:x+w+0.06,y:y-0.03,w:0.9,h:0.22,fontSize:8.5,color:C.ink,fontFace:'Calibri',margin:0});
}

const pres=new pptxgen();
pres.layout='LAYOUT_16x9';

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 1 · Executive Summary
// ═══════════════════════════════════════════════════════════════════════════════
{
  const s=pres.addSlide();
  hdr(s,"July 2026 — MT Offtake Executive Summary","All-channel offtake ₹ Cr  ·  MT + eB2B + SIS  ·  FY'26-27  ·  All 4 months confirmed",true);

  // 5 KPI cards row
  const cards=[
    {v:'₹36.06 Cr', l:'Jul-26 Total NSV', sub:'3,606 L · 18.95L units · ASP ₹179'},
    {v:'₹150.55 Cr',l:'FYTD Apr–Jul NSV', sub:'15,055 L · Q1+Jul · All 4 months'},
    {v:'₹24.49 Cr', l:'Mamaearth Jul',    sub:'Offtake · 66% brand share · conv 73.4%'},
    {v:'₹11.03 Cr', l:'Derma Co. Jul',    sub:'Offtake · 29.7% share · Face Cleaner ↑217%'},
    {v:'₹15.66 Cr', l:'Face Cleanser Jul', sub:'MH ₹8.53 + DC ₹7.13 · Category #1'},
  ];
  cards.forEach((c,i)=>kpi(s,0.25+i*1.93,1.06,1.78,1.28,c.v,c.l,c.sub,null,true));

  // YoY momentum bars (FYTD zone)
  s.addText('FYTD Zone Momentum (YoY % vs FY26 full-year)',{x:0.25,y:2.5,w:5.8,h:0.25,fontSize:9,bold:true,color:'8EAACF',fontFace:'Calibri',margin:0});
  const yoyData=[
    {z:'North',  y:62.37},{z:'South-1',y:56.70},{z:'East',   y:53.84},
    {z:'South-2',y:26.92},{z:'West',   y:31.47},
  ];
  yoyData.forEach((d,i)=>{
    const x=0.25+i*1.93, y=2.75;
    const bh=(d.y/70)*0.85;
    s.addShape('rect',{x:x+0.4,y:y+(0.85-bh),w:0.9,h:bh,fill:{color:yoyColor(d.y)},line:{type:'none'}});
    s.addText('+'+d.y.toFixed(0)+'%',{x,y:y+(0.85-bh)-0.3,w:1.78,h:0.28,fontSize:11,bold:true,color:yoyColor(d.y),fontFace:'Cambria',align:'center',margin:0});
    s.addText(d.z,{x,y:y+0.87,w:1.78,h:0.22,fontSize:8.5,color:'8EAACF',fontFace:'Calibri',align:'center',margin:0});
  });

  // Jul recovery callout
  s.addShape('rect',{x:0.25,y:3.88,w:9.5,h:0.62,fill:{color:'132A48'},line:{type:'none'}});
  s.addShape('rect',{x:0.25,y:3.88,w:0.18,h:0.62,fill:{color:C.gold},line:{type:'none'}});
  s.addText('Jul Recovery Signal',{x:0.52,y:3.91,w:2.0,h:0.22,fontSize:9,bold:true,color:C.gold,fontFace:'Calibri',margin:0});
  s.addText('MT conversion stabilised at 72.2% after Jun dip  ·  Derma Co. Face Cleanser +47.6% MoM (₹4.83→₹7.13 Cr)  ·  Shampoo holds steady at ₹6.95 Cr  ·  North+East gap = ₹7.97 Cr recoverable',
    {x:0.52,y:4.12,w:9.1,h:0.28,fontSize:9,color:'B8CADF',fontFace:'Calibri',align:'left',margin:0});

  s.addText('Source: mt_price_volume.json + july_mt_channel_split.json + july_mt_chart_series.json · pipeline v2.4.0 · 2026-08-19',
    {x:0.25,y:4.9,w:9.5,h:0.2,fontSize:7,color:'4A6080',fontFace:'Calibri',italic:true,align:'left',margin:0});
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 2 · Channel Performance Matrix
// ═══════════════════════════════════════════════════════════════════════════════
{
  const s=pres.addSlide();
  hdr(s,'Channel Performance Matrix — July 2026','MT · eB2B (FSN/Nykaa) · SIS  ·  Primary, Offtake, Conversion %  ·  Monthly trend Apr–Jul',false);

  // 3 channel KPI cards
  const channels=[
    {name:'Modern Trade (MT)', pri:'₹47.02 Cr', off:'₹33.96 Cr', conv:'72.2%', share:'94.1%', shareN:94.1, gap:'₹13.06 Cr', col:C.navy},
    {name:'eB2B (FSN/Nykaa)',  pri:'₹2.20 Cr',  off:'₹2.07 Cr',  conv:'93.9%', share:'5.7%',  shareN:5.7,  gap:'₹0.13 Cr', col:C.teal},
    {name:'SIS',               pri:'—',          off:'₹0.03 Cr',  conv:'—',     share:'0.1%',  shareN:0.1,  gap:'—',        col:C.muted},
  ];
  channels.forEach((ch,i)=>{
    const x=0.28+i*3.24, y=1.06;
    s.addShape('rect',{x,y,w:3.0,h:2.2,fill:{color:i===0?C.midnavy:'FFFFFF'},
      line:{color:C.lgray,pt:1},shadow:{type:'outer',blur:3,offset:1,angle:45,color:'8E8E8E'}});
    const fg=i===0?C.white:C.ink, sf=i===0?'8EAACF':C.muted;
    s.addText(ch.name,{x:x+0.12,y:y+0.1,w:2.76,h:0.28,fontSize:10.5,bold:true,color:i===0?C.gold:C.ink,fontFace:'Calibri',margin:0});
    shareBar(s,x+0.12,y+0.42,2.4,ch.shareN,ch.col);
    s.addText(ch.share+' of total offtake',{x:x+0.12,y:y+0.62,w:2.76,h:0.22,fontSize:8.5,color:sf,fontFace:'Calibri',margin:0});
    const rows=[['Primary',ch.pri],['Offtake',ch.off],['Conv %',ch.conv],['Gap',ch.gap]];
    rows.forEach(([k,v],ri)=>{
      s.addText(k+':',{x:x+0.12,y:y+0.88+ri*0.3,w:0.85,h:0.26,fontSize:9.5,color:sf,fontFace:'Calibri',margin:0});
      s.addText(v,{x:x+0.95,y:y+0.88+ri*0.3,w:1.88,h:0.26,fontSize:9.5,bold:true,color:k==='Conv %'?convColor(parseFloat(v)):fg,fontFace:'Calibri',margin:0});
    });
  });

  // Monthly offtake trend chart (MT)
  s.addText('MT Monthly Offtake Trend (₹ Cr)',{x:0.28,y:3.36,w:5.5,h:0.24,fontSize:9.5,bold:true,color:C.ink,fontFace:'Calibri',margin:0});
  s.addChart(pres.ChartType.bar,[
    {name:'MT Offtake (₹ Cr)',labels:monthly.labels,values:monthly.nsv}
  ],{
    x:0.28,y:3.62,w:5.5,h:1.6,
    barDir:'col',chartColors:[C.midnavy,C.blue,C.teal,C.navy],
    showValue:true,dataLabelFontSize:10,dataLabelPosition:'inEnd',dataLabelColor:C.white,
    catAxisLabelFontSize:9,catAxisLabelColor:C.ink,valAxisHidden:true,
    catGridLine:{style:'none'},valGridLine:{style:'none'},showLegend:false,
    chartArea:{fill:{color:C.bg}},plotArea:{fill:{color:C.bg}},showTitle:false,
  });

  // eB2B trend line
  s.addText('eB2B Monthly Trend (₹ Cr) — Jan to Jul',{x:6.0,y:3.36,w:3.7,h:0.24,fontSize:9.5,bold:true,color:C.ink,fontFace:'Calibri',margin:0});
  s.addChart(pres.ChartType.line,[
    {name:'eB2B Offtake',labels:eb2bMonthly.labels,values:eb2bMonthly.vals}
  ],{
    x:6.0,y:3.62,w:3.72,h:1.6,
    chartColors:[C.teal],lineSize:2.5,
    showValue:false,
    catAxisLabelFontSize:9,catAxisLabelColor:C.ink,valAxisHidden:false,valAxisLabelFontSize:8,
    catGridLine:{style:'none'},valGridLine:{color:'E0E0E0',size:0.5},showLegend:false,
    chartArea:{fill:{color:C.bg}},plotArea:{fill:{color:C.bg}},showTitle:false,
  });

  s.addText('Inventory rebalancing story: MT primary ₹47.02 Cr vs offtake ₹33.96 Cr → ₹13.06 Cr pipeline in trade. Monitor Reliance (₹7.60 Cr gap) and DMart (₹4.28 Cr gap) DOI vs plan.',
    {x:0.28,y:5.25,w:9.44,h:0.25,fontSize:7.5,color:'5A7090',fontFace:'Calibri',italic:true,align:'left',margin:0});
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 3 · MT Market Share Review
// ═══════════════════════════════════════════════════════════════════════════════
{
  const s=pres.addSlide();
  hdr(s,'MT Market Share Review — July 2026','Nielsen/Internal WD data · Face Wash value share · Shampoo value share · WD / L3M / SoG metrics',true);

  // Face Wash panel
  s.addShape('rect',{x:0.28,y:1.05,w:4.5,h:3.62,fill:{color:C.midnavy},line:{type:'none'}});
  s.addText('Face Wash — Value Share %',{x:0.38,y:1.12,w:4.3,h:0.3,fontSize:11,bold:true,color:C.gold,fontFace:'Calibri',margin:0});

  s.addChart(pres.ChartType.bar,[
    {name:'Value share (%)',labels:mktShare.faceWash.map(r=>r.brand),values:mktShare.faceWash.map(r=>r.share)}
  ],{
    x:0.35,y:1.45,w:4.3,h:1.9,
    barDir:'bar',chartColors:[C.muted,C.muted,C.muted,C.gold],
    showValue:true,dataLabelFontSize:10,dataLabelPosition:'inEnd',dataLabelColor:C.white,
    catAxisLabelFontSize:10,catAxisLabelColor:C.white,valAxisHidden:true,
    catGridLine:{style:'none'},valGridLine:{style:'none'},showLegend:false,
    chartArea:{fill:{color:C.midnavy}},plotArea:{fill:{color:C.midnavy}},showTitle:false,
  });

  // Face wash metric chips
  const fwMetrics=[['Rank','#4'],['SoG','10.5%'],['+YoY','+1.2pp'],['#1 Gap','−12.1pp']];
  fwMetrics.forEach(([k,v],i)=>{
    const x=0.38+i*1.08, y=3.38;
    s.addShape('rect',{x,y,w:1.0,h:0.55,fill:{color:'162B4A'},line:{type:'none'}});
    s.addText(v,{x,y:y+0.04,w:1.0,h:0.28,fontSize:13,bold:true,color:i===2?C.pos:i===3?C.neg:C.gold,fontFace:'Cambria',align:'center',margin:0});
    s.addText(k,{x,y:y+0.32,w:1.0,h:0.2,fontSize:8,color:'8EAACF',fontFace:'Calibri',align:'center',margin:0});
  });

  s.addText('Himalaya losing −1.6pp YoY. Mamaearth gaining +1.2pp → opportunity to close gap through Q2 activation.',
    {x:0.38,y:4.0,w:4.3,h:0.5,fontSize:8.5,color:'8EAACF',fontFace:'Calibri',italic:true,align:'left',margin:0});

  // Shampoo panel
  s.addShape('rect',{x:5.0,y:1.05,w:4.72,h:3.62,fill:{color:C.bg},line:{color:C.lgray,pt:1}});
  s.addText('Shampoo — Value Share %',{x:5.1,y:1.12,w:4.5,h:0.3,fontSize:11,bold:true,color:C.ink,fontFace:'Calibri',margin:0});

  s.addChart(pres.ChartType.bar,[
    {name:'Value share (%)',labels:mktShare.shampoo.map(r=>r.brand),values:mktShare.shampoo.map(r=>r.share)}
  ],{
    x:5.08,y:1.45,w:4.56,h:1.5,
    barDir:'bar',chartColors:[C.muted,C.muted,C.teal],
    showValue:true,dataLabelFontSize:10,dataLabelPosition:'inEnd',dataLabelColor:C.white,
    catAxisLabelFontSize:10,catAxisLabelColor:C.ink,valAxisHidden:true,
    catGridLine:{style:'none'},valGridLine:{style:'none'},showLegend:false,
    chartArea:{fill:{color:C.bg}},plotArea:{fill:{color:C.bg}},showTitle:false,
  });

  const shMetrics=[['Rank','#7'],['Share','3.7%'],['L3M Δ','+0.3pp'],['Gap #1','−12.9pp']];
  shMetrics.forEach(([k,v],i)=>{
    const x=5.08+i*1.14, y=3.05;
    s.addShape('rect',{x,y,w:1.07,h:0.55,fill:{color:C.white},line:{color:C.lgray,pt:1}});
    s.addText(v,{x,y:y+0.04,w:1.07,h:0.28,fontSize:13,bold:true,color:i===2?C.pos:i===3?C.neg:C.ink,fontFace:'Cambria',align:'center',margin:0});
    s.addText(k,{x,y:y+0.32,w:1.07,h:0.2,fontSize:8,color:C.muted,fontFace:'Calibri',align:'center',margin:0});
  });

  // Tier 3 badge for Jul market share
  s.addShape('rect',{x:5.08,y:3.7,w:4.56,h:0.72,fill:{color:'FEF9E7'},line:{color:'F0C040',pt:1}});
  s.addText('⚠  Jul Market Share data pending Nielsen full-month file.\nL3M directional shown. WD expansion focus: target +200 stores West & South-1 in Q2.',
    {x:5.14,y:3.74,w:4.4,h:0.62,fontSize:8.5,color:'7A5C00',fontFace:'Calibri',margin:0});

  s.addText('Nielsen L3M · WD = Weighted Distribution · SoG = Share of Growth · L3M = Last 3 months rolling average · Internal source for WD data.',
    {x:0.28,y:4.97,w:9.44,h:0.2,fontSize:7,color:'5A7090',fontFace:'Calibri',italic:true,margin:0});
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 4 · Brand Portfolio Dynamics
// ═══════════════════════════════════════════════════════════════════════════════
{
  const s=pres.addSlide();
  hdr(s,'Brand Portfolio Dynamics — July 2026','Primary & Offtake ₹ Cr · Category trends Feb–Jul · Emerging brand momentum',false);

  // Anchor brand cards
  const anchors=[
    {
      brand:'Mamaearth', share:'66.0%', primary:33.38, offtake:24.49, conv:73.4,
      topCat:'Face Cleanser', topVal:8.53, topTrend:'↑ peak May ₹9.63 → Jul ₹8.53 (−12% MoM seasonality)',
      cat2:'Shampoo', val2:6.95, trend2:'↑ steady growth ₹4.81→₹6.95 (+44% in 5M)',
      cat3:'Sun Care', val3:1.30, trend3:'↓ post-season dip from peak ₹3.10 Apr',
      col:C.navy,
    },
    {
      brand:'The Derma Co.', share:'29.7%', primary:15.19, offtake:11.03, conv:72.6,
      topCat:'Face Cleanser', topVal:7.13, topTrend:'🚀 +217% in 5M (Feb ₹2.25→Jul ₹7.13) — Fastest growing',
      cat2:'Sun Care', val2:1.99, trend2:'Peak May ₹3.18 → Jul ₹1.99 (post-season)',
      cat3:'Face Serum', val3:0.63, trend3:'Stable ₹0.56–₹0.69 range, hold strategy',
      col:C.teal,
    },
  ];
  anchors.forEach((b,i)=>{
    const x=0.28+i*4.88, y=1.04;
    s.addShape('rect',{x,y,w:4.64,h:3.38,fill:{color:i===0?C.midnavy:'FFFFFF'},line:{color:C.lgray,pt:1}});
    const fg=i===0?C.white:C.ink, sf=i===0?'8EAACF':C.muted;
    s.addText(b.brand,{x:x+0.14,y:y+0.1,w:3.0,h:0.3,fontSize:13,bold:true,color:i===0?C.gold:C.teal,fontFace:'Cambria',margin:0});
    s.addText(b.share+' brand share',{x:x+3.1,y:y+0.1,w:1.4,h:0.3,fontSize:10,bold:true,color:fg,fontFace:'Calibri',align:'right',margin:0});

    // Mini KPIs
    [['Primary',b.primary],['Offtake',b.offtake],['Conv',b.conv+'%']].forEach(([k,v],ki)=>{
      const kx=x+0.14+ki*1.5;
      s.addShape('rect',{x:kx,y:y+0.44,w:1.38,h:0.55,fill:{color:i===0?'162B4A':C.bg},line:{type:'none'}});
      s.addText('₹'+v,{x:kx,y:y+0.48,w:1.38,h:0.28,fontSize:13,bold:true,color:ki===2?convColor(b.conv):fg,fontFace:'Cambria',align:'center',margin:0});
      s.addText(k,{x:kx,y:y+0.76,w:1.38,h:0.18,fontSize:8,color:sf,fontFace:'Calibri',align:'center',margin:0});
    });

    // Category breakdown
    [[b.topCat,b.topVal,b.topTrend],[b.cat2,b.val2,b.trend2],[b.cat3,b.val3,b.trend3]].forEach(([cat,val,trend],ci)=>{
      const cy=y+1.08+ci*0.72;
      s.addShape('rect',{x:x+0.14,y:cy,w:4.36,h:0.68,fill:{color:i===0?'162B4A':'F8F9FC'},line:{type:'none'}});
      s.addText(cat+' — ₹'+val.toFixed(2)+' Cr',{x:x+0.22,y:cy+0.06,w:4.18,h:0.26,fontSize:10,bold:true,color:ci===0?(i===0?C.gold:C.teal):fg,fontFace:'Calibri',margin:0});
      s.addText(trend,{x:x+0.22,y:cy+0.34,w:4.18,h:0.26,fontSize:8.5,color:sf,fontFace:'Calibri',italic:true,margin:0});
    });
  });

  // Emerging brands row
  s.addText('Emerging Brands — July Offtake',{x:0.28,y:4.52,w:4.0,h:0.24,fontSize:9,bold:true,color:C.ink,fontFace:'Calibri',margin:0});
  const emerging=[
    {b:'Aqualogica',off:'₹0.48 Cr',note:'OFT > Primary — demand pull signal'},
    {b:'BBlunt',    off:'₹0.06 Cr',note:'Low conv — assortment review needed'},
    {b:"Dr. Sheth's",off:'₹0.03 Cr',note:'Zero primary — monitor billing start'},
  ];
  emerging.forEach((e,i)=>{
    const x=0.28+i*3.24;
    s.addShape('rect',{x,y:4.78,w:3.0,h:0.58,fill:{color:C.bg},line:{color:C.lgray,pt:1}});
    s.addText(e.b,{x:x+0.1,y:4.82,w:2.8,h:0.24,fontSize:10,bold:true,color:C.ink,fontFace:'Calibri',margin:0});
    s.addText(e.off+' · '+e.note,{x:x+0.1,y:5.06,w:2.8,h:0.22,fontSize:8,color:C.muted,fontFace:'Calibri',italic:true,margin:0});
  });

  // Portfolio share bar
  s.addText('Portfolio offtake share:',{x:9.6,y:4.52,w:0,h:0}); // placeholder position
  const portData=[{b:'MH',pct:66,col:C.navy},{b:'DC',pct:29.7,col:C.teal},{b:'Aq',pct:1.3,col:C.gold},{b:'Other',pct:3,col:C.lgray}];
  let bx=0.28;
  const totalW=9.44;
  portData.forEach(p=>{
    const w=totalW*(p.pct/100);
    s.addShape('rect',{x:bx,y:4.55,w:w,h:0.18,fill:{color:p.col},line:{type:'none'}});
    if(w>0.4) s.addText(p.b,{x:bx+0.04,y:4.55,w:w-0.06,h:0.18,fontSize:7.5,bold:true,color:C.white,fontFace:'Calibri',align:'center',margin:0});
    bx+=w;
  });
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 5 · Focus Category Analysis
// ═══════════════════════════════════════════════════════════════════════════════
{
  const s=pres.addSlide();
  hdr(s,'Focus Category Analysis — July 2026','Honasa MT offtake by category ₹ Cr  ·  6-month trend Feb–Jul  ·  MoM and 5-month CAGR',true);

  // Honasa category totals Jul (MH + DC)
  const cats=[
    {cat:'Face Cleanser', jul:15.66, mh:8.53, dc:7.13, trend:'↑ MH −12% MoM seasonal; DC +47.6% MoM — structural shift'},
    {cat:'Shampoo',       jul: 6.95, mh:6.95, dc:0.00, trend:'↑ MH steady growth +44% vs Feb; DC not in category'},
    {cat:'Sun Care',      jul: 3.29, mh:1.30, dc:1.99, trend:'↓ Post-season dip both brands; Apr–May peak period ended'},
    {cat:'Face Serum',    jul: 0.63, mh:0.00, dc:0.63, trend:'→ Stable DC-only; no volume movement signal'},
    {cat:'Body Care*',    jul: 3.30, mh:3.30, dc:0.00, trend:'*Estimated residual from brand total; article-level TBD'},
  ];
  const maxV=16;

  // Horizontal bar chart
  s.addChart(pres.ChartType.bar,[
    {name:'Mamaearth (₹ Cr)',    labels:cats.map(c=>c.cat), values:cats.map(c=>c.mh)},
    {name:'The Derma Co. (₹ Cr)',labels:cats.map(c=>c.cat), values:cats.map(c=>c.dc)},
  ],{
    x:0.28,y:1.06,w:5.6,h:3.6,
    barDir:'bar',barGrouping:'stacked',
    chartColors:[C.navy,C.teal],
    showValue:true,dataLabelFontSize:9,dataLabelPosition:'ctr',dataLabelColor:C.white,
    catAxisLabelFontSize:10,catAxisLabelColor:C.white,valAxisHidden:true,
    catGridLine:{style:'none'},valGridLine:{style:'none'},
    showLegend:true,legendPos:'b',legendFontSize:10,legendColor:C.white,
    chartArea:{fill:{color:C.navy}},plotArea:{fill:{color:C.navy}},showTitle:false,
  });

  // Data table right side
  s.addShape('rect',{x:6.05,y:1.06,w:3.67,h:0.38,fill:{color:'162B4A'},line:{type:'none'}});
  ['Category','Jul ₹Cr','5M CAGR'].forEach((h,i)=>{
    s.addText(h,{x:6.1+i*1.15,y:1.1,w:1.1,h:0.28,fontSize:9,bold:true,color:C.white,fontFace:'Calibri',align:i===0?'left':'center',margin:0});
  });

  // 5-month CAGR estimates
  const cagr=['+14.7%','+7.5%','−12.4%','0%','—'];
  cats.forEach((c,i)=>{
    const ry=1.44+i*0.62;
    const bg=i%2===0?C.midnavy:'162B4A';
    s.addShape('rect',{x:6.05,y:ry,w:3.67,h:0.6,fill:{color:bg},line:{type:'none'}});
    s.addText(c.cat,{x:6.1,y:ry+0.15,w:1.1,h:0.28,fontSize:9,bold:true,color:C.white,fontFace:'Calibri',margin:0});
    s.addText('₹'+c.jul.toFixed(2),{x:7.22,y:ry+0.15,w:1.1,h:0.28,fontSize:10,bold:true,color:C.gold,fontFace:'Calibri',align:'center',margin:0});
    const cagrC=cagr[i].startsWith('+')?C.pos:cagr[i].startsWith('−')?C.neg:C.muted;
    s.addText(cagr[i],{x:8.35,y:ry+0.15,w:1.1,h:0.28,fontSize:10,bold:true,color:cagrC,fontFace:'Calibri',align:'center',margin:0});
    s.addText(c.trend,{x:6.1,y:ry+0.38,w:3.55,h:0.2,fontSize:7.5,color:'8EAACF',fontFace:'Calibri',italic:true,margin:0});
  });

  // Face Cleanser leadership callout
  s.addShape('rect',{x:0.28,y:4.76,w:9.44,h:0.42,fill:{color:C.gold},line:{type:'none'}});
  s.addText('★  Face Cleanser is the growth engine: Honasa ₹15.66 Cr Jul (+47.6% DC MoM surge). Protect MH share; accelerate DC distribution to White-space outlets in West & North.',
    {x:0.38,y:4.8,w:9.24,h:0.3,fontSize:9.5,bold:true,color:C.navy,fontFace:'Calibri',margin:0});
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 6 · Zonal Performance
// ═══════════════════════════════════════════════════════════════════════════════
{
  const s=pres.addSlide();
  hdr(s,'Zonal Performance — July 2026 & FYTD','Jul NSV ₹ Cr · Units · ASP Index · Conv % · FYTD YoY%  ·  Sorted by Jul NSV (descending)',false);

  // Zone cards (3 + 3 layout)
  const sortedZ=[...julZones].sort((a,b)=>b.nsv-a.nsv);
  sortedZ.forEach((z,i)=>{
    const col=i<2?0:i<4?1:2;
    const row=i<3?0:1;
    const x=0.28+col*3.25, y=1.05+row*2.22;
    const fytdZ=fytdZones.find(f=>f.zone===z.zone);
    const dark=i===0||i===2;
    s.addShape('rect',{x,y,w:3.08,h:2.1,fill:{color:dark?C.midnavy:'F8F9FC'},line:{color:C.lgray,pt:1}});
    const fg=dark?C.white:C.ink, sf=dark?'8EAACF':C.muted;

    // Zone header
    s.addText(z.zone,{x:x+0.12,y:y+0.08,w:2.0,h:0.3,fontSize:13,bold:true,color:dark?C.gold:C.navy,fontFace:'Cambria',margin:0});
    // Conv badge
    s.addShape('rect',{x:x+2.15,y:y+0.1,w:0.82,h:0.28,fill:{color:convColor(z.conv)},line:{type:'none'}});
    s.addText(z.conv+'%',{x:x+2.15,y:y+0.12,w:0.82,h:0.22,fontSize:9,bold:true,color:C.white,fontFace:'Calibri',align:'center',margin:0});

    // NSV big number
    s.addText('₹'+z.nsv.toFixed(2)+' Cr',{x:x+0.12,y:y+0.42,w:1.8,h:0.4,fontSize:18,bold:true,color:dark?C.white:C.ink,fontFace:'Cambria',margin:0});
    s.addText('Jul offtake',{x:x+0.12,y:y+0.82,w:1.8,h:0.2,fontSize:7.5,color:sf,fontFace:'Calibri',margin:0});

    // Stats row
    const stats=[
      [(z.units/100000).toFixed(1)+'L','Units'],
      ['₹'+z.asp.toFixed(0),'ASP'],
      [z.aspIdx,'ASP Idx'],
    ];
    stats.forEach(([v,k],si)=>{
      const sx=x+0.12+si*0.95;
      s.addText(v,{x:sx,y:y+1.06,w:0.9,h:0.26,fontSize:10,bold:true,color:si===2?(z.aspIdx>=100?C.pos:z.aspIdx>=95?C.amber:C.neg):fg,fontFace:'Calibri',align:'center',margin:0});
      s.addText(k,{x:sx,y:y+1.32,w:0.9,h:0.18,fontSize:7.5,color:sf,fontFace:'Calibri',align:'center',margin:0});
    });

    // FYTD & YoY
    if(fytdZ){
      s.addShape('rect',{x:x+0.12,y:y+1.56,w:2.84,h:0.42,fill:{color:dark?'162B4A':'EBEBEB'},line:{type:'none'}});
      s.addText('FYTD ₹'+(fytdZ.fy27/100).toFixed(1)+'L',{x:x+0.18,y:y+1.6,w:1.5,h:0.28,fontSize:9.5,bold:true,color:fg,fontFace:'Calibri',margin:0});
      if(fytdZ.yoy!=null)
        s.addText('+'+fytdZ.yoy.toFixed(1)+'% YoY',{x:x+1.7,y:y+1.6,w:1.1,h:0.28,fontSize:9.5,bold:true,color:yoyColor(fytdZ.yoy),fontFace:'Calibri',align:'right',margin:0});
      else
        s.addText('NEW',{x:x+1.7,y:y+1.6,w:1.1,h:0.28,fontSize:9.5,bold:true,color:C.gold,fontFace:'Calibri',align:'right',margin:0});
    }
  });

  // Column chart of FYTD
  s.addChart(pres.ChartType.bar,[
    {name:"FY'26-27 FYTD (₹L)",labels:fytdZones.filter(f=>f.zone!=='Pan India (eB2B)').sort((a,b)=>b.fy27-a.fy27).map(z=>z.zone),
      values:fytdZones.filter(f=>f.zone!=='Pan India (eB2B)').sort((a,b)=>b.fy27-a.fy27).map(z=>z.fy27)}
  ],{
    x:0.28,y:3.3,w:9.44,h:1.45,
    barDir:'col',barGrouping:'clustered',
    chartColors:[C.navy,C.teal,C.blue,C.gold,C.amber,C.muted],
    showValue:true,dataLabelFontSize:8.5,dataLabelPosition:'inEnd',dataLabelColor:C.white,
    catAxisLabelFontSize:9,catAxisLabelColor:C.ink,valAxisHidden:true,
    catGridLine:{style:'none'},valGridLine:{style:'none'},showLegend:false,
    chartArea:{fill:{color:C.bg}},plotArea:{fill:{color:C.bg}},showTitle:false,
  });

  s.addText('South-1 is the velocity leader (highest conv 86.3%). North leads FYTD volume (+62.4% YoY) but lags on conversion. East requires structural fix: Conv 49.9% = demand or DOI issue.',
    {x:0.28,y:4.82,w:9.44,h:0.26,fontSize:7.5,color:'5A7090',fontFace:'Calibri',italic:true,margin:0});
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 7 · Shopper Activation & Strategic Priorities
// ═══════════════════════════════════════════════════════════════════════════════
{
  const s=pres.addSlide();
  hdr(s,'Shopper Activation & Strategic Priorities — Q2 FY\'26-27','4 action blocks · Pack-size strategy · Merchandising execution',true);

  const priorities=[
    {
      n:'01', col:C.neg, title:'Fix North & East Conversion  ·  ₹7.97 Cr Gap',
      bullets:[
        'North 61.3% / East 49.9% — DOI check first; OOS or scheme pullback likely cause.',
        'NKAM action: reactivate listing in stores billing zero; push next primary order.',
        'Trade Marketing: run 2-week visibility drive (shelf + gondola ends) in both zones.',
        'Target: bring both zones to ≥72% conversion (MT average) by Aug-26. Owner: RKAM + TM.',
      ],
    },
    {
      n:'02', col:C.gold, title:"Protect Mamaearth Face Cleanser + Scale Derma Co.",
      bullets:[
        'MH Face Cleanser: −12% MoM (₹9.65→₹8.53). Seasonality vs distribution — verify active stores.',
        "DC Face Cleanser: +47.6% MoM (₹4.83→₹7.13 Cr) — fastest growing SKU in portfolio.",
        'Strategy: Defend MH shelf position; expand DC to 500+ new outlets in North & South-2.',
        'Action: Category team to file planogram update for DC in all top-20 chains. Owner: Cat + KAM.',
      ],
    },
    {
      n:'03', col:C.teal, title:'Reliance Conversion Recovery  ·  ₹7.60 Cr Gap',
      bullets:[
        'Reliance primary ₹15.66 Cr vs offtake ₹8.06 Cr = 51.5% conv — worst account.',
        "Pipeline risk: ₹7.60 Cr loaded into Reliance but not selling. Ageing stock / scheme mismatch.",
        'Action: NKAM + Supply to conduct full DOI audit at Reliance stores by 31-Aug.',
        'Trade Marketing to propose mid-shelf activation for Aug to clear excess inventory.',
      ],
    },
    {
      n:'04', col:C.pos, title:'Pack-Size & Premiumisation — ASP ₹179.2 (+4.4% YoY)',
      bullets:[
        'East ASP Index 108, South-1 105 — premium mix holding strong in high-ASP zones.',
        'West ASP Index 93 — check if large packs (150ml+) are being replaced by smaller SKUs.',
        'Shampoo: grow ₹6.95 Cr base by introducing 400ml/700ml in North & South-1 high-ASP doors.',
        'Target: overall ASP ₹182+ by Oct-26 through pack-size mix shift. Owner: Category.',
      ],
    },
  ];

  priorities.forEach((p,i)=>{
    const y=1.06+i*1.05;
    s.addShape('rect',{x:0.28,y,w:9.44,h:0.98,fill:{color:C.midnavy},line:{type:'none'}});
    s.addShape('rect',{x:0.28,y,w:0.5,h:0.98,fill:{color:p.col},line:{type:'none'}});
    s.addText(p.n,{x:0.28,y:y+0.32,w:0.5,h:0.32,fontSize:13,bold:true,color:C.white,fontFace:'Cambria',align:'center',margin:0});
    s.addText(p.title,{x:0.85,y:y+0.06,w:8.8,h:0.28,fontSize:11,bold:true,color:p.col===C.gold?C.gold:C.white,fontFace:'Calibri',margin:0});
    p.bullets.forEach((b,bi)=>{
      s.addText('·  '+b,{x:0.92,y:y+0.35+bi*0.15,w:8.7,h:0.15,fontSize:8.5,color:'B8CADF',fontFace:'Calibri',margin:0});
    });
  });

  // Merchandising execution strip
  s.addShape('rect',{x:0.28,y:5.22,w:9.44,h:0.32,fill:{color:'0A1628'},line:{type:'none'}});
  s.addText('Merchandising: Gondola ends → Face Cleanser & Shampoo prioritised  ·  Off-shelf display → Derma Co. for West & South-1  ·  Digital shelf: Ensure 4+ images + A+ on FSN/Nykaa top SKUs',
    {x:0.38,y:5.25,w:9.24,h:0.24,fontSize:8,color:C.gold,fontFace:'Calibri',margin:0});
}

// ═══════════════════════════════════════════════════════════════════════════════
// SLIDE 8 · Additional Insights & Forward Signals
// ═══════════════════════════════════════════════════════════════════════════════
{
  const s=pres.addSlide();
  hdr(s,'Additional Insights & Forward Signals — July 2026','ASP premiumisation · eB2B deep dive · Derma Co. spike analysis · 5 forward signals',false);

  // ASP premiumisation timeline
  s.addShape('rect',{x:0.28,y:1.05,w:4.55,h:1.5,fill:{color:C.white},line:{color:C.lgray,pt:1}});
  s.addText('ASP Premiumisation Trend (₹)',{x:0.38,y:1.1,w:4.3,h:0.26,fontSize:10,bold:true,color:C.ink,fontFace:'Calibri',margin:0});
  const aspData=[{m:'Apr',v:171.7},{m:'May',v:173.5},{m:'Jun',v:null},{m:'Jul',v:179.2}];
  aspData.forEach((a,i)=>{
    const x=0.42+i*1.08;
    s.addShape('rect',{x,y:1.42+(a.v!=null?(179.2-a.v)/20*0.55:0.55),w:0.9,h:a.v!=null?(a.v-170)/20*0.55:0.1,
      fill:{color:a.v!=null?C.blue:C.lgray},line:{type:'none'}});
    s.addText(a.v!=null?'₹'+a.v:'—',{x,y:1.38,w:0.9,h:0.2,fontSize:8.5,bold:true,color:a.v!=null?C.teal:C.muted,fontFace:'Calibri',align:'center',margin:0});
    s.addText(a.m,{x,y:2.02,w:0.9,h:0.2,fontSize:8,color:C.muted,fontFace:'Calibri',align:'center',margin:0});
  });
  s.addText('+4.4% Apr→Jul · Realisation stable 41.6–42.9%',{x:0.38,y:2.26,w:4.3,h:0.22,fontSize:8.5,color:C.pos,bold:true,fontFace:'Calibri',margin:0});

  // eB2B trend analysis
  s.addShape('rect',{x:5.02,y:1.05,w:4.7,h:1.5,fill:{color:C.white},line:{color:C.lgray,pt:1}});
  s.addText('eB2B (FSN/Nykaa) Trend — Jan to Jul ₹ Cr',{x:5.12,y:1.1,w:4.5,h:0.26,fontSize:10,bold:true,color:C.ink,fontFace:'Calibri',margin:0});
  s.addChart(pres.ChartType.line,[
    {name:'eB2B Offtake',labels:eb2bMonthly.labels,values:eb2bMonthly.vals}
  ],{
    x:5.08,y:1.32,w:4.56,h:1.18,
    chartColors:[C.teal],lineSize:2.5,
    showValue:true,dataLabelFontSize:8,dataLabelPosition:'t',
    catAxisLabelFontSize:8,catAxisLabelColor:C.ink,valAxisHidden:true,
    catGridLine:{style:'none'},valGridLine:{style:'none'},showLegend:false,
    chartArea:{fill:{color:'F8F9FC'}},plotArea:{fill:{color:'F8F9FC'}},showTitle:false,
  });

  // Derma Co. Face Cleanser spike analysis
  s.addShape('rect',{x:0.28,y:2.64,w:4.55,h:2.06,fill:{color:C.midnavy},line:{type:'none'}});
  s.addText('🚀 Derma Co. Face Cleanser — Structural Growth Story',{x:0.38,y:2.7,w:4.35,h:0.3,fontSize:10,bold:true,color:C.gold,fontFace:'Calibri',margin:0});
  const dcFC=[2.25,2.75,3.24,4.63,4.83,7.13];
  const dcFClabs=['Feb','Mar','Apr','May','Jun','Jul'];
  s.addChart(pres.ChartType.line,[
    {name:'DC Face Cleanser',labels:dcFClabs,values:dcFC}
  ],{
    x:0.32,y:3.02,w:2.8,h:1.38,
    chartColors:[C.gold],lineSize:3,
    showValue:true,dataLabelFontSize:8,dataLabelPosition:'t',dataLabelColor:C.white,
    catAxisLabelFontSize:8,catAxisLabelColor:C.white,valAxisHidden:true,
    catGridLine:{style:'none'},valGridLine:{style:'none'},showLegend:false,
    chartArea:{fill:{color:C.midnavy}},plotArea:{fill:{color:C.midnavy}},showTitle:false,
  });
  s.addText('+217% in 5M\nFeb ₹2.25→Jul ₹7.13\nNow = MH Face Cleanser 83%',
    {x:3.2,y:3.02,w:1.55,h:1.38,fontSize:11,bold:true,color:C.gold,fontFace:'Cambria',align:'center',margin:0});

  // 5 Forward signals
  s.addShape('rect',{x:5.02,y:2.64,w:4.7,h:2.06,fill:{color:C.bg},line:{color:C.lgray,pt:1}});
  s.addText('5 Forward-Looking Signals for Aug-Sep',{x:5.12,y:2.7,w:4.5,h:0.28,fontSize:10,bold:true,color:C.ink,fontFace:'Calibri',margin:0});
  const signals=[
    {ic:'1',col:C.neg,   txt:'North+East conv <62% → OOS/scheme fix must close before Sep planning'},
    {ic:'2',col:C.pos,   txt:'DC Face Cleanser trajectory → ₹8–9 Cr possible in Aug if listings expand'},
    {ic:'3',col:C.amber, txt:'Reliance DOI risk → audit needed before Sep primary loading starts'},
    {ic:'4',col:C.teal,  txt:'Shampoo ₹6.95 Cr steady → 400ml introduction to push ASP above ₹185'},
    {ic:'5',col:C.blue,  txt:'eB2B Active EANs 198 (vs peak 222 Jan) → relist top-20 delisted SKUs'},
  ];
  signals.forEach((sg,i)=>{
    s.addShape('rect',{x:5.12,y:3.02+i*0.38,w:0.26,h:0.3,fill:{color:sg.col},line:{type:'none'}});
    s.addText(sg.ic,{x:5.12,y:3.04+i*0.38,w:0.26,h:0.26,fontSize:8.5,bold:true,color:C.white,fontFace:'Cambria',align:'center',margin:0});
    s.addText(sg.txt,{x:5.44,y:3.04+i*0.38,w:4.2,h:0.3,fontSize:8.5,color:C.ink,fontFace:'Calibri',margin:0});
  });

  // Account gap summary
  s.addShape('rect',{x:0.28,y:4.78,w:9.44,h:0.42,fill:{color:'0A1628'},line:{type:'none'}});
  s.addText('Account Gaps: Reliance ₹7.60 Cr (51.5% conv)  ·  DMart ₹4.28 Cr (76.5% conv)  ·  Metro ₹1.35 Cr (26.6% conv)  ·  Total recoverable above 25% floor: ₹6.22 Cr',
    {x:0.38,y:4.82,w:9.24,h:0.3,fontSize:8.5,bold:true,color:C.gold,fontFace:'Calibri',margin:0});

  s.addText('Sources: mt_price_volume.json · july_mt_channel_split.json · july_mt_chart_series.json (pipeline v2.4.0) · eB2B Active EANs from chart series "11" · Account gaps from chart series "16"',
    {x:0.28,y:5.27,w:9.44,h:0.2,fontSize:7,color:'5A7090',fontFace:'Calibri',italic:true,margin:0});
}

// ── Write ─────────────────────────────────────────────────────────────────────
pres.writeFile({fileName:'MT_Offtake_Jul26_DeepDive.pptx'})
  .then(()=>console.log('✓  MT_Offtake_Jul26_DeepDive.pptx written'))
  .catch(e=>{console.error(e);process.exit(1);});
