// Playwright E2E configuration (approved stack). The tests run against their
// own Django server on port 8001 with a separate, freshly migrated and seeded
// SQLite file, so they never touch the dev database or the dev server on 8000.
// A pristine copy of the freshly migrated and seeded file is kept; tests that
// need a clean state copy it back (helpers.resetDatabase, bolt 011 Decision 4).
const path = require('node:path');
const { defineConfig, devices } = require('@playwright/test');

const PORT = 8001;
const BASE_URL = `http://localhost:${PORT}`;
const E2E_DB = path.join(__dirname, 'playwright', '.cache', 'e2e.sqlite3');
const E2E_PRISTINE = path.join(__dirname, 'playwright', '.cache', 'e2e.pristine.sqlite3');
const PYTHON = path.join(__dirname, '.venv', 'bin', 'python');

module.exports = defineConfig({
  testDir: './playwright',
  // Tests share one server and toggle its training modes: run them one by one.
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    viewport: { width: 1280, height: 900 },
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: [
      `mkdir -p ${path.dirname(E2E_DB)}`,
      `rm -f ${E2E_DB} ${E2E_PRISTINE}`,
      `${PYTHON} manage.py migrate --noinput`,
      `${PYTHON} manage.py seed_training`,
      `cp ${E2E_DB} ${E2E_PRISTINE}`,
      `${PYTHON} manage.py runserver ${PORT} --noreload`,
    ].join(' && '),
    url: BASE_URL,
    reuseExistingServer: false,
    timeout: 120000,
    env: {
      WEIGHINGMS_DB_PATH: E2E_DB,
      ORGATEX_BASE_URL: `${BASE_URL}/api`,
      SCALE_BASE_URL: `${BASE_URL}/api`,
      SCANNER_BASE_URL: `${BASE_URL}/api`,
      PRINTER_BASE_URL: `${BASE_URL}/api`,
    },
  },
});
