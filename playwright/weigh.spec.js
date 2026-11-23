// Stories 007/003, 007/004, 007/005 (bolt 011): View 2 · Weigh, fed by the
// station API and the Dummy Scale / Scanner (training contracts). Weights are
// set with the Dummy Scale's training control; operator actions go through
// the terminal UI. Each test starts from the seeded database.
const { test, expect } = require('@playwright/test');
const {
  resetDatabase,
  resetModes,
  setWeight,
  openB24187,
} = require('./helpers');

const OK = 'rgb(47, 191, 107)';
const WARN = 'rgb(240, 167, 38)';
const OVER = 'rgb(232, 80, 58)';
const INK = 'rgb(233, 238, 244)';
const STEEL = 'rgb(91, 140, 196)';

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

// Simulate scan of the prefilled (expected) code through the training panel,
// once the panel has followed the active component.
async function scanExpected(page) {
  const code = (await page.getByTestId('component-meta').innerText()).split(' · ')[0];
  await expect(page.getByTestId('sim-scan-code')).toHaveValue(code);
  await page.getByTestId('sim-scan').click();
  await expect(page.getByTestId('scan-step')).toBeHidden();
}

// Yellow RGB active and verified, the scale at 0.0 g.
async function yellowReady(page) {
  await openB24187(page);
  await row(page, 3).click();
  await expect(page.getByTestId('component-name')).toHaveText('Remazol Yellow RGB');
  await scanExpected(page);
  await expect(page.getByTestId('weighed-now')).toHaveText('0.0');
}

async function showWeight(page, request, weight) {
  await setWeight(request, 'scale-3kg', weight, 'g');
  await expect(page.getByTestId('weighed-now')).toHaveText(weight);
}

// Pour (Simulate dispense), scan and confirm with F1 the active component.
async function weighActive(page, weighed) {
  await scanExpected(page);
  await page.getByTestId('sim-dispense').click();
  await expect(page.getByTestId('btn-ok')).toBeEnabled();
  await page.keyboard.press('F1');
  await expect(page.getByTestId('rail-progress')).toHaveText(
    `${weighed} of 5 components weighed`,
  );
}

test.describe('recipe rail and header (story 003)', () => {
  test('the rail shows Teal 4C, B-24187, the counter and the five components', async ({
    page,
  }) => {
    await openB24187(page);

    await expect(page.getByTestId('recipe-name')).toHaveText('Teal 4C');
    await expect(page.getByTestId('rail-batch')).toHaveText('B-24187');
    await expect(page.getByTestId('rail-progress')).toHaveText('0 of 5 components weighed');
    const rows = page.locator('.comp');
    await expect(rows.locator('.nm')).toHaveText([
      'Remazol Brill. Blue RSPL',
      'Remazol Red RB',
      'Remazol Yellow RGB',
      'Sodium Sulphate',
      'Soda Ash',
    ]);
    await expect(rows.locator('.sub')).toHaveText([
      'DYE-1180 · 3 kg',
      'DYE-2204 · 3 kg',
      'DYE-4471 · 3 kg',
      'AUX-0101 · 32 kg',
      'AUX-0107 · 32 kg',
    ]);
    await expect(rows.locator('.qty')).toHaveText([
      '1240.0 g',
      '386.0 g',
      '94.0 g',
      '24.000 kg',
      '9.600 kg',
    ]);
    await expect(rows.locator('.st')).toHaveText([
      'WEIGHING',
      'PENDING',
      'PENDING',
      'PENDING',
      'PENDING',
    ]);
    await expect(row(page, 1).locator('.swatch')).toHaveCSS(
      'background-color',
      'rgb(31, 79, 168)',
    );
  });

  test('rows show whatever the components API returns', async ({ page }) => {
    await page.route('**/station/api/sessions/*/components', async (route) => {
      const response = await route.fetch();
      const body = await response.json();
      body.components[0].name = 'Served by the API';
      await route.fulfill({ response, json: body });
    });

    await openB24187(page);

    await expect(row(page, 1).locator('.nm')).toHaveText('Served by the API');
  });

  test('Yellow RGB header shows code, lot, container and tare', async ({ page }) => {
    await openB24187(page);

    await row(page, 3).click();

    await expect(page.getByTestId('component-name')).toHaveText('Remazol Yellow RGB');
    await expect(page.getByTestId('component-meta')).toHaveText(
      'DYE-4471 · LOT 2026-0387 · CONTAINER C-12 · TARE 214 g',
    );
    await expect(row(page, 3)).toHaveAttribute('data-state', 'active');
    await expect(row(page, 1)).toHaveAttribute('data-state', 'pending');
  });

  test('touching a done row sends nothing and changes nothing', async ({ page }) => {
    await openB24187(page);
    await weighActive(page, 1);
    await expect(row(page, 1).locator('.st')).toHaveText('✓ 1242.4');
    const posts = [];
    page.on('request', (r) => {
      if (r.method() === 'POST') {
        posts.push(r.url());
      }
    });

    await row(page, 1).click();
    await page.waitForTimeout(500);

    expect(posts).toEqual([]);
    await expect(row(page, 1)).toHaveAttribute('data-state', 'done');
    await expect(row(page, 2)).toHaveAttribute('data-state', 'active');
  });

  test('scan dyestuff step: a mismatch shows "Wrong dyestuff" and blocks OK', async ({
    page,
    request,
  }) => {
    await openB24187(page);
    await row(page, 3).click();
    // Activation tares the scale; set the weight only after it.
    await expect(page.getByTestId('component-name')).toHaveText('Remazol Yellow RGB');
    await expect(page.getByTestId('weighed-now')).toHaveText('0.0');
    await expect(page.getByTestId('scan-step')).toBeVisible();
    await expect(page.getByTestId('scan-step')).toContainText('Scan dyestuff');
    await showWeight(page, request, '94.0');
    await expect(page.getByTestId('btn-ok')).toBeDisabled();
    // Within tolerance but unverified: the reason, never "PRESS OK TO CONFIRM".
    await expect(page.getByTestId('status-line')).toHaveText('Scan the dyestuff first');
    await expect(page.getByTestId('status-line')).toHaveAttribute('data-zone', 'blocked');
    await expect(page.getByTestId('status-line')).toHaveCSS('color', WARN);

    await page.getByTestId('sim-scan-code').fill('DYE-2204');
    await page.getByTestId('sim-scan').click();

    await expect(page.getByTestId('weigh-message')).toHaveText('Wrong dyestuff');
    await expect(page.getByTestId('scan-step')).toBeVisible();
    await expect(page.getByTestId('btn-ok')).toBeDisabled();
    await expect(page.getByTestId('status-line')).toHaveText('Wrong dyestuff');

    await page.getByTestId('sim-scan-code').fill('DYE-4471');
    await page.getByTestId('sim-scan').click();

    await expect(page.getByTestId('scan-step')).toBeHidden();
    await expect(page.getByTestId('weigh-message')).toBeHidden();
    await expect(page.getByTestId('btn-ok')).toBeEnabled();
    await expect(page.getByTestId('status-line')).toHaveText(
      'WITHIN TOLERANCE — PRESS OK TO CONFIRM',
    );
  });
});

test.describe('live readout and tolerance (story 004)', () => {
  test('the readout follows the Dummy Scale without a reload', async ({ page, request }) => {
    await yellowReady(page);
    const url = page.url();

    for (const weight of ['12.5', '80.0', '94.2']) {
      await setWeight(request, 'scale-3kg', weight, 'g');
      await expect(page.getByTestId('weighed-now')).toHaveText(weight, { timeout: 1000 });
    }

    expect(page.url()).toBe(url);
    await expect(page.getByTestId('fill')).toHaveAttribute('style', /width: 75\.4%/);
  });

  test('the active scale is polled at least every 200 ms (NFR-1)', async ({ page }) => {
    await yellowReady(page);
    const reads = [];
    page.on('request', (r) => {
      if (r.url().endsWith('/api/scales/scale-3kg/weight')) {
        reads.push(Date.now());
      }
    });

    await page.waitForTimeout(2000);

    expect(reads.length).toBeGreaterThanOrEqual(9);
    const gaps = reads.slice(1).map((t, i) => t - reads[i]);
    const sorted = [...gaps].sort((a, b) => a - b);
    expect(sorted[Math.floor(sorted.length / 2)]).toBeLessThanOrEqual(220);
  });

  test('Yellow RGB panel: target, still to weigh, caption, band and target line', async ({
    page,
  }) => {
    await yellowReady(page);

    await expect(page.getByTestId('target')).toHaveText('94.0');
    await expect(page.getByTestId('still-to-weigh')).toHaveText('94.0');
    await expect(page.locator('.readout .u').first()).toHaveText('g');
    await expect(page.getByTestId('caption-band')).toHaveText(
      'TOLERANCE ±0.5 g (93.5 – 94.5)',
    );
    await expect(page.getByTestId('caption-max')).toHaveText('125.0 g');
    await expect(page.getByTestId('band')).toHaveAttribute(
      'style',
      /left: 74\.8%; width: 0\.8%/,
    );
    await expect(page.getByTestId('target-line')).toHaveAttribute('style', /left: 75\.2%/);
    await expect(page.getByTestId('status-line')).toHaveText('DISPENSE — 94.0 g REMAINING');
  });

  const ZONES = [
    { weight: '50.0', zone: 'under', colour: INK, fill: STEEL, status: 'DISPENSE — 44.0 g REMAINING' },
    { weight: '90.0', zone: 'near', colour: WARN, fill: WARN, status: 'DISPENSE — 4.0 g REMAINING' },
    { weight: '94.2', zone: 'within', colour: OK, fill: OK, status: 'WITHIN TOLERANCE — PRESS OK TO CONFIRM' },
    { weight: '96.4', zone: 'over', colour: OVER, fill: OVER, status: 'OVER TOLERANCE — SURPLUS +2.4 g' },
  ];

  test('zones from the API colour the readout, bar and status line', async ({
    page,
    request,
  }) => {
    await yellowReady(page);

    for (const z of ZONES) {
      await showWeight(page, request, z.weight);
      await expect(page.getByTestId('bar')).toHaveAttribute('data-zone', z.zone);
      await expect(page.locator('.cell.live .v')).toHaveCSS('color', z.colour);
      await expect(page.getByTestId('fill')).toHaveCSS('background-color', z.fill);
      await expect(page.getByTestId('status-line')).toHaveText(z.status);
    }
    await expect(page.getByTestId('status-line')).toHaveCSS('color', OVER);
  });

  test('Sodium Sulphate switches to the 32 kg floor scale and kg', async ({ page }) => {
    await openB24187(page);

    await row(page, 4).click();

    await expect(page.getByTestId('scale-selected')).toContainText('Scale selected');
    await expect(page.getByTestId('scale-selected')).toContainText('32 kg floor');
    await expect(page.getByTestId('scale-selected')).toContainText('automatic');
    await expect(page.getByTestId('target')).toHaveText('24.000');
    await expect(page.locator('.readout .u')).toHaveText(['kg', 'kg', 'kg']);
    await expect(page.getByTestId('weighed-now')).toHaveText('0.000');
    await expect(page.getByTestId('caption-band')).toHaveText(
      'TOLERANCE ±0.120 kg (23.880 – 24.120)',
    );
    await expect(page.getByTestId('caption-max')).toHaveText('32.000 kg');
  });
});

test.describe('actions and function keys (story 005)', () => {
  const BOUNDARIES = [
    { weight: '93.4', enabled: false },
    { weight: '93.5', enabled: true },
    { weight: '94.0', enabled: true },
    { weight: '94.5', enabled: true },
    { weight: '94.6', enabled: false },
  ];

  test('OK · Confirm F1 is enabled only within tolerance (93.5 – 94.5)', async ({
    page,
    request,
  }) => {
    await yellowReady(page);

    for (const b of BOUNDARIES) {
      await showWeight(page, request, b.weight);
      const ok = page.getByTestId('btn-ok');
      if (b.enabled) {
        await expect(ok, b.weight).toBeEnabled();
      } else {
        await expect(ok, b.weight).toBeDisabled();
      }
    }
  });

  test('F1 at 94.6 g records nothing', async ({ page, request }) => {
    await yellowReady(page);
    await showWeight(page, request, '94.6');
    const confirms = [];
    page.on('request', (r) => {
      if (r.url().endsWith('/confirm')) {
        confirms.push(r.url());
      }
    });

    await page.keyboard.press('F1');
    await page.waitForTimeout(300);

    expect(confirms).toEqual([]);
    await expect(page.getByTestId('rail-progress')).toHaveText('0 of 5 components weighed');
  });

  test('F1 confirms: the record is shown and the next pending component is active', async ({
    page,
    request,
  }) => {
    await yellowReady(page);
    await showWeight(page, request, '94.2');

    await page.keyboard.press('F1');

    await expect(page.getByTestId('rail-progress')).toHaveText('1 of 5 components weighed');
    await expect(row(page, 3).locator('.st')).toHaveText('✓ 94.2');
    await expect(row(page, 1)).toHaveAttribute('data-state', 'active');
    await expect(page.getByTestId('component-name')).toHaveText('Remazol Brill. Blue RSPL');
  });

  test('F4 quits: nothing recorded, tare required; F2 re-tares to 0.0', async ({
    page,
    request,
  }) => {
    await yellowReady(page);
    await showWeight(page, request, '94.2');

    await page.keyboard.press('F4');

    await expect(page.getByTestId('status-line')).toHaveText(
      'TARE REQUIRED — PRESS RE-TARE (F2)',
    );
    await expect(page.getByTestId('btn-ok')).toBeDisabled();
    await expect(page.getByTestId('rail-progress')).toHaveText('0 of 5 components weighed');
    await expect(page.getByTestId('btn-retare')).toBeEnabled();

    await page.keyboard.press('F2');

    await expect(page.getByTestId('weighed-now')).toHaveText('0.0');
    await expect(page.getByTestId('status-line')).toHaveText('DISPENSE — 94.0 g REMAINING');
  });

  test('the buttons do what the keys do', async ({ page, request }) => {
    await yellowReady(page);
    await showWeight(page, request, '94.2');

    await page.getByTestId('btn-quit').click();
    await expect(page.getByTestId('status-line')).toHaveText(
      'TARE REQUIRED — PRESS RE-TARE (F2)',
    );
    await page.getByTestId('btn-retare').click();
    await expect(page.getByTestId('weighed-now')).toHaveText('0.0');
    await showWeight(page, request, '94.0');
    await page.getByTestId('btn-ok').click();

    await expect(row(page, 3).locator('.st')).toHaveText('✓ 94.0');
  });

  test('every action key is at least 57 px (15 mm)', async ({ page }) => {
    await yellowReady(page);

    for (const key of ['btn-ok', 'btn-retare', 'btn-quit', 'btn-override']) {
      const box = await page.getByTestId(key).boundingBox();
      expect(box.height, key).toBeGreaterThanOrEqual(57);
    }
    await expect(page.getByTestId('btn-ok')).toHaveText(/OK · Confirm\s*F1/);
    await expect(page.getByTestId('btn-retare')).toHaveText(/Re-tare\s*F2/);
    await expect(page.getByTestId('btn-quit')).toHaveText(/Quit\s*F4/);
  });

  test('Supervisor override is shown and disabled until STEP 24', async ({ page }) => {
    await yellowReady(page);

    await expect(page.getByTestId('btn-override')).toHaveText('Supervisor override');
    await expect(page.getByTestId('btn-override')).toBeDisabled();
  });
});

test.describe('the whole batch', () => {
  test('five components in recipe order; the floor scale takes over after Yellow RGB', async ({
    page,
  }) => {
    await openB24187(page);

    await weighActive(page, 1);
    await weighActive(page, 2);
    await expect(page.getByTestId('component-name')).toHaveText('Remazol Yellow RGB');
    await expect(page.getByTestId('scale-selected')).toContainText('3 kg precision');
    await weighActive(page, 3);
    await expect(page.getByTestId('component-name')).toHaveText('Sodium Sulphate');
    await expect(page.getByTestId('scale-selected')).toContainText('32 kg floor');
    await expect(page.getByTestId('weighed-now')).toHaveText('0.000');
    await weighActive(page, 4);
    await weighActive(page, 5);

    await expect(page.locator('.comp .st')).toHaveText([
      '✓ 1242.4',
      '✓ 386.8',
      '✓ 94.2',
      '✓ 24.048',
      '✓ 9.619',
    ]);
    await expect(page.getByTestId('btn-ok')).toBeDisabled();
    await expect(page.getByTestId('btn-retare')).toBeDisabled();
    await expect(page.getByTestId('btn-quit')).toBeDisabled();
  });

  test('a reload resumes at the in-progress component with 2 of 5 kept', async ({ page }) => {
    await openB24187(page);
    await weighActive(page, 1);
    await weighActive(page, 2);

    await page.reload();

    await expect(page.locator('#v-weigh')).toBeVisible();
    await expect(page.getByTestId('rail-progress')).toHaveText('2 of 5 components weighed');
    await expect(row(page, 3)).toHaveAttribute('data-state', 'active');
    await expect(page.getByTestId('component-name')).toHaveText('Remazol Yellow RGB');
    await expect(page.locator('.comp .st')).toHaveText([
      '✓ 1242.4',
      '✓ 386.8',
      'WEIGHING',
      'PENDING',
      'PENDING',
    ]);
    await expect(page.getByTestId('crumb')).toContainText('BATCH B-24187');
  });
});
