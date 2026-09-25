// Shared Chromium launcher for the browser tests.
//
// Why: Playwright looks for the browser revision it was built against
// (e.g. chromium-1243). A machine can have a different revision installed
// (the cloud container ships /opt/pw-browsers/chromium, a symlink to its own
// revision), and then a plain chromium.launch() dies with "Executable doesn't
// exist" unless someone hand-edits an executablePath into the test.
//
// Order used, first hit wins:
//   1. PW_CHROMIUM_PATH env var           -- explicit override, any machine
//   2. Playwright's own bundled browser   -- CI after `npx playwright install`
//   3. <PLAYWRIGHT_BROWSERS_PATH>/chromium -- pre-installed browser dir
//                                            (cloud container: /opt/pw-browsers)
// If none exists, fail with a message that names the fix -- never a silent skip.
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

function resolveChromium(env = process.env, exists = fs.existsSync, bundled = () => chromium.executablePath()) {
  if (env.PW_CHROMIUM_PATH) {
    if (!exists(env.PW_CHROMIUM_PATH)) {
      throw new Error(`PW_CHROMIUM_PATH is set but does not exist: ${env.PW_CHROMIUM_PATH}`);
    }
    return { executablePath: env.PW_CHROMIUM_PATH, source: 'PW_CHROMIUM_PATH' };
  }
  let own = null;
  try { own = bundled(); } catch (_) { /* no bundled browser registered */ }
  if (own && exists(own)) return { executablePath: undefined, source: 'playwright-bundled' };
  if (env.PLAYWRIGHT_BROWSERS_PATH) {
    const pre = path.join(env.PLAYWRIGHT_BROWSERS_PATH, 'chromium');
    if (exists(pre)) return { executablePath: pre, source: 'PLAYWRIGHT_BROWSERS_PATH/chromium' };
  }
  throw new Error(
    'No Chromium found. Run `npx playwright install chromium`, or set PW_CHROMIUM_PATH ' +
    'to a Chromium/Chrome executable.');
}

async function launchChromium(opts = {}) {
  const { executablePath } = resolveChromium();
  return chromium.launch({ headless: true, ...opts, ...(executablePath ? { executablePath } : {}) });
}

module.exports = { resolveChromium, launchChromium };
