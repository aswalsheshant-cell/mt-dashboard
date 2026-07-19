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

secondary_distributor_chain_Jun_26.csv — supplied 2026-07-19, 142 data rows,
20 distributors, 19 chains, 5 brands. All chain names resolved (2 new
spelling variants added to ChainAliases.csv, see its Verified column).
