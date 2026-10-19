#!/usr/bin/env python3
"""Check chain primary in a dashboard against the MT Channel Analyst Lead's MoM chain-wise primary.

The control is PowerBI/SeedData/Mapping/Chain_Primary_MoM_Control_Apr25_Sep26.csv: the owner's
Excel pivot (Direct/Dist. x Channel x Chain x Month, INR Lakh, all channels incl. SIS), supplied
2026-10-17. This script says whether a dashboard shows the same chain numbers.

  HTML dashboard   python scripts/reconcile_chain_primary_to_control.py
      Compares dashboard/data.js detail_meta.fyx_primary FY27 by_chain (all channels) with the
      control, summed over the months data.js covers.

  Power BI         python scripts/reconcile_chain_primary_to_control.py --pbi-csv export.csv
      In Power BI: a matrix with Chain on rows, MonthStart on columns, [Total Primary NSV] as
      the value -> ... ▸ Export data ▸ CSV. Primary NSV in Power BI is in rupees, so the default
      --scale is 100000 (rupees -> lakh). Compares every chain x month.

Chain names go through canon_chain() on both sides. Exit 0 = every chain within --tol (INR Lakh),
exit 1 = at least one chain is off. Read-only.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_dashboard_data as B  # noqa: E402

CONTROL = ROOT / "PowerBI" / "SeedData" / "Mapping" / "Chain_Primary_MoM_Control_Apr25_Sep26.csv"
MON3 = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9,
        "Oct": 10, "Nov": 11, "Dec": 12}


def month_key(v):
    """'YYYY-MM' from 2026-04-01, Apr-26, April'26, 01-Apr-26 or 'Apr 2026'."""
    t = str(v).strip()
    if len(t) >= 7 and t[:4].isdigit() and t[4] == "-" and t[5:7].isdigit():
        return t[:7]
    pm = B._month_period(t.replace("-", "'", 1) if t[:3].isalpha() and "'" not in t else t)
    if pm:
        return pm
    parts = t.replace("/", "-").split("-")           # 01-Apr-26
    if len(parts) == 3 and parts[1][:3].title() in MON3:
        y = int(parts[2]) + (2000 if int(parts[2]) < 100 else 0)
        return "%04d-%02d" % (y, MON3[parts[1][:3].title()])
    return None


def load_control():
    out = {}
    with open(CONTROL, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            k = (B.canon_chain(r["Chain Name"]), r["MonthStart"][:7])
            out[k] = out.get(k, 0.0) + float(r["NSV_Lakh"])
    return out


def load_datajs(path):
    s = Path(path).read_text(encoding="utf-8")
    d = json.loads(s[s.index("{"): s.rindex("}") + 1])
    fx = ((d.get("detail_meta") or {}).get("fyx_primary") or {}).get("FY27")
    if not fx:
        raise SystemExit("data.js has no detail_meta.fyx_primary.FY27")
    months = []
    for lab in fx["months_canon"]:                   # 'Apr-26'
        mon, yy = lab.split("-")
        months.append("%04d-%02d" % (2000 + int(yy), MON3[mon]))
    chains = {}
    for c in fx["by_chain"]:
        k = B.canon_chain(c["name"])
        chains[k] = chains.get(k, 0.0) + float(c["nsv"])
    return months, chains


def load_pbi(path, chain_col, month_col, value_col, scale):
    out = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        for col in (chain_col, month_col, value_col):
            if col not in (rd.fieldnames or []):
                raise SystemExit("column %r not in the export; it has %s" % (col, rd.fieldnames))
        for r in rd:
            m = month_key(r[month_col])
            v = str(r[value_col]).replace(",", "").strip()
            if m is None or not v:
                continue
            k = (B.canon_chain(r[chain_col]), m)
            out[k] = out.get(k, 0.0) + float(v) / scale
    return out


def report(rows, tol, label):
    rows = sorted(rows, key=lambda r: -abs(r[3]))
    bad = [r for r in rows if abs(r[3]) > tol]
    print("%-22s %12s %12s %10s" % (label, "dashboard", "control", "diff"))
    for name, a, c, diff in rows[:15]:                      # largest differences first
        print("%-22s %12.2f %12.2f %+10.2f%s" % (name, a, c, diff, "   <-- off" if abs(diff) > tol else ""))
    tot = sum(abs(r[3]) for r in rows)
    print("\nchains/cells compared: %d | off by more than %.2f L: %d | sum of |diff|: %.2f L" % (len(rows), tol, len(bad), tot))
    print("VERDICT: %s" % ("PASS" if not bad else "FAIL"))
    return 0 if not bad else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--datajs", default=str(ROOT / "dashboard" / "data.js"))
    ap.add_argument("--pbi-csv", help="Power BI matrix export (chain x month)")
    ap.add_argument("--chain-col", default="Chain")
    ap.add_argument("--month-col", default="MonthStart")
    ap.add_argument("--value-col", default="Primary NSV")
    ap.add_argument("--scale", type=float, default=100000.0, help="divide Power BI values by this to get lakh (default 100000, rupees)")
    ap.add_argument("--tol", type=float, default=0.5, help="allowed difference per chain, INR Lakh")
    a = ap.parse_args()
    ctl = load_control()
    if a.pbi_csv:
        pbi = load_pbi(a.pbi_csv, a.chain_col, a.month_col, a.value_col, a.scale)
        months = sorted({m for (_, m) in pbi})
        keys = {k for k in set(ctl) | set(pbi) if k[1] in months}
        rows = [("%s %s" % k, pbi.get(k, 0.0), ctl.get(k, 0.0), pbi.get(k, 0.0) - ctl.get(k, 0.0)) for k in keys]
        print("Power BI export vs control, months %s..%s\n" % (months[0], months[-1]))
        return report(rows, a.tol, "chain month")
    months, chains = load_datajs(a.datajs)
    covered = [m for m in months if any(k[1] == m for k in ctl)]
    ctl_tot = {}
    for (c, m), v in ctl.items():
        if m in covered:
            ctl_tot[c] = ctl_tot.get(c, 0.0) + v
    keys = set(ctl_tot) | set(chains)
    rows = [(c, chains.get(c, 0.0), ctl_tot.get(c, 0.0), chains.get(c, 0.0) - ctl_tot.get(c, 0.0)) for c in keys]
    print("data.js FY27 by_chain vs control, months %s..%s (all channels)\n" % (covered[0], covered[-1]))
    return report(rows, a.tol, "chain")


if __name__ == "__main__":
    sys.exit(main())
