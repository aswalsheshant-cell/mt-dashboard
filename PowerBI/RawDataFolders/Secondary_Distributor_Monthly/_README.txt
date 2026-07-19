Drop the MONTHLY distributor-to-chain secondary file here (Format, customer
[distributor name], Direct/Distributor, Chain Name, State, Zone, NSV, MRP
value, Brand, Revised month, Month, FY, Channel, EMP ID, KAM, Secondary Sale,
Incentive).

Used to compute Cont%(Distributor, Brand, Chain) = NSV_chain / SUM(NSV across
chains for that distributor+brand) — the same "Monthly dynamic Cont%
(secondary-driven)" methodology already used in
PowerBI/SeedData/Mapping/ChainAccount_Mapping_Inferred.csv for other
multi-chain distributors. That Cont% is what allocates a distributor's raw,
un-split PRIMARY NSV across chains (see PowerQuery/34_PrimaryAllocationMap.pq).

Chain Name values are matched against PowerBI/SeedData/Masters/ChainMaster.csv
and PowerBI/SeedData/Masters/ChainAliases.csv — a raw name with no match in
either is NOT guessed; it goes to
PowerBI/SeedData/Mapping/ChainAccount_Mapping_NeedsReview.csv instead.

secondary_distributor_chain_Jun_26.csv — REPLACED 2026-07-19 with the
authoritative full file ("Dist_secondary_for_driven_primary_june26.xlsx",
712 data rows, 399 distinct Bill-to-customer, 26 chains, 5 brands),
superseding the earlier 142-row/20-distributor excerpt pasted in chat
(same period, that version was a partial sample, not a different dataset).
All 26 raw chain names resolved against ChainMaster.csv/ChainAliases.csv
case-insensitively -- 3 new spelling variants added to ChainAliases.csv
this session (FRANKROSS, Sasta Sunder, Reliance Retail-(Azorte)); VMM
(all-caps) matched the existing Vmm alias case-insensitively, no new
entry needed. Cont% recomputed at full float precision in
PowerBI/SeedData/Mapping/Secondary_Cont_Pct_Jun26.csv (677 rows, 616
Distributor x Brand groups, every group verified to sum to exactly 100%)
and used to allocate PowerBI/RawDataFolders/Primary_MTD_Monthly/
MTD_Primary_Jun_26.csv to chain -- see agent/pbi_build/FY27_Jun26/.
