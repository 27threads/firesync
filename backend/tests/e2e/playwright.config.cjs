const { defineConfig, devices } = require('../../../frontend/e2e/node_modules/@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  testMatch: 'http.spec.cjs',
  workers: 1,
  timeout: 60000,
  use: { baseURL: process.env.FRONTEND_URL || 'http://127.0.0.1:5173', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
});
