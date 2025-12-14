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

  // Capture network requests
  const apiResponses = [];
  page.on('response', async (response) => {
    const url = response.url();
    if (url.includes('/api/diagnostics')) {
      try {
        const body = await response.json();
        apiResponses.push({
          url: url,
          status: response.status(),
          body: body
        });
      } catch (e) {
        console.error('Error parsing response:', e);
      }
    }
  });

  try {
    await page.goto('http://127.0.0.1:9244/', { waitUntil: 'networkidle', timeout: 10000 });
    await page.waitForTimeout(1000);

    console.log('Clicking on Diagnostics...');
    await page.click('.sidebar-item[data-page="diagnostics"]');
    await page.waitForTimeout(3000);

    console.log('\n=== API RESPONSES ===\n');
    apiResponses.forEach(resp => {
      console.log('URL:', resp.url);
      console.log('Status:', resp.status);
      console.log('Body:');
      console.log(JSON.stringify(resp.body, null, 2));
    });

  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    // Close context first, then browser to ensure clean shutdown
    await context.close();
    await browser.close();
    browser = null;
  }
})();
