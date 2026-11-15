import type { Indicators } from '../api/types';
import { formatCount, formatSignedPct } from '../format';

export interface IndicatorTile {
  id: 'total' | 'year' | 'recent';
  label: string;
  value: string;
  detail: string;
}

// Indicadores em destaque (RD06): os números vêm prontos da API; o front só formata.
export function buildIndicators(indicators: Indicators): IndicatorTile[] {
  const tiles: IndicatorTile[] = [
    { id: 'total', label: 'Detections in this period', value: formatCount(indicators.total_detections), detail: 'On the VIIRS scale' },
  ];
  const year = indicators.latest_complete_year;
  if (year) {
    const reference = year.reference_median === null ? 'no reference years' : `typical year ${formatCount(year.reference_median)}`;
    tiles.push({
      id: 'year',
      label: `${year.year} vs. a typical year`,
      value: formatSignedPct(year.anomaly_pct),
      detail: `${formatCount(year.detections)} detections; ${reference}`,
    });
  }
  tiles.push({
    id: 'recent',
    label: 'Last 7 days vs. typical',
    value: formatSignedPct(indicators.last_7_days_vs_typical_pct),
    detail: 'Same dates, other years',
  });
  return tiles;
}
