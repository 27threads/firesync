import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { RegionOption } from '../api/types';
import { AreaPeriodControls } from './AreaPeriodControls';

const SAMPLE_REGIONS: RegionOption[] = [
  { region_id: 1, name: 'Amazônia', source: 'IBGE, Biomas do Brasil 1:250.000', bbox: [-74.0, -16.3, -43.9, 5.3] },
  { region_id: 5, name: 'Pantanal', source: 'IBGE, Biomas do Brasil 1:250.000', bbox: [-59.2, -22.2, -54.8, -15.6] },
];

describe('AreaPeriodControls', () => {
  it('populates the region select dynamically from API regions and submits the selected region', () => {
    const onSubmit = vi.fn();
    render(
      <AreaPeriodControls
        regions={[
          { region_id: 42, name: 'Dynamic Biome', source: 'IBGE', bbox: [-50, -15, -45, -10] },
        ]}
        lastMonth="2026-11"
        activeArea={null}
        onSubmitRequest={onSubmit}
      />,
    );

    const select = screen.getByRole('combobox', { name: /region/i });
    expect(screen.queryByRole('option', { name: 'Amazônia' })).toBeNull();
    fireEvent.change(select, { target: { value: '42' } });

    expect(onSubmit).toHaveBeenCalledWith({
      area: { type: 'region', region_id: 42 },
      start: '2003-01',
      end: '2026-11',
    });
  });

  it('validates lat/lon/radius with accessible aria-describedby errors and submits point requests when valid', () => {
    const onSubmit = vi.fn();
    render(
      <AreaPeriodControls
        regions={SAMPLE_REGIONS}
        lastMonth="2026-11"
        activeArea={null}
        onSubmitRequest={onSubmit}
      />,
    );

    const latInput = screen.getByLabelText(/latitude/i);
    const lonInput = screen.getByLabelText(/longitude/i);
    const radiusInput = screen.getByLabelText(/radius/i);
    const submitButton = screen.getByRole('button', { name: /show|search/i });

    fireEvent.change(latInput, { target: { value: '95' } });
    fireEvent.change(lonInput, { target: { value: '-60' } });
    fireEvent.change(radiusInput, { target: { value: '25' } });
    fireEvent.click(submitButton);

    expect(onSubmit).not.toHaveBeenCalled();
    expect(latInput).toHaveAttribute('aria-invalid', 'true');
    const describedId = latInput.getAttribute('aria-describedby');
    expect(describedId).toBeTruthy();
    expect(document.getElementById(describedId!)).toHaveTextContent(/between -90 and 90/i);

    fireEvent.change(latInput, { target: { value: '-3.1' } });
    fireEvent.click(submitButton);

    expect(onSubmit).toHaveBeenCalledWith({
      area: { type: 'point', lat: -3.1, lon: -60, radius_km: 25 },
      start: '2003-01',
      end: '2026-11',
    });
  });

  it('blocks start after end or months outside 2003-01..last_month and attaches an accessible error message', () => {
    const onSubmit = vi.fn();
    render(
      <AreaPeriodControls
        regions={SAMPLE_REGIONS}
        lastMonth="2026-10"
        activeArea={{ type: 'region', region_id: 1 }}
        onSubmitRequest={onSubmit}
      />,
    );

    const startInput = screen.getByLabelText(/start month/i) as HTMLInputElement;
    const endInput = screen.getByLabelText(/end month/i) as HTMLInputElement;
    expect(startInput.value).toBe('2003-01');
    expect(endInput.value).toBe('2026-10');

    fireEvent.change(startInput, { target: { value: '2026-11' } });
    expect(onSubmit).not.toHaveBeenCalled();
    expect(startInput).toHaveAttribute('aria-invalid', 'true');
    const errorId = startInput.getAttribute('aria-describedby');
    expect(errorId).toBeTruthy();
    expect(document.getElementById(errorId!)).toHaveTextContent(/2003-01.*2026-10/);

    fireEvent.change(startInput, { target: { value: '2025-06' } });
    onSubmit.mockClear();
    fireEvent.change(endInput, { target: { value: '2025-01' } });
    expect(onSubmit).not.toHaveBeenCalled();
    expect(document.getElementById(errorId!)).toHaveTextContent(/after/i);

    fireEvent.change(endInput, { target: { value: '2025-12' } });
    expect(onSubmit).toHaveBeenCalledWith({
      area: { type: 'region', region_id: 1 },
      start: '2025-06',
      end: '2025-12',
    });
  });

  it('supports drawing a rectangle in the accessible map region and emits a closed GeoJSON Polygon in [lon, lat] order', () => {
    const onSubmit = vi.fn();
    render(
      <AreaPeriodControls
        regions={SAMPLE_REGIONS}
        lastMonth="2026-11"
        activeArea={null}
        onSubmitRequest={onSubmit}
      />,
    );

    const drawRectBtn = screen.getByRole('button', { name: /draw (a )?rectangle/i });
    expect(screen.getByRole('button', { name: /draw (a )?polygon/i })).toBeInTheDocument();
    const mapRegion = screen.getByRole('region', { name: /map/i });

    vi.spyOn(mapRegion, 'getBoundingClientRect').mockReturnValue({
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      width: 600,
      height: 400,
      right: 600,
      bottom: 400,
      toJSON: () => ({}),
    });

    fireEvent.click(drawRectBtn);
    fireEvent.mouseDown(mapRegion, { clientX: 200, clientY: 120 });
    fireEvent.mouseMove(mapRegion, { clientX: 350, clientY: 260 });
    fireEvent.mouseUp(mapRegion, { clientX: 350, clientY: 260 });

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const req = onSubmit.mock.calls[0][0];
    expect(req.area.type).toBe('geojson');
    expect(req.area.geometry.type).toBe('Polygon');
    const ring = req.area.geometry.coordinates[0];
    expect(ring).toHaveLength(5);
    expect(ring[0]).toEqual(ring[4]);
    // Longitude comes before latitude in GeoJSON (-74..-34 vs -34..6)
    expect(ring[0][0]).toBeLessThan(-30);
  });

  it('supports drawing a polygon via clicks and finishing it into a closed GeoJSON Polygon', () => {
    const onSubmit = vi.fn();
    render(
      <AreaPeriodControls
        regions={SAMPLE_REGIONS}
        lastMonth="2026-11"
        activeArea={null}
        onSubmitRequest={onSubmit}
      />,
    );

    const drawPolyBtn = screen.getByRole('button', { name: /draw (a )?polygon/i });
    const mapRegion = screen.getByRole('region', { name: /map/i });

    vi.spyOn(mapRegion, 'getBoundingClientRect').mockReturnValue({
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      width: 600,
      height: 400,
      right: 600,
      bottom: 400,
      toJSON: () => ({}),
    });

    fireEvent.click(drawPolyBtn);
    fireEvent.click(mapRegion, { clientX: 150, clientY: 100 });
    fireEvent.click(mapRegion, { clientX: 350, clientY: 100 });
    fireEvent.click(mapRegion, { clientX: 300, clientY: 250 });
    fireEvent.click(screen.getByRole('button', { name: /finish polygon/i }));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    const req = onSubmit.mock.calls[0][0];
    expect(req.area.type).toBe('geojson');
    expect(req.area.geometry.type).toBe('Polygon');
    const ring = req.area.geometry.coordinates[0];
    expect(ring).toHaveLength(4);
    expect(ring[0]).toEqual(ring[3]);
  });

  it('toggles recent hot spots layer and switches time window (24 h, 72 h, 7 days) calling GET /api/v1/detections/recent', async () => {
    const fetchMock = vi.fn().mockImplementation(async () =>
      new Response(
        JSON.stringify({
          type: 'FeatureCollection',
          mode: 'points',
          hours: 72,
          updated_at: '2026-11-14T15:00:00Z',
          total_detections: 128,
          features: [
            {
              type: 'Feature',
              geometry: { type: 'Point', coordinates: [-60.21, -3.12] },
              properties: {
                satellite: 'N20',
                acquired_utc: '2026-11-14T05:42:00Z',
                confidence: 'nominal',
                intensity: 'high',
                daynight: 'N',
              },
            },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } },
      ),
    );
    vi.stubGlobal('fetch', fetchMock);

    render(
      <AreaPeriodControls
        regions={SAMPLE_REGIONS}
        lastMonth="2026-11"
        activeArea={null}
        onSubmitRequest={vi.fn()}
      />,
    );

    const toggleBtn = screen.getByRole('button', { name: /recent hot spots/i });
    expect(toggleBtn).toHaveAttribute('aria-pressed', 'true');

    const windowSelect = screen.getByRole('combobox', { name: /recent hot spots window/i }) as HTMLSelectElement;
    expect(windowSelect.value).toBe('24');

    fireEvent.change(windowSelect, { target: { value: '72' } });
    expect(windowSelect.value).toBe('72');

    expect(await screen.findByText(/128 hot spots in view/i)).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringMatching(/\/api\/v1\/detections\/recent\?bbox=.*&hours=72&zoom=/),
      expect.objectContaining({ method: 'GET' }),
    );

    fireEvent.click(toggleBtn);
    expect(toggleBtn).toHaveAttribute('aria-pressed', 'false');
    vi.unstubAllGlobals();
  });
});
