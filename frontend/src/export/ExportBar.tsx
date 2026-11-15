import { useState } from 'react';
import { ApiClientError, fetchAuditPackage } from '../api/client';
import type { CalendarRequest, CalendarResponse } from '../api/types';
import { renderCalendarPng } from './calendarPng';
import { buildMonthsCsv, buildSeasonalityCsv, buildYearsCsv } from './exportModel';

interface ExportBarProps {
  data: CalendarResponse;
  isDemo: boolean;
  request: CalendarRequest | null;
  areaLabel: string;
  periodLabel: string;
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function csv(text: string): Blob {
  return new Blob([text], { type: 'text/csv;charset=utf-8' });
}

export function ExportBar({ data, isDemo, request, areaLabel, periodLabel }: ExportBarProps) {
  const [busy, setBusy] = useState<'png' | 'zip' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const prefix = isDemo ? 'firesync-demo' : 'firesync';
  const auditAvailable = !isDemo && request !== null;

  async function png() {
    setBusy('png');
    setError(null);
    try {
      const blob = await renderCalendarPng(data.months, { areaLabel, periodLabel, isDemo });
      downloadBlob(blob, `${prefix}-calendar.png`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not create the image.');
    } finally {
      setBusy(null);
    }
  }

  async function audit() {
    if (!request) return;
    setBusy('zip');
    setError(null);
    try {
      const { blob, filename } = await fetchAuditPackage(request);
      downloadBlob(blob, filename);
    } catch (e) {
      setError(
        e instanceof ApiClientError && e.code !== 'http_error'
          ? e.message
          : 'The audit package could not be downloaded because the API did not respond. Try again later.',
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="exports" aria-labelledby="exports-title">
      <div className="section-head">
        <div>
          <h3 id="exports-title">Downloads</h3>
          <p>
            Take this analysis with you. The audit package includes the raw counts and the conversion factors, so anyone can
            recompute the calendar.
          </p>
        </div>
      </div>
      <ul className="exports__list">
        <li>
          <button type="button" className="btn btn--quiet" onClick={png} disabled={busy === 'png'}>
            Calendar (PNG)
          </button>
        </li>
        <li>
          <button type="button" className="btn btn--quiet" onClick={() => downloadBlob(csv(buildMonthsCsv(data.months)), `${prefix}-monthly-series.csv`)}>
            Monthly series (CSV)
          </button>
        </li>
        <li>
          <button type="button" className="btn btn--quiet" onClick={() => downloadBlob(csv(buildYearsCsv(data.years)), `${prefix}-annual-totals.csv`)}>
            Annual totals (CSV)
          </button>
        </li>
        <li>
          <button type="button" className="btn btn--quiet" onClick={() => downloadBlob(csv(buildSeasonalityCsv(data.seasonality)), `${prefix}-seasonality.csv`)}>
            Seasonality (CSV)
          </button>
        </li>
        <li>
          <button
            type="button"
            className="btn btn--quiet"
            onClick={audit}
            disabled={!auditAvailable || busy === 'zip'}
            aria-describedby="audit-note"
          >
            {busy === 'zip' ? 'Preparing audit package…' : 'Download audit package (ZIP)'}
          </button>
        </li>
      </ul>
      <p className="exports__note" id="audit-note">
        {auditAvailable
          ? 'The audit package is built by the API from the same area and period.'
          : 'The audit package is built by the API from the selected area. It is not available for demo data.'}
        {isDemo && ' Files from the demo are named firesync-demo.'}
      </p>
      {error && (
        <p className="notice notice--alert" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
