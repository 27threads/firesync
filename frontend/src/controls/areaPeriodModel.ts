import type { AreaInput, CalendarRequest, GeoJsonPolygon, PeriodInput, PointArea } from '../api/types';

export const DEFAULT_START_MONTH = '2003-01';
export const DEFAULT_END_MONTH = '2026-11';
// TODO(confirm): valor inicial do campo Radius (km) na entrada por coordenadas; faixa permitida 1–200 km definida no docs/api.md.
export const DEFAULT_RADIUS_KM = 25;
// TODO(confirm): enquadramento inicial da câmera do mapa (Brasil) antes de selecionar uma região de GET /regions; sem fonte numérica fixa nos docs.
export const DEFAULT_MAP_BBOX: [number, number, number, number] = [-74.0, -33.8, -34.8, 5.3];

const STALE_DATA_THRESHOLD_MS = 6 * 60 * 60 * 1000;
const YEAR_MONTH_RE = /^\d{4}-(0[1-9]|1[0-2])$/;

/** Ensures a GeoJSON coordinate ring has its closing vertex equal to its first vertex. */
export function closePolygonRing(ring: number[][]): number[][] {
  if (ring.length === 0) return [];
  const copy = ring.map(([lon, lat]) => [lon, lat]);
  const first = copy[0];
  const last = copy[copy.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) {
    copy.push([first[0], first[1]]);
  }
  return copy;
}

/** Converts a [west, south, east, north] bounding box into a closed GeoJSON Polygon in [lon, lat] order. */
export function bboxToPolygon(west: number, south: number, east: number, north: number): GeoJsonPolygon {
  const minLon = Math.min(west, east);
  const maxLon = Math.max(west, east);
  const minLat = Math.min(south, north);
  const maxLat = Math.max(south, north);
  return {
    type: 'Polygon',
    coordinates: [
      [
        [minLon, minLat],
        [maxLon, minLat],
        [maxLon, maxLat],
        [minLon, maxLat],
        [minLon, minLat],
      ],
    ],
  };
}

/** Builds the POST /api/v1/calendar request payload matching docs/api.md. */
export function buildCalendarRequest(area: AreaInput, period: PeriodInput = {}): CalendarRequest {
  let normalizedArea: AreaInput;
  if (area.type === 'geojson') {
    normalizedArea = {
      type: 'geojson',
      geometry: {
        type: 'Polygon',
        coordinates: area.geometry.coordinates.map(closePolygonRing),
      },
    };
  } else if (area.type === 'point') {
    normalizedArea = {
      type: 'point',
      lat: area.lat,
      lon: area.lon,
      radius_km: area.radius_km,
    };
  } else {
    normalizedArea = { type: 'region', region_id: area.region_id };
  }

  const request: CalendarRequest = { area: normalizedArea };
  if (period.start) request.start = period.start;
  if (period.end) request.end = period.end;
  return request;
}

export interface PointValidationErrors {
  lat?: string;
  lon?: string;
  radius?: string;
}

export type PointValidationResult =
  | { ok: true; value: PointArea }
  | { ok: false; errors: PointValidationErrors };

function parseFiniteNumber(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const num = Number(trimmed);
  return Number.isFinite(num) ? num : null;
}

/** Validates latitude (-90..90), longitude (-180..180), and radius_km (1..200). */
export function validatePointInput(latRaw: string, lonRaw: string, radiusRaw: string): PointValidationResult {
  const errors: PointValidationErrors = {};
  const lat = parseFiniteNumber(latRaw);
  const lon = parseFiniteNumber(lonRaw);
  const radius = parseFiniteNumber(radiusRaw);

  if (lat === null || lat < -90 || lat > 90) {
    errors.lat = 'Enter a latitude between -90 and 90.';
  }
  if (lon === null || lon < -180 || lon > 180) {
    errors.lon = 'Enter a longitude between -180 and 180.';
  }
  if (radius === null || radius < 1 || radius > 200) {
    errors.radius = 'Enter a radius between 1 and 200 km.';
  }

  if (errors.lat || errors.lon || errors.radius) {
    return { ok: false, errors };
  }
  return {
    ok: true,
    value: { type: 'point', lat: lat!, lon: lon!, radius_km: radius! },
  };
}

export type PeriodValidationResult =
  | { ok: true; value: { start: string; end: string } }
  | { ok: false; error: string };

/** Validates YYYY-MM period strings against [2003-01, lastMonth] and start <= end. */
export function validatePeriod(startRaw: string, endRaw: string, lastMonth: string): PeriodValidationResult {
  const start = startRaw.trim();
  const end = endRaw.trim();
  if (!YEAR_MONTH_RE.test(start) || !YEAR_MONTH_RE.test(end)) {
    return { ok: false, error: 'Use YYYY-MM format for start and end months.' };
  }
  if (start < DEFAULT_START_MONTH || start > lastMonth || end < DEFAULT_START_MONTH || end > lastMonth) {
    return { ok: false, error: `Period must be between ${DEFAULT_START_MONTH} and ${lastMonth}.` };
  }
  if (start > end) {
    return { ok: false, error: 'Start month must not be after end month.' };
  }
  return { ok: true, value: { start, end } };
}

/** Returns true when updated_at (UTC ISO timestamp) is strictly older than 6 hours (RNF07). */
export function isDataStale(updatedAt: string, nowMs: number = Date.now()): boolean {
  const parsed = Date.parse(updatedAt);
  if (!Number.isFinite(parsed)) return false;
  return nowMs - parsed > STALE_DATA_THRESHOLD_MS;
}
