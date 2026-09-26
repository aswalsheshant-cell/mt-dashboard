// Regression test for F17 (docs/PHASE_2B_FINANCIAL_CONSUMER_INVENTORY.md
// follow-up sweep, 2026-09-25): buildPnl() used to hardcode the literal
// string 'FY26' for its gate/labels instead of reading pnl_block()'s own
// real `fy_tag` field. Dormant today (the P&L source hasn't been extended
// past FY26 yet), but proven here directly so a future extension doesn't
// silently keep gating/labelling everything as FY26.
//
// Also proves the related D.pnl defensive-default fix: the old default
// ({chains:[],totals:{},blended:{}}) never matched pnl_block()'s real shape
// ({by_chain,fy_tag,...}) -- a structural check on the source text, since
// D.pnl is always present in the real data.js and the init-time default
// assignment can't be exercised live without deleting D.pnl before page
// load runs its own init IIFE.
const fs = require('fs');
const { launchChromium } = require('./browser_launch');   // PW_CHROMIUM_PATH -> bundled -> PLAYWRIGHT_BROWSERS_PATH

(async () => {
  const b = await launchChromium();
  const pg = await b.newPage();
  const errs = [];
  pg.on('pageerror', e => errs.push('PAGEERROR: ' + e.message));
  await pg.goto(`http://127.0.0.1:${process.env.SWEEP_PORT || 8899}/index.html`, { waitUntil: 'load' });
  await pg.waitForFunction(() => typeof D !== 'undefined' && !!D.pnl, { timeout: 30000 });

  let pass = 0, fail = 0;
  function check(name, cond, detail) {
    if (cond) { pass++; console.log(`  PASS ${name}`); }
    else { fail++; console.log(`  FAIL ${name}${detail !== undefined ? ' -- ' + JSON.stringify(detail) : ''}`); }
  }

  // Structural check: the D.pnl defensive default must match pnl_block()'s
  // real return shape (by_chain, fy_tag), not the old, wrong (chains,
  // totals, blended) shape that would crash buildPnl()'s chains.filter().
  const src = fs.readFileSync('/home/user/mt-dashboard/dashboard/index.html', 'utf8');
  const defaultLineMatch = src.match(/D\.pnl\s*=\s*D\.pnl\s*\|\|\s*(\{[^;]*\});/);
  check('test_pnl_default_shape_uses_by_chain_not_chains',
    !!defaultLineMatch && /by_chain\s*:\s*\[\]/.test(defaultLineMatch[1]) && !/\bchains\s*:/.test(defaultLineMatch[1]),
    defaultLineMatch && defaultLineMatch[1]);
  check('test_pnl_default_shape_includes_fy_tag',
    !!defaultLineMatch && /fy_tag\s*:\s*null/.test(defaultLineMatch[1]),
    defaultLineMatch && defaultLineMatch[1]);

  const result = await pg.evaluate(() => {
    const savedPnl = D.pnl;
    D.pnl = { ...savedPnl, fy_tag: 'FY27' };
    buildPnl();
    const htmlFy27Tag = document.getElementById('tab-pnl').innerHTML;

    D.pnl = { ...savedPnl, fy_tag: 'FY26' };
    buildPnl();
    const htmlFy26Tag = document.getElementById('tab-pnl').innerHTML;

    D.pnl = savedPnl;
    buildPnl(); // restore real render

    return { htmlFy27Tag, htmlFy26Tag };
  });

  check('test_fy_tag_fy27_renders_fy27_not_hardcoded_fy26',
    result.htmlFy27Tag.includes('FY27') && !/Gross-to-net by chain \(FY26\)/.test(result.htmlFy27Tag),
    result.htmlFy27Tag.slice(0, 500));
  check('test_fy_tag_fy26_still_renders_fy26',
    /Gross-to-net by chain \(FY26\)/.test(result.htmlFy26Tag),
    result.htmlFy26Tag.slice(0, 500));
  check('test_fy27_and_fy26_tag_render_differently',
    result.htmlFy27Tag !== result.htmlFy26Tag, {});

  check('test_no_js_errors', errs.length === 0, errs);

  console.log(`\n  pnl-dynamic-fy-label tests: ${pass} passed, ${fail} failed`);
  await b.close();
  process.exit(fail || errs.length ? 1 : 0);
})();
