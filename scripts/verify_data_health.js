#!/usr/bin/env node
/**
 * Dashboard Data Health Verification
 * Runs before build/commit to catch regressions early
 * Detects: NaN, missing offtake keys, empty chain arrays, unmapped chains
 */

const fs = require('fs');
const path = require('path');

const CHECKS = {
  NAN_DETECTION: { name: 'Raw NaN Prevention', critical: true },
  OFFTAKE_SCHEMA: { name: 'Offtake Total Object', critical: true },
  PRIMARY_CHAINS: { name: 'Primary Chain Data', critical: true },
  UNMAPPED_FILTER: { name: 'No Unmapped Chains in Output', critical: false },
  CANVAS_ELEMENTS: { name: 'Canvas Element Creation', critical: false }
};

function loadDataJS(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const match = content.match(/window\.DASH\s*=\s*(\{.*\});/s);
  if (!match) throw new Error('Cannot extract DASH object');
  return JSON.parse(match[1]);
}

function loadIndexHTML(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function runChecks(dataPath, htmlPath) {
  const results = [];
  const data = loadDataJS(dataPath);
  const html = loadIndexHTML(htmlPath);

  // Check 1: No raw NaN
  const hasNaN = /:\s*NaN\b/.test(fs.readFileSync(dataPath, 'utf8'));
  results.push({
    check: 'NAN_DETECTION',
    pass: !hasNaN,
    msg: hasNaN ? '❌ Raw NaN in data.js' : '✓ No raw NaN'
  });

  // Check 2: Offtake total object
  const hasOfftakeTotal = typeof data.offtake?.total === 'object' && Object.keys(data.offtake.total).length > 0;
  results.push({
    check: 'OFFTAKE_SCHEMA',
    pass: hasOfftakeTotal,
    msg: hasOfftakeTotal ? '✓ Offtake total object valid' : '❌ Offtake total missing'
  });

  // Check 3: Primary chains exist
  const chainCount = (data.primary?.by_chain || []).length;
  results.push({
    check: 'PRIMARY_CHAINS',
    pass: chainCount > 0,
    msg: chainCount > 0 ? `✓ ${chainCount} primary chains` : '❌ No primary chains'
  });

  // Check 4: No "Unmapped Chain" in output
  const unmappedChains = (data.primary?.by_chain || []).filter(c => c.name === 'Unmapped Chain');
  results.push({
    check: 'UNMAPPED_FILTER',
    pass: unmappedChains.length === 0,
    msg: unmappedChains.length === 0 ? '✓ No unmapped chains' : `⚠️  ${unmappedChains.length} unmapped chains found`
  });

  // Check 5: Canvas creation pattern present
  const hasCanvasCreation = html.includes("createElement('canvas')");
  results.push({
    check: 'CANVAS_ELEMENTS',
    pass: hasCanvasCreation,
    msg: hasCanvasCreation ? '✓ Canvas creation pattern present' : '❌ Canvas creation missing'
  });

  return results;
}

function main() {
  const dataPath = path.join(__dirname, '../dashboard/data.js');
  const htmlPath = path.join(__dirname, '../dashboard/index.html');

  console.log('\n' + '='.repeat(60));
  console.log('DASHBOARD DATA HEALTH VERIFICATION');
  console.log('='.repeat(60) + '\n');

  try {
    const results = runChecks(dataPath, htmlPath);

    let allCriticalPass = true;
    results.forEach(r => {
      console.log(r.msg);
      if (CHECKS[r.check].critical && !r.pass) {
        allCriticalPass = false;
      }
    });

    console.log('\n' + '='.repeat(60));
    if (allCriticalPass) {
      console.log('✅ All critical checks passed');
      console.log('='.repeat(60) + '\n');
      process.exit(0);
    } else {
      console.log('❌ Critical checks failed - build blocked');
      console.log('='.repeat(60) + '\n');
      process.exit(1);
    }
  } catch (err) {
    console.error(`❌ Verification error: ${err.message}`);
    process.exit(1);
  }
}

main();
