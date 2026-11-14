import { describe, expect, it } from 'vitest';
import example from '../../../docs/api-exemplo.json';
import type { CalendarResponse } from '../api/types';
import {
  buildMonthsCsv,
  buildSeasonalityCsv,
  buildYearsCsv,
  defaultAuditFilenameUtc,
  parseContentDispositionFilename,
} from './exportModel';

const sample = example as unknown as CalendarResponse;

describe('exportModel (pure CSV builders & filename helpers)', () => {
  describe('parseContentDispositionFilename', () => {
    it('extracts quoted filename from Content-Disposition header', () => {
      expect(parseContentDispositionFilename('attachment; filename="firesync-2026-11-14.zip"')).toBe(
        'firesync-2026-11-14.zip',
      );
    });

    it('extracts unquoted filename from Content-Disposition header', () => {
      expect(parseContentDispositionFilename('attachment; filename=firesync-2026-11-14.zip')).toBe(
        'firesync-2026-11-14.zip',
      );
    });

    it('extracts RFC 5987 filename* when present', () => {
      expect(parseContentDispositionFilename("attachment; filename*=UTF-8''firesync-2026-11-14.zip")).toBe(
        'firesync-2026-11-14.zip',
      );
    });

    it('returns null when header is missing or has no filename', () => {
      expect(parseContentDispositionFilename(null)).toBeNull();
      expect(parseContentDispositionFilename('')).toBeNull();
      expect(parseContentDispositionFilename('attachment')).toBeNull();
      expect(parseContentDispositionFilename('attachment; filename="../evil.zip"')).toBeNull();
    });
  });

  describe('defaultAuditFilenameUtc', () => {
    it('formats firesync-YYYY-MM-DD.zip in UTC even near day boundary', () => {
      const d = new Date('2026-11-14T23:55:00-03:00'); // 2026-11-15T02:55:00Z
      expect(defaultAuditFilenameUtc(d)).toBe('firesync-2026-11-15.zip');
    });
  });

  describe('buildMonthsCsv (result.csv)', () => {
    it('exports header and rows matching months[] fields from docs/api.md', () => {
      const csv = buildMonthsCsv(sample.months.slice(0, 2));
      const lines = csv.trim().split('\n');
      expect(lines[0]).toBe(
        'month,detections,band_low,band_high,source,raw_count,missing_days,incomplete,provisional,anomaly,anomaly_pct',
      );
      expect(lines[1]).toBe('2003-01,89.2,84.5,96.4,estimated_modis,18,0,false,false,-47.2,-0.346');
      expect(lines[2]).toBe('2003-02,58.7,52.9,63.4,estimated_modis,13,0,false,false,-0.3,-0.005');
    });

    it('renders null band_low, band_high, anomaly and anomaly_pct as empty CSV cells', () => {
      const observedMonth = sample.months[sample.months.length - 1];
      const csv = buildMonthsCsv([observedMonth]);
      const lines = csv.trim().split('\n');
      expect(lines[1]).toBe(
        `${observedMonth.month},${observedMonth.detections},,,${observedMonth.source},${observedMonth.raw_count},${observedMonth.missing_days},${observedMonth.incomplete},${observedMonth.provisional},,`,
      );
    });
  });

  describe('buildYearsCsv', () => {
    it('exports ranked years with band_low/band_high and null fields as empty cells', () => {
      const csv = buildYearsCsv(sample.years.slice(0, 2));
      const lines = csv.trim().split('\n');
      expect(lines[0]).toBe('year,detections,band_low,band_high,source,complete,rank');
      const first = sample.years[0];
      expect(lines[1]).toBe(
        `${first.year},${first.detections},${first.band_low ?? ''},${first.band_high ?? ''},${first.source},${first.complete},${first.rank ?? ''}`,
      );
    });
  });

  describe('buildSeasonalityCsv', () => {
    it('exports 12 months of seasonality with UTC month names in English', () => {
      const csv = buildSeasonalityCsv(sample.seasonality);
      const lines = csv.trim().split('\n');
      expect(lines).toHaveLength(13);
      expect(lines[0]).toBe('month_of_year,month_name,median,mean,min,max,n_years');
      expect(lines[1]).toMatch(/^1,Jan,/);
      expect(lines[12]).toMatch(/^12,Dec,/);
    });
  });
});
