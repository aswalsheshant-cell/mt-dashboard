'use strict';
const PptxGenJS = require('pptxgenjs');
const pres = new PptxGenJS();
pres.layout = 'LAYOUT_WIDE';

const BG='0B1226',CARD='111D38',NAVY2='0F2040',NAVY3='162548';
const GOLD='C49A1A',GOLD2='D4AC1E',TEAL='1B7A6E';
const GREEN='27AE60',RED='C0392B',AMBER='E67E22';
const WHITE='FFFFFF',LGREY='B8C4D0',MGREY='6B7A8D';
const W=13.33,H=7.5,M=0.25,FTOP=6.88,FH=0.40,SRCY=7.33;
const SRC='Source: pipeline v2.4.0 · July Offtake + Primary.xlsb · Codex analysis · 2026-08-19';

const bg=s=>s.addShape(pres.ShapeType.rect,{x:0,y:0,w:W,h:H,fill:{color:BG},line:{type:'none'}});
const badge=(s,n)=>{
  s.addShape(pres.ShapeType.ellipse,{x:W-.77,y:.12,w:.55,h:.55,fill:{color:GOLD},line:{type:'none'}});
  s.addText(String(n).padStart(2,'0'),{x:W-.77,y:.12,w:.55,h:.55,fontSize:12,bold:true,color:WHITE,align:'center',valign:'middle',margin:0});
};
const hdr=(s,t,sub,opt={})=>{
  const{y=.10,fs=19}=opt;
  s.addText(t.toUpperCase(),{x:M,y,w:W-.90,h:.60,fontSize:fs,bold:true,color:WHITE,fontFace:'Calibri',valign:'middle',margin:0});
  if(sub) s.addText(sub,{x:M,y:y+.58,w:W-.90,h:.26,fontSize:9.5,color:LGREY,fontFace:'Calibri',valign:'middle',margin:0});
};
const kpi=(s,x,y,w,h,val,lbl,sub,c,vc)=>{
  s.addShape(pres.ShapeType.rect,{x,y,w,h,fill:{color:c||CARD},line:{color:GOLD,pt:.4}});
  const vH=sub?h*.42:h*.54;
  s.addText(val,{x:x+.06,y:y+.05,w:w-.12,h:vH,fontSize:w<1.8?16:21,bold:true,color:vc||WHITE,align:'center',valign:'bottom',margin:0,fontFace:'Calibri'});
  s.addText(lbl,{x:x+.06,y:y+vH+.04,w:w-.12,h:h*.27,fontSize:7.5,color:LGREY,align:'center',valign:'top',margin:0,fontFace:'Calibri'});
  if(sub) s.addText(sub,{x:x+.06,y:y+vH+h*.33,w:w-.12,h:h*.22,fontSize:7,color:GOLD2,align:'center',valign:'top',margin:0,fontFace:'Calibri'});
};
const sh=(s,x,y,w,h,txt,tc)=>{
  s.addShape(pres.ShapeType.rect,{x,y,w,h,fill:{color:GOLD},line:{type:'none'}});
  s.addText(txt,{x,y,w,h,fontSize:8.5,bold:true,color:tc||'000000',align:'center',valign:'middle',margin:0});
};
const ft=(s,src)=>{
  const ls=['EVIDENCE','IMPLICATION','ACTION','OWNER'],bgs=['0F2040','162548','0F2040','162548'];
  const fw=(W-2*M)/4;
  ls.forEach((l,i)=>{
    s.addShape(pres.ShapeType.rect,{x:M+i*fw,y:FTOP,w:fw,h:FH,fill:{color:bgs[i]},line:{color:GOLD,pt:.3}});
    s.addText(l,{x:M+i*fw,y:FTOP,w:fw,h:FH,fontSize:8,bold:true,color:GOLD,align:'center',valign:'middle',margin:0});
  });
  s.addText(src||SRC,{x:M,y:SRCY,w:W-2*M,h:.16,fontSize:7,color:MGREY,margin:0});
};
const bl=(s,x,y,w,h,items,opt={})=>{
  const{fs=9,col=LGREY}=opt;
  if(!items.length) return;
  s.addText(items.map((t,i)=>({text:t,options:{fontSize:fs,color:col,bullet:{type:'bullet',code:'25CF'},breakLine:i<items.length-1}})),
    {x,y,w,h,margin:[2,4,2,14],valign:'top',fontFace:'Calibri'});
};
const card=(s,x,y,w,h,c)=>s.addShape(pres.ShapeType.rect,{x,y,w,h,fill:{color:c||CARD},line:{color:NAVY2,pt:.3}});
const pill=(s,x,y,txt,c,tc)=>{
  s.addShape(pres.ShapeType.rect,{x,y,w:.55,h:.22,fill:{color:c||GREEN},line:{type:'none'}});
  s.addText(txt,{x,y,w:.55,h:.22,fontSize:7.5,bold:true,color:tc||WHITE,align:'center',valign:'middle',margin:0});
};
const signalColor=sig=>sig==='Scale'?GREEN:sig==='Recover'?RED:sig==='Protect'?TEAL:NAVY3;

// ── ZONE DATA ─────────────────────────────────────────────────────────────────
const ZONES=[
  {z:'West',  p:10.05,o:8.28,cv:82.3,g:1.78,act:'WATCH',rank:1,mx:'22.9%',
   states:['Maharashtra  ₹3.43 Cr','Gujarat  ₹2.57 Cr','Mumbai  ₹2.28 Cr'],
   top1:'DMart  ₹5.76 Cr',top2:'Reliance  ₹1.23 Cr',top3:'Wellness F…  ₹0.65 Cr',
   mhoft:'₹4.97 Cr',dcoft:'₹3.24 Cr',npi:'₹0.54 Cr',npipct:'6.6%',
   mhcat:['Face Cleanser  ₹2.39 Cr','Shampoo  ₹1.53 Cr','Sun Care  ₹0.22 Cr'],
   dccat:['Face Cleanser  ₹2.84 Cr','Sun Care  ₹0.55 Cr','Face Serum  ₹0.22 Cr'],
   priority:'DMart × hero-EAN availability',
   mhd:[[2.09,1.33,0.44],[2.45,1.55,1.03],[2.42,1.59,0.97],[2.73,1.64,0.81],[2.90,1.79,0.46],[2.39,1.53,0.22]],
   dcd:[[1.12,0.35,0.17],[1.33,0.66,0.17],[1.42,0.73,0.20],[2.04,1.07,0.17],[2.19,0.67,0.16],[2.84,0.55,0.22]],
   insights:['West delivers ₹8.28 Cr offtake, 22.9% of national value.',
     'Primary is ₹10.05 Cr versus ₹8.28 Cr offtake.','Flow conversion is 82.3% for July.',
     'The same-period flow gap is ₹1.78 Cr.','West ranks #1 by national offtake.',
     'Maharashtra ranks #1 with ₹3.43 Cr offtake.','Gujarat ranks #2 with ₹2.57 Cr offtake.',
     'Mumbai ranks #3 with ₹2.28 Cr offtake.','The leading state contributes 41.4% of zone offtake.',
     'The top three states contribute 100.0% of zone offtake.',
     'DMart: ₹5.76 Cr offtake; 94.2%.','Reliance: ₹1.23 Cr offtake; 54.5%.',
     'Wellness Forever: ₹0.65 Cr offtake; 134.9%.','The leading chain contributes 69.6% of zone offtake.',
     'The top three chains contribute 92.5% of zone offtake.']},
  {z:'South-1',p:9.80,o:8.19,cv:83.6,g:1.61,act:'WATCH',rank:2,mx:'22.7%',
   states:['Karnataka  ₹4.10 Cr','Tamil Nadu  ₹2.63 Cr','Kerala  ₹1.17 Cr'],
   top1:'Apollo  ₹2.84 Cr',top2:'DMart  ₹2.31 Cr',top3:'Lulu  ₹1.22 Cr',
   mhoft:'₹5.24 Cr',dcoft:'₹2.76 Cr',npi:'₹0.64 Cr',npipct:'7.9%',
   mhcat:['Face Cleanser  ₹1.12 Cr','Shampoo  ₹1.23 Cr','Sun Care  ₹0.32 Cr'],
   dccat:['Face Cleanser  ₹1.18 Cr','Sun Care  ₹0.61 Cr','Face Serum  ₹0.19 Cr'],
   priority:'Apollo × hero-EAN availability',
   mhd:[[0.94,0.86,0.26],[1.03,0.95,0.38],[1.08,0.96,0.46],[1.29,1.21,0.48],[1.12,1.28,0.33],[1.12,1.23,0.32]],
   dcd:[[0.37,0.25,0.14],[0.40,0.43,0.15],[0.52,0.65,0.17],[0.77,0.81,0.19],[0.71,0.51,0.19],[1.18,0.61,0.19]],
   insights:['South-1 delivers ₹8.19 Cr offtake, 22.7% of national value.',
     'Primary is ₹9.80 Cr versus ₹8.19 Cr offtake.','Flow conversion is 83.6% for July.',
     'The same-period flow gap is ₹1.61 Cr.','South-1 ranks #2 by national offtake.',
     'Karnataka ranks #1 with ₹4.10 Cr offtake.','Tamil Nadu ranks #2 with ₹2.63 Cr offtake.',
     'Kerala ranks #3 with ₹1.17 Cr offtake.','The leading state contributes 50.1% of zone offtake.',
     'The top three states contribute 96.5% of zone offtake.',
     'Apollo: ₹2.84 Cr offtake; 81.0%.','DMart: ₹2.31 Cr offtake; 74.8%.',
     'Lulu: ₹1.22 Cr offtake; primary comparison unavailable.',
     'The leading chain contributes 34.7% of zone offtake.',
     'The top three chains contribute 77.8% of zone offtake.']},
  {z:'North', p:11.95,o:6.99,cv:58.5,g:4.97,act:'FIX',rank:3,mx:'19.4%',
   states:['Delhi NCR  ₹1.97 Cr','Rajasthan  ₹1.67 Cr','Punjab  ₹1.55 Cr'],
   top1:'DMart  ₹2.53 Cr',top2:'Reliance  ₹2.40 Cr',top3:'Apollo  ₹1.16 Cr',
   mhoft:'₹4.74 Cr',dcoft:'₹2.12 Cr',npi:'₹0.65 Cr',npipct:'9.2%',
   mhcat:['Face Cleanser  ₹2.09 Cr','Shampoo  ₹1.68 Cr','Sun Care  ₹0.35 Cr'],
   dccat:['Face Cleanser  ₹1.41 Cr','Sun Care  ₹0.36 Cr','Face Serum  ₹0.10 Cr'],
   priority:'DMart × hero-EAN availability',
   mhd:[[1.72,1.22,0.39],[2.08,1.33,0.66],[2.23,1.63,0.77],[2.43,1.75,0.79],[2.28,1.68,0.56],[2.09,1.68,0.35]],
   dcd:[[0.49,0.21,0.07],[0.66,0.42,0.10],[0.74,0.48,0.11],[1.09,0.71,0.11],[1.11,0.51,0.10],[1.41,0.36,0.10]],
   insights:['North delivers ₹6.99 Cr offtake, 19.4% of national value.',
     'Primary is ₹11.95 Cr versus ₹6.99 Cr offtake.','Flow conversion is 58.5% for July.',
     'The same-period flow gap is ₹4.97 Cr.','North ranks #3 by national offtake.',
     'Delhi NCR ranks #1 with ₹1.97 Cr offtake.','Rajasthan ranks #2 with ₹1.67 Cr offtake.',
     'Punjab ranks #3 with ₹1.55 Cr offtake.','The leading state contributes 28.2% of zone offtake.',
     'The top three states contribute 74.3% of zone offtake.',
     'DMart: ₹2.53 Cr offtake; 77.9%.','Reliance: ₹2.40 Cr offtake; 44.9%.',
     'Apollo: ₹1.16 Cr offtake; 98.3%.','The leading chain contributes 36.2% of zone offtake.',
     'The top three chains contribute 87.1% of zone offtake.']},
  {z:'South-2',p:6.89,o:4.91,cv:71.3,g:1.98,act:'FIX',rank:4,mx:'13.6%',
   states:['Telangana  ₹2.56 Cr','Andhra Pradesh  ₹2.35 Cr','—'],
   top1:'DMart  ₹1.95 Cr',top2:'Apollo  ₹1.64 Cr',top3:'Reliance  ₹0.67 Cr',
   mhoft:'₹3.74 Cr',dcoft:'₹1.11 Cr',npi:'₹0.31 Cr',npipct:'6.4%',
   mhcat:['Face Cleanser  ₹1.04 Cr','Shampoo  ₹0.94 Cr','Sun Care  ₹0.14 Cr'],
   dccat:['Face Cleanser  ₹0.56 Cr','Sun Care  ₹0.20 Cr','Face Serum  ₹0.05 Cr'],
   priority:'DMart × hero-EAN availability',
   mhd:[[0.73,0.66,0.12],[0.89,0.78,0.25],[0.89,0.84,0.28],[1.08,0.87,0.29],[1.23,1.00,0.20],[1.04,0.94,0.14]],
   dcd:[[0.11,0.09,0.04],[0.19,0.13,0.04],[0.29,0.17,0.05],[0.48,0.36,0.05],[0.50,0.20,0.04],[0.56,0.20,0.05]],
   insights:['South-2 delivers ₹4.91 Cr offtake, 13.6% of national value.',
     'Primary is ₹6.89 Cr versus ₹4.91 Cr offtake.','Flow conversion is 71.3% for July.',
     'The same-period flow gap is ₹1.98 Cr.','South-2 ranks #4 by national offtake.',
     'Telangana ranks #1 with ₹2.56 Cr offtake.','Andhra Pradesh ranks #2 with ₹2.35 Cr offtake.',
     'The leading state contributes 52.2% of zone offtake.',
     'The top three states contribute 100.0% of zone offtake.',
     'Source reports 2 material states in this zone cut.',
     'DMart: ₹1.95 Cr offtake; 45.1%.','Apollo: ₹1.64 Cr offtake; 148.5%.',
     'Reliance: ₹0.67 Cr offtake; 82.5%.','The leading chain contributes 39.7% of zone offtake.',
     'The top three chains contribute 86.6% of zone offtake.']},
  {z:'East',  p:7.83,o:3.55,cv:45.3,g:4.28,act:'FIX',rank:5,mx:'9.8%',
   states:['West Bengal  ₹1.56 Cr','Odisha  ₹0.60 Cr','Bihar  ₹0.49 Cr'],
   top1:'Reliance  ₹2.16 Cr',top2:'Apollo  ₹0.80 Cr',top3:'Vishal Mega M…  ₹0.17 Cr',
   mhoft:'₹2.91 Cr',dcoft:'₹0.60 Cr',npi:'₹0.36 Cr',npipct:'10.2%',
   mhcat:['Face Cleanser  ₹1.34 Cr','Shampoo  ₹1.18 Cr','Sun Care  ₹0.19 Cr'],
   dccat:['Face Cleanser  ₹0.47 Cr','Sun Care  ₹0.09 Cr','Face Serum  ₹0.05 Cr'],
   priority:'Reliance × hero-EAN availability',
   mhd:[[0.81,0.62,0.15],[0.99,0.66,0.16],[1.00,0.95,0.25],[1.15,1.07,0.30],[1.05,0.96,0.19],[1.34,1.18,0.19]],
   dcd:[[0.06,0.06,0.04],[0.08,0.06,0.03],[0.12,0.09,0.04],[0.11,0.10,0.05],[0.15,0.07,0.07],[0.47,0.09,0.05]],
   insights:['East delivers ₹3.55 Cr offtake, 9.8% of national value.',
     'Primary is ₹7.83 Cr versus ₹3.55 Cr offtake.','Flow conversion is 45.3% for July.',
     'The same-period flow gap is ₹4.28 Cr.','East ranks #5 by national offtake.',
     'West Bengal ranks #1 with ₹1.56 Cr offtake.','Odisha ranks #2 with ₹0.60 Cr offtake.',
     'Bihar ranks #3 with ₹0.49 Cr offtake.','The leading state contributes 43.8% of zone offtake.',
     'The top three states contribute 74.3% of zone offtake.',
     'Reliance: ₹2.16 Cr offtake; 52.9%.','Apollo: ₹0.80 Cr offtake; 121.1%.',
     'Vishal Mega Mart: ₹0.17 Cr offtake; primary comparison unavailable.',
     'The leading chain contributes 60.9% of zone offtake.',
     'The top three chains contribute 88.2% of zone offtake.']},
  {z:'Central',p:2.69,o:2.12,cv:78.8,g:0.57,act:'WATCH',rank:6,mx:'5.9%',
   states:['Madhya Pradesh  ₹1.68 Cr','Chhattisgarh  ₹0.44 Cr','—'],
   top1:'DMart  ₹1.41 Cr',top2:'Reliance  ₹0.46 Cr',top3:'Apollo  ₹0.19 Cr',
   mhoft:'₹1.25 Cr',dcoft:'₹0.82 Cr',npi:'₹0.18 Cr',npipct:'8.5%',
   mhcat:['Face Cleanser  ₹0.54 Cr','Shampoo  ₹0.40 Cr','Sun Care  ₹0.09 Cr'],
   dccat:['Face Cleanser  ₹0.66 Cr','Sun Care  ₹0.18 Cr','Face Serum  ₹0.02 Cr'],
   priority:'DMart × hero-EAN availability',
   mhd:[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0.54,0.40,0.09]],
   dcd:[[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0,0,0],[0.66,0.18,0.02]],
   insights:['Central delivers ₹2.12 Cr offtake, 5.9% of national value.',
     'Primary is ₹2.69 Cr versus ₹2.12 Cr offtake.','Flow conversion is 78.8% for July.',
     'The same-period flow gap is ₹0.57 Cr.','Central ranks #6 by national offtake.',
     'Madhya Pradesh ranks #1 with ₹1.68 Cr offtake.','Chhattisgarh ranks #2 with ₹0.44 Cr offtake.',
     'The leading state contributes 79.3% of zone offtake.',
     'The top three states contribute 100.0% of zone offtake.',
     'Source reports 2 material states in this zone cut.',
     'DMart: ₹1.41 Cr offtake; 95.3%.','Reliance: ₹0.46 Cr offtake; 51.2%.',
     'Apollo: ₹0.19 Cr offtake; 137.7%.','The leading chain contributes 66.5% of zone offtake.',
     'The top three chains contribute 97.6% of zone offtake.']},
];

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 1 — COMMAND CENTER
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,1);
  hdr(s,'July Modern Trade Growth Command Center',
    'Honasa Consumer | Primary, offtake, portfolio and execution | July 2026',{fs:22});

  // 3 top KPI tiles
  const kx=[M,M+3.26,M+6.52,M+9.78];
  kpi(s,kx[0],.92,3.18,.58,'₹36.1 Cr','July Offtake','MT+eB2B+SIS combined',CARD);
  kpi(s,kx[1],.92,3.18,.58,'73.4%','Flow Conversion','Offtake ÷ Primary',CARD);
  kpi(s,kx[2],.92,3.18,.58,'₹13.11 Cr','Total Gap','Primary − Offtake',CARD);
  kpi(s,kx[3],.92,3.18,.58,'90.7%','Gap in DMart+Reliance','₹11.89 Cr of ₹13.11 Cr',CARD,AMBER);

  // Row 1 section headers
  sh(s,M,1.57,4.24,.24,'SALES FLOW'); sh(s,M+4.28,1.57,4.24,.24,'GAP CONCENTRATION'); sh(s,M+8.56,1.57,4.24,.24,'MANAGEMENT PRIORITY');

  // Primary vs Offtake chart
  s.addChart(pres.ChartType.bar,[
    {name:'Primary',labels:['West','S-1','North','S-2','East','Central'],values:[10.05,9.80,11.95,6.89,7.83,2.69]},
    {name:'Offtake',labels:['West','S-1','North','S-2','East','Central'],values:[8.28,8.19,6.99,4.91,3.55,2.12]},
  ],{x:M,y:1.83,w:4.24,h:2.18,barDir:'bar',barGrouping:'clustered',
    chartColors:[GOLD,'1B7A6E'],showLegend:true,legendPos:'b',legendFontSize:8,legendFontColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:7,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,valAxisLabelFontSize:7,catAxisLabelFontSize:7,
    plotAreaFillColor:BG,showTitle:false,shadow:{type:'none'}});

  // Gap by account chart
  s.addChart(pres.ChartType.bar,[
    {name:'Gap ₹ Cr',labels:['Reliance','DMart','Metro'],values:[7.61,4.29,1.36]},
  ],{x:M+4.28,y:1.83,w:4.24,h:2.18,barDir:'bar',barGrouping:'clustered',
    chartColors:[RED],showLegend:false,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:8,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,valAxisLabelFontSize:7,catAxisLabelFontSize:7,
    plotAreaFillColor:BG,showTitle:false,shadow:{type:'none'}});

  bl(s,M+8.56,1.83,4.24,2.18,[
    'North + East hold 70.5% of the gap.',
    'West + South-1 deliver 45.6% of offtake.',
    'Protect hero-SKU OSA while closing weak chain-zone exceptions.',
    'Use Apollo and FSN/Nykaa as flow-governance benchmarks.',
    'Review chain × zone × EAN exceptions weekly.',
    '73.4% conversion | ₹13.11 Cr gap',
  ]);

  // Row 2 section headers
  sh(s,M,4.06,4.24,.24,'GEOGRAPHIC ENGINES'); sh(s,M+4.28,4.06,4.24,.24,'PORTFOLIO ENGINES'); sh(s,M+8.56,4.06,4.24,.24,'ACCOUNT SIGNALS');

  bl(s,M,4.32,4.24,1.30,[
    'West: ₹8.28 Cr at 82.3% conversion.',
    'South-1: ₹8.19 Cr at 83.6%.',
    'North: ₹4.97 Cr gap; largest recovery pool.',
    'East: 45.3% conversion; weakest flow.',
    'Replicate strong-zone availability cadence selectively.',
  ]);
  bl(s,M+4.28,4.32,4.24,1.30,[
    '98.4% of offtake from Mamaearth + The Derma Co.',
    'Mamaearth ₹24.49 Cr | 73.4% conversion.',
    'TDC ₹11.03 Cr | ₹4.16 Cr gap.',
    'ME Face Cleanser ₹8.53 Cr in July.',
    'TDC Face Cleanser ₹7.13 Cr in July.',
  ]);
  bl(s,M+8.56,4.32,4.24,1.30,[
    'DMart ₹13.97 Cr | 76.5% conversion.',
    'Reliance ₹8.06 Cr | 51.4% conversion.',
    'Apollo 99.7% conversion — benchmark cadence.',
    'FSN/Nykaa ₹2.07 Cr combined.',
    'Treat >100% account flows as timing/stock signals, not success claims.',
  ]);

  // Row 3
  sh(s,M,5.68,4.24,.24,'90-DAY COMMERCIAL MOVES'); sh(s,M+4.28,5.68,4.24,.24,'LEADERSHIP SCOREBOARD'); sh(s,M+8.56,5.68,4.24,.24,'DECISION SAFEGUARDS');
  bl(s,M,5.94,4.24,0.88,[
    '0–30d: validate mappings and publish exception list.',
    '0–30d: fix North/East hero-SKU OSA.',
    '31–60d: close DMart South-2 and Reliance North/East.',
    '61–90d: reset loading rules by verified conversion.',
  ]);
  bl(s,M+4.28,5.94,4.24,0.88,[
    'Flow conversion: move toward >90%.',
    'DMart + Reliance gap: close 50% with named owners.',
    'Hero-SKU OSA: maintain >95% in priority stores.',
    'North and East gaps: decline every week.',
  ]);
  bl(s,M+8.56,5.94,4.24,0.88,[
    'Flow gap is not closing inventory or stock cover.',
    'No YoY or target claim without matched comparator data.',
    'Revoke loading rules when offtake proof fails.',
    'FSN and Nykaa SS combined at article level.',
  ]);

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 2 — GROWTH EQUATION / DECISION FRAMEWORK
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,2);
  hdr(s,'Convert reporting into a State × Chain × SKU growth engine',
    'Decision framework | source-backed measures plus clearly labelled diagnostic extensions');

  s.addText('The decision is not "push more primary"; it is "find proven demand constrained by execution."',{
    x:M,y:.92,w:W-2*M,h:.32,fontSize:11,bold:true,color:GOLD,fontFace:'Calibri',italic:true,margin:0});
  s.addText('Use validated July flow measures now; add SAH, PDO, OOS and stock fields only after reconciliation.',{
    x:M,y:1.22,w:W-2*M,h:.26,fontSize:9.5,color:LGREY,fontFace:'Calibri',margin:0});

  sh(s,M,1.54,4.24,.24,'GROWTH EQUATION'); sh(s,M+4.28,1.54,4.24,.24,'SAH × SHARE DIAGNOSIS'); sh(s,M+8.56,1.54,4.24,.24,'DISTRIBUTION PRODUCTIVITY');
  bl(s,M,1.82,4.24,1.40,[
    'Distribution white space','Assortment and pack','Availability recovery','Hero-SKU scaling','Conversion productivity',
  ]);
  bl(s,M+4.28,1.82,4.24,1.40,[
    'High SAH + low share: test distribution constraint',
    'Low SAH + high WD: fix proposition/range',
    'Causal conclusions require field reconciliation',
  ]);
  bl(s,M+8.56,1.82,4.24,1.40,[
    'SPD = MS ÷ WD · Higher SPD means each point works harder',
    'Combine SPD with PDO',
    'Low WD + high PDO is the priority test cell',
  ]);

  sh(s,M,3.28,.24,'FACE WASH'); // small label
  sh(s,M,3.28,4.24,.24,'FACE WASH'); sh(s,M+4.28,3.28,4.24,.24,'SHAMPOO'); sh(s,M+8.56,3.28,4.24,.24,'HERO-SKU AVAILABILITY');
  bl(s,M,3.56,4.24,1.10,[
    'Scale strength','Protect Rice and Ubtan heroes',
    'Expand only where demand signals are proven',
    'Prioritize availability before blanket discounting',
  ]);
  bl(s,M+4.28,3.56,4.24,1.10,[
    'Selective headroom','Lead with Onion and Rosemary heroes',
    'Scale winning variant × pack × state × chain',
    'Avoid full-range rollout without productivity proof',
  ]);
  bl(s,M+8.56,3.56,4.24,1.10,[
    'Must-stock first','Measure hero availability %, not only SKU count',
    'Missing #1 hero should fail assortment score',
    'Long tail follows proven heroes',
  ]);

  sh(s,M,4.72,4.24,.24,'PACK ARCHITECTURE'); sh(s,M+4.28,4.72,4.24,.24,'MARKET × FLOW RULE'); sh(s,M+8.56,4.72,4.24,.24,'₹ WHITE-SPACE SIZE');
  bl(s,M,5.00,4.24,1.20,[
    'Traffic pack · Core-volume pack',
    'Premium/value-upgrade pack','Dead or low-productivity pack',
    'Do not give every format every pack',
  ]);
  bl(s,M+4.28,5.00,4.24,1.20,[
    'Share ↑ + offtake ↑: scale','Primary ↑ + offtake weak: stop loading',
    'Offtake ↑ + supply weak: replenish','Share ↓: validate competitor/OOS transfer',
  ]);
  bl(s,M+8.56,5.00,4.24,1.20,[
    'Stores × PDO = potential white space',
    'Potential stores − current productive stores','Multiply by benchmark monthly PDO',
    'Annualize only after a controlled pilot','Rank actions by ₹ and named owner',
  ]);

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 3 — MARKET SHARE
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,3);
  hdr(s,'Mamaearth is gaining share in both strategic categories',
    'June 2026 market share | Nielsen RMS | value share');

  kpi(s,M,.92,4.00,.72,'10.5%','Face Wash Value Share  #4','#4 | +3.1 pp YoY | L3M +58.2% YoY',CARD);
  kpi(s,M+4.09,.92,4.00,.72,'3.7%','Shampoo Value Share  #7','+1.2 pp YoY | L3M +80.3% YoY',CARD);
  kpi(s,M+8.18,.92,4.00,.72,'0.4%','TDC Face Wash Share','+0.3 pp YoY | WD 27.3%',CARD);

  s.addChart(pres.ChartType.bar,[
    {name:'Value share (%)',labels:['Himalaya','Garnier','Pond\'s','Mamaearth'],values:[22.6,14.2,13.8,10.5]},
  ],{x:M,y:1.74,w:4.00,h:2.60,barDir:'bar',barGrouping:'clustered',
    chartColors:[TEAL,TEAL,TEAL,GOLD],showLegend:false,showTitle:true,title:'Face Wash Value Share (%)',titleFontSize:9,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:9,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,valAxisLabelFontSize:8,catAxisLabelFontSize:9,
    plotAreaFillColor:BG,shadow:{type:'none'}});

  s.addChart(pres.ChartType.bar,[
    {name:'Value share (%)',labels:['Dove','H&S','Mamaearth'],values:[16.6,13.0,3.7]},
  ],{x:M+4.09,y:1.74,w:4.00,h:2.60,barDir:'bar',barGrouping:'clustered',
    chartColors:[TEAL,TEAL,GOLD],showLegend:false,showTitle:true,title:'Shampoo Value Share (%)',titleFontSize:9,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:9,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,valAxisLabelFontSize:8,catAxisLabelFontSize:9,
    plotAreaFillColor:BG,shadow:{type:'none'}});

  sh(s,M+8.18,1.74,4.00,.24,'GROWTH, DISTRIBUTION AND PACK OPPORTUNITY');
  bl(s,M+8.18,2.02,4.00,2.32,[
    'Face Wash: Mamaearth L3M growth +58.2% YoY, 89.0% weighted distribution (+6.0 pp).',
    'Shampoo: Mamaearth L3M growth +80.3% YoY, 81.5% weighted distribution (+4.4 pp).',
    'The Derma Co. Face Wash 27.3% weighted distribution; scale selectively with store productivity proof.',
    'Face Wash missing packs = 5% of category value; prioritize 240 ml and 60 ml.',
    'Shampoo misses 12 of 16 formats (66% of category value); pilot the largest formats.',
    'FACE WASH: 7/16 established | 2 newly entered | 7 missing',
    'SHAMPOO: 3/16 established | 1 newly entered | 12 missing',
  ]);

  ft(s,'Source: pipeline v2.4.0 · Nielsen RMS Jun-26 · Market_Share_By_PackSize_June26.pptx · 2026-08-19');
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 4 — ZONE PORTFOLIO SCORECARD
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,4);
  hdr(s,'Two high-conversion zones can fund focused intervention in North and East',
    'Zone portfolio | contribution, conversion and action');

  // Zone scorecard table
  const cols=['Zone','Primary','Offtake','Mix','Conv.','Gap','Action'];
  const cw=[1.8,1.4,1.4,1.0,1.0,1.0,1.2];
  const tx=M, ty=1.02, rh=0.38;
  // header row
  let cx=tx;
  cols.forEach((c,i)=>{
    s.addShape(pres.ShapeType.rect,{x:cx,y:ty,w:cw[i],h:rh,fill:{color:GOLD},line:{type:'none'}});
    s.addText(c,{x:cx,y:ty,w:cw[i],h:rh,fontSize:9,bold:true,color:'000000',align:'center',valign:'middle',margin:0});
    cx+=cw[i]+.04;
  });
  // data rows
  ZONES.forEach((z,ri)=>{
    cx=tx;
    const rowBg=z.act==='FIX'?'1A0B0B':'0A1220';
    const actColor=z.act==='FIX'?RED:TEAL;
    const vals=[z.z,`₹${z.p} Cr`,`₹${z.o} Cr`,z.mx,`${z.cv}%`,`₹${z.g} Cr`,z.act];
    vals.forEach((v,ci)=>{
      s.addShape(pres.ShapeType.rect,{x:cx,y:ty+(ri+1)*(rh+.04),w:cw[ci],h:rh,fill:{color:rowBg},line:{color:NAVY2,pt:.3}});
      s.addText(v,{x:cx,y:ty+(ri+1)*(rh+.04),w:cw[ci],h:rh,
        fontSize:9.5,bold:ci===0||ci===6,
        color:ci===6?actColor:(ci===4?(z.cv<65?RED:z.cv<80?AMBER:GREEN):WHITE),
        align:'center',valign:'middle',margin:0,fontFace:'Calibri'});
      cx+=cw[ci]+.04;
    });
  });

  // Right panel: actions
  const rx=M+9.30, ry=1.02, rw=3.78;
  sh(s,rx,ry,rw,.24,'PORTFOLIO ACTIONS');
  bl(s,rx,ry+.28,rw,2.20,[
    'Protect: West, South-1 and Central — maintain hero-SKU availability and avoid unnecessary loading.',
    'Watch: South-2 — isolate the DMart gap while sustaining Apollo and Reliance throughput.',
    'Fix: North and East — run weekly chain-zone gap closure with named owners and SKU-level exceptions.',
    'Separate: Pan India / FSN — maintain a distinct e-commerce flow view because geographic primary is unavailable.',
  ]);

  sh(s,M,3.96,4.24,.24,'PROTECT ENGINES'); sh(s,M+4.28,3.96,4.24,.24,'WATCH FLOW'); sh(s,M+8.56,3.96,4.24,.24,'FIX CONCENTRATION');
  kpi(s,M,4.24,4.24,1.00,'West + South-1','₹16.47 Cr offtake | defend hero-SKU OSA','Conv 82–84% | benchmark achieved',CARD,GREEN);
  kpi(s,M+4.28,4.24,4.24,1.00,'South-2','₹1.98 Cr gap | isolate DMart exceptions','Apollo 148.5% → investigate stock cover',CARD,AMBER);
  kpi(s,M+8.56,4.24,4.24,1.00,'North + East','70.5% of national gap | weekly owner review','N ₹4.97 Cr @ 58.5% · E ₹4.28 Cr @ 45.3%',CARD,RED);

  sh(s,M,5.30,4.24,.24,'WHAT DROVE'); sh(s,M+4.28,5.30,4.24,.24,'WHY IT MATTERS'); sh(s,M+8.56,5.30,4.24,.24,'ACTIONS');
  bl(s,M,5.58,4.24,1.20,[
    'North primary ₹11.95 Cr but offtake only ₹6.99 Cr.',
    'East conversion collapsed to 45.3%.',
    'West and S-1 sustain above benchmark.']);
  bl(s,M+4.28,5.58,4.24,1.20,[
    '₹9.25 Cr stuck in North+East pipeline — OOS risk once stock clears.',
    'West+S-1 profits protect investment in Fix zones.',
    'Reliance North ₹2.40 Cr at 44.9% must be recovered.']);
  bl(s,M+8.56,5.58,4.24,1.20,[
    'NKAM: publish North+East hero-EAN gap list by 25 Aug.',
    'ZSM North: weekly conversion review with chain-specific actions.',
    'ZSM East: Reliance store-level audit by 31 Aug.']);

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// ZONE DEEP DIVE BUILDER (slides 5-10)
// ──────────────────────────────────────────────────────────────────────────────
function zoneSlide(slideNum, z) {
  const s=pres.addSlide(); bg(s); badge(s,slideNum);
  const act=z.act==='FIX'?'Urgent gap closure':'Watch and convert';
  hdr(s,`${z.z}: ${act}`,`Zone deep dive | July 2026 | ₹ Cr`);

  // 4 KPI tiles
  const kw=3.18, ky=.92;
  kpi(s,M,ky,kw,.62,`₹${z.p} Cr`,'PRIMARY',`July billing · ${z.mx} mix`,CARD);
  kpi(s,M+3.22,ky,kw,.62,`₹${z.o} Cr`,'OFFTAKE','Consumer-facing flow',CARD);
  kpi(s,M+6.44,ky,kw,.62,`${z.cv}%`,'CONVERSION','Flow',z.act==='FIX'?'180A0A':CARD,z.act==='FIX'?RED:GREEN);
  kpi(s,M+9.66,ky,kw,.62,`₹${z.g} Cr`,'GAP','Primary − Offtake',CARD,z.act==='FIX'?RED:AMBER);

  const mgmt=z.act==='FIX'
    ?`Close ${z.top1.split('  ')[0]} exceptions  •  Protect hero-SKU OSA  •  Review conversion weekly`
    :  `Protect hero-SKU OSA  •  Replicate strong-zone cadence  •  Monitor conversion weekly`;
  s.addText(`MANAGEMENT PRIORITY  |  ${mgmt}`,{
    x:M,y:1.59,w:W-2*M,h:.22,fontSize:8.5,color:LGREY,fontFace:'Calibri',italic:true,margin:0});

  // Two sub-category charts side by side
  const months=['Feb 26','Mar 26','Apr 26','May 26','Jun 26','Jul 26'];
  s.addChart(pres.ChartType.bar,[
    {name:'Face Cleanser',labels:months,values:z.mhd.map(r=>r[0])},
    {name:'Shampoo',      labels:months,values:z.mhd.map(r=>r[1])},
    {name:'Sun Care',     labels:months,values:z.mhd.map(r=>r[2])},
  ],{x:M,y:1.85,w:6.00,h:2.00,barDir:'col',barGrouping:'clustered',
    chartColors:[GOLD,'1B7A6E',RED],showLegend:true,legendPos:'b',legendFontSize:7,legendFontColor:LGREY,
    showTitle:true,title:'Mamaearth — top 3 sub-categories',titleFontSize:8,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:6.5,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,valAxisLabelFontSize:7,catAxisLabelFontSize:7,
    plotAreaFillColor:BG,shadow:{type:'none'}});

  s.addChart(pres.ChartType.bar,[
    {name:'Face Cleanser',labels:months,values:z.dcd.map(r=>r[0])},
    {name:'Sun Care',     labels:months,values:z.dcd.map(r=>r[1])},
    {name:'Face Serum',   labels:months,values:z.dcd.map(r=>r[2])},
  ],{x:M+6.08,y:1.85,w:6.00,h:2.00,barDir:'col',barGrouping:'clustered',
    chartColors:[GOLD,'1B7A6E',RED],showLegend:true,legendPos:'b',legendFontSize:7,legendFontColor:LGREY,
    showTitle:true,title:'The Derma Co. — top 3 sub-categories',titleFontSize:8,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:6.5,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,valAxisLabelFontSize:7,catAxisLabelFontSize:7,
    plotAreaFillColor:BG,shadow:{type:'none'}});

  // Top chains / states + brand sub-cat
  const panels=[
    {x:M,     y:3.92, w:3.82, header:'TOP CHAINS / STATES',
     items:[z.top1,z.top2,z.top3,...z.states]},
    {x:M+3.90,y:3.92, w:3.94, header:'MAMAEARTH | TOP 3 SUB-CATS',
     items:[`Mamaearth | ${z.mhoft}`,...z.mhcat]},
    {x:M+7.88,y:3.92, w:3.94, header:'THE DERMA CO. | TOP 3 SUB-CATS',
     items:[`The Derma Co. | ${z.dcoft}`,...z.dccat]},
  ];
  panels.forEach(p=>{
    sh(s,p.x,p.y,p.w,.24,p.header);
    bl(s,p.x,p.y+.28,p.w,0.92,p.items,{fs:8.5});
  });

  s.addText(`NPI CONTRIBUTION  |  ${z.npi} | ${z.npipct} of zone | Priority: ${z.priority}`,{
    x:M,y:5.00,w:W-2*M,h:.22,fontSize:8,color:GOLD,fontFace:'Calibri',bold:true,margin:0});

  // 15 numbered insights in 3 columns of 5
  s.addText('15 ZONE-SPECIFIC INSIGHTS AND ACTIONS',{x:M,y:5.26,w:W-2*M,h:.22,fontSize:8.5,bold:true,color:WHITE,margin:0});
  const colW=(W-2*M)/3-.04, rh=.25;
  z.insights.forEach((ins,i)=>{
    const col=Math.floor(i/5), row=i%5;
    const ix=M+col*(colW+.06), iy=5.50+row*rh;
    s.addShape(pres.ShapeType.ellipse,{x:ix,y:iy+.04,w:.18,h:.18,fill:{color:GOLD},line:{type:'none'}});
    s.addText(String(i+1).padStart(2,'0'),{x:ix,y:iy+.04,w:.18,h:.18,fontSize:6.5,bold:true,color:WHITE,align:'center',valign:'middle',margin:0});
    s.addText(ins,{x:ix+.22,y:iy,w:colW-.22,h:rh,fontSize:7.5,color:LGREY,fontFace:'Calibri',valign:'middle',margin:0});
  });

  ft(s,SRC);
}

ZONES.forEach((z,i)=>zoneSlide(5+i,z));

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 11 — PAN INDIA / FSN+NYKAA
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,11);
  hdr(s,'Pan India: Separate view','Zone deep dive | July 2026 | ₹ Cr');

  kpi(s,M,.92,3.18,.62,'N/A','PRIMARY','July billing · 5.7% mix',CARD);
  kpi(s,M+3.22,.92,3.18,.62,'₹2.07 Cr','OFFTAKE','FSN+Nykaa SS combined',CARD,GREEN);
  kpi(s,M+6.44,.92,3.18,.62,'99.4%','FLOW','+26.0 pp vs Pan India MT avg',CARD,GREEN);
  kpi(s,M+9.66,.92,3.18,.62,'N/A','GAP','Supply view unavailable',CARD);

  s.addText('MANAGEMENT PRIORITY  |  Protect account flow  •  Track campaign velocity  •  Build comparable supply view',{
    x:M,y:1.59,w:W-2*M,h:.22,fontSize:8.5,color:LGREY,fontFace:'Calibri',italic:true,margin:0});

  const months=['Jan','Feb','Mar','Apr','May','Jun','Jul'];
  s.addChart(pres.ChartType.line,[
    {name:'FSN/Nykaa Offtake (₹ Cr)',labels:months,values:[1.64,1.68,1.73,2.29,2.08,2.17,2.07]},
  ],{x:M,y:1.85,w:5.80,h:2.20,
    lineDataSymbol:'none',lineSize:3,chartColors:[GOLD],
    showLegend:true,legendPos:'b',legendFontSize:8,legendFontColor:LGREY,
    showTitle:true,title:'FSN/Nykaa offtake trend (₹ Cr) — Jan to Jul',titleFontSize:8.5,titleColor:LGREY,
    showValue:true,dataLabelFontSize:8,dataLabelColor:WHITE,
    valGridLine:{color:NAVY2,size:0.5},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,plotAreaFillColor:BG,shadow:{type:'none'}});

  s.addChart(pres.ChartType.line,[
    {name:'Active EANs',labels:months,values:[222,217,203,196,190,200,198]},
  ],{x:M+5.88,y:1.85,w:5.80,h:2.20,
    lineDataSymbol:'none',lineSize:3,chartColors:[TEAL],
    showLegend:true,legendPos:'b',legendFontSize:8,legendFontColor:LGREY,
    showTitle:true,title:'Active FSN/Nykaa EANs — Jan to Jul',titleFontSize:8.5,titleColor:LGREY,
    showValue:true,dataLabelFontSize:8,dataLabelColor:WHITE,
    valGridLine:{color:NAVY2,size:0.5},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,plotAreaFillColor:BG,shadow:{type:'none'}});

  sh(s,M,4.12,4.00,.24,'TOP CHAINS'); sh(s,M+4.08,4.12,4.00,.24,'MAMAEARTH'); sh(s,M+8.16,4.12,4.00,.24,'THE DERMA CO.');
  bl(s,M,4.40,4.00,.90,['FSN / Nykaa  ₹2.07 Cr','Pan India  ₹2.07 Cr','Separate from geographic zones']);
  bl(s,M+4.08,4.40,4.00,.90,['Mamaearth | ₹1.65 Cr (79.7%)','Face Cleanser (top sub-cat)','Sun Care (2nd)','Shampoo (3rd)']);
  bl(s,M+8.16,4.40,4.00,.90,['The Derma Co. | ₹0.37 Cr (17.9%)','Face Cleanser (top sub-cat)','Sun Care (2nd)','Face Serum (3rd)']);

  s.addText('FSN/Nykaa: 99.4% flow | July ₹2.07 Cr | NPI ₹0.13 Cr (6.3%) | Jul ₹2.07 Cr — 4.6% below Jun | maintain >95% flow as account benchmark',{
    x:M,y:5.38,w:W-2*M,h:.30,fontSize:9,color:GOLD,bold:true,fontFace:'Calibri',margin:0});

  sh(s,M,5.74,4.24,.24,'TOP NPI ARTICLES (₹)');
  bl(s,M,6.02,12.83,.82,[
    'Rice Face Wash 100 ml ₹0.27 Cr · Rice Face Wash 50 ml ₹0.19 Cr · ME Ubtan Natural Glow FW ₹0.14 Cr',
    'Vitamin C Face Wash ₹0.09 Cr · ME VitC Daily Glow FW ₹0.08 Cr · ME Ubtan FW 50 ml ₹0.08 Cr',
  ]);
  s.addText('LEADERSHIP CALL  |  Protect top face-wash and sunscreen availability, reverse the 4.6% June–July softness, and retain >95% flow conversion as the account benchmark.',{
    x:M,y:5.74,w:W-2*M,h:.24,fontSize:8.5,color:LGREY,italic:true,margin:0});

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 12 — CHAIN GROWTH SCORECARD
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,12);
  hdr(s,'Lulu leads growth; Reliance and Metro require targeted recovery',
    'Chain growth and risk command centre | June–July 2026');

  const chains=[
    {n:'DMart',   jun:14.56,jul:14.33,mom:-1.5, sig:'Watch'},
    {n:'Reliance',jun:9.48, jul:8.06, mom:-15.0,sig:'Recover'},
    {n:'Lulu',    jun:1.16, jul:1.70, mom:46.5,  sig:'Scale'},
    {n:'WF',      jun:0.80, jul:0.72, mom:-9.9,  sig:'Watch'},
    {n:'H&G',     jun:0.52, jul:0.51, mom:-2.0,  sig:'Watch'},
    {n:'Metro',   jun:0.61, jul:0.49, mom:-20.5, sig:'Recover'},
    {n:'More',    jun:0.44, jul:0.41, mom:-6.8,  sig:'Watch'},
    {n:'Vishal',  jun:0.31, jul:0.36, mom:18.2,  sig:'Scale'},
    {n:'V-Mart',  jun:0.13, jul:0.12, mom:-8.5,  sig:'Watch'},
    {n:'Spencer', jun:0.08, jul:0.09, mom:0.7,   sig:'Protect'},
    {n:'Arambagh',jun:0.05, jul:0.04, mom:-22.5, sig:'Recover'},
    {n:'Ratandeep',jun:0.03,jul:0.03, mom:21.5,  sig:'Scale'},
    {n:'Sasta S', jun:0.01, jul:0.02, mom:127.8, sig:'Scale'},
    {n:'Sumo',    jun:0.01, jul:0.02, mom:9.8,   sig:'Protect'},
  ];
  const hdrCols=['CHAIN','JUN','JUL','MoM%','SIGNAL'];
  const cw=[2.20,1.50,1.50,1.50,1.50]; const tx=M;
  let cx=tx;
  // header
  hdrCols.forEach((c,i)=>{
    s.addShape(pres.ShapeType.rect,{x:cx,y:1.02,w:cw[i],h:.30,fill:{color:GOLD},line:{type:'none'}});
    s.addText(c,{x:cx,y:1.02,w:cw[i],h:.30,fontSize:9,bold:true,color:'000000',align:'center',valign:'middle',margin:0});
    cx+=cw[i]+.04;
  });
  chains.forEach((c,ri)=>{
    cx=tx;
    const momColor=c.mom>0?GREEN:RED;
    const vals=[c.n,`₹${c.jun} Cr`,`₹${c.jul} Cr`,(c.mom>0?'+':'')+c.mom.toFixed(1)+'%',c.sig];
    const rBg=ri%2===0?CARD:'0D1A30';
    vals.forEach((v,ci)=>{
      s.addShape(pres.ShapeType.rect,{x:cx,y:1.36+ri*.34,w:cw[ci],h:.30,fill:{color:rBg},line:{color:NAVY2,pt:.2}});
      s.addText(v,{x:cx,y:1.36+ri*.34,w:cw[ci],h:.30,fontSize:9,
        color:ci===3?momColor:ci===4?signalColor(c.sig):WHITE,
        bold:ci===4,align:'center',valign:'middle',margin:0,fontFace:'Calibri'});
      cx+=cw[ci]+.04;
    });
  });

  // Right panel
  const rx=M+8.56, rw=4.52;
  sh(s,rx,1.02,rw,.24,'LEADERSHIP READOUT');
  bl(s,rx,1.30,rw,3.52,[
    'Lulu +46.5% on a stable 19-site footprint: protect availability and copy winning store execution.',
    'Reliance -15.0%: Mamaearth Shampoo and Sun Care are the central recovery pool; protect TDC growth.',
    'Metro -20.5% despite more SKUs: stop range expansion until sales/SKU and store productivity recover.',
    'DMart -1.5% is broadly stable: TDC Face Cleanser offsets Mamaearth seasonal/mix softness.',
    'Missing July feeds are data gaps — not commercial de-growth — and remain outside the ranking.',
    'Arambagh -22.5%: investigate listing status before any commercial intervention.',
    'Sasta Sundar +127.8%: small base; protect fill rate before expanding footprint.',
    'Vishal +18.2%: Shampoo and cleanser leading — replicate winning EAN set in new doors.',
  ],{fs:9.5});

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 13 — CHAIN RECOVERY PLAN
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,13);
  hdr(s,'Fix the specific commercial loophole — not the whole account',
    'Chain recovery plan | evidence, action and success KPI');

  const recoveries=[
    {chain:'LULU',heading:'Scale same-store velocity',ev:'Face Cleanser, Shampoo and Sun Care growth on a stable footprint',
     rec:'Keep hero NPI/cleanser OSA above 95%; replicate winning stores',kpi:'Sales/store and OSA'},
    {chain:'RELIANCE',heading:'Mamaearth mix erosion',ev:'Shampoo and Sun Care explain most of the decline',
     rec:'Recover top declining Mamaearth EAN-store pairs; protect TDC growth',kpi:'Weekly lost sales and conversion'},
    {chain:'DMART',heading:'Brand mix shift',ev:'TDC Face Cleanser offsets Mamaearth Sun Care/Shampoo',
     rec:'Copy TDC cleanser execution; fix only weak Mamaearth hero EANs',kpi:'Sales/store-EAN and 80%+ conversion'},
    {chain:'METRO',heading:'Range dilution',ev:'More sites/SKUs but lower sales; Face Cleanser down',
     rec:'Pause range expansion and remove non-productive EANs',kpi:'Sales/SKU and sales/store'},
    {chain:'WF',heading:'Seasonal concentration',ev:'Sun Care explains almost the full decline',
     rec:'Rebalance space to Face Cleanser; audit serum and sunscreen OSA',kpi:'Sun Care recovery and OSA'},
    {chain:'MORE RETAIL',heading:'Low NPI penetration',ev:'NPI is 3.78% and Sun Care is declining',
     rec:'Prioritize top NPI EAN listings and seasonal recovery',kpi:'NPI share >5%'},
    {chain:'H&G',heading:'Mix softness, not structural decline',ev:'Sun Care and Face Serum down; Face Cleanser offsets',
     rec:'Monitor and fix targeted EANs without blanket trade spend',kpi:'Stable sales/store'},
    {chain:'VISHAL',heading:'Expansion execution risk',ev:'Sites +10.2%; Shampoo and cleanser lead growth',
     rec:'Protect fill rate before adding more doors',kpi:'OSA and sales/new door'},
    {chain:'FSN/NYKAA',heading:'June-July softness after strong base',ev:'July -4.6%, but conversion remains 99.4%',
     rec:'Protect top face-wash/sunscreen articles and maintain flow parity',kpi:'Conversion >95%; return to ₹2.17 Cr'},
  ];
  const CW=4.24, CH=0.76;
  recoveries.forEach((r,i)=>{
    const col=i%3, row=Math.floor(i/3);
    const x=M+col*(CW+.08), y=1.10+row*(CH+.10);
    s.addShape(pres.ShapeType.rect,{x,y,w:CW,h:CH,fill:{color:CARD},line:{color:GOLD,pt:.4}});
    s.addShape(pres.ShapeType.rect,{x,y,w:CW,h:.22,fill:{color:NAVY2},line:{type:'none'}});
    s.addText(r.chain,{x,y,w:CW,h:.22,fontSize:9,bold:true,color:GOLD,align:'center',valign:'middle',margin:0});
    s.addText(r.heading,{x:x+.06,y:y+.24,w:CW-.12,h:.18,fontSize:8,bold:true,color:WHITE,margin:0,fontFace:'Calibri'});
    s.addText('EVIDENCE  '+r.ev,{x:x+.06,y:y+.42,w:CW-.12,h:.16,fontSize:7.5,color:LGREY,margin:0,fontFace:'Calibri'});
    s.addText('ACTION  '+r.rec,{x:x+.06,y:y+.56,w:CW-.12,h:.16,fontSize:7.5,color:LGREY,margin:0,fontFace:'Calibri'});
    // KPI label
    s.addText('KPI: '+r.kpi,{x:x+.06,y:y+CH-.18,w:CW-.12,h:.16,fontSize:7,color:GOLD2,margin:0,fontFace:'Calibri'});
  });

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 14 — FSN/NYKAA DETAIL
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,14);
  hdr(s,'FSN/Nykaa maintains near-parity flow despite modest July softness',
    'FSN/Nykaa versus Pan India | January–July 2026');

  kpi(s,M,.92,4.00,.70,'₹2.08 Cr','JUL PRIMARY','FSN + Nykaa SS',CARD);
  kpi(s,M+4.08,.92,4.00,.70,'₹2.07 Cr','JUL OFFTAKE','5.7% of Pan India',CARD,GREEN);
  kpi(s,M+8.16,.92,4.00,.70,'99.4%','FLOW','+26.0 pp vs Pan India',CARD,GREEN);

  const months=['Jan','Feb','Mar','Apr','May','Jun','Jul'];
  s.addChart(pres.ChartType.line,[
    {name:'FSN/Nykaa Offtake (₹ Cr)',labels:months,values:[1.64,1.68,1.73,2.29,2.08,2.17,2.07]},
  ],{x:M,y:1.74,w:12.83,h:2.80,
    lineDataSymbol:'circle',lineSize:3,chartColors:[GOLD],
    showLegend:false,
    showTitle:true,title:'Seven-month offtake trend (₹ Cr)',titleFontSize:10,titleColor:LGREY,
    showValue:true,dataLabelFontSize:9,dataLabelColor:WHITE,
    valGridLine:{color:NAVY2,size:0.5},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,valAxisLabelFontSize:9,catAxisLabelFontSize:9,
    plotAreaFillColor:BG,shadow:{type:'none'}});

  sh(s,M,4.66,12.83,.24,'ARTICLE ENGINES AND LEADERSHIP ACTION');
  const arts=[
    ['Rice Face Wash 100 ml','₹0.27 Cr'],['Rice Face Wash 50 ml','₹0.19 Cr'],
    ['ME Ubtan Natural Glow FW','₹0.14 Cr'],['Vitamin C Face Wash','₹0.09 Cr'],
    ['ME VitC Daily Glow FW','₹0.08 Cr'],['ME Ubtan FW 50 ml','₹0.08 Cr'],
    ['VitC Daily Glow Sunscreen 50 ml','₹0.08 Cr'],['ME Onion Hair Fall Control Shampoo','₹0.07 Cr'],
  ];
  arts.forEach((a,i)=>{
    const col=i%4, row=Math.floor(i/4);
    const x=M+col*3.22, y=5.00+row*.46;
    s.addShape(pres.ShapeType.rect,{x,y,w:3.14,h:.40,fill:{color:CARD},line:{color:NAVY2,pt:.2}});
    s.addText(a[0],{x:x+.08,y,w:2.40,h:.40,fontSize:8.5,color:WHITE,valign:'middle',margin:0,fontFace:'Calibri'});
    s.addText(a[1],{x:x+2.50,y,w:.60,h:.40,fontSize:9,bold:true,color:GOLD,valign:'middle',align:'right',margin:0,fontFace:'Calibri'});
  });
  s.addText('LEADERSHIP CALL  |  Protect top face-wash and sunscreen availability, reverse the 4.6% June–July softness, and retain >95% flow conversion as the account benchmark.',{
    x:M,y:5.92,w:W-2*M,h:.30,fontSize:9.5,color:LGREY,italic:true,fontFace:'Calibri',margin:0});

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 15 — NPI CONTRIBUTION
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,15);
  hdr(s,'NPI contributes ₹2.82 Cr; Reliance and DMart hold most of the value',
    'NPI contribution | Overall, zone and chain | July 2026');

  kpi(s,M,.92,4.00,.70,'₹2.82 Cr','NPI SALES','July offtake · 58/60 EANs active',CARD);
  kpi(s,M+4.08,.92,4.00,.70,'7.82%','CONTRIBUTION','of total sales',CARD);
  kpi(s,M+8.16,.92,4.00,.70,'58 / 60','SELLING EANs','2 require audit before loading',CARD,AMBER);

  s.addChart(pres.ChartType.bar,[
    {name:'NPI contribution (%)',labels:['North','South-1','West','East','South-2','Central'],values:[9.2,7.9,6.6,10.2,6.4,8.5]},
  ],{x:M,y:1.74,w:5.80,h:2.50,barDir:'bar',barGrouping:'clustered',
    chartColors:[TEAL],showLegend:false,
    showTitle:true,title:'Zone NPI contribution (%)',titleFontSize:8.5,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:8,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,plotAreaFillColor:BG,shadow:{type:'none'}});

  s.addChart(pres.ChartType.bar,[
    {name:'NPI sales (₹ lakh)',labels:['Reliance','DMart','Lulu','FSN/Nykaa','H&G','Metro','WF'],values:[130.5,97.7,18.0,12.9,5.9,5.0,3.7]},
  ],{x:M+5.88,y:1.74,w:6.95,h:2.50,barDir:'bar',barGrouping:'clustered',
    chartColors:[GOLD],showLegend:false,
    showTitle:true,title:'Chain NPI sales (₹ lakh)',titleFontSize:8.5,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:8,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,plotAreaFillColor:BG,shadow:{type:'none'}});

  sh(s,M,4.34,8.50,.24,'TOP NPI ARTICLES');
  const npiArts=[
    ['1. ME Onion Hair Fall Control Shampoo','₹0.31 Cr'],
    ['2. ME Onion Hair Oil 200 ml','₹0.30 Cr'],
    ['3. ME Gentle Cleansing Shampoo 400 ml','₹0.21 Cr'],
    ['4. ME Multani Mitti Face Wash 100 ml','₹0.20 Cr'],
    ['5. ME Vitamin C Daily Glow Sunscreen','₹0.20 Cr'],
    ['6. ME Lemon Anti-Dandruff Shampoo','₹0.19 Cr'],
    ['7. Rosemary Anti-Hair Fall Shampoo','₹0.18 Cr'],
    ['8. ME Rice Water Dewy Sunscreen 80 ml','₹0.18 Cr'],
  ];
  npiArts.forEach((a,i)=>{
    const col=i%4, row=Math.floor(i/4);
    const x=M+col*2.16, y=4.62+row*.44;
    s.addShape(pres.ShapeType.rect,{x,y,w:2.10,h:.38,fill:{color:CARD},line:{color:NAVY2,pt:.2}});
    s.addText(a[0],{x:x+.06,y,w:1.56,h:.38,fontSize:7.5,color:WHITE,valign:'middle',margin:0,fontFace:'Calibri'});
    s.addText(a[1],{x:x+1.60,y,w:.46,h:.38,fontSize:8,bold:true,color:GOLD,valign:'middle',align:'right',margin:0});
  });

  sh(s,M+8.56,4.34,4.52,.24,'ZERO-SALE EANs (AUDIT REQUIRED)',WHITE);
  s.addShape(pres.ShapeType.rect,{x:M+8.56,y:4.62,w:4.52,h:.80,fill:{color:'180808'},line:{color:RED,pt:.4}});
  bl(s,M+8.56,4.62,4.52,.80,[
    'BBLUNT Cherry Red Hair Colour 130g',
    'TDC 20% Actives Peptide–Stem Cell Hair Serum',
    'Audit listing, stock receipt, OSA and launch visibility before further loading.',
  ],{fs:9,col:RED});

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 16 — CHAIN DEEP DIVE: PRIMARY vs OFFTAKE
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,16);
  hdr(s,'DMart and Reliance hold most of the convertible chain gap',
    'Chain deep dive | July 2026 | ₹ Cr');

  s.addChart(pres.ChartType.bar,[
    {name:'Primary',labels:['DMart','Reliance','Apollo','FSN/Nykaa','Lulu','WF','H&G','Metro'],
      values:[18.25,15.66,7.20,2.08,0,0.49,0.22,1.84]},
    {name:'Offtake',labels:['DMart','Reliance','Apollo','FSN/Nykaa','Lulu','WF','H&G','Metro'],
      values:[13.97,8.06,7.18,2.07,1.70,0.72,0.51,0.49]},
  ],{x:M,y:1.02,w:8.10,h:3.40,barDir:'bar',barGrouping:'clustered',
    chartColors:[GOLD,TEAL],showLegend:true,legendPos:'b',legendFontSize:8,legendFontColor:LGREY,
    showTitle:true,title:'Top chain flow (₹ Cr)',titleFontSize:9,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:7.5,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,plotAreaFillColor:BG,shadow:{type:'none'}});

  const rx=M+8.18, rw=4.90;
  sh(s,rx,1.02,rw,.24,'ACCOUNT SIGNALS');
  kpi(s,rx,1.30,rw,.64,'₹4.29 Cr','DMART GAP','76.5% conversion',CARD,RED);
  kpi(s,rx,1.98,rw,.64,'₹7.61 Cr','RELIANCE GAP','51.4% conversion','180A0A',RED);
  kpi(s,rx,2.66,rw,.64,'99.7%','APOLLO','Near flow parity · replicate cadence',CARD,GREEN);
  kpi(s,rx,3.34,rw,.64,'99.4%','FSN/NYKAA','5.7% of total · benchmark conversion',CARD,GREEN);

  sh(s,M,4.50,12.83,.24,'ACCOUNT PLAN');
  bl(s,M,4.78,12.83,2.00,[
    'DMart: attack South-2 first, then North; review top-SKU store availability and DC-to-store fill. (Gap ₹4.29 Cr @ 76.5% conv)',
    'Reliance: prioritize North and East; convert billed inventory through chain-specific hero-SKU visibility and replenishment. (Gap ₹7.61 Cr @ 51.4% conv)',
    'Apollo: protect cadence and replicate its near-parity review rhythm across strategic accounts. (99.7% conv — the standard)',
    'Chains above 100% conversion cannot be called over-converted without opening stock; investigate distributor and timing coverage.',
    'Metro: stop range expansion until sales/SKU and store productivity recover. Gap ₹1.36 Cr; 26.3% conversion.',
    'RECOVER: ₹11.89 Cr DMart + Reliance combined gap · REPLICATE: Apollo 99.7% · CONTROL: >100% = stock/timing signal',
  ],{fs:9.5});

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 17 — BRAND AND SUB-CATEGORY ARCHITECTURE
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,17);
  hdr(s,'Face care powers two-thirds of offtake; brand conversion is concentrated in two engines',
    'Brand and sub-category architecture | July 2026');

  s.addChart(pres.ChartType.bar,[
    {name:'Primary',labels:['Mamaearth','The Derma Co.','Aqualogica','BBlunt','Dr. Sheth\'s'],values:[33.38,15.19,0.41,0.18,0]},
    {name:'Offtake', labels:['Mamaearth','The Derma Co.','Aqualogica','BBlunt','Dr. Sheth\'s'],values:[24.49,11.03,0.48,0.06,0.03]},
  ],{x:M,y:1.02,w:5.30,h:2.70,barDir:'bar',barGrouping:'clustered',
    chartColors:[GOLD,TEAL],showLegend:true,legendPos:'b',legendFontSize:8,legendFontColor:LGREY,
    showTitle:true,title:'Brand primary vs offtake (₹ Cr)',titleFontSize:9,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:7.5,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,plotAreaFillColor:BG,shadow:{type:'none'}});

  const months=['Feb 26','Mar 26','Apr 26','May 26','Jun 26','Jul 26'];
  s.addChart(pres.ChartType.bar,[
    {name:'Face Cleanser',labels:months,values:[7.03,8.17,8.55,9.63,9.65,8.53]},
    {name:'Shampoo',      labels:months,values:[4.81,5.38,6.11,6.68,6.87,6.95]},
    {name:'Sun Care',     labels:months,values:[1.55,2.73,3.10,2.95,1.99,1.30]},
  ],{x:M+5.38,y:1.02,w:3.70,h:2.70,barDir:'col',barGrouping:'clustered',
    chartColors:[GOLD,TEAL,RED],showLegend:true,legendPos:'b',legendFontSize:7,legendFontColor:LGREY,
    showTitle:true,title:'Mamaearth — top 3 sub-categories',titleFontSize:8,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:6,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,plotAreaFillColor:BG,shadow:{type:'none'}});

  s.addChart(pres.ChartType.bar,[
    {name:'Face Cleanser',labels:months,values:[2.25,2.75,3.24,4.63,4.83,7.13]},
    {name:'Sun Care',     labels:months,values:[1.04,1.81,2.27,3.18,2.05,1.99]},
    {name:'Face Serum',   labels:months,values:[0.56,0.57,0.69,0.66,0.66,0.63]},
  ],{x:M+9.16,y:1.02,w:3.70,h:2.70,barDir:'col',barGrouping:'clustered',
    chartColors:[GOLD,TEAL,RED],showLegend:true,legendPos:'b',legendFontSize:7,legendFontColor:LGREY,
    showTitle:true,title:'The Derma Co. — top 3 sub-categories',titleFontSize:8,titleColor:LGREY,
    dataLabelPosition:'outEnd',showValue:true,dataLabelFontSize:6,dataLabelColor:WHITE,
    valGridLine:{style:'none'},catGridLine:{style:'none'},
    valAxisLabelColor:LGREY,catAxisLabelColor:LGREY,plotAreaFillColor:BG,shadow:{type:'none'}});

  sh(s,M,3.82,12.83,.24,'PORTFOLIO IMPLICATIONS');
  bl(s,M,4.10,12.83,2.70,[
    'Mamaearth contributes 67.8% of offtake and converts at 73.4%.',
    'The Derma Co. adds ₹11.03 Cr but carries a ₹4.16 Cr flow gap.',
    'Mamaearth Face Cleanser closes July at ₹8.53 Cr; protect its hero EAN availability.',
    'The Derma Co. Face Cleanser closes July at ₹7.13 Cr; sustain productive distribution.',
    'TDC Face Cleanser +47.6% MoM (₹4.83→₹7.13 Cr) — fastest growing sub-category in portfolio.',
    'Aqualogica above 100% conversion signals stock/timing effects; validate availability before additional loading.',
    'Shampoo holds steady at ₹6.95 Cr; MoM stable in Jul despite peak Sun Care season ending.',
    'Sun Care declining naturally after peak (₹3.10→₹1.30 Cr); not a share loss — seasonal rotation expected.',
  ],{fs:9.5});

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 18 — 90-DAY ACTION PLAN
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,18);
  hdr(s,'A 90-day operating cadence can convert the gap without indiscriminate loading',
    'Sales uplift plan | owners, actions and proof points');

  const phases=[
    {label:'0–30 DAYS',color:RED,items:[
      'Reconcile SAH / WD / PDO / OOS fields across all chains',
      'Publish state × chain × hero-EAN gaps for North and East',
      'Find stores missing Rice / Ubtan / Onion / Rosemary heroes',
      'Stop loading weak-conversion exceptions (Reliance North/East)',
    ]},
    {label:'31–60 DAYS',color:AMBER,items:[
      'Size white space in ₹ using productive stores × PDO',
      'Run pack and hero-SKU controlled pilots in test chains',
      'Test share-transfer causes in declining markets',
      'Replicate Apollo flow cadence across mid-tier chains',
    ]},
    {label:'61–90 DAYS',color:GREEN,items:[
      'Scale only proven state × chain × SKU cells',
      'Reset load rules by verified conversion',
      'Rationalize dead/low-productivity packs',
      'Embed weekly owner and action receipts in all zone reviews',
    ]},
  ];

  phases.forEach((p,i)=>{
    const x=M+i*4.30, y=1.02, w=4.20, h=3.40;
    s.addShape(pres.ShapeType.rect,{x,y,w,h,fill:{color:CARD},line:{color:p.color,pt:.5}});
    s.addShape(pres.ShapeType.rect,{x,y,w,h:.30,fill:{color:p.color},line:{type:'none'}});
    s.addText(p.label,{x,y,w,h:.30,fontSize:10,bold:true,color:WHITE,align:'center',valign:'middle',margin:0});
    p.items.forEach((item,j)=>{
      s.addShape(pres.ShapeType.ellipse,{x:x+.12,y:y+.44+j*.70,w:.22,h:.22,fill:{color:p.color},line:{type:'none'}});
      s.addText(String(j+1),{x:x+.12,y:y+.44+j*.70,w:.22,h:.22,fontSize:8,bold:true,color:WHITE,align:'center',valign:'middle',margin:0});
      s.addText(item,{x:x+.40,y:y+.38+j*.70,w:w-.50,h:.58,fontSize:9.5,color:LGREY,fontFace:'Calibri',valign:'middle',margin:0});
    });
  });

  sh(s,M,4.52,12.83,.26,'WEEKLY MANAGEMENT SCOREBOARD');
  const scorecard=[
    {metric:'Flow conversion',target:'>90%',owner:'Sales lead'},
    {metric:'North gap',target:'↓ weekly',owner:'North ZSM'},
    {metric:'East gap',target:'↓ weekly',owner:'East ZSM'},
    {metric:'Hero-SKU OSA',target:'>95%',owner:'KAM + Supply'},
    {metric:'DMart / Reliance gap',target:'Close 50%',owner:'KAMs'},
    {metric:'Data exceptions',target:'0 unresolved',owner:'Analytics'},
  ];
  scorecard.forEach((sc,i)=>{
    const col=i%3, row=Math.floor(i/3);
    const x=M+col*4.30, y=4.82+row*.60;
    s.addShape(pres.ShapeType.rect,{x,y,w:4.20,h:.54,fill:{color:CARD},line:{color:NAVY2,pt:.3}});
    s.addText(sc.metric,{x:x+.1,y,w:2.00,h:.54,fontSize:9.5,color:WHITE,valign:'middle',margin:0,fontFace:'Calibri'});
    s.addText(sc.target,{x:x+2.10,y,w:1.00,h:.54,fontSize:10,bold:true,color:GREEN,valign:'middle',align:'center',margin:0});
    s.addText(sc.owner,{x:x+3.12,y,w:1.00,h:.54,fontSize:8.5,color:GOLD,valign:'middle',align:'right',margin:0});
  });

  ft(s,SRC);
})();

// ──────────────────────────────────────────────────────────────────────────────
// SLIDE 19 — GOVERNANCE / AUDIT
// ──────────────────────────────────────────────────────────────────────────────
(()=>{
  const s=pres.addSlide(); bg(s); badge(s,19);
  hdr(s,'Decision-safe definitions, quality gates and authority boundaries',
    'Audit command center | source coverage, interpretation and controlled execution');

  s.addText('Use the deck to prioritize investigation and owner action — not to infer inventory, causality or autonomous execution.',{
    x:M,y:.92,w:W-2*M,h:.28,fontSize:10,bold:true,color:GOLD,italic:true,margin:0});
  s.addText('Every consequential commercial change remains subject to named human approval.',{
    x:M,y:1.18,w:W-2*M,h:.24,fontSize:9.5,color:LGREY,margin:0});

  kpi(s,M,1.48,4.00,.70,'₹49.21 Cr','PRIMARY','Invoice net value · July primary sheet · Converted to ₹ Cr',CARD);
  kpi(s,M+4.08,1.48,4.00,.70,'₹36.10 Cr','OFFTAKE','July transaction NSV · Compiled offtake source',CARD);
  kpi(s,M+8.16,1.48,4.00,.70,'73.4%','FLOW CONVERSION','Offtake ÷ Primary · Comparable mapped cuts only',CARD);

  const gates=[
    {h:'SOURCE COVERAGE',items:['31,355 / 197,740 primary / offtake rows','Missing zone rows: 0','Period: July 2026']},
    {h:'DECISION FOCUS',items:['Rank material conversion gaps','Protect proven demand signals','Verify availability before loading']},
    {h:'ACCOUNT MAPPING',items:['₹2.07 Cr FSN + Nykaa SS combined','Article-level account view','Pan India flow handled separately']},
    {h:'DIAGNOSTIC GATE',items:['Reconcile SAH / WD / PDO / OOS first','Stock pressure and turnover not measured here','No measured claim before state-chain validation']},
    {h:'HUMAN APPROVAL',items:['AI recommends and sizes — humans approve','NKAM / RKAM / KAM approve loading, range and distribution','Revoke or stop when proof fails']},
    {h:'ACTION RECEIPT',items:['Record what changed and state evidence and authority','Track closure and outcome','Revoke or stop when proof fails']},
  ];
  gates.forEach((g,i)=>{
    const col=i%3, row=Math.floor(i/3);
    const x=M+col*4.30, y=2.30+row*2.00, w=4.20, h=1.88;
    s.addShape(pres.ShapeType.rect,{x,y,w,h,fill:{color:CARD},line:{color:NAVY2,pt:.3}});
    sh(s,x,y,w,.24,g.h);
    bl(s,x,y+.28,w,h-.30,g.items,{fs:9});
  });

  s.addText('DEMAND · protect hero SKUs    DISTRIBUTION · close chain-zone gaps    CONVERSION · move toward >90%    GOVERNANCE · weekly EAN review',{
    x:M,y:6.50,w:W-2*M,h:.28,fontSize:9,color:GOLD,bold:true,align:'center',margin:0});

  ft(s,'Source: pipeline v2.4.0 · July Offtake + Primary.xlsb · 2026-08-19 | Human approval required before consequential commercial execution.');
})();

// ──────────────────────────────────────────────────────────────────────────────
// WRITE
// ──────────────────────────────────────────────────────────────────────────────
pres.writeFile({fileName:'MT_Jul26_CommandCenter.pptx'})
  .then(()=>console.log('✓  MT_Jul26_CommandCenter.pptx written'))
  .catch(e=>{ console.error(e); process.exit(1); });
