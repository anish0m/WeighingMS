// Story 007/001 (header, clock) and the UI part of story 005/001 (operator).
const { test, expect } = require('@playwright/test');
const { resetDatabase, resetModes, openAsOperator } = require('./helpers');

// An open B-24187 session would resume View 2 on load: start from the seed.
test.beforeEach(async ({ request }) => {
  resetDatabase();
  await resetModes(request);
});

test('the operator must be chosen before the batch queue is shown', async ({ page }) => {
  await page.goto('/');

  await expect(page.locator('#v-operator')).toBeVisible();
  await expect(page.locator('#v-queue')).toBeHidden();
  await expect(page.getByTestId('operator')).toHaveText('No operator');
  await expect(page.getByRole('button', { name: 'R. Karim · Shift A' })).toBeVisible();
});

test('header shows the station and the chosen operator', async ({ page }) => {
  await openAsOperator(page);

  await expect(page.locator('.brandmark')).toHaveText(/WeighingMS\s*STATION 01/);
  await expect(page.getByTestId('operator')).toHaveText(/^\s*Operator\s+R\. Karim · Shift A\s*$/);
  await expect(page.getByTestId('crumb')).toBeHidden();
});

test('the chosen operator stays after a reload', async ({ page }) => {
  await openAsOperator(page);

  await page.reload();

  await expect(page.locator('#v-queue')).toBeVisible();
  await expect(page.getByTestId('operator')).toHaveText(/R\. Karim · Shift A/);
});

test('header shows batch, order and machine once a batch is open', async ({ page }) => {
  await openAsOperator(page);

  await page.locator('tr[data-batch="B-24187"]').click();

  await expect(page.getByTestId('crumb')).toHaveText(
    'BATCH B-24187 · ORDER SO-9931 · MACHINE JET-04',
  );
  await expect(page.getByTestId('operator')).toHaveText(/R\. Karim · Shift A/);
});

test('the clock shows hh:mm:ss and ticks', async ({ page }) => {
  await openAsOperator(page);
  const clock = page.getByTestId('clock');
  await expect(clock).toHaveText(/^\d{2}:\d{2}:\d{2}$/);
  const first = await clock.textContent();

  await expect(clock).not.toHaveText(first, { timeout: 3000 });
});

test('status bar shows every device, ORGATEX and EN', async ({ page }) => {
  await openAsOperator(page);
  const bar = page.getByTestId('status-bar');

  for (const text of [
    'SCALE 3 kg · READY',
    'SCALE 32 kg · READY',
    'SCANNER · READY',
    'PRINTER · READY',
  ]) {
    await expect(bar).toContainText(text);
  }
  await expect(bar).toContainText(/ORGATEX · LINKED \d{2}:\d{2}/);
  await expect(bar).toContainText('EN');
});
