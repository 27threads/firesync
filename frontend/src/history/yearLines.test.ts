import type { CalendarMonth } from '../api/types';
import { linesMax, yearLine, yearsOf } from './yearLines';

const month = (key: string, detections: number, missing_days = 0): CalendarMonth => ({
  month: key,
  detections,
  band_low: null,
  band_high: null,
  source: 'observed_viirs',
  raw_count: detections,
  missing_days,
  incomplete: false,
  provisional: false,
  anomaly: null,
  anomaly_pct: null,
});

test('one value per calendar month of the chosen year, January to December', () => {
  const months = [month('2024-12', 9), month('2025-01', 10), month('2025-03', 30), month('2026-01', 99)];
  expect(yearLine(months, 2025)).toEqual([10, null, 30, null, null, null, null, null, null, null, null, null]);
});

test('a year not in the record gives an empty line', () => {
  expect(yearLine([month('2025-01', 10)], 2003).every((v) => v === null)).toBe(true);
});

test('a month without satellite data is a gap in the line, never a zero', () => {
  expect(yearLine([month('2026-05', 0, 31), month('2026-06', 0, 3)], 2026).slice(4, 6)).toEqual([null, 0]);
});

test('the years of the record, oldest first, for the From and To lists', () => {
  expect(yearsOf([month('2003-01', 1), month('2003-02', 1), month('2026-11', 1)])).toEqual([2003, 2026]);
});

test('the scale fits the chosen years and the typical month, not the record-breaking ones', () => {
  expect(linesMax([[10, null, 30], [5, 80, null]], [50, 60, 70])).toBe(80);
  expect(linesMax([[null, null]], [])).toBe(0);
});
