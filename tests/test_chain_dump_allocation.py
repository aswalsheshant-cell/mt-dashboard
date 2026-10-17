"""Distributor primary is split to chains with the business's chain-wise primary dump.

Found 2026-10-17: FY27 chain primary on the dashboard did not match the MT Channel
Analyst Lead's MoM chain-wise primary (an Excel pivot of ChainWisePrimarySale_Dump_Snapshot.csv).
Direct-billed chains tied to the paisa; every gap sat in the distributor-billed split
(~Rs 7,225 L of Apr-Aug'26). Root cause: with Dist_primary_cont_based_on_secondary_MOM.xlsx
absent, allocate_dist_primary() fell back to Primary_ShipTo_FY25-26_to_May26.csv, a
different split from the dump (Rs 473.67 L across chains, Apr-Aug'26). The B2 weights built
from the dump (PR #303) only fed the legacy primary block, not fyx_primary.

load_chain_dump_weights() now supplies the weights. These tests pin its behaviour and
that, on the repo's real Apr-Aug'26 files, the chain totals tie to the dump.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as B  # noqa: E402

DUMP = ROOT / "PowerBI" / "SeedData" / "Mapping" / "ChainWisePrimarySale_Dump_Snapshot.csv"
ALIASES = ROOT / "PowerBI" / "SeedData" / "Mapping" / "ShipTo_Family_Aliases.csv"
ARTICLES = ROOT / "PowerBI" / "RawDataFolders" / "Primary_Article_Monthly"
FY27_MONTHS = [("Apr", "2026-04"), ("May", "2026-05"), ("Jun", "2026-06"), ("Jul", "2026-07"), ("Aug", "2026-08")]


def _mini_repo(tmp_path, dump_rows, alias_rows=None):
    m = tmp_path / "PowerBI" / "SeedData" / "Mapping"
    m.mkdir(parents=True)
    pd.DataFrame(dump_rows, columns=["Month", "Bill to customer", "Brand", "Chain Name", "NSV"]).to_csv(
        m / "ChainWisePrimarySale_Dump_Snapshot.csv", index=False)
    if alias_rows:
        pd.DataFrame(alias_rows, columns=["Family", "Ship_To_Name", "Basis", "Status"]).to_csv(
            m / "ShipTo_Family_Aliases.csv", index=False)
    return tmp_path


def test_missing_dump_returns_none(tmp_path):
    assert B.load_chain_dump_weights(repo_root=tmp_path) == (None, None)


def test_fractions_sum_to_one_per_key_and_follow_the_dump(tmp_path):
    root = _mini_repo(tmp_path, [
        ["April'26", "Kiran Trading", "Mamaearth", "D-Mart", 60.0],
        ["April'26", "Kiran Trading", "Mamaearth", "Apollo Healthco", 40.0],
    ])
    w, rs = B.load_chain_dump_weights(repo_root=root)
    w = w[w._pm == "2026-04"]
    got = dict(zip(w["_AllocChainRaw"], w["_frac"]))
    assert got == pytest.approx({"D-Mart": 0.6, "Apollo Healthco": 0.4})
    assert set(rs.values()) == {100.0}


def test_naming_variants_of_one_distributor_share_one_mix(tmp_path):
    """The dump books it under one name or both; article files use the other."""
    root = _mini_repo(tmp_path, [
        ["April'26", "Az Enterprises", "Mamaearth", "Apollo Healthco", 30.0],
        ["April'26", "Az Enterprises(Apollo/More)Mt", "Mamaearth", "More Retail", 10.0],
    ], [["AZ", "Az Enterprises", "", ""], ["AZ", "Az Enterprises(Apollo/More)Mt", "", ""]])
    w, _ = B.load_chain_dump_weights(repo_root=root)
    for name in ("az enterprises", "az enterprises(apollo/more)mt"):
        mix = w[(w._st == name) & (w._bl == "mamaearth")].set_index("_AllocChainRaw")["_frac"].to_dict()
        assert mix == pytest.approx({"Apollo Healthco": 0.75, "More Retail": 0.25})


def test_every_brand_spelling_the_allocator_may_meet_is_covered(tmp_path):
    """Article files say 'The Derma Co.' (dot); the dump says 'The Derma Co'."""
    root = _mini_repo(tmp_path, [["April'26", "Kiran Trading", "The Derma Co", "D-Mart", 5.0]])
    w, _ = B.load_chain_dump_weights(repo_root=root)
    assert {"the derma co", "the derma co."} <= set(w._bl)


def test_offsetting_returns_do_not_create_wild_fractions(tmp_path):
    root = _mini_repo(tmp_path, [
        ["April'26", "Kiran Trading", "BBlunt", "D-Mart", 10.0],
        ["April'26", "Kiran Trading", "BBlunt", "Apollo Healthco", -9.0],
    ])
    w, rs = B.load_chain_dump_weights(repo_root=root)
    assert (w._frac >= 0).all() and (w._frac <= 1).all()
    assert w._frac.sum() == pytest.approx(1.0)


def test_unparseable_months_are_dropped_not_guessed(tmp_path):
    root = _mini_repo(tmp_path, [["not a month", "Kiran Trading", "Mamaearth", "D-Mart", 1.0],
                                 ["April'26", "Kiran Trading", "Mamaearth", "D-Mart", 1.0]])
    w, _ = B.load_chain_dump_weights(repo_root=root)
    assert set(w._pm) == {"2026-04"}


def test_dump_is_tried_before_the_shipto_csv_and_workbook_still_wins(tmp_path, monkeypatch):
    dump, shipto = object(), object()
    monkeypatch.setattr(B, "_load_dist_cont_patch_rows", lambda: None)
    monkeypatch.setattr(B, "load_chain_dump_weights", lambda *a, **k: (dump, {"k": 1}))
    monkeypatch.setattr(B, "load_shipto_primary_weights", lambda: (shipto, {"k": 2}))
    wdf, _, label = B.load_dist_cont_weights(tmp_path)          # no workbook in tmp_path
    assert wdf is dump and label == "chain_wise_primary_dump"
    monkeypatch.setattr(B, "load_chain_dump_weights", lambda *a, **k: (None, None))
    wdf, _, label = B.load_dist_cont_weights(tmp_path)          # dump absent: old fallback
    assert wdf is shipto and label == "shipto_primary_csv"


def test_alias_file_is_marked_proposed_for_owner_confirmation():
    a = pd.read_csv(ALIASES)
    assert list(a.columns) == ["Family", "Ship_To_Name", "Basis", "Status"]
    assert a["Status"].str.startswith("PROPOSED_NAMING_VARIANT").all()


@pytest.mark.skipif(not (DUMP.exists() and ARTICLES.exists()), reason="repo seed CSVs not present")
def test_fy27_apr_aug_chain_totals_tie_to_the_dump_on_real_files():
    """Chain totals (non-SIS) from article-wise primary + the new weights equal the dump's."""
    nk = B._norm_shipto
    fr = []
    for mon, pm in FY27_MONTHS:
        d = pd.read_csv(ARTICLES / f"primary_article_{mon}_26.csv", low_memory=False)
        d.columns = [" ".join(str(c).split()) for c in d.columns]
        cc = "Chain name for Dashboard" if "Chain name for Dashboard" in d.columns else "Chain name"
        fr.append(pd.DataFrame({
            "pm": pm, "st": d["Ship To Name"].map(nk), "brand": d["brand"].astype(str).str.strip().str.lower(),
            "nsv": pd.to_numeric(d["Inv. Net value(LOC)"], errors="coerce").fillna(0) / 1e5,
            "chan": d["Channel"].astype(str).str.strip().str.upper(),
            "dist": d["PO Type"].astype(str).str.strip().str.lower().str.startswith("dist"),
            "chain": d[cc].astype(str).str.strip().map(B.canon_chain)}))
    p = pd.concat(fr, ignore_index=True)
    sis_chains = set(p[p.chan == "SIS"].chain)
    p = p[p.chan != "SIS"]

    w, _ = B.load_chain_dump_weights()
    dist = p[p.dist].merge(
        w.rename(columns={"_st": "st", "_bl": "brand", "_pm": "pm"})[["st", "brand", "pm", "_AllocChainRaw", "_frac"]],
        on=["st", "brand", "pm"], how="left")
    unmatched = dist[dist._frac.isna()]["nsv"].sum()
    assert unmatched / p[p.dist].nsv.sum() < 0.002, f"{unmatched:.2f} L of distributor primary has no dump key"
    dist = dist[dist._frac.notna()]
    dist["chain"] = dist["_AllocChainRaw"].map(B.canon_chain)
    dist["nsv"] = dist["nsv"] * dist["_frac"]
    ours = pd.concat([p[~p.dist][["pm", "chain", "nsv"]], dist[["pm", "chain", "nsv"]]])
    ours = ours[~ours.chain.isin(sis_chains)].groupby(["pm", "chain"]).nsv.sum()

    d = pd.read_csv(DUMP).dropna(subset=["Month", "NSV"])
    d["pm"] = d["Month"].map(B._month_period)
    d = d[d.pm.isin([pm for _, pm in FY27_MONTHS])]
    d["chain"] = d["Chain Name"].map(B.canon_chain)
    truth = d[~d.chain.isin(sis_chains)].groupby(["pm", "chain"]).NSV.sum()

    diff = ours.sub(truth, fill_value=0.0)
    assert diff.abs().sum() < 3.0, f"chain-month differences sum to {diff.abs().sum():.2f} L"
    by_chain = diff.groupby(level="chain").sum()
    assert by_chain.abs().max() < 1.5, by_chain.abs().sort_values().tail(3).to_dict()


# ---- Power BI side: Query 41 must use the same source and rules (static, not run in Desktop) ----
PQ41 = ROOT / "PowerBI" / "PowerQuery" / "41_DistContWeights.pq"


def test_power_query_41_reads_the_dump_and_the_alias_file_not_the_shipto_csv():
    code = [ln for ln in PQ41.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("//")]
    text = "\n".join(code)
    assert "ChainWisePrimarySale_Dump_Snapshot.csv" in text
    assert "ShipTo_Family_Aliases.csv" in text
    assert "Primary_ShipTo_FY25-26_to_May26.csv" not in text, "Query 41 must not read the old fallback CSV"
    assert ".xlsx" not in text
    assert "Jun26Start" not in text, "the Jun'26-only rule was replaced by the generic 3-month carry-forward"
    # same rules as load_chain_dump_weights(): offsetting threshold, 3-month window, failing loudly
    assert "0.5 * [AbsSum]" in text
    assert "CarryRows(1), CarryRows(2), CarryRows(3)" in text
    import re
    picked = re.search(r"DumpPicked = Table\.SelectColumns\(.*?\}\)", text, re.S).group(0)
    assert "UseNull" not in picked, "the dump must fail the refresh when a column is missing, not blank rows out"
