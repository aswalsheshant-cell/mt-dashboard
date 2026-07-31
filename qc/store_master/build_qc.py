# -*- coding: utf-8 -*-
"""Chain-wise Store Master City QC + Duplicate Detection engine.
Produces a correction-ready 8-sheet Excel workbook.
Grounded in an offline curated India-geography reference (geo_ref.py).
No web sources are fabricated; web-uncertain rows are honestly flagged.
"""
import re, sys
from datetime import date
import pandas as pd
from geo_ref import (CANONICAL_CITY, CITY_INFO, LOCALITY_TO_CITY, STATE_CANON,
                     GROUPING_MEMBERS, STATE_GEO_ZONE, VALID_CITY_REGION,
                     AMBIGUOUS_MULTI_STATE)

SRC = "/root/.claude/uploads/49d427d8-c459-5531-9f39-32d1bfca9b64/2c0fb11b-Final_Jan26_to_June26_chainwise_storelist.xlsb"
OUT = "/tmp/claude-0/-home-user-mt-dashboard/49d427d8-c459-5531-9f39-32d1bfca9b64/scratchpad/Store_Master_QC_Report.xlsx"
TODAY = date(2026, 7, 31).isoformat()

STATE_NAMES_UPPER = {v[0].upper() for v in STATE_CANON.values()}

CHAIN_CANON = {
    "DMART": "DMart", "FRANKROS": "Frank Ross", "WH-SMITH": "WH Smith",
    "METRO CNC": "Metro C&C", "WALMART CNC": "Walmart C&C",
    "SANCUS(RMT)": "Sancus (RMT)", "BEAUTY & NUTRIE": "Beauty & Nutrie",
    "MORE RETAIL": "More Retail", "V-MART": "V-Mart", "VMM": "VMM",
    "H&G": "H&G", "WELLNESS FOREVER": "Wellness Forever", "APOLLO": "Apollo",
    "SASTA SUNDAR": "Sasta Sundar", "RELIANCE": "Reliance", "SPENCER": "Spencer",
    "TRENT": "Trent", "GUARDIAN": "Guardian", "LULU": "Lulu",
}


def nkey(s):
    """Normalised lookup key: upper, collapse spaces, strip trailing dots."""
    if s is None:
        return ""
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    s = s.rstrip(".").strip()
    return s.upper()


def title_case(s):
    if s is None:
        return ""
    s = re.sub(r"\s+", " ", str(s).strip())
    small = {"and", "of", "the", "&"}
    out = []
    for w in s.split(" "):
        if not w:
            continue
        if w.upper() in {"HSR", "BTM", "OMR", "LB", "RR", "CP", "T", "VMM", "H&G", "KVK"}:
            out.append(w.upper())
        elif w.lower() in small:
            out.append(w.lower() if out else w.capitalize())
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


def norm_name(s):
    """Aggressive normalisation for duplicate matching."""
    s = nkey(s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)       # drop punctuation/dots/hyphens
    s = re.sub(r"\bH\s*S\s*R\b", "HSR", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
df = pd.read_excel(SRC, sheet_name="Sheet1", engine="pyxlsb", header=1)
df = df.loc[:, ~df.columns.astype(str).str.startswith("Unnamed")]
df = df.rename(columns={c: c.strip() for c in df.columns})
N = len(df)
print("loaded rows:", N)

# Preserve Site Code exactly as text
def sc_text(x):
    if isinstance(x, float) and x == x and float(x).is_integer():
        return str(int(x))
    return str(x).strip()

orig = df.copy()
df["Site Code"] = df["Site Code"].map(sc_text)

# ---------------------------------------------------------------------------
# Per-row classification
# ---------------------------------------------------------------------------
records = []
for i, r in df.iterrows():
    chain_raw = "" if pd.isna(r["Chain Name"]) else str(r["Chain Name"]).strip()
    sc_raw = r["Site Code"]
    sn_raw = "" if pd.isna(r["Site Name"]) else str(r["Site Name"]).strip()
    zone_raw = "" if pd.isna(r["Zone"]) else str(r["Zone"]).strip()
    state_raw = "" if pd.isna(r["State"]) else str(r["State"]).strip()
    city_raw = "" if pd.isna(r["City"]) else str(r["City"]).strip()

    chain_canon = CHAIN_CANON.get(nkey(chain_raw), title_case(chain_raw))
    sc_clean = "" if nkey(sc_raw) in ("(BLANK)", "BLANK", "NAN", "") else str(sc_raw).strip()
    sn_clean = title_case(sn_raw)

    ckey = nkey(city_raw)
    skey = nkey(state_raw)

    # ---- STATE ----
    if skey in STATE_CANON:
        state_canon, is_group = STATE_CANON[skey]
    else:
        state_canon, is_group = (title_case(state_raw), False)
    rec_state = state_canon
    state_status = "PASS"
    state_is_city_error = (skey == "MUMBAI")
    if state_is_city_error:
        rec_state = "Maharashtra"
        state_status = "STATE CORRECTION REQUIRED"
    elif not state_raw:
        state_status = "STATE MISSING"
    elif state_canon != state_raw:
        state_status = "FORMAT STANDARDIZATION"

    # ---- CITY ----
    rec_district = ""
    city_status = "PASS"
    if not city_raw:
        rec_city = ""
        city_status = "CITY MISSING"
    elif ckey in LOCALITY_TO_CITY:
        rec_city = LOCALITY_TO_CITY[ckey]
        city_status = "LOCALITY MAINTAINED AS CITY"
    elif ckey in VALID_CITY_REGION:
        # Delhi / Delhi NCR are legitimate city / region labels
        rec_city = CANONICAL_CITY.get(ckey, title_case(city_raw))
        city_status = "PASS" if rec_city == city_raw else "FORMAT STANDARDIZATION"
    elif ckey in STATE_NAMES_UPPER:
        # city column holds a state name
        rec_city = title_case(city_raw)
        city_status = "STATE MAINTAINED AS CITY"
    elif ckey in CANONICAL_CITY:
        rec_city = CANONICAL_CITY[ckey]
        city_status = "PASS" if rec_city == city_raw else "FORMAT STANDARDIZATION"
    else:
        rec_city = title_case(city_raw)
        city_status = "PASS" if rec_city == city_raw else "FORMAT STANDARDIZATION"

    # geographic knowledge for the recommended city
    info = CITY_INFO.get(rec_city)
    geo_zone = ""
    state_city_mismatch = False
    if info:
        rec_district, true_state, geo_zone = info
        if is_group:
            members = GROUPING_MEMBERS.get(state_canon, set())
            if members and true_state not in members:
                state_city_mismatch = True
        else:
            if not state_is_city_error and state_canon and true_state != state_canon:
                state_city_mismatch = True
        # ambiguous multi-state city: don't force a correction if maintained
        # state (or its grouping members) plausibly contains the city
        if state_city_mismatch and rec_city in AMBIGUOUS_MULTI_STATE:
            valid = AMBIGUOUS_MULTI_STATE[rec_city]
            plausible = {state_canon} | GROUPING_MEMBERS.get(state_canon, set())
            if plausible & valid:
                state_city_mismatch = False
        if state_city_mismatch:
            state_status = "STATE-CITY MISMATCH"
            rec_state = true_state  # recommend the geographically correct state
    if not geo_zone:
        geo_zone = STATE_GEO_ZONE.get(state_canon, "")

    # ---- ZONE ----
    def std_zone(z):
        if not z:
            return ""
        parts = re.split(r"[-\s]+", z.strip())
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0].capitalize() + "-" + parts[1]
        return parts[0].capitalize() if len(parts) == 1 else "-".join(
            [parts[0].capitalize()] + parts[1:])
    rec_bzone = std_zone(zone_raw)
    zone_status = "PASS" if rec_bzone == zone_raw else ("ZONE MISSING" if not zone_raw
                                                        else "FORMAT STANDARDIZATION")

    records.append(dict(
        idx=i, chain_raw=chain_raw, sc_raw=str(sc_raw), sn_raw=sn_raw,
        zone_raw=zone_raw, state_raw=state_raw, city_raw=city_raw,
        chain_canon=chain_canon, sc_clean=sc_clean, sn_clean=sn_clean,
        rec_city=rec_city, rec_district=rec_district, rec_state=rec_state,
        rec_bzone=rec_bzone, geo_zone=geo_zone,
        city_status=city_status, state_status=state_status, zone_status=zone_status,
        city_known=bool(info), state_city_mismatch=state_city_mismatch,
        state_is_city_error=state_is_city_error,
    ))

res = pd.DataFrame(records)
print("classified rows:", len(res))

# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------
res["dup_status"] = "UNIQUE"
res["dup_group"] = ""
res["dup_type"] = ""
res["master_flag"] = ""
res["conflict_fields"] = ""

def chain_abbr(c):
    a = re.sub(r"[^A-Z]", "", c.upper())[:6]
    return a or "CHN"

grp_counter = {}
def next_gid(chain):
    ab = chain_abbr(chain)
    grp_counter[ab] = grp_counter.get(ab, 0) + 1
    return "DUP-%s-%04d" % (ab, grp_counter[ab])

res["_norm_name"] = res["sn_raw"].map(norm_name)

# --- Pass A: exact Chain + Site Code collisions (code present) ---
present = res[res["sc_clean"] != ""]
for (chain, sc), g in present.groupby([present["chain_canon"], present["sc_clean"].str.upper()]):
    if len(g) < 2:
        continue
    gid = next_gid(chain)
    names = g["_norm_name"].nunique()
    cities = g["rec_city"].nunique()
    states = g["rec_state"].nunique()
    identical = (names == 1 and cities == 1 and states == 1)
    dtype = "EXACT DUPLICATE" if identical else "SITE CODE CONFLICT"
    dstatus = "EXACT DUPLICATE" if identical else "SITE CODE CONFLICT"
    conf = []
    if names > 1: conf.append("Site Name")
    if cities > 1: conf.append("City")
    if states > 1: conf.append("State")
    if g["rec_bzone"].nunique() > 1: conf.append("Zone")
    # master = most complete (longest cleaned site name), tie-break lowest idx
    gi = g.copy()
    gi["_score"] = gi["sn_clean"].str.len().fillna(0)
    master_idx = gi.sort_values(["_score", "idx"], ascending=[False, True]).index[0]
    for j in g.index:
        res.at[j, "dup_group"] = gid
        res.at[j, "dup_status"] = dstatus
        res.at[j, "dup_type"] = dtype
        res.at[j, "master_flag"] = "MASTER" if j == master_idx else "DUPLICATE"
        res.at[j, "conflict_fields"] = ", ".join(conf)

# --- Pass B: blank site codes -> cannot key, needs verification ---
for j in res[res["sc_clean"] == ""].index:
    if res.at[j, "dup_status"] == "UNIQUE":
        res.at[j, "dup_status"] = "SITE CODE CONFLICT"
        res.at[j, "dup_type"] = "MISSING SITE CODE"
        res.at[j, "conflict_fields"] = "Site Code"

# --- Pass C: same store, different site code / formatting dup ---
# within chain + recommended city, group by normalised name
cand = res[(res["dup_status"] == "UNIQUE") & (res["_norm_name"] != "") & (res["rec_city"] != "")]
for (chain, city, nm), g in cand.groupby([cand["chain_canon"], cand["rec_city"], cand["_norm_name"]]):
    if len(g) < 2:
        continue
    codes = g["sc_clean"].nunique()
    raw_names = g["sn_raw"].str.strip().nunique()
    gid = next_gid(chain)
    if raw_names > 1:
        dtype = "DUPLICATE DUE TO FORMATTING"
        dstatus = "DUPLICATE DUE TO FORMATTING"
    elif codes > 1:
        dtype = "SAME STORE, DIFFERENT SITE CODE"
        dstatus = "SAME STORE, DIFFERENT SITE CODE"
    else:
        dtype = "POSSIBLE DUPLICATE"
        dstatus = "POSSIBLE DUPLICATE"
    gi = g.copy()
    gi["_score"] = gi["sn_clean"].str.len().fillna(0) + (gi["sc_clean"] != "").astype(int) * 5
    master_idx = gi.sort_values(["_score", "idx"], ascending=[False, True]).index[0]
    conf = []
    if raw_names > 1: conf.append("Site Name formatting")
    if codes > 1: conf.append("Site Code")
    for j in g.index:
        res.at[j, "dup_group"] = gid
        res.at[j, "dup_status"] = dstatus
        res.at[j, "dup_type"] = dtype
        res.at[j, "master_flag"] = "MASTER" if j == master_idx else "DUPLICATE"
        res.at[j, "conflict_fields"] = ", ".join(conf)

# ---------------------------------------------------------------------------
# Action / confidence / remarks / method / evidence
# ---------------------------------------------------------------------------
def build_row(r):
    cs, ss, zs, ds = r.city_status, r.state_status, r.zone_status, r.dup_status
    remarks, methods = [], []
    manual = False

    # geographic / city remarks
    if cs == "CITY MISSING":
        remarks.append("City value is blank; cannot validate. Manual review required.")
        manual = True
    elif cs == "LOCALITY MAINTAINED AS CITY":
        remarks.append("Current City '%s' is a locality within %s. Recommended parent city assigned."
                       % (r.city_raw, r.rec_city))
        methods.append("Locality-to-city mapping")
    elif cs == "STATE MAINTAINED AS CITY":
        remarks.append("Current City '%s' appears to be a state name, not a city. Verify correct city."
                       % r.city_raw)
        manual = True
    elif cs == "FORMAT STANDARDIZATION":
        remarks.append("City geographically consistent; standardize spelling/case '%s' -> '%s'."
                       % (r.city_raw, r.rec_city))
        methods.append("Canonical city standardization")
    elif cs == "PASS":
        if r.city_known:
            remarks.append("City '%s' validated against geography reference." % r.rec_city)
        else:
            remarks.append("City '%s' retained; internally consistent." % r.rec_city)

    # state remarks
    if r.state_is_city_error:
        remarks.append("State 'Mumbai' is a city, not a state; corrected to Maharashtra.")
        methods.append("State correction")
    elif ss == "STATE-CITY MISMATCH":
        remarks.append("City '%s' geographically belongs to %s, not maintained '%s'. Verify."
                       % (r.rec_city, r.rec_state, r.state_raw))
        manual = True
    elif ss == "FORMAT STANDARDIZATION":
        methods.append("State standardization")
    elif ss == "STATE MISSING":
        remarks.append("State value is blank.")
        manual = True

    if zs == "FORMAT STANDARDIZATION":
        methods.append("Zone standardization")
    elif zs == "ZONE MISSING":
        remarks.append("Zone value is blank.")

    # duplicate remarks + action priority
    action = "RETAIN AS IS"
    if ds == "EXACT DUPLICATE":
        methods.append("Exact key match")
        if r.master_flag == "MASTER":
            remarks.append("Exact duplicate group %s; retain this record as master." % r.dup_group)
            action = "RETAIN AS IS"
        else:
            remarks.append("Exact duplicate of master in %s; remove." % r.dup_group)
            action = "REMOVE EXACT DUPLICATE"
    elif ds == "SITE CODE CONFLICT":
        methods.append("Site-code conflict analysis")
        if r.dup_type == "MISSING SITE CODE":
            remarks.append("Site Code is blank; cannot key uniquely. Verify correct code with chain team.")
        else:
            remarks.append("Same Chain+Site Code maps to differing %s (group %s). Verify with chain team."
                           % (r.conflict_fields or "details", r.dup_group))
        action = "VERIFY SITE CODE"
        manual = True
    elif ds == "SAME STORE, DIFFERENT SITE CODE":
        methods.append("Name+city similarity")
        remarks.append("Same store name & city under different Site Codes (group %s)." % r.dup_group)
        action = "MERGE DUPLICATE RECORDS" if r.master_flag != "MASTER" else "RETAIN AS IS"
        manual = True
    elif ds == "DUPLICATE DUE TO FORMATTING":
        methods.append("Formatting-variant match")
        remarks.append("Store name differs only by formatting within same city (group %s)." % r.dup_group)
        action = "MERGE DUPLICATE RECORDS" if r.master_flag != "MASTER" else "RETAIN AS IS"
        manual = True
    elif ds == "POSSIBLE DUPLICATE":
        methods.append("Name+city similarity")
        remarks.append("Possible duplicate; evidence insufficient to confirm same physical outlet (group %s)."
                       % r.dup_group)
        action = "VERIFY WITH CHAIN TEAM"
        manual = True

    # if no duplicate action, derive from corrections
    if action == "RETAIN AS IS":
        if r.state_is_city_error:
            action = "CORRECT STATE"
        elif ss == "STATE-CITY MISMATCH":
            action = "CORRECT STATE"
        elif cs in ("LOCALITY MAINTAINED AS CITY", "STATE MAINTAINED AS CITY"):
            action = "CORRECT CITY"
        elif cs == "CITY MISSING":
            action = "MANUAL REVIEW"
        elif cs == "FORMAT STANDARDIZATION":
            action = "STANDARDIZE CITY NAME"
        elif ss == "FORMAT STANDARDIZATION":
            action = "CORRECT STATE"
        elif zs == "FORMAT STANDARDIZATION":
            action = "CORRECT ZONE"

    # confidence
    if ds == "EXACT DUPLICATE":
        conf = 95
    elif ds in ("SITE CODE CONFLICT", "POSSIBLE DUPLICATE"):
        conf = 62
    elif ds in ("SAME STORE, DIFFERENT SITE CODE", "DUPLICATE DUE TO FORMATTING"):
        conf = 72
    elif cs == "CITY MISSING" or cs == "STATE MAINTAINED AS CITY":
        conf = 40
    elif ss == "STATE-CITY MISMATCH":
        conf = 60
    elif r.state_is_city_error:
        conf = 96
    elif cs == "LOCALITY MAINTAINED AS CITY":
        conf = 90
    elif cs in ("FORMAT STANDARDIZATION", "PASS") and r.city_known:
        conf = 95 if cs == "PASS" else 92
    elif cs in ("FORMAT STANDARDIZATION", "PASS"):
        conf = 80  # standardized but city not in offline reference
    else:
        conf = 75

    if conf < 75:
        manual = True

    # validation method / evidence
    if not methods:
        methods.append("Internal workbook consistency")
    method = "; ".join(dict.fromkeys(methods))
    if r.city_known or r.state_is_city_error or cs == "LOCALITY MAINTAINED AS CITY":
        evidence = "Curated India geography reference (offline) + internal workbook consistency"
    elif conf < 75:
        evidence = "Insufficient offline evidence - web/store-locator verification recommended"
    else:
        evidence = "Internal workbook consistency (offline); web verification recommended for low-frequency towns"

    if not remarks:
        remarks.append("Record validated; no correction required.")
    return pd.Series(dict(action=action, confidence=conf, manual=("YES" if manual else "NO"),
                          method=method, evidence=evidence, remarks=" ".join(remarks)))

extra = res.apply(build_row, axis=1)
res = pd.concat([res, extra], axis=1)
print("row-build done")
res.to_pickle("/tmp/claude-0/-home-user-mt-dashboard/49d427d8-c459-5531-9f39-32d1bfca9b64/scratchpad/res.pkl")
orig.to_pickle("/tmp/claude-0/-home-user-mt-dashboard/49d427d8-c459-5531-9f39-32d1bfca9b64/scratchpad/orig.pkl")
print("saved intermediate")
