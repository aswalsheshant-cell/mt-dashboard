# Refresh Guide (Monthly SOP)

This is the standard operating procedure for refreshing the MT Leadership
Dashboard. It is also reproduced as **Page 18: Refresh Guide** inside the report
so anyone opening the `.pbix` can read it without leaving Power BI.

---

## 1. Where to paste the latest file

Copy the new raw file into the matching folder under your root
(`pRootFolder`, e.g. `C:\MT-Dashboard`):

| Data | Folder | How often | Grain |
|---|---|---|---|
| Primary sales | `RawDataFolders\Primary_Weekly\` | **Weekly** | Week × Store × Article |
| Offtake sales | `RawDataFolders\Offtake_Monthly\` | **Monthly** | Month × Store × Article |
| Nielsen market share | `RawDataFolders\Nielsen_Monthly\` | Monthly | Month × Category × Brand × Zone |
| TDP / ACV | `RawDataFolders\TDP_Monthly\` | Monthly | Month × Chain × Article |

- Just **add** the new file; do not delete old ones (history is built by
  combining all files). To **fix** a month, replace that single file.
- Files whose name starts with `_` are ignored — that's how the `_TEMPLATE_*`
  files sit safely in the folder. Prefix anything you want excluded with `_`.
- Suggested naming: `Offtake_May26.csv`, `Primary_2026-W18.csv`.

## 2. What file format to use

- **CSV (UTF-8)** is preferred. `.xlsx` and `.xlsb` also work — the first sheet
  is read.
- The **first row must be the header**, matching the template exactly.
- Use the blank templates in `templates/` (and the `_TEMPLATE_*` copy already in
  each folder) as the starting point every month.

## 3. Column names that must NOT be changed

Power Query matches columns **by name**. Renaming any of these breaks the
refresh. (Full list with types in `DataDictionary.md`.) The critical keys:

**Primary (weekly):** `Week Start Date, Month, FY Year, Quarter, Chain, Account,
Zone, State, City, Store Code, Store Name, Brand, Category, Sub-category, Range,
Pack Size, Article Code, Article Description, EAN Code, Primary NSV, Primary Qty,
MRP Sales, Data Source Name`

**Offtake (monthly):** same as above but `Offtake NSV, Offtake Qty` instead of
the Primary measures, and no `Week Start Date`.

**Nielsen:** `Month, FY Year, Nielsen Category, Brand, Zone, Market Value Sales,
Our Brand Sales, Value Market Share %, Volume Market Share %, Data Source Name`

**TDP:** `Month, FY Year, Chain, Zone, State, Brand, Category, Sub-category,
Pack Size, Article Code, Article Description, ACV %, AIC, Numeric Distribution,
Weighted Distribution, Data Source Name`

> `Month` must be in the form **`MMM'YY`** e.g. `May'26`. The model converts it
> to a real date. If your source uses a different format, fix it in the file
> before saving, or adjust the `AddMonthStart` step once in the query.

## 4. Checks to do after refresh

1. Open **Page 12: Data Quality Check** — every issue count should be **0**
   (or explained). Look specifically at:
   - Unmapped Chain / Brand / Category / Zone → add the new value to the
     relevant master CSV in `SeedData\Masters\` and refresh again.
   - Missing EAN / Article Code / negative or blank NSV → fix in the raw file.
   - `Data Health %` should be ≥ 99%.
2. Open **Page 1: Executive Summary** — confirm the **Latest Month** is the
   month you just added and the NSV total looks right vs the source.
3. Spot-check one chain's NSV on **Page 3** against the raw file.
4. If you added a new SKU, confirm it appears in `Article Master` (add it to
   `ArticleMaster.csv` if not).

## 5. How to export raw data from Power BI

Use **Page 11: Raw Data Export View**.

- **In Power BI Desktop:** click the table visual ▸ *More options (…)* ▸
  *Export data* ▸ choose *Summarized* or *Underlying* data ▸ Excel/CSV.
- **In Power BI Service (browser):** same *More options ▸ Export data*. The
  *Underlying data* option must be enabled for the user — see below.
- Apply the slicers first (Month, Chain, Zone, State, Brand, Category,
  Sub-category, Article, Data Source) to scope exactly what you need, then export.

### Enabling export permissions (admin, one-time)
- **Tenant level:** Power BI Admin Portal ▸ *Tenant settings ▸ Export and
  sharing settings* ▸ "Export data" / "Export to Excel" → enable for the
  required security group only.
- **Dataset level:** Workspace ▸ dataset ▸ *Settings* — ensure *Build* /
  *Read with underlying data* is granted only to users who should export raw.
- Keep underlying-data export restricted to the MT analytics group; everyone
  else can still export summarized visuals.

---

## Quick monthly checklist

- [ ] New file(s) dropped into the correct folder, template headers intact
- [ ] `Month` formatted `MMM'YY`
- [ ] Home ▸ Refresh completed without errors
- [ ] Page 12 Data Quality all zero / explained
- [ ] Page 1 latest month correct
- [ ] New masters (chain/brand/SKU) added if flagged
- [ ] Published to Service (if shared)
