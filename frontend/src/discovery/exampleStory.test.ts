import example from '../../../docs/api-exemplo.json';
import type { CalendarResponse } from '../api/types';
import { buildExampleStory } from './exampleStory';

const data = example as unknown as CalendarResponse;

describe('guided discovery built from the response fields', () => {
  const story = buildExampleStory(data);

  it('asks about the last 7 days and answers with the typical P25–P75 range', () => {
    const recent = story.find((s) => s.id === 'recent')!;
    expect(recent.question).toMatch(/last 7 days/i);
    expect(recent.answer).toContain('61 detections');
    expect(recent.answer).toContain('35.2–45.5');
    expect(recent.answer).toMatch(/above the typical range/i);
    expect(recent.answer).toContain('14 years');
  });

  it('names the month with the highest median from seasonality[]', () => {
    const season = story.find((s) => s.id === 'season')!;
    const peak = [...data.seasonality].sort((a, b) => b.median - a.median)[0];
    expect(season.monthIndex).toBe(peak.month_of_year - 1);
    expect(season.answer).toContain('Sep');
  });

  it('names the first-ranked complete year, never an incomplete one', () => {
    const ranked = story.find((s) => s.id === 'ranking')!;
    expect(ranked.year).toBe(2024);
    expect(ranked.answer).toContain('2024');
    expect(ranked.answer).toMatch(/observed by VIIRS/);
  });

  it('says "within" when the current window falls inside the typical range', () => {
    const within: CalendarResponse = {
      ...data,
      recent: { ...data.recent, last_7_days: { ...data.recent.last_7_days, detections: 40, difference_pct: 0.01 } },
    };
    const recent = buildExampleStory(within).find((s) => s.id === 'recent')!;
    expect(recent.answer).toMatch(/within the typical range/i);
  });

  it('shows the uncertainty range when the top year is estimated from MODIS', () => {
    const estimatedTop: CalendarResponse = {
      ...data,
      years: [{ year: 2010, detections: 11831.6, band_low: 11104.8, band_high: 12252.7, source: 'estimated_modis', complete: true, rank: 1 }],
    };
    const ranked = buildExampleStory(estimatedTop).find((s) => s.id === 'ranking')!;
    expect(ranked.answer).toContain('11,105–12,253');
    expect(ranked.answer).toMatch(/estimated from MODIS/);
  });
});
