# Excel for MT reporting

Grain, fiscal-year and denominator rules are in the parent SKILL.md. This file covers
formula construction, tracker design and reconciliation sheets.

## Ask before writing a formula

1. What is the grain of the sheet — one row per what?
2. Are the lookup keys unique on the lookup sheet? If not, `XLOOKUP` returns the first
   match silently and the total is wrong.
3. Is this a one-off or a monthly file? A monthly file needs structured references and
   a QC row; a one-off does not.
4. Who will edit it after you? Formulas that only their author can follow get replaced
   by hand-typed values within two cycles.

## House style

- Use Excel Tables and structured references (`Table1[Value]`) rather than `A2:A10000`.
  Ranges break when rows are added; tables do not.
- One calculation per column, with a header that names the unit.
- Absolute and relative references chosen deliberately — `$B$2` for a single parameter
  cell, `$B2` when copying across.
- Parameters (fiscal year, thresholds, exclusions) live in a labelled input block at the
  top of the sheet, never inside the formula.
- Wrap anything that can fail in `IFERROR` with an explicit fallback, not a blank.
- Colour convention: blue for inputs, black for formulas, green for links to other
  sheets. This makes an unauthorised hardcode visible immediately.

## Core patterns

### Conditional aggregation

```excel
=SUMIFS(Offtake[Value], Offtake[Chain], $A2, Offtake[Month], B$1)
=COUNTIFS(Offtake[Chain], $A2, Offtake[Units], ">0")
=AVERAGEIFS(Offtake[Value], Offtake[Chain], $A2)
```

`SUMIFS` over `SUMPRODUCT` wherever possible — it is faster and readable. Criteria
referencing cells (`$A2`, `B$1`) rather than typed text keeps the grid maintainable.

### Lookup

```excel
=XLOOKUP($A2, Master[ChainCode], Master[ChainName], "UNMAPPED")
=INDEX(Master[ChainName], MATCH($A2, Master[ChainCode], 0))
```

Always supply the not-found argument, and make it `"UNMAPPED"` rather than `""` — a
blank hides the failure, a label surfaces it and can be counted.

Check for duplicate keys before trusting any lookup:

```excel
=SUMPRODUCT(MAX(COUNTIF(Master[ChainCode], Master[ChainCode])))
```

A result above 1 means the lookup table has duplicates and every result is suspect.

### Growth, contribution, rank

```excel
=IFERROR((C2-B2)/ABS(B2), "NA")                                  growth, signed
=IFERROR(C2/SUM($C$2:$C$200), 0)                                 contribution
=COUNTIFS($C$2:$C$200, ">"&C2)+1                                 rank — use this one
=SUMPRODUCT((Zone=$A2)*(Value>C2))+1                             rank within a zone
=RANK.EQ(C2, $C$2:$C$200)                                        avoid on dynamic data
```

`ABS()` in the growth denominator keeps the sign correct when the base is negative.

**Use the COUNTIFS method for ranking, not `RANK.EQ`.** On a range that grows each month
`RANK.EQ` silently misranks when rows are added outside its fixed reference, and it
handles ties by leaving gaps that break a top-N filter. COUNTIFS re-evaluates against
whatever is currently in the range and is easier to extend with a second criterion.

### L3M average — the standard smoothed base

```excel
=IFERROR(AVERAGE(OFFSET(D2,0,-3,1,3)), "NA")     last three columns, avoid: volatile
=AVERAGEIFS(Offtake[Value], Offtake[Chain], $A2,
            Offtake[Month], ">="&EDATE($B$1,-3),
            Offtake[Month], "<"&$B$1)             preferred: non-volatile, auditable
```

L3M is this organisation's standard comparison base alongside MoM and YoY. Prefer the
`AVERAGEIFS` form — `OFFSET` is volatile and recalculates on every keystroke.

### Fiscal year and month order

```excel
=IF(MONTH(A2)>=4, YEAR(A2)+1, YEAR(A2))                          FY year
="FY"&TEXT(MOD(IF(MONTH(A2)>=4,YEAR(A2)+1,YEAR(A2)),100),"00")   FY tag
=MOD(MONTH(A2)-4,12)+1                                           FY month number, Apr=1
```

Sort and chart by the FY month number, never by the month name.

### Indian number display

Custom number formats, applied to the cell rather than embedded in the formula:

```
[>=10000000]0.0,,,"Cr";[>=100000]0.0,,"L";0
+0.0%;-0.0%;0.0%
```

The first shows crore above one crore, lakh above one lakh, and the raw number below.
The second forces an explicit sign on growth, which is what a reader scans first.

## Tracker design

A monthly tracker has four zones, top to bottom:

1. **Inputs** — parameters and the refresh date, labelled and blue.
2. **Raw** — the pasted or queried source, untouched. Never type over it.
3. **Working** — mapped and calculated columns.
4. **Output** — the summary that is read or copied out.

Keep raw and working separate so a bad refresh can be diagnosed. Add a refresh date
cell and reference it in the output header, so a stale file announces itself.

Prefer Power Query inside Excel over manual paste for anything repeated. It records the
transformation, survives a new month, and removes the paste step where most errors
enter.

## The QC block — every file ends with one

```excel
Source total          =SUM(Raw[Value])
Output total          =SUM(Output[Value])
Difference            =B1-B2
Status                =IF(ABS(B3)<1, "PASS", "BLOCKED")
Duplicate keys        =SUMPRODUCT(MAX(COUNTIF(Key,Key)))-1
Unmapped rows         =COUNTIF(Working[ChainName], "UNMAPPED")
Rows in / rows out    =ROWS(Raw) & " / " & ROWS(Output)
```

A file without a QC block is not finished. The status cell is the thing another person
looks at before using the numbers.

## Working habits with raw MT files

- **Keep raw data headers exactly as received.** Every mapping, formula and Power Query
  step binds to them. Rename in the working layer, never in the raw layer.
- **Never delete total rows from a source extract.** They are the reconciliation check —
  exclude them from calculations with a filter or a flag column instead, so the source
  total remains available to tie against.
- **Force a full recalculation before sharing**: `Ctrl+Alt+F9`. A file that looks right
  on screen can be showing cached results, and `F9` alone does not rebuild dependencies.
- Refresh Power Query and pivots before reading any number off the output tab, and note
  the refresh time in the header.
- Paste as values only into an explicitly named snapshot sheet, never over a live
  formula column.

## What not to do

- Do not merge cells in a data range. It breaks sorting, filtering and every structured
  reference.
- Do not hide rows to exclude data — filter or flag it, so the exclusion is visible and
  countable.
- Do not use volatile functions (`OFFSET`, `INDIRECT`, `NOW`) in large grids; they
  recalculate on every change and make the file unusable.
- Do not hardcode a number inside a formula. It becomes invisible the moment the author
  leaves.
- Do not paste values over a formula column to "fix" a result. Fix the input.
- Do not build a fourth tracker for something the dashboard already reports.
