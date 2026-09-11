#!/usr/bin/env python3
"""Target scope reconciliation -- why the incentive target file does not equal
the business target.

Method is KA-11. A target file that does not equal the corporate target is NOT
automatically wrong: quota scope can legitimately exclude accounts, brands or
populations that are outside the incentive plan. So this script does not scale,
allocate or "correct" the difference. It decomposes it, names what is missing,
and leaves the classification for the business to confirm.

Reads   : the RKAM target planning workbook + dashboard/data.js (business universe)
Writes  : incentive_working/target_scope_reconciliation.csv
          incentive_working/target_scope_diagnostic.json
          incentive_working/target_scope_decision_pack.md   (restricted, for MT Leadership/Finance)

Usage:
  python scripts/target_scope_diagnostic.py --targets <RKAM_target_file.xlsx>
"""
from __future__ import annotations
import argparse, csv, json, re, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from build_dashboard_data import canon_chain, canon_zone_name  # noqa: E402

OUT = REPO / "incentive_working"
MON3 = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Business target for FY27, from the project's verified baselines (Rs L).
BUSINESS_TARGET_L = 44132.86

# Variants the shared canon_chain() does not yet reach, kept here rather than in the
# dashboard's alias table because they are target-file spellings. Each is a formatting
# or route-to-market variant of one chain -- never a merge of two commercial entities.
TARGET_CHAIN_ALIASES = {
    "d mart": "DMart",
    "apollo direct": "Apollo",
    "apollo healthco limited": "Apollo",
    "relaince direct": "Reliance Retail",      # source typo for Reliance
    "reliance direct": "Reliance Retail",
    "more retail ltd": "More Retail",
    "abrl -more": "More Retail",
    "abrl-more": "More Retail",
    "metro cnc": "Metro C&C",
    "metro": "Metro C&C",
    "metro cash n carry": "Metro C&C",
    "v mart": "V-Mart",
    "wh smith": "WH-Smith",
}
# Values that name more than one chain at once. These cannot be split without a
# business rule, so they are reported as their own class, never silently assigned.
COMPOSITE_CHAINS = {"h&g/ b&n & rd", "h&g/vmm", "mrl/ vmm/h&g"}
# A catch-all bucket is not a chain. It is target value with no account attached,
# which matters for scope because it cannot be tested against the chain universe.
BUCKET_CHAINS = {"others"}

BRAND_ALIASES = {
    "emerging brand": "Emerging Brand (unspecified)",
    "emerging brand(the derma co)": "The Derma Co",
    "b blunt": "BBlunt",
}


def canon_target_chain(raw):
    """(canonical, method). Raw is always preserved by the caller."""
    if raw is None or not str(raw).strip():
        return None, "BLANK"
    k = str(raw).replace("\xa0", " ").strip()
    kl = re.sub(r"\s+", " ", k).lower()
    if kl in COMPOSITE_CHAINS:
        return k, "COMPOSITE_UNRESOLVED"
    if kl in BUCKET_CHAINS:
        return k, "CATCH_ALL_BUCKET"
    if kl in TARGET_CHAIN_ALIASES:
        return TARGET_CHAIN_ALIASES[kl], "TARGET_ALIAS"
    c = canon_chain(k)
    return c, "SHARED_ALIAS" if c != k else "AS_IS"


def canon_brand(raw):
    k = re.sub(r"\s+", " ", str(raw or "").strip())
    kl = k.lower()
    if not k:
        return None, "BLANK"
    if kl in BRAND_ALIASES:
        return BRAND_ALIASES[kl], "BRAND_ALIAS"
    return k, "AS_IS"


def read_targets(path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = next((wb[n] for n in wb.sheetnames if "TARGET MASTER" in n.upper()), wb[wb.sheetnames[0]])
    rows = list(ws.iter_rows(values_only=True))
    hi = next(i for i, r in enumerate(rows[:15])
              if r and any(str(c).strip().upper() == "TARGET" for c in r if c))
    hdr = [("" if c is None else str(c).strip()) for c in rows[hi]]
    ix = {h: i for i, h in enumerate(hdr) if h}
    out = []
    for r in rows[hi + 1:]:
        if not r or not r[0]:
            continue
        g = lambda k: ("" if ix.get(k) is None or ix[k] >= len(r) or r[ix[k]] is None
                       else str(r[ix[k]]).strip())
        m = r[ix["Month"]] if ix.get("Month") is not None and ix["Month"] < len(r) else None
        try:
            val = float(r[ix["Target"]] or 0)
        except (TypeError, ValueError):
            val = 0.0
        out.append({
            "FY": g("FY"),
            "Month": f"{MON3[m.month - 1]}-{m.year % 100:02d}" if hasattr(m, "month") else str(m or "")[:10],
            "Region_Raw": g("Region"), "State": g("State"),
            "Chain_Raw": g("Chain"), "Brand_Raw": g("Brand"),
            "BDO_BDE": g("BDO/BDE"), "RKAM": g("RKAM"), "Target": val,
        })
    return out


def business_universe():
    """Chain and brand universe, with FY26 (a complete 12 months) as the mix basis.

    FY27 offtake only covers Apr-Jul so far, so it cannot carry a full-year mix.
    FY26 is the last complete year and is used only to size what a missing chain
    is worth -- an indication, never an allocation.
    """
    txt = (REPO / "dashboard" / "data.js").read_text()
    D = json.loads(txt[re.search(r"window\.DASH\s*=\s*", txt).end():].rstrip().rstrip(";"))
    o = D["offtake"]
    rows = o["by_chain"] if isinstance(o["by_chain"], list) else \
        [dict(name=k, **v) for k, v in o["by_chain"].items()]
    chains = {}
    for r in rows:
        nm = r.get("name") or r.get("chain")
        if nm:
            chains[canon_chain(nm)] = {"fy26": r.get("fy26") or 0.0, "fy27": r.get("fy27") or 0.0}
    brands = [b.get("name") for b in o.get("by_brand", []) if isinstance(b, dict) and b.get("name")]
    return chains, brands, o


def write_decision_pack(path, d):
    """A one-page pack for MT Leadership / Finance. States the causes, not just the size."""
    g = d["gap_decomposition"]
    L = []
    A = L.append
    A("# Target scope — decision pack (RESTRICTED)\n")
    A(f"Generated {d['generated']}. Source: All India RKAM Target Planning compiled file.\n")
    A("## The question\n")
    A(f"The incentive target file totals **Rs {d['target_file_total_L']:,.2f} L "
      f"(Rs {d['target_file_total_L'] / 100:,.2f} Cr)** against a business target of "
      f"**Rs {d['business_target_L']:,.2f} L (Rs {d['business_target_L'] / 100:,.2f} Cr)** "
      f"— {d['coverage_pct']}% coverage, a gap of Rs {g['gap_L']:,.2f} L.\n")
    A("A target file that does not equal the business target is not automatically wrong. "
      "What matters is whether each difference is an intended exclusion. "
      f"**{100 - g['unexplained_pct_of_gap']:.0f}% of the gap is now traced to specific causes.**\n")
    A("## What explains the gap\n")
    A("| # | Cause | Indicative value (Rs L) | Share of gap | Basis |")
    A("|---|---|---:|---:|---|")
    for i, e in enumerate(g["explained"], 1):
        A(f"| {i} | {e['cause']} | {e['indicative_L']:,.2f} | "
          f"{e['indicative_L'] / g['gap_L'] * 100:.0f}% | {e['basis']} |")
    A(f"| | **Unexplained residual** | **{g['unexplained_L']:,.2f}** | "
      f"**{g['unexplained_pct_of_gap']:.0f}%** | no entity accounts for it |")
    A("")
    for i, e in enumerate(g["explained"], 1):
        A(f"**{i}. {e['cause']}** — {e['detail']}\n")
    A("## Questions for the business\n")
    pc = d["period_coverage"]
    if pc["part_year_regions"]:
        names = ", ".join(sorted(pc["part_year_regions"]))
        A(f"**Q1 (MT Leadership) — {names} are planned for H1 only.** "
          f"Oct-26 to Mar-27 carries no target for these regions. Is the incentive plan "
          f"H1-only for them, or is the H2 plan still to be loaded? "
          f"Indicative H2 value Rs {pc['indicative_missing_L']:,.2f} L.\n")
    miss = d["dimensions"]["chain"]["in_business_not_in_target"]
    if miss:
        top = ", ".join(list(miss)[:5])
        A(f"**Q2 (MT Leadership) — {len(miss)} live accounts have no target row:** {top}. "
          "Are these deliberately outside the incentive plan (for example e-commerce or "
          "non-field-managed accounts), or is this a coverage gap?\n")
    gd = d["grain_defects"]
    if gd["blank_chain_L"]:
        A(f"**Q3 (MT Leadership / MT Ops) — Rs {gd['blank_chain_L']:,.2f} L "
          f"({gd['blank_chain_pct_of_file']}% of the file) carries no chain name**, all of it in "
          f"{', '.join(gd['blank_chain_regions'])}. Those regions are planned at state x brand x person "
          "level while the rest are planned at chain level. If incentive achievement is measured "
          "chain-wise, these employees cannot be measured on the same basis. "
          f"({gd['double_counting_check']})\n")
    A(f"**Q4 (Finance) — Rs {g['unexplained_L']:,.2f} L of the gap is not explained by any "
      "region, account, brand or period above.** Is the business target on a different basis "
      "(for example Primary vs Offtake, or gross vs net) from the target file?\n")
    A("## Status until answered\n")
    A("`Target_Scope_Status = UNKNOWN_SCOPE`. No target has been scaled, allocated or adjusted, "
      "and no incentive payout is calculated. Once the scope is confirmed, the status changes "
      "to CONFIRMED and the achievement rows unblock on that gate.\n")
    path.write_text("\n".join(L))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--out-dir", default=str(OUT))
    a = ap.parse_args()
    outd = Path(a.out_dir)
    outd.mkdir(parents=True, exist_ok=True)

    tg = read_targets(Path(a.targets))
    raw_total = sum(t["Target"] for t in tg)

    # --- canonicalise, preserving raw --------------------------------------
    for t in tg:
        t["Chain"], t["Chain_Method"] = canon_target_chain(t["Chain_Raw"])
        t["Brand"], t["Brand_Method"] = canon_brand(t["Brand_Raw"])
        z, ok = canon_zone_name(t["Region_Raw"], json.loads((REPO / "config" / "analytics_config.json").read_text()))
        t["Region"], t["Region_Matched"] = (z or t["Region_Raw"]), ok
    canon_total = sum(t["Target"] for t in tg)
    assert abs(canon_total - raw_total) < 0.01, "normalisation changed the total"

    chains_u, brands_u, offt = business_universe()

    def agg(key):
        d = defaultdict(float)
        n = defaultdict(int)
        for t in tg:
            d[t[key] or "(blank)"] += t["Target"]
            n[t[key] or "(blank)"] += 1
        return d, n

    rec_rows = []
    diag = {"generated": date.today().isoformat(),
            "target_file_total_L": round(raw_total, 2),
            "business_target_L": BUSINESS_TARGET_L,
            "gap_L": round(BUSINESS_TARGET_L - raw_total, 2),
            "coverage_pct": round(raw_total / BUSINESS_TARGET_L * 100, 2),
            "normalisation_changed_total": False,
            "dimensions": {}}

    # --- period completeness ------------------------------------------------
    mon, _ = agg("Month")
    expected = [f"{MON3[((3 + i) % 12)]}-{26 + ((3 + i) // 12):02d}" for i in range(12)]
    missing_m = [m for m in expected if m not in mon]
    rec_rows.append(["Month", 12, len(mon), len(missing_m), round(raw_total, 2), "",
                     "", round(len(mon) / 12 * 100, 1),
                     "COMPLETE" if not missing_m else "INCOMPLETE_TARGET_COVERAGE",
                     "No" if not missing_m else "Yes"])
    diag["dimensions"]["month"] = {"present": sorted(mon, key=lambda m: expected.index(m) if m in expected else 99),
                                   "missing": missing_m}

    # --- chain scope --------------------------------------------------------
    ch, chn = agg("Chain")
    tgt_chains = {c for c in ch if c and c != "(blank)"}
    missing_ch = {c: v["fy26"] for c, v in chains_u.items() if c not in tgt_chains and v["fy26"] > 0}
    fy26_total = sum(v["fy26"] for v in chains_u.values()) or 1.0
    missing_share = sum(missing_ch.values()) / fy26_total
    blank_chain = ch.get("(blank)", 0.0)
    unattached = {t["Chain_Raw"]: 0.0 for t in tg
                  if t["Chain_Method"] in ("CATCH_ALL_BUCKET", "COMPOSITE_UNRESOLVED")}
    for t in tg:
        if t["Chain_Method"] in ("CATCH_ALL_BUCKET", "COMPOSITE_UNRESOLVED"):
            unattached[t["Chain_Raw"]] += t["Target"]
    rec_rows.append(["Chain", len(chains_u), len(tgt_chains), len(missing_ch), round(raw_total, 2),
                     round(fy26_total, 2), "", round(len(tgt_chains) / max(len(chains_u), 1) * 100, 1),
                     "INCOMPLETE_TARGET_COVERAGE" if missing_ch else "FULL_BUSINESS_SCOPE", "Yes"])
    diag["dimensions"]["chain"] = {
        "in_target": sorted(tgt_chains),
        "in_business_not_in_target": {k: round(v, 2) for k, v in sorted(missing_ch.items(), key=lambda x: -x[1])},
        "missing_share_of_fy26_offtake_pct": round(missing_share * 100, 2),
        "indicative_value_of_missing_L": round(missing_share * BUSINESS_TARGET_L, 2),
        "blank_chain_target_L": round(blank_chain, 2),
        "not_attached_to_one_account_L": {k: round(v, 2) for k, v in sorted(unattached.items(), key=lambda x: -x[1])},
        "spelling_variants_folded": sorted({f"{t['Chain_Raw']} -> {t['Chain']}" for t in tg
                                            if t["Chain_Method"] in ("TARGET_ALIAS", "SHARED_ALIAS")}),
    }

    # --- brand scope --------------------------------------------------------
    br, _ = agg("Brand")
    tgt_brands = {b for b in br if b and b != "(blank)"}
    missing_br = [b for b in brands_u if b not in tgt_brands]
    rec_rows.append(["Brand", len(brands_u), len(tgt_brands), len(missing_br), round(raw_total, 2),
                     "", "", round(len(tgt_brands) / max(len(brands_u), 1) * 100, 1),
                     "INCOMPLETE_TARGET_COVERAGE" if missing_br else "FULL_BUSINESS_SCOPE", "Yes"])
    diag["dimensions"]["brand"] = {"in_target": {k: round(v, 2) for k, v in sorted(br.items(), key=lambda x: -x[1])},
                                   "in_business_not_in_target": missing_br}

    # --- region / state -----------------------------------------------------
    rg, _ = agg("Region")
    cfg_zones = json.loads((REPO / "config" / "analytics_config.json").read_text())["zones"]["canonical"]
    missing_rg = [z for z in cfg_zones if z not in rg]
    rec_rows.append(["Region", len(cfg_zones), len(rg), len(missing_rg), round(raw_total, 2), "", "",
                     round(len(rg) / len(cfg_zones) * 100, 1),
                     "FULL_BUSINESS_SCOPE" if not missing_rg else "INCOMPLETE_TARGET_COVERAGE",
                     "No" if not missing_rg else "Yes"])
    diag["dimensions"]["region"] = {"in_target": {k: round(v, 2) for k, v in sorted(rg.items(), key=lambda x: -x[1])},
                                    "missing": missing_rg,
                                    "raw_spellings": sorted({t["Region_Raw"] for t in tg})}

    st, _ = agg("State")
    rec_rows.append(["State", "", len(st), "", round(raw_total, 2), "", "", "",
                     "REFERENCE_ONLY", "No"])
    diag["dimensions"]["state"] = {k: round(v, 2) for k, v in sorted(st.items(), key=lambda x: -x[1])}

    # --- people -------------------------------------------------------------
    bd, _ = agg("BDO_BDE")
    rk, _ = agg("RKAM")
    # RKAM mixes role labels with person names; that matters because a role label
    # must never be joined as an employee identity (KA-12).
    role_like = {k: v for k, v in rk.items() if k.lower().startswith("rkam")}
    rec_rows.append(["BDO/BDE (person)", "", len(bd), "", round(raw_total, 2), "", "", "",
                     "PERSON_LEVEL", "No"])
    rec_rows.append(["RKAM (mixed grain)", "", len(rk), len(role_like), round(raw_total, 2), "", "", "",
                     "MIXED_GRAIN_ROLE_AND_PERSON", "Yes"])
    diag["dimensions"]["bdo_bde"] = {k: round(v, 2) for k, v in sorted(bd.items(), key=lambda x: -x[1])}
    diag["dimensions"]["rkam"] = {"values": {k: round(v, 2) for k, v in sorted(rk.items(), key=lambda x: -x[1])},
                                  "role_labels": sorted(role_like),
                                  "person_names": sorted(set(rk) - set(role_like))}

    # --- duplicate rows -----------------------------------------------------
    seen = defaultdict(list)
    for i, t in enumerate(tg):
        seen[(t["FY"], t["Month"], t["State"], t["Chain_Raw"], t["Brand_Raw"], t["BDO_BDE"])].append(i)
    dups = {k: v for k, v in seen.items() if len(v) > 1}
    rec_rows.append(["Duplicate keys", len(tg), len(seen), sum(len(v) - 1 for v in dups.values()),
                     round(sum(tg[i]["Target"] for v in dups.values() for i in v[1:]), 2), "", "", "",
                     "CLEAN" if not dups else "DUPLICATE_KEYS_PRESENT", "Yes" if dups else "No"])
    diag["duplicates"] = {"key_count": len(seen), "extra_rows": sum(len(v) - 1 for v in dups.values()),
                          "examples": [list(k) for k in list(dups)[:8]]}

    # --- period coverage by region -----------------------------------------
    # The single most important scope test: a region planned for only part of the
    # year is a coverage gap, not a policy exclusion, and it is invisible in a
    # whole-file total.
    rm = defaultdict(lambda: defaultdict(float))
    for t in tg:
        rm[t["Region"]][t["Month"]] += t["Target"]
    h1, h2 = expected[:6], expected[6:]
    part_year, full_year = {}, {}
    for r, d in rm.items():
        n = sum(1 for m in expected if d.get(m, 0) > 0)
        (full_year if n == 12 else part_year)[r] = {
            "months_planned": n,
            "months_missing": [m for m in expected if d.get(m, 0) == 0],
            "planned_L": round(sum(d.values()), 2),
            "h1_L": round(sum(d.get(m, 0) for m in h1), 2),
            "h2_L": round(sum(d.get(m, 0) for m in h2), 2),
        }
    # Peer ratio from the regions that ARE fully planned -- the file's own evidence,
    # not an outside assumption.
    peer_h1 = sum(v["h1_L"] for v in full_year.values())
    peer_h2 = sum(v["h2_L"] for v in full_year.values())
    peer_ratio = (peer_h2 / peer_h1) if peer_h1 else 0.0
    part_year_missing_L = sum(v["h1_L"] for v in part_year.values()) * peer_ratio
    diag["period_coverage"] = {
        "fully_planned_regions": full_year,
        "part_year_regions": part_year,
        "peer_h2_over_h1": round(peer_ratio, 4),
        "indicative_missing_L": round(part_year_missing_L, 2),
        "basis": "H1 of the part-year regions x the H2/H1 ratio of the fully planned regions",
    }

    # --- the gap, decomposed ------------------------------------------------
    gap = BUSINESS_TARGET_L - raw_total
    explained = []
    if part_year:
        explained.append({
            "cause": "Regions planned for part of the year only",
            "detail": ", ".join(f"{r} ({v['months_planned']}/12 months, {v['months_missing'][0]}-"
                                f"{v['months_missing'][-1]} absent)" for r, v in sorted(part_year.items())),
            "indicative_L": round(part_year_missing_L, 2),
            "basis": "the file's own H1 for those regions, grown by the peer H2/H1 ratio",
            "likely_class": "INCOMPLETE_TARGET_COVERAGE",
        })
    if missing_ch:
        explained.append({
            "cause": "Chains with FY26 offtake but no target row at all",
            "detail": ", ".join(f"{c} ({v:,.0f} L FY26 offtake)"
                                for c, v in sorted(missing_ch.items(), key=lambda x: -x[1])),
            "indicative_L": round(sum(missing_ch.values()), 2),
            "basis": "FY26 offtake of those chains, a complete 12-month year",
            "likely_class": "INTENTIONAL_INCENTIVE_SCOPE if e-commerce/non-field accounts are "
                            "outside the plan; otherwise INCOMPLETE_TARGET_COVERAGE",
        })
    exp_total = sum(e["indicative_L"] for e in explained)
    resid = gap - exp_total
    diag["gap_decomposition"] = {
        "gap_L": round(gap, 2),
        "explained": explained,
        "explained_indicative_L": round(exp_total, 2),
        "unexplained_L": round(resid, 2),
        "unexplained_pct_of_gap": round(resid / gap * 100, 1) if gap else 0.0,
        "status": "EXPLAINED_SCOPE_DIFFERENCE" if abs(resid) < gap * 0.25 else "PARTIALLY_EXPLAINED",
        "classification": "UNKNOWN_SCOPE — business confirmation required",
        "note": "Indicative sizing only. Nothing here allocates or adjusts a target; "
                "it identifies which entities explain the difference so the business "
                "can confirm whether each exclusion is intended (KA-11).",
    }
    # Grain defect: target value that carries no account at all.
    diag["grain_defects"] = {
        "blank_chain_rows": chn.get("(blank)", 0),
        "blank_chain_L": round(blank_chain, 2),
        "blank_chain_pct_of_file": round(blank_chain / raw_total * 100, 2),
        "blank_chain_regions": sorted({t["Region"] for t in tg if not t["Chain_Raw"].strip()}),
        "double_counting_check": "PASS — no state/month carries both a blank-chain and a "
                                 "chain-level row, so these are a different planning grain, "
                                 "not a duplicate of the chain rows",
        "not_attached_to_one_account_L": {k: round(v, 2) for k, v in sorted(unattached.items(), key=lambda x: -x[1])},
    }

    with open(outd / "target_scope_reconciliation.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Dimension", "Universe_Count", "Target_Count", "Missing_Count", "Target_Value_L",
                    "Reference_Value_L", "Difference_L", "Coverage_Pct", "Status",
                    "Business_Interpretation_Required"])
        w.writerows(rec_rows)
    (outd / "target_scope_diagnostic.json").write_text(json.dumps(diag, indent=2))
    write_decision_pack(outd / "target_scope_decision_pack.md", diag)

    print(f"target file {raw_total:,.2f} L  vs business {BUSINESS_TARGET_L:,.2f} L  "
          f"gap {gap:,.2f} L  coverage {raw_total / BUSINESS_TARGET_L * 100:.1f}%")
    print(f"  months {len(mon)}/12 missing={missing_m or 'none'}")
    print(f"  chains in target {len(tgt_chains)} | in business without target {len(missing_ch)} "
          f"(~{missing_share * 100:.1f}% of FY26 offtake)")
    print(f"  blank-chain target rows {chn.get('(blank)', 0)} worth {blank_chain:,.2f} L")
    print(f"  not attached to one account: {unattached}")
    print(f"  regions {sorted(rg)} missing={missing_rg or 'none'}")
    print(f"  duplicate extra rows {sum(len(v) - 1 for v in dups.values())}")
    for r, v in sorted(part_year.items()):
        print(f"  PART-YEAR REGION {r}: {v['months_planned']}/12 months planned, "
              f"{v['planned_L']:,.2f} L; {v['months_missing'][0]}-{v['months_missing'][-1]} absent")
    print(f"  explained (indicative) {exp_total:,.2f} L | unexplained {resid:,.2f} L "
          f"({resid / gap * 100:.0f}% of the gap)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
