"""Turn one new monthly offtake file into rows for the Excel dashboard (sheet Offtake_Data).

  python scripts/offtake_month_to_rows.py Sep_26            # reads offtake_store_article_Sep_26.csv from the Offtake_Monthly watch folder
  python scripts/offtake_month_to_rows.py Sep_26 --out exports/Sep_26_rows.csv

Same rules as the web dashboard: Brand Counter stores left out, chain names standardised (scripts/visit_cities.py), NSV in Rs lakh.
Paste the CSV rows under the last row of Offtake_Data (columns A to I), then recalculate.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_offtake_excel as be  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("month", help="file suffix as in offtake_store_article_<Mon>_<yy>.csv, e.g. Sep_26")
    ap.add_argument("--out")
    a = ap.parse_args()
    mon, yy = a.month.split("_")
    rows = be.load_cy([mon], year=yy)
    rows["NSV"] = rows["NSV"].round(6)
    out = Path(a.out) if a.out else ROOT / "exports" / f"{a.month}_rows.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    rows.rename(columns={"NSV": "NSV (₹ L)"}).to_csv(out, index=False, date_format="%d-%b-%Y")
    print(f"wrote {out}: {len(rows)} rows, NSV {rows['NSV'].sum():.2f} L ({mon}'{yy}, Brand Counter excluded)")


if __name__ == "__main__":
    main()
