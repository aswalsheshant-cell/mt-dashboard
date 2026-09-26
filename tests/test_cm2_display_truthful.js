// CM2 must not look like a calculated margin when expenses are missing.
//
// Found 2026-09-26 on main 4f85622 (data.js: cm2.has_expense_data = false,
// total_expense = 0): the P&L tab's "No expense data" banner showed, but the
// KPI card still read CM2 Value = NSV / 100% of NSV, every chain row read
// CM2% 100%, and the chart drew NSV as "CM2 Value". The same happened for an FY
// with no expense rows even when another FY had some, and a partial expense
// load (e.g. MT Direct DN claims only) said nothing about which cost buckets
// were missing once expenses passed 5% of NSV.
//
// Scenario 1 uses the committed data.js as is. Scenario 2 injects a small
// partial-expense cm2 block in the browser only (never written to disk).
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && !!D.cm2 && typeof buildPnl === 'function', { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  const r = await pg.evaluate(() => {
    const cm2Section = () => {
      const t = document.getElementById('tab-pnl').innerText;
      const i = t.indexOf('P&L / CM2');
      return i < 0 ? '' : t.slice(i);
    };
    const kpiVal = (_txt, label) => {   // DOM, not innerText: .kpi .lab is CSS-uppercased
      const k = [...document.querySelectorAll('#tab-pnl .kpi')].find(el => el.querySelector('.lab').textContent.trim() === label);
      return k ? k.querySelector('.val').textContent.trim() : null;
    };
    const cm2Chart = () => charts.find(c => c.canvas && c.canvas.id === 'cm2Chart') || null;
    const tableCm2Pct = () => [...document.querySelectorAll('#tab-pnl table')]
      .find(t => /CM2%/.test(t.tHead ? t.tHead.innerText : ''));
    const pctCells = () => { const t = tableCm2Pct(); return t ? [...t.tBodies[0].rows].map(tr => tr.cells[4] && tr.cells[4].innerText.trim()) : []; };
    const snap = (fy) => {
      F.FY = fy ? [fy] : []; buildPnl();
      const s = cm2Section();
      return { fy: fy || 'all', cm2: kpiVal(s, 'CM2 Value'), exp: kpiVal(s, 'Total P&L Expense'),
               has100: /100(\.0)?% of NSV/.test(s), banner: /No expense data loaded/.test(s),
               partial: /Partial cost coverage/.test(s), text: s.slice(0, 1500),
               chart: !!cm2Chart(), pcts: pctCells() };
    };
    const out = { real: [], partial: [] };
    const fys = [...new Set((D.cm2.monthly || []).map(m => m.fy))];
    out.fys = fys;
    out.realHasExpense = !!D.cm2.has_expense_data;
    for (const fy of [null, ...fys]) out.real.push(snap(fy));

    // Scenario 2: partial expenses in the LAST covered FY only, on one chain.
    const orig = D.cm2;
    const c = JSON.parse(JSON.stringify(orig));
    const fyE = fys[fys.length - 1];
    let first = true;
    c.monthly = c.monthly.map(m => {
      if (m.fy === fyE && first) { first = false; return Object.assign({}, m, { expense: 50, cm2_value: m.nsv - 50, cm2_pct: Math.round((m.nsv - 50) / m.nsv * 1000) / 10 }); }
      return m;
    });
    const top = c.by_chain.slice().sort((a, b2) => b2.nsv - a.nsv)[0];
    c.by_chain = c.by_chain.map(ch => ch.name === top.name
      ? Object.assign({}, ch, { expense: 50, cm2_value: ch.nsv - 50, cm2_pct: Math.round((ch.nsv - 50) / ch.nsv * 1000) / 10 }) : ch);
    c.by_expense_head = [{ name: 'Promotion', amount: 30 }, { name: 'Visibility', amount: 20 }];
    Object.assign(c, { has_expense_data: true, total_expense: 50, cm2_value: c.total_nsv - 50,
                       cm2_pct: Math.round((c.total_nsv - 50) / c.total_nsv * 1000) / 10,
                       expense_pct_of_nsv: Math.round(50 / c.total_nsv * 1000) / 10 });
    D.cm2 = c;
    out.fyE = fyE; out.topChain = top.name;
    for (const fy of [null, ...fys]) out.partial.push(snap(fy));
    D.cm2 = orig; F.FY = []; buildPnl();
    return out;
  });

  // Scenario 1: no expense data (the committed data.js today).
  check('committed data.js has no expense data (precondition)', r.realHasExpense === false, r.realHasExpense);
  for (const s of r.real) {
    check(`no data, FY=${s.fy}: CM2 Value card shows – not a number`, s.cm2 === '–', s.cm2);
    check(`no data, FY=${s.fy}: no "100% of NSV"`, !s.has100, s.text.slice(0, 400));
    check(`no data, FY=${s.fy}: banner kept`, s.banner);
    check(`no data, FY=${s.fy}: no CM2 chart drawn from NSV`, !s.chart);
    check(`no data, FY=${s.fy}: chain CM2% column all –`, s.pcts.length > 0 && s.pcts.every(p => p === '–'), s.pcts.slice(0, 5));
  }
  // Scenario 2: partial expenses (one FY, one chain, two heads).
  for (const s of r.partial) {
    const inScope = s.fy === 'all' || s.fy === r.fyE;
    check(`partial, FY=${s.fy}: partial-coverage note names the loaded heads`,
          s.partial && /Promotion/.test(s.text) && /Visibility/.test(s.text), s.text.slice(0, 600));
    if (inScope) {
      check(`partial, FY=${s.fy}: CM2 Value is a real figure`, s.cm2 && s.cm2 !== '–', s.cm2);
      check(`partial, FY=${s.fy}: chart drawn`, s.chart);
    } else {
      check(`partial, FY=${s.fy} (no expense rows in this FY): CM2 Value shows –`, s.cm2 === '–', s.cm2);
      check(`partial, FY=${s.fy}: no "100% of NSV"`, !s.has100, s.text.slice(0, 400));
    }
    check(`partial, FY=${s.fy}: chains with no expense rows show CM2% –, not 100%`,
          s.pcts.filter(p => p !== '–').length === 1 && !s.pcts.includes('100%'), s.pcts.slice(0, 5));
  }
  check('no JS errors', errs.length === 0, errs.slice(0, 3));
  console.log(`\n  cm2-display-truthful tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail ? 1 : 0);
})();
