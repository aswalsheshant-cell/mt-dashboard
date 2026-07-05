Drop MONTHLY store x article offtake CSVs here (from
scripts/split_offtake_store_article_xlsb.py -> primary source:
"FY-24-26 Chain offtake Store Wise File till May.xlsb").
Query 11 is locked to these source headers:
Unique, Zone, State, City, SO/ASE Emp Code, SO/ASE Name, Chain Name, Store Type,
DC Code, DC Name, Internal Code, Site Code, Site Name, Article, Article_1, EAN,
Chain Article Description, Net Weight, Description as per Fountain, Brand,
Category, Sub_category, Range, MRP, Sales Qty, MRP Sales Value, NSV, Per pc,
With Tax, Margin, Revised Month, Month, Year, PPT Category.
Files starting with "_" are ignored. Then: Power BI > Refresh.
