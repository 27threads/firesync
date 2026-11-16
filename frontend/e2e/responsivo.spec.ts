/**
 * Responsividade: o jurado pode abrir o site no celular ou no tablet.
 *
 * Sem API (modo demo): as medidas são de layout e não dependem dos dados.
 */
import { expect, Page, test } from '@playwright/test';

const CELULAR = { width: 375, height: 812 };
const TABLET = { width: 768, height: 1024 };

async function abrirSemApi(page: Page, viewport: { width: number; height: number }) {
  await page.route('**/api/v1/**', (r) => r.fulfill({ status: 502, body: '' }));
  await page.setViewportSize(viewport);
  await page.goto('/');
  await expect(page.locator('#explore .calendar-svg-root')).toBeAttached();
}

// Altura do texto na tela: tamanho da fonte vezes a escala do SVG.
async function menorTextoEmPx(page: Page, seletor: string): Promise<number> {
  await page.locator(seletor).first().scrollIntoViewIfNeeded();
  return page.locator(seletor).evaluateAll((svgs) =>
    Math.min(
      ...svgs.flatMap((svg) =>
        [...svg.querySelectorAll('text')]
          .filter((t) => t.getBoundingClientRect().width > 0)
          .map((t) => parseFloat(getComputedStyle(t).fontSize) * ((t as SVGGraphicsElement).getScreenCTM()?.a ?? 1)),
      ),
    ),
  );
}

test.describe('Responsividade', () => {
  test('R1: no tablet em pé, a abertura empilha o texto sobre o globo', async ({ page }) => {
    await abrirSemApi(page, TABLET);
    await expect(page.locator('.opening')).toHaveAttribute('data-layout', 'stacked');
  });

  test('R2: no desktop, a abertura põe o texto ao lado do globo', async ({ page }) => {
    await abrirSemApi(page, { width: 1280, height: 800 });
    await expect(page.locator('.opening')).toHaveAttribute('data-layout', 'side');
  });

  test('R3: no celular, o texto dos gráficos tem pelo menos 10 px', async ({ page }) => {
    await abrirSemApi(page, CELULAR);
    for (const seletor of ['#explore .calendar-svg-root', '#explore svg.chart']) {
      expect(await menorTextoEmPx(page, seletor), seletor).toBeGreaterThanOrEqual(10);
    }
  });

  test('R4: no celular, o calendário mostra os 12 meses sem rolar para o lado', async ({ page }) => {
    await abrirSemApi(page, CELULAR);
    const rolagem = page.locator('#explore .calendar-scroll');
    await rolagem.scrollIntoViewIfNeeded();
    const { scroll, visivel } = await rolagem.evaluate((el) => ({ scroll: el.scrollWidth, visivel: el.clientWidth }));
    expect(scroll).toBeLessThanOrEqual(visivel);
  });

  test('R5: na tela de toque, os botões pequenos têm pelo menos 44 px', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'celular', 'só na tela de toque');
    await abrirSemApi(page, CELULAR);
    const botoes = [
      page.getByRole('button', { name: /^Question 1/ }),
    ];
    for (const botao of botoes) {
      await botao.scrollIntoViewIfNeeded();
      const caixa = await botao.boundingBox();
      expect(caixa?.width, String(botao)).toBeGreaterThanOrEqual(44);
      expect(caixa?.height, String(botao)).toBeGreaterThanOrEqual(44);
    }
  });

  test('R6: a curva de detecção do Method abre em tamanho cheio', async ({ page }) => {
    await abrirSemApi(page, CELULAR);
    const link = page.getByRole('link', { name: /detection curve at full size/i });
    await expect(link).toHaveAttribute('href', '/img/curva_deteccao_2024.png');
  });

  test('R8: no celular, os controles do mapa do hero não se cobrem, com a legenda aberta ou fechada', async ({ page }) => {
    await abrirSemApi(page, CELULAR);
    // O mapa do hero só monta quando a abertura chega nele.
    await page.getByText('Explore an area', { exact: true }).first().click();
    await expect(page.locator('.hm-next')).toBeVisible({ timeout: 15_000 });
    const pares = [
      ['.hm-toolbar', '.hm-filters'],
      ['.hm-toolbar', '.hm-right'],
      ['.hm-legend', '.hm-next'],
      ['.hm-legend', '.hm-back'],
      ['.hm-zoom', '.hm-next'],
      ['.hm-zoom', '.hm-back'],
      ['.hm-next', '.hm-back'],
    ];
    const sobrepostos = () =>
      page.evaluate((lista) => {
        const caixa = (s: string) => document.querySelector(s)!.getBoundingClientRect();
        return lista
          .filter(([a, b]) => {
            const r1 = caixa(a);
            const r2 = caixa(b);
            return r1.left < r2.right && r2.left < r1.right && r1.top < r2.bottom && r2.top < r1.bottom;
          })
          .map((par) => par.join(' x '));
      }, pares);
    expect(await sobrepostos()).toEqual([]);
    await page.locator('.hm-legend__head').dispatchEvent('click');
    expect(await sobrepostos()).toEqual([]);
  });

  test('R11: em telas médias, o detalhe do mês e o calendário não ficam por cima da tabela', async ({ page }) => {
    await abrirSemApi(page, { width: 1100, height: 900 });
    await page.locator('#explore [role="gridcell"]').nth(20).click();
    const caixa = async (s: string) => (await page.locator(s).first().boundingBox())!;
    const tabela = await caixa('.cal-table-wrap');
    for (const s of ['.month-detail', '.calendar-scroll']) {
      const r = await caixa(s);
      const cobre = r.x < tabela.x + tabela.width && tabela.x < r.x + r.width && r.y < tabela.y + tabela.height && tabela.y < r.y + r.height;
      expect(cobre, s).toBe(false);
    }
  });

  test('R9: no celular, a página não rola para o lado', async ({ page }) => {
    await abrirSemApi(page, CELULAR);
    const { largura, visivel } = await page.evaluate(() => ({
      largura: document.body.scrollWidth,
      visivel: document.documentElement.clientWidth,
    }));
    expect(largura).toBeLessThanOrEqual(visivel);
  });

  test('R10: no celular, os números dos eixos dos gráficos não são cortados', async ({ page }) => {
    await abrirSemApi(page, CELULAR);
    await page.locator('#explore svg.chart').first().scrollIntoViewIfNeeded();
    const cortados = await page.locator('#explore svg.chart').evaluateAll((svgs) =>
      svgs.flatMap((svg) => {
        const borda = svg.getBoundingClientRect();
        return [...svg.querySelectorAll('text')]
          .filter((t) => {
            const r = t.getBoundingClientRect();
            return r.width > 0 && (r.left < borda.left - 0.5 || r.right > borda.right + 0.5);
          })
          .map((t) => t.textContent);
      }),
    );
    expect(cortados).toEqual([]);
  });
});
