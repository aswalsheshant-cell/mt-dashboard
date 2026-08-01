# -*- coding: utf-8 -*-
"""Canonical schema for the Chain x Article Margin Repository.

Single source of truth for column names, grouping, primary-key composition
and the margin-component sign map. Every other module imports from here so
the repository, imports and all 10 outputs stay column-consistent.
"""

# ---------------------------------------------------------------------------
# Column groups (exact order used in the repository master table)
# ---------------------------------------------------------------------------
ARTICLE_COLS = [
    "Chain", "Brand", "Category", "Sub Category", "Range", "Article", "Variant",
    "Pack Size", "EAN", "SKU Code", "MRP", "Launch Status", "NPI Flag",
    "EPD Flag", "Status",
]

# Commercial percentage components. sign = +1 earned margin, -1 pass-through/cost.
# Used to DERIVE "Final Effective Margin %" only when the source leaves it blank.
# Business-configurable: edit the sign here if a component should net differently.
COMMERCIAL_COMPONENTS = [
    ("Trade Margin %", +1),
    ("TOT %", +1),
    ("Backend %", +1),
    ("Frontend %", +1),
    ("Visibility %", +1),
    ("Listing Support %", +1),
    ("Rental Support %", +1),
    ("Display %", +1),
    ("Scheme %", +1),
    ("Special Commercial %", +1),
    ("Additional Discount %", +1),
    ("Distributor Margin %", +1),
    ("Consumer Offer %", -1),   # pass-through to consumer
    ("Cash Discount %", -1),    # early-payment cost
]
COMMERCIAL_PCT_COLS = [c for c, _ in COMMERCIAL_COMPONENTS]
COMMERCIAL_COLS = COMMERCIAL_PCT_COLS + ["Final Effective Margin %"]

CONDITION_COLS = [
    "Minimum Order Qty", "Case Configuration", "GST %", "Distributor",
    "Warehouse", "Supply Source", "Region Applicability", "State Applicability",
    "Store Format",
]

DATE_COLS = [
    "Effective From", "Effective To", "Last Updated", "Updated By",
    "Approval Status", "Approval Date", "Version Number",
]

# Approval workflow columns
APPROVAL_COLS = [
    "Submitted_By", "Submitted_Date", "Reviewed_By", "Reviewed_Date",
    "Approval_Remarks", "Business_Owner", "Finance_Approval_Status",
]
VALID_APPROVAL_STATUSES = {
    "DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED", "SUPERSEDED",
}

# Repository-internal audit columns (appended, never sourced from files)
AUDIT_COLS = [
    "Record_Key", "Article_Key", "Source_File", "Import_Batch_Id",
    "Import_Timestamp", "Record_Status", "QC_Severity", "Validation_Flags",
    "Is_Current", "Change_Type",
]

REPO_COLS = ARTICLE_COLS + COMMERCIAL_COLS + CONDITION_COLS + DATE_COLS + APPROVAL_COLS + AUDIT_COLS

# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------
# Full record identity (a unique physical row / one commercial version).
RECORD_KEY_COLS = [
    "Chain", "Brand", "Category", "Sub Category", "Article", "EAN",
    "Pack Size", "MRP", "Effective From",
]

# Article identity for versioning + change detection. EAN takes priority;
# when EAN is present it dominates. Effective From is intentionally excluded
# so that a new Effective From is treated as a NEW VERSION of the same article.
ARTICLE_KEY_EAN = ["Chain", "EAN", "Pack Size", "MRP"]
ARTICLE_KEY_FALLBACK = ["Chain", "Brand", "Article", "Pack Size", "MRP"]

VALID_GST = {0, 5, 12, 18, 28}

# Numeric columns (for coercion / validation)
NUMERIC_PCT_COLS = COMMERCIAL_PCT_COLS + ["Final Effective Margin %", "GST %"]
NUMERIC_COLS = NUMERIC_PCT_COLS + ["MRP", "Minimum Order Qty", "Case Configuration",
                                   "Version Number"]

# ---------------------------------------------------------------------------
# Header aliases: map messy incoming headers -> canonical repository columns.
# Extend freely as new source layouts appear.
# ---------------------------------------------------------------------------
HEADER_ALIASES = {
    "chain": "Chain", "chain name": "Chain", "customer": "Chain", "account": "Chain",
    "brand": "Brand",
    "category": "Category", "cat": "Category",
    "sub category": "Sub Category", "subcategory": "Sub Category", "sub-cat": "Sub Category",
    "sub_category": "Sub Category",
    "range": "Range",
    "article": "Article", "article name": "Article", "product": "Article",
    "description": "Article", "item description": "Article", "material description": "Article",
    "product name": "Article", "sku name": "Article",
    "variant": "Variant",
    "pack size": "Pack Size", "pack": "Pack Size", "size": "Pack Size", "grammage": "Pack Size",
    "ean": "EAN", "ean code": "EAN", "barcode": "EAN", "ean/upc": "EAN", "gtin": "EAN",
    "sku": "SKU Code", "sku code": "SKU Code", "material": "SKU Code", "material code": "SKU Code",
    "article code": "SKU Code", "sap code": "SKU Code",
    "mrp": "MRP", "mrp (inr)": "MRP", "mrp rs": "MRP",
    "launch status": "Launch Status", "npi": "NPI Flag", "npi flag": "NPI Flag",
    "epd": "EPD Flag", "epd flag": "EPD Flag", "status": "Status", "active": "Status",
    # commercial
    "trade margin": "Trade Margin %", "trade margin %": "Trade Margin %", "margin": "Trade Margin %",
    "margin %": "Trade Margin %", "retailer margin": "Trade Margin %",
    "tot margin": "Trade Margin %", "tot margin %": "Trade Margin %",
    "tot": "TOT %", "tot %": "TOT %", "turnover tax": "TOT %",
    "backend": "Backend %", "backend %": "Backend %",
    "frontend": "Frontend %", "frontend %": "Frontend %",
    "visibility": "Visibility %", "visibility %": "Visibility %", "visibility support": "Visibility %",
    "listing": "Listing Support %", "listing support": "Listing Support %", "listing %": "Listing Support %",
    "rental": "Rental Support %", "rental support": "Rental Support %",
    "display": "Display %", "display %": "Display %", "display support": "Display %",
    "consumer offer": "Consumer Offer %", "consumer offer %": "Consumer Offer %", "offer": "Consumer Offer %",
    "cash discount": "Cash Discount %", "cd": "Cash Discount %", "cash disc": "Cash Discount %",
    "scheme": "Scheme %", "scheme %": "Scheme %",
    "additional discount": "Additional Discount %", "add disc": "Additional Discount %",
    "additional margin": "Additional Discount %",
    "special commercial": "Special Commercial %", "special": "Special Commercial %",
    "distributor margin": "Distributor Margin %", "dist margin": "Distributor Margin %",
    "final effective margin": "Final Effective Margin %", "effective margin": "Final Effective Margin %",
    "final margin": "Final Effective Margin %", "final margin to be uploaded": "Final Effective Margin %",
    # conditions
    "moq": "Minimum Order Qty", "minimum order qty": "Minimum Order Qty", "min order": "Minimum Order Qty",
    "case config": "Case Configuration", "case configuration": "Case Configuration", "case size": "Case Configuration",
    "gst": "GST %", "gst %": "GST %", "tax": "GST %",
    "distributor": "Distributor", "distributor name": "Distributor", "customer name": "Distributor",
    "warehouse": "Warehouse", "wh": "Warehouse",
    "supply source": "Supply Source", "source": "Supply Source", "dc/dsd": "Supply Source",
    "region": "Region Applicability", "region applicability": "Region Applicability",
    "state": "State Applicability", "state applicability": "State Applicability",
    "store format": "Store Format", "format": "Store Format",
    # dates
    "effective from": "Effective From", "eff from": "Effective From", "valid from": "Effective From",
    "start date": "Effective From", "wef": "Effective From",
    "effective to": "Effective To", "eff to": "Effective To", "valid to": "Effective To",
    "end date": "Effective To", "expiry": "Effective To",
    "last updated": "Last Updated", "updated on": "Last Updated",
    "updated by": "Updated By", "owner": "Updated By",
    "approval status": "Approval Status", "approved": "Approval Status",
    "approval date": "Approval Date", "approved on": "Approval Date",
    "version": "Version Number", "version number": "Version Number",
}


def canon_header(h):
    if h is None:
        return None
    key = " ".join(str(h).strip().lower().split())
    return HEADER_ALIASES.get(key, str(h).strip())
