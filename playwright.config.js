// @ts-check
import { defineConfig } from '@playwright/test';

/**
 * Playwright configuration
 * - Opens new browser windows (not tabs) for each test
 * - Closes browser windows when tests exit
 */
export default defineConfig({
  testDir: './tests',
  testMatch: '**/*.spec.js',

  // Run tests in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: 'list',

  use: {
    // Base URL to use in actions like `await page.goto('/')`
    baseURL: 'http://127.0.0.1:9244',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Run in headed mode (visible browser) - set to true to see windows
    headless: true,

    // Each test gets a fresh browser context (new window, not tab)
    // This is the default behavior with contextOptions
    contextOptions: {
      // Ensure clean state for each test
      ignoreHTTPSErrors: true,
    },
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: {
        browserName: 'chromium',
        // Launch options - each context is like a new window
        launchOptions: {
          // Set to false to see the browser
          headless: true,
        },
      },
    },
  ],

  // Timeout for each test
  timeout: 30000,

  // Global teardown to ensure all browser processes are cleaned up
  globalTeardown: undefined,
});
