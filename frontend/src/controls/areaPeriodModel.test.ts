import { describe, expect, it } from 'vitest';
import {
  bboxToPolygon,
  buildCalendarRequest,
  closePolygonRing,
  isDataStale,
  validatePeriod,
  validatePointInput,
} from './areaPeriodModel';

describe('closePolygonRing', () => {
  it('closes an open coordinate ring by repeating the first [lon, lat] point', () => {
    const open = [
      [-60.5, -3.5],
      [-59.5, -3.5],
      [-59.5, -2.5],
      [-60.5, -2.5],
    ];
    expect(closePolygonRing(open)).toEqual([
      [-60.5, -3.5],
      [-59.5, -3.5],
      [-59.5, -2.5],
      [-60.5, -2.5],
      [-60.5, -3.5],
    ]);
  });

  it('does not duplicate the closing coordinate when the ring is already closed', () => {
    const closed = [
      [-60.5, -3.5],
      [-59.5, -3.5],
      [-59.5, -2.5],
      [-60.5, -2.5],
      [-60.5, -3.5],
    ];
    expect(closePolygonRing(closed)).toEqual(closed);
  });
});

describe('bboxToPolygon', () => {
  it('builds a closed GeoJSON Polygon in [lon, lat] order from a bounding box', () => {
    expect(bboxToPolygon(-60.5, -3.5, -59.5, -2.5)).toEqual({
      type: 'Polygon',
      coordinates: [
        [
          [-60.5, -3.5],
          [-59.5, -3.5],
          [-59.5, -2.5],
          [-60.5, -2.5],
          [-60.5, -3.5],
        ],
      ],
    });
  });

  it('normalizes swapped coordinates regardless of drag direction', () => {
    expect(bboxToPolygon(-59.5, -2.5, -60.5, -3.5)).toEqual(bboxToPolygon(-60.5, -3.5, -59.5, -2.5));
  });
});

describe('buildCalendarRequest', () => {
  it('builds the contract payload for a preloaded region', () => {
    expect(buildCalendarRequest({ type: 'region', region_id: 1 }, { start: '2003-01', end: '2026-11' })).toEqual({
      area: { type: 'region', region_id: 1 },
      start: '2003-01',
      end: '2026-11',
    });
  });

  it('builds the contract payload for a geojson Polygon and ensures the ring is closed', () => {
    const request = buildCalendarRequest(
      {
        type: 'geojson',
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [-60.5, -3.5],
              [-59.5, -3.5],
              [-59.5, -2.5],
              [-60.5, -2.5],
            ],
          ],
        },
      },
      { start: '2003-01', end: '2026-11' },
    );

    expect(request).toEqual({
      area: {
        type: 'geojson',
        geometry: {
          type: 'Polygon',
          coordinates: [
            [
              [-60.5, -3.5],
              [-59.5, -3.5],
              [-59.5, -2.5],
              [-60.5, -2.5],
              [-60.5, -3.5],
            ],
          ],
        },
      },
      start: '2003-01',
      end: '2026-11',
    });
  });

  it('builds the contract payload for a point with radius_km', () => {
    expect(
      buildCalendarRequest({ type: 'point', lat: -3.1, lon: -60.0, radius_km: 25 }, { start: '2012-02', end: '2026-11' }),
    ).toEqual({
      area: { type: 'point', lat: -3.1, lon: -60, radius_km: 25 },
      start: '2012-02',
      end: '2026-11',
    });
  });
});

describe('validatePointInput', () => {
  it('accepts valid latitude, longitude, and radius values', () => {
    expect(validatePointInput('-3.1', '-60.0', '25')).toEqual({
      ok: true,
      value: { type: 'point', lat: -3.1, lon: -60, radius_km: 25 },
    });
    expect(validatePointInput('90', '180', '200').ok).toBe(true);
    expect(validatePointInput('-90', '-180', '1').ok).toBe(true);
  });

  it('rejects out-of-range or missing latitude, longitude, and radius with English messages', () => {
    const badLat = validatePointInput('91', '-60', '25');
    expect(badLat.ok).toBe(false);
    if (!badLat.ok) expect(badLat.errors.lat).toMatch(/between -90 and 90/i);

    const badLon = validatePointInput('-3', '-181', '25');
    expect(badLon.ok).toBe(false);
    if (!badLon.ok) expect(badLon.errors.lon).toMatch(/between -180 and 180/i);

    const badRadiusLow = validatePointInput('-3', '-60', '0');
    expect(badRadiusLow.ok).toBe(false);
    if (!badRadiusLow.ok) expect(badRadiusLow.errors.radius).toMatch(/between 1 and 200/i);

    const badRadiusHigh = validatePointInput('-3', '-60', '201');
    expect(badRadiusHigh.ok).toBe(false);
    if (!badRadiusHigh.ok) expect(badRadiusHigh.errors.radius).toMatch(/between 1 and 200/i);

    const emptyAll = validatePointInput('', ' ', '');
    expect(emptyAll.ok).toBe(false);
    if (!emptyAll.ok) {
      expect(emptyAll.errors.lat).toBeTruthy();
      expect(emptyAll.errors.lon).toBeTruthy();
      expect(emptyAll.errors.radius).toBeTruthy();
    }
  });
});

describe('validatePeriod', () => {
  it('accepts valid YYYY-MM periods within 2003-01 to last_month', () => {
    expect(validatePeriod('2003-01', '2026-11', '2026-11')).toEqual({
      ok: true,
      value: { start: '2003-01', end: '2026-11' },
    });
  });

  it('rejects start after end', () => {
    const res = validatePeriod('2020-05', '2020-04', '2026-11');
    expect(res.ok).toBe(false);
    if (!res.ok) expect(res.error).toMatch(/start.*after.*end|not be after/i);
  });

  it('rejects periods before 2003-01 or after last_month', () => {
    const before = validatePeriod('2002-12', '2026-11', '2026-11');
    expect(before.ok).toBe(false);
    if (!before.ok) expect(before.error).toMatch(/2003-01.*2026-11/);

    const after = validatePeriod('2003-01', '2026-12', '2026-11');
    expect(after.ok).toBe(false);
    if (!after.ok) expect(after.error).toMatch(/2003-01.*2026-11/);
  });

  it('rejects malformed months', () => {
    const invalid = validatePeriod('2020-13', '2026-11', '2026-11');
    expect(invalid.ok).toBe(false);
    if (!invalid.ok) expect(invalid.error).toMatch(/YYYY-MM/);
  });
});

describe('isDataStale', () => {
  it('returns true only when updated_at is more than 6 hours old (UTC)', () => {
    const now = Date.parse('2026-11-14T15:00:00Z');
    expect(isDataStale('2026-11-14T09:00:00Z', now)).toBe(false);
    expect(isDataStale('2026-11-14T08:59:59Z', now)).toBe(true);
    expect(isDataStale('2026-11-13T00:00:00Z', now)).toBe(true);
  });
});
