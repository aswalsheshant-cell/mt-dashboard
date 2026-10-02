// =====================================================================
// FUNCTION: fnFYLabel   (THE ONE FY RULE, Power Query side)
// Returns the model's FY label ("25-26") for a date, Indian FY Apr-Mar:
//   Apr-Dec of year Y -> "YY-(YY+1)"      e.g. Apr-26 -> "26-27"
//   Jan-Mar of year Y -> "(YY-1)-YY"      e.g. Mar-26 -> "25-26"
// Same text as 'Date Table'[FY Year] and Targets[FY Year], so a fact's own
// [FY Year] column always agrees with the date slicer. Every fact query
// DERIVES [FY Year] from its month column with this function instead of
// copying whatever text the source file carried (FY'25-26 / FY26 / FY_24-25 /
// 25-26 ...). No year is typed anywhere, so FY28+ works on its own.
//
// Usage:  each fnFYLabel([MonthStart])
// =====================================================================
let
    fnFYLabel = (d as nullable date) as nullable text =>
        if d = null then null
        else
            let
                y = Date.Year(d),
                m = Date.Month(d),
                startYear = if m >= 4 then y else y - 1
            in
                Text.PadStart(Text.From(Number.Mod(startYear, 100)), 2, "0") & "-" &
                Text.PadStart(Text.From(Number.Mod(startYear + 1, 100)), 2, "0")
in
    fnFYLabel
