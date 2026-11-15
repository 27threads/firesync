import { ApiClientError } from '../api/client';
import type { AreaInput, CalendarApiResult, CalendarResponse, RegionOption } from '../api/types';

// Estados da área em análise. "Demo" e "API indisponível" mostram o JSON de exemplo,
// sempre rotulado; os outros estados nunca reaproveitam números de outra área.

export type ResultState =
  | { kind: 'demo' }
  | { kind: 'loading' }
  | { kind: 'ready'; data: CalendarResponse }
  | { kind: 'no_coverage'; message: string }
  | { kind: 'error'; message: string; code: string }
  | { kind: 'rate_limited'; message: string; retryAfter: number | null }
  | { kind: 'api_unavailable' };

export type FailureState = Extract<ResultState, { kind: 'error' | 'rate_limited' | 'api_unavailable' }>;

const NO_COVERAGE_FALLBACK = 'No data for this area yet.';

export function resultFromResponse(result: CalendarApiResult): ResultState {
  if (result.coverage?.status === 'none' || !('months' in result)) {
    return { kind: 'no_coverage', message: result.coverage?.message ?? NO_COVERAGE_FALLBACK };
  }
  return { kind: 'ready', data: result };
}

// Erro do contrato vem com JSON e código próprio; página de erro do proxy (502/503) ou falha de rede
// significam que a API não está no ar.
export function classifyFailure(err: unknown): FailureState {
  if (err instanceof ApiClientError) {
    if (err.status === 429) return { kind: 'rate_limited', message: err.message, retryAfter: err.retryAfter };
    if (err.code !== 'http_error') return { kind: 'error', message: err.message, code: err.code };
  }
  return { kind: 'api_unavailable' };
}

export function describeArea(area: AreaInput, regions: RegionOption[] = []): string {
  if (area.type === 'point') {
    return `${area.radius_km} km around ${area.lat.toFixed(3)}, ${area.lon.toFixed(3)}`;
  }
  if (area.type === 'region') {
    return regions.find((r) => r.region_id === area.region_id)?.name ?? `Region ${area.region_id}`;
  }
  return 'Drawn area';
}
