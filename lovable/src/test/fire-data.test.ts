import { describe, expect, it } from 'vitest';
import { conversionBand, csv, demoData, number, percent, rankedYears } from '@/lib/fire-data';

describe('scientific data rules', () => {
  it('shows fractional percentages as percentages', () => { expect(percent(0.54)).toBe('+54%'); });
  it('does not treat absent detections as zero', () => { expect(number(null)).toBe('Not available'); expect(number(0)).toBe('0'); });
  it('preserves the February 2012 sensor transition', () => { expect(demoData.months.find(m => m.month === '2012-01')?.source).toBe('estimated_modis'); expect(demoData.months.find(m => m.month === '2012-02')?.source).toBe('observed_viirs'); });
  it('does not attach conversion uncertainty to observed VIIRS', () => { const m = demoData.months.find(m => m.month === '2012-02'); if (!m) throw new Error('Missing fixture'); expect(conversionBand({ ...m, band_low: 1, band_high: 2 })).toBeNull(); });
  it('uses supplied annual uncertainty rather than summing monthly bands', () => { const year = demoData.years.find(y => y.year === 2010); expect(year?.band_low).toBe(11104.8); expect(year?.band_high).toBe(12252.7); });
  it('keeps incomplete 2026 out of the ranking', () => { expect(rankedYears(demoData).some(y => y.year === 2026)).toBe(false); expect(demoData.years.find(y => y.year === 2026)?.rank).toBeNull(); });
  it('keeps the supplied recent detections and typical range distinct', () => { expect(demoData.recent.last_7_days.detections).toBe(61); expect(demoData.recent.last_7_days.typical_p25).toBe(35.2); expect(demoData.recent.last_7_days.typical_p75).toBe(45.5); });
  it('exports missing numeric values without silently converting them to zero', () => { expect(csv([{ detections: null }, { detections: 0 }])).toBe('"detections"\r\n""\r\n"0"'); });
});