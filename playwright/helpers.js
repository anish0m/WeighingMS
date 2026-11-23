// Shared E2E helpers. The tests drive the Dummies through the training
// controls (/api/training/...), the same ones the terminal's training panel
// uses (story 008); operator actions always go through the terminal UI.
const fs = require('node:fs');
const path = require('node:path');
const { expect } = require('@playwright/test');

const TARGETS = ['orgatex', 'scale-3kg', 'scale-32kg', 'scanner', 'printer'];
const CACHE = path.join(__dirname, '.cache');
const E2E_DB = path.join(CACHE, 'e2e.sqlite3');
const E2E_PRISTINE = path.join(CACHE, 'e2e.pristine.sqlite3');

// Restores the freshly migrated and seeded E2E database (bolt 011 Decision 4).
// An open weighing session resumes View 2 on page load, so tests that start
// from the queue call this first. Django opens a new SQLite connection per
// request, so the server picks up the restored file with its next request.
function resetDatabase() {
  fs.copyFileSync(E2E_PRISTINE, E2E_DB);
}

async function setMode(request, target, mode) {
  const response = await request.put(`/api/training/modes/${target}`, { data: { mode } });
  expect(response.ok()).toBeTruthy();
}

async function resetModes(request) {
  for (const target of TARGETS) {
    await setMode(request, target, 'ok');
  }
}

async function scan(request, kind, code) {
  const response = await request.post('/api/training/scanner/scans', { data: { kind, code } });
  expect(response.status()).toBe(201);
}

// Sets the Dummy Scale's net weight exactly (DB-6 "set exact weight").
async function setWeight(request, scaleId, weight, unit) {
  const response = await request.post(`/api/training/scales/${scaleId}/simulate`, {
    data: { action: 'set', weight, unit },
  });
  expect(response.ok()).toBeTruthy();
}

// Opens the terminal and identifies R. Karim (story 005/001).
async function openAsOperator(page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'R. Karim · Shift A' }).click();
  await expect(page.locator('#v-queue')).toBeVisible();
}

// From a clean database: R. Karim opens B-24187 by touch; View 2 shows the
// first component (Blue RSPL) active and tared by the server.
async function openB24187(page) {
  await openAsOperator(page);
  await page.locator('tr[data-batch="B-24187"]').click();
  await expect(page.locator('#v-weigh')).toBeVisible();
  await expect(page.locator('.comp[data-state="active"]')).toHaveCount(1);
}

function statusOf(page, device) {
  return page.locator(`[data-testid="status-bar"] [data-device="${device}"]`);
}

module.exports = {
  resetDatabase,
  resetModes,
  setMode,
  scan,
  setWeight,
  openAsOperator,
  openB24187,
  statusOf,
};
