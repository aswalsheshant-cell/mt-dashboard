// Month dropdown must follow the selected FY (THE ONE FY RULE): only months that
// really exist for that FY are offered, and a month the FY does not have is dropped.
// Needs the dashboard served at 127.0.0.1:$SWEEP_PORT (default 8899).
const { launchChromium } = require('./browser_launch');

(async () => {
  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && typeof optsFor === 'function', { timeout: 30000 });

  let pass = 0, fail = 0;
  const check = (n, c, d) => { if (c) { pass++; console.log('  PASS ' + n); } else { fail++; console.log('  FAIL ' + n + (d !== undefined ? ' -- ' + JSON.stringify(d) : '')); } };
  const m3 = a => a.map(x => String(x).slice(0, 3).toLowerCase());

  const r = await pg.evaluate(() => {
    const out = {};
    const sel = (fy, months) => { F.FY = fy; F.Month = months || []; onFilterChange(); };
    sel([]);                       out.none = optsFor('Month');
    sel(['FY27']);                 out.fy27 = optsFor('Month');
    sel(['FY26']);                 out.fy26 = optsFor('Month');
    sel(['FY26', 'FY27']);         out.both = optsFor('Month');
    sel(['FY26'], ['January']);    out.keepJan = F.Month.slice();
    sel(['FY27']);                 // January is not an FY27 month -> must be dropped
    F.Month = ['January', 'May'];  onFilterChange();
    out.pruned = F.Month.slice();
    sel(['FY99']);                 out.unknownFy = optsFor('Month');
    sel([]);
    // data truth: every FY27 record month is in the FY27 option list
    out.recFy27 = [...new Set(REC.filter(x => x.FY === 'FY27').map(x => x.Month))];
    return out;
  });

  check('no FY selected -> all months offered', r.none.length >= 12, r.none);
  check('FY27 -> only months that exist (Apr-Aug)', JSON.stringify(m3(r.fy27)) === JSON.stringify(['apr', 'may', 'jun', 'jul', 'aug']), r.fy27);
  check('FY26 -> all 12 months', r.fy26.length === 12, r.fy26);
  check('FY26+FY27 -> union (12)', r.both.length === 12, r.both);
  check('month valid for FY is kept', r.keepJan.length === 1 && r.keepJan[0] === 'January', r.keepJan);
  check('month not in FY27 is dropped, valid one kept', JSON.stringify(r.pruned) === JSON.stringify(['May']), r.pruned);
  check('FY with no months -> empty list (no invented months)', r.unknownFy.length === 0, r.unknownFy);
  check('every FY27 record month is offered under FY27', r.recFy27.every(x => m3(r.fy27).includes(String(x).slice(0, 3).toLowerCase())), { rec: r.recFy27, opts: r.fy27 });
  check('no JS errors', errs.length === 0, errs);

  console.log(`\n  month-follows-fy tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
