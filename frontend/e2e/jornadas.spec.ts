/**
 * Jornadas de usuário (E2E) do firesync.
 *
 * Cada teste é uma jornada inteira de quem usa o site, do jeito que o jurado e a equipe de resposta usam.
 * A API é simulada com o docs/api-exemplo.json, então as jornadas testam o front sozinho. Quando a API
 * existir, rodem também com FRONTEND_URL apontando para o site completo (sem a simulação).
 *
 * As 11 jornadas (J1–J11) rodam no desktop e no celular. Os seletores usam papéis e textos acessíveis
 * (getByRole, getByText), que também validam a acessibilidade pedida no RD04 e no RNF05.
 */
import { expect, Page, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const exemplo = JSON.parse(readFileSync(join(__dirname, '..', '..', 'docs', 'api-exemplo.json'), 'utf-8'));

const semFocos = { type: 'FeatureCollection', mode: 'points', hours: 24, updated_at: exemplo.meta.updated_at, total_detections: 0, features: [] };

// Mapa recente em hexágonos como a API de hoje manda (sem os campos dos PRs #86 e #97).
const hexagono = {
  type: 'Feature',
  geometry: { type: 'Polygon', coordinates: [[[-60.31, -3.05], [-60.22, -2.97], [-60.11, -3.01], [-60.10, -3.12], [-60.19, -3.20], [-60.30, -3.16], [-60.31, -3.05]]] },
  properties: { h3: '85a8100ffffffff', detections: 37, n_low: 21, n_medium: 12, n_high: 4 },
};
const mapaSemAlertas = { type: 'FeatureCollection', mode: 'hexagons', h3_resolution: 5, hours: 24, updated_at: exemplo.meta.updated_at, total_detections: 37, features: [hexagono] };

// O mesmo mapa com o aviso antecipado (contrato dos PRs #86 e #97): uma célula com fogo e uma sem fogo agora.
const mapaComAlertas = {
  ...mapaSemAlertas,
  features: [{ ...hexagono, properties: { ...hexagono.properties, alert_cell: '84a8101ffffffff', alert_level: 'critical', risk_prob: 0.71, risk_tier: 'very_high' } }],
  alerts: {
    data_through: '2026-11-14', alert_rules_version: '1.1', unit: 'H3 resolution 4 cell (about 1,770 km2)', horizon_days: 14, overall_share: 0.042,
    priority: [
      { h3: '84a8101ffffffff', alert_level: 'critical', detections_7d: 46, typical_median: 7, share_followed_by_high: 0.266, center: [-60.2, -3.1], risk_prob: 0.71, risk_tier: 'very_high' },
      { h3: '848f2a3ffffffff', alert_level: null, detections_7d: null, typical_median: null, share_followed_by_high: null, center: [-55.5, -9.25], risk_prob: 0.62, risk_tier: 'very_high' },
    ],
    risk: {
      scored_at: '2026-11-14T06:12:00Z', data_ref: '2026-11-13', model_version: 'gbm-1', horizon_days: 14, rules_version: '1.0',
      tiers: [
        { tier: 'very_high', min_prob: 0.6, historical_share: 0.82 },
        { tier: 'high', min_prob: 0.4, historical_share: 0.46 },
        { tier: 'medium', min_prob: 0.2, historical_share: 0.27 },
        { tier: 'lower', min_prob: 0, historical_share: 0.03 },
      ],
    },
  },
};

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

  test('J2: desenha uma área no mapa e recebe o calendário dela', async ({ page }) => {
    await simularApi(page);
    const pedido = page.waitForRequest('**/api/v1/calendar');
    await page.goto('/');
    await page.getByRole('button', { name: /draw (a )?rectangle/i }).click();
    const mapa = page.getByRole('region', { name: /map/i });
    const box = (await mapa.boundingBox())!;
    await page.mouse.move(box.x + box.width * 0.4, box.y + box.height * 0.4);
    await page.mouse.down();
    await page.mouse.move(box.x + box.width * 0.6, box.y + box.height * 0.6);
    await page.mouse.up();
    const corpo = (await pedido).postDataJSON();
    expect(corpo.area.type).toBe('geojson');
    expect(corpo.area.geometry.type).toBe('Polygon');
    await expect(page.getByRole('grid', { name: /fire calendar/i })).toBeVisible();
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

  test('J10: vê onde olhar primeiro e o risco dos 14 dias, e vai até a célula sem fogo agora (RD08)', async ({ page }) => {
    await simularApi(page, exemplo, mapaComAlertas);
    await page.goto('/');
    const lista = page.getByRole('list', { name: /where to look first/i });
    await expect(lista.getByRole('button')).toHaveCount(2);
    await expect(lista.getByRole('button').first()).toContainText('Unusual for the season');
    const semFogo = lista.getByRole('button').nth(1);
    await expect(semFogo).toContainText('No fire now');
    await expect(semFogo).not.toContainText('Unusual');

    const legenda = page.getByRole('group', { name: /fire risk, next 14 days/i });
    await expect(legenda).toContainText('Scored on 14 Nov 2026, 06:12 UTC');
    await expect(legenda).toContainText('Very high: relevant fire (10+ detections) followed in 82% of past cases');
    await expect(legenda).toContainText('A frequency from the past, not a forecast.');
    await expect(legenda).toContainText(/not burned area/);

    // O center vem [lon, lat]: o mapa tem que ir até lon -55.5, lat -9.25, e pedir os focos dessa vista.
    const naCelula = page.waitForRequest((req) => {
      if (!req.url().includes('/api/v1/detections/recent')) return false;
      const [w, s, e, n] = (new URL(req.url()).searchParams.get('bbox') ?? '').split(',').map(Number);
      return w < -55.5 && e > -55.5 && s < -9.25 && n > -9.25 && e - w < 10;
    });
    await semFogo.click();
    await naCelula;
  });

  test('J11: sem os campos novos da API, o mapa fica como antes, sem lista nem risco', async ({ page }) => {
    await simularApi(page, exemplo, mapaSemAlertas);
    await page.goto('/');
    await expect(page.getByText('37 VIIRS detections in view, last 24 h')).toBeVisible();
    await expect(page.getByText('Detections per hexagon (log scale)')).toBeVisible();
    await expect(page.getByText(/where to look first/i)).toHaveCount(0);
    await expect(page.getByText(/fire risk/i)).toHaveCount(0);
    await expect(page.getByText(/unusual for the season/i)).toHaveCount(0);
  });
});

