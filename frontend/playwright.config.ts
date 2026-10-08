import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './browser-tests', timeout: 30000, fullyParallel: false, workers: 1,
  use: { browserName: 'chromium', viewport: { width: 1440, height: 900 },
    baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure' },
  expect: { toHaveScreenshot: { maxDiffPixelRatio: .001 } },
  webServer: { command: 'npm run dev -- --port 5173 --strictPort', url: 'http://127.0.0.1:5173', reuseExistingServer: true },
  reporter: 'list'
});
