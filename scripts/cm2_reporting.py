"""Signed Primary source-tax QC, with all monetary values in INR lakh.

Callers must validate invoice NSV semantics and explicitly set
``frame.attrs['invoice_nsv_tax_exclusive'] = True`` before a rate is shown.
QC does not certify source units, source-to-allocation reconciliation, or
Finance approval. MRP is recorded independently and is never reconstructed.
"""
import numpy as np
import pandas as pd

# A 0.05 percentage point tolerance accommodates recorded rounding. Nonzero
# tax on less than Rs 1 NSV or Rs 0.10 tax is reviewed even if its ratio fits.
# These are QC thresholds, not authority to adjust or discard source amounts.
RATE_TOLERANCE_PCT = 0.05
MIN_ABS_NSV_LAKH = 1.0 / 100_000
MIN_ABS_TAX_LAKH = 0.10 / 100_000
REQUIRED_COLUMNS = ("_FY", "_M", "_Chain", "_Brand", "_category", "_EAN No.",
                    "_NSV", "_TaxLOC", "_MRP", "_Chan")


def build_tax_basis(primary: pd.DataFrame) -> pd.DataFrame:
    """Copy allocated article rows, preserve signed source fields, add row QC.

    Missing tax is distinct from recorded zero. Missing/nonfinite base or MRP,
    zero base, inconsistent signs, and immaterial nonzero invoices are reviewed.
    The function neither changes amounts nor asserts tax exclusivity for callers.
    """
    missing = sorted(set(REQUIRED_COLUMNS) - set(primary.columns))
    if missing:
        raise ValueError(f"Missing Primary columns: {', '.join(missing)}")
    rows = primary.copy()
    nsv, tax, mrp = (pd.to_numeric(rows[c], errors="coerce")
                     for c in ("_NSV", "_TaxLOC", "_MRP"))
    status = pd.Series("REVIEW_RATE_OR_BASE", index=rows.index, dtype="object")
    compatible = (np.isfinite(nsv) & np.isfinite(tax) & np.isfinite(mrp)
                  & nsv.ne(0) & (np.sign(mrp) == np.sign(nsv)))
    status.loc[compatible & tax.eq(0)] = "ZERO_TAX"
    material = (compatible & nsv.abs().ge(MIN_ABS_NSV_LAKH)
                & tax.abs().ge(MIN_ABS_TAX_LAKH) & (np.sign(tax) == np.sign(nsv)))
    rate = 100 * tax / nsv.where(nsv.ne(0))
    for expected in (5, 18):
        status.loc[material & (rate - expected).abs().le(RATE_TOLERANCE_PCT)] = f"VALID_{expected}_PERCENT"
    status.loc[tax.isna()] = "MISSING_TAX"
    rows["gst_qc_status"] = status
    return rows


def tax_summary(rows: pd.DataFrame) -> dict:
    """Summarize a selected signed population, withholding unvalidated rates.

    ``reviewed_amount`` is absolute reviewed NSV exposure (INR lakh), preventing
    credits from cancelling exceptions; ``reviewed_nsv``/``reviewed_tax`` remain
    signed. Missing tax sums stay None if no numeric tax exists. A population
    with missing/review rows exposes its recorded totals but no effective rate.
    """
    if "gst_qc_status" not in rows:
        raise ValueError("Call build_tax_basis before tax_summary")
    amounts = {key: pd.to_numeric(rows[col], errors="coerce")
               for key, col in {"nsv": "_NSV", "tax": "_TaxLOC", "mrp": "_MRP"}.items()}
    def total(values):
        value = values.sum(min_count=1)
        return float(value) if np.isfinite(value) else None
    result = {key: total(values) for key, values in amounts.items()}
    counts = {str(k): int(v) for k, v in rows.gst_qc_status.value_counts().items()}
    statuses = set(counts)
    if "MISSING_TAX" in statuses:
        aggregate = "MISSING_TAX"
    elif "REVIEW_RATE_OR_BASE" in statuses:
        aggregate = "REVIEW_RATE_OR_BASE"
    elif len(statuses) > 1:
        aggregate = "MIXED_RATE"
    else:
        aggregate = next(iter(statuses), "NOT_AVAILABLE")
    reviewed = rows.gst_qc_status.eq("REVIEW_RATE_OR_BASE")
    missing = rows.gst_qc_status.eq("MISSING_TAX")
    validated = rows.attrs.get("invoice_nsv_tax_exclusive") is True
    rate_available = (validated and bool(statuses)
                      and statuses <= {"VALID_5_PERCENT", "VALID_18_PERCENT", "ZERO_TAX"}
                      and result["nsv"] is not None and result["nsv"] != 0
                      and result["tax"] is not None)
    result.update(
        effective_gst_pct=100 * result["tax"] / result["nsv"] if rate_available else None,
        invoice_nsv_tax_exclusive=validated,
        gst_qc_status=aggregate,
        status_counts=counts,
        reviewed_amount=float(amounts["nsv"][reviewed].abs().sum()),
        reviewed_nsv=total(amounts["nsv"][reviewed]),
        reviewed_tax=total(amounts["tax"][reviewed]),
        missing_tax_nsv=total(amounts["nsv"][missing]),
    )
    return result
