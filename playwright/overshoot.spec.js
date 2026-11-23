// Story 007/006 (bolt 013): View 2 under the STEP 24 overshoot rule (OQ-4,
// ADR-012). The surplus panel, the status line, OK and Supervisor override
// show only what the server's evaluation returns; no recalculation proposal.
// Weights come from the Dummy Scale's training controls (training contract).
const { test, expect } = require('@playwright/test');
const { resetDatabase, resetModes, setWeight, openB24187 } = require('./helpers');

const OVER = 'rgb(232, 80, 58)';
const RECOVERY =
  'Remove material until the weight is back in the band, ' +
  'or press Quit (F4) to discard and re-weigh.';
const NO_OVERRIDE = 'Supervisor override is not available in this training build';

test.beforeEach(async ({ request }) => {
  resetDatabase();
  await resetModes(request);
});

test.afterEach(async ({ request }) => {
  await resetModes(request);
});

function row(page, sequence) {
  return page.locator(`.comp[data-sequence="${sequence}"]`);
}

// Activates a component by touch and verifies it with the training scan.
async function activeAndScanned(page, sequence, name) {
  await openB24187(page);
  await row(page, sequence).click();
  await expect(page.getByTestId('component-name')).toHaveText(name);
  const code = (await page.getByTestId('component-meta').innerText()).split(' · ')[0];
  await expect(page.getByTestId('sim-scan-code')).toHaveValue(code);
  await page.getByTestId('sim-scan').click();
  await expect(page.getByTestId('scan-step')).toBeHidden();
}

async function yellowOvershoot(page) {
  await activeAndScanned(page, 3, 'Remazol Yellow RGB');
  await expect(page.getByTestId('surplus-panel')).toBeHidden();
  await page.getByRole('button', { name: '▶ Simulate overshoot' }).click();
  await expect(page.getByTestId('weighed-now')).toHaveText('96.4');
}

test('Yellow RGB at 96.4 g: status line, surplus panel, OK disabled (AC 1)', async ({
  page,
}) => {
  await yellowOvershoot(page);

  await expect(page.getByTestId('status-line')).toHaveText('OVER TOLERANCE — SURPLUS +2.4 g');
  await expect(page.getByTestId('status-line')).toHaveCSS('color', OVER);
  await expect(page.getByTestId('surplus-panel')).toBeVisible();
  await expect(page.getByTestId('surplus-heading')).toHaveText(
    'Surplus +2.4 g (+2.6%) — over tolerance',
  );
  await expect(page.getByTestId('surplus-heading')).toHaveCSS('color', OVER);
  await expect(page.getByTestId('btn-ok')).toBeDisabled();
  await page.keyboard.press('F1');
  await expect(page.getByTestId('rail-progress')).toHaveText('0 of 5 components weighed');
});

test('the panel shows only the STEP 24 rule: no recalculation proposal (AC 2)', async ({
  page,
}) => {
  await yellowOvershoot(page);

  const panel = page.getByTestId('surplus-panel');
  await expect(panel.locator(':scope > *')).toHaveCount(3);
  await expect(page.getByTestId('surplus-recovery')).toHaveText(RECOVERY);
  await expect(page.getByTestId('surplus-override')).toHaveText(NO_OVERRIDE);
  await expect(panel).not.toContainText('Sodium Sulphate');
  await expect(panel).not.toContainText('Soda Ash');
  await expect(panel).not.toContainText('→');
  await expect(panel.locator('table')).toHaveCount(0);
  const view = page.locator('#v-weigh');
  await expect(view).not.toContainText('24.624');
  await expect(view).not.toContainText('9.850');
  await expect(view).not.toContainText('Proposal');
  // Every remaining target is the recipe's own.
  await expect(row(page, 4).locator('.qty')).toHaveText('24.000 kg');
  await expect(row(page, 5).locator('.qty')).toHaveText('9.600 kg');
});

test('Supervisor override stays disabled with the server reason (AC 3 n/a)', async ({
  page,
}) => {
  await yellowOvershoot(page);

  const override = page.getByTestId('btn-override');
  await expect(override).toBeDisabled();
  await expect(override).toHaveAttribute('title', NO_OVERRIDE);
  await expect(page.locator('form')).toHaveCount(0);
});

test('recovery (a): removing material back into the band re-enables OK', async ({
  page,
  request,
}) => {
  await yellowOvershoot(page);

  await setWeight(request, 'scale-3kg', '94.0', 'g');

  await expect(page.getByTestId('weighed-now')).toHaveText('94.0');
  await expect(page.getByTestId('surplus-panel')).toBeHidden();
  await expect(page.getByTestId('status-line')).toHaveText(
    'WITHIN TOLERANCE — PRESS OK TO CONFIRM',
  );
  await expect(page.getByTestId('btn-override')).not.toHaveAttribute('title');
  await expect(page.getByTestId('btn-ok')).toBeEnabled();
  await page.getByTestId('btn-ok').click();
  await expect(page.getByTestId('rail-progress')).toHaveText('1 of 5 components weighed');
});

test('recovery (b): Quit F4 discards the overshoot and asks for a re-tare', async ({
  page,
  request,
}) => {
  await yellowOvershoot(page);

  await page.keyboard.press('F4');

  await expect(page.getByTestId('weigh-message')).toHaveText(
    'Overshoot discarded (96.4 g). Empty the container and press Re-tare (F2).',
  );
  await expect(row(page, 3)).toHaveAttribute('data-state', 'active');
  await expect(page.getByTestId('rail-progress')).toHaveText('0 of 5 components weighed');
  await expect(page.getByTestId('status-line')).toHaveText(
    'TARE REQUIRED — PRESS RE-TARE (F2)',
  );
  await expect(page.getByTestId('surplus-panel')).toBeHidden();
  await expect(page.getByTestId('btn-ok')).toBeDisabled();

  // Re-weigh: the emptied container is tared, then weighed into the band.
  await setWeight(request, 'scale-3kg', '0.0', 'g');
  await page.keyboard.press('F2');
  await expect(page.getByTestId('weigh-message')).toBeHidden();
  await page.getByRole('button', { name: '▶ Simulate dispense' }).click();
  await expect(page.getByTestId('btn-ok')).toBeEnabled();
  await page.keyboard.press('F1');
  await expect(page.getByTestId('rail-progress')).toHaveText('1 of 5 components weighed');
});

test('a kg component: Sodium Sulphate overshoot in kg', async ({ page }) => {
  await activeAndScanned(page, 4, 'Sodium Sulphate');

  await page.getByRole('button', { name: '▶ Simulate overshoot' }).click();

  await expect(page.getByTestId('weighed-now')).toHaveText('24.576');
  await expect(page.getByTestId('status-line')).toHaveText(
    'OVER TOLERANCE — SURPLUS +0.576 kg',
  );
  await expect(page.getByTestId('surplus-heading')).toHaveText(
    'Surplus +0.576 kg (+2.4%) — over tolerance',
  );
  await expect(page.getByTestId('btn-ok')).toBeDisabled();
});
