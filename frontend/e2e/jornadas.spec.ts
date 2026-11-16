/**
 * Jornadas de usuário (E2E) do firesync.
 *
 * Cada teste é uma jornada inteira de quem usa o site, do jeito que o jurado e a equipe de resposta usam.
 * A API é simulada com o docs/api-exemplo.json, então as jornadas testam o front sozinho. Quando a API
 * existir, rodem também com FRONTEND_URL apontando para o site completo (sem a simulação).
 *
 * As jornadas rodam no desktop e no celular. Os seletores usam papéis e textos acessíveis
 * (getByRole, getByText), que também validam a acessibilidade pedida no RD04 e no RNF05.
 */
import { expect, Page, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const exemplo = JSON.parse(readFileSync(join(__dirname, '..', '..', 'docs', 'api-exemplo.json'), 'utf-8'));

const semFocos = { type: 'FeatureCollection', mode: 'points', hours: 24, updated_at: exemplo.meta.updated_at, total_detections: 0, features: [] };

async function simularApi(page: Page, calendar: object = exemplo, recent: object = semFocos) {
  await page.route('**/api/v1/health', (r) =>
    r.fulfill({ json: { status: 'ok', data_version: '2026-11-14', last_month: '2026-11', updated_at: exemplo.meta.updated_at, h3_resolution: 6 } }));
  await page.route('**/api/v1/regions', (r) =>
    r.fulfill({ json: [{ region_id: 1, name: 'Amazônia', source: 'IBGE', bbox: [-74.0, -16.3, -43.9, 5.3] }] }));
  await page.route('**/api/v1/calendar', (r) => r.fulfill({ json: calendar }));
  await page.route('**/api/v1/detections/recent**', (r) =>
    r.fulfill({ json: recent }));
}

test.describe('Jornadas do usuário', () => {
  test('J1: escolhe uma região pronta e vê o calendário de 2003 até hoje', async ({ page }) => {
    await simularApi(page);
    await page.goto('/');
    await page.getByRole('combobox', { name: /region/i }).selectOption({ label: 'Amazônia' });
    const calendario = page.getByRole('grid', { name: /fire calendar/i });
    await expect(calendario).toBeVisible();
    await expect(calendario.getByRole('row')).toHaveCount(1 + 24); // cabeçalho + 2003..2026
    await expect(page.getByText(/NASA FIRMS/).first()).toBeVisible(); // crédito visível (submissão)
  });

  test('J3: digita latitude, longitude e raio (RD02)', async ({ page }) => {
    await simularApi(page);
    const pedido = page.waitForRequest('**/api/v1/calendar');
    await page.goto('/');
    await page.getByText(/more options/i).click();
    await page.getByLabel(/latitude/i).fill('-3.1');
    await page.getByLabel(/longitude/i).fill('-60.0');
    await page.getByLabel(/radius/i).fill('25');
    await page.getByRole('button', { name: /search|show this area/i }).click();
    expect((await pedido).postDataJSON().area).toMatchObject({ type: 'point', lat: -3.1, lon: -60, radius_km: 25 });
  });

  test('J4: área fora da cobertura mostra aviso, nunca um calendário de zeros', async ({ page }) => {
    const fora = { meta: exemplo.meta, area: exemplo.area,
      coverage: { status: 'none', covered_fraction: 0, message: 'No data for this area yet. Current coverage: Brazil.' } };
    await simularApi(page, fora);
    await page.goto('/');
    await page.getByText(/more options/i).click();
    await page.getByLabel(/latitude/i).fill('48.8');
    await page.getByLabel(/longitude/i).fill('2.3');
    await page.getByRole('button', { name: /search|show this area/i }).click();
    await expect(page.getByText(/Current coverage: Brazil/)).toBeVisible();
    await expect(page.getByRole('grid', { name: /fire calendar/i })).toHaveCount(0);
  });

  test('J5: vê os últimos 7 dias contra o normal da época, com a hora da atualização', async ({ page }) => {
    await simularApi(page);
    await page.goto('/');
    await page.getByRole('combobox', { name: /region/i }).selectOption({ label: 'Amazônia' });
    const card = page.getByRole('region', { name: /last 7 days/i });
    await expect(card).toContainText(String(exemplo.recent.last_7_days.detections));
    await expect(card).toContainText(/\+54%/);
    await expect(page.getByText(/updated/i)).toBeVisible();
  });

  test('J6: mês estimado mostra a faixa de incerteza e o mês incompleto vem marcado', async ({ page }) => {
    await simularApi(page);
    await page.goto('/');
    await page.getByRole('combobox', { name: /region/i }).selectOption({ label: 'Amazônia' });
    await page.getByRole('gridcell', { name: /2010.*Sep|Sep.*2010/ }).hover();
    await expect(page.getByRole('tooltip')).toContainText(/range/i);
    await expect(page.getByRole('gridcell', { name: /2026.*Nov|Nov.*2026/ })).toHaveAttribute('aria-label', /incomplete/i);
  });

  test('J7: baixa o pacote de auditoria (RF13)', async ({ page }) => {
    await simularApi(page);
    await page.route('**/api/v1/export', (r) =>
      r.fulfill({ status: 200, contentType: 'application/zip', body: Buffer.from('PK'), headers: { 'content-disposition': 'attachment; filename="firesync-2026-11-14.zip"' } }));
    await page.goto('/');
    await page.getByRole('combobox', { name: /region/i }).selectOption({ label: 'Amazônia' });
    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: /audit package/i }).click();
    expect((await download).suggestedFilename()).toMatch(/^firesync-\d{4}-\d{2}-\d{2}\.zip$/);
  });

  test('J8: dado velho (mais de 6 h) mostra aviso de desatualizado (RNF07)', async ({ page }) => {
    const velho = { ...exemplo, meta: { ...exemplo.meta, updated_at: '2026-11-13T00:00:00Z' } };
    await simularApi(page, velho);
    await page.clock.setFixedTime(new Date('2026-11-14T15:00:00Z'));
    await page.goto('/');
    await page.getByRole('combobox', { name: /region/i }).selectOption({ label: 'Amazônia' });
    await expect(page.getByRole('alert')).toContainText(/may be out of date/i);
  });

  test('J9: muitos pedidos seguidos mostram aviso amigável, não erro (RNF06)', async ({ page }) => {
    await simularApi(page);
    await page.route('**/api/v1/calendar', (r) =>
      r.fulfill({ status: 429, headers: { 'retry-after': '30' }, json: { error: { code: 'rate_limited', message: 'Too many requests. Try again in 30 seconds.' } } }));
    await page.goto('/');
    await page.getByRole('combobox', { name: /region/i }).selectOption({ label: 'Amazônia' });
    await expect(page.getByRole('alert')).toContainText(/try again in 30 seconds/i);
  });
});

