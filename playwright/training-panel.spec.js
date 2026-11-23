// Story 007/008 (bolt 011): the TRAINING ONLY panel drives the Dummies like
// the prototype's demo buttons, and View 2 follows. Each test starts from the
// seeded database.
const { test, expect } = require('@playwright/test');
const { resetDatabase, resetModes, openB24187, statusOf } = require('./helpers');

test.beforeEach(async ({ request }) => {
  resetDatabase();
  await resetModes(request);
});

test.afterEach(async ({ request }) => {
  await resetModes(request);
});

async function yellowActive(page) {
  await openB24187(page);
  await page.locator('.comp[data-sequence="3"]').click();
  await expect(page.getByTestId('component-name')).toHaveText('Remazol Yellow RGB');
  await expect(page.getByTestId('weighed-now')).toHaveText('0.0');
}

async function scaleReading(request, scaleId) {
  const response = await request.get(`/api/scales/${scaleId}/weight`);
  return (await response.json()).netWeight;
}

test('Simulate dispense / overshoot / Reset land at 94.2 / 96.4 / 0.0 g and View 2 follows', async ({
  page,
  request,
}) => {
  await yellowActive(page);
  const panel = page.getByTestId('training-panel');

  await panel.getByRole('button', { name: '▶ Simulate dispense' }).click();
  await expect(page.getByTestId('weighed-now')).toHaveText('94.2');
  expect(await scaleReading(request, 'scale-3kg')).toBe('94.2000');
  await expect(page.getByTestId('bar')).toHaveAttribute('data-zone', 'within');

  await panel.getByRole('button', { name: '▶ Simulate overshoot' }).click();
  await expect(page.getByTestId('weighed-now')).toHaveText('96.4');
  expect(await scaleReading(request, 'scale-3kg')).toBe('96.4000');
  await expect(page.getByTestId('bar')).toHaveAttribute('data-zone', 'over');

  await panel.getByRole('button', { name: 'Reset' }).click();
  await expect(page.getByTestId('weighed-now')).toHaveText('0.0');
  expect(await scaleReading(request, 'scale-3kg')).toBe('0.0000');
});

test('the simulate buttons use the active component: Sodium Sulphate in kg', async ({
  page,
  request,
}) => {
  await openB24187(page);
  await page.locator('.comp[data-sequence="4"]').click();
  await expect(page.getByTestId('component-name')).toHaveText('Sodium Sulphate');

  await page.getByTestId('sim-dispense').click();

  await expect(page.getByTestId('weighed-now')).toHaveText('24.048');
  expect(await scaleReading(request, 'scale-32kg')).toBe('24.0480');
});

test('Set weight puts an exact weight on the scale', async ({ page }) => {
  await yellowActive(page);

  await page.getByTestId('sim-weight').fill('93.5');
  await page.getByTestId('sim-set').click();

  await expect(page.getByTestId('weighed-now')).toHaveText('93.5');
  await expect(page.getByTestId('training-panel')).toContainText('Set weight');
  await expect(page.getByTestId('training-panel')).toContainText('g');
});

test('a rejected simulation shows the Dummy message', async ({ page }) => {
  await yellowActive(page);

  await page.getByTestId('sim-weight').fill('5000');
  await page.getByTestId('sim-set').click();

  await expect(page.getByTestId('training-message')).toContainText('capacity');
});

test('Simulate scan is prefilled with the active code and verifies it', async ({ page }) => {
  await yellowActive(page);

  await expect(page.getByTestId('sim-scan-code')).toHaveValue('DYE-4471');
  await page.getByTestId('sim-scan').click();

  await expect(page.getByTestId('scan-step')).toBeHidden();
});

const SWITCHES = [
  { target: 'scale-3kg', device: 'scale3kg', text: 'SCALE 3 kg · DISCONNECTED' },
  { target: 'scale-32kg', device: 'scale32kg', text: 'SCALE 32 kg · DISCONNECTED' },
  { target: 'scanner', device: 'scanner', text: 'SCANNER · UNAVAILABLE' },
  { target: 'printer', device: 'printer', text: 'PRINTER · ERROR' },
];

for (const s of SWITCHES) {
  test(`the ${s.target} failure switch sets and clears its failure mode`, async ({ page }) => {
    await openB24187(page);
    const toggle = page.locator(`.toggle[data-target="${s.target}"] input`);
    const stat = statusOf(page, s.device);
    await expect(stat).toContainText('READY');

    await toggle.check();

    await expect(stat).toHaveText(s.text, { timeout: 2000 });

    await toggle.uncheck();

    await expect(stat).toContainText('READY', { timeout: 2000 });
  });
}

test('the OrgaTEX failure switch sets and clears unavailable', async ({ page, request }) => {
  await openB24187(page);
  const toggle = page.locator('.toggle[data-target="orgatex"] input');
  await expect(page.locator('.toggle[data-target="orgatex"]')).toHaveText(
    'ORGATEX · UNAVAILABLE',
  );

  const orgatexMode = async () =>
    (await (await request.get('/api/training/modes')).json()).modes.orgatex;

  await toggle.check();
  await expect.poll(orgatexMode).toBe('unavailable');

  await toggle.uncheck();
  await expect.poll(orgatexMode).toBe('ok');
});

test('a disconnected scale blanks the readout and blocks OK', async ({ page }) => {
  await yellowActive(page);
  await page.getByTestId('sim-scan').click();
  await page.getByTestId('sim-dispense').click();
  await expect(page.getByTestId('btn-ok')).toBeEnabled();

  await page.locator('.toggle[data-target="scale-3kg"] input').check();

  await expect(page.getByTestId('btn-ok')).toBeDisabled();
  await expect(page.getByTestId('weighed-now')).toHaveText('—');
  await expect(page.getByTestId('status-line')).toHaveText(/^Scale disconnected/);

  await page.locator('.toggle[data-target="scale-3kg"] input').uncheck();

  await expect(page.getByTestId('weighed-now')).toHaveText('94.2');
  await expect(page.getByTestId('btn-ok')).toBeEnabled();
});

test('the panel is marked TRAINING ONLY and sits outside the operator screen', async ({
  page,
}) => {
  await openB24187(page);
  const panel = page.getByTestId('training-panel');

  await expect(panel).toBeVisible();
  await expect(panel).toContainText('TRAINING ONLY');
  await expect(page.locator('.device [data-testid="training-panel"]')).toHaveCount(0);
  await expect(page.locator('.screen').getByText('Simulate dispense')).toHaveCount(0);
});
