#!/usr/bin/env python3
"""Account (retailer) category share: the chain's own category sales against Honasa sales, by month, zone and state.

Reads the retailer-side files the account teams supply (they stay outside Git):
  --lulu      Compiled_Monthly_Files_*.xlsx   sheets Compiled_Brand_Share (store x category x brand) and Compiled_SKU (store x article)
  --more      More_MS_Till_Aug26_Updated.xlsx sheets Performance Categorywise / Performance Sub-Categories / Data Sheet (DC city x item)
  --wellness  Wellness_MS_*.xlsb              Sheet1 (category x month: Honasa row, OVERALL row)
  --reliance  RIL_BA_Store_MS_*.xlsb          'Article MS Source' (Reliance stores outside the brand counters, Nov 25 on: RRL = Reliance category
                                              sales, HCL = Honasa) and 'BA Store' (the staffed brand-counter stores, Jan 26 on). RRL Others (categories
                                              outside the file's own pivot scope) is left out, as the file's pivots do. Gross sales Rs lakh as supplied.
                                              The two are kept as two lines (Reliance Retail, Reliance Brand Counter) and never added together.
and writes small aggregate CSVs to data/account_share/ (no store names, no employee data):

  Account_Category_Monthly.csv   Chain, Month, Category (as in the source), Common Category, Account Sales Rs L, Honasa Sales Rs L, Share %
  Account_Category_Geo.csv       the same by Zone / State / City (Lulu: store state; More: DC city) where the file has it
  Account_Assortment.csv         Honasa articles (distinct) per category and month where the file has item level data
  Account_Store_Map.csv          Lulu store code -> city, state, zone, format (city read from the store name) for store-city checks
  Account_Category_Map.csv       every source category and the common category it rolls up to (check this before reading a total)

Basis. Value in Rs lakh without GST as supplied. Lulu and More category sales cover the categories and stores where Honasa sells
(the files carry no category sales for stores or categories without a Honasa sale), so a category where Honasa is absent is NOT in
Lulu's file: white space there needs the account's full category report. Wellness lists every category, including those with no
Honasa sale. Share = Honasa sales / account category sales.

    python scripts/build_account_share.py --lulu <xlsx> --more <xlsx> --wellness <xlsb>
"""
import argparse
import datetime
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "account_share"
MON = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
LAKH = 1e5
RELEVANT_MIN_PCT = 0.5     # a common category is "relevant for us" when it is at least this % of our own sales across the chains (Jun-Aug 26); "Other" never is


def month_label(x):
    """"Aug'26" / datetime / Excel serial -> "Aug 26"."""
    if isinstance(x, (int, float)) and not isinstance(x, bool) and x > 30000:
        x = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=float(x))
    if isinstance(x, (datetime.datetime, pd.Timestamp)):
        return f"{MON[x.month - 1]} {x.year % 100:02d}"
    m = re.match(r"^([A-Za-z]{3})[' -]*(\d{2})$", str(x).strip())
    return f"{m.group(1).title()} {m.group(2)}" if m else str(x)


def month_key(label):
    mon, yy = label.split()
    return (int(yy), MON.index(mon))


# ------------------------------------------------------------------ common categories
RULES = [   # first match wins; lower-case keyword -> common category
    (("hair serum",), "Hair Treatment & Styling"),
    (("soaps beauty", "beauty soap"), "Beauty Soap"),
    (("moisturizing lotion", "moisturising lotion", "body lotion", "body care", "body moist", "cream & lotion body"), "Body Lotion & Care"),
    (("perfume", "fragrance", "eau de"), "Fragrance"),
    (("toner", "astringent"), "Toner"),
    (("aloe",), "Face Moisturiser & Cream"),
    (("facial kit",), "Face Mask & Scrub"),
    (("face wash", "facewash", "facial cleanser", "face cleanser", "cleanser"), "Face Wash & Cleanser"),
    (("sun", "spf"), "Sun Care"),
    (("serum", "essence", "niacinamide", "vitamin c", "peeling", "brightening", "anti ageing", "anti acne", "acne", "depigment"), "Face Serum & Treatment"),
    (("face mask", "face pack", "clay mask", "sheet mask", "scrub", "mask/ pack"), "Face Mask & Scrub"),
    (("moistur", "face cream", "night cream", "fairness", "whtng", "other facial", "face care", "cream & gel", "eye care", "other skin"), "Face Moisturiser & Cream"),
    (("conditioner",), "Conditioner"),
    (("hair oil",), "Hair Oil"),
    (("shampoo",), "Shampoo"),
    (("hair", "treatment & styling", "henna", "colour", "color", "spray", "mousse"), "Hair Treatment & Styling"),
    (("baby", "other baby"), "Baby Care"),
    (("body wash", "shower", "soap", "personal wash"), "Body Wash & Soap"),
    (("lip",), "Lip Care"),
    (("deo",), "Deodorant"),
    (("tooth", "oral"), "Oral Care"),
]


def common_category(name):
    n = str(name).lower().replace("\xa0", " ")
    if "baby" in n:
        return "Baby Care"
    if "shower" in n or "body wash" in n:
        return "Body Wash & Soap"
    for keys, common in RULES:
        if any(k in n for k in keys):
            return common
    return "Other"


# ------------------------------------------------------------------ Lulu
def lulu_city(store_name):
    """City from a store name such as 'Lulu Hypermarket, Kochi' or 'Lulu Daily, Maradu, Kochi' (last comma part)."""
    s = re.sub(r"\s+", " ", str(store_name)).strip()
    if "," in s:
        c = s.split(",")[-1].strip()
        return None if re.search(r"lulu|connect|reo|falcon|mall", c, re.I) and "kochi" not in c.lower() else c.title()
    return None


def load_lulu(path):
    bs = pd.read_excel(path, sheet_name="Compiled_Brand_Share")
    sku = pd.read_excel(path, sheet_name="Compiled_SKU")
    bs["Month"] = bs["Month"].map(month_label)
    sku["Month"] = sku["Month"].map(month_label)
    bs["Plant Code"] = bs["Plant Code"].astype(str).str.strip()
    sku["Plant Code"] = sku["Plant Code"].astype(str).str.strip()
    bs = bs[bs["Share %"].gt(0) & bs["Honasa Sales"].notna()].copy()
    bs["cat_row"] = bs["Honasa Sales"] / bs["Share %"]
    # store attributes: one value per store code (most frequent non-blank)
    mode = lambda s: s.dropna().mode().iloc[0] if s.notna().any() else None   # noqa: E731
    stores = bs.groupby("Plant Code").agg(Store=("Plant/Store Name", mode), Zone=("Zone", mode), State=("State", mode), Format=("Format", mode)).reset_index()
    stores["Zone"] = stores["Zone"].map(lambda z: z.title().replace("South-", "South-") if isinstance(z, str) else z)
    stores["State"] = stores["State"].map(lambda s: s.title() if isinstance(s, str) else s)
    stores["City"] = stores["Store"].map(lulu_city)
    bs = bs.merge(stores[["Plant Code", "Zone", "State", "City"]].rename(columns={"Zone": "Z", "State": "S", "City": "C"}), on="Plant Code", how="left")
    # Honasa = sum of brand rows; category sales is the same on every brand row of a store-category-month: take it once
    cell = bs.groupby(["Month", "Plant Code", "MC Description"]).agg(h=("Honasa Sales", "sum"), c=("cat_row", "max"), Zone=("Z", "first"), State=("S", "first"), City=("C", "first")).reset_index()
    cell["h"] /= LAKH
    cell["c"] /= LAKH
    return cell, sku, stores


def lulu_tables(cell, sku):
    cell = cell.rename(columns={"MC Description": "Category"})
    monthly = cell.groupby(["Month", "Category"]).agg(Account=("c", "sum"), Honasa=("h", "sum")).reset_index()
    geo = cell.groupby(["Month", "Zone", "State", "City", "Category"], dropna=False).agg(Account=("c", "sum"), Honasa=("h", "sum"), Stores=("Plant Code", "nunique")).reset_index()
    art = sku.groupby(["Month", "MC Description"]).agg(Articles=("Article Code", "nunique"), Stores=("Plant Code", "nunique")).reset_index().rename(columns={"MC Description": "Category"})
    return monthly, geo, art


# ------------------------------------------------------------------ More
def load_more(path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)

    def sheet(name, ncols_key):
        rows = [list(r) for r in wb[name].iter_rows(values_only=True)]
        h = next(i for i, r in enumerate(rows) if r and r[0] == "Group")
        hdr = rows[h]
        body = [r for r in rows[h + 1:] if r and r[0] and r[0] != "Grand Total"]
        return hdr, body
    out = []
    for name, keycols in (("Performance Categorywise", 2), ("Performance Sub-Categories", 3)):
        hdr, body = sheet(name, keycols)
        pairs = {}
        for i, hname in enumerate(hdr):
            m = re.match(r"^([A-Za-z]{3}'\d{2}) (MRL|HCL)$", str(hname))
            if m:
                pairs.setdefault(m.group(1), {})[m.group(2)] = i
        for r in body:
            cat = r[1] if keycols == 2 else r[2]
            group = r[0]
            for mlabel, ix in pairs.items():
                if "MRL" in ix and "HCL" in ix:
                    out.append({"Level": "Class" if keycols == 2 else "Sub-Class", "Group": group, "Class": r[1], "Category": cat,
                                "Month": month_label(mlabel), "Account": float(r[ix["MRL"]] or 0), "Honasa": float(r[ix["HCL"]] or 0)})
    raw = pd.read_excel(path, sheet_name="Data Sheet", header=None)
    h = raw.index[raw[0] == "Month"][0]
    cols = raw.iloc[h].tolist()
    end = cols.index("Subcategory Summary Scope")
    data = raw.iloc[h + 1:, :end + 1].copy()
    data.columns = cols[:end + 1]
    data = data.dropna(subset=["Month"])
    data["Month"] = data["Month"].map(month_label)
    data["Realised Sales (INR Lakh)"] = pd.to_numeric(data["Realised Sales (INR Lakh)"], errors="coerce")
    return pd.DataFrame(out), data


def more_tables(perf, data):
    cls = perf[perf["Level"] == "Class"].copy()
    cls["Category"] = cls["Group"] + " / " + cls["Class"]
    monthly = cls[["Month", "Category", "Account", "Honasa"]].copy()
    sub = perf[perf["Level"] == "Sub-Class"].copy()
    sub["Category"] = sub["Group"] + " / " + sub["Class"] + " / " + sub["Category"].astype(str)
    sub = sub[["Month", "Category", "Account", "Honasa"]]
    d = data.copy()
    d["Category"] = d["Group"] + " / " + d["Class"]
    d["Zone"] = d["Zone"].map(lambda z: str(z).title())
    d["State"] = d["State"].map(lambda s: str(s).title().replace("Delhi/Ncr", "Delhi NCR"))
    piv = d.pivot_table(index=["Month", "Zone", "State", "DC City", "Category"], columns="Data For", values="Realised Sales (INR Lakh)", aggfunc="sum").reset_index()
    piv = piv.rename(columns={"MRL": "Account", "HCL": "Honasa", "DC City": "City"}).fillna({"Honasa": 0.0})
    hcl = d[d["Data For"] == "HCL"]
    art = hcl.groupby(["Month", "Category"]).agg(Articles=("Item No", "nunique"), Stores=("DC City", "nunique")).reset_index()
    sub_art = hcl.assign(Category=hcl["Category"] + " / " + hcl["Sub-Class"].astype(str)).groupby(["Month", "Category"]).agg(Articles=("Item No", "nunique"), Stores=("DC City", "nunique")).reset_index()
    return monthly, sub, piv, pd.concat([art, sub_art], ignore_index=True)


# ------------------------------------------------------------------ Wellness
def load_wellness(path):
    from pyxlsb import open_workbook
    with open_workbook(str(path)) as wb, wb.get_sheet("Sheet1") as sh:
        rows = [[c.v for c in r] for r in sh.rows()]
    months = [(i, month_label(v)) for i, v in enumerate(rows[0]) if i >= 4 and isinstance(v, float) and v > 30000]
    out, cur = [], {}
    for r in rows[1:]:
        if not r or r[0] != "HONASA CONSUMER PVT LTD":
            continue
        key = (r[1], r[2])
        if r[3] == "HONASA CONSUMER PVT LTD":
            cur[key] = {"h": r}
        elif r[3] == "OVERALL" and key in cur:
            cur[key]["o"] = r
    for (grp, cat), v in cur.items():
        if "o" not in v:
            continue
        for i, m in months:
            a, h = v["o"][i], v["h"][i]
            if a is None or h is None:
                continue
            out.append({"Month": m, "Group": str(grp).title(), "Category": str(cat).replace("\xa0", " ").title(), "Account": float(a), "Honasa": float(h)})
    df = pd.DataFrame(out)
    # months with no sales anywhere (the sheet carries empty future columns) are dropped
    live = df.groupby("Month")["Account"].sum()
    return df[df["Month"].isin(live[live > 0].index)]


# ------------------------------------------------------------------ Reliance
def load_reliance(path):
    """(stores, counters): Reliance category sales (RRL) against Honasa (HCL) by month, zone, state, category [, city for counters]."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import visit_cities as vc

    def prep(df, who_col, month_col="Month"):
        d = df.copy()
        d["who"] = d[who_col].astype(str).str.upper().str.strip()
        d = d[d["who"].isin(["HCL", "RRL"])]
        d["Month"] = d[month_col].map(month_label)
        d["Category"] = d["Article Hierarchy Brick.1"].astype(str).str.strip().str.title()
        d["Sales"] = pd.to_numeric(d["Total Gross Sales"], errors="coerce").fillna(0.0)
        d["Zone"] = d["Zone"].map(vc.norm_zone)
        std = d["State"].map(lambda x: vc.std_state(x)[0])
        unknown = sorted(set(d.loc[std.isna(), "State"].dropna()))
        if unknown:
            raise SystemExit(f"Reliance state(s) not in STATE_STANDARD: {unknown} (add them on purpose in scripts/visit_cities.py)")
        d["State"] = std
        return d

    stores = prep(pd.read_excel(path, sheet_name="Article MS Source", engine="pyxlsb"), "Data For")
    counters = prep(pd.read_excel(path, sheet_name="BA Store", header=1, engine="pyxlsb"), "Data Consider for")
    counters["City"] = counters["City"].map(lambda c: str(c).strip().title() if isinstance(c, str) and c.strip() else None)
    return stores, counters


def reliance_tables(d, geo_keys):
    def split(keys):
        g = d.groupby(keys + ["who"], dropna=False)["Sales"].sum().unstack("who").fillna(0.0)
        g = g.rename(columns={"RRL": "Account", "HCL": "Honasa"}).reset_index()
        return g
    monthly = split(["Month", "Category"])
    geo = split(["Month"] + geo_keys + ["Category"])
    h = d[(d["who"] == "HCL") & (d["Sales"] > 0)]
    art = h.groupby(["Month", "Category"]).agg(Articles=("Article", "nunique")).reset_index()
    if "Store" in h:
        art = art.merge(h.groupby(["Month", "Category"]).agg(Stores=("Store", "nunique")).reset_index(), on=["Month", "Category"])
    else:
        art["Stores"] = None
    return monthly, geo, art


# ------------------------------------------------------------------ assemble
def finish(df, chain, source):
    df = df.copy()
    df.insert(0, "Chain", chain)
    df["Common Category"] = df["Category"].map(common_category)
    # a share above 100% means the two files class an item differently (Reliance Perfume, Hair Oil Others): sales stay in the totals, the share is left blank
    df["Share %"] = (df["Honasa"] / df["Account"] * 100).where((df["Account"] > 0) & (df["Honasa"] <= df["Account"] * 1.0001))
    df["Source"] = source
    return df.rename(columns={"Account": "Account Sales Rs L", "Honasa": "Honasa Sales Rs L"})


def build(lulu_path, more_path, wf_path, rel_path=None):
    cell, sku, stores = load_lulu(lulu_path)
    l_m, l_g, l_a = lulu_tables(cell, sku)
    perf, mdata = load_more(more_path)
    m_m, m_sub, m_g, m_a = more_tables(perf, mdata)
    wf = load_wellness(wf_path)
    parts = [finish(l_m, "Lulu", "Compiled_Monthly_Files (Lulu)"), finish(m_m, "More Retail", "More_MS (class level)"),
             finish(m_sub, "More Retail", "More_MS (sub-class level)").assign(**{"Level": "Sub-Class"}),
             finish(wf[["Month", "Category", "Account", "Honasa"]], "Wellness Forever", "Wellness_MS (Sheet1)")]
    geo_parts = [finish(l_g, "Lulu", "Compiled_Monthly_Files (Lulu)"), finish(m_g, "More Retail", "More_MS Data Sheet (DC city)")]
    art_parts = [l_a.assign(Chain="Lulu"), m_a.assign(Chain="More Retail")]
    if rel_path:
        r_s, r_c = load_reliance(rel_path)
        for chain, d, keys, src in (("Reliance Retail", r_s, ["Zone", "State"], "RIL_BA_Store_MS (Article MS Source)"),
                                    ("Reliance Brand Counter", r_c, ["Zone", "State", "City"], "RIL_BA_Store_MS (BA Store)")):
            rm, rg, ra = reliance_tables(d, keys)
            parts.append(finish(rm, chain, src))
            geo_parts.append(finish(rg, chain, src))
            art_parts.append(ra.assign(Chain=chain))
    monthly = pd.concat(parts, ignore_index=True)
    monthly["Level"] = monthly["Level"].fillna("Category") if "Level" in monthly else "Category"
    def scope(r):
        if r["Chain"] == "Lulu":
            return "Stores and categories where Honasa sells"
        if r["Chain"] == "Wellness Forever":
            return "All categories in the account file"
        if r["Chain"] == "Reliance Retail":
            return "Reliance stores outside the brand counters; RRL Others left out"
        if r["Chain"] == "Reliance Brand Counter":
            return "Staffed brand-counter (BA) stores only; RRL Others left out"
        return "Sub-categories where Honasa sells (to May 26)" if month_key(r["Month"]) <= (26, 4) else "Full account category report (from Jun 26)"
    monthly["Scope"] = monthly.apply(scope, axis=1)
    monthly["Month Key"] = monthly["Month"].map(lambda m: month_key(m)[0] * 12 + month_key(m)[1])
    monthly = monthly.sort_values(["Chain", "Month Key", "Category"]).drop(columns="Month Key")
    geo = pd.concat(geo_parts, ignore_index=True)
    geo["Month Key"] = geo["Month"].map(lambda m: month_key(m)[0] * 12 + month_key(m)[1])
    geo = geo.sort_values(["Chain", "Month Key", "Zone", "State", "Category"]).drop(columns="Month Key")
    art = pd.concat(art_parts, ignore_index=True)
    art["Common Category"] = art["Category"].map(common_category)
    smap = stores.rename(columns={"Plant Code": "Store Code", "Store": "Store Name", "City": "City (from store name)"})[["Store Code", "Store Name", "City (from store name)", "State", "Zone", "Format"]]
    smap.insert(0, "Chain", "Lulu")
    master = ROOT / "PowerBI" / "SeedData" / "Masters" / "Store_City_Master.csv"
    if master.exists():
        mm = pd.read_csv(master, dtype=str)
        mm = mm[mm["Chain Name"] == "Lulu"].set_index("Site Code")["City Final"]
        smap["City (store master)"] = smap["Store Code"].map(mm)
        alias = {"calicut": "kozhikode", "trivandrum": "thiruvananthapuram", "bangalore": "bengaluru"}
        norm = lambda c: alias.get(str(c).lower(), str(c).lower())   # noqa: E731
        def verdict(r):
            if pd.isna(r["City (store master)"]):
                return "Store not in the store master"
            if pd.isna(r["City (from store name)"]):
                return "City not in the store name"
            return "Same city" if norm(r["City (from store name)"]) == norm(r["City (store master)"]) else "Differs: check"
        smap["Check"] = smap.apply(verdict, axis=1)
    # relevance: only categories that matter to us are ever flagged (white space, proven elsewhere); the rest are shown for size only
    last3 = monthly[(monthly["Level"] == "Category") & monthly["Month"].isin(["Jun 26", "Jul 26", "Aug 26"])]
    mix = last3.groupby("Common Category")["Honasa Sales Rs L"].sum()
    relevant = set((mix / mix.sum() * 100)[lambda x: x >= RELEVANT_MIN_PCT].index) - {"Other"}
    for df in (monthly, geo, art):
        df["Relevant For Us"] = df["Common Category"].map(lambda c: "Yes" if c in relevant else "No")
    cmap = pd.concat([monthly[["Chain", "Category", "Common Category"]], art[["Chain", "Category", "Common Category"]]]).drop_duplicates().sort_values(["Chain", "Common Category", "Category"])
    return monthly, geo, art, smap, cmap


def qc_reliance(monthly, geo):
    """Ties to the figures inside the Reliance workbook itself (its pivots and its Aug26 Check sheet)."""
    chk = []
    r = monthly[(monthly["Chain"] == "Reliance Retail") & (monthly["Level"] == "Category")]
    c = monthly[(monthly["Chain"] == "Reliance Brand Counter") & (monthly["Level"] == "Category")]
    tot = r.groupby("Month")["Honasa Sales Rs L"].sum()
    chk.append(("Reliance Retail Aug 26 Honasa = 2,602.857 L (workbook Aug26 Check, Offtake Data)", round(abs(tot.get("Aug 26", 0) - 2602.857), 2), 0))
    ctot = c.groupby("Month")["Honasa Sales Rs L"].sum()
    chk.append(("Reliance Brand Counter Aug 26 Honasa = 1,600.298 L (workbook Aug26 Check, Brand Counter Stores)", round(abs(ctot.get("Aug 26", 0) - 1600.298), 2), 0))
    fw = r[(r["Category"] == "Face Wash") & (r["Month"] == "Jan 26")].iloc[0]
    chk.append(("Reliance Face Wash Jan 26 RRL = 3,018.97 L and HCL = 618.99 L (workbook TOP Category MS)", round(abs(fw["Account Sales Rs L"] - 3018.972) + abs(fw["Honasa Sales Rs L"] - 618.992), 2), 0))
    sh = r[(r["Category"] == "Shampoo Herbal") & (r["Month"] == "Aug 26")].iloc[0]
    chk.append(("Reliance Shampoo Herbal Aug 26 RRL = 2,324.48 L and HCL = 1,111.17 L (workbook TOP Category MS)", round(abs(sh["Account Sales Rs L"] - 2324.477) + abs(sh["Honasa Sales Rs L"] - 1111.168), 2), 0))
    g = geo[geo["Chain"] == "Reliance Retail"].groupby("Month")["Honasa Sales Rs L"].sum()
    chk.append(("Reliance Retail geo cut ties to the monthly cut", round(float(abs(g - tot.reindex(g.index)).max()), 3), 0))
    return chk


def qc(monthly, geo, art):
    """Checks that must hold; returns (name, found, expected)."""
    chk = []
    chk.append(("every chain has a standard name", len(set(monthly["Chain"]) - {"Lulu", "More Retail", "Wellness Forever", "Reliance Retail", "Reliance Brand Counter"}), 0))
    chk.append(("no share above 100%", int((monthly["Share %"] > 100.0001).sum()), 0))
    chk.append(("no blank category", int(monthly["Category"].isna().sum()), 0))
    dup = monthly.duplicated(["Chain", "Month", "Level", "Category"]).sum()
    chk.append(("one row per chain, month and category", int(dup), 0))
    # Lulu: monthly Honasa total ties to the file's own source totals (Rs): 105.92 L Jan, 115.31 L Aug
    lulu = monthly[monthly["Chain"] == "Lulu"].groupby("Month")["Honasa Sales Rs L"].sum()
    chk.append(("Lulu Aug 26 Honasa sales = 115.31 Rs L (source total 11,530,837.86)", round(abs(lulu.get("Aug 26", 0) - 115.3084), 3), 0))
    chk.append(("Lulu Jan 26 Honasa sales = 105.92 Rs L (source total 10,591,757.36)", round(abs(lulu.get("Jan 26", 0) - 105.9176), 3), 0))
    g = geo[geo["Chain"] == "Lulu"].groupby("Month")["Honasa Sales Rs L"].sum()
    chk.append(("More Retail scope break is flagged (both scopes present)", int(monthly[monthly["Chain"] == "More Retail"]["Scope"].nunique() != 2), 0))
    chk.append(("Lulu geo cut ties to the monthly cut", round(float(abs(g - lulu.reindex(g.index)).max()), 3), 0))
    if (monthly["Chain"] == "Reliance Retail").any():
        chk += qc_reliance(monthly, geo)
    return chk


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lulu", type=Path, required=True)
    ap.add_argument("--more", type=Path, required=True)
    ap.add_argument("--wellness", type=Path, required=True)
    ap.add_argument("--reliance", type=Path, help="RIL_BA_Store_MS_*.xlsb (optional; adds Reliance Retail and Reliance Brand Counter)")
    a = ap.parse_args()
    monthly, geo, art, smap, cmap = build(a.lulu, a.more, a.wellness, a.reliance)
    findings = qc(monthly, geo, art)
    for name, got, exp in findings:
        print(("PASS " if got == exp else "FAIL ") + name, got)
    if any(g != e for _, g, e in findings):
        raise SystemExit("QC failed, nothing written")
    OUT.mkdir(parents=True, exist_ok=True)
    r3 = lambda df: df.round({c: 4 for c in df.columns if df[c].dtype.kind == "f"})   # noqa: E731
    r3(monthly).to_csv(OUT / "Account_Category_Monthly.csv", index=False)
    r3(geo).to_csv(OUT / "Account_Category_Geo.csv", index=False)
    art.to_csv(OUT / "Account_Assortment.csv", index=False)
    smap.to_csv(OUT / "Account_Store_Map.csv", index=False)
    cmap.to_csv(OUT / "Account_Category_Map.csv", index=False)
    blank = monthly[monthly["Share %"].isna() & (monthly["Honasa Sales Rs L"] > 0)]
    print(f"WARN {len(blank)} chain-month-category rows have our sales above the account's category (item classed differently): share left blank, sales kept in totals ({blank['Honasa Sales Rs L'].sum():.1f} Rs L)")
    print("wrote", OUT)
    print(monthly.groupby("Chain")["Month"].agg(lambda s: f"{s.nunique()} months").to_string())
    print("categories mapped to Other:", sorted(cmap.loc[cmap["Common Category"] == "Other", "Category"].unique()))


if __name__ == "__main__":
    main()
