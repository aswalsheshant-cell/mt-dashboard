#!/usr/bin/env node
/**
 * Dashboard QA Sentinel — Auto-Fix Engine
 * Automatically detects and resolves dashboard regressions
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const BASE = path.join(__dirname, '../..');
const DATA_JS = path.join(BASE, 'dashboard/data.js');
const INDEX_HTML = path.join(BASE, 'dashboard/index.html');
const REPORT_FILE = '/tmp/dashboard_qa_sentinel_report.json';

class DashboardQASentinel {
  constructor() {
    this.report = {
      timestamp: new Date().toISOString(),
      branch: this.getCurrentBranch(),
      checks: [],
      fixes_applied: [],
      auto_fixed: 0,
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
      this.log('NaN regression detected - applying fix');
      const fixed = content.replace(/:\s*NaN\b/g, ': null');
      fs.writeFileSync(DATA_JS, fixed);
      this.fixes_applied.push('NaN → null conversion');
      this.report.auto_fixed++;
      return true;
    }
    return false;
  }

  // Check 2: Offtake Schema
  checkOfftakeSchema() {
    try {
      const content = fs.readFileSync(DATA_JS, 'utf8');
      const match = content.match(/window\.DASH\s*=\s*(\{.*\});/s);
      if (!match) return false;

      const data = JSON.parse(match[1]);
      const hasOfftakeTotal = typeof data.offtake?.total === 'object' &&
                              Object.keys(data.offtake.total || {}).length > 0;

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

  // Check 3: Unmapped Chain Filter
  checkUnmappedChainFilter() {
    const html = fs.readFileSync(INDEX_HTML, 'utf8');

    // Find buildChannelDynamics function
    const match = html.match(/function buildChannelDynamics\(\)\{[^}]*by_chain[^}]*/);
    if (!match) return false;

    // Check if filter is present
    const hasFilter = html.includes("filter(c=>c.name!=='Unmapped Chain')");

    if (!hasFilter) {
      this.log('Unmapped chain filter missing - requires manual code fix');
      this.report.requires_human_review.push({
        issue: 'Unmapped chain filter not found in buildChannelDynamics',
        fix: 'Add: .filter(c=>c.name!=="Unmapped Chain") to chains initialization'
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
    const hasFYFallback = html.includes('fallbackFy') || html.includes('fallback');

    if (!hasFYFallback) {
      this.log('FY fallback logic missing - requires manual code fix');
      this.report.requires_human_review.push({
        issue: 'FY fallback logic not found',
        fix: 'Add fallback mapping when primYr data is unavailable'
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
      { name: 'Unmapped Chain Filter', fn: () => this.checkUnmappedChainFilter(), critical: false },
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

  commitFixes() {
    if (this.fixes_applied.length === 0) {
      this.log('No fixes to commit');
      return;
    }

    try {
      execSync('git add dashboard/data.js dashboard/index.html', { cwd: BASE });
      const msg = `fix(dashboard): Sentinel auto-fix applied\n\nFixed issues:\n${
        this.fixes_applied.map(f => `- ${f}`).join('\n')
      }\n\nCo-Authored-By: Dashboard QA Sentinel <noreply@anthropic.com>`;

      execSync(`git commit -m "${msg.replace(/"/g, '\\"')}"`, { cwd: BASE });
      execSync('git push', { cwd: BASE });

      this.log(`Committed ${this.fixes_applied.length} fix(es) and pushed`, 'success');
    } catch (e) {
      this.log(`Commit/push failed: ${e.message}`, 'error');
    }
  }

  generateReport() {
    fs.writeFileSync(REPORT_FILE, JSON.stringify(this.report, null, 2));
    this.log(`Report written to ${REPORT_FILE}`);
  }

  run() {
    this.runAllChecks();
    this.commitFixes();
    this.generateReport();

    console.log('');
    console.log('='.repeat(60));
    if (this.report.auto_fixed > 0) {
      this.log(`Dashboard QA Sentinel: Fixed ${this.report.auto_fixed} issue(s)`, 'success');
    }
    if (this.report.requires_human_review.length > 0) {
      this.log(`${this.report.requires_human_review.length} issue(s) require manual review`, 'warn');
      this.report.requires_human_review.forEach(item => {
        console.log(`  • ${item.issue}`);
      });
    }
    console.log('='.repeat(60));
  }
}

const sentinel = new DashboardQASentinel();
sentinel.run();
