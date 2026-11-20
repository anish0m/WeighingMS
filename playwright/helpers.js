// Shared E2E helpers. Training controls (/api/training/...) are used only by
// the tests, never by the terminal UI.
const { expect } = require('@playwright/test');

const TARGETS = ['orgatex', 'scale-3kg', 'scale-32kg', 'scanner', 'printer'];

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

// Opens the terminal and identifies R. Karim (story 005/001).
async function openAsOperator(page) {
  await page.goto('/');
  await page.getByRole('button', { name: 'R. Karim · Shift A' }).click();
  await expect(page.locator('#v-queue')).toBeVisible();
}

function statusOf(page, device) {
  return page.locator(`[data-testid="status-bar"] [data-device="${device}"]`);
}

module.exports = { resetModes, setMode, scan, openAsOperator, statusOf };
