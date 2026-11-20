// Story 007/002: View 1 · Select batch, fed only by the APIs (FR-21).
const { test, expect } = require('@playwright/test');
const { resetModes, setMode, scan, openAsOperator } = require('./helpers');

const COLUMNS = ['Batch', 'Order', 'Machine', 'Fabric / lot', 'Shade', 'Comp.', 'Status'];

test.beforeEach(async ({ request }) => {
  await resetModes(request);
});

test.afterEach(async ({ request }) => {
  await resetModes(request);
});

test('view 1 shows the prompt and one row per batch from GET /api/batches', async ({
  page,
  request,
}) => {
  const queueResponse = page.waitForResponse((r) => r.url().endsWith('/api/batches'));
  await openAsOperator(page);
  const queue = await (await queueResponse).json();
  const expected = (await (await request.get('/api/batches')).json()).batches;

  await expect(page.getByText('Scan a batch card to begin')).toBeVisible();
  await expect(page.getByTestId('queue-received')).toHaveText(
    /^\s*Or touch a row below\. Queue received from OrgaTEX at \d{2}:\d{2}\.\s*$/,
  );
  await expect(page.locator('table.q th')).toHaveText(COLUMNS);
  expect(queue.batches.map((b) => b.batchId)).toEqual([
    'B-24187',
    'B-24188',
    'B-24190',
    'B-24191',
  ]);
  const rows = page.locator('tr[data-batch]');
  await expect(rows).toHaveCount(expected.length);
  for (const [index, batch] of expected.entries()) {
    await expect(rows.nth(index).locator('td')).toHaveText([
      batch.batchId,
      batch.orderId,
      batch.machine,
      batch.fabricLot,
      batch.shade,
      String(batch.componentCount),
      batch.status,
    ]);
  }
});

test('rows show whatever the API returns: nothing is hard-coded', async ({ page }) => {
  await page.route('**/api/batches', (route) =>
    route.fulfill({
      json: {
        receivedAt: '2026-11-20T06:12:00Z',
        batches: [
          {
            batchId: 'B-90001',
            orderId: 'SO-0001',
            machine: 'JET-99',
            fabricLot: 'Test fabric',
            shade: 'Test shade',
            componentCount: 2,
            status: 'QUEUED',
          },
        ],
      },
    }),
  );

  await openAsOperator(page);

  await expect(page.locator('tr[data-batch]')).toHaveCount(1);
  await expect(page.locator('tr[data-batch="B-90001"] td').first()).toHaveText('B-90001');
});

test('touching B-24187 opens view 2 after the server selected it', async ({ page }) => {
  await openAsOperator(page);
  const calls = [];
  page.on('request', (r) => {
    const url = new URL(r.url());
    if (/^\/(station\/)?api\/(batches|selections|sessions)/.test(url.pathname)) {
      calls.push(`${r.method()} ${url.pathname}`);
    }
  });

  await page.locator('tr[data-batch="B-24187"]').click();

  await expect(page.locator('#v-weigh')).toBeVisible();
  await expect(page.locator('#v-queue')).toBeHidden();
  await expect(page.getByTestId('recipe-name')).toHaveText('Teal 4C');
  expect(calls).toEqual([
    'POST /station/api/selections',
    'POST /station/api/sessions',
    'GET /api/batches/B-24187',
    'GET /api/batches/B-24187/recipe',
  ]);
});

test('scanning the B-24187 batch card opens view 2', async ({ page, request }) => {
  await openAsOperator(page);
  const selection = page.waitForRequest(
    (r) => r.url().endsWith('/station/api/selections') && r.method() === 'POST',
  );
  await page.waitForTimeout(500); // let the scan watcher take its baseline

  await scan(request, 'batch', 'B-24187');

  expect((await selection).postDataJSON()).toEqual({ batchId: 'B-24187', method: 'scan' });
  await expect(page.getByTestId('recipe-name')).toHaveText('Teal 4C');
  await expect(page.getByTestId('crumb')).toContainText('BATCH B-24187');
});

test('B-24188 without a training recipe shows the reason and stays on view 1', async ({
  page,
}) => {
  await openAsOperator(page);

  await page.locator('tr[data-batch="B-24188"]').click();

  await expect(page.getByTestId('message')).toHaveText('Recipe not available in training data');
  await expect(page.locator('#v-queue')).toBeVisible();
  await expect(page.getByTestId('crumb')).toBeHidden();
});

test('scanning an unknown batch shows "Batch not found"', async ({ page, request }) => {
  await openAsOperator(page);
  await page.waitForTimeout(500);

  await scan(request, 'batch', 'B-99999');

  await expect(page.getByTestId('message')).toHaveText('Batch not found');
  await expect(page.locator('#v-queue')).toBeVisible();
});

test('a dyestuff scan on view 1 is ignored', async ({ page, request }) => {
  await openAsOperator(page);
  await page.waitForTimeout(500);

  await scan(request, 'dyestuff', 'DYE-4471');
  await page.waitForTimeout(800);

  await expect(page.locator('#v-queue')).toBeVisible();
  await expect(page.getByTestId('message')).toBeHidden();
});

test('OrgaTEX going down during selection shows "OrgaTEX unavailable"', async ({
  page,
  request,
}) => {
  await openAsOperator(page);
  await expect(page.locator('tr[data-batch="B-24187"]')).toBeVisible();

  await setMode(request, 'orgatex', 'unavailable');
  await page.locator('tr[data-batch="B-24187"]').click();

  await expect(page.getByTestId('message')).toHaveText('OrgaTEX unavailable');
  await expect(page.locator('#v-queue')).toBeVisible();
});
