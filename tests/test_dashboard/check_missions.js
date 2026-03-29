import { chromium } from 'playwright';

// Ensure browser closes on exit/interrupt
let browser = null;
const cleanup = async () => {
  if (browser) {
    try {
      await browser.close();
      browser = null;
    } catch (e) {
      // Ignore close errors
    }
  }
  process.exit(0);
};
process.on('SIGINT', cleanup);
process.on('SIGTERM', cleanup);

(async () => {
  // Launch a NEW browser window (not reusing existing)
  browser = await chromium.launch({
    headless: true,
    args: ['--new-window']  // Force new window
  });
  // Create isolated context (like a new window, not a tab)
  const context = await browser.newContext();
  const page = await context.newPage();

  const consoleMessages = [];
  page.on('console', msg => {
    consoleMessages.push(`[${msg.type()}] ${msg.text()}`);
  });

  try {
    await page.goto('http://127.0.0.1:9244/', { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(1000);

    await page.click('.sidebar-item[data-page="diagnostics"]');
    await page.waitForTimeout(3000);

    // Check what's in the missions container
    const missionsInfo = await page.evaluate(() => {
      const container = document.getElementById('diagnostics-missions');
      return {
        exists: !!container,
        innerHTML: container ? container.innerHTML : null,
        childCount: container ? container.children.length : 0
      };
    });

    console.log('Missions container info:', JSON.stringify(missionsInfo, null, 2));

    // Check if displayDiagnostics function is populating missions
    const diagnosticsData = await page.evaluate(async () => {
      const response = await fetch('/api/diagnostics');
      const data = await response.json();

      // Check what the displayDiagnostics function would do
      return {
        missions: data.missions,
        recommendations: data.recommendations,
        issues: data.issues
      };
    });

    console.log('\nDiagnostics data:');
    console.log(JSON.stringify(diagnosticsData, null, 2));

    console.log('\nConsole messages:');
    consoleMessages.forEach(msg => console.log(msg));

    await page.screenshot({
      path: '/Users/robert/Code/spec-kitty/diagnostics_missions_check.png',
      fullPage: true
    });

  } catch (error) {
    console.error('Error:', error);
  } finally {
    // Close context first, then browser to ensure clean shutdown
    await context.close();
    await browser.close();
    browser = null;
  }
})();
