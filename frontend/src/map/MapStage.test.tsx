import { render, screen } from '@testing-library/react';
import { MapStage } from './MapStage';

describe('MapStage', () => {
  it('opens on a NASA GIBS base map, with another NASA GIBS map as the alternative', () => {
    vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('offline'))));
    render(<MapStage shape={{ kind: 'bbox', bbox: [-74, -16.3, -43.9, 5.3] }} onSelectPolygon={vi.fn()} />);

    expect(screen.getByRole('button', { name: /Black Marble \(NASA GIBS\)/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /Blue Marble \(NASA GIBS\)/ })).toHaveAttribute('aria-pressed', 'false');
    expect(screen.queryByRole('button', { name: /CARTO/ })).toBeNull();
    vi.unstubAllGlobals();
  });
});
