import example from '../../../docs/api-exemplo.json';
import { ApiClientError } from '../api/client';
import type { CalendarResponse, NoCoverageResponse } from '../api/types';
import { classifyFailure, describeArea, resultFromResponse } from './explorerModel';

const data = example as unknown as CalendarResponse;

describe('explorer result states', () => {
  it('turns a full response into a ready state', () => {
    expect(resultFromResponse(data)).toEqual({ kind: 'ready', data });
  });

  it('turns coverage none into its own state, never a calendar of zeros', () => {
    const none: NoCoverageResponse = {
      meta: data.meta,
      area: data.area!,
      coverage: { status: 'none', covered_fraction: 0, message: 'No data for this area yet. Current coverage: Brazil.' },
    };
    expect(resultFromResponse(none)).toEqual({ kind: 'no_coverage', message: 'No data for this area yet. Current coverage: Brazil.' });
  });

  it('reads 429 as rate limited, keeping Retry-After', () => {
    const err = new ApiClientError(429, 'rate_limited', 30, 'Too many requests. Try again in 30 seconds.');
    expect(classifyFailure(err)).toEqual({ kind: 'rate_limited', message: 'Too many requests. Try again in 30 seconds.', retryAfter: 30 });
  });

  it('shows contract errors with the API message', () => {
    const err = new ApiClientError(413, 'area_too_large', null, 'The selected area is too large. Draw a smaller area.');
    expect(classifyFailure(err)).toEqual({ kind: 'error', message: 'The selected area is too large. Draw a smaller area.', code: 'area_too_large' });
  });

  it('treats a network failure or a proxy error page as API unavailable', () => {
    expect(classifyFailure(new TypeError('Failed to fetch'))).toEqual({ kind: 'api_unavailable' });
    expect(classifyFailure(new ApiClientError(502, 'http_error', null, 'Request failed with status 502.'))).toEqual({ kind: 'api_unavailable' });
  });
});

describe('area description', () => {
  it('describes each kind of area in plain words', () => {
    expect(describeArea({ type: 'point', lat: -3.1, lon: -60, radius_km: 25 })).toBe('25 km around -3.100, -60.000');
    expect(describeArea({ type: 'region', region_id: 1 }, [{ region_id: 1, name: 'Amazônia', source: 'IBGE', bbox: [0, 0, 1, 1] }])).toBe('Amazônia');
    expect(describeArea({ type: 'geojson', geometry: { type: 'Polygon', coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]] } })).toBe('Drawn area');
  });
});
