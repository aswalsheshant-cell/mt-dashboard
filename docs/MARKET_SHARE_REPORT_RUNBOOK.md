# Market-share report: monthly refresh

One report, one command. The HTML (Nielsen Cuts, Opportunity, 90-Day Tracker, Chains & Packs, Price & Volume, Chain Share & Plan), the card in the MT dashboard
(Demand & S&OP > Market Share) and the Power BI seeds are all built from the same files, so they always show the same numbers.

## What to have each month
| Input | Used for | If missing |
|---|---|---|
| Nielsen Facewash and Shampoo workbooks (.xlsb) | share, price, distribution, packs | the Nielsen blocks stay at the last month |
| Store x article offtake for the month (`PowerBI/RawDataFolders/Offtake_Monthly/offtake_store_article_<Mon>_26.csv`) | chain contribution, price and volume, city plan, store counts | those blocks stay as they were |
| Lulu, More Retail, Wellness, Reliance retailer files | Chain Share & Plan | the committed account files are used |
| Store list workbook | store master (unique stores, state and zone follow the offtake) | the committed master is used |
| Last-year store files `offtake_store_article_<Mon>_25.csv` | last-year columns in the city workbook | those columns stay grey, nothing is estimated |

## Run
```
python scripts/refresh_market_share_report.py --label Sep26 --month "Sep 26" \
    --months Apr May Jun Jul Aug Sep --tracker-from data/nielsen_aug26.json --standalone \
    --facewash Nielson_FW_Report_Sep26.xlsb --shampoo Nielson_Shampoo_Report_Sep26.xlsb \
    --lulu <Compiled_Monthly_Files.xlsx> --more <More_MS.xlsx> --wellness <Wellness_MS.xlsb> --reliance <RIL_BA_Store_MS.xlsb> \
    --store-master <storelist.xlsb>
```
`--dry-run` lists the steps. It stops at the first failure; earlier steps are safe to repeat.

Offtake data for the month also goes into `dashboard/data.js`:
`python scripts/build_dashboard_data.py --offtake-patch --src PowerBI/RawDataFolders/Offtake_Monthly --out dashboard/data.js`

## Then check
1. `python -m pytest -q`
2. `node tests/nielsen_ms_browser.js dist/Nielsen_MS_<label>_Dashboard.html <screenshot-folder> aug` (the aug mode checks need the new month's expected figures updated in the test)
3. `node tests/dashboard_sweep.js` with the dashboard served over HTTP (44 states).
4. Power BI: copy `PowerBI/SeedData/Nielsen/*` into the matching `RawDataFolders/Nielsen_*` drop folders, Refresh. Brand cuts are in `Nielsen_Brand_Cut_Monthly` (query 57, measures in DAX 18).

## Rules that keep it the same every month
- Value is Rs crore (Nielsen) or Rs lakh (internal and retailer files); Reliance retailer files are gross sales, so compare shares not rupees.
- Reliance Brand Counter is kept out of the offtake total and is its own line in the chain share view.
- A store is one row; state and zone follow the offtake data; a blank source cell is shown as a dash, never zero.
- Only categories that matter to us (0.5% or more of our own sales across the chains) are flagged as white space.
