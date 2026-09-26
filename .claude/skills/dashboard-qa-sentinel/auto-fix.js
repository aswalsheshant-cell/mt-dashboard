#!/usr/bin/env node
/**
 * Dashboard QA Sentinel — read-only check engine
 * Detects dashboard regressions and reports them. It never writes data.js or
 * index.html and never runs git: data.js is generated (CLAUDE.md "DO NOT
 * hand-edit"), and every fix goes through the generator + validation sweep on
 * a branch. Exit code: 0 = all critical checks pass, 1 = a critical check failed.
 * (File name kept so existing references keep working.)
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');   // read-only git query only

const BASE = path.join(__dirname, '../../..');
const DATA_JS = path.join(BASE, 'dashboard/data.js');
const INDEX_HTML = path.join(BASE, 'dashboard/index.html');
const REPORT_FILE = '/tmp/dashboard_qa_sentinel_report.json';

class DashboardQASentinel {
  constructor() {
    this.report = {
      timestamp: new Date().toISOString(),
      branch: this.getCurrentBranch(),
      checks: [],
      requires_human_review: []
    };
  }

  getCurrentBranch() {
    try {
      return execSync('git rev-parse --abbrev-ref HEAD', { cwd: BASE }).toString().trim();
    } catch {
      return 'unknown';
    }
  }

  log(msg, type = 'info') {
    const prefix = { error: '❌', warn: '⚠️ ', success: '✅', info: 'ℹ️' }[type];
    console.log(`${prefix} ${msg}`);
  }

  // Check 1: NaN Regression
  checkNaN() {
    const content = fs.readFileSync(DATA_JS, 'utf8');
    const hasNaN = /:\s*NaN\b/.test(content);

    if (hasNaN) {
      // Report only. The NaN comes from the generator; fixing data.js by hand
      // hides the bug and is overwritten on the next rebuild.
      this.report.requires_human_review.push({
        issue: 'Raw NaN found in dashboard/data.js',
        fix: 'Find the NaN source in scripts/build_dashboard_data.py, fix it, rebuild, run the validation sweep'
      });
      return false;
    }
    return true;
  }

  // Check 2: Offtake Schema
  checkOfftakeSchema() {
    try {
      const content = fs.readFileSync(DATA_JS, 'utf8');
      const match = content.match(/window\.DASH\s*=\s*(\{.*\});/s);
      if (!match) return false;

      const data = JSON.parse(match[1]);
      // offtake.total is the FY26 national total (a number, Rs Lac); older
      // builds used an object keyed by FY. Either shape is valid; empty is not.
      const t = data.offtake?.total;
      const hasOfftakeTotal = (typeof t === 'number' && Number.isFinite(t) && t > 0) ||
                              (t !== null && typeof t === 'object' && Object.keys(t).length > 0);

      if (!hasOfftakeTotal) {
        this.log('Offtake schema missing - requires full rebuild');
        this.report.requires_human_review.push({
          issue: 'Offtake total object missing',
          fix: 'Run: python scripts/build_dashboard_data.py --offtake-patch --src <dir>'
        });
        return false;
      }
      return true;
    } catch (e) {
      return false;
    }
  }

  // Check 3: Unmapped Chain stays visible
  // "Unmapped Chain" is a real NSV bucket (FAILURE_MODE_REGISTER FM-17/19/20).
  // Filtering it out of the chain view makes chain totals stop adding up to
  // Primary, so the regression is a filter that HIDES it, not a missing one.
  checkUnmappedChainFilter() {
    const html = fs.readFileSync(INDEX_HTML, 'utf8');
    const hides = /filter\(\s*c\s*=>\s*c\.name\s*!==?\s*['"]Unmapped Chain['"]\s*\)/.test(html);

    if (hides) {
      this.log('Unmapped Chain is filtered out of a chain view - requires manual code fix');
      this.report.requires_human_review.push({
        issue: 'A chain view filters out "Unmapped Chain", so chain totals no longer tie to Primary',
        fix: 'Remove the filter; reduce Unmapped Chain through mapping governance (FM-19), not by hiding it'
      });
      return false;
    }
    return true;
  }

  // Check 4: Canvas Element Creation
  checkCanvasPattern() {
    const html = fs.readFileSync(INDEX_HTML, 'utf8');
    const hasCanvasCreation = html.includes("createElement('canvas')");

    if (!hasCanvasCreation) {
      this.log('Canvas creation pattern missing - requires manual code fix');
      this.report.requires_human_review.push({
        issue: 'Canvas element creation not found in chart rendering functions',
        fix: 'Add: const cv=document.createElement("canvas"); cvDiv.appendChild(cv);'
      });
      return false;
    }
    return true;
  }

  // Check 5: FY Fallback Logic
  checkFYFallback() {
    const html = fs.readFileSync(INDEX_HTML, 'utf8');
    // FY27+ must be gated (fyBeyondPreagg / FPX), never filled with another FY's numbers.
    const hasFYFallback = html.includes('fyBeyondPreagg');

    if (!hasFYFallback) {
      this.log('FY27+ gating (fyBeyondPreagg) missing - requires manual code fix');
      this.report.requires_human_review.push({
        issue: 'fyBeyondPreagg() gate not found in index.html',
        fix: 'Restore the THE ONE FY RULE gate; show "–" / not-in-source, never copy another FY'
      });
      return false;
    }
    return true;
  }

  // Check 6: Alert Controller Wiring
  checkAlertController() {
    const html = fs.readFileSync(INDEX_HTML, 'utf8');
    const hasAlertWiring = html.includes('AlertController.buildAlerts') &&
                           html.includes('alert_controller.js');

    if (!hasAlertWiring) {
      this.log('Alert controller not properly wired');
      this.report.requires_human_review.push({
        issue: 'Alert controller missing or not wired to buildAlerts',
        fix: 'Ensure alert_controller.js is loaded and buildAlerts() calls it'
      });
      return false;
    }
    return true;
  }

  runAllChecks() {
    this.log('Running Dashboard QA Sentinel checks...');
    console.log('');

    const checks = [
      { name: 'NaN Regression', fn: () => this.checkNaN(), critical: true },
      { name: 'Offtake Schema', fn: () => this.checkOfftakeSchema(), critical: true },
      { name: 'Unmapped Chain Visible', fn: () => this.checkUnmappedChainFilter(), critical: false },
      { name: 'Canvas Pattern', fn: () => this.checkCanvasPattern(), critical: false },
      { name: 'FY Fallback', fn: () => this.checkFYFallback(), critical: false },
      { name: 'Alert Controller', fn: () => this.checkAlertController(), critical: false }
    ];

    let passCount = 0;
    checks.forEach(check => {
      const passed = check.fn();
      this.report.checks.push({
        name: check.name,
        passed,
        critical: check.critical
      });

      if (passed) {
        this.log(`${check.name}: OK`, 'success');
        passCount++;
      } else {
        const level = check.critical ? 'error' : 'warn';
        this.log(`${check.name}: FAILED`, level);
      }
    });

    console.log('');
    this.log(`Results: ${passCount}/${checks.length} passed`);
  }

  generateReport() {
    fs.writeFileSync(REPORT_FILE, JSON.stringify(this.report, null, 2));
    this.log(`Report written to ${REPORT_FILE}`);
  }

  run() {
    this.runAllChecks();
    this.generateReport();

    console.log('');
    console.log('='.repeat(60));
    if (this.report.requires_human_review.length > 0) {
      this.log(`${this.report.requires_human_review.length} issue(s) require manual review`, 'warn');
      this.report.requires_human_review.forEach(item => {
        console.log(`  • ${item.issue}`);
      });
    }
    console.log('='.repeat(60));
    return this.report.checks.some(c => c.critical && !c.passed) ? 1 : 0;
  }
}

const sentinel = new DashboardQASentinel();
process.exitCode = sentinel.run();
