// Story 007/007 (bolt 017): View 3 · Confirm & print. Every value comes from
// the station API: the summary (bolt 015), the write-back status (bolt 014)
// and the ticket text and print result (bolt 016). Dummy OrgaTEX and the
// Dummy Printer are training contracts; their failures are switched through
// the training controls. Operator actions go through the terminal UI.
const { test, expect } = require('@playwright/test');
const { resetDatabase, resetModes, setMode, weighAllB24187 } = require('./helpers');

const OK = 'rgb(47, 191, 107)';
const OVER = 'rgb(232, 80, 58)';
const HHMMSS = /^CONFIRMED \d{2}:\d{2}:\d{2}$/;

test.beforeEach(async ({ request }) => {
  resetDatabase();
  await resetModes(request);
});

test.afterEach(async ({ request }) => {
  await resetModes(request);
});

async function consumptions(request) {
  const response = await request.get('/api/batches/B-24187/consumption');
  return (await response.json()).consumptions;
}

test('View 3 shows the summary from the API and CONFIRMED (AC 1, AC 2)', async ({
  page,
}) => {
  const sessionId = await weighAllB24187(page);
  const api = await page.evaluate(
    (id) => window.WeighingMS.station.summary(id),
    sessionId,
  );

  await expect(page.getByTestId('done-heading')).toHaveText('Batch B-24187 weighed');
  await expect(page.getByTestId('sum-components')).toHaveText(api.summary.componentsText);
  await expect(page.getByTestId('sum-components')).toHaveText('5 of 5');
  await expect(page.getByTestId('sum-within')).toHaveText('YES');
  await expect(page.getByTestId('sum-within')).toHaveCSS('color', OK);
  await expect(page.getByTestId('sum-total')).toHaveText(api.summary.totalDispensedText);
  await expect(page.getByTestId('sum-total')).toHaveText(/^\d+\.\d{3} kg$/);
  await expect(page.getByTestId('sum-elapsed')).toHaveText(api.summary.elapsedText);
  await expect(page.getByTestId('sum-elapsed')).toHaveText(/^\d+ min \d+ s$/);
  await expect(page.getByTestId('sum-operator')).toHaveText('R. Karim');
  await expect(page.getByTestId('sum-orgatex')).toHaveText(HHMMSS);
  await expect(page.getByTestId('sum-orgatex')).toHaveCSS('color', OK);
  await expect(page.getByTestId('done-note')).toHaveText(
    'Actual consumption posted against the batch. Container released for transport to JET-04.',
  );
  await expect(page.getByTestId('btn-retry-writeback')).toBeHidden();
  await expect(page.getByTestId('crumb')).toContainText('B-24187');
});

test('OrgaTEX unavailable: NOT WRITTEN with Retry; Retry after restore confirms (AC 2)', async ({
  page,
  request,
}) => {
  await weighAllB24187(page, {
    beforeLast: () => setMode(request, 'orgatex', 'unavailable'),
  });

  await expect(page.getByTestId('sum-orgatex')).toHaveText('NOT WRITTEN');
  await expect(page.getByTestId('sum-orgatex')).toHaveCSS('color', OVER);
  await expect(page.getByTestId('writeback-reason')).toHaveText(
    'Not written to OrgaTEX: OrgaTEX unavailable',
  );
  await expect(page.getByTestId('done-note')).toBeHidden();
  await expect(page.getByTestId('btn-retry-writeback')).toBeVisible();

  await setMode(request, 'orgatex', 'ok');
  await page.getByTestId('btn-retry-writeback').click();

  await expect(page.getByTestId('sum-orgatex')).toHaveText(HHMMSS);
  await expect(page.getByTestId('btn-retry-writeback')).toBeHidden();
  await expect(page.getByTestId('writeback-reason')).toBeHidden();
  expect(await consumptions(request)).toHaveLength(1);
});

test('Print ticket F1: the preview is the printed ticket; F1 again is a REPRINT (AC 3)', async ({
  page,
  request,
}) => {
  await weighAllB24187(page);
  const preview = page.getByTestId('ticket-preview');
  await expect(preview).toContainText('FCI DYEING — WEIGHING TICKET');
  const shown = await preview.innerText();

  const posted = page.waitForResponse(
    (r) => r.request().method() === 'POST' && r.url().endsWith('/api/tickets'),
  );
  await page.keyboard.press('F1');
  const ticket = await (await posted).json();

  await expect(page.getByTestId('print-result')).toHaveText(/^Ticket printed \d{2}:\d{2}:\d{2}$/);
  const stored = await (await request.get(`/api/tickets/${ticket.ticketId}`)).json();
  expect(stored.content.trimEnd()).toBe(shown.trimEnd());
  for (const text of ['BATCH   B-24187', 'Remazol Yellow RGB', 'ALL WITHIN TOLERANCE', '*B-24187*']) {
    expect(stored.content).toContain(text);
  }
  await expect(preview).toContainText('*** REPRINT ***');

  await page.getByTestId('btn-print').click();
  await expect(page.getByTestId('print-result')).toHaveText(/^REPRINT printed \d{2}:\d{2}:\d{2}$/);
});

test('printer error: the failure is shown; restored, the ticket prints (AC 3)', async ({
  page,
  request,
}) => {
  await weighAllB24187(page);
  await setMode(request, 'printer', 'error');

  await page.keyboard.press('F1');

  await expect(page.getByTestId('print-result')).toHaveText(
    'Printer error: ticket not printed',
  );
  await expect(page.getByTestId('print-result')).toHaveCSS('color', OVER);
  await expect(page.getByTestId('ticket-preview')).not.toContainText('REPRINT');

  await setMode(request, 'printer', 'ok');
  await page.keyboard.press('F1');

  await expect(page.getByTestId('print-result')).toHaveText(/^Ticket printed /);
});

test('Next batch F3 opens the queue; a reload then stays on the queue (AC 3)', async ({
  page,
}) => {
  await weighAllB24187(page);

  await page.keyboard.press('F3');

  await expect(page.locator('#v-queue')).toBeVisible();
  await expect(page.locator('#v-done')).toBeHidden();
  await expect(page.locator('tr[data-batch="B-24187"]')).toBeVisible();
  await page.reload();
  await expect(page.locator('#v-queue')).toBeVisible();
});

test('a reload on View 3 reopens it without a second write-back', async ({
  page,
  request,
}) => {
  await weighAllB24187(page);
  const confirmed = await page.getByTestId('sum-orgatex').innerText();

  await page.reload();

  await expect(page.locator('#v-done')).toBeVisible();
  await expect(page.getByTestId('done-heading')).toHaveText('Batch B-24187 weighed');
  await expect(page.getByTestId('sum-orgatex')).toHaveText(confirmed);
  await expect(page.getByTestId('done-note')).toContainText('JET-04');
  await expect(page.getByTestId('crumb')).toContainText('B-24187');
  await expect(page.getByTestId('ticket-preview')).toContainText('*B-24187*');
  expect(await consumptions(request)).toHaveLength(1);
});
