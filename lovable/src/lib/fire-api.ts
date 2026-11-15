import type { CalendarData } from './fire-data';

const base = import.meta.env['VITE_API_URL']?.replace(/\/$/, '');
export const apiConfigured = Boolean(base);
export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}
export async function apiRequest<T>(path: string, body?: unknown): Promise<T> {
  if (!base) throw new ApiError(0, 'Production API is not connected. Demo data remains available.');
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${base}/api/v1/${path}`, { signal: controller.signal, ...(body === undefined ? { method: 'GET' } : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) });
    if (!response.ok) throw new ApiError(response.status, response.status === 429 ? 'Request limit reached. Wait a moment and try again.' : `API unavailable (${response.status}). Try again or explore the example.`);
    return await response.json() as T;
  } finally { clearTimeout(timeout); }
}
export const getHealth = () => apiRequest<unknown>('health');
export type Region = { id?: number; region_id?: number; name: string };
export const getRegions = () => apiRequest<Region[] | { regions: Region[] }>('regions');
// Request envelopes must be confirmed against the production api.md before connection.
export const getCalendar = (selection: unknown) => apiRequest<CalendarData>('calendar', selection);
export const getRecent = () => apiRequest<unknown>('detections/recent');
