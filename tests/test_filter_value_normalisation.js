// Regression test for filter-value normalisation (recovered from the closed
// offline-AI branch, PR #14, rebuilt against current main).
// Source spellings that differ only by case/spacing ("West"/"WEST",
// "Hyaluronic Acid"/"Hyaluronic acid", "TDC  1%"/"TDC 1%") must show as ONE
// filter choice, and picking that choice must return the rows of EVERY
// spelling -- without changing any record, NSV value or total.
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && typeof normVal === 'function', { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  const r = await pg.evaluate(() => {
    const key = v => String(v).trim().replace(/\s+/g, ' ').toLowerCase();
    const dims = FILT.map(([k]) => k).filter(k => k !== 'FY' && k !== 'Month');
    FILT.forEach(([k]) => F[k] = []);
    const totalNsv = REC.reduce((a, x) => a + (x.NSV || 0), 0);

    // 1. no two filter options in a dimension differ only by case/spacing
    const dupOpts = {};
    dims.forEach(k => {
      const seen = {}, d = [];
      optsFor(k).forEach(v => { const n = key(v); if (seen[n]) d.push([seen[n], v]); else seen[n] = v; });
      if (d.length) dupOpts[k] = d;
    });

    // 2. every real variant group in the data: selecting its one option
    //    returns exactly the rows of all its raw spellings
    const groups = [];
    dims.forEach(k => {
      const g = {};
      REC.forEach(x => { if (x[k] == null) return; const n = key(x[k]); (g[n] = g[n] || new Set()).add(String(x[k])); });
      Object.values(g).filter(s => s.size > 1).forEach(s => {
        const raws = [...s];
        const expectRows = REC.filter(x => x[k] != null && s.has(String(x[k])));
        const canon = normVal(k, raws[0]);
        F[k] = [canon];
        const got = recFilter();
        F[k] = [];
        groups.push({
          dim: k, raws, canon,
          allSpellingsMapToOne: raws.every(v => normVal(k, v) === canon),
          optionCount: optsFor(k).filter(v => key(v) === key(canon)).length,
          expRows: expectRows.length, gotRows: got.length,
          expNsv: +expectRows.reduce((a, x) => a + (x.NSV || 0), 0).toFixed(4),
          gotNsv: +got.reduce((a, x) => a + (x.NSV || 0), 0).toFixed(4),
        });
      });
    });

    // 3. partition check: per dimension, NSV grouped by normalised value
    //    still adds up to the untouched grand total (no row lost/doubled)
    const partition = dims.map(k => {
      let s = 0; REC.forEach(x => { if (x[k] != null) s += (x.NSV || 0); });
      const nullNsv = REC.filter(x => x[k] == null).reduce((a, x) => a + (x.NSV || 0), 0);
      return { k, ok: Math.abs(s + nullNsv - totalNsv) < 1e-6 };
    });

    // 4. raw records untouched: original spellings still present in REC
    const rawStillThere = groups.every(g => g.raws.every(v => REC.some(x => String(x[g.dim]) === v)));

    // 5. drill-down stores the canonical value
    let drillOk = true;
    if (groups.length) {
      const g = groups[0];
      const nonCanon = g.raws.find(v => v !== g.canon) || g.raws[0];
      drillTo(g.dim, nonCanon);
      drillOk = F[g.dim].length === 1 && F[g.dim][0] === g.canon;
      FILT.forEach(([k]) => F[k] = []); onFilterChange();
    }

    // 6. case/space variants of a real Zone value resolve to that value
    const zone = optsFor('Zone')[0];
    const zoneVariants = zone ? [zone.toUpperCase(), zone.toLowerCase(), `  ${zone}  `] : [];
    const zoneOk = zoneVariants.every(v => normVal('Zone', v) === zone);

    // 7. FY / Month untouched
    const fyMonthRaw = normVal('FY', 'fy26') === 'fy26' && normVal('Month', ' april') === ' april';

    return { dupOpts, groups, partition, rawStillThere, drillOk, zone, zoneOk, fyMonthRaw,
             unfilteredCount: recFilter().length, recCount: REC.length };
  });

  check('test_no_duplicate_case_or_space_filter_options', Object.keys(r.dupOpts).length === 0, r.dupOpts);
  console.log(`  (real variant groups found in data: ${r.groups.length})`);
  r.groups.forEach(g => {
    const tag = `${g.dim}:${g.raws.map(v => JSON.stringify(v)).join('/')}`;
    check(`test_one_option_for ${tag}`, g.allSpellingsMapToOne && g.optionCount === 1, g);
    check(`test_same_rows_and_nsv ${tag}`, g.expRows === g.gotRows && g.expNsv === g.gotNsv, g);
  });
  check('test_nsv_partition_totals_unchanged', r.partition.every(p => p.ok), r.partition);
  check('test_unfiltered_record_count_unchanged', r.unfilteredCount === r.recCount, [r.unfilteredCount, r.recCount]);
  check('test_raw_records_not_mutated', r.rawStillThere);
  check('test_drill_stores_canonical_value', r.drillOk);
  check('test_zone_case_space_variants_collapse', r.zoneOk, r.zone);
  check('test_fy_and_month_left_as_is', r.fyMonthRaw);
  check('test_no_page_errors', errs.length === 0, errs);

  console.log(`\n  filter-value-normalisation tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
