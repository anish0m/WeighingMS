// Story 007/001 AC 3 / FR-20: a failing device shows within 2 s, never READY.
const { test, expect } = require('@playwright/test');
const { resetDatabase, resetModes, setMode, openAsOperator, statusOf } = require('./helpers');

// An open B-24187 session would resume View 2 on load: start from the seed.
test.beforeEach(async ({ request }) => {
  resetDatabase();
  await resetModes(request);
});

test.afterEach(async ({ request }) => {
  await resetModes(request);
});

const FAILURES = [
  { target: 'scanner', device: 'scanner', mode: 'unavailable', text: 'SCANNER · UNAVAILABLE' },
  { target: 'scale-3kg', device: 'scale3kg', mode: 'disconnected', text: 'SCALE 3 kg · DISCONNECTED' },
  { target: 'scale-32kg', device: 'scale32kg', mode: 'disconnected', text: 'SCALE 32 kg · DISCONNECTED' },
  { target: 'printer', device: 'printer', mode: 'error', text: 'PRINTER · ERROR' },
];

for (const failure of FAILURES) {
  test(`${failure.target} failure shows within 2 s and recovers`, async ({ page, request }) => {
    await openAsOperator(page);
    const stat = statusOf(page, failure.device);
    await expect(stat).toContainText('READY');

    await setMode(request, failure.target, failure.mode);

    await expect(stat).toHaveText(failure.text, { timeout: 2000 });
    await expect(stat.locator('.dot')).toHaveClass(/down/);
    await expect(stat).not.toContainText('READY');

    await setMode(request, failure.target, 'ok');

    await expect(stat).toContainText('READY', { timeout: 2000 });
    await expect(stat.locator('.dot')).toHaveClass(/up/);
  });
}

test('ORGATEX shows UNAVAILABLE and the queue gives way to the message', async ({
  page,
  request,
}) => {
  await setMode(request, 'orgatex', 'unavailable');

  await openAsOperator(page);

  await expect(statusOf(page, 'orgatex')).toHaveText('ORGATEX · UNAVAILABLE');
  await expect(page.getByTestId('message')).toHaveText('OrgaTEX unavailable');
  await expect(page.locator('tr[data-batch]')).toHaveCount(0);
});
