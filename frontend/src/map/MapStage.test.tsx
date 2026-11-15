import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { arrivalView, MapStage } from './MapStage';

describe('MapStage', () => {
  it('opens on a NASA GIBS base map, with another NASA GIBS map as the alternative', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('offline'))));
    render(<MapStage shape={{ kind: 'bbox', bbox: [-74, -16.3, -43.9, 5.3] }} onSelectPolygon={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText(/recent hot spots are unavailable/i)).toBeInTheDocument();
    });

    // O Blue Marble é a mesma imagem do fim da descida do globo, então a passagem não troca de mapa.
    expect(screen.getByRole('button', { name: /Blue Marble \(NASA GIBS\)/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Black Marble \(NASA GIBS\)/ })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.queryByRole('button', { name: /CARTO/ })).toBeNull();
    vi.unstubAllGlobals();
  });

  it('on touch screens, lets one finger scroll the page (with a hint) and two fingers move/zoom the map', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('offline'))));
    vi.stubGlobal(
      'matchMedia',
      vi.fn((query: string) => ({
        matches: query === '(pointer: coarse)',
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      })),
    );
    vi.stubGlobal(
      'IntersectionObserver',
      class {
        observe(target: Element) {
          this.cb([{ isIntersecting: true, target } as IntersectionObserverEntry], this as unknown as IntersectionObserver);
        }
        disconnect() {}
        unobserve() {}
        takeRecords() {
          return [];
        }
        root = null;
        rootMargin = '';
        thresholds = [];
        constructor(private cb: IntersectionObserverCallback) {}
      },
    );

    render(<MapStage shape={{ kind: 'bbox', bbox: [-74, -16.3, -43.9, 5.3] }} onSelectPolygon={vi.fn()} />);

    const viewport = screen.getByRole('region', { name: /area selection map/i });
    await waitFor(() => {
      expect(viewport.querySelector('.leaflet-container')).not.toBeNull();
    });

    const container = viewport.querySelector('.leaflet-container')!;
    // 1 dedo rola a página (sem leaflet-touch-drag) e 2 dedos movem/dão zoom no mapa (com leaflet-touch-zoom).
    expect(container).toHaveClass('leaflet-touch-zoom');
    expect(container).not.toHaveClass('leaflet-touch-drag');

    // Arrasto com 1 dedo avisa que o mapa se move com 2 dedos.
    act(() => {
      fireEvent.touchStart(viewport, { touches: [{ clientX: 120, clientY: 180 }] });
      fireEvent.touchMove(viewport, { touches: [{ clientX: 120, clientY: 120 }] });
    });
    expect(screen.getByText(/use two fingers to move the map/i)).toBeInTheDocument();

    // Toque com 2 dedos esconde o aviso e entrega o gesto ao mapa.
    act(() => {
      fireEvent.touchStart(viewport, {
        touches: [
          { clientX: 100, clientY: 150 },
          { clientX: 200, clientY: 150 },
        ],
      });
    });
    expect(screen.queryByText(/use two fingers to move the map/i)).toBeNull();

    vi.unstubAllGlobals();
  });
});

describe('arrivalView', () => {
  it('starts the map where the globe opening ends, over Brazil, while the example is shown', () => {
    expect(arrivalView(true)).toEqual({ center: [-14, -52], zoom: 4 });
  });

  it('frames the area the user chose instead', () => {
    expect(arrivalView(false)).toBeNull();
  });
});
