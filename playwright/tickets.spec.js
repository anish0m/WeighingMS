// Stories 006/001 and 006/002 (bolt 016): the browser prints the server's
// ticket text on the Dummy Printer (training contract) through its printer
// client, and the server marks the job printed only after reading the ticket
// back. View 3's preview and Print ticket key come with bolt 017.
const { test, expect } = require('@playwright/test');
const { resetDatabase, resetModes, setMode, weighAllB24187 } = require('./helpers');

test.beforeEach(async ({ request }) => {
  resetDatabase();
  await resetModes(request);
});

test.afterEach(async ({ request }) => {
  await resetModes(request);
});

function printTicket(page, sessionId) {
  return page.evaluate((id) => window.WeighingMS.station.printTicket(id), sessionId);
}

test('Print ticket stores the ticket; the second print is a REPRINT', async ({
  page,
  request,
}) => {
  const sessionId = await weighAllB24187(page);
  const preview = await page.evaluate(
    (id) => window.WeighingMS.station.ticketPreview(id),
    sessionId,
  );

  const posted = page.waitForRequest(
    (r) => r.method() === 'POST' && r.url().endsWith('/api/tickets'),
  );
  const job = await printTicket(page, sessionId);
  const sent = (await posted).postDataJSON();

  expect(job.status).toBe('printed');
  expect(job.reprint).toBe(false);
  expect(sent.batchId).toBe('B-24187');
  expect(sent.content).toBe(preview.content);
  for (const text of [
    'FCI DYEING — WEIGHING TICKET',
    'BATCH   B-24187',
    'OPER.   R. Karim',
    'Remazol Yellow RGB',
    'ALL WITHIN TOLERANCE',
    '*B-24187*',
  ]) {
    expect(sent.content).toContain(text);
  }
  const stored = await (await request.get(`/api/tickets/${job.ticketId}`)).json();
  expect(stored.content).toBe(sent.content);

  const reprint = await printTicket(page, sessionId);
  expect(reprint.status).toBe('printed');
  expect(reprint.reprint).toBe(true);
  const again = await (await request.get(`/api/tickets/${reprint.ticketId}`)).json();
  expect(again.content.trimStart().startsWith('*** REPRINT ***')).toBe(true);
});

test('printer error: not printed; restored: printed, not a reprint', async ({
  page,
  request,
}) => {
  const sessionId = await weighAllB24187(page);
  await setMode(request, 'printer', 'error');

  const failed = await printTicket(page, sessionId);

  expect(failed.status).toBe('failed');
  expect(failed.ticketId).toBeNull();
  expect(failed.reason).toBeTruthy();

  await setMode(request, 'printer', 'ok');
  const printed = await printTicket(page, sessionId);

  expect(printed.status).toBe('printed');
  expect(printed.reprint).toBe(false);
});
