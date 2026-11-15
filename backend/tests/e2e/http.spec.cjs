// No intercepted API responses: browser -> Vite proxy -> FastAPI -> PostGIS fixture.
const { test, expect } = require('../../../frontend/e2e/node_modules/@playwright/test');
const { readFile } = require('node:fs/promises');

test('uses all five real endpoints and downloads the audit ZIP', async ({ page }) => {
  const calendarResponse = page.waitForResponse(r => r.url().includes('/api/v1/calendar') && r.status() === 200);
  await page.goto('/');
  const mapResponse = page.waitForResponse(r => r.url().includes('/api/v1/detections/recent') && r.status() === 200);
  await page.getByRole('combobox', { name: /region/i }).selectOption({ label: 'Synthetic demo' });
  const response = await calendarResponse;
  const calendar = await response.json();
  expect(calendar.area.biomes[0].name).toBe('Synthetic demo');
  expect(calendar.months[0].detections).toBe(15);
  await expect(page.getByRole('combobox', { name: /region/i })).toContainText('Synthetic demo');
  await expect(page.getByRole('grid', { name: /fire calendar/i })).toBeVisible();
  await expect(page.getByRole('region', { name: /last 7 days/i })).toContainText('7');
  await expect(page.getByText(/NASA FIRMS/).first()).toBeVisible();

  const map = await (await mapResponse).json();
  expect(map.type).toBe('FeatureCollection');
  expect(map.total_detections).toBeGreaterThan(0);

  const exported = page.waitForResponse(r => r.url().includes('/api/v1/export'));
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: /download audit package/i }).click();
  expect((await exported).status()).toBe(200);
  const file = await download;
  expect(file.suggestedFilename()).toMatch(/^firesync-\d{4}-\d{2}-\d{2}\.zip$/);
  const bytes = await readFile(await file.path());
  expect(bytes.subarray(0, 2).toString()).toBe('PK');
  expect(bytes.includes(Buffer.from('metadata.json'))).toBe(true);
  expect(bytes.includes(Buffer.from('detections.csv'))).toBe(true);

  await page.getByText(/more options/i).click();
  await page.getByLabel(/latitude/i).fill('48.8');
  await page.getByLabel(/longitude/i).fill('2.3');
  await page.getByRole('button', { name: /search|show this area/i }).click();
  await expect(page.getByRole('grid', { name: /fire calendar/i })).toHaveCount(0);
  await expect(page.getByText(/Current coverage: Brazil/)).toBeVisible();
});
