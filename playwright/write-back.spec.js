// Stories 002/002 and 002/003 (bolt 014): the browser's write-back. B-24187 is
// weighed 5 of 5 through the terminal UI; then the page's own clients run
// writeBack: the station API supplies body and key, the OrgaTEX client posts
// to Dummy OrgaTEX (training contract), and the server decides the status.
// View 3 (bolt 017) will call the same writeBack.
const { test, expect } = require('@playwright/test');
const { resetDatabase, resetModes, setMode, openB24187 } = require('./helpers');

test.beforeEach(async ({ request }) => {
  resetDatabase();
  await resetModes(request);
});

test.afterEach(async ({ request }) => {
  await resetModes(request);
});

async function scanExpected(page) {
  const code = (await page.getByTestId('component-meta').innerText()).split(' · ')[0];
  await expect(page.getByTestId('sim-scan-code')).toHaveValue(code);
  await page.getByTestId('sim-scan').click();
  await expect(page.getByTestId('scan-step')).toBeHidden();
}

// Weighs all five components: scan, Simulate dispense, F1.
async function weighAll(page) {
  await openB24187(page);
  for (let weighed = 1; weighed <= 5; weighed += 1) {
    await scanExpected(page);
    await page.getByTestId('sim-dispense').click();
    await expect(page.getByTestId('btn-ok')).toBeEnabled();
    await page.keyboard.press('F1');
    await expect(page.getByTestId('rail-progress')).toHaveText(
      `${weighed} of 5 components weighed`,
    );
  }
}

function runWriteBack(page) {
  return page.evaluate(async () => {
    const station = window.WeighingMS.station;
    const session = await station.currentSession();
    return station.writeBack(session.sessionId);
  });
}

async function consumptions(request) {
  const response = await request.get('/api/batches/B-24187/consumption');
  return (await response.json()).consumptions;
}

test('writeBack posts the consumption once and is CONFIRMED', async ({ page, request }) => {
  await weighAll(page);

  const posted = page.waitForRequest(
    (r) => r.method() === 'POST' && r.url().endsWith('/api/batches/B-24187/consumption'),
  );
  const result = await runWriteBack(page);
  const body = (await posted).postDataJSON();

  expect(result.status).toBe('confirmed');
  expect(result.confirmedAt).not.toBeNull();
  expect(body.idempotencyKey).toBe(result.idempotencyKey);
  expect(body.idempotencyKey).toMatch(/^WMS-B-24187-S\d+$/);
  expect(body.components.map((c) => c.code)).toEqual([
    'DYE-1180',
    'DYE-2204',
    'DYE-4471',
    'AUX-0101',
    'AUX-0107',
  ]);
  for (const component of body.components) {
    expect(typeof component.actualQty).toBe('string');
  }

  // Triggered again: already confirmed, nothing new in OrgaTEX.
  const again = await runWriteBack(page);
  expect(again.status).toBe('confirmed');
  expect(again.attempts).toBe(2);
  expect(await consumptions(request)).toHaveLength(1);
});

test('OrgaTEX unavailable: not written, then retry with the same key confirms', async ({
  page,
  request,
}) => {
  await weighAll(page);
  await setMode(request, 'orgatex', 'unavailable');

  const failed = await runWriteBack(page);

  expect(failed.status).toBe('not_written');
  expect(failed.reason).toBe('OrgaTEX unavailable');
  expect(failed.confirmedAt).toBeNull();

  await setMode(request, 'orgatex', 'ok');
  const retried = await runWriteBack(page);

  expect(retried.status).toBe('confirmed');
  expect(retried.idempotencyKey).toBe(failed.idempotencyKey);
  expect(retried.attempts).toBe(2);
  expect(await consumptions(request)).toHaveLength(1);
});
