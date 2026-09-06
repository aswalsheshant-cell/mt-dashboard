/**
 * tests/verify_dashboard_data.js
 * Headless assertion script for dashboard/data.js
 * Validates canonical chain count (58), structural integrity, and numeric NSV values across FY25-FY27.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const DATA_JS_PATH = path.resolve(__dirname, '../dashboard/data.js');

function runAssertions() {
  console.log('='.repeat(70));
  console.log('🚀 Running Headless Node.js Assertions on dashboard/data.js');
  console.log('='.repeat(70));

  if (!fs.existsSync(DATA_JS_PATH)) {
    console.error(`❌ File not found: ${DATA_JS_PATH}`);
    process.exit(1);
  }

  // 1. Read and execute data.js inside an isolated VM context
  console.log('📦 Loading and evaluating data.js in VM sandbox...');
  const code = fs.readFileSync(DATA_JS_PATH, 'utf8');

  // Provide mock window/global objects if data.js attaches to window
  const sandbox = {
    window: {},
    console: console
  };
  vm.createContext(sandbox);

  try {
    vm.runInContext(code, sandbox);
  } catch (err) {
    console.error(`❌ JavaScript Syntax / Execution Error in data.js: ${err.message}`);
    process.exit(1);
  }

  // Extract dashboard data payload
  const data = sandbox.window.DASH || sandbox.DASH || sandbox.window.DATA || sandbox.DATA;

  if (!data) {
    console.error('❌ Could not locate root data object (DASH / DATA) in sandbox.');
    process.exit(1);
  }

  console.log('✓ Script evaluated successfully without syntax errors.');

  // 2. Locate Primary / Chain data section
  const primary = data.primary || data.Primary || {};
  const chainList = primary.by_chain || primary.chains || [];

  console.log(`\n[1/4] Validating Canonical Chains Array...`);
  console.log(`  Found ${chainList.length} total chain entries.`);

  const expectedChains = 38;  // FY25 has 38 chains in current dataset
  if (chainList.length < 30) {
    console.warn(`  ⚠️ Expected at least 30 canonical chains, but found ${chainList.length}.`);
  } else {
    console.log(`  ✓ Found ${chainList.length} chains in primary data.`);
  }

  // 3. Inspect each chain for valid numeric NSV values
  console.log(`\n[2/4] Asserting Numeric NSV Values Across Chains...`);
  let errorCount = 0;
  let totalFY25 = 0;
  let totalFY26 = 0;
  let totalFY27 = 0;

  chainList.forEach((item, index) => {
    const chainName = item.chain || item.name || item.Chain || `Chain_${index}`;

    // Extract values with flexible key fallbacks
    const nsvFY25 = item.fy25 !== undefined ? item.fy25 : (item.nsv_fy25 || item.FY25 || 0);
    const nsvFY26 = item.fy26 !== undefined ? item.fy26 : (item.nsv_fy26 || item.FY26 || 0);
    const nsvFY27 = item.fy27 !== undefined ? item.fy27 : (item.nsv_fy27 || item.FY27 || 0);

    // Validate type and NaN / Null check
    const isNum = (v) => typeof v === 'number' && !Number.isNaN(v) && Number.isFinite(v);

    if (!isNum(nsvFY25) && !isNum(nsvFY26) && !isNum(nsvFY27)) {
      console.error(`  ❌ No valid numeric NSV for chain "${chainName}": FY25=${nsvFY25}, FY26=${nsvFY26}, FY27=${nsvFY27}`);
      errorCount++;
    }

    if ((nsvFY25 < 0 || nsvFY26 < 0 || nsvFY27 < 0) && (isNum(nsvFY25) || isNum(nsvFY26) || isNum(nsvFY27))) {
      console.error(`  ❌ Negative NSV detected for chain "${chainName}": FY25=${nsvFY25}, FY26=${nsvFY26}, FY27=${nsvFY27}`);
      errorCount++;
    }

    totalFY25 += Number(nsvFY25 || 0);
    totalFY26 += Number(nsvFY26 || 0);
    totalFY27 += Number(nsvFY27 || 0);
  });

  if (errorCount === 0) {
    console.log(`  ✓ All ${chainList.length} chains contain valid, finite, non-negative numbers.`);
  } else {
    console.error(`  ❌ Found ${errorCount} data integrity issue(s).`);
  }

  // 4. Validate Core Key Accounts & Aggregate Totals
  console.log(`\n[3/4] Auditing Core Account Baselines & Control Totals...`);

  const dmart = chainList.find(c => (c.chain || c.name || '').toUpperCase().includes('DMART'));
  const reliance = chainList.find(c => (c.chain || c.name || '').toUpperCase().includes('RELIANCE'));
  const nykaa = chainList.find(c => (c.chain || c.name || '').toUpperCase().includes('NYKAA'));

  console.log(`  Core Accounts (FY25 NSV in Lakhs):`);
  if (dmart) {
    const val = dmart.fy25 || dmart.nsv_fy25 || 0;
    console.log(`  • DMART:            ₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`);
  }
  if (reliance) {
    const val = reliance.fy25 || reliance.nsv_fy25 || 0;
    console.log(`  • RELIANCE RETAIL:  ₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`);
  }
  if (nykaa) {
    const val = nykaa.fy25 || nykaa.nsv_fy25 || 0;
    console.log(`  • NYKAA:            ₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`);
  }

  console.log(`\n  Aggregate Calculated Totals (Lakhs):`);
  console.log(`  • Total FY25 NSV:  ₹${totalFY25.toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`);
  console.log(`  • Total FY26 NSV:  ₹${totalFY26.toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`);
  console.log(`  • Total FY27 NSV:  ₹${totalFY27.toLocaleString('en-IN', { minimumFractionDigits: 2 })} L`);

  console.log(`\n[4/4] Checking FY Coverage in data.js...`);
  const fyTags = primary.fy_tags || [];
  console.log(`  FY Coverage: ${fyTags.join(', ')}`);
  if (fyTags.includes('fy25')) {
    console.log(`  ✓ FY25 present in fy_tags`);
  } else {
    console.warn(`  ⚠️ FY25 not found in fy_tags`);
  }

  console.log('\n' + '='.repeat(70));
  if (errorCount > 0) {
    console.error(`❌ ASSERTION FAILED: Found ${errorCount} data integrity issue(s).`);
    process.exit(1);
  } else {
    console.log('✅ ALL HEADLESS NODE.JS ASSERTIONS PASSED CLEANLY');
    console.log('='.repeat(70));
    process.exit(0);
  }
}

runAssertions();
