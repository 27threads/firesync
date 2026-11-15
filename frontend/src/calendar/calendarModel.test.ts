import type { CalendarMonth } from '../api/types';
import { buildCalendar } from './calendarModel';

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

describe('buildCalendar', () => {
  it('makes one row per year, from the first to the last month, with 12 cells each', () => {
    const calendar = buildCalendar([month({ month: '2011-11' }), month({ month: '2011-12' }), month({ month: '2012-01' })]);
    expect(calendar.years.map((row) => row.year)).toEqual([2011, 2012]);
    expect(calendar.years.every((row) => row.cells.length === 12)).toBe(true);
  });

  it('marks months outside the requested interval as not requested', () => {
    const calendar = buildCalendar([month({ month: '2011-11' }), month({ month: '2011-12' })]);
    expect(calendar.years[0].cells[0].state).toBe('not_requested');
    expect(calendar.years[0].cells[10].state).toBe('value');
  });

  it('keeps zero, missing data and a normal count as three different states', () => {
    const calendar = buildCalendar([
      month({ month: '2020-01', detections: 0, raw_count: 0 }),
      month({ month: '2020-02', detections: 0, raw_count: 0, missing_days: 29 }),
      month({ month: '2020-03', detections: 5 }),
    ]);
    const [jan, feb, mar] = calendar.years[0].cells;
    expect(jan.state).toBe('zero');
    expect(feb.state).toBe('no_data');
    expect(mar.state).toBe('value');
  });

  it('describes an estimated month with its uncertainty range', () => {
    const calendar = buildCalendar([
      month({ month: '2010-09', detections: 1234.4, band_low: 1100.2, band_high: 1400.7, source: 'estimated_modis' }),
    ]);
    const sep = calendar.years[0].cells[8];
    expect(sep.estimated).toBe(true);
    expect(sep.label).toBe('Sep 2010: 1,234 detections, estimated from MODIS (range 1,100 to 1,401)');
  });

  it('describes an observed month without a range', () => {
    const calendar = buildCalendar([month({ month: '2015-08', detections: 3021 })]);
    expect(calendar.years[0].cells[7].label).toBe('Aug 2015: 3,021 detections, observed by VIIRS');
  });

  it('flags incomplete and provisional months in the label', () => {
    const calendar = buildCalendar([month({ month: '2026-11', detections: 146, incomplete: true, provisional: true })]);
    expect(calendar.years[0].cells[10].label).toBe(
      'Nov 2026: 146 detections, observed by VIIRS, incomplete month, provisional (near real-time data)',
    );
  });

  it('keeps the provisional flag and the source month on each cell, for the marks and the detail panel', () => {
    const nov = month({ month: '2026-11', detections: 146, incomplete: true, provisional: true });
    const calendar = buildCalendar([nov]);
    expect(calendar.years[0].cells[10].provisional).toBe(true);
    expect(calendar.years[0].cells[10].month).toBe(nov);
    expect(calendar.years[0].cells[11].month).toBeNull();
    expect(calendar.years[0].cells[11].provisional).toBe(false);
  });

  it('says how many days are missing when a month has gaps', () => {
    const calendar = buildCalendar([month({ month: '2026-09', detections: 2132, missing_days: 4, incomplete: true })]);
    expect(calendar.years[0].cells[8].label).toMatch(/4 days without satellite data/);
  });

  it('labels a month without satellite data without a count', () => {
    const calendar = buildCalendar([month({ month: '2020-02', detections: 0, raw_count: 0, missing_days: 29 })]);
    expect(calendar.years[0].cells[1].label).toBe('Feb 2020: no satellite data');
  });

  it('finds the first month observed by VIIRS, where the sensor switch is drawn', () => {
    const calendar = buildCalendar([
      month({ month: '2012-01', source: 'estimated_modis' }),
      month({ month: '2012-02', source: 'observed_viirs' }),
    ]);
    expect(calendar.sensorSwitch).toEqual({ year: 2012, monthIndex: 1 });
  });

  it('has no sensor switch when the interval has a single source', () => {
    const calendar = buildCalendar([month({ month: '2015-01' }), month({ month: '2015-02' })]);
    expect(calendar.sensorSwitch).toBeNull();
  });

  it('returns the range of positive counts, used by the color scale', () => {
    const calendar = buildCalendar([
      month({ month: '2020-01', detections: 0 }),
      month({ month: '2020-02', detections: 3 }),
      month({ month: '2020-03', detections: 900 }),
    ]);
    expect(calendar.positiveExtent).toEqual([3, 900]);
  });
});
