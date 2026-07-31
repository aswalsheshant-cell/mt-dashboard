# -*- coding: utf-8 -*-
"""Lightweight natural-language-ish query over the repository current view.

This is a pragmatic keyword parser (not an LLM). It covers the charter's
example queries. Returns a filtered DataFrame; the CLI prints it.
"""
import re
import pandas as pd


def search(current, query):
    q = " " + query.lower().strip() + " "
    df = current.copy()
    if df.empty:
        return df

    def col_contains(col, term):
        return df[col].astype(str).str.lower().str.contains(re.escape(term), na=False)

    # margin below / above X
    m = re.search(r"margin (below|under|less than|<)\s*(\d+(\.\d+)?)", q)
    if m:
        thr = float(m.group(2))
        val = pd.to_numeric(df["Final Effective Margin %"], errors="coerce")
        df = df[val < thr]
    m = re.search(r"margin (above|over|greater than|>)\s*(\d+(\.\d+)?)", q)
    if m:
        thr = float(m.group(2))
        val = pd.to_numeric(df["Final Effective Margin %"], errors="coerce")
        df = df[val > thr]

    # "not listed in <chain>"  -> articles (by EAN) absent from that chain
    m = re.search(r"not listed in ([a-z0-9 &\-]+)", q)
    if m:
        chain = m.group(1).strip()
        listed = set(df[col_contains("Chain", chain)]["EAN"].astype(str))
        df = df[~df["EAN"].astype(str).isin(listed) & (df["EAN"].astype(str) != "")]

    # chain / brand / category keyword filters
    KNOWN_CHAINS = ["apollo", "reliance", "dmart", "nykaa", "wellness", "spencer",
                    "trent", "guardian", "lulu", "vmart", "v-mart", "more", "metro"]
    for ch in KNOWN_CHAINS:
        if (" " + ch + " ") in q or (" " + ch + "'s ") in q:
            df = df[col_contains("Chain", ch)]
            break
    # brand
    for br in df["Brand"].dropna().astype(str).str.lower().unique():
        if br and (" " + br + " ") in q:
            df = df[col_contains("Brand", br)]
            break
    # category keywords
    for cat_word in ["sunscreen", "shampoo", "serum", "facewash", "face wash",
                     "moisturizer", "conditioner", "cream", "oil", "kajal"]:
        if cat_word in q:
            df = df[col_contains("Category", cat_word) | col_contains("Sub Category", cat_word)
                    | col_contains("Article", cat_word)]
            break

    # "changed margin this month"
    if "changed" in q and ("month" in q or "this month" in q):
        ts = pd.to_datetime(df["Last Updated"], errors="coerce")
        now = pd.Timestamp.today()
        df = df[(ts.dt.month == now.month) & (ts.dt.year == now.year)]

    return df
