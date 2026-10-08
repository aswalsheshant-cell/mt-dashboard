# Dashboard unit reconciliation — 2026-10-03

**Scope:** FY27 Apr–Aug'26 governed Offtake NSV, same committed store × article source files, Reliance Brand Counter excluded, INR lakh. **Status:** source-to-HTML MATCH; live Power BI Desktop values PENDING. B5 remains BLOCKED_PENDING_DESKTOP_EVIDENCE.

[Successful read-only reconciliation run](https://github.com/aswalsheshant-cell/mt-dashboard/actions/runs/37109594457) on commit `622016e6c8a7f3f08921c2421831763b4a4685d3`: 9 targeted tests passed; the aggregate [private artifact](https://github.com/aswalsheshant-cell/mt-dashboard/actions/runs/37109594457/artifacts/11269141832) expires 2026-10-10 08:25 UTC. The full JSON was reviewed in the job log. All 25 audited source files retained the same SHA-256, row counts, and signed totals as the earlier [source unit audit](dashboard_unit_source_audit_2026-10-03.md).

| FY27 month | Governed source (lakh) | HTML (lakh) | Source − HTML (lakh) | Expected model rupees from source | Live Power BI rupees / lakh | Status |
|---|---:|---:|---:|---:|---|---|
| Apr-26 | 3588.51 | 3588.51 | -0.0032 | ₹35,88,50,677.38 (calculated, unobserved) | Pending Desktop refresh | SOURCE_HTML_MATCH; PBI_PENDING |
| May-26 | 4019.42 | 4019.42 | 0.0032 | ₹40,19,42,315.01 (calculated, unobserved) | Pending Desktop refresh | SOURCE_HTML_MATCH; PBI_PENDING |
| Jun-26 | 3840.46 | 3840.46 | -0.0027 | ₹38,40,45,725.05 (calculated, unobserved) | Pending Desktop refresh | SOURCE_HTML_MATCH; PBI_PENDING |
| Jul-26 | 3621.47 | 3621.47 | -0.0038 | ₹36,21,46,620.54 (calculated, unobserved) | Pending Desktop refresh | SOURCE_HTML_MATCH; PBI_PENDING |
| Aug-26 | 3975.13 | 3975.13 | -0.0045 | ₹39,75,12,553.71 (calculated, unobserved) | Pending Desktop refresh | SOURCE_HTML_MATCH; PBI_PENDING |

The comparison uses the source’s governed signed NSV totals and the published `offtake.months_fy27` / `monthly_fy27` arrays. It does not compare Primary against Offtake. Missing HTML months and duplicate monthly source files fail the audit instead of becoming zero.

## Power BI changes awaiting live verification

- `PowerBI/PowerQuery/11_Fact_OfftakeSales.pq` multiplies source Offtake NSV by 100,000 once at import. Source MRP Sales is already rupees and stays unchanged. Nulls and negative returns retain their meaning.
- The same query maps early “Reliance” rows by Store Type to either “Reliance Retail” or “Reliance Brand Counter,” preserving the separate RBC diagnostic. It parses quoted month labels, Excel serials, and monthly filenames, then derives FY through `fnFYLabel`; contradictory or unparseable periods fail refresh.
- `PowerBI/DAX/01_CoreMeasures.dax` uses governed MT Offtake for the headline target basis and Primary/Offtake gap. `14_SecondarySales_Measures.dax` converts the rupee Primary denominator to lakh before dividing by distributor secondary lakh. `43_SecondarySalesEfficiency.pq` leaves absent source months null and labels the model operands as rupees.
- QuickSetup consolidated copies have been updated. Structural and CI checks do not prove Desktop results, model relationships, or visual totals.

## Remaining evidence and holds

1. Refresh the exact PR commit in Power BI Desktop; record application version, source root, refresh result, five same-scope monthly Offtake values in rupees and lakh, and screenshots. Compare each to the table above at 0.01 lakh reporting precision. Record any difference as unresolved with the affected query/measure; do not change source rows to force equality.
2. Run the governed B5 live Desktop cases from PR #291 and record raw outputs and screenshots. Keep B5 open until the documented human exit decision.
3. Resolve the overlapping Primary ShipTo composite/narrower snapshots before claiming Primary model reconciliation. FY25/FY26 Offtake history is preaggregated in HTML and is outside these five committed monthly CSVs; it is NOT_COMPARABLE through this audit.
4. Keep PR #119 frozen and PR #267 on HOLD. Do not merge this draft PR without owner instruction.
