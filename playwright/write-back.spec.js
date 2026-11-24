// Stories 002/002 and 002/003 (bolt 014): the browser's write-back. B-24187 is
// weighed 5 of 5 through the terminal UI; the 5th confirmation completes the
// batch (bolt 015) and View 3 (bolt 017) runs writeBack by itself: the station
// API supplies body and key, the OrgaTEX client posts to Dummy OrgaTEX
// (training contract), and the server decides the status.
const { test, expect } = require('@playwright/test');
const { resetDatabase, resetModes, setMode, weighAllB24187 } = require('./helpers');

test.beforeEach(async ({ request }) => {
  resetDatabase();
  await resetModes(request);
});

test.afterEach(async ({ request }) => {
  await resetModes(request);
});

function runWriteBack(page, sessionId) {
  return page.evaluate((id) => window.WeighingMS.station.writeBack(id), sessionId);
}

function writeBackStatus(page, sessionId) {
  return page.evaluate((id) => window.WeighingMS.station.writeBackStatus(id), sessionId);
}

async function consumptions(request) {
  const response = await request.get('/api/batches/B-24187/consumption');
  return (await response.json()).consumptions;
}

test('completion posts the consumption once and is CONFIRMED', async ({ page, request }) => {
  const posted = page.waitForRequest(
    (r) => r.method() === 'POST' && r.url().endsWith('/api/batches/B-24187/consumption'),
  );
  const sessionId = await weighAllB24187(page);
  const body = (await posted).postDataJSON();
  const result = await writeBackStatus(page, sessionId);

  expect(result.status).toBe('confirmed');
  expect(result.confirmedAt).not.toBeNull();
  expect(result.attempts).toBe(1);
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
  const again = await runWriteBack(page, sessionId);
  expect(again.status).toBe('confirmed');
  expect(again.attempts).toBe(2);
  expect(await consumptions(request)).toHaveLength(1);
});

test('OrgaTEX unavailable: not written, then retry with the same key confirms', async ({
  page,
  request,
}) => {
  const sessionId = await weighAllB24187(page, {
    beforeLast: () => setMode(request, 'orgatex', 'unavailable'),
  });

  const failed = await writeBackStatus(page, sessionId);

  expect(failed.status).toBe('not_written');
  expect(failed.reason).toBe('OrgaTEX unavailable');
  expect(failed.confirmedAt).toBeNull();

  await setMode(request, 'orgatex', 'ok');
  const retried = await runWriteBack(page, sessionId);

  expect(retried.status).toBe('confirmed');
  expect(retried.idempotencyKey).toBe(failed.idempotencyKey);
  expect(retried.attempts).toBe(2);
  expect(await consumptions(request)).toHaveLength(1);
});
