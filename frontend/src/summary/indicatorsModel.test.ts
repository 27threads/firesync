import example from '../../../docs/api-exemplo.json';
import type { CalendarResponse, Indicators } from '../api/types';
import { buildIndicators } from './indicatorsModel';

const indicators = (example as unknown as CalendarResponse).indicators;

describe('buildIndicators', () => {
  it('shows the total, the latest complete year against the typical year and the last 7 days', () => {
    expect(buildIndicators(indicators)).toEqual([
      { id: 'total', label: 'Detections in this period', value: '173,393', detail: 'On the VIIRS scale' },
      { id: 'year', label: '2025 vs. a typical year', value: '−41%', detail: '4,406 detections; typical year 7,460' },
      { id: 'recent', label: 'Last 7 days vs. typical', value: '+54%', detail: 'Same dates, other years' },
    ]);
  });

  it('leaves out the year when the period has no complete year', () => {
    const ids = buildIndicators({ ...indicators, latest_complete_year: null }).map((tile) => tile.id);
    expect(ids).toEqual(['total', 'recent']);
  });

  it('says when there is no reference to compare, instead of showing zero', () => {
    const noReference: Indicators = {
      total_detections: 10,
      latest_complete_year: { year: 2003, detections: 10, reference_median: null, anomaly_pct: null },
      last_7_days_vs_typical_pct: null,
    };
    const [, year, recent] = buildIndicators(noReference);
    expect(year.value).toBe('n/a');
    expect(year.detail).toBe('10 detections; no reference years');
    expect(recent.value).toBe('n/a');
  });
});
