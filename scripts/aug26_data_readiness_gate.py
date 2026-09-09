#!/usr/bin/env python3
"""
Aug'26 Primary vs Offtake -- Data Readiness Gate.

Reusable validation utility so every corrected/additional Aug'26 Primary,
Secondary or Offtake file gets re-run through the SAME checks instead of being
manually patched into the dashboard. This script never touches dashboard
code or source files -- it only reads inputs and reports/records readiness.

IMPORTANT -- "Customer name 2" caution (do not remove this without the data
owner's sign-off): the raw primary export carries a "Customer name 2" field
that lists several chain names for one distributor row (e.g. "Dmart/Apollo/
H&G/Lulu/Max Hyper/Pothys"). It looks like the same thing the allocation
methodology doc calls "Dist chain ten", but that is an OBSERVATION, not a
confirmed mapping. This script uses it ONLY as diagnostic evidence in the
exception register (which chains a distributor's pool *might* cover) -- it is
NEVER used as an allocation weight or ratio source. Allocation only happens
when actual chain-level Secondary evidence exists. Promoting "Customer name 2"
to a real allocation input requires the data owner confirming what the field
actually means.

Usage:
    python scripts/aug26_data_readiness_gate.py \
        --primary <path> --secondary <path> --offtake <path> \
        [--prior-primary <path>] [--prior-secondary-month 2026-07] [--prior-offtake <path>] \
        [--promote]

Without --promote, the script only reports (dry run) -- it never writes to
the baseline history file. Pass --promote to append a new baseline record
after you have reviewed the report.
"""
import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import build_dashboard_data as bdd  # governed canon_chain / canon_brand -- do not reimplement

BASELINE_DIR = REPO_ROOT / "PowerBI" / "docs" / "DataReadiness"
BASELINE_FILE = BASELINE_DIR / "Aug26_Baseline_History.jsonl"

PUBLICATION_LABEL = "AUG'26 PARTIAL PRIMARY VS OFFTAKE -- COVERED CHAINS ONLY"

# Agreed thresholds (Phase 6). Do not change without explicit business approval.
PRIMARY_COVERAGE_PARTIAL_THRESHOLD_PCT = 80.0
UNRESOLVED_OFFTAKE_WARNING_PCT = 5.0

# The 8 chains under active investigation as of the approved baseline. New
# unknown chains discovered by a future run are NEVER silently matched --
# they always land in the exception register (Phase 3).
TRACKED_EXCEPTION_CHAINS = [
    "Lulu", "Spencer", "Ratnadeep", "National Mart", "Frankross",
    "Sumo Save", "B&N", "Apna Mart",
]

REQUIRED_SECONDARY_COLS = {"Source_Month", "Distributor", "Chain", "Brand", "EAN", "NSV_Value"}
REQUIRED_OFFTAKE_COLS = {"Chain Name", "Brand", "NSV", "Description as per Fountain"}

# Two known Primary schema variants seen in this repo:
#  - "raw SAP invoice" (the ad-hoc Aug'26 upload): NSV value, Chain Name,
#    Ship-To Name, Division Desc., Cancelled (explicit column), EAN No.
#  - "locked File2/query16" (official Primary_Article_Monthly/*.csv, per
#    PowerBI/docs/DistributorPrimaryAllocation_Logic.md): Inv. Net value(LOC),
#    Chain name for Dashboard, Ship To Name, brand, EAN No., MTD-Sale type
#    (Cancel Invoice / MRN / Sales -- no separate Cancelled column).
# Both are normalized to the same canonical column names below so the rest
# of this script never has to care which one it was handed.
PRIMARY_SCHEMA_ALIASES = {
    "NSV value": "NSV value", "Inv. Net value(LOC)": "NSV value",
    "Chain Name": "Chain Name", "Chain name for Dashboard": "Chain Name",
    "Ship-To Name": "Ship-To Name", "Ship To Name": "Ship-To Name",
    "Division Desc.": "Division Desc.", "brand": "Division Desc.",
    "EAN No.": "EAN No.",
    "Description": "Description",
    "PO Type": "PO Type",
}
REQUIRED_PRIMARY_COLS_CANONICAL = {"NSV value", "Chain Name", "Ship-To Name", "PO Type",
                                    "Division Desc.", "EAN No."}


def normalize_primary_schema(df):
    df = df.rename(columns={k: v for k, v in PRIMARY_SCHEMA_ALIASES.items() if k in df.columns})
    if "Cancelled" not in df.columns:
        # Locked File2 schema has no explicit Cancelled column -- derive it
        # from MTD-Sale type so both schemas cancel out the same rows.
        if "MTD-Sale type" in df.columns:
            df["Cancelled"] = pd.Series(
                np.where(df["MTD-Sale type"] == "Cancel Invoice", "X", None), dtype=object)
        else:
            df["Cancelled"] = pd.Series([None] * len(df), dtype=object)
    return df


def norm_desc(x):
    if pd.isna(x):
        return None
    return re.sub(r"\s+", " ", str(x).strip().upper()).replace("-", " ")


# --------------------------------------------------------------------------
# PHASE 2 -- INPUT VALIDATION
# --------------------------------------------------------------------------
def validate_input(df, required_cols, label, grain_cols=None):
    problems = []
    missing = required_cols - set(c.strip() for c in df.columns)
    if missing:
        problems.append(f"{label}: missing required columns {sorted(missing)}")
    if grain_cols and set(grain_cols) <= set(df.columns):
        dups = df.duplicated(subset=grain_cols).sum()
        if dups:
            problems.append(f"{label}: {dups} duplicate records at grain {grain_cols}")
    return problems


def load_primary(path):
    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    df = normalize_primary_schema(df)
    problems = validate_input(df, REQUIRED_PRIMARY_COLS_CANONICAL, "Primary")
    df["NSV value"] = pd.to_numeric(df["NSV value"], errors="coerce")
    if df["NSV value"].isna().any():
        problems.append(f"Primary: {df['NSV value'].isna().sum()} rows failed to parse NSV value as numeric")
    df = df[df["Cancelled"].isna()].copy()
    df["NSV value"] = df["NSV value"].fillna(0.0)
    blank_chain = df["Chain Name"].isna().sum()
    if blank_chain:
        problems.append(f"Primary: {blank_chain} rows with blank Chain Name")
    ean_ok = pd.to_numeric(df["EAN No."], errors="coerce").round(0).astype("Int64").astype(str)
    ean_rounded_suspect = (ean_ok.str.endswith("000000") | ean_ok.str.endswith("00000")).mean()
    soft_warnings = []
    if ean_rounded_suspect > 0.5:
        soft_warnings.append(
            f"Primary: EAN No. looks corrupted -- {ean_rounded_suspect:.0%} of values are "
            "suspiciously round (Excel float-export defect). This blocks ARTICLE-level "
            "reconciliation only (see Phase 7) -- it does not block chain-level analysis.")
    return df, problems, soft_warnings


def load_secondary(path, month):
    df = pd.read_csv(path, low_memory=False)
    # NOTE: no duplicate-grain check here. (Source_Month, Distributor, Chain,
    # Brand, EAN) looks like it should be unique but is verifiably NOT --
    # rows sharing that exact key legitimately carry different NSV_Value and
    # different Chain_TOT_Pct (consistent with this file's documented
    # quirks in .claude/skills/mt-distributor-secondary/SKILL.md). Asserting
    # an unverified grain would itself be an invented rule, which is exactly
    # what this gate exists to avoid -- so this stays an open question for
    # the data owner rather than a hard-coded (and wrong) duplicate check.
    problems = validate_input(df, REQUIRED_SECONDARY_COLS, "Secondary")
    df["NSV_Value"] = pd.to_numeric(df["NSV_Value"], errors="coerce")
    if df["NSV_Value"].isna().any():
        problems.append(f"Secondary: {df['NSV_Value'].isna().sum()} rows failed to parse NSV_Value as numeric")
    df["NSV_Value"] = df["NSV_Value"].fillna(0.0)
    if month not in set(df["Source_Month"].astype(str)):
        problems.append(f"Secondary: no rows found for expected period {month} -- wrong file or period?")
    df_month = df[df["Source_Month"].astype(str) == month].copy()
    blank = df_month["Distributor"].isna().sum() + df_month["Chain"].isna().sum()
    if blank:
        problems.append(f"Secondary: {blank} blank Distributor/Chain identifiers in {month}")
    return df, df_month, problems


def load_offtake(path):
    df = pd.read_csv(path, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    # NOTE: no duplicate-grain check here either. (Site Code, Article, Chain
    # Name) is not confirmed unique -- rows sharing that exact key can carry
    # identical Sales Qty/NSV, and this extract has no transaction/invoice-
    # level identifier to prove whether that is a real repeat sale or a true
    # duplicate. Flagging a number here without being able to tell the two
    # apart would be a guess dressed up as a finding.
    problems = validate_input(df, REQUIRED_OFFTAKE_COLS, "Offtake")
    df["NSV"] = pd.to_numeric(df["NSV"], errors="coerce")
    if df["NSV"].isna().any():
        problems.append(f"Offtake: {df['NSV'].isna().sum()} rows failed to parse NSV as numeric")
    df["NSV"] = df["NSV"].fillna(0.0)
    blank_chain = df["Chain Name"].isna().sum()
    if blank_chain:
        problems.append(f"Offtake: {blank_chain} rows with blank Chain Name")
    return df, problems


def fingerprint_file(path):
    """SHA-256 + size, computed by reading the file (never writing to it), so
    a replacement file with the SAME NAME but DIFFERENT CONTENT is detectable
    in the baseline record -- a filename alone cannot prove the source is
    the one that was actually validated."""
    p = Path(path)
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return dict(path=str(p), sha256=h.hexdigest(), size_bytes=p.stat().st_size)


def check_total_collapse(new_total, prior_total, label, tolerance_pct=50.0):
    """Flag a suspicious total swing vs the prior known good file (not a hard
    fail -- a genuine partial drop can legitimately look like this -- but it
    must be surfaced, never silently accepted)."""
    if prior_total is None or prior_total == 0:
        return []
    change_pct = abs(new_total - prior_total) / prior_total * 100
    if change_pct > tolerance_pct:
        return [f"{label}: total moved {change_pct:.0f}% vs prior reference "
                f"({prior_total:,.2f}L -> {new_total:,.2f}L) -- confirm this is a real "
                f"partial-coverage file and not a load error before trusting it"]
    return []


# --------------------------------------------------------------------------
# PHASE 3 -- CHAIN NORMALIZATION (governed mapping only, no fuzzy matching)
# --------------------------------------------------------------------------
def build_chain_mapping_audit(primary, secondary_month, offtake):
    """Every raw chain-ish string seen across the three sources, canonicalized
    ONLY via the repo's governed canon_chain(). Anything canon_chain() passes
    through unchanged (i.e. no alias exists) is flagged UNKNOWN_CHAIN --
    status NEEDS_REVIEW -- never silently treated as a new match."""
    rows = []
    seen = set()

    def add(raw, source):
        raw = str(raw).strip()
        if not raw or raw.lower() == "nan" or (raw, source) in seen:
            return
        seen.add((raw, source))
        canon = bdd.canon_chain(raw)
        known = raw.lower() in bdd._ALIAS_LOOKUP or raw == canon and raw in bdd._ALIAS_LOOKUP.values()
        rows.append(dict(
            raw_chain=raw, canonical_chain=canon, source=source,
            mapping_method="repo CHAIN_ALIASES (governed)" if raw.lower() in bdd._ALIAS_LOOKUP else "passthrough (no alias found)",
            confidence="High" if raw.lower() in bdd._ALIAS_LOOKUP else "Unconfirmed",
            status="MAPPED" if raw.lower() in bdd._ALIAS_LOOKUP else "NEEDS_REVIEW",
        ))

    for v in primary["Chain Name"].dropna().unique():
        add(v, "Primary.Chain Name")
    for v in secondary_month["Chain"].dropna().unique():
        add(v, "Secondary.Chain")
    for v in offtake["Chain Name"].dropna().unique():
        add(v, "Offtake.Chain Name")

    return pd.DataFrame(rows).sort_values(["status", "source", "raw_chain"])


# --------------------------------------------------------------------------
# PHASE 4 -- ALLOCATION (unchanged methodology) + EXCEPTION RECHECK
# --------------------------------------------------------------------------
# Confirmed, reviewed spelling-variant fixes: the SAME real-world distributor
# spelled differently in the primary Ship-To Name column vs the secondary
# Distributor column (verified by exact-string cross-check against the Aug'26
# secondary file -- these are not a guess, they were checked one at a time).
# This is separate from, and much narrower than, the "Customer name 2"
# question: it does not assign a distributor to a chain, it only lets the
# SAME distributor's primary and secondary rows find each other so the
# existing chain-split ratio logic below can run at all.
DISTRIBUTOR_NAME_ALIAS = {
    "JUST MARK-Dmart_ship to": "JUST MARK-Dmart",
    "Kiran Trading Co_Shipto (Solapur)": "Kiran Trading Co- Dmart",
    "Kiran Trading Company_Ship to": "Kiran Trading Co- Dmart",
    "M/S KOTTARAM BUSINESS CORPORATION-MT": "M/S KOTTARAM BUSINESS CORPORATION-M",
}


def allocate_primary(primary, secondary_month):
    """Same method validated in the earlier sessions: Direct rows keep their
    own Chain Name; Dist. rows are split using ONLY actual chain-level
    Secondary evidence (article-description match first, then
    distributor+brand fallback). 'Customer name 2' is NEVER used as a
    weight here -- see module docstring."""
    primary = primary.copy()
    primary["_brand"] = primary["Division Desc."].map(bdd.canon_brand)
    primary["_desc"] = primary["Description"].map(norm_desc)
    primary["_distributor"] = primary["Ship-To Name"].astype(str).str.strip().replace(DISTRIBUTOR_NAME_ALIAS)

    sec = secondary_month.copy()
    sec["_brand"] = sec["Brand"].map(bdd.canon_brand)
    sec["_desc"] = sec["Article"].map(norm_desc) if "Article" in sec.columns else None
    sec["_distributor"] = sec["Distributor"].astype(str).str.strip()
    sec["_chain"] = sec["Chain"].map(bdd.canon_chain)

    art_grp = sec.groupby(["_distributor", "_brand", "_desc", "_chain"])["NSV_Value"].sum().reset_index()
    art_tot = art_grp.groupby(["_distributor", "_brand", "_desc"])["NSV_Value"].sum().rename("tot").reset_index()
    art_grp = art_grp.merge(art_tot, on=["_distributor", "_brand", "_desc"])
    art_grp["frac"] = art_grp["NSV_Value"] / art_grp["tot"].replace(0, np.nan)
    art_ratio = {k: list(zip(g["_chain"], g["frac"])) for k, g in art_grp.groupby(["_distributor", "_brand", "_desc"]) if g["tot"].iloc[0] > 0}

    db_grp = sec.groupby(["_distributor", "_brand", "_chain"])["NSV_Value"].sum().reset_index()
    db_tot = db_grp.groupby(["_distributor", "_brand"])["NSV_Value"].sum().rename("tot").reset_index()
    db_grp = db_grp.merge(db_tot, on=["_distributor", "_brand"])
    db_grp["frac"] = db_grp["NSV_Value"] / db_grp["tot"].replace(0, np.nan)
    db_ratio = {k: list(zip(g["_chain"], g["frac"])) for k, g in db_grp.groupby(["_distributor", "_brand"]) if g["tot"].iloc[0] > 0}

    direct = primary[primary["PO Type"] == "Direct"].copy()
    direct["Allocated_Chain"] = direct["Chain Name"].map(bdd.canon_chain)
    direct["Allocation_Basis"] = "Direct (unambiguous)"

    dist = primary[primary["PO Type"] == "Dist."].copy()
    out_rows = []
    for _, r in dist.iterrows():
        key_art = (r["_distributor"], r["_brand"], r["_desc"])
        key_db = (r["_distributor"], r["_brand"])
        if key_art in art_ratio:
            splits, basis = art_ratio[key_art], "Allocated (article-level Secondary ratio)"
        elif key_db in db_ratio:
            splits, basis = db_ratio[key_db], "Allocated (distributor-brand Secondary ratio)"
        else:
            splits, basis = [("Unmapped Chain", 1.0)], "Unmapped (no Secondary evidence)"
        for chain, frac in splits:
            row = r.copy()
            row["Allocated_Chain"] = chain
            row["Allocation_Basis"] = basis
            row["NSV value"] = r["NSV value"] * frac
            out_rows.append(row)
    dist_alloc = pd.DataFrame(out_rows) if out_rows else dist.iloc[0:0].copy()

    result = pd.concat([direct, dist_alloc], ignore_index=True, sort=False)

    # Phase 8 check: derived == parent, nothing lost or invented
    assert abs(result["NSV value"].sum() - primary["NSV value"].sum()) < 0.01, \
        "Reconciliation failure: allocated total does not match parent Primary total"
    return result


def recheck_exceptions(primary, secondary_month, offtake, prior_secondary_month=None,
                        prior_primary=None, prior_offtake=None):
    """Classify each tracked exception chain. 'Customer name 2' is checked
    here ONLY as diagnostic evidence -- whether a distributor's pooled primary
    row *mentions* this chain -- to tell MAPPING_GAP (real primary probably
    exists, just pooled under a distributor) apart from PRIMARY_SOURCE_MISSING
    (no trace of the chain anywhere in primary). It is never used to compute
    an allocated amount; see the DISTRIBUTOR_NAME_ALIAS / allocate_primary
    docstring for why that stays out of scope until the data owner confirms
    what the field means."""
    has_custname2 = "Customer name 2" in primary.columns
    dist_rows = primary[primary["PO Type"] == "Dist."] if "PO Type" in primary.columns else primary.iloc[0:0]

    rows = []
    for chain in TRACKED_EXCEPTION_CHAINS:
        p_val = primary[primary["Chain Name"].map(bdd.canon_chain) == chain]["NSV value"].sum() / 1e5
        s_val = secondary_month[secondary_month["Chain"].map(bdd.canon_chain) == chain]["NSV_Value"].sum() / 1e5
        o_val = offtake[offtake["Chain Name"].map(bdd.canon_chain) == chain]["NSV"].sum()

        prior_p = (prior_primary[prior_primary["Chain Name"].map(bdd.canon_chain) == chain]["NSV value"].sum() / 1e5
                   if prior_primary is not None else None)
        prior_s = (prior_secondary_month[prior_secondary_month["Chain"].map(bdd.canon_chain) == chain]["NSV_Value"].sum() / 1e5
                   if prior_secondary_month is not None else None)
        prior_o = (prior_offtake[prior_offtake["Chain Name"].map(bdd.canon_chain) == chain]["NSV"].sum()
                   if prior_offtake is not None else None)

        pooled_evidence_L = None
        pooled_distributors = []
        if has_custname2 and len(dist_rows):
            pattern = re.escape(chain.split(" (")[0].split(" [")[0])
            mask = dist_rows["Customer name 2"].astype(str).str.contains(pattern, case=False, na=False, regex=True)
            if mask.any():
                pooled_evidence_L = round(dist_rows.loc[mask, "NSV value"].sum() / 1e5, 2)
                pooled_distributors = sorted(dist_rows.loc[mask, "Ship-To Name"].unique().tolist())

        # NOTE on SECONDARY_SOURCE_MISSING vs PRIMARY_SOURCE_MISSING: both
        # require p_val == 0 this month (no Aug-26 Primary landed for this
        # chain either way), so the label must describe what is DIFFERENT
        # about the two situations, not just repeat "no Primary" under two
        # names. SECONDARY_SOURCE_MISSING is reserved for a chain we can
        # independently confirm DID have real Primary before (prior_p > 0)
        # -- i.e. Secondary specifically dropping out this month is plausibly
        # *why* the split broke. If Primary itself has never been seen for
        # this chain (prior_p in (0, None) too), the accurate description is
        # PRIMARY_SOURCE_MISSING regardless of whether Secondary happened to
        # exist in a prior month -- that fact is still visible in
        # prior_secondary_L for evidence, it just isn't the current-month
        # root cause.
        if p_val > 0 and o_val > 0:
            status = "MATCHED"
        elif o_val > 0 and p_val == 0 and s_val > 0:
            status = "MAPPING_GAP"          # secondary sees it, primary allocation didn't land it
        elif o_val > 0 and p_val == 0 and pooled_evidence_L:
            status = "MAPPING_GAP"          # diagnostic only: named in a distributor's pooled billing, not yet split
        elif o_val > 0 and p_val == 0 and s_val == 0 and (prior_p or 0) > 0:
            status = "SECONDARY_SOURCE_MISSING"   # this chain's Primary was confirmed before -- Secondary dropping is the plausible current-month cause
        elif o_val > 0 and p_val == 0 and s_val == 0 and not any([prior_s, prior_o, prior_p]):
            status = "UNRESOLVED"           # no corroborating history anywhere -- too little evidence to classify confidently
        elif o_val > 0 and p_val == 0 and s_val == 0:
            status = "PRIMARY_SOURCE_MISSING"     # Primary has never been captured for this chain in any period checked, regardless of Secondary/Offtake history
        else:
            status = "UNRESOLVED"

        rows.append(dict(chain=chain, aug26_primary_L=round(p_val, 4), aug26_secondary_L=round(s_val, 4),
                          aug26_offtake_L=round(o_val, 4), prior_primary_L=prior_p, prior_secondary_L=prior_s,
                          prior_offtake_L=prior_o, pooled_distributor_evidence_L=pooled_evidence_L,
                          pooled_distributors="; ".join(pooled_distributors) if pooled_distributors else None,
                          status=status))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# PHASE 6 -- COVERAGE
# --------------------------------------------------------------------------
def compute_coverage(allocated_primary, offtake):
    off = offtake.copy()
    off["_chain"] = off["Chain Name"].map(bdd.canon_chain)
    prim_chains = set(allocated_primary["Allocated_Chain"].unique())
    off_chains = set(off["_chain"].unique())
    matched_chains = prim_chains & off_chains

    total_primary = allocated_primary["NSV value"].sum() / 1e5
    matched_primary = allocated_primary[allocated_primary["Allocated_Chain"].isin(matched_chains)]["NSV value"].sum() / 1e5
    matched_offtake = off[off["_chain"].isin(matched_chains)]["NSV"].sum()
    total_offtake = off["NSV"].sum()
    unresolved_offtake = total_offtake - matched_offtake

    value_coverage_pct = (matched_primary / total_primary * 100) if total_primary else 0.0
    unresolved_offtake_pct = (unresolved_offtake / total_offtake * 100) if total_offtake else 0.0
    chain_coverage_pct = (len(matched_chains) / len(off_chains) * 100) if off_chains else 0.0

    status = "PARTIAL" if value_coverage_pct < PRIMARY_COVERAGE_PARTIAL_THRESHOLD_PCT else "FULL"
    dq_warning = unresolved_offtake_pct > UNRESOLVED_OFFTAKE_WARNING_PCT

    return dict(
        matched_chains=sorted(matched_chains), total_primary_L=round(total_primary, 2),
        matched_primary_L=round(matched_primary, 2), unmatched_primary_L=round(total_primary - matched_primary, 2),
        total_offtake_L=round(total_offtake, 2), matched_offtake_L=round(matched_offtake, 2),
        unresolved_offtake_L=round(unresolved_offtake, 2), value_coverage_pct=round(value_coverage_pct, 1),
        chain_coverage_pct=round(chain_coverage_pct, 1), unresolved_offtake_pct=round(unresolved_offtake_pct, 1),
        status=status, dq_warning=dq_warning,
    )


# --------------------------------------------------------------------------
# PHASE 7 -- ARTICLE READINESS (checks only -- never auto-promotes to READY)
# --------------------------------------------------------------------------
def article_readiness_check(primary, secondary_month, offtake):
    findings = {}

    ean_num = pd.to_numeric(primary["EAN No."], errors="coerce")
    findings["primary_ean_nonnull_pct"] = round(ean_num.notna().mean() * 100, 1)
    findings["primary_ean_unique_count"] = int(ean_num.dropna().nunique())
    findings["primary_ean_reliable"] = findings["primary_ean_unique_count"] > 50  # sanity floor, not a business threshold

    off_ean = offtake["EAN"] if "EAN" in offtake.columns else pd.Series(dtype=float)
    findings["offtake_ean_nonnull_pct"] = round(off_ean.notna().mean() * 100, 1) if len(off_ean) else 0.0
    findings["offtake_ean_unique_count"] = int(pd.to_numeric(off_ean, errors="coerce").dropna().nunique())

    p_desc = set(primary["Description"].map(norm_desc).dropna()) if "Description" in primary.columns else set()
    o_desc = set(offtake["Description as per Fountain"].map(norm_desc).dropna()) if "Description as per Fountain" in offtake.columns else set()
    record_match_pct = round(len(p_desc & o_desc) / max(len(p_desc), 1) * 100, 1)
    findings["description_record_match_pct"] = record_match_pct

    p_val = primary.copy()
    p_val["_desc"] = p_val["Description"].map(norm_desc)
    matched_val = p_val[p_val["_desc"].isin(o_desc)]["NSV value"].sum()
    total_val = p_val["NSV value"].sum()
    findings["description_value_weighted_match_pct"] = round(matched_val / total_val * 100, 1) if total_val else 0.0

    ready = (not findings["primary_ean_reliable"]) is False and findings["primary_ean_unique_count"] > 50 \
        and findings["primary_ean_nonnull_pct"] > 95 and findings["offtake_ean_nonnull_pct"] > 95
    findings["status"] = "READY" if ready else "BLOCKED_BY_SOURCE_KEY_QUALITY"
    findings["note"] = ("Free-text description match rate is reported for visibility ONLY -- "
                         "it is never used as the production reconciliation key.")
    return findings


# --------------------------------------------------------------------------
# BASELINE PERSISTENCE (Phase 1 / 9 / 10)
# --------------------------------------------------------------------------
def load_baseline_history():
    if not BASELINE_FILE.exists():
        return []
    with open(BASELINE_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]


def append_baseline(record):
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    with open(BASELINE_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")


def delta_report(prior, new):
    if prior is None:
        print("No prior baseline on file -- this run becomes baseline #1 if promoted.")
        return
    print(f"\nPREVIOUS -> NEW")
    print(f"Primary coverage:     {prior['coverage']['value_coverage_pct']}% -> {new['coverage']['value_coverage_pct']}%")
    print(f"Matched chains:       {len(prior['coverage']['matched_chains'])} -> {len(new['coverage']['matched_chains'])}")
    print(f"Matched Primary:      Rs{prior['coverage']['matched_primary_L']}L -> Rs{new['coverage']['matched_primary_L']}L")
    print(f"Matched Offtake:      Rs{prior['coverage']['matched_offtake_L']}L -> Rs{new['coverage']['matched_offtake_L']}L")
    print(f"Unresolved Offtake:   Rs{prior['coverage']['unresolved_offtake_L']}L -> Rs{new['coverage']['unresolved_offtake_L']}L")
    prior_status_counts = pd.Series([r["status"] for r in prior["exceptions"]]).value_counts().to_dict()
    new_status_counts = pd.Series([r["status"] for r in new["exceptions"]]).value_counts().to_dict()
    for status in ["MATCHED", "MAPPING_GAP", "SECONDARY_SOURCE_MISSING", "PRIMARY_SOURCE_MISSING", "UNRESOLVED"]:
        pv, nv = prior_status_counts.get(status, 0), new_status_counts.get(status, 0)
        if pv or nv:
            print(f"{status}: {pv} -> {nv}")
    print(f"Article status:       {prior['article_readiness']['status']} -> {new['article_readiness']['status']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--primary", required=True, help="Aug'26 primary raw invoice CSV")
    ap.add_argument("--secondary", required=True, help="Secondary hierarchy CSV covering Aug'26 (and ideally prior months)")
    ap.add_argument("--offtake", required=True, help="Aug'26 store x article offtake CSV")
    ap.add_argument("--month", default="2026-08", help="Expected Source_Month tag for the secondary file")
    ap.add_argument("--prior-primary", help="Prior month primary (for exception-history comparison)")
    ap.add_argument("--prior-secondary-month", default="2026-07", help="Prior Source_Month tag inside --secondary")
    ap.add_argument("--prior-offtake", help="Prior month offtake (for exception-history comparison)")
    ap.add_argument("--promote", action="store_true", help="Append this run to the baseline history (default: dry run, report only)")
    args = ap.parse_args()

    problems = []       # hard problems -- block the gate / chain analysis
    soft_warnings = []  # known, already-scoped issues (e.g. EAN quality) -- affect article gate only
    primary, p_probs, p_soft = load_primary(args.primary)
    secondary_all, secondary_month, s_probs = load_secondary(args.secondary, args.month)
    offtake, o_probs = load_offtake(args.offtake)
    problems += p_probs + s_probs + o_probs
    soft_warnings += p_soft

    fingerprints = dict(primary=fingerprint_file(args.primary),
                         secondary=fingerprint_file(args.secondary),
                         offtake=fingerprint_file(args.offtake))

    history = load_baseline_history()
    prior_record = history[-1] if history else None
    if prior_record:
        problems += check_total_collapse(primary["NSV value"].sum() / 1e5,
                                          prior_record["coverage"]["total_primary_L"], "Primary")
        problems += check_total_collapse(offtake["NSV"].sum(),
                                          prior_record["coverage"]["total_offtake_L"], "Offtake")
    provenance_notices = []
    if prior_record:
        prior_fp = prior_record.get("source_fingerprints", {})
        for key in ("primary", "secondary", "offtake"):
            prior_path = prior_record.get("source_files", {}).get(key)
            new_path = str(getattr(args, key))
            prior_sha = prior_fp.get(key, {}).get("sha256")
            if prior_path == new_path and prior_sha and prior_sha != fingerprints[key]["sha256"]:
                provenance_notices.append(
                    f"{key}: same filename as the prior baseline record but DIFFERENT content "
                    f"(sha256 changed from {prior_sha[:12]}... to {fingerprints[key]['sha256'][:12]}...) "
                    "-- this is a genuine replacement file, not a re-read of the same source.")
            elif prior_path == new_path and prior_sha == fingerprints[key]["sha256"]:
                provenance_notices.append(f"{key}: identical file (same name, same sha256) as the prior baseline record.")

    print("=" * 90)
    print(f"AUG'26 DATA READINESS GATE -- run at {datetime.now(timezone.utc).isoformat()}")
    print("=" * 90)
    print(f"\nPHASE 2 -- INPUT VALIDATION: {'FAIL' if problems else 'PASS'}")
    for p in problems:
        print(f"  ! {p}")
    for w in soft_warnings:
        print(f"  (known, scoped) {w}")
    for n in provenance_notices:
        print(f"  (provenance) {n}")

    # A missing required column or an unrecognized period is structural --
    # continuing into allocation/coverage would crash with a raw traceback
    # instead of a clean, explicit failure. Stop here rather than let a bad
    # input produce a stack trace (or worse, a partially-computed result).
    structural = [p for p in problems if "missing required columns" in p or "no rows found for expected period" in p]
    if structural:
        print(f"\nSTRUCTURAL INPUT PROBLEM -- cannot safely proceed to allocation/coverage:")
        for s in structural:
            print(f"  ! {s}")
        print("\nDATA READINESS GATE: FAIL")
        print("RECOMMENDED DISPOSITION: REJECT SOURCE")
        if args.promote:
            print("\n--promote requested but gate FAILed -- refusing to write baseline.")
        sys.exit(1)

    chain_audit = build_chain_mapping_audit(primary, secondary_month, offtake)
    needs_review = chain_audit[chain_audit["status"] == "NEEDS_REVIEW"]
    print(f"\nPHASE 3 -- CHAIN NORMALIZATION: {len(chain_audit)} raw chain strings audited, "
          f"{len(needs_review)} NEEDS_REVIEW (no governed alias)")

    allocated = allocate_primary(primary, secondary_month)
    prior_primary_df = None
    prior_secondary_month_df = secondary_all[secondary_all["Source_Month"].astype(str) == args.prior_secondary_month]
    prior_offtake_df = None
    if args.prior_primary:
        prior_primary_df, _, _ = load_primary(args.prior_primary)
    if args.prior_offtake:
        prior_offtake_df, _ = load_offtake(args.prior_offtake)

    exceptions = recheck_exceptions(primary, secondary_month, offtake,
                                     prior_secondary_month_df, prior_primary_df, prior_offtake_df)
    print(f"\nPHASE 4 -- EXCEPTION RECHECK:")
    print(exceptions.to_string(index=False))

    coverage = compute_coverage(allocated, offtake)
    print(f"\nPHASE 6 -- COVERAGE: {coverage}")

    article = article_readiness_check(primary, secondary_month, offtake)
    print(f"\nPHASE 7 -- ARTICLE READINESS: {article}")

    # Phase 8 reconciliation controls
    recon_ok = True
    if allocated["NSV value"].isna().any() or np.isinf(allocated["NSV value"]).any():
        problems.append("Reconciliation: NaN/Infinity found in allocated Primary")
        recon_ok = False
    if allocated["Allocated_Chain"].isna().any():
        problems.append("Reconciliation: rows with no Allocated_Chain")
        recon_ok = False
    matched_set = set(coverage["matched_chains"])
    exc_matched_wrongly = exceptions[(exceptions["status"] != "MATCHED") & (exceptions["chain"].isin(matched_set))]
    if len(exc_matched_wrongly):
        problems.append(f"Reconciliation: {len(exc_matched_wrongly)} unresolved chain(s) leaked into MATCHED set")
        recon_ok = False
    print(f"\nPHASE 8 -- RECONCILIATION: {'PASS' if recon_ok else 'FAIL'}")

    record = dict(
        run_at=datetime.now(timezone.utc).isoformat(),
        source_files=dict(primary=str(args.primary), secondary=str(args.secondary), offtake=str(args.offtake)),
        source_fingerprints=fingerprints,
        period=args.month,
        input_validation_problems=problems,
        input_validation_soft_warnings=soft_warnings,
        chain_mapping_needs_review=needs_review["raw_chain"].tolist(),
        exceptions=exceptions.to_dict(orient="records"),
        coverage=coverage,
        article_readiness=article,
    )
    record = json.loads(json.dumps(record, default=lambda o: bool(o) if isinstance(o, np.bool_) else float(o)))

    delta_report(prior_record, record)

    gate_pass = (not problems) and recon_ok
    print(f"\nDATA READINESS GATE: {'PASS' if gate_pass else 'FAIL'}")

    if coverage["value_coverage_pct"] >= 80 and article["status"] == "READY":
        disposition = "READY FOR DASHBOARD INTEGRATION"
    elif coverage["value_coverage_pct"] >= 80:
        disposition = "ACCEPT FOR CHAIN ANALYSIS"
    elif not problems:
        disposition = "ACCEPT AS PARTIAL"
    else:
        disposition = "REJECT SOURCE"
    print(f"RECOMMENDED DISPOSITION: {disposition}")
    print(f"Mandatory label while PARTIAL: \"{PUBLICATION_LABEL}\"")

    if args.promote:
        if not gate_pass:
            print("\n--promote requested but gate FAILed -- refusing to write baseline. Fix input problems first.")
            sys.exit(1)
        append_baseline(record)
        print(f"\nBaseline promoted -- appended to {BASELINE_FILE}")
    else:
        print("\nDry run only (no --promote) -- baseline history NOT modified.")


if __name__ == "__main__":
    main()
