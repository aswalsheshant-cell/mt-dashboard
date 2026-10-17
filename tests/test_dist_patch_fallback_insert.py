"""Owner-approved Sep'26 split patch must reach the allocator on the fallback
path (no base cont workbook in --src), insert-only, history untouched."""
import importlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
bd = importlib.import_module("build_dashboard_data")


def _fallback_frame():
    return pd.DataFrame({
        "_st": ["alpha"], "_bl": ["mamaearth"], "_pm": ["2026-05"],
        "_AllocChainRaw": ["DMart"], "_frac": [1.0],
        "_ShipToRaw": ["Alpha"], "_BrandRaw": ["Mamaearth"]})


def test_patch_inserts_new_key_and_never_replaces_covered_key(tmp_path, monkeypatch):
    patch = pd.DataFrame([
        # new key (Sep'26): 75/25 split -> must be inserted
        {"Ship To Name": "Beta", "Chain Name": "Lulu", "Brand": "Mamaearth",
         "Month": "2026-09-01", "Secondary contribution %": 75.0},
        {"Ship To Name": "Beta", "Chain Name": "D-Mart", "Brand": "Mamaearth",
         "Month": "2026-09-01", "Secondary contribution %": 25.0},
        # key the fallback already covers -> must be ignored
        {"Ship To Name": "Alpha", "Chain Name": "Apollo", "Brand": "Mamaearth",
         "Month": "2026-05-01", "Secondary contribution %": 100.0},
        # uncovered key but INSIDE fallback coverage (older month) -> ignored
        {"Ship To Name": "Gamma", "Chain Name": "Apollo", "Brand": "Mamaearth",
         "Month": "2026-03-01", "Secondary contribution %": 100.0},
    ])
    monkeypatch.setattr(bd, "_load_dist_cont_patch_rows", lambda: patch)
    monkeypatch.setattr(bd, "load_shipto_primary_weights",
                        lambda: (_fallback_frame(), {("alpha", "mamaearth", "2026-05"): 100.0}))
    wdf, raw_sums, label = bd.load_dist_cont_weights(tmp_path)
    assert label == "shipto_primary_csv"
    beta = wdf[wdf["_st"] == "beta"].set_index("_AllocChainRaw")["_frac"]
    assert beta.to_dict() == {"Lulu": 0.75, "D-Mart": 0.25}
    alpha = wdf[wdf["_st"] == "alpha"]
    assert list(alpha["_AllocChainRaw"]) == ["DMart"]       # history unchanged
    assert "gamma" not in set(wdf["_st"])
    assert raw_sums[("beta", "mamaearth", "2026-09")] == 100.0
