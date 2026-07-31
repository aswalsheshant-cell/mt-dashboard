# Chain-Wise Store Master — City QC & Duplicate Detection

Correction-ready QC audit of the chain-wise store master
(`Final_Jan26_to_June26_chainwise_storelist.xlsb`, Sheet1 — 11,497 rows, 19 chains).

## Deliverable

`Store_Master_QC_Report.xlsx` — 8 sheets:

| Sheet | Contents |
|-------|----------|
| `Store_Master_QC` | All 11,497 original rows, unchanged, + 25 appended QC columns. Colour-highlighted. |
| `City_Corrections` | Rows needing city/state/zone standardization or correction. |
| `Duplicate_Review` | Exact / site-code-conflict / same-store / formatting duplicates. |
| `Removal_Recommendations` | Records recommended for removal or merge, with the master to retain. |
| `Manual_Review` | Rows with insufficient/conflicting evidence (confidence < 75). |
| `QC_Summary` | Reconciliation and counts. |
| `Chain_Summary` | Per-chain corrections, duplicates, manual reviews, QC accuracy %. |
| `Audit_Log` | Validation date, source, assumptions, completion status. |

## Method (grounded, no fabricated evidence)

Validation uses the primary business key **Chain Name × Site Code** plus an
**offline curated India-geography reference** (`geo_ref.py`): canonical city
spellings (Bangalore→Bengaluru, etc.), city→district→state→geographic-zone
lookups, a locality→parent-city map (Kondapur→Hyderabad, HSR Layout→Bengaluru,
Salt Lake→Kolkata …), state canonicalisation, and zone standardization rules.

No live web calls were made in this run and **no source links were invented**.
Rows that would need a store-locator / map confirmation are honestly flagged
`Manual_Review_Required = YES` and listed in `Manual_Review`.

Business conventions are respected, not "corrected": state groupings
(Delhi NCR, UP/UK, Punjab/J&K/HP, Northeast) and business sub-zones
(South-1, South-2) are valid. Ambiguous multi-state city names (Bilaspur,
Aurangabad …) are not force-corrected.

## Reproduce

```bash
pip install pyxlsb openpyxl pandas
python build_qc.py         # classify -> res.pkl  (edit SRC path at top)
python build_workbook.py   # render -> Store_Master_QC_Report.xlsx
```

Original values are never overwritten; every recommendation lives in a new
column. Site Code is preserved as text.
