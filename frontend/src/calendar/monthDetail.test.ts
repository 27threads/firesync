import type { CalendarMonth } from '../api/types';
import { describeMonth } from './monthDetail';

function month(overrides: Partial<CalendarMonth> & { month: string }): CalendarMonth {
  return {
    detections: 10,
    band_low: null,
    band_high: null,
    source: 'observed_viirs',
    raw_count: 10,
    missing_days: 0,
    incomplete: false,
    provisional: false,
    anomaly: null,
    anomaly_pct: null,
    ...overrides,
  };
}

describe('describeMonth (tooltip and month detail)', () => {
  it('shows an estimated month with its conversion range and raw MODIS count', () => {
    const d = describeMonth(
      month({ month: '2010-09', detections: 3503.4, band_low: 3301.2, band_high: 3790.9, source: 'estimated_modis', raw_count: 640, anomaly: 1200.5, anomaly_pct: 0.521 }),
    );
    expect(d.title).toBe('Sep 2010');
    expect(d.value).toBe('3,503 detections');
    expect(d.source).toBe('Estimated from MODIS Aqua, VIIRS scale');
    expect(d.range).toBe('Uncertainty range 3,301–3,791 (P5–P95)');
    expect(d.rawCount).toBe('640 raw MODIS Aqua detections before conversion');
    expect(d.anomaly).toBe('+1,201 (+52%) vs. the median for Sep');
  });

  it('gives observed VIIRS months no conversion range', () => {
    const d = describeMonth(month({ month: '2020-09', detections: 3483, source: 'observed_viirs', raw_count: 3483 }));
    expect(d.source).toBe('Observed by VIIRS');
    expect(d.range).toBeNull();
  });

  it('lists missing days, incomplete and provisional flags', () => {
    const d = describeMonth(month({ month: '2026-09', missing_days: 4, incomplete: true, provisional: true }));
    expect(d.flags).toEqual(['4 days without satellite data', 'Incomplete month', 'Provisional (near real-time data)']);
  });

  it('never shows a month without satellite data as zero', () => {
    const d = describeMonth(month({ month: '2020-02', detections: 0, missing_days: 29 }));
    expect(d.value).toBe('No satellite data');
  });

  it('shows a real zero as 0 detections', () => {
    expect(describeMonth(month({ month: '2020-03', detections: 0 })).value).toBe('0 detections');
  });

  it('leaves the anomaly empty for the current month (null from the API)', () => {
    expect(describeMonth(month({ month: '2026-11', anomaly: null, anomaly_pct: null })).anomaly).toBeNull();
  });

  it('writes the anomaly without a percentage when the median is zero', () => {
    expect(describeMonth(month({ month: '2019-03', anomaly: 12, anomaly_pct: null })).anomaly).toBe('+12 vs. the median for Mar');
  });
});
