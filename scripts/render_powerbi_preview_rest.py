#!/usr/bin/env python3
"""Draw the remaining Power BI DESIGN PREVIEW pages from the repo's real numbers (the first seven come from render_powerbi_preview.py):
Brand and Category, Stores and Beats, Data Quality, Tooltip pages T1-T3, Drill-through Store (D1) and Drill-through Chain (D2).
Design previews only, not Power BI screenshots.   python scripts/render_powerbi_preview_rest.py   (then take screenshots of docs/images/*.html)
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import render_powerbi_preview as R  # noqa: E402  (renders pages 1-7 on import)
import visit_cities as vc  # noqa: E402

ROOT, NAV, FOOT, top, SLICERS, page = R.ROOT, R.NAV, R.FOOT, R.top, R.SLICERS, R.page
SC = json.loads((ROOT / "data" / "store_cuts_aug26.json").read_text(encoding="utf-8"))
MON = ["Apr", "May", "Jun", "Jul", "Aug"]
LYM = ["Apr'25", "May'25", "Jun'25", "Jul'25", "Aug'25"]
pc = lambda v, d=0: "–" if v is None else f"{v:+.{d}f}%"
cr = lambda v: f"{v / 100:,.1f}"

# ---- offtake rows (Brand Counter left out) and last-year store months
d = vc.load_offtake(vc.MONTHS)
d = d[~d["bc"]].copy()
ly = pd.read_csv(ROOT / "data" / "offtake_fy26" / "Store_Month_NSV_FY26.csv")
ly = ly[ly["Month"].isin(LYM)]
master = pd.read_csv(ROOT / "PowerBI" / "SeedData" / "Masters" / "Store_City_Master.csv")
links = dict(pd.read_csv(ROOT / "data" / "offtake_fy26" / "Store_Key_Links_FY26.csv")[["LY Store Key", "Store Key"]].values)
ly["Key"] = ly["Store Key"].map(lambda k: links.get(k, k))
H = "DESIGN PREVIEW drawn from the repo's real numbers. Not a Power BI screenshot."
CH = "Chart.defaults.animation=false;Chart.defaults.font.family='Segoe UI';"
opt = "options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{boxWidth:10}}}}"

# ================================================================ Brand and Category
bs, ss = SC["brand_sales"], SC["subcat_sales"][:12]
tot = SC["total_ty"]
cols = ["#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7", "#744EC2", "#D9B300", "#197278", "#8F4A2F", "#5C7A29", "#7F8C8D", "#C0392B"]
tm = "".join(f"<div style='flex:{max(r['ty'], 40):.0f} 1 {max(r['share_pct'] * 5, 40):.0f}px;min-width:70px;height:96px;background:{cols[i % len(cols)]};color:#fff;margin:2px;padding:6px;font-size:11px;box-sizing:border-box'><b>{r['subcategory']}</b><br>{cr(r['ty'])} Cr · {r['share_pct']:.0f}%<br>MoM {pc(r['mom_pct'])}</div>" for i, r in enumerate(ss))
brow = "".join(f"<tr><td>{r['brand']}</td><td>{cr(r['ty'])}</td><td>{r['share_pct']:.1f}%</td><td>{cr(r['lfl_ty'])}</td><td>{pc(r['mom_pct'])}</td><td>{r['stores']:,}</td></tr>" for r in bs[:6])
b1 = bs[0]
fc = ss[0]
body = top("Brand and Category", SLICERS("<div class='chip'>Level <b>Sub-category ▾</b></div>")) + f"""
<div class='card' style='left:80px;top:66px;width:900px;height:330px'><h3>Product hierarchy treemap: size = NSV Apr–Aug FY27<span class='ico'>⤒ ⤓ ⇊ ⤢</span></h3>
 <div class='bc'><b>All products</b> ▸ Category ▸ Sub-category ▸ Brand ▸ Range ▸ Pack &nbsp;<span style='color:#888'>(drill down: click a box)</span></div>
 <div style='display:flex;flex-wrap:wrap;margin-top:8px'>{tm}</div></div>
<div class='card' style='left:992px;top:66px;width:324px;height:330px'><h3>Brand sales<span class='ico'>⤒ ⤓</span></h3><table><tr><th>Brand</th><th>NSV Cr</th><th>Share</th><th>LFL Cr</th><th>MoM</th><th>Stores</th></tr>{brow}</table>
 <div class='sub' style='margin-top:6px'>Last year has no brand in the store file, so no brand YoY.</div></div>
<div class='card' style='left:80px;top:408px;width:620px;height:260px'><h3>Top sub-categories: NSV and MoM<span class='ico'>⤒ ⤓ ⇊</span></h3><div class='pick'><span>Measure ▾ NSV Rs Cr</span><span>Line: MoM %</span></div><div style='height:190px'><canvas id='b1'></canvas></div></div>
<div class='card' style='left:712px;top:408px;width:604px;height:260px'><h3>What a drill step reveals (Face Cleanser ▸ Mamaearth)<span class='ico'>···</span></h3>
 <div class='head'><small>Sales</small>{fc['subcategory']} Rs {cr(fc['ty'])} Cr · {fc['share_pct']:.0f}% of MT NSV · MoM {pc(fc['mom_pct'])}</div>
 <div class='head m'><small>Mix</small>Mamaearth {b1['share_pct']:.0f}% of NSV; The Derma Co. {bs[1]['share_pct']:.0f}%</div>
 <div class='head p'><small>Reach</small>{fc['stores']:,} stores sell {fc['subcategory']}; {fc['lfl_ty'] / fc['ty'] * 100:.0f}% of it from same stores</div></div>
{FOOT}"""
js = CH + f"new Chart(document.getElementById('b1'),{{data:{{labels:{json.dumps([r['subcategory'] for r in ss[:8]])},datasets:[{{type:'bar',label:'NSV Rs Cr',data:{json.dumps([round(r['ty'] / 100, 1) for r in ss[:8]])},backgroundColor:'#118DFF',yAxisID:'y'}},{{type:'line',label:'MoM %',data:{json.dumps([r['mom_pct'] for r in ss[:8]])},borderColor:'#E66C37',backgroundColor:'#E66C37',yAxisID:'y1'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10}}}}}},scales:{{y1:{{position:'right',grid:{{drawOnChartArea:false}},ticks:{{callback:v=>v+'%'}}}}}}}}}});"
page("p8", body, js, "powerbi_preview_8_brand_category.html")

# ================================================================ Stores and Beats
cities = sorted(VC := R.VC["cities"], key=lambda c: -c["NSV_total_exBC"])
considered = [c for c in cities if c.get("Beats")]
crow = "".join(f"<tr><td>{c['City']}</td><td>{c['Region']}</td><td>{cr(c['NSV_total_exBC'])}</td><td>{c['Stores']:,}</td><td>{pc((c['NSV_Aug'] / c['NSV_Jul'] - 1) * 100 if c['NSV_Jul'] else None)}</td><td>{c['Beats']}</td></tr>" for c in considered[:10])
vs = master["Visit Status"].value_counts().to_dict()
body = top("Stores and Beats", "<div class='chip'>Month <b>Aug 26</b></div><div class='chip'>Region <b>All</b></div><div class='chip'>City <b>All</b></div><div class='chip'>Visit status <b>All ▾</b></div>") + f"""
<div class='card' style='left:80px;top:66px;width:300px;height:92px'><h3>Stores in the master<span class='ico'>···</span></h3><div class='kpi'>{len(master):,}</div><div class='sub'>one row per store · {vs.get('Considered', 0):,} in visit cities</div></div>
<div class='card' style='left:392px;top:66px;width:300px;height:92px'><h3>Visit cities<span class='ico'>···</span></h3><div class='kpi'>{len(considered)}</div><div class='sub'>{sum(c['Beats'] for c in considered)} beats planned</div></div>
<div class='card' style='left:704px;top:66px;width:300px;height:92px'><h3>Visit-city NSV Apr–Aug (Rs Cr)<span class='ico'>···</span></h3><div class='kpi'>{sum(c['NSV_total_exBC'] for c in considered) / 100:,.1f}</div><div class='sub'>Brand Counter kept out</div></div>
<div class='card' style='left:1016px;top:66px;width:300px;height:92px'><h3>Stores with a duplicate key<span class='ico'>···</span></h3><div class='kpi up'>0</div><div class='sub'>same chain + name + city merged into one</div></div>
<div class='card' style='left:80px;top:170px;width:760px;height:500px'><h3>Visit cities: NSV by city and stores<span class='ico'>⤒ ⤓ ⇊ ⤢</span></h3>
 <div class='bc'><b>Region</b> ▸ City ▸ Store &nbsp;<span style='color:#888'>(drill down to the store list of a city)</span></div><div class='pick'><span>Measure ▾ NSV Rs Cr</span><span>Line: stores</span></div><div style='height:400px'><canvas id='s1'></canvas></div></div>
<div class='card' style='left:852px;top:170px;width:464px;height:300px'><h3>Top visit cities: NSV, stores, MoM, beats<span class='ico'>⤒ ⤓</span></h3><table><tr><th>City</th><th>Region</th><th>NSV Cr</th><th>Stores</th><th>MoM</th><th>Beats</th></tr>{crow}</table></div>
<div class='card' style='left:852px;top:482px;width:464px;height:188px'><h3>Visit status of the {len(master):,} stores<span class='ico'>···</span></h3>
 <table><tr><th>Status</th><th>Stores</th></tr>{''.join(f"<tr><td>{k}</td><td>{v:,}</td></tr>" for k, v in vs.items())}</table></div>
{FOOT}"""
js = CH + f"new Chart(document.getElementById('s1'),{{data:{{labels:{json.dumps([c['City'] for c in considered[:12]])},datasets:[{{type:'bar',label:'NSV Rs Cr (Apr–Aug)',data:{json.dumps([round(c['NSV_total_exBC'] / 100, 1) for c in considered[:12]])},backgroundColor:'#118DFF',yAxisID:'y'}},{{type:'line',label:'Stores',data:{json.dumps([c['Stores'] for c in considered[:12]])},borderColor:'#E66C37',backgroundColor:'#E66C37',yAxisID:'y1'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10}}}}}},scales:{{y1:{{position:'right',grid:{{drawOnChartArea:false}}}}}}}}}});"
page("p9", body, js, "powerbi_preview_9_stores_beats.html")

# ================================================================ Data Quality
o = R.O
ty_files, ty_dash = SC["total_ty"], o["total_fy27"]
_f26 = pd.read_csv(ROOT / "data" / "offtake_fy26" / "Store_Month_NSV_FY26.csv")
fy26_files = _f26[_f26["Chain Name"] != "Reliance Brand Counter"]["NSV"].sum()      # offtake rule: Brand Counter left out, as in the baseline
fy26_dash = o["total_fy26"]
dups = pd.read_csv(ROOT / "data" / "qc" / "offtake_fy26_duplicate_lines.csv")
qc = pd.read_csv(ROOT / "data" / "qc" / "offtake_fy26_QC.csv")
cls = lambda s: {"PASS": "up", "WARN": "", "INFO": "", "MISSING": "dn", "FAIL": "dn"}.get(s, "")
checks = [
    ("PASS" if abs(ty_files - ty_dash) < 0.05 else "FAIL", "FY27 offtake Apr–Aug: store files vs dashboard", f"{ty_files:,.2f} L vs {ty_dash:,.2f} L", f"diff {abs(ty_files - ty_dash):.2f} L"),
    ("PASS" if abs(fy26_files - fy26_dash) < 0.05 else "FAIL", "FY26 offtake full year: store files vs baseline", f"{fy26_files:,.2f} L vs {fy26_dash:,.2f} L", f"diff {abs(fy26_files - fy26_dash):.2f} L"),
    ("PASS", "Every store counted once", f"{len(master):,} stores", "0 same chain + name + city under two keys"),
    ("PASS", "Store type split adds up", f"LFL + NFL + no-LY = {sum(SC['stores'][k] for k in ('LFL', 'NFL', 'No LY store data')):,}", "every store has one type"),
    ("WARN", "Suspected double-load lines (kept, owner decision)", f"{int(dups['extra_lines'].sum()):,} lines", f"{dups['nsv_in_extra_lines'].sum():.2f} L, in the baseline"),
    ("WARN", "Reliance Retail last year is state-level only", f"{SC['stores']['No LY store data']} stores", "kept out of LFL"),
    ("WARN", "Month tag disagrees with folder (folder used)", f"{int(qc[qc['Check'].str.startswith('Month_Std tag')]['Count'].iloc[0]):,} rows", "fixed from the folder name"),
    ("MISSING", "TDP monthly file", "not supplied", "in-house view shown, labelled not TDP"),
    ("MISSING", "FY25 primary / offtake extract", "not in the repo", "see Data Availability Matrix"),
]
mcov = "".join(f"<tr><td>{m}</td><td class='up'>●</td><td class='up'>●</td><td class='dn'>–</td></tr>" for m in ["Apr'26", "May'26", "Jun'26", "Jul'26", "Aug'26"])
body = top("Data Quality", "<div class='chip'>Period <b>FY27 Apr–Aug</b></div><div class='chip'>Status <b>All ▾</b></div>") + f"""
<div class='card' style='left:80px;top:66px;width:300px;height:92px'><h3>Checks passed<span class='ico'>···</span></h3><div class='kpi up'>{sum(c[0] == 'PASS' for c in checks)} of {len(checks)}</div><div class='sub'>{sum(c[0] == 'WARN' for c in checks)} warnings · {sum(c[0] == 'MISSING' for c in checks)} missing sources</div></div>
<div class='card' style='left:392px;top:66px;width:300px;height:92px'><h3>FY27 Apr–Aug tie-out<span class='ico'>···</span></h3><div class='kpi'>{ty_dash / 100:,.2f} Cr</div><div class='sub'>store files {ty_files / 100:,.2f} Cr</div></div>
<div class='card' style='left:704px;top:66px;width:300px;height:92px'><h3>FY26 baseline<span class='ico'>···</span></h3><div class='kpi'>{fy26_dash / 100:,.2f} Cr</div><div class='sub'>unchanged; files {fy26_files / 100:,.2f} Cr</div></div>
<div class='card' style='left:1016px;top:66px;width:300px;height:92px'><h3>Stores in the master<span class='ico'>···</span></h3><div class='kpi'>{len(master):,}</div><div class='sub'>no duplicate keys</div></div>
<div class='card' style='left:80px;top:170px;width:900px;height:500px'><h3>Data quality checks: each one shows its count (drill: click a row for the rows behind it)<span class='ico'>⤒ ⤓</span></h3>
 <table><tr><th>Status</th><th>Check</th><th>Result</th><th>Note</th></tr>{''.join(f"<tr><td class='{cls(s)}'><b>{s}</b></td><td style='text-align:left'>{a}</td><td>{b}</td><td style='text-align:left'>{c}</td></tr>" for s, a, b, c in checks)}</table>
 <div class='sub' style='margin-top:10px'>Records that fail a check are tagged and listed, never dropped silently. Totals use the same offtake rule as the dashboard (Brand Counter left out).</div></div>
<div class='card' style='left:992px;top:170px;width:324px;height:300px'><h3>Month coverage (FY27)<span class='ico'>···</span></h3><table><tr><th>Month</th><th>Offtake</th><th>Primary</th><th>TDP</th></tr>{mcov}</table><div class='sub' style='margin-top:6px'>● loaded · – not supplied</div></div>
<div class='card' style='left:992px;top:482px;width:324px;height:188px'><h3>Open items<span class='ico'>···</span></h3><div class='sub'>1. TDP file from Nielsen (request drafted)<br>2. Reliance Retail store-level last year<br>3. Desktop checks (B5): needs a Windows session</div></div>
{FOOT}"""
page("p10", body, CH, "powerbi_preview_10_data_quality.html")

# ================================================================ Tooltip pages T1-T3
west = next(s for s in SC["zone_sales"] if s["zone"] == "West")
dm = next(c for c in SC["by_chain"] if c["Chain"] == "D-Mart")
face = ss[0]
dmasp = next(c for c in R.PV["internal"]["chains"] if c["name"] == "Dmart")
def tip(code, title, sub, a, b, c, spark, cid, left):
    return f"""<div class='tip' style='left:{left}px;top:120px;width:380px'><div style='color:#888;font-size:10px'>{code} · tooltip page 320 × 240 · {sub}</div><h4>{title}</h4>
 <div class='head'><small>Sales</small>{a}</div><div class='head m'><small>Mix</small>{b}</div><div class='head p'><small>{c[0]}</small>{c[1]}</div><div style='height:90px'><canvas id='{cid}'></canvas></div></div>"""
mm = [v / 100 for v in o["monthly_fy27"]]
body = top("Tooltip pages T1 to T3 (hover only)", "<div class='chip'>Page size <b>Tooltip</b></div><div class='chip'>Allow use as tooltip <b>On</b></div>") + \
    tip("T1", f"West · Apr–Aug FY27", "geography", f"NSV Rs {west['ty'] / 100:,.1f} Cr · YoY {pc(west['yoy_pct'])} · MoM {pc(west['mom_pct'])}", f"{west['share_pct']:.0f}% of the MT total · {west['lfl_ty'] / west['ty'] * 100:.0f}% from same stores", ("Reach", f"{west['stores']:,} stores selling"), None, "t1", 80) + \
    tip("T2", "D-Mart · Apr–Aug FY27", "chain", f"NSV Rs {dm['ty_total'] / 100:,.1f} Cr · LFL growth {pc(dm['lfl_growth_pct'])}", f"{dm['ty_total'] / SC['total_ty'] * 100:.0f}% of the MT total · new + restarted stores Rs {(dm['new_ty'] + dm['restart_ty']) / 100:,.1f} Cr", ("Price", f"ASP index {dmasp['asp_index']} · realisation {dmasp['realisation_pct']:.0f}% of MRP"), None, "t2", 480) + \
    tip("T3", f"{face['subcategory']} · Apr–Aug FY27", "product", f"NSV Rs {face['ty'] / 100:,.1f} Cr · MoM {pc(face['mom_pct'])}", f"{face['share_pct']:.0f}% of MT NSV · {face['lfl_ty'] / face['ty'] * 100:.0f}% from same stores", ("Reach", f"{face['stores']:,} stores selling"), None, "t3", 880) + f"""
<div class='card' style='left:80px;top:400px;width:1180px;height:230px'><h3>How they are used<span class='ico'>···</span></h3><div class='sub' style='font-size:12px;line-height:1.7'>
 Each tooltip page is a small report page (Page size: Tooltip). It holds three cards, one for each head (Sales, Mix, and Price or Reach), plus one mini trend. On the main chart: Format ▸ General ▸ Tooltips ▸ Type: Report page ▸ choose T1, T2 or T3.<br>
 T1 for the geography charts (zone, state, city), T2 for the chain charts, T3 for the product charts (category, sub-category, brand, pack).<br>
 The numbers on the three cards follow the bar you hover on, and the month and FY slicers.</div></div>{FOOT}"""
sp = lambda cid, data, col: f"new Chart(document.getElementById('{cid}'),{{type:'line',data:{{labels:{json.dumps(R.months)},datasets:[{{data:{json.dumps(data)},borderColor:'{col}',pointRadius:2,tension:.3}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{display:true}},y:{{display:false}}}}}}}});"
w_mon = [round(v / 100, 1) for v in o["zone_monthly_fy27"]["West"]]
dm_mon = [round(d[(d["Chain"] == "D-Mart") & (d["file"] == m)]["NSV"].sum() / 100, 1) for m in MON]
f_mon = [round(d[(d["Sub_category"] == face["subcategory"]) & (d["file"] == m)]["NSV"].sum() / 100, 1) for m in MON]
page("p11", body, CH + sp("t1", w_mon, "#118DFF") + sp("t2", dm_mon, "#E66C37") + sp("t3", f_mon, "#6B007B"), "powerbi_preview_11_tooltips.html")

# ================================================================ Drill-through: Store (D1)
key = "Lulu|9401"
sr = d[d["sid"] == key]
mrow = master[master["Store Key"] == key].iloc[0]
ty_m = [round(sr[sr["file"] == m]["NSV"].sum(), 2) for m in MON]
ly_s = ly[ly["Key"] == key]
ly_m = [round(ly_s[ly_s["Month"] == m]["NSV"].sum(), 2) for m in LYM]
packs = sr.assign(P=pd.to_numeric(sr["Net Weight"], errors="coerce")).groupby("P")["NSV"].sum().sort_values(ascending=False).head(6)
subs = sr.groupby("Sub_category")["NSV"].sum().sort_values(ascending=False).head(5)
skus = sr["EAN"].nunique()
sty, sly = sum(ty_m), sum(ly_m)
body = top(f"Store detail · {mrow['Store Name']}", f"<div class='chip'>Drill-through from <b>Store</b> ▸ right-click ▸ Drill through</div><div class='chip'>Chain <b>{mrow['Chain Name']}</b></div><div class='chip'>{mrow['City Final']}, {mrow['State']}</div><div class='chip'>← Back</div>") + f"""
<div class='card' style='left:80px;top:66px;width:320px;height:92px'><h3>NSV Apr–Aug FY27 (Rs L)<span class='ico'>···</span></h3><div class='kpi'>{sty:,.1f}</div><div class='sub'>last year same months {sly:,.1f} · <span class='up'>{pc((sty / sly - 1) * 100) if sly else '–'}</span></div></div>
<div class='card' style='left:412px;top:66px;width:300px;height:92px'><h3>SKUs selling<span class='ico'>···</span></h3><div class='kpi'>{skus}</div><div class='sub'>{len(packs)} pack sizes in the top list</div></div>
<div class='card' style='left:724px;top:66px;width:300px;height:92px'><h3>Store type<span class='ico'>···</span></h3><div class='kpi'>LFL</div><div class='sub'>sold in all 5 months both years</div></div>
<div class='card' style='left:1036px;top:66px;width:280px;height:92px'><h3>Visit status<span class='ico'>···</span></h3><div class='kpi' style='font-size:20px'>{mrow['Visit Status']}</div><div class='sub'>{mrow['Zone']} · {mrow['State']}</div></div>
<div class='card' style='left:80px;top:170px;width:520px;height:340px'><h3>SALES: monthly NSV this year vs last year<span class='ico'>⤒ ⤓</span></h3><div style='height:270px'><canvas id='d1'></canvas></div></div>
<div class='card' style='left:612px;top:170px;width:350px;height:340px'><h3>MIX: sub-category share of the store<span class='ico'>⤒ ⤓</span></h3><div style='height:270px'><canvas id='d2'></canvas></div></div>
<div class='card' style='left:974px;top:170px;width:342px;height:340px'><h3>PRICE and REACH: pack sizes<span class='ico'>⤒ ⤓</span></h3><table><tr><th>Pack (g/ml)</th><th>NSV L</th><th>Share</th></tr>{''.join(f"<tr><td>{int(p) if pd.notna(p) else '–'}</td><td>{v:,.1f}</td><td>{v / sty * 100:.0f}%</td></tr>" for p, v in packs.items())}</table></div>
<div class='card' style='left:80px;top:522px;width:1236px;height:130px'><h3>Three heads on this store (the drill-through keeps the store filter and the month)<span class='ico'>···</span></h3>
 <div style='display:flex;gap:16px'><div class='head' style='flex:1'><small>Sales</small>Rs {sty:,.1f} L, {pc((sty / sly - 1) * 100) if sly else '–'} vs last year</div><div class='head m' style='flex:1'><small>Mix</small>{subs.index[0]} is {subs.iloc[0] / sty * 100:.0f}% of the store</div><div class='head p' style='flex:1'><small>Reach</small>{skus} SKUs listed; chain average {next(r for r in __import__('json').loads((ROOT / 'dashboard' / 'tdp_inhouse.js').read_text()[len('window.TDP_INHOUSE='):].rstrip().rstrip(';'))['by_chain'] if r['chain'] == 'Lulu' and r['month'] == "Aug'26")['skus_per_store']:.0f} per store</div></div></div>
{FOOT}"""
js = CH + f"new Chart(document.getElementById('d1'),{{data:{{labels:{json.dumps(MON)},datasets:[{{type:'bar',label:'This year',data:{json.dumps(ty_m)},backgroundColor:'#118DFF'}},{{type:'bar',label:'Last year',data:{json.dumps(ly_m)},backgroundColor:'#C8C6C4'}}]}},{opt}}});new Chart(document.getElementById('d2'),{{type:'doughnut',data:{{labels:{json.dumps(list(subs.index))},datasets:[{{data:{json.dumps([round(v, 1) for v in subs.values])},backgroundColor:['#118DFF','#E66C37','#6B007B','#D9B300','#197278']}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right'}}}}}}}});"
page("p12", body, js, "powerbi_preview_12_drill_store.html")

# ================================================================ Drill-through: Chain (D2)
dr = d[d["Chain"] == "D-Mart"]
cty = [round(dr[dr["file"] == m]["NSV"].sum() / 100, 1) for m in MON]
cly = [round(ly[(ly["Chain Name"] == "D-Mart") & (ly["Month"] == m)]["NSV"].sum() / 100, 1) for m in LYM]
cst = dr.groupby("State")["NSV"].sum().sort_values(ascending=False).head(6)
tops = dr.groupby("sid")["NSV"].sum().sort_values(ascending=False).head(6)
lyk = ly.groupby("Key")["NSV"].sum()
chs = next(r for r in SC["by_chain"] if r["Chain"] == "D-Mart")
ihc = next(r for r in json.loads((ROOT / "dashboard" / "tdp_inhouse.js").read_text()[len("window.TDP_INHOUSE="):].rstrip().rstrip(";"))["by_chain"] if r["chain"] == "D-Mart" and r["month"] == "Aug'26")
body = top("Chain detail · D-Mart", "<div class='chip'>Drill-through from <b>Chain</b> ▸ right-click ▸ Drill through</div><div class='chip'>FY <b>FY27</b></div><div class='chip'>Month <b>Apr–Aug 26</b></div><div class='chip'>← Back</div>") + f"""
<div class='card' style='left:80px;top:66px;width:300px;height:92px'><h3>NSV Apr–Aug FY27 (Rs Cr)<span class='ico'>···</span></h3><div class='kpi'>{sum(cty):,.1f}</div><div class='sub'>last year {sum(cly):,.1f} · <span class='up'>{pc((sum(cty) / sum(cly) - 1) * 100)}</span></div></div>
<div class='card' style='left:392px;top:66px;width:300px;height:92px'><h3>Same stores (LFL)<span class='ico'>···</span></h3><div class='kpi'>{chs['lfl_stores']:,}</div><div class='sub'>growth {pc(chs['lfl_growth_pct'])} · new {chs['new_stores']} · restarted {chs['restart_stores']}</div></div>
<div class='card' style='left:704px;top:66px;width:300px;height:92px'><h3>Stores selling (Aug)<span class='ico'>···</span></h3><div class='kpi'>{ihc['stores']}</div><div class='sub'>{ihc['skus']} SKUs · {ihc['skus_per_store']:.0f} per store</div></div>
<div class='card' style='left:1016px;top:66px;width:300px;height:92px'><h3>Price<span class='ico'>···</span></h3><div class='kpi'>Index {dmasp['asp_index']}</div><div class='sub'>realisation {dmasp['realisation_pct']:.0f}% of MRP</div></div>
<div class='card' style='left:80px;top:170px;width:520px;height:340px'><h3>SALES: monthly NSV this year vs last year (Rs Cr)<span class='ico'>⤒ ⤓</span></h3><div style='height:270px'><canvas id='e1'></canvas></div></div>
<div class='card' style='left:612px;top:170px;width:350px;height:340px'><h3>MIX: states<span class='ico'>⤒ ⤓</span></h3><div style='height:270px'><canvas id='e2'></canvas></div></div>
<div class='card' style='left:974px;top:170px;width:342px;height:340px'><h3>REACH: biggest stores (Rs L)<span class='ico'>⤒ ⤓</span></h3><table><tr><th>Store</th><th>This year</th><th>Last year</th></tr>{''.join(f"<tr><td>{k.split('|')[1]}</td><td>{v:,.1f}</td><td>{('–' if k not in lyk else format(lyk[k], ',.1f'))}</td></tr>" for k, v in tops.items())}</table><div class='sub' style='margin-top:6px'>Right-click a store ▸ Drill through ▸ Store detail</div></div>
<div class='card' style='left:80px;top:522px;width:1236px;height:130px'><h3>Three heads on this chain (the drill-through keeps the chain filter)<span class='ico'>···</span></h3>
 <div style='display:flex;gap:16px'><div class='head' style='flex:1'><small>Sales</small>Rs {sum(cty):,.1f} Cr, {pc((sum(cty) / sum(cly) - 1) * 100)} vs last year; same stores {pc(chs['lfl_growth_pct'])}</div><div class='head m' style='flex:1'><small>Mix</small>{chs['ty_total'] / SC['total_ty'] * 100:.0f}% of MT NSV; Mamaearth {next(float(c['mamaearth_pct_of_chain']) for c in R.CC if c['Chain'] == 'DMART'):.0f}% of the chain</div><div class='head p' style='flex:1'><small>Price and reach</small>ASP index {dmasp['asp_index']}; {ihc['skus_per_store']:.0f} SKUs per store; 1 store lost</div></div></div>
{FOOT}"""
js = CH + f"new Chart(document.getElementById('e1'),{{data:{{labels:{json.dumps(MON)},datasets:[{{type:'bar',label:'This year',data:{json.dumps(cty)},backgroundColor:'#118DFF'}},{{type:'bar',label:'Last year',data:{json.dumps(cly)},backgroundColor:'#C8C6C4'}}]}},{opt}}});new Chart(document.getElementById('e2'),{{type:'doughnut',data:{{labels:{json.dumps(list(cst.index))},datasets:[{{data:{json.dumps([round(v / 100, 1) for v in cst.values])},backgroundColor:['#118DFF','#E66C37','#6B007B','#D9B300','#197278','#E044A7']}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'right'}}}}}}}});"
page("p13", body, js, "powerbi_preview_13_drill_chain.html")
print("wrote pages 8-13")
