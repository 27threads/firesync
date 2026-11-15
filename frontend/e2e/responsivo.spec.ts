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
    // O mapa só carrega quando aparece na tela.
    await page.locator('.map-stage').scrollIntoViewIfNeeded();
    const botoes = [
      page.getByRole('button', { name: 'Pause the globe' }),
      page.getByRole('button', { name: /^Chapter 1/ }),
      page.getByRole('button', { name: /^Question 1/ }),
      // O hero também tem um mapa com zoom: mede o do explorador, que é o que foi rolado até a tela.
      page.locator('.map-stage').getByRole('button', { name: 'Zoom in' }),
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

  test('R7: na tela de toque, 1 dedo no mapa permite rolar a página e 2 dedos movem o mapa', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'celular', 'só na tela de toque');
    await abrirSemApi(page, CELULAR);
    const viewport = page.getByRole('region', { name: /area selection map/i });
    await viewport.scrollIntoViewIfNeeded();
    const container = viewport.locator('.leaflet-container');
    await expect(container).toHaveClass(/leaflet-touch-zoom/);
    await expect(container).not.toHaveClass(/leaflet-touch-drag/);
    await expect(container).toHaveCSS('touch-action', 'pan-x pan-y');

    await viewport.evaluate((el) => {
      const touch = (x: number, y: number, id = 0) =>
        new Touch({ identifier: id, target: el, clientX: x, clientY: y, pageX: x, pageY: y });
      el.dispatchEvent(new TouchEvent('touchstart', { bubbles: true, cancelable: true, touches: [touch(150, 200)] }));
      el.dispatchEvent(new TouchEvent('touchmove', { bubbles: true, cancelable: true, touches: [touch(150, 140)] }));
    });
    await expect(page.getByText('Use two fingers to move the map.')).toBeVisible();
  });
});
