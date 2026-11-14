import { buildCalendarRequest } from '../controls/areaPeriodModel';
import type { CalendarApiResult, CalendarRequest, HealthResponse, RegionOption } from './types';

export { buildCalendarRequest };

/** Typed API error carrying contract code, HTTP status, and Retry-After seconds when present. */
export class ApiClientError extends Error {
  readonly status: number;
  readonly code: string;
  readonly retryAfter: number | null;

  constructor(status: number, code: string, retryAfter: number | null, message: string) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

interface ContractErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
}

/** Resolves the API base URL from VITE_API_URL (empty = same origin). */
export function getApiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_URL ?? '';
  return raw.trim().replace(/\/+$/, '');
}

function parseRetryAfter(headerValue: string | null): number | null {
  if (!headerValue) return null;
  const parsed = Number.parseInt(headerValue.trim(), 10);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

async function parseErrorResponse(response: Response): Promise<ApiClientError> {
  const retryAfter = parseRetryAfter(response.headers.get('retry-after'));
  let code = 'http_error';
  let message = `Request failed with status ${response.status}.`;

  try {
    const body = (await response.json()) as ContractErrorPayload;
    if (body?.error?.code) code = body.error.code;
    if (body?.error?.message) message = body.error.message;
  } catch {
    // Non-JSON error bodies (e.g. proxy 502/503) fall back to generic HTTP status handling.
  }

  if (response.status === 429) {
    code = code === 'http_error' ? 'rate_limited' : code;
    if (retryAfter !== null && !message.includes(String(retryAfter))) {
      message = `${message.replace(/\.$/, '')}. Try again in ${retryAfter} seconds.`;
    }
  }

  return new ApiClientError(response.status, code, retryAfter, message);
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, init);
  if (!response.ok) {
    throw await parseErrorResponse(response);
  }
  return (await response.json()) as T;
}

/** Fetches API health metadata including last_month and updated_at. */
export function fetchHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return requestJson<HealthResponse>('/api/v1/health', { method: 'GET', signal });
}

/** Fetches ready-made selectable regions (biomes) from the API. */
export function fetchRegions(signal?: AbortSignal): Promise<RegionOption[]> {
  return requestJson<RegionOption[]>('/api/v1/regions', { method: 'GET', signal });
}

/** Fetches the harmonized fire calendar (or no-coverage status) for a requested area and period. */
export function fetchCalendar(request: CalendarRequest, signal?: AbortSignal): Promise<CalendarApiResult> {
  return requestJson<CalendarApiResult>('/api/v1/calendar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  });
}
