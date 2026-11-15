import { formatCount, formatDayRange, formatShare, formatSignedPct, formatUpdatedAt, formatWindowValue } from './format';

describe('formatCount', () => {
  it('rounds to whole detections with thousands separators', () => {
    expect(formatCount(173392.9)).toBe('173,393');
    expect(formatCount(61)).toBe('61');
  });
});

describe('formatWindowValue', () => {
  it('keeps one decimal for medians and quartiles of short windows', () => {
    expect(formatWindowValue(39.5)).toBe('39.5');
    expect(formatWindowValue(61)).toBe('61');
    expect(formatWindowValue(1234.56)).toBe('1,234.6');
  });
});

describe('formatSignedPct', () => {
  it('always shows the sign, with a true minus for negatives', () => {
    expect(formatSignedPct(0.544)).toBe('+54%');
    expect(formatSignedPct(-0.409)).toBe('−41%');
    expect(formatSignedPct(0)).toBe('0%');
  });

  it('says "n/a" when there is no percentage (typical median of zero)', () => {
    expect(formatSignedPct(null)).toBe('n/a');
  });
});

describe('formatShare', () => {
  it('shows a share as a rounded percentage', () => {
    expect(formatShare(0.082)).toBe('8%');
  });
});

describe('formatUpdatedAt', () => {
  it('shows the UTC date and time, never the local time', () => {
    expect(formatUpdatedAt('2026-11-14T15:00:00Z')).toBe('14 Nov 2026, 15:00 UTC');
    expect(formatUpdatedAt('2026-01-03T04:05:00Z')).toBe('3 Jan 2026, 04:05 UTC');
  });
});

describe('formatDayRange', () => {
  it('joins days of the same month', () => {
    expect(formatDayRange('2026-11-08', '2026-11-14')).toBe('8–14 Nov 2026');
  });

  it('names both months when the window crosses a month', () => {
    expect(formatDayRange('2026-10-29', '2026-11-04')).toBe('29 Oct – 4 Nov 2026');
  });

  it('names both years when the window crosses a year', () => {
    expect(formatDayRange('2025-12-29', '2026-01-04')).toBe('29 Dec 2025 – 4 Jan 2026');
  });
});
