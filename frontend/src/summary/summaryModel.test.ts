import example from '../../../docs/api-exemplo.json';
import type { CalendarResponse, RecentWindow, YearTotal } from '../api/types';
import { buildRanking, buildSeasonality, compareToTypical, rangeStripScale, sourceLabel } from './summaryModel';

const response = example as unknown as CalendarResponse;

function windowWith(detections: number): RecentWindow {
  return { ...response.recent.last_7_days, detections };
}

describe('compareToTypical', () => {
  it('is "above" when the window is over the typical P75', () => {
    expect(compareToTypical(response.recent.last_7_days)).toBe('above');
  });

  it('is "within" between P25 and P75, both ends included', () => {
    expect(compareToTypical(windowWith(40))).toBe('within');
    expect(compareToTypical(windowWith(35.2))).toBe('within');
    expect(compareToTypical(windowWith(45.5))).toBe('within');
  });

  it('is "below" under the typical P25', () => {
    expect(compareToTypical(windowWith(10))).toBe('below');
  });
});

describe('rangeStripScale', () => {
  it('starts at zero and leaves room for the largest of the current value and the typical range', () => {
    const scale = rangeStripScale(response.recent.last_7_days, 200);
    expect(scale(0)).toBe(0);
    expect(scale(61)).toBeLessThan(200);
    expect(scale(61)).toBeGreaterThan(scale(45.5));
  });
});

describe('sourceLabel', () => {
  it('names the origin of every kind of total', () => {
    expect(sourceLabel('observed_viirs')).toBe('Observed (VIIRS)');
    expect(sourceLabel('estimated_modis')).toBe('Estimated from MODIS');
    expect(sourceLabel('mixed')).toBe('Mixed (MODIS + VIIRS)');
  });
});

describe('buildRanking', () => {
  const rows = buildRanking(response.years);

  it('keeps the order of the API', () => {
    expect(rows.map((r) => r.year)).toEqual(response.years.map((y) => y.year));
  });

  it('gives a position only to complete years', () => {
    expect(rows[0]).toMatchObject({ year: 2024, rankLabel: '1' });
    expect(rows.find((r) => r.year === 2026)).toMatchObject({ rankLabel: null, incomplete: true });
  });

  it('shows the uncertainty range on estimated years and none on observed years', () => {
    expect(rows.find((r) => r.year === 2010)?.rangeText).toBe('11,105–12,253');
    expect(rows.find((r) => r.year === 2024)?.rangeText).toBeNull();
  });

  it('hatches estimated and mixed years, not observed ones', () => {
    expect(rows.find((r) => r.year === 2010)?.hatched).toBe(true);
    expect(rows.find((r) => r.year === 2012)?.hatched).toBe(true);
    expect(rows.find((r) => r.year === 2024)?.hatched).toBe(false);
  });

  it('describes each year in words for screen readers', () => {
    expect(rows.find((r) => r.year === 2010)?.label).toBe(
      'Rank 2: 2010, 11,832 detections, estimated from MODIS, range 11,105 to 12,253',
    );
    expect(rows.find((r) => r.year === 2012)?.label).toMatch(/^Rank 19: 2012, 5,636 detections, mixed \(MODIS \+ VIIRS\)/);
    expect(rows.find((r) => r.year === 2026)?.label).toBe(
      'Not ranked: 2026, 5,313 detections so far, observed by VIIRS, incomplete year',
    );
  });

  it('marks a year cut by the selected period as incomplete even if it is in the past', () => {
    const partial: YearTotal = { ...response.years[0], complete: false, rank: null };
    expect(buildRanking([partial])[0]).toMatchObject({ incomplete: true, rankLabel: null });
  });
});

describe('buildSeasonality', () => {
  const model = buildSeasonality(response.seasonality);

  it('has the 12 months in calendar order with their names', () => {
    expect(model.months.map((m) => m.name)).toEqual([
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ]);
  });

  it('finds the month with the highest median', () => {
    expect(model.peak).toMatchObject({ name: 'Sep', median: 2055.6 });
  });

  it('uses the largest yearly maximum as the top of the scale', () => {
    expect(model.maxValue).toBe(3503.4);
  });

  it('reports how many years entered, when all months agree', () => {
    expect(model.nYears).toBe(23);
  });
});
