# -*- coding: utf-8 -*-
"""Validation & QC rules for the margin repository.

Every rule returns a flag; nothing is silently dropped. Each record ends up
with a set of Validation_Flags and a QC_Severity in the ladder:
    PASS  <  WARNING  <  FAIL  <  BLOCKED
BLOCKED / FAIL records are surfaced but NOT published to the "current" /
forecast-ready views until resolved.
"""
import math
import pandas as pd
from schema import VALID_GST
from config import DEFAULT_CONFIG, get_rule_severity

SEVERITY_ORDER = {"PASS": 0, "WARNING": 1, "FAIL": 2, "BLOCKED": 3}

# default rule -> severity (used when no config override is provided)
RULE_SEVERITY = DEFAULT_CONFIG["rule_severity"].copy()


def _blank(v):
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return str(v).strip() == ""


def _num(v):
    try:
        if _blank(v):
            return None
        return float(str(v).replace("%", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def validate_frame(df, today=None, cfg=None):
    """Return df with Validation_Flags, QC_Severity, Record_Status added.
    Cross-row rules (duplicate EAN / chain+article / effective date) included.
    cfg: optional config dict from config.load_config(); defaults apply if None.
    """
    today = pd.Timestamp(today) if today is not None else pd.Timestamp.today().normalize()
    rule_sev = (cfg or DEFAULT_CONFIG).get("rule_severity", RULE_SEVERITY)
    gst_rates = set((cfg or DEFAULT_CONFIG).get("gst_controls", {}).get("valid_rates", VALID_GST))
    df = df.copy()
    flags = [[] for _ in range(len(df))]

    # --- cross-row duplicate detection ---
    ean_norm = df["EAN"].map(lambda x: "" if _blank(x) else str(x).strip())
    chain_norm = df["Chain"].map(lambda x: "" if _blank(x) else str(x).strip().upper())
    art_norm = df["Article"].map(lambda x: "" if _blank(x) else str(x).strip().upper())

    # duplicate EAN mapped to >1 distinct article within a chain
    ean_group = {}
    for i, (c, e, a) in enumerate(zip(chain_norm, ean_norm, art_norm)):
        if e:
            ean_group.setdefault((c, e), set()).add(a)
    # duplicate chain+article rows
    ca_counts = {}
    for c, a in zip(chain_norm, art_norm):
        if a:
            ca_counts[(c, a)] = ca_counts.get((c, a), 0) + 1
    # duplicate effective date within same article identity
    eff = df["Effective From"].map(lambda x: "" if _blank(x) else str(x).strip())
    ident = list(zip(chain_norm, ean_norm, art_norm,
                     df["Pack Size"].astype(str), df["MRP"].astype(str), eff))
    ident_counts = {}
    for k in ident:
        ident_counts[k] = ident_counts.get(k, 0) + 1

    for i, row in df.reset_index(drop=True).iterrows():
        f = flags[i]
        ean, mrp = row.get("EAN"), row.get("MRP")
        if _blank(ean):
            f.append("BLANK_EAN")
        if _blank(mrp) or _num(mrp) is None:
            f.append("BLANK_MRP")
        if _blank(row.get("Chain")):
            f.append("MISSING_CHAIN")
        if _blank(row.get("Brand")):
            f.append("MISSING_BRAND")
        if _blank(row.get("Category")):
            f.append("MISSING_CATEGORY")

        tm = _num(row.get("Trade Margin %"))
        fem = _num(row.get("Final Effective Margin %"))
        for m in (tm, fem):
            if m is not None and m > 100:
                f.append("MARGIN_OVER_100")
            if m is not None and m < 0:
                f.append("NEGATIVE_MARGIN")
        if tm is None:
            f.append("BLANK_TRADE_MARGIN")

        gst = _num(row.get("GST %"))
        if gst is None:
            f.append("BLANK_GST")
        elif int(round(gst)) not in gst_rates:
            f.append("INCORRECT_GST")

        if _blank(row.get("Pack Size")):
            f.append("INCORRECT_PACK_SIZE")

        # commercials entirely blank?
        comm_vals = [_num(row.get(c)) for c in
                     ["Trade Margin %", "TOT %", "Backend %", "Frontend %",
                      "Visibility %", "Display %", "Scheme %"]]
        if all(v in (None, 0) for v in comm_vals):
            f.append("MISSING_COMMERCIALS")

        # cross-row
        c, e, a = chain_norm.iloc[i], ean_norm.iloc[i], art_norm.iloc[i]
        if e and len(ean_group.get((c, e), set())) > 1:
            f.append("DUPLICATE_EAN")
        if a and ca_counts.get((c, a), 0) > 1:
            f.append("DUPLICATE_CHAIN_ARTICLE")
        if ident_counts.get(ident[i], 0) > 1:
            f.append("DUPLICATE_EFFECTIVE_DATE")

        # dates / status
        et = row.get("Effective To")
        if not _blank(et):
            try:
                if pd.Timestamp(et) < today:
                    f.append("EXPIRED_COMMERCIAL")
            except (ValueError, TypeError):
                pass
        st = str(row.get("Status") or "").strip().lower()
        if st in ("inactive", "delisted", "discontinued", "closed", "n", "no"):
            f.append("INACTIVE_ARTICLE")

    dedup = [sorted(set(f)) for f in flags]
    df["Validation_Flags"] = ["; ".join(f) for f in dedup]
    df["QC_Severity"] = [
        max((rule_sev.get(x, "WARNING") for x in f), key=lambda s: SEVERITY_ORDER[s])
        if f else "PASS" for f in dedup
    ]
    df["Record_Status"] = df["QC_Severity"].map(
        lambda s: "PUBLISHED" if s in ("PASS", "WARNING") else "HELD")
    return df


def qc_report(df):
    """Repository-level QC engine summary."""
    total = len(df)
    sev = df["QC_Severity"].value_counts().to_dict()
    def has(flag):
        return int(df["Validation_Flags"].str.contains(flag, na=False).sum())
    published = int((df["Record_Status"] == "PUBLISHED").sum())
    health = round(100.0 * published / total, 1) if total else 0.0
    # confidence: penalise fails/blocked
    conf = round(100.0 * (sev.get("PASS", 0) + 0.6 * sev.get("WARNING", 0)) / total, 1) if total else 0.0
    rows = [
        ("Total Articles (records)", total),
        ("Total Chains", int(df["Chain"].nunique())),
        ("PASS", sev.get("PASS", 0)),
        ("WARNING", sev.get("WARNING", 0)),
        ("FAIL", sev.get("FAIL", 0)),
        ("BLOCKED", sev.get("BLOCKED", 0)),
        ("Blank EAN", has("BLANK_EAN")),
        ("Blank MRP", has("BLANK_MRP")),
        ("Blank / missing margins", has("BLANK_TRADE_MARGIN")),
        ("Missing commercials", has("MISSING_COMMERCIALS")),
        ("Duplicate EAN", has("DUPLICATE_EAN")),
        ("Duplicate Chain+Article", has("DUPLICATE_CHAIN_ARTICLE")),
        ("Duplicate effective dates", has("DUPLICATE_EFFECTIVE_DATE")),
        ("Margin > 100%", has("MARGIN_OVER_100")),
        ("Negative margin", has("NEGATIVE_MARGIN")),
        ("Incorrect GST", has("INCORRECT_GST")),
        ("Expired commercials", has("EXPIRED_COMMERCIAL")),
        ("Inactive articles", has("INACTIVE_ARTICLE")),
        ("Published (forecast-ready) records", published),
        ("Held records (need resolution)", total - published),
        ("Confidence Score %", conf),
        ("Repository Health %", health),
    ]
    return pd.DataFrame(rows, columns=["QC Metric", "Value"])
