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
print("wrote", OUT)
