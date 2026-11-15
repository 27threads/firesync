import type { CalendarMonth, SeasonalityMonth, YearTotal } from '../api/types';
import { MONTH_NAMES } from '../calendar/calendarModel';

const SAFE_FILENAME_RE = /^[A-Za-z0-9._-]+$/;

/** Extracts and sanitizes a filename from an HTTP Content-Disposition header. */
export function parseContentDispositionFilename(header: string | null): string | null {
  if (!header) return null;

  const starMatch = header.match(/filename\*\s*=\s*UTF-8''([^;\s]+)/i);
  if (starMatch?.[1]) {
    try {
      const decoded = decodeURIComponent(starMatch[1].trim());
      if (SAFE_FILENAME_RE.test(decoded) && !decoded.includes('..')) {
        return decoded;
      }
    } catch {
      // Ignore malformed percent-encoding and try standard filename parameter.
    }
  }

  const quotedMatch = header.match(/filename\s*=\s*"([^"]+)"/i);
  if (quotedMatch?.[1]) {
    const candidate = quotedMatch[1].trim();
    return SAFE_FILENAME_RE.test(candidate) && !candidate.includes('..') ? candidate : null;
  }

  const plainMatch = header.match(/filename\s*=\s*([^;\s]+)/i);
  if (plainMatch?.[1]) {
    const candidate = plainMatch[1].trim();
    return SAFE_FILENAME_RE.test(candidate) && !candidate.includes('..') ? candidate : null;
  }

  return null;
}

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

/** Generates the UTC fallback filename firesync-YYYY-MM-DD.zip matching docs/api.md. */
export function defaultAuditFilenameUtc(now: Date = new Date()): string {
  const year = now.getUTCFullYear();
  const month = pad2(now.getUTCMonth() + 1);
  const day = pad2(now.getUTCDate());
  return `firesync-${year}-${month}-${day}.zip`;
}

function csvCell(value: string | number | boolean | null | undefined): string {
  if (value === null || value === undefined) return '';
  const text = String(value);
  if (text.includes(',') || text.includes('"') || text.includes('\n')) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function joinCsvRows(rows: (string | number | boolean | null | undefined)[][]): string {
  return `${rows.map((row) => row.map(csvCell).join(',')).join('\n')}\n`;
}

/** Converts months[] into result.csv format matching docs/api.md. */
export function buildMonthsCsv(months: CalendarMonth[]): string {
  const header = [
    'month',
    'detections',
    'band_low',
    'band_high',
    'source',
    'raw_count',
    'missing_days',
    'incomplete',
    'provisional',
    'anomaly',
    'anomaly_pct',
  ];
  const rows = months.map((m) => [
    m.month,
    m.detections,
    m.band_low,
    m.band_high,
    m.source,
    m.raw_count,
    m.missing_days,
    m.incomplete,
    m.provisional,
    m.anomaly,
    m.anomaly_pct,
  ]);
  return joinCsvRows([header, ...rows]);
}

/** Converts years[] (ranking by detections) into English CSV. */
export function buildYearsCsv(years: YearTotal[]): string {
  const header = ['year', 'detections', 'band_low', 'band_high', 'source', 'complete', 'rank'];
  const rows = years.map((y) => [y.year, y.detections, y.band_low, y.band_high, y.source, y.complete, y.rank]);
  return joinCsvRows([header, ...rows]);
}

/** Converts seasonality[] (12 months of the year) into English CSV. */
export function buildSeasonalityCsv(seasonality: SeasonalityMonth[]): string {
  const header = ['month_of_year', 'month_name', 'median', 'mean', 'min', 'max', 'n_years'];
  const rows = seasonality.map((s) => [
    s.month_of_year,
    MONTH_NAMES[s.month_of_year - 1] ?? String(s.month_of_year),
    s.median,
    s.mean,
    s.min,
    s.max,
    s.n_years,
  ]);
  return joinCsvRows([header, ...rows]);
}
