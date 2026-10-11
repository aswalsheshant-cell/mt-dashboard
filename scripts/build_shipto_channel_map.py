"""Build PowerBI/SeedData/Masters/ShipToChannelMap.csv (Ship To Name -> Channel).

Primary_ShipTo files have no Channel column, but Primary Article does, and a ship-to
name sits in exactly one channel there. This writes that lookup so 15_Fact_PrimaryShipTo.pq
can apply the same pPrimaryChannel scope as Primary Article.

Only names and channel labels are written, no values. A ship-to name that appears in the
ShipTo files but not in Primary Article is listed in the console output and left out of the
map; the query then labels those rows UNMAPPED instead of guessing.

Usage: python scripts/build_shipto_channel_map.py
"""

import csv
import glob
import sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "PowerBI" / "RawDataFolders"
OUT = ROOT / "PowerBI" / "SeedData" / "Masters" / "ShipToChannelMap.csv"


def norm(s):
    return " ".join((s or "").lower().split())


def main():
    by_name = defaultdict(Counter)
    for f in sorted(glob.glob(str(RAW / "Primary_Article_Monthly" / "primary_article_*.csv"))):
        with open(f, newline="", encoding="utf-8-sig") as fh:
            r = csv.DictReader(fh)
            r.fieldnames = [" ".join(x.split()) for x in r.fieldnames or []]
            for x in r:
                by_name[norm(x["Ship To Name"])][(x["Channel"] or "").strip().upper()] += 1
    conflicts = [n for n, c in by_name.items() if len(c) > 1]
    if conflicts:
        sys.exit("Ship-to names in more than one channel: %s" % conflicts[:5])

    names, missing = {}, set()
    for f in sorted(glob.glob(str(RAW / "Primary_ShipTo_Monthly" / "Primary_ShipTo_*.csv"))):
        with open(f, newline="", encoding="utf-8-sig") as fh:
            for x in csv.DictReader(fh):
                n = (x["Ship To Name"] or "").strip()
                key = norm(n)
                hit = by_name.get(key) or by_name.get(key.removesuffix("_shipto").strip())
                if hit:
                    names[n] = next(iter(hit))
                else:
                    missing.add(n)
    rows = sorted(names.items(), key=lambda t: t[0].lower())
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Ship To Name", "Channel", "Source"])
        for n, ch in rows:
            w.writerow([n, ch, "Primary_Article_Monthly (Ship To Name -> Channel)"])
    print("wrote %d ship-to names; channels %s; not in Primary Article: %d" % (
        len(rows), dict(Counter(c for _, c in rows)), len(missing)))
    for n in sorted(missing)[:10]:
        print("  unmapped:", n)


if __name__ == "__main__":
    main()
