Drop the MONTHLY SAP invoice-level primary export here (Purchase Order
Number, Inv No., Ship-To Name, Article Code, EAN No., brand, Inv Qty,
Inv. Net value(LOC) [=NSV], MRP Value, Chanel [MT/EB2B/SIS], MTD-Sale type,
Cancelled, Zone/State, ...).

Distinct from Primary_ShipTo_Monthly/, which holds ALREADY chain-allocated
primary. This folder holds the RAW, un-split SAP export -- one row per
invoice line, Ship-To Name only (no Chain column). Allocation to chain
happens via agent/mtagent (or manually, see below):
  - Direct Ship-To Name -> 1:1 chain via PowerBI/SeedData/Masters/ShipToMaster.csv
  - Distributor Ship-To Name -> N-way chain split via Cont% from
    PowerBI/SeedData/Mapping/Secondary_Cont_Pct_Jun26.csv (or the matching
    month's Cont% file), same methodology as
    PowerBI/PowerQuery/34_PrimaryAllocationMap.pq.

MTD_Primary_Jun_26.csv -- supplied 2026-07-19, 23,193 data rows.
Total NSV Rs 41,67,37,933.62 (Rs 41.67 Cr). Allocated to chain and
reconciled: see agent/pbi_build/FY27_Jun26/ (build output, gitignored --
regenerate by rerunning the allocation, not committed here).
