import { render, screen } from '@testing-library/react';
import { arrivalView, MapStage } from './MapStage';

describe('MapStage', () => {
  it('opens on a NASA GIBS base map, with another NASA GIBS map as the alternative', () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('offline'))));
    render(<MapStage shape={{ kind: 'bbox', bbox: [-74, -16.3, -43.9, 5.3] }} onSelectPolygon={vi.fn()} />);

    // O Blue Marble é a mesma imagem do fim da descida do globo, então a passagem não troca de mapa.
    expect(screen.getByRole('button', { name: /Blue Marble \(NASA GIBS\)/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Black Marble \(NASA GIBS\)/ })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.queryByRole('button', { name: /CARTO/ })).toBeNull();
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
