# Data-impact checklist

Screen every PR. Any "yes" routes that part to `sales-data-reconciliation` before the
finding is rated.

- [ ] Does the diff touch `scripts/build_dashboard_data.py`, a `split_*` script,
      `config/`, `PowerBI/SeedData/` or `dashboard/data.js`?
- [ ] Could it change a displayed total, a KPI card or a chart series?
- [ ] Does it filter, dedupe or exclude rows (e.g. `Unmapped Chain`, negative
      return/credit rows, `Pan India`, Reliance Brand Counter)? If so, do the shown rows
      still add up to the governed total?
- [ ] Reliance Brand Counter isolation applies to **Offtake only**, never Primary.
- [ ] Are Primary, Distributor Secondary and Offtake kept separate, and is any
      cross-measure ratio labelled as such?
- [ ] FY bucket derived by THE ONE FY RULE; FY25 has no real Primary or Offtake source
      (see `docs/DATA_AVAILABILITY_MATRIX.md` before calling a month missing).
- [ ] Missing is shown as `–` and never filled with another FY's numbers or a zero.
- [ ] Governed baselines unchanged unless the PR's purpose is to change them:
      FY26 Primary 32,900.36 L; FY26 Offtake 31,119.88 L (`offtake.total`); MT universe
      426 stores; FY27 forecast baseline 441 Cr. Confirm with
      `python scripts/ci_validate_datajs.py` and a before/after diff of the block.
- [ ] Effective-dated mappings not applied retroactively.
- [ ] Claims, promotions, provisions: no lifecycle double count (FM-14).

If the PR does not touch data, say so explicitly in the merge preview ("Not changed:
data.js, config/, PowerBI/, seed data, baselines") with the diff command that shows it.
