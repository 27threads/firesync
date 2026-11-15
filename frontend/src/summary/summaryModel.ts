import { scaleLinear } from 'd3-scale';
import type { RecentWindow, SeasonalityMonth, YearSource, YearTotal } from '../api/types';
import { MONTH_NAMES } from '../calendar/calendarModel';
import { formatCount } from '../format';

export type TypicalStatus = 'above' | 'within' | 'below';

// Faixa do normal (P25–P75 das janelas de referência), ponta incluída: igual à mediana não é "acima".
export function compareToTypical(window: RecentWindow): TypicalStatus {
  if (window.detections > window.typical_p75) return 'above';
  if (window.detections < window.typical_p25) return 'below';
  return 'within';
}

export function rangeStripScale(window: RecentWindow, width: number) {
  const top = Math.max(window.detections, window.typical_p75) * 1.15;
  return scaleLinear().domain([0, top || 1]).range([0, width]);
}

const SOURCE_LABELS: Record<YearSource, string> = {
  observed_viirs: 'Observed (VIIRS)',
  estimated_modis: 'Estimated from MODIS',
  mixed: 'Mixed (MODIS + VIIRS)',
};

const SOURCE_PHRASES: Record<YearSource, string> = {
  observed_viirs: 'observed by VIIRS',
  estimated_modis: 'estimated from MODIS',
  mixed: 'mixed (MODIS + VIIRS)',
};

export function sourceLabel(source: YearSource): string {
  return SOURCE_LABELS[source];
}

export interface RankingRow {
  year: number;
  detections: number;
  bandLow: number | null;
  bandHigh: number | null;
  rankLabel: string | null;
  rangeText: string | null;
  source: YearSource;
  hatched: boolean;
  incomplete: boolean;
  label: string;
}

function toRankingRow(item: YearTotal): RankingRow {
  const hasBand = item.band_low !== null && item.band_high !== null;
  const incomplete = !item.complete;
  const rankLabel = incomplete || item.rank === null ? null : String(item.rank);

  const parts = [`${item.year}`, `${formatCount(item.detections)} detections${incomplete ? ' so far' : ''}`, SOURCE_PHRASES[item.source]];
  if (hasBand) parts.push(`range ${formatCount(item.band_low!)} to ${formatCount(item.band_high!)}`);
  if (incomplete) parts.push('incomplete year');

  return {
    year: item.year,
    detections: item.detections,
    bandLow: item.band_low,
    bandHigh: item.band_high,
    rankLabel,
    rangeText: hasBand ? `${formatCount(item.band_low!)}–${formatCount(item.band_high!)}` : null,
    source: item.source,
    hatched: item.source !== 'observed_viirs',
    incomplete,
    label: `${rankLabel ? `Rank ${rankLabel}` : 'Not ranked'}: ${parts.join(', ')}`,
  };
}

// A ordem vem da API (maior para o menor). O front não reordena.
export function buildRanking(years: YearTotal[]): RankingRow[] {
  return years.map(toRankingRow);
}

export interface SeasonalityRow {
  name: string;
  median: number;
  min: number;
  max: number;
}

export interface SeasonalityModel {
  months: SeasonalityRow[];
  peak: SeasonalityRow;
  maxValue: number;
  nYears: number | null; // null quando os meses têm números de anos diferentes
}

export function buildSeasonality(items: SeasonalityMonth[]): SeasonalityModel {
  const sorted = [...items].sort((a, b) => a.month_of_year - b.month_of_year);
  const months = sorted.map((m) => ({ name: MONTH_NAMES[m.month_of_year - 1], median: m.median, min: m.min, max: m.max }));
  const peak = months.reduce((best, m) => (m.median > best.median ? m : best));
  const counts = new Set(sorted.map((m) => m.n_years));
  return {
    months,
    peak,
    maxValue: Math.max(...months.map((m) => m.max)),
    nYears: counts.size === 1 ? sorted[0].n_years : null,
  };
}
