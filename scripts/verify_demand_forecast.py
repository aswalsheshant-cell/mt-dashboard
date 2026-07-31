#!/usr/bin/env python3
"""
Validate the Demand Forecast / S&OP workbook: evaluate every formula with the
`formulas` engine (pip install formulas) and assert there are no Excel error
values (#REF!, #NAME?, #DIV/0!, …). Also prints a few headline numbers so a
reviewer can sanity-check the model without opening Excel.

Usage:
    python scripts/verify_demand_forecast.py [path-to-xlsx]

Exit code is non-zero if any formula evaluates to an error.
(LibreOffice's recalc path does not work in the CCR sandbox — its import filter
cannot load files — so we verify with `formulas` instead.)
"""
import sys, warnings
warnings.filterwarnings("ignore")

DEFAULT = "DemandForecast/MT_Demand_Forecast_SOP_Model.xlsx"
ERRS = ("#REF!", "#NAME?", "#DIV/0!", "#VALUE!", "#N/A", "#NUM!", "#NULL!", "#CYCLE", "#CALC!")


def _s(v):
    try:
        return str(v.value[0, 0])
    except Exception:
        return str(getattr(v, "value", v))


def main():
    import formulas
    fn = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    base = fn.split("/")[-1]
    xl = formulas.ExcelModel().loads(fn).finish()
    sol = xl.calculate()

    def V(sheet, addr):
        v = sol.get(f"'[{base}]{sheet.upper()}'!{addr}")
        if v is None:
            return None
        try:
            return round(float(_s(v)), 3)
        except Exception:
            return _s(v)

    errs = [(k, _s(v)) for k, v in sol.items() if any(e in _s(v) for e in ERRS)]
    print(f"cells evaluated : {len(sol)}")
    print(f"formula errors  : {len(errs)}")
    for k, s in errs[:40]:
        print("   ", k, "=", s)

    print("\nHeadline checks (default Control-Panel state):")
    checks = [
        ("Scenario Summary", "E5", "Base case 3-month (₹ Cr)"),
        ("Scenario Summary", "E6", "Optimistic 3-month (₹ Cr)"),
        ("Scenario Summary", "E7", "Conservative 3-month (₹ Cr)"),
        ("Scenario Summary", "E8", "Target 3-month (₹ Cr)"),
        ("Event Impact Engine", "O13", "Final incl. events – total row area (₹ Cr)"),
    ]
    for sh, addr, lab in checks:
        print(f"   {lab:44} {V(sh, addr)}")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
