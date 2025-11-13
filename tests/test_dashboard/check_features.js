import { chromium } from 'playwright';

(async () => {
  const browser = await chromium.launch({ headless: true });
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

    // Check what's in the features container
    const featuresInfo = await page.evaluate(() => {
      const container = document.getElementById('diagnostics-features');
      return {
        exists: !!container,
        innerHTML: container ? container.innerHTML : null,
        childCount: container ? container.children.length : 0
      };
    });

    console.log('Features container info:', JSON.stringify(featuresInfo, null, 2));

    // Check if displayDiagnostics function is populating features
    const diagnosticsData = await page.evaluate(async () => {
      const response = await fetch('/api/diagnostics');
      const data = await response.json();

      // Check what the displayDiagnostics function would do
      return {
        features: data.features,
        recommendations: data.recommendations,
        issues: data.issues
      };
    });

    console.log('\nDiagnostics data:');
    console.log(JSON.stringify(diagnosticsData, null, 2));

    console.log('\nConsole messages:');
    consoleMessages.forEach(msg => console.log(msg));

    await page.screenshot({
      path: '/Users/robert/Code/spec-kitty/diagnostics_features_check.png',
      fullPage: true
    });

  } catch (error) {
    console.error('Error:', error);
  } finally {
    await browser.close();
  }
})();
