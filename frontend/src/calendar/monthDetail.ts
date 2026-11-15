import type { CalendarMonth } from '../api/types';
import { formatCount, formatSignedPct } from '../format';
import { MONTH_NAMES } from './calendarModel';

export interface MonthDescription {
  title: string;
  value: string;
  source: string;
  range: string | null;
  rawCount: string;
  anomaly: string | null;
  flags: string[];
}

function daysInMonth(year: number, monthIndex: number): number {
  return new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();
}

function signedCount(value: number): string {
  const rounded = Math.round(value);
  if (rounded === 0) return '0';
  return `${rounded > 0 ? '+' : '−'}${formatCount(Math.abs(rounded))}`;
}

export function describeMonth(m: CalendarMonth): MonthDescription {
  const [year, monthNumber] = m.month.split('-').map(Number);
  const name = MONTH_NAMES[monthNumber - 1];
  const estimated = m.source === 'estimated_modis';
  const noData = m.missing_days >= daysInMonth(year, monthNumber - 1);

  const flags: string[] = [];
  if (m.missing_days > 0 && !noData) {
    flags.push(`${m.missing_days} ${m.missing_days === 1 ? 'day' : 'days'} without satellite data`);
  }
  if (m.incomplete) flags.push('Incomplete month');
  if (m.provisional) flags.push('Provisional (near real-time data)');

  let anomaly: string | null = null;
  if (m.anomaly !== null) {
    const pct = m.anomaly_pct !== null ? ` (${formatSignedPct(m.anomaly_pct)})` : '';
    anomaly = `${signedCount(m.anomaly)}${pct} vs. the median for ${name}`;
  }

  return {
    title: `${name} ${year}`,
    value: noData ? 'No satellite data' : `${formatCount(m.detections)} detections`,
    source: estimated ? 'Estimated from MODIS Aqua, VIIRS scale' : 'Observed by VIIRS',
    range:
      estimated && m.band_low !== null && m.band_high !== null
        ? `Uncertainty range ${formatCount(m.band_low)}–${formatCount(m.band_high)} (P5–P95)`
        : null,
    rawCount: `${formatCount(m.raw_count)} raw ${estimated ? 'MODIS Aqua' : 'VIIRS'} detections${estimated ? ' before conversion' : ''}`,
    anomaly,
    flags,
  };
}
