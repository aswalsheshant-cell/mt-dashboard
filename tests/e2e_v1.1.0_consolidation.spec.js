import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

const ARTIFACT_DIR = path.resolve(process.cwd(), 'qc-artifacts/v1.1.0-e2e');
// This spec was never actually executed before (see PR description) — its
// BASE_URL was hardcoded to a port (3000) nothing in this repo serves on.
// Align it with the convention already used by playwright.config.js and
// the CI server (both default to 8765), overridable via env for local runs.
const BASE_URL = `${process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8765'}/dashboard/index.html`;

// 11 Canonical tabs post-Issue #105
const CONSOLIDATED_TABS = [
  { id: 'explorer', name: 'Data Explorer', hasSubviews: false },
  { id: 'executive-cockpit', name: 'Executive Cockpit', hasSubviews: false },
  {
    id: 'channel-dynamics',
    name: 'Channel & Chain Performance',
    hasSubviews: true,
    subviews: ['primary', 'category', 'reliance']
  },
  {
    id: 'inventory-health',
    name: 'Inventory & Supply Health',
    hasSubviews: true,
    subviews: ['velocity', 'gap', 'coverage']
  },
  {
    id: 'demand-planning',
    name: 'Demand & S&OP Planning',
    hasSubviews: true,
    subviews: ['forecast', 'promo', 'market-share']
  },
  { id: 'pnl', name: 'P&L', hasSubviews: false },
  { id: 'comparison', name: 'Performance & Comparison', hasSubviews: false },
  { id: 'analytics', name: 'Commercial Analytics', hasSubviews: false },
  { id: 'alerts', name: 'Operational Alerts', hasSubviews: false },
  { id: 'stores', name: 'Store Audit Scorecard', hasSubviews: false },
  { id: 'inventory', name: 'Supply Chain & Inventory', hasSubviews: false }
];

// FY states exercised across the full tab traversal (Part B item 4)
const FY_STATES = ['', 'FY26', 'FY27'];
const FY_LABEL = (fy) => fy || 'All';

// All 12 legacy tab IDs redirected by LEGACY_TAB_ROUTES (Guardrail #1).
//
// IMPORTANT: `show(id)` only ever redirects the TOP-LEVEL tab id — it does
// NOT set any subview state based on which legacy id was used (verified
// empirically: channelDynamicsState/inventoryHealthState/demandPlanningState
// stay at their defaults — 'primary'/'velocity'/'forecast' — regardless of
// which legacy id redirected into that tab). So this table only asserts the
// one thing LEGACY_TAB_ROUTES actually guarantees: which top-level tab an
// old id lands on. A prior version of this table also asserted a specific
// active subview per legacy id; that assumption did not hold against the
// real app and was never caught because this spec was never wired into CI.
const LEGACY_ROUTES = [
  { legacy: 'overview', expectedTab: 'executive-cockpit' },
  { legacy: 'insights', expectedTab: 'executive-cockpit' },
  { legacy: 'primary', expectedTab: 'channel-dynamics' },
  { legacy: 'category', expectedTab: 'channel-dynamics' },
  { legacy: 'reliance-bc', expectedTab: 'channel-dynamics' },
  { legacy: 'offtake', expectedTab: 'inventory-health' },
  { legacy: 'offtake-impact', expectedTab: 'inventory-health' },
  { legacy: 'distribution', expectedTab: 'inventory-health' },
  { legacy: 'forecast', expectedTab: 'demand-planning' },
  { legacy: 'promo', expectedTab: 'demand-planning' },
  { legacy: 'market-share', expectedTab: 'demand-planning' },
  // 'share' was the REAL pre-consolidation top-level tab id (the removed
  // TABS entry was ['share','Market Share']) — LEGACY_TAB_ROUTES was
  // missing it until PR #112/#109-era fixes. Keep it in this table so a
  // future regression here fails CI instead of going unnoticed again.
  { legacy: 'share', expectedTab: 'demand-planning' },
];

test.beforeAll(() => {
  if (!fs.existsSync(ARTIFACT_DIR)) {
    fs.mkdirSync(ARTIFACT_DIR, { recursive: true });
  }
});

// Shared rendering-guard assertion: no NaN / undefined / Infinity /
// [object Object] anywhere in the given body text.
function assertCleanBodyText(bodyText, context) {
  expect(bodyText, `${context}: NaN leaked into rendered text`).not.toContain('NaN');
  expect(bodyText, `${context}: undefined leaked into rendered text`).not.toContain('undefined');
  expect(bodyText, `${context}: Infinity leaked into rendered text`).not.toContain('Infinity');
  expect(bodyText, `${context}: [object Object] leaked into rendered text`).not.toContain('[object Object]');
}

test.describe('v1.1.0 Navigation Consolidation E2E Suite', () => {
  let consoleErrors = [];

  test.beforeEach(async ({ page }) => {
    consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') consoleErrors.push(msg.text());
    });
    page.on('pageerror', err => consoleErrors.push(err.message));
  });

  // TEST 1: Legacy Routing & Backward Compatibility (Guardrail #1)
  test('TC01 - Legacy Tab Redirection Engine (all 12 routes)', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    for (const route of LEGACY_ROUTES) {
      const info = await page.evaluate((legacyId) => {
        window.show(legacyId);
        // currentTab is declared with top-level `let` in index.html, which
        // does NOT attach to window (only `function` declarations and
        // explicit window.x= assignments do) — reference it as a bare
        // identifier, resolved via the page's shared script scope.
        // eslint-disable-next-line no-undef
        return { currentTab: currentTab };
      }, route.legacy);

      await page.waitForTimeout(300);

      // The original legacy id passed to show() is preserved in
      // window.currentTab even after the internal redirect.
      expect(info.currentTab, `show('${route.legacy}') should set currentTab`).toBe(route.legacy);

      // Verify the canonical (redirected) tab section is the one visible.
      const activeSection = page.locator(`section#tab-${route.expectedTab}`);
      await expect(activeSection, `'${route.legacy}' should redirect to '${route.expectedTab}'`).toBeVisible();
    }

    expect(consoleErrors.length).toBe(0);
  });

  // TEST 1b: dedicated, explicit assertion for the 'share' legacy route —
  // the id that LEGACY_TAB_ROUTES was historically missing.
  test("TC01b - Legacy route 'share' resolves to Demand & S&OP Planning", async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    await page.evaluate(() => window.show('share'));
    await page.waitForTimeout(300);

    await expect(page.locator('section#tab-demand-planning')).toBeVisible();
    const bodyText = await page.locator('section#tab-demand-planning').innerText();
    assertCleanBodyText(bodyText, "show('share')");
    expect(consoleErrors.length).toBe(0);
  });

  // TEST 2: All 11 Tabs Mount Cleanly Under Every FY State
  for (const fy of FY_STATES) {
    test(`TC02 - 11 Canonical Tabs Traversal & Visual Proof (FY=${FY_LABEL(fy)})`, async ({ page }) => {
      await page.goto(BASE_URL, { waitUntil: 'networkidle' });

      const fySelect = page.locator('#filter-FY');
      if (await fySelect.count()) {
        await fySelect.selectOption(fy).catch(() => {});
        await page.waitForTimeout(200);
      }

      for (let i = 0; i < CONSOLIDATED_TABS.length; i++) {
        const tab = CONSOLIDATED_TABS[i];

        await page.evaluate((tabId) => window.show(tabId), tab.id);
        await page.waitForTimeout(600); // Allow Chart.js / SVG layout to settle

        const section = page.locator(`section#tab-${tab.id}`);
        await expect(section).toBeVisible();

        const bodyText = await section.innerText();
        assertCleanBodyText(bodyText, `FY=${FY_LABEL(fy)} / tab=${tab.id}`);

        if (fy === '') {
          // Screenshot only once (All-FY pass) to keep the suite fast.
          const screenshotPath = path.join(
            ARTIFACT_DIR,
            `tab_${String(i + 1).padStart(2, '0')}_${tab.id}.png`
          );
          await page.screenshot({ path: screenshotPath, fullPage: true });
        }
      }

      expect(consoleErrors.length).toBe(0);
    });
  }

  // TEST 3: Canvas Lifecycle & Chart Teardown (Guardrail #3)
  test('TC03 - Sub-View Canvas Lifecycle & Memory Cleanup', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    const multiViewTabs = CONSOLIDATED_TABS.filter(t => t.hasSubviews);

    for (const tab of multiViewTabs) {
      await page.evaluate((tabId) => window.show(tabId), tab.id);

      for (const subview of tab.subviews) {
        // Trigger sub-view transition. channel-dynamics' subview buttons
        // are wired via a data-subview attribute + a JS-assigned .onclick
        // property (see buildChannelDynamics), NOT an onclick="..." HTML
        // attribute like inventory-health/demand-planning use — so the
        // selector must branch per tab or it silently never matches.
        const pillSelector = tab.id === 'channel-dynamics'
          ? `#tab-${tab.id} .subview-tab[data-subview="${subview}"]`
          : `#tab-${tab.id} .subview-tab[onclick*="'${subview}'"]`;
        const pill = page.locator(pillSelector);
        await pill.click();
        await page.waitForTimeout(500);

        // Verify active status. Issue #114 (fixed): buildChannelDynamics()'s
        // click handler previously updated state and re-rendered content
        // correctly but never toggled the .active class on the clicked
        // button, unlike switchInventorySubview/switchDemandSubview. Now
        // mirrors that same pattern, so this assertion is unconditional
        // across all 9 subviews / all 3 consolidated tabs.
        const hasActive = await pill.evaluate(el => el.classList.contains('active')).catch(() => false);
        expect(hasActive, `${tab.id}/${subview} pill should be .active after click`).toBeTruthy();

        // NOTE: deliberately NOT asserting a chart-canvas count here.
        // channel-dynamics' 'category'/'reliance' subviews and
        // demand-planning's 'market-share' subview are chart-less by
        // design (table/card content only — confirmed in source: no
        // mkBar/mkDonut/mkLine/new Chart call exists in those branches,
        // and market-share explicitly has no data source to chart at
        // all). A per-subview chart-count invariant doesn't hold across
        // all 9 subviews, so the meaningful, universally-true regression
        // signal is that the subview's own section renders visibly with
        // clean content — asserted below.
        const bodyText = await page.locator(`section#tab-${tab.id}`).innerText();
        assertCleanBodyText(bodyText, `subview ${tab.id}/${subview}`);
        expect(bodyText.trim().length, `subview ${tab.id}/${subview} rendered empty content`).toBeGreaterThan(0);

        // Screenshot sub-view
        await page.screenshot({
          path: path.join(ARTIFACT_DIR, `subview_${tab.id}_${subview}.png`),
          fullPage: true
        });
      }
    }

    expect(consoleErrors.length).toBe(0);
  });

  // TEST 4: Asymmetric Timeline Data Boundary (Guardrail #2)
  test('TC04 - August 2026 Asymmetric Data Boundary Safeguard', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    // Switch to Inventory Health
    await page.evaluate(() => window.show('inventory-health'));
    await page.waitForTimeout(400);

    const periodCheck = await page.evaluate(() => {
      const data = window.DASH || {};
      if (!data.offtake) return { ok: false, error: 'Offtake data unavailable' };
      return {
        ok: true,
        hasMetrics: !!data.offtake.metrics,
        totalExists: !!data.offtake.total
      };
    });

    expect(periodCheck.ok).toBe(true);
    expect(periodCheck.hasMetrics || periodCheck.totalExists).toBe(true);
  });

  // TEST 5: Filter State Isolation (Guardrail #4)
  test('TC05 - Filter Encapsulation Across Sub-Views', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    // Navigate to Channel Dynamics and switch sub-views
    await page.evaluate(() => window.show('channel-dynamics'));

    // channel-dynamics subview buttons use data-subview, not onclick="..."
    // (see the pillSelector note in TC03) — 'reliance', not 'reliance-bc',
    // is the actual subview id (CONSOLIDATED_TABS.channel-dynamics.subviews).
    const primaryPill = page.locator('#tab-channel-dynamics .subview-tab[data-subview="primary"]');
    const reliancePill = page.locator('#tab-channel-dynamics .subview-tab[data-subview="reliance"]');
    await reliancePill.click();
    await page.waitForTimeout(400);

    // Issue #114 (fixed): the previously-active pill (Primary Sales, the
    // default subview) must lose .active, and the clicked one must gain it.
    expect(await reliancePill.evaluate(el => el.classList.contains('active'))).toBeTruthy();
    expect(await primaryPill.evaluate(el => el.classList.contains('active'))).toBeFalsy();

    // Verify section is still mounted
    const section = page.locator('section#tab-channel-dynamics');
    await expect(section).toBeVisible();
  });

  // TEST 6: Browser Console Health (Guardrail #3)
  test('TC06 - Zero Critical Errors Across All Tabs', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    const allErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') allErrors.push({ type: 'console', text: msg.text() });
    });
    page.on('pageerror', err => {
      allErrors.push({ type: 'uncaught', text: err.message });
    });

    // Traverse all tabs
    for (const tab of CONSOLIDATED_TABS) {
      await page.evaluate((tabId) => window.show(tabId), tab.id);
      await page.waitForTimeout(400);
    }

    // Verify zero critical errors
    expect(allErrors.length).toBe(0);
  });

  // TEST 7: Navigation Architecture Consistency — derived from the app's own
  // runtime objects rather than a second hardcoded copy, so a future drift
  // between TABS / LEGACY_TAB_ROUTES / this spec's expectations is caught
  // even if nobody remembers to update a parallel list by hand.
  test('TC07 - TABS count and LEGACY_TAB_ROUTES targets stay consistent', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    // TABS and LEGACY_TAB_ROUTES are top-level `const` bindings in
    // index.html — not window properties (see the currentTab note in
    // TC01) — reference them bare via the page's shared script scope.
    const arch = await page.evaluate(() => {
      /* eslint-disable no-undef */
      return {
        tabsLength: typeof TABS !== 'undefined' ? TABS.length : null,
        tabIds: typeof TABS !== 'undefined' ? TABS.map(t => t[0]) : [],
        legacyTargets: typeof LEGACY_TAB_ROUTES !== 'undefined' ? Object.values(LEGACY_TAB_ROUTES) : [],
        legacyKeys: typeof LEGACY_TAB_ROUTES !== 'undefined' ? Object.keys(LEGACY_TAB_ROUTES) : [],
      };
      /* eslint-enable no-undef */
    });

    expect(arch.tabsLength, 'TABS must have exactly 11 top-level entries').toBe(11);

    // Every CONSOLIDATED_TABS id this spec exercises must actually be a
    // live tab id — catches this spec drifting from the app, not just the
    // other way around.
    for (const tab of CONSOLIDATED_TABS) {
      expect(arch.tabIds, `expected tab id '${tab.id}' missing from live TABS`).toContain(tab.id);
    }

    // Every legacy route target must resolve to one of the 11 current tabs
    // — never to a removed/renamed id.
    for (const target of arch.legacyTargets) {
      expect(arch.tabIds, `LEGACY_TAB_ROUTES target '${target}' is not a live tab id`).toContain(target);
    }

    // Every legacy id this spec expects to exist must actually be present
    // in the live LEGACY_TAB_ROUTES (catches 'share' regressing again).
    for (const route of LEGACY_ROUTES) {
      expect(arch.legacyKeys, `LEGACY_TAB_ROUTES is missing expected legacy id '${route.legacy}'`).toContain(route.legacy);
    }
  });

  // TEST 8: Critical business-data regressions fixed this session — cheap
  // structural checks, not fragile value/snapshot tests. These are exactly
  // the two bugs (VMM chain-naming, Central zone data loss) found and fixed
  // via manual investigation before this suite existed; from here on they
  // fail CI automatically instead of requiring another manual audit.
  test('TC08 - Critical business-data structural regressions', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });

    const dash = await page.evaluate(() => {
      const D = window.DASH || {};
      return {
        primaryChainNames: (D.primary?.by_chain || []).map(c => c.name),
        offtakeZoneNames: (D.offtake?.by_zone || []).map(z => z.name),
        universeActiveStores: D.universe?.active_stores,
        fcLabelsLen: (D.forecast?.fc_labels || []).length,
        momChainScorecard: Array.isArray(D.mom_chain_scorecard) ? D.mom_chain_scorecard : null,
        forecastDiagnostics: D.forecast?.diagnostics || null,
      };
    });

    // VMM chain-naming regression (fixed in PR #109): 'VMM' must appear as
    // its own canonical chain in primary.by_chain — never as a bare
    // "Vishal Mega Mart" / missing / merged-into-another-chain entry.
    expect(dash.primaryChainNames, "DASH.primary.by_chain must contain a chain named 'VMM'")
      .toContain('VMM');
    expect(dash.primaryChainNames, "'Vishal Mega Mart' must not reappear as a separate chain name")
      .not.toContain('Vishal Mega Mart');

    // Central zone offtake regression (fixed in PR #108): 'Central' must
    // exist as its own zone in offtake.by_zone.
    expect(dash.offtakeZoneNames, "DASH.offtake.by_zone must contain a zone named 'Central'")
      .toContain('Central');

    // MT Universe baseline (CLAUDE.md: 426 active stores).
    expect(typeof dash.universeActiveStores).toBe('number');
    expect(dash.universeActiveStores).toBeGreaterThan(0);

    // Forecast series must always be a 12-month curve.
    expect(dash.fcLabelsLen).toBe(12);

    // The two structural checks below are only meaningful once a full data
    // rebuild has populated these optional blocks — ported from the
    // (now-retired) tests/test_dashboard_ui.py, which treated their absence
    // as a skip rather than a failure. Preserve that semantic here.
    if (dash.momChainScorecard) {
      expect(dash.momChainScorecard.length).toBeGreaterThan(0);
      const required = ['chain', 'apr_lakh', 'may_lakh', 'jun_lakh', 'trajectory'];
      const actual = Object.keys(dash.momChainScorecard[0]);
      for (const key of required) {
        expect(actual, `mom_chain_scorecard[0] missing key '${key}'`).toContain(key);
      }
    }

    if (dash.forecastDiagnostics) {
      const required = ['n_calibrated_months', 'mape_pct', 'bias_pct', 'mae_lakh'];
      const actual = Object.keys(dash.forecastDiagnostics);
      for (const key of required) {
        expect(actual, `forecast.diagnostics missing key '${key}'`).toContain(key);
      }
    }
  });

  // TEST 9: Issue #114 fix — Channel & Chain Performance active-pill sync.
  // Dedicated, explicit coverage (beyond TC03's generic per-subview loop)
  // for the exact defect reported: clicking a subview changed content but
  // never moved the .active class off the previously-selected pill. Asserts
  // the visible DOM class directly, not just internal state, because the
  // DOM class was the actual bug.
  test('TC09 - Channel & Chain Performance subview pills sync .active on click', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    await page.evaluate(() => window.show('channel-dynamics'));
    await page.waitForTimeout(400);

    const pillFor = (sv) => page.locator(`#tab-channel-dynamics .subview-tab[data-subview="${sv}"]`);
    const order = ['primary', 'category', 'reliance', 'primary'];

    // Primary Sales is the default subview — verify it starts active before
    // any click, so the first transition below has a real "previous" to
    // check losing .active from.
    expect(await pillFor('primary').evaluate(el => el.classList.contains('active'))).toBeTruthy();

    for (let i = 1; i < order.length; i++) {
      const previous = order[i - 1];
      const current = order[i];

      await pillFor(current).click();
      await page.waitForTimeout(400);

      const state = await Promise.all([
        pillFor(current).evaluate(el => el.classList.contains('active')),
        pillFor(previous).evaluate(el => el.classList.contains('active')),
        page.evaluate(() => channelDynamicsState.subview),
      ]);
      const [currentActive, previousStillActive, stateSubview] = state;

      expect(currentActive, `${current} pill should become .active after click`).toBeTruthy();
      expect(previousStillActive, `${previous} pill should lose .active once ${current} is selected`).toBeFalsy();
      expect(stateSubview, 'channelDynamicsState.subview should track the clicked pill').toBe(current);

      // Exactly one pill active at a time, across all three.
      const allActive = await page.$$eval('#tab-channel-dynamics .subview-tab.active', els => els.map(e => e.dataset.subview));
      expect(allActive, 'exactly one subview-tab should carry .active').toEqual([current]);

      // Content still renders correctly, and cleanly.
      const bodyText = await page.locator('#channel-subview-content').innerText();
      expect(bodyText.trim().length, `${current} subview content should not be empty`).toBeGreaterThan(0);
      assertCleanBodyText(bodyText, `channel-dynamics/${current}`);
    }

    expect(consoleErrors.length, 'no console/page errors during subview switching').toBe(0);
  });

  // TC10 - 2026-09-15 fix: two confirmed-wrong dashboard values found in live
  // QA. (a) Inventory & Supply Health -> Offtake Velocity's "Top Chains by
  // Offtake" table showed every chain with 0 stores (reading offtake.by_chain's
  // nonexistent by_month field) and a steep negative "Growth %" for every
  // chain (naively comparing FY27's 5-month partial year against FY26's full
  // 12 months -- a coverage-window artifact, not a real decline; the same
  // chains correctly show +91-158% like-for-like growth elsewhere on this
  // dashboard for the identical period). (b) Demand & S&OP Planning's
  // "TY Target (FY27)" KPI read a forecast field (f.ty_target) that never
  // existed, showing Rs 0 L right above a Zone table that correctly cascades
  // the real Rs 441.33 Cr target.
  test('TC10 - Offtake Velocity real store counts + honest partial-year growth, TY Target not zero', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    // F is a top-level `const` in index.html, not a window property (classic
    // scripts don't hoist const/let onto window) -- window.F.FY is undefined
    // from the test's page context. The dashboard's own filter <select>,
    // used by every other test in this suite (see TC02), is the real way to
    // drive the FY filter from outside the page.
    const fySelect = page.locator('#filter-FY');
    if (await fySelect.count()) {
      await fySelect.selectOption('FY27').catch(() => {});
      await page.waitForTimeout(200);
    }

    await page.evaluate(() => window.show('inventory-health'));
    await page.waitForTimeout(400);
    const velocityRows = await page.$$eval('#tab-inventory-health .tbl tbody tr', trs =>
      trs.map(tr => Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim())));
    expect(velocityRows.length, 'Top Chains by Offtake table should have rows').toBeGreaterThan(0);

    // Stores = real POS stores (distinct offtake Site Code) selling in the
    // FY's latest month, from offtake.pos_stores -- NOT universe.by_chain,
    // which counts Primary SAP billing codes (PR #256: DMart showed 24 billing
    // codes instead of 507 stores). Exact match, rendered en-IN, '*' suffix
    // where part of the chain's offtake has no Site Code.
    const pos = await page.evaluate(() => {
      const o = window.DASH?.offtake || {};
      const fyTags = o.fy_tags || [];
      const fyR = fyTags[fyTags.length - 1] || 'fy26';
      return (o.pos_stores && o.pos_stores[fyR]) || null;
    });
    expect(pos, 'test premise: offtake.pos_stores must exist for the latest FY').toBeTruthy();
    const knownStoreChain = Object.entries(pos.by_chain).find(([, v]) => v.latest > 0);
    expect(knownStoreChain, 'test premise: pos_stores needs at least one chain with real stores').toBeTruthy();
    for (const [name, ps] of Object.entries(pos.by_chain)) {
      const matchedRow = velocityRows.find(([n]) => n === name);
      if (!matchedRow) continue;
      // Column order: Chain, In store master, Stores, Offtake (Cr), Growth %  ("In store master" was added next to Stores)
      const expected = ps.latest == null ? '–'
        : ps.latest.toLocaleString('en-IN') + (ps.no_site_pct > 0 ? '*' : '');
      expect(matchedRow[2], `${name}'s Stores column must be its real POS store count (offtake.pos_stores), not SAP billing codes`)
        .toBe(expected);
    }
    // No row may show a fabricated-looking negative/positive Growth % computed
    // from mismatched FY month coverage -- either a genuine like-for-like
    // number or an honest "–", never a raw full-year-vs-partial-year ratio.
    const currMonths = await page.evaluate(() => {
      const o = window.DASH?.offtake || {};
      const fyTags = o.fy_tags || [];
      const fyR = fyTags[fyTags.length - 1] || 'fy26';
      const priorFy = 'fy' + String(parseInt(fyR.slice(2), 10) - 1).padStart(2, '0');
      return { curr: (o['months_' + fyR] || []).length, prior: (o['months_' + priorFy] || []).length };
    });
    if (currMonths.curr !== currMonths.prior) {
      for (const row of velocityRows) {
        expect(row[4], `Growth % must be "–" (not a coverage-mismatch artifact) for ${row[0]} when FY windows differ`).toBe('–');
      }
    }

    await page.evaluate(() => window.show('demand-planning'));
    await page.waitForTimeout(400);
    const tyTargetText = await page.locator('#tab-demand-planning .kpi-card').first().locator('.kpi-value').innerText();
    const forecastTarget = await page.evaluate(() => window.DASH?.forecast?.fy27_forecast);
    expect(forecastTarget, 'test premise: forecast.fy27_forecast must exist and be positive').toBeGreaterThan(0);
    expect(tyTargetText, 'TY Target (FY27) KPI must not read as Rs 0 L when forecast.fy27_forecast is real')
      .not.toMatch(/^(Rs\s*0(\.0)?\s*L|₹0(\.0)?\s*L)$/i);
  });
  // Found 2026-09-30 in dashboard QC: the Primary Sales Trend card read "FY25 to
  // FY27 trajectory" in every FY state while it plotted FY26 only, and the FY27
  // months (detail_meta.fyx_primary) were fetched but never drawn. The header
  // read "FY25–27 (140 zone-months)", a fixed count from a deprecated script.
  // The subtitle and header must describe the data actually plotted/loaded.
  test('TC11 - Primary Sales Trend label and header follow the plotted data (All/FY25/FY26/FY27)', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    const hdr = await page.locator('#hPeriod').innerText();
    expect(hdr, 'header must not carry a fixed zone-month count').not.toMatch(/zone-month/i);
    const fyx = await page.evaluate(() => window.DASH.detail_meta.fyx_primary.FY27);
    expect(hdr).toContain(`Primary through ${fyx.months_canon[fyx.months_canon.length - 1]}`);

    for (const fy of ['', 'FY25', 'FY26', 'FY27']) {
      const r = await page.evaluate(async (f) => {
        F.FY = f ? [f] : []; show('channel-dynamics');
        await new Promise(res => setTimeout(res, 900));
        const card = [...document.querySelectorAll('#channel-subview-content .card')]
          .find(c => /Primary Sales Trend/.test(c.innerText));
        const ch = Chart.getChart('chanPrimTrend');
        return { text: card ? card.innerText : '',
                 sets: ch ? ch.data.datasets.map(d => ({ label: d.label, n: d.data.filter(v => v != null).length,
                                                          sum: d.data.reduce((a, v) => a + (v || 0), 0) })) : [] };
      }, fy);
      const tag = fy || 'All';
      expect(r.text, `${tag}: no hard-coded FY range in the subtitle`).not.toContain('FY25 to FY27');
      for (const s of r.sets) expect(r.text, `${tag}: subtitle names every plotted series`).toContain(s.label);
      if (fy === 'FY25') {
        expect(r.sets.length, 'FY25: no Primary series (no FY25 billing extract in repo)').toBe(0);
        expect(r.text).toContain('No monthly Primary in source for FY25');
      } else {
        const want = fy ? [fy] : ['FY26', 'FY27'];
        expect(r.sets.map(s => s.label.slice(0, 4)), `${tag}: plotted FYs`).toEqual(want);
      }
      const s27 = r.sets.find(s => s.label.startsWith('FY27'));
      if (s27) {
        expect(s27.n, 'FY27 plots every month fyx_primary carries').toBe(fyx.months_canon.length);
        expect(Math.abs(s27.sum - fyx.nsv), 'FY27 series sums to fyx_primary.FY27.nsv').toBeLessThan(0.05);
      }
    }
  });
  // Dashboard QC 2026-10-01 (two independent review passes). Each check below
  // was a reproduced defect on main fba9b89.
  test('TC12 - Chart/table/filter QC regressions (trend months, promo chart, Reliance BC toggle, NPI, channel share, KPI styles)', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    const r = await page.evaluate(async () => {
      const W = ms => new Promise(res => setTimeout(res, ms));
      const out = {};
      // 1. Cockpit trend: primary keyed by calendar month, not array position.
      F.FY = []; show('executive-cockpit'); await W(900);
      const c = Chart.getChart('cockpitTrend'); const L = c.data.labels;
      const prim = c.data.datasets.find(d => /Primary/.test(d.label)).data;
      const fx = DASH.detail_meta.fyx_primary.FY27;
      out.trendApr26 = prim[L.indexOf(fx.months_canon[0])]; out.fx0 = fx.monthly_canon[0];
      out.trendSets = c.data.datasets.map(d => d.label);
      // 2. Promo scatter keeps its chart after the correlation card is added.
      show('demand-planning'); await W(700);
      document.querySelectorAll('#tab-demand-planning .subview-tab')[1].click(); await W(900);
      out.promoCharts = [...document.querySelectorAll('#tab-demand-planning canvas')].map(cv => !!Chart.getChart(cv));
      // 3. Reliance Brand Counter toggle switches the table.
      F.FY = ['FY27']; show('channel-dynamics'); await W(700);
      document.querySelectorAll('#tab-channel-dynamics .subview-tab')[2].click(); await W(700);
      document.getElementById('bcBABtn').click(); await W(200);
      out.bc = { macro: document.getElementById('bcMacroView').style.display, ba: document.getElementById('bcBAView').style.display,
                 txt: document.getElementById('bcBAView').innerText };
      // 4. NPI units are counts; FY27 April launches read Apr-26.
      F.FY = []; show('analytics'); await W(1200);
      const th = [...document.querySelectorAll('#tab-analytics th')].find(h => h.innerText.trim() === 'Units');
      const i = th ? [...th.parentNode.children].indexOf(th) : -1;
      out.units = th ? [...th.closest('table').querySelectorAll('tbody tr')].map(tr => tr.children[i].innerText) : [];
      out.badLaunch = /\b(April|Apr)-27\b/.test(document.getElementById('tab-analytics').innerText);
      // 5. Channel split shares stay a share of the channels' own total.
      F.Chain = ['DMart']; show('channel-dynamics'); await W(600);
      document.querySelectorAll('#tab-channel-dynamics .subview-tab')[0].click(); await W(800);
      const h = [...document.querySelectorAll('.card h3')].find(x => /Channel Split/.test(x.innerText));
      out.shares = [...h.closest('.card').querySelectorAll('tbody tr')].map(tr => parseFloat(tr.children[2].innerText));
      F.Chain = [];
      // 6. KPI rows are styled cards.
      show('inventory-health'); await W(800);
      const k = document.querySelector('.kpi-card');
      out.kpiBorder = k ? getComputedStyle(k).borderTopWidth : null;
      return out;
    });
    expect(Math.abs(r.trendApr26 - r.fx0), 'cockpit trend: FY27 first month plots FY27 primary').toBeLessThan(0.01);
    expect(r.trendSets.join('|')).not.toContain('FY25');
    expect(r.promoCharts.length).toBeGreaterThan(0);
    expect(r.promoCharts.every(Boolean), 'promo scatter canvas keeps its Chart').toBe(true);
    expect(r.bc.macro).toBe('none'); expect(r.bc.ba).toBe('block');
    expect(r.bc.txt).toContain('Brand Counter offtake');
    expect(r.units.length).toBeGreaterThan(0);
    for (const u of r.units) expect(u, 'NPI units are counts, not rupees').not.toContain('₹');
    expect(r.badLaunch, 'FY27 April launch must read Apr-26').toBe(false);
    const tot = r.shares.reduce((a, v) => a + (v || 0), 0);
    expect(Math.abs(tot - 100), 'channel shares sum to ~100% with a chain filter').toBeLessThan(0.5);
    expect(r.kpiBorder).toBe('1px');
  });
  // Cosmetic QC follow-up 2026-10-01: four charts were bare canvases with no
  // title; an empty alerts feed gave no hint how old it was.
  test('TC13 - Charts sit in titled cards; empty alerts feed states its date', async ({ page }) => {
    await page.goto(BASE_URL, { waitUntil: 'networkidle' });
    const r = await page.evaluate(async () => {
      const W = ms => new Promise(res => setTimeout(res, ms));
      const titles = [];
      for (const [tab, i] of [['inventory-health', 0], ['inventory-health', 2], ['demand-planning', 0], ['demand-planning', 1]]) {
        F.FY = []; show(tab); await W(800);
        document.querySelectorAll('#tab-' + tab + ' .subview-tab')[i].click(); await W(900);
        for (const cv of document.querySelectorAll('#tab-' + tab + ' canvas')) {
          const card = cv.closest('.card');
          titles.push(card && card.querySelector('h3') ? card.querySelector('h3').innerText.trim() : '');
        }
      }
      show('alerts'); await W(800);
      return { titles, alerts: document.getElementById('tab-alerts').innerText };
    });
    expect(r.titles.length).toBeGreaterThan(0);
    for (const t of r.titles) expect(t, 'every chart sits in a titled card').not.toBe('');
    if (/No active alerts/.test(r.alerts)) expect(r.alerts).toContain('Feed generated');
  });
});
