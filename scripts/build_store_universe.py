#!/usr/bin/env python3
"""Write dashboard/store_universe.js from PowerBI/SeedData/Masters/Store_Universe_Overrides.csv.

The MT dashboard counts POS stores per chain from the store x article offtake (data.js offtake.pos_stores). Chains whose offtake has
no store codes are handled here, once, for every tab and for Power BI:
  TENTATIVE  a working estimate (Reliance Retail about 1,000, More Retail about 400): shown with a ~ and counted in the total
  NA         not applicable (Nykaa / FSN is online): shown as NA, not counted
data.js is not touched.

    python scripts/build_store_universe.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "PowerBI" / "SeedData" / "Masters" / "Store_Universe_Overrides.csv"
OUT = ROOT / "dashboard" / "store_universe.js"
MASTER = ROOT / "PowerBI" / "SeedData" / "Masters" / "Store_City_Master.csv"
STATUSES = {"TENTATIVE", "NA"}
import visit_cities as vc


def _norm(s):
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def master_counts(path=MASTER):
    """Stores per standard chain in the maintained store master (chain-level pseudo keys left out; Reliance Brand Counter kept apart)."""
    if not Path(path).exists():
        return None
    with Path(path).open(encoding="utf-8", newline="") as h:
        rows = [r for r in csv.DictReader(h) if "|NO-CITY" not in r["Store Key"]]
    by = {}
    for r in rows:
        by[r["Chain Name"]] = by.get(r["Chain Name"], 0) + 1
    total = sum(v for k, v in by.items() if k != "Reliance Brand Counter")
    return {"total": total, "by_chain": by}


def build(src=SRC):
    with Path(src).open(encoding="utf-8", newline="") as h:
        rows = list(csv.DictReader(h))
    overrides = {}
    for r in rows:
        status = r["Status"].strip().upper()
        if status not in STATUSES:
            raise ValueError(f"{r['Chain']}: status must be one of {sorted(STATUSES)}, got {status!r}")
        count = r["Store Count"].strip()
        if status == "TENTATIVE" and not count:
            raise ValueError(f"{r['Chain']}: a tentative override needs a store count")
        overrides[r["Chain"].strip()] = {"count": int(count) if count else None, "status": status, "note": r["Note"].strip(),
                                         "source": r["Source"].strip(), "as_of": r["As Of"].strip()}
    mc = master_counts()
    out = {"overrides": overrides}
    if mc:
        out["master"] = {"total": mc["total"], "by_chain": mc["by_chain"], "alias": vc.CHAIN_LOOKUP,
                         "note": "Stores in the maintained store master (Jan-Jun 26 store list plus stores added from the offtake files); Reliance Brand Counter staffed counters not included. alias maps a chain spelling (letters and digits only, lower case) to the standard chain name."}
    return out


def main():
    data = build()
    OUT.write_text("window.STORE_UNIVERSE=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
    print("wrote", OUT, f"({len(data['overrides'])} chains)")


if __name__ == "__main__":
    main()
