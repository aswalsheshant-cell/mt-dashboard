#!/usr/bin/env python3
"""Draw the Power BI dynamic-dashboard DESIGN PREVIEW (two pages) from the repo's real numbers: HTML files in docs/images (screenshots are taken with Chromium).

This is a mock-up of the layout described in docs/POWERBI_DYNAMIC_DASHBOARD_BUILD.md, not a Power BI screenshot.
    python scripts/render_powerbi_preview.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
t = (ROOT / "dashboard" / "data.js").read_text()
O = json.loads(t[t.index("{"): t.rstrip().rstrip(";").rindex("}") + 1])["offtake"]
P = json.loads((ROOT / "data" / "nielsen_aug26.json").read_text(encoding="utf-8"))
PV = json.loads((ROOT / "data" / "nielsen" / "Price_Volume_Aug26.json").read_text(encoding="utf-8"))
CHART = (ROOT / "dashboard" / "chart.umd.js").read_text(encoding="utf-8").replace("</script", "<\\/script")

# ---- real numbers, Rs lakh -> Rs crore
months = O["months_fy27"]
nm = len(months)
zones = [z["name"] for z in O["by_zone"]]                      # all seven, Pan India included, so the zones add up to the MT total
ty = {z: sum(O["zone_monthly_fy27"][z][:nm]) / 100 for z in zones}
ly = {z: sum(O["zone_monthly_fy26"][z][:nm]) / 100 for z in zones}
yoy = {z: (ty[z] / ly[z] - 1) * 100 for z in zones}
order = sorted(zones, key=lambda z: -ty[z])
tot_ty, tot_ly = sum(ty.values()), sum(ly.values())
mt_ty = O["total_fy27"] / 100
mon = [v / 100 for v in O["monthly_fy27"]]
mom = [None] + [(mon[i] / mon[i - 1] - 1) * 100 for i in range(1, nm)]
ly_mon = [v / 100 for v in O["monthly_fy26"][:nm]]
yoy_m = [(mon[i] / ly_mon[i] - 1) * 100 for i in range(nm)]
growth = {z: ty[z] - ly[z] for z in zones}
w = "West"
zi = next(z for z in PV["internal"]["zones_cumulative"] if z["name"] == w)
states_w = sorted([(s["state"], s["fy27"] / 100) for s in O["by_state"] if s["zone"] == w], key=lambda x: -x[1])[:6]

CSS = """
*{box-sizing:border-box}body{margin:0;font-family:'Segoe UI',Arial,sans-serif;background:#EAEAEA;color:#252423;width:1500px;height:880px;position:relative;overflow:hidden}
.nav{position:absolute;left:0;top:0;bottom:0;width:62px;background:#2B2B2B;color:#ddd;font-size:10px;text-align:center;padding-top:10px}
.nav div{margin:12px 4px;padding:7px 0;border-radius:4px}.nav .on{background:#F2C811;color:#222;font-weight:600}
.top{position:absolute;left:62px;right:0;top:0;height:54px;background:#fff;border-bottom:1px solid #ccc;display:flex;align-items:center;padding:0 18px;gap:12px}
.top h1{font-size:18px;margin:0 18px 0 0;font-weight:600}.chip{border:1px solid #bbb;border-radius:3px;padding:4px 10px;font-size:12px;background:#fafafa}.chip b{color:#0078D4}
.card{position:absolute;background:#fff;border:1px solid #d6d6d6;border-radius:3px;padding:8px 12px}
.card h3{margin:0 0 4px;font-size:12px;color:#555;font-weight:600;display:flex;justify-content:space-between}.ico{color:#777;font-size:12px;letter-spacing:3px}
.kpi{font-size:26px;font-weight:600}.sub{font-size:11px;color:#666}.up{color:#107C10}.dn{color:#C50F1F}
.tip{position:absolute;background:#fff;border:1px solid #888;border-radius:4px;box-shadow:0 6px 18px rgba(0,0,0,.28);padding:10px 14px;font-size:12px;width:350px}
.tip h4{margin:0 0 6px;font-size:13px}.head{margin:5px 0;padding:5px 8px;border-left:4px solid #0078D4;background:#F3F9FD}.head.m{border-color:#8764B8;background:#F6F2FA}.head.p{border-color:#CA5010;background:#FDF4EF}
.head small{display:block;color:#666;font-size:10px;text-transform:uppercase;letter-spacing:.5px}
.foot{position:absolute;left:62px;right:0;bottom:0;height:24px;background:#fff8d6;border-top:1px solid #e3d48a;font-size:11px;padding:4px 18px;color:#665}
.bc{font-size:12px;color:#444}.bc b{color:#0078D4}.pick{display:flex;gap:8px;font-size:11px;margin:2px 0 6px}.pick span{border:1px solid #0078D4;color:#0078D4;border-radius:12px;padding:2px 10px}
table{border-collapse:collapse;font-size:11px;width:100%}th{background:#f3f2f1;text-align:right;padding:3px 6px}td{padding:3px 6px;text-align:right;border-bottom:1px solid #eee}td:first-child,th:first-child{text-align:left}
"""


def page(title, body, js, name):
    html = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style><script>{CHART}</script></head><body>{body}<script>{js}</script></body></html>"
    (OUT / name).write_text(html, encoding="utf-8")


NAV = "<div class='nav'><div class='on'>Executive</div><div>Chain</div><div>Zone / State</div><div>Brand</div><div>Nielsen</div><div>Chain share</div><div>Stores</div><div>Quality</div></div>"
SLICERS = lambda extra="": f"<div class='chip'>FY <b>FY27</b></div><div class='chip'>Month <b>Apr–Aug 26</b></div><div class='chip'>Chain <b>All MT</b></div><div class='chip'>Zone <b>All</b></div><div class='chip'>Category <b>All</b></div>{extra}"

# ---------------------------------------------------------------- page 1
decomp = "".join(f"<tr><td>{z}</td><td>{growth[z]:.1f}</td><td>{growth[z] / sum(growth.values()) * 100:.0f}%</td></tr>" for z in sorted(zones, key=lambda z: -growth[z]))
body1 = f"""{NAV}<div class='top'><h1>Executive Cockpit</h1>{SLICERS()}</div>
<div class='card' style='left:80px;top:66px;width:300px;height:92px'><h3>Offtake FY27 Apr–Aug (Rs Cr)<span class='ico'>···</span></h3><div class='kpi'>{mt_ty:,.2f}</div><div class='sub'>YoY <span class='up'>+{(tot_ty / tot_ly - 1) * 100:.1f}%</span> vs Apr–Aug FY26 (Rs {tot_ly:,.0f} Cr)</div></div>
<div class='card' style='left:392px;top:66px;width:300px;height:92px'><h3>Aug-26 (Rs Cr)<span class='ico'>···</span></h3><div class='kpi'>{mon[-1]:,.2f}</div><div class='sub'>MoM <span class='up'>+{mom[-1]:.1f}%</span> · YoY <span class='up'>+{yoy_m[-1]:.1f}%</span></div></div>
<div class='card' style='left:704px;top:66px;width:300px;height:92px'><h3>Nielsen Facewash share (IN URB MT)<span class='ico'>···</span></h3><div class='kpi'>{P['ms'][-1]:.1f}%</div><div class='sub'>YoY +2.6 pp · WD {P['wd'][-1]:.1f}%</div></div>
<div class='card' style='left:1016px;top:66px;width:300px;height:92px'><h3>Brand Counter (separate, Rs Cr)<span class='ico'>···</span></h3><div class='kpi'>7.28</div><div class='sub'>Aug-26 · not in the MT total</div></div>
<div class='card' style='left:80px;top:170px;width:700px;height:520px'><h3>NSV and YoY by zone: one chart, two insights<span class='ico'>⤒ ⤓ ⇊ ⤢</span></h3>
 <div class='bc'><b>All MT</b> ▸ Zone ▸ State ▸ City ▸ Store &nbsp; <span style='color:#888'>(Drill down: right-click a bar, or use the arrows)</span></div>
 <div class='pick'><span>Measure ▾ NSV Rs Cr</span><span>By ▾ Zone</span><span>Line: YoY %</span></div><div style='height:400px'><canvas id='c1'></canvas></div></div>
<div class='card' style='left:792px;top:170px;width:524px;height:250px'><h3>Monthly trend: NSV and MoM<span class='ico'>⤒ ⤓ ⇊</span></h3><div style='height:200px'><canvas id='c2'></canvas></div></div>
<div class='card' style='left:792px;top:432px;width:524px;height:258px'><h3>Why did YoY move? (decomposition: zone ▸ chain ▸ brand)<span class='ico'>+</span></h3>
 <table><tr><th>Zone</th><th>Growth Rs Cr</th><th>Share of growth</th></tr>{decomp}</table></div>
<div class='tip' style='left:300px;top:250px'><h4>West · Apr–Aug FY27</h4>
 <div class='head'><small>Sales</small>NSV Rs {ty[w]:,.2f} Cr · YoY <span class='up'>+{yoy[w]:.1f}%</span> · Aug MoM {(O['zone_monthly_fy27'][w][nm - 1] / O['zone_monthly_fy27'][w][nm - 2] - 1) * 100:+.1f}%</div>
 <div class='head m'><small>Mix</small>{ty[w] / tot_ty * 100:.1f}% of the MT total · carries {growth[w] / sum(growth.values()) * 100:.0f}% of the growth</div>
 <div class='head p'><small>Price and reach</small>ASP Rs {zi['asp']:.0f} per unit (index {zi['asp_index']}) · realisation {zi['realisation_pct']:.0f}% of MRP</div>
 <div style='margin-top:6px;color:#0078D4;font-size:11px'>Right-click ▸ Drill down to State · Drill through to Zone detail</div></div>
<div class='foot'>DESIGN PREVIEW drawn from the repo's real numbers (data.js offtake, Nielsen Aug-26, price/volume). Not a Power BI screenshot: the .pbix is built in Power BI Desktop with docs/POWERBI_DYNAMIC_DASHBOARD_BUILD.md.</div>"""
js1 = f"""Chart.defaults.animation=false;Chart.defaults.font.family='Segoe UI';
new Chart(document.getElementById('c1'),{{data:{{labels:{json.dumps(order)},datasets:[{{type:'bar',label:'NSV Rs Cr (Apr–Aug FY27)',data:{json.dumps([round(ty[z], 1) for z in order])},backgroundColor:{json.dumps(['#F2C811' if z == w else '#118DFF' for z in order])},yAxisID:'y'}},{{type:'line',label:'YoY %',data:{json.dumps([round(yoy[z], 1) for z in order])},borderColor:'#E66C37',backgroundColor:'#E66C37',yAxisID:'y1',tension:0,pointRadius:5}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},scales:{{y:{{title:{{display:true,text:'NSV Rs Cr'}}}},y1:{{position:'right',grid:{{drawOnChartArea:false}},title:{{display:true,text:'YoY %'}},ticks:{{callback:v=>v+'%'}}}}}}}}}});
new Chart(document.getElementById('c2'),{{data:{{labels:{json.dumps(months)},datasets:[{{type:'bar',label:'NSV Rs Cr',data:{json.dumps([round(v, 1) for v in mon])},backgroundColor:'#118DFF',yAxisID:'y'}},{{type:'line',label:'MoM %',data:{json.dumps([None if v is None else round(v, 1) for v in mom])},borderColor:'#E66C37',backgroundColor:'#E66C37',yAxisID:'y1'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},scales:{{y1:{{position:'right',grid:{{drawOnChartArea:false}},ticks:{{callback:v=>v+'%'}}}}}}}}}});"""
page("p1", body1, js1, "powerbi_preview_1_cockpit.html")

# ---------------------------------------------------------------- page 2 (drill-through: brand detail)
me = next(b for b in P["fw_all"] if b["n"] == "Mamaearth")
cat = P["fw_cat"]
idx = me["ppml"] / cat["ppml"] * 100
sah95 = me["sah"] * 0.95
rows = "".join(f"<tr><td>{r['n']}</td><td>{r['ms']:.1f}</td><td>{r['ppml']:.2f}</td><td>{r['ppml'] / cat['ppml'] * 100:.0f}</td><td>{r['wd']:.1f}</td><td>{r['nd']:.1f}</td></tr>" for r in sorted(P["fw_all"], key=lambda b: -b["ms"])[:6])
miss = [x for x in P["fw_pack_gap"]["rows"] if x["status"] == "Not present" and x["cat_share"] >= 1][:3]
body2 = f"""{NAV}<div class='top'><h1>Brand detail · Mamaearth Facewash</h1><div class='chip'>Drill-through from <b>Brand</b> ▸ right-click ▸ Drill through</div><div class='chip'>Month <b>Aug 26</b></div><div class='chip'>Market <b>IN URB MT</b></div><div class='chip'>← Back</div></div>
<div class='card' style='left:80px;top:66px;width:470px;height:380px'><h3>SHARE: value share trend (36 months)<span class='ico'>⤒ ⤓</span></h3><div class='kpi'>{me['ms']:.1f}% <span class='sub'>YoY +{me['pp']:.1f} pp</span></div><div style='height:270px'><canvas id='c3'></canvas></div></div>
<div class='card' style='left:562px;top:66px;width:470px;height:380px'><h3>PRICE: price per ml against the category<span class='ico'>⤒ ⤓</span></h3><div class='kpi'>Index {idx:.0f} <span class='sub'>Rs {me['ppml']:.2f} / ml vs category Rs {cat['ppml']:.2f}</span></div>
 <table><tr><th>Brand</th><th>Share %</th><th>Rs / ml</th><th>Index</th><th>WD %</th><th>ND %</th></tr>{rows}</table>
 <div class='sub' style='margin-top:8px'>Value share {me['ms']:.1f}% above volume share {me['ms_vol']:.1f}%: we sell above the category price.</div></div>
<div class='card' style='left:1044px;top:66px;width:300px;height:380px'><h3>REACH: distribution and headroom<span class='ico'>⤒ ⤓</span></h3>
 <div class='kpi'>WD {me['wd']:.1f}%</div><div class='sub'>ND {me['nd']:.1f}% · {me['stores']:,.0f} stores · Rs {me['pdo']:,.0f} per store</div>
 <div class='head' style='margin-top:12px'><small>Where listed we hold (SAH)</small>{me['sah']:.1f}%</div>
 <div class='head m'><small>Share at 95% WD</small>{sah95:.1f}% ({sah95 - me['ms']:+.1f} pp)</div>
 <div class='head p'><small>Packs not sold (≥1% of value)</small>{', '.join(f"{x['size']} ml" for x in miss)}</div></div>
<div class='card' style='left:80px;top:458px;width:1264px;height:130px'><h3>Same brand, other heads: sales inside our MT chains (internal offtake) and account share<span class='ico'>⤒ ⤓</span></h3>
 <div style='display:flex;gap:30px;font-size:12px'><div><b>SALES</b><br>Mamaearth NSV Apr–Aug: Rs {next(b for b in PV['internal']['brands'] if b['name']=='Mamaearth')['nsv_cr']:,.1f} Cr · ASP Rs {next(b for b in PV['internal']['brands'] if b['name']=='Mamaearth')['asp']:.0f}</div>
 <div><b>MIX</b><br>Dmart Rs {PV['internal']['chains'][0]['nsv_cr']:,.1f} Cr is the biggest chain; ASP index {PV['internal']['chains'][0]['asp_index']}</div>
 <div><b>ACCOUNT SHARE</b><br>Lulu 26.0% · Reliance 27.2% · Wellness 17.0% · More 11.2% (face wash, Aug 26)</div></div>
 <div class='sub' style='margin-top:10px'>Each block carries a different head; the drill-through keeps the brand filter and the month.</div></div>
<div class='foot'>DESIGN PREVIEW drawn from the repo's real numbers (Nielsen Aug-26 payload, price/volume, account share). Not a Power BI screenshot.</div>"""
js2 = f"""Chart.defaults.animation=false;Chart.defaults.font.family='Segoe UI';
new Chart(document.getElementById('c3'),{{type:'line',data:{{labels:{json.dumps(P['months'])},datasets:[{{label:'Mamaearth value share %',data:{json.dumps(P['ms'])},borderColor:'#118DFF',backgroundColor:'rgba(17,141,255,.15)',fill:true,pointRadius:1}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{maxTicksLimit:8}}}},y:{{ticks:{{callback:v=>v+'%'}}}}}}}}}});"""
page("p2", body2, js2, "powerbi_preview_2_brand_drillthrough.html")


# ================================================================ more pages
import csv
CC = list(csv.DictReader((ROOT / "data" / "nielsen" / "Chain_Contribution_Aug26.csv").open(encoding="utf-8")))[:8]
VC = json.loads((ROOT / "data" / "nielsen" / "Visit_Cities_Aug26.json").read_text(encoding="utf-8"))
AV = json.loads((ROOT / "data" / "account_share" / "Account_View.json").read_text(encoding="utf-8"))
asp = {c["name"].upper(): c for c in PV["internal"]["chains"]}
FOOT = "<div class='foot'>DESIGN PREVIEW drawn from the repo's real numbers. Not a Power BI screenshot.</div>"
pretty = lambda n: {"DMART": "D-Mart", "RELIANCE": "Reliance Retail"}.get(n, n.title())


def top(title, extra=""):
    return f"{NAV}<div class='top'><h1>{title}</h1>{extra}</div>"


# ---- page 3: Chain performance
rows = "".join(f"<tr><td>{pretty(c['Chain'])}</td><td>{float(c['ty']) / 100:,.1f}</td><td>{float(c['growth_pct']):+.0f}%</td><td>{float(c['share_ty_pct']):.1f}%</td><td>{float(c['share_of_growth_pct']):.0f}%</td><td>{float(c['mamaearth_pct_of_chain']):.0f}%</td><td>{asp.get(c['Chain'], {}).get('asp_index', '–')}</td><td>{asp.get(c['Chain'], {}).get('realisation_pct', '–')}</td></tr>" for c in CC)
d = CC[0]
body3 = top("Chain Performance", SLICERS()) + f"""
<div class='card' style='left:80px;top:66px;width:700px;height:420px'><h3>NSV, growth and share of growth by chain: one chart, three insights<span class='ico'>⤒ ⤓ ⇊ ⤢</span></h3>
 <div class='bc'><b>All chains</b> ▸ Chain ▸ Store &nbsp;<span style='color:#888'>(drill down to the stores of one chain)</span></div><div class='pick'><span>Measure ▾ NSV Rs Cr</span><span>By ▾ Chain</span><span>Line: YoY %</span><span>Bubble: share of growth</span></div>
 <div style='height:310px'><canvas id='c4'></canvas></div></div>
<div class='card' style='left:792px;top:66px;width:524px;height:420px'><h3>Chain table (matrix): sales, mix, price<span class='ico'>⤒ ⤓ ⇊</span></h3>
 <table><tr><th>Chain</th><th>NSV Cr</th><th>YoY</th><th>Share</th><th>Of growth</th><th>Our % of chain</th><th>ASP idx</th><th>Real. %</th></tr>{rows}</table>
 <div class='sub' style='margin-top:8px'>Click a row to cross-filter the chart; right-click ▸ Drill through ▸ Chain detail.</div></div>
<div class='card' style='left:80px;top:498px;width:1236px;height:150px'><h3>Insights for the selected chain (D-Mart)<span class='ico'>···</span></h3>
 <div style='display:flex;gap:26px;font-size:12px'><div><b>SALES</b><br>Rs {float(d['ty']) / 100:,.1f} Cr · {float(d['growth_pct']):+.0f}% YoY</div><div><b>MIX</b><br>{float(d['share_ty_pct']):.0f}% of MT NSV · carries {float(d['share_of_growth_pct']):.0f}% of the growth</div><div><b>PRICE</b><br>ASP index {asp['DMART']['asp_index']} · realisation {asp['DMART']['realisation_pct']}% of MRP</div><div><b>OUR SHARE</b><br>Mamaearth is {float(d['mamaearth_pct_of_chain']):.0f}% of the chain's NSV</div></div></div>""" + FOOT
js3 = f"""Chart.defaults.animation=false;new Chart(document.getElementById('c4'),{{data:{{labels:{json.dumps([pretty(c['Chain']) for c in CC])},datasets:[{{type:'bar',label:'NSV Rs Cr',data:{json.dumps([round(float(c['ty']) / 100, 1) for c in CC])},backgroundColor:'#118DFF',yAxisID:'y'}},{{type:'line',label:'YoY %',data:{json.dumps([round(float(c['growth_pct']), 0) for c in CC])},borderColor:'#E66C37',backgroundColor:'#E66C37',yAxisID:'y1',pointRadius:5}},{{type:'line',label:'Share of growth %',data:{json.dumps([round(float(c['share_of_growth_pct']), 0) for c in CC])},borderColor:'#8764B8',backgroundColor:'#8764B8',yAxisID:'y1',borderDash:[5,4],pointRadius:4}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},scales:{{y1:{{position:'right',grid:{{drawOnChartArea:false}},ticks:{{callback:v=>v+'%'}}}}}}}}}});"""
page("p3", body3, js3, "powerbi_preview_3_chain.html")

# ---- page 4: zone and state, drilled into West
wcities = sorted([c for c in VC["cities"] if c["Region"] == "West"], key=lambda c: -c["NSV_total_exBC"])
tw = ty[w]
sr = "".join(f"<tr><td>{c['City']}</td><td>{c['NSV_total_exBC'] / 100:.1f}</td><td>{c['Stores']}</td><td>{(c['NSV_Aug'] / c['NSV_Jul'] - 1) * 100:+.0f}%</td><td>{c['Beats']}</td></tr>" for c in wcities)
body4 = top("Zone and State · drilled into West", SLICERS("").replace("Zone <b>All</b>","Zone <b>West</b>")) + f"""
<div class='card' style='left:80px;top:66px;width:640px;height:440px'><h3>West by state: NSV (Apr–Aug FY27) and share of the zone<span class='ico'>⤒ ⤓ ⇊ ⤢</span></h3>
 <div class='bc'>All MT ▸ <b>West</b> ▸ State ▸ City ▸ Store &nbsp;<span style='color:#888'>(you are one level down; ⤒ goes back up)</span></div><div class='pick'><span>Measure ▾ NSV Rs Cr</span><span>By ▾ State</span><span>Line: share of zone %</span></div><div style='height:330px'><canvas id='c5'></canvas></div><div class='sub'>"Mumbai" is a state label used in the offtake file for some chains; the real state list is cleaned in the Power BI model.</div></div>
<div class='card' style='left:732px;top:66px;width:584px;height:440px'><h3>West cities (visit-city list): NSV, stores, MoM, beats<span class='ico'>⤒ ⤓ ⇊</span></h3>
 <table><tr><th>City</th><th>NSV Apr–Aug Rs L</th><th>Stores</th><th>MoM Aug</th><th>Beats</th></tr>{sr}</table>
 <div class='sub' style='margin-top:8px'>Mumbai includes Thane and Navi Mumbai; Pune is West. Right-click a city ▸ Drill through ▸ Store list with last-year NSV and YoY.</div></div>
<div class='tip' style='left:300px;top:150px'><h4>Maharashtra · Apr–Aug FY27</h4>
 <div class='head'><small>Sales</small>NSV Rs {states_w[0][1]:,.1f} Cr · FY26 full year Rs {next(x for x in O['by_state'] if x['state'] == 'Maharashtra')['fy26'] / 100:,.1f} Cr</div>
 <div class='head m'><small>Mix</small>{states_w[0][1] / tw * 100:.0f}% of the West zone · {states_w[0][1] / mt_ty * 100:.0f}% of the MT total</div>
 <div class='head p'><small>Reach</small>{sum(c['Stores'] for c in wcities if c['City'] in ('Mumbai', 'Pune', 'Nashik')):,} stores in Mumbai, Pune and Nashik</div></div>""" + FOOT
js4 = f"""Chart.defaults.animation=false;new Chart(document.getElementById('c5'),{{data:{{labels:{json.dumps([x[0] for x in states_w])},datasets:[{{type:'bar',label:'NSV Rs Cr',data:{json.dumps([round(x[1], 1) for x in states_w])},backgroundColor:'#118DFF',yAxisID:'y'}},{{type:'line',label:'Share of West %',data:{json.dumps([round(x[1] / tw * 100, 1) for x in states_w])},borderColor:'#E66C37',backgroundColor:'#E66C37',yAxisID:'y1',pointRadius:5}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},scales:{{y1:{{position:'right',grid:{{drawOnChartArea:false}},ticks:{{callback:v=>v+'%'}}}}}}}}}});"""
page("p4", body4, js4, "powerbi_preview_4_zone_state.html")

# ---- page 5: Nielsen cuts
fw = sorted(P["fw_all"], key=lambda b: -b["ms"])[:7]
nr = "".join(f"<tr><td>{b['n']}</td><td>{b['ms']:.1f}</td><td>{b['pp']:+.1f}</td><td>{b['ppml']:.2f}</td><td>{b['ppml'] / cat['ppml'] * 100:.0f}</td><td>{b['wd']:.1f}</td><td>{b['nd']:.1f}</td><td>{b['sah']:.1f}</td></tr>" for b in fw)
packs = [x for x in P["fw_pack_gap"]["rows"] if x["cat_share"] >= 1][:7]
body5 = top("Nielsen Cuts · Facewash", "<div class='chip'>Category <b>Facewash</b></div><div class='chip'>Market <b>IN URB MT</b></div><div class='chip'>Month <b>Aug 26</b></div><div class='chip'>View <b>Both ▾</b></div>") + f"""
<div class='card' style='left:80px;top:66px;width:520px;height:330px'><h3>Mamaearth share trend (face wash, urban MT)<span class='ico'>⤒ ⤓</span></h3><div style='height:270px'><canvas id='c6'></canvas></div></div>
<div class='card' style='left:612px;top:66px;width:704px;height:330px'><h3>Brand cut: share, price, distribution, productivity<span class='ico'>⤒ ⤓ ⇊</span></h3>
 <table><tr><th>Brand</th><th>Share %</th><th>Δ pp YoY</th><th>Rs / ml</th><th>Price idx</th><th>WD %</th><th>ND %</th><th>SAH %</th></tr>{nr}</table>
 <div class='sub' style='margin-top:8px'>WD above ND = in the larger stores first. SAH = share where the brand is listed.</div></div>
<div class='card' style='left:80px;top:408px;width:760px;height:260px'><h3>Pack presence: category value by pack and Mamaearth's own mix<span class='ico'>⤒ ⤓</span></h3><div style='height:200px'><canvas id='c7'></canvas></div></div>
<div class='card' style='left:852px;top:408px;width:464px;height:260px'><h3>Insights<span class='ico'>···</span></h3>
 <div class='head'><small>Price</small>Index {idx:.0f}: we sell above the category price</div><div class='head m'><small>Reach</small>WD {me['wd']:.1f}% but ND {me['nd']:.1f}%: smaller stores still open</div><div class='head p'><small>Headroom</small>Share at 95% WD {sah95:.1f}% ({sah95 - me['ms']:+.1f} pp); 125 and 240 ml not sold</div></div>""" + FOOT
colors = ["#118DFF", "#12239E", "#E66C37", "#6B007B", "#E044A7", "#744EC2"]
tops = [next(b for b in P["brands"] if b["n"] == n) for n in ("Mamaearth",)]
js5 = f"""Chart.defaults.animation=false;
new Chart(document.getElementById('c6'),{{type:'line',data:{{labels:{json.dumps(P['months'])},datasets:[{{label:'Mamaearth',data:{json.dumps(P['ms'])},borderColor:'#118DFF',pointRadius:0,borderWidth:3}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},scales:{{x:{{ticks:{{maxTicksLimit:7}}}},y:{{ticks:{{callback:v=>v+'%'}}}}}}}}}});
new Chart(document.getElementById('c7'),{{type:'bar',data:{{labels:{json.dumps([x['size'] + ' ml' for x in packs])},datasets:[{{label:'Category value share %',data:{json.dumps([x['cat_share'] for x in packs])},backgroundColor:'#C8C6C4'}},{{label:'Mamaearth own mix %',data:{json.dumps([x['me_mix'] for x in packs])},backgroundColor:'#118DFF'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}}}}}});"""
page("p5", body5, js5, "powerbi_preview_5_nielsen.html")

# ---- page 6: chain share and plan
cols6 = {"Lulu": "#118DFF", "More Retail": "#E66C37", "Wellness Forever": "#107C10", "Reliance Retail": "#8764B8", "Reliance Brand Counter": "#E044A7"}
allm = sorted({x["month"] for c in AV["chains"].values() for x in c["series"]}, key=lambda m: (int(m.split()[1]), ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(m.split()[0])))
ds = []
for n, c in AV["chains"].items():
    by = {x["month"]: x for x in c["series"]}
    ds.append({"label": n, "data": [by[m]["fw_share"] if m in by else None for m in allm], "borderColor": cols6.get(n), "backgroundColor": cols6.get(n), "tension": .25, "spanGaps": True, "pointRadius": 2})
t6 = "".join(f"<tr><td>{n}</td><td>{c['share_latest']:.1f}</td><td>{c['fw_share_latest']:.1f}</td><td>{c['account_mom_pct']:+.0f}%</td><td>{c['honasa_mom_pct']:+.0f}%</td></tr>" for n, c in AV["chains"].items())
fl = [f for f in AV["flags"] if f["flag"] in ("White space", "Low assortment")][:5]
lv = AV["facewash_plan"]["levers"][:4]
body6 = top("Chain Share and Plan", "<div class='chip'>Chain <b>All 4 ▾</b></div><div class='chip'>Month <b>Aug 26</b></div><div class='chip'>Level <b>Chain ▾</b></div>") + f"""
<div class='card' style='left:80px;top:66px;width:640px;height:330px'><h3>Face wash share inside each chain's own category (%)<span class='ico'>⤒ ⤓ ⇊</span></h3><div class='pick'><span>Chain ▾ Lulu · More · Wellness · Reliance · Brand Counter</span></div><div style='height:250px'><canvas id='c8'></canvas></div><div class='sub'>Dashed in the report: More Retail months on the smaller scope.</div></div>
<div class='card' style='left:732px;top:66px;width:584px;height:330px'><h3>Account sales vs ours, MoM<span class='ico'>⤒ ⤓</span></h3><table><tr><th>Chain</th><th>Our share %</th><th>Face wash %</th><th>Account MoM</th><th>Our MoM</th></tr>{t6}</table><div class='sub' style='margin-top:6px'>Reliance values are gross sales as supplied: compare shares, not rupees.</div></div>
<div class='card' style='left:80px;top:408px;width:640px;height:260px'><h3>White space and low assortment (only categories that matter to us)<span class='ico'>⤒ ⤓</span></h3><table><tr><th>Chain</th><th>Category</th><th>Flag</th><th>% of chain</th><th>Our share %</th><th>Articles</th></tr>{''.join(f"<tr><td>{f['chain']}</td><td>{f['category']}</td><td>{f['flag']}</td><td>{f['pct_of_chain']:.1f}</td><td>{f['share']:.2f}</td><td>{f['articles'] if f['articles'] is not None else '–'}</td></tr>" for f in fl)}</table></div>
<div class='card' style='left:732px;top:408px;width:584px;height:260px'><h3>Plan to lift Facewash share (Rs Cr / month, upper bound)<span class='ico'>⤒ ⤓</span></h3><table><tr><th>Lever</th><th>Rs Cr / month</th><th>Owner</th><th>Timeline</th></tr>{''.join(f"<tr><td>{l['lever']}</td><td>{l['size_cr_month']:.2f}</td><td>{l['owner']}</td><td>{l['timeline']}</td></tr>" for l in lv)}</table><div class='sub' style='margin-top:6px'>Total {AV['facewash_plan']['total_cr_month']:.2f} Cr a month: levers overlap, so it is not a forecast.</div></div>""" + FOOT
js6 = f"""Chart.defaults.animation=false;new Chart(document.getElementById('c8'),{{type:'line',data:{{labels:{json.dumps(allm)},datasets:{json.dumps(ds)}}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10}}}}}},scales:{{y:{{ticks:{{callback:v=>v+'%'}}}}}}}}}});"""
page("p6", body6, js6, "powerbi_preview_6_chain_share.html")
# ---- page 7: state, pack size, LFL / NFL stores
SC = json.load((ROOT / "data" / "store_cuts_aug26.json").open())
sst = [r for r in SC["by_state"] if r["State"]][:8]
lfl_t = sum(r["lfl_ty"] for r in SC["by_chain"]); lfl_l = sum(r["lfl_ly"] for r in SC["by_chain"])
nfl_t = sum(r["nfl_ty"] for r in SC["by_chain"]); noly_t = sum(r["noly_ty"] for r in SC["by_chain"])
ch7 = [r for r in SC["by_chain"] if r["lfl_stores"] + r["nfl_stores"] > 0][:8]
t7 = "".join(f"<tr><td>{r['Chain']}</td><td>{r['lfl_stores']:,}</td><td>{r['nfl_stores']:,}</td><td>{r['lfl_ty'] / 100:.1f}</td><td>{r['nfl_ty'] / 100:.1f}</td><td>{'–' if r['lfl_growth_pct'] is None else format(r['lfl_growth_pct'], '+.0f') + '%'}</td><td>{r['lost_stores']}</td></tr>" for r in ch7)
pk7 = SC["by_pack"][:8]
zr = "".join(f"<tr><td>{r['zone']}</td><td>{r['ty'] / 100:,.1f}</td><td>{r['share_pct']:.0f}%</td><td>{r['lfl_ty'] / 100:,.1f}</td><td>{'–' if r['yoy_pct'] is None else format(r['yoy_pct'], '+.0f') + '%'}</td><td>{'–' if r['mom_pct'] is None else format(r['mom_pct'], '+.0f') + '%'}</td></tr>" for r in SC["zone_sales"])
br = "".join(f"<tr><td>{r['brand']}</td><td>{r['ty'] / 100:,.1f}</td><td>{r['share_pct']:.0f}%</td><td>{'–' if r['mom_pct'] is None else format(r['mom_pct'], '+.0f') + '%'}</td></tr>" for r in SC["brand_sales"][:5])
sr = "".join(f"<tr><td>{r['subcategory']}</td><td>{r['ty'] / 100:,.1f}</td><td>{r['share_pct']:.0f}%</td><td>{'–' if r['mom_pct'] is None else format(r['mom_pct'], '+.0f') + '%'}</td></tr>" for r in SC["subcat_sales"][:6])
extra7 = f"""
<div class='card' style='left:80px;top:680px;width:560px;height:260px'><h3>Zone sales: NSV Cr, share, LFL, YoY, MoM<span class='ico'>⤒ ⤓ ⇊</span></h3><table><tr><th>Zone</th><th>NSV Cr</th><th>Share</th><th>LFL Cr</th><th>YoY</th><th>MoM</th></tr>{zr}</table></div>
<div class='card' style='left:652px;top:680px;width:320px;height:260px'><h3>Brand sales<span class='ico'>⤒ ⤓</span></h3><table><tr><th>Brand</th><th>NSV Cr</th><th>Share</th><th>MoM</th></tr>{br}</table></div>
<div class='card' style='left:984px;top:680px;width:332px;height:260px'><h3>Sub-category sales<span class='ico'>⤒ ⤓</span></h3><table><tr><th>Sub-category</th><th>NSV Cr</th><th>Share</th><th>MoM</th></tr>{sr}</table></div>"""
body7 = top("State, Pack Size and Store Type", "<div class='chip'>FY <b>FY27</b></div><div class='chip'>Month <b>Apr–Aug 26</b></div><div class='chip'>Store type <b>All ▾</b></div><div class='chip'>Pack <b>All ▾</b></div>") + f"""
<div class='card' style='left:80px;top:66px;width:640px;height:330px'><h3>State cut: NSV split by LFL and NFL stores (Rs Cr)<span class='ico'>⤒ ⤓ ⇊ ⤢</span></h3>
 <div class='bc'>All MT ▸ <b>State</b> ▸ City ▸ Store</div><div class='pick'><span>Measure ▾ NSV Rs Cr</span><span>Split ▾ Store type</span><span>Line: LFL growth %</span></div><div style='height:240px'><canvas id='c9'></canvas></div></div>
<div class='card' style='left:732px;top:66px;width:584px;height:330px'><h3>LFL vs NFL by chain<span class='ico'>⤒ ⤓ ⇊</span></h3>
 <table><tr><th>Chain</th><th>LFL stores</th><th>NFL stores</th><th>LFL NSV Cr</th><th>NFL NSV Cr</th><th>LFL growth</th><th>Lost</th></tr>{t7}</table>
 <div class='sub' style='margin-top:8px'>LFL = sold this year and in the same months last year. NFL = no sales last year. Lost = sold last year, nothing this year. Reliance Retail has no store-level last year, so it is kept out of LFL.</div></div>
<div class='card' style='left:80px;top:408px;width:760px;height:260px'><h3>Pack size cut: NSV share and MoM (g / ml)<span class='ico'>⤒ ⤓</span></h3><div style='height:200px'><canvas id='c10'></canvas></div></div>
<div class='card' style='left:852px;top:408px;width:464px;height:260px'><h3>Insights<span class='ico'>···</span></h3>
 <div class='head'><small>Sales</small>LFL stores Rs {lfl_t / 100:,.1f} Cr vs Rs {lfl_l / 100:,.1f} Cr last year: {(lfl_t / lfl_l - 1) * 100:+.0f}%</div>
 <div class='head m'><small>Mix</small>NFL adds Rs {nfl_t / 100:,.1f} Cr: only {SC['stores']['New']:,} are truly new (Rs {sum(r['new_ty'] for r in SC['by_chain']) / 100:,.1f} Cr); {SC['stores']['Restarted']:,} restarted (Rs {sum(r['restart_ty'] for r in SC['by_chain']) / 100:,.1f} Cr)</div>
 <div class='head p'><small>Reach</small>{SC['lost']['stores']:,} stores sold last year, nothing this year (Rs {SC['lost']['ly_nsv'] / 100:,.1f} Cr last year)</div></div>""" + extra7 + FOOT.replace("class='foot'", "class='foot' style='position:absolute;top:950px;bottom:auto;left:62px;right:0'")
js7 = f"""Chart.defaults.animation=false;
new Chart(document.getElementById('c9'),{{data:{{labels:{json.dumps([r['State'] for r in sst])},datasets:[{{type:'bar',label:'LFL stores',data:{json.dumps([round(r['lfl_ty'] / 100, 1) for r in sst])},backgroundColor:'#118DFF',stack:'a'}},{{type:'bar',label:'NFL stores',data:{json.dumps([round(r['nfl_ty'] / 100, 1) for r in sst])},backgroundColor:'#E66C37',stack:'a'}},{{type:'bar',label:'No LY store data',data:{json.dumps([round(r['noly_ty'] / 100, 1) for r in sst])},backgroundColor:'#C8C6C4',stack:'a'}},{{type:'line',label:'LFL growth %',data:{json.dumps([r['lfl_growth_pct'] for r in sst])},borderColor:'#6B007B',backgroundColor:'#6B007B',yAxisID:'y1'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10}}}}}},scales:{{x:{{stacked:true}},y:{{stacked:true}},y1:{{position:'right',grid:{{drawOnChartArea:false}},ticks:{{callback:v=>v+'%'}}}}}}}}}});
new Chart(document.getElementById('c10'),{{data:{{labels:{json.dumps([x['pack'] for x in pk7])},datasets:[{{type:'bar',label:'Share of NSV %',data:{json.dumps([x['share_pct'] for x in pk7])},backgroundColor:'#118DFF'}},{{type:'line',label:'MoM Aug vs Jul %',data:{json.dumps([x['mom_pct'] for x in pk7])},borderColor:'#E66C37',backgroundColor:'#E66C37',yAxisID:'y1'}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:10}}}}}},scales:{{y:{{beginAtZero:true,max:30,ticks:{{callback:v=>v+'%'}}}},y1:{{position:'right',grid:{{drawOnChartArea:false}},ticks:{{callback:v=>v+'%'}}}}}}}}}});"""
page("p7", body7, js7, "powerbi_preview_7_state_pack_lfl.html")
print("wrote", OUT)
