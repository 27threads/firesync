import { afterEach, describe, expect, it, vi } from 'vitest';
import example from '../../../docs/api-exemplo.json';
import {
  ApiClientError,
  fetchAuditPackage,
  fetchCalendar,
  fetchHealth,
  fetchRecentDetections,
  fetchRegions,
} from './client';
import type { CalendarResponse, NoCoverageResponse, RecentDetectionsResponse } from './types';

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

describe('API client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllEnvs();
  });

  it('fetches health metadata from /api/v1/health using VITE_API_URL when set', async () => {
    vi.stubEnv('VITE_API_URL', 'https://api.example.com/');
    const fetchMock = vi.fn().mockResolvedValue(
      jsonResponse({
        status: 'ok',
        data_version: '2026-11-14T19:48:30Z',
        last_month: '2026-11',
        updated_at: '2026-11-14T15:00:00Z',
        h3_resolution: 6,
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const health = await fetchHealth();
    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.com/api/v1/health',
      expect.objectContaining({ method: 'GET' }),
    );
    expect(health.last_month).toBe('2026-11');
  });

  it('fetches regions from same-origin /api/v1/regions when VITE_API_URL is empty', async () => {
    vi.stubEnv('VITE_API_URL', '');
    const regionsPayload = [
      { region_id: 1, name: 'Amazônia', source: 'IBGE, Biomas do Brasil 1:250.000', bbox: [-74.0, -16.3, -43.9, 5.3] },
    ];
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(regionsPayload));
    vi.stubGlobal('fetch', fetchMock);

    const regions = await fetchRegions();
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/regions', expect.objectContaining({ method: 'GET' }));
    expect(regions).toEqual(regionsPayload);
  });

  it('posts /api/v1/calendar with exact request JSON and returns calendar response', async () => {
    vi.stubEnv('VITE_API_URL', '');
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(example));
    vi.stubGlobal('fetch', fetchMock);

    const payload = { area: { type: 'region' as const, region_id: 1 }, start: '2003-01', end: '2026-11' };
    const result = await fetchCalendar(payload);

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/calendar',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    );
    expect((result as CalendarResponse).indicators.total_detections).toBe(example.indicators.total_detections);
  });

  it('returns coverage status "none" responses without throwing', async () => {
    const noCoverage: NoCoverageResponse = {
      meta: example.meta,
      area: { type: 'point', n_cells: 0, area_km2: 0, biomes: [] },
      coverage: {
        status: 'none',
        covered_fraction: 0,
        message: 'No data for this area yet. Current coverage: Brazil.',
      },
    };
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse(noCoverage)));

    const result = await fetchCalendar({
      area: { type: 'point', lat: 48.8, lon: 2.3, radius_km: 25 },
      start: '2003-01',
      end: '2026-11',
    });
    expect(result.coverage?.status).toBe('none');
    expect(result.coverage?.message).toBe('No data for this area yet. Current coverage: Brazil.');
  });

  it('formats 429 rate_limited errors including Retry-After seconds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          { error: { code: 'rate_limited', message: 'Too many requests.' } },
          429,
          { 'Retry-After': '30' },
        ),
      ),
    );

    await expect(
      fetchCalendar({ area: { type: 'region', region_id: 1 }, start: '2003-01', end: '2026-11' }),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      status: 429,
      code: 'rate_limited',
      retryAfter: 30,
      message: expect.stringMatching(/30 seconds/i),
    });
  });

  it('preserves contract error code and message for invalid_geometry, area_too_large, and invalid_period', async () => {
    for (const [status, code, message] of [
      [400, 'invalid_geometry', 'The drawn polygon has self-intersecting edges.'],
      [413, 'area_too_large', 'The selected area is too large. Draw a smaller area.'],
      [400, 'invalid_period', 'Period must be between 2003-01 and 2026-11.'],
    ] as const) {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ error: { code, message } }, status)));

      let caught: unknown;
      try {
        await fetchCalendar({ area: { type: 'region', region_id: 1 }, start: '2003-01', end: '2026-11' });
      } catch (err) {
        caught = err;
      }
      expect(caught).toBeInstanceOf(ApiClientError);
      expect(caught).toMatchObject({ status, code, message });
    }
  });

  it('posts /api/v1/export with exact request JSON and preserves Content-Disposition filename', async () => {
    vi.stubEnv('VITE_API_URL', '');
    const zipBytes = new Uint8Array([0x50, 0x4b]);
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(zipBytes, {
        status: 200,
        headers: {
          'Content-Type': 'application/zip',
          'Content-Disposition': 'attachment; filename="firesync-2026-11-14.zip"',
        },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const payload = { area: { type: 'region' as const, region_id: 1 }, start: '2003-01', end: '2026-11' };
    const result = await fetchAuditPackage(payload);

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/export',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    );
    expect(result.filename).toBe('firesync-2026-11-14.zip');
    expect(result.blob.size).toBe(2);
  });

  it('falls back to UTC firesync-YYYY-MM-DD.zip when Content-Disposition header is absent on /api/v1/export', async () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-11-14T23:30:00-03:00')); // 2026-11-15 UTC
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(new Uint8Array([0x50, 0x4b]), {
          status: 200,
          headers: { 'Content-Type': 'application/zip' },
        }),
      ),
    );

    const result = await fetchAuditPackage({ area: { type: 'region', region_id: 1 }, start: '2003-01', end: '2026-11' });
    expect(result.filename).toBe('firesync-2026-11-15.zip');
    vi.useRealTimers();
  });

  it('handles 429 rate_limited and contract errors on /api/v1/export identically to /api/v1/calendar', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonResponse(
          { error: { code: 'rate_limited', message: 'Too many requests.' } },
          429,
          { 'Retry-After': '45' },
        ),
      ),
    );

    await expect(
      fetchAuditPackage({ area: { type: 'region', region_id: 1 }, start: '2003-01', end: '2026-11' }),
    ).rejects.toMatchObject({
      name: 'ApiClientError',
      status: 429,
      code: 'rate_limited',
      retryAfter: 45,
      message: expect.stringMatching(/45 seconds/i),
    });
  });

  it('fetches recent detections in hexagons mode from GET /api/v1/detections/recent preserving string H3 IDs', async () => {
    vi.stubEnv('VITE_API_URL', '');
    const hexagonsPayload: RecentDetectionsResponse = {
      type: 'FeatureCollection',
      mode: 'hexagons',
      h3_resolution: 5,
      hours: 168,
      updated_at: '2026-11-14T15:00:00Z',
      total_detections: 51588,
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [
              [
                [-60.31, -3.05],
                [-60.22, -3.14],
                [-60.09, -3.11],
                [-60.05, -2.99],
                [-60.14, -2.9],
                [-60.27, -2.93],
                [-60.31, -3.05],
              ],
            ],
          },
          properties: {
            h3: '85a8100ffffffff',
            detections: 37,
            n_low: 21,
            n_medium: 12,
            n_high: 4,
          },
        },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(hexagonsPayload));
    vi.stubGlobal('fetch', fetchMock);

    const response = await fetchRecentDetections({
      bbox: [-63.5, -6.0, -57.0, 0.5],
      hours: 168,
      zoom: 5,
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/detections/recent?bbox=-63.5,-6,-57,0.5&hours=168&zoom=5',
      expect.objectContaining({ method: 'GET' }),
    );
    expect(response.mode).toBe('hexagons');
    if (response.mode === 'hexagons') {
      expect(typeof response.features[0].properties.h3).toBe('string');
      expect(response.features[0].properties.h3).toBe('85a8100ffffffff');
    }
  });

  it('fetches recent detections in points mode defaulting hours to 24 and passing mode when provided', async () => {
    vi.stubEnv('VITE_API_URL', '');
    const pointsPayload: RecentDetectionsResponse = {
      type: 'FeatureCollection',
      mode: 'points',
      hours: 24,
      updated_at: '2026-11-14T15:00:00Z',
      total_detections: 3833,
      features: [
        {
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [-60.21, -3.12] },
          properties: {
            satellite: 'N20',
            acquired_utc: '2026-11-14T05:42:00Z',
            confidence: 'nominal',
            intensity: 'medium',
            daynight: 'N',
          },
        },
      ],
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(pointsPayload));
    vi.stubGlobal('fetch', fetchMock);

    const response = await fetchRecentDetections({
      bbox: [-61.0, -4.0, -59.5, -2.5],
      zoom: 8,
      mode: 'points',
    });

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/detections/recent?bbox=-61,-4,-59.5,-2.5&hours=24&zoom=8&mode=points',
      expect.objectContaining({ method: 'GET' }),
    );
    expect(response.mode).toBe('points');
    expect(response.total_detections).toBe(3833);
  });

  it('preserves contract errors invalid_bbox, invalid_hours, invalid_mode, and 429 on /api/v1/detections/recent', async () => {
    for (const [status, code, message] of [
      [400, 'invalid_bbox', 'bbox must have 4 numbers in west,south,east,north order.'],
      [400, 'invalid_hours', 'hours must be 24, 72, or 168.'],
      [400, 'invalid_mode', 'mode must be auto, hexagons, or points.'],
    ] as const) {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ error: { code, message } }, status)));
      await expect(
        fetchRecentDetections({ bbox: [-60, -4, -59, -3], hours: 24, zoom: 6 }),
      ).rejects.toMatchObject({
        name: 'ApiClientError',
        status,
        code,
        message,
      });
    }
  });

  it('gives up when the API does not answer in time, so the page never stays on Loading forever', async () => {
    vi.useFakeTimers();
    // Like a browser: a fetch that never answers rejects with the abort reason once its signal aborts.
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init: RequestInit) => new Promise((_, reject) => init.signal?.addEventListener('abort', () => reject(init.signal?.reason)))),
    );
    const caller = new AbortController(); // the explorer passes its own signal too
    const health = fetchHealth(caller.signal);
    const audit = fetchAuditPackage({ area: { type: 'region', region_id: 1 } });
    const checks = [expect(health).rejects.toMatchObject({ name: 'TimeoutError' }), expect(audit).rejects.toMatchObject({ name: 'TimeoutError' })];
    await vi.advanceTimersByTimeAsync(20_000);
    await Promise.all(checks);
    vi.useRealTimers();
  });

  it('still cancels at once when the caller aborts (a new area replaces the old request)', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init: RequestInit) => new Promise((_, reject) => init.signal?.addEventListener('abort', () => reject(init.signal?.reason)))),
    );
    const caller = new AbortController();
    const pending = fetchCalendar({ area: { type: 'region', region_id: 1 } }, caller.signal);
    caller.abort(new DOMException('replaced', 'AbortError'));
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  });
});
