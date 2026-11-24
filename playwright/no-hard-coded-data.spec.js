// Story 007/009 AC 2 (bolt 017): a changed seed shows after a reload. The
// Dummy OrgaTEX training data is changed in the E2E database itself (Node's
// built-in SQLite), not intercepted in the browser: the terminal can only
// show the new values if it reads them from the APIs. The pristine database
// is restored before and after each test.
const path = require('node:path');
const { DatabaseSync } = require('node:sqlite');
const { test, expect } = require('@playwright/test');
const { resetDatabase, resetModes, openAsOperator, openB24187 } = require('./helpers');

const E2E_DB = path.join(__dirname, '.cache', 'e2e.sqlite3');

test.beforeEach(async ({ request }) => {
  resetDatabase();
  await resetModes(request);
});

test.afterEach(() => {
  resetDatabase();
});

function changeSeed(sql, ...params) {
  const db = new DatabaseSync(E2E_DB);
  try {
    const result = db.prepare(sql).run(...params);
    expect(result.changes).toBe(1);
  } finally {
    db.close();
  }
}

test('a changed shade in the Dummy seed appears in the queue after a reload', async ({
  page,
}) => {
  await openAsOperator(page);
  const row = page.locator('tr[data-batch="B-24190"]');
  await expect(row.locator('td').nth(4)).toHaveText('Navy 12');

  changeSeed(
    'UPDATE dummy_orgatex_dummybatch SET shade = ? WHERE batch_id = ?',
    'Navy 14 (seed changed)',
    'B-24190',
  );
  await page.reload();

  await expect(row.locator('td').nth(4)).toHaveText('Navy 14 (seed changed)');
});

test('a changed target in the Dummy seed appears in View 2 after a reload', async ({
  page,
}) => {
  changeSeed(
    'UPDATE dummy_orgatex_dummyrecipecomponent SET target_qty = ? WHERE code = ?',
    '95.0',
    'DYE-4471',
  );
  await page.goto('/');

  await openB24187(page);

  const yellow = page.locator('.comp[data-sequence="3"]');
  await expect(yellow.locator('.qty')).toHaveText('95.0 g');
  await yellow.click();
  await expect(page.getByTestId('component-name')).toHaveText('Remazol Yellow RGB');
  await expect(page.getByTestId('target')).toHaveText('95.0');
  // The server derives the band from the new target (ADR-008).
  await expect(page.getByTestId('caption-band')).toContainText('94.5 – 95.5');
});
