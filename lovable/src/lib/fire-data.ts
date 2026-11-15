import fixture from '@/data/demo-calendar.json';

export type Month = { month: string; detections: number | null; band_low: number | null; band_high: number | null; source: string; raw_count: number | null; missing_days: number; incomplete: boolean; provisional: boolean; anomaly: number | null; anomaly_pct: number | null };
export type CalendarData = Omit<typeof fixture, 'months'> & { months: Month[] };
export const demoData: CalendarData = fixture;
export const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const number = (n: number | null | undefined) => n == null ? 'Not available' : new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(n);
export const percent = (n: number | null | undefined) => n == null ? 'Not available' : new Intl.NumberFormat('en-US', { style: 'percent', maximumFractionDigits: 1, signDisplay: 'exceptZero' }).format(n);
export const monthLabel = (value: string) => new Date(`${value}-01T00:00:00Z`).toLocaleDateString('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' });
export const conversionBand = (m: Month) => m.source === 'estimated_modis' && m.band_low != null && m.band_high != null ? `${number(m.band_low)}–${number(m.band_high)}` : null;
export const rankedYears = (data: CalendarData) => data.years.filter(y => y.complete && y.rank != null).sort((a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity));
export function csv(rows: Record<string, unknown>[]) {
  const first = rows[0];
  if (!first) return '';
  const keys = Object.keys(first);
  const escape = (v: unknown) => `"${String(v ?? '').replaceAll('"', '""')}"`;
  return [keys.map(escape).join(','), ...rows.map(row => keys.map(k => escape(row[k])).join(','))].join('\r\n');
}
export function download(content: Blob | string, filename: string, type = 'text/csv;charset=utf-8') {
  const url = URL.createObjectURL(content instanceof Blob ? content : new Blob([content], { type }));
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}