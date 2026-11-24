// Stories 002/002 and 002/003 (bolt 014): the browser's write-back. B-24187 is
// weighed 5 of 5 through the terminal UI; then the page's own clients run
// writeBack: the station API supplies body and key, the OrgaTEX client posts
// to Dummy OrgaTEX (training contract), and the server decides the status.
// View 3 (bolt 017) will call the same writeBack. Since bolt 015 the 5th
// confirmation completes the batch and opens the write-back (pending, 0
// attempts), so the first writeBack is attempt 1.
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

async function consumptions(request) {
  const response = await request.get('/api/batches/B-24187/consumption');
  return (await response.json()).consumptions;
}

test('writeBack posts the consumption once and is CONFIRMED', async ({ page, request }) => {
  const sessionId = await weighAllB24187(page);

  const posted = page.waitForRequest(
    (r) => r.method() === 'POST' && r.url().endsWith('/api/batches/B-24187/consumption'),
  );
  const result = await runWriteBack(page, sessionId);
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
  const again = await runWriteBack(page, sessionId);
  expect(again.status).toBe('confirmed');
  expect(again.attempts).toBe(2);
  expect(await consumptions(request)).toHaveLength(1);
});

test('OrgaTEX unavailable: not written, then retry with the same key confirms', async ({
  page,
  request,
}) => {
  const sessionId = await weighAllB24187(page);
  await setMode(request, 'orgatex', 'unavailable');

  const failed = await runWriteBack(page, sessionId);

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
