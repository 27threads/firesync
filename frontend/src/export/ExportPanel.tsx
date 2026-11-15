import { useState } from 'react';
import { ApiClientError, fetchAuditPackage } from '../api/client';
import type { CalendarRequest, CalendarResponse } from '../api/types';
import { renderCalendarSvgToPngBlob } from './calendarPng';
import { buildMonthsCsv, buildSeasonalityCsv, buildYearsCsv } from './exportModel';

const CONTRACT_ERROR_CODES = new Set([
  'invalid_geometry',
  'area_too_large',
  'invalid_period',
  'region_not_found',
  'rate_limited',
  'internal_error',
]);

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function formatAreaSummary(data: CalendarResponse, request: CalendarRequest): string {
  const biomeNames = data.area?.biomes?.map((b) => b.name).join(', ');
  if (biomeNames) {
    const km2 = data.area?.area_km2 ? ` (${Math.round(data.area.area_km2).toLocaleString('en-US')} km²)` : '';
    return `Area: ${biomeNames}${km2}`;
  }
  if (request.area.type === 'point') {
    return `Area: ${request.area.lat.toFixed(2)}, ${request.area.lon.toFixed(2)} (${request.area.radius_km} km radius)`;
  }
  if (request.area.type === 'region') {
    return `Area: Region #${request.area.region_id}`;
  }
  return 'Area: Selected polygon';
}

export interface ExportPanelProps {
  data: CalendarResponse;
  request: CalendarRequest;
  isDemo: boolean;
  disabled?: boolean;
  onTriggerDownload?: (blob: Blob, filename: string) => void;
}

export function ExportPanel({
  data,
  request,
  isDemo,
  disabled = false,
  onTriggerDownload = triggerBrowserDownload,
}: ExportPanelProps) {
  const [exportingAudit, setExportingAudit] = useState(false);
  const [exportingPng, setExportingPng] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [exportDemoFallbackNote, setExportDemoFallbackNote] = useState<string | null>(null);

  const periodStart = request.start ?? data.months[0]?.month ?? '2003-01';
  const periodEnd = request.end ?? data.months[data.months.length - 1]?.month ?? data.meta.last_month;
  const highDetectionCount = data.indicators.total_detections > 500_000;

  const handleAuditDownload = async () => {
    if (disabled || exportingAudit) return;
    setExportingAudit(true);
    setExportError(null);
    setExportDemoFallbackNote(null);

    try {
      const { blob, filename } = await fetchAuditPackage(request);
      onTriggerDownload(blob, filename);
    } catch (err) {
      if (err instanceof ApiClientError && (err.status === 429 || CONTRACT_ERROR_CODES.has(err.code))) {
        setExportError(err.message);
      } else {
        // Fallback in demo/offline mode: download local result.csv so the user still gets the visible series.
        const csvContent = buildMonthsCsv(data.months);
        const csvBlob = new Blob([csvContent], { type: 'text/csv;charset=utf-8' });
        onTriggerDownload(csvBlob, 'result.csv');
        setExportDemoFallbackNote(
          'API export endpoint unavailable in demo mode — downloaded local monthly series (result.csv).',
        );
      }
    } finally {
      setExportingAudit(false);
    }
  };

  const handleDownloadMonthsCsv = () => {
    if (disabled) return;
    const csv = buildMonthsCsv(data.months);
    onTriggerDownload(new Blob([csv], { type: 'text/csv;charset=utf-8' }), 'result.csv');
  };

  const handleDownloadYearsCsv = () => {
    if (disabled) return;
    const csv = buildYearsCsv(data.years);
    onTriggerDownload(new Blob([csv], { type: 'text/csv;charset=utf-8' }), 'years.csv');
  };

  const handleDownloadSeasonalityCsv = () => {
    if (disabled) return;
    const csv = buildSeasonalityCsv(data.seasonality);
    onTriggerDownload(new Blob([csv], { type: 'text/csv;charset=utf-8' }), 'seasonality.csv');
  };

  const handleDownloadCalendarPng = async () => {
    if (disabled || exportingPng) return;
    const svg = document.querySelector<SVGSVGElement>('.fire-calendar svg');
    if (!svg) return;
    setExportingPng(true);
    try {
      const pngBlob = await renderCalendarSvgToPngBlob(svg, {
        areaLabel: formatAreaSummary(data, request),
        periodLabel: `${periodStart} to ${periodEnd}`,
      });
      onTriggerDownload(pngBlob, `firesync-calendar-${periodStart}-${periodEnd}.png`);
    } finally {
      setExportingPng(false);
    }
  };

  return (
    <section className="summary-block export-panel" aria-labelledby="export-panel-title">
      <h3 id="export-panel-title">Export &amp; audit package</h3>
      <p>
        Take the calendar and underlying tables outside the app to attach to reports or independently recompute every
        number from <code>counts.csv × factors.csv</code>.
      </p>

      <div className="export-panel__actions">
        <button
          type="button"
          className="map-btn map-btn--primary"
          disabled={disabled || exportingAudit}
          onClick={() => void handleAuditDownload()}
        >
          {exportingAudit ? 'Exporting…' : 'Download audit package (ZIP)'}
        </button>

        <button
          type="button"
          className="map-btn"
          disabled={disabled}
          onClick={handleDownloadMonthsCsv}
        >
          Monthly series CSV (result.csv)
        </button>

        <button
          type="button"
          className="map-btn"
          disabled={disabled}
          onClick={handleDownloadYearsCsv}
        >
          Annual ranking CSV (years.csv)
        </button>

        <button
          type="button"
          className="map-btn"
          disabled={disabled}
          onClick={handleDownloadSeasonalityCsv}
        >
          Seasonality CSV (seasonality.csv)
        </button>

        <button
          type="button"
          className="map-btn"
          disabled={disabled || exportingPng}
          onClick={() => void handleDownloadCalendarPng()}
        >
          {exportingPng ? 'Exporting…' : 'Calendar image (PNG)'}
        </button>
      </div>

      {exportError && (
        <p className="tool-alert" role="alert">
          {exportError}
        </p>
      )}

      {exportDemoFallbackNote && (
        <p className="example-notice" role="status">
          {exportDemoFallbackNote}
        </p>
      )}

      <div className="export-panel__details">
        <p className="stat-note">
          <strong>Full API audit package (<code>firesync-YYYY-MM-DD.zip</code>):</strong> includes{' '}
          <code>result.csv</code> (harmonized monthly series), <code>counts.csv</code> (raw detections and FRP sum by
          biome, month, satellite, and day/night), <code>factors.csv</code> (Aqua to S-NPP calibration factors across
          all calibration years), <code>metadata.json</code> (query parameters, formula, P5–P95 linear interpolation,
          filters, and NASA FIRMS sources), and <code>detections.csv</code> (individual hot spots in UTC).
          {isDemo && ' In demo mode without a live API, use the CSV buttons above to export the visible series locally.'}
        </p>
        <p className="stat-note">
          {highDetectionCount ? (
            <strong>
              Notice: this selection exceeds 500,000 fire detections. In the ZIP audit package,{' '}
              <code>detections.csv</code> is omitted and <code>metadata.json</code> sets{' '}
              <code>&quot;detections_omitted&quot;: true</code>. Select a smaller area or shorter period to download
              individual detections.
            </strong>
          ) : (
            <>
              Individual hot spots in <code>detections.csv</code> are included up to <strong>500,000</strong> detections.
              If an area and period exceed 500,000 detections, <code>detections.csv</code> is omitted from the ZIP and{' '}
              <code>metadata.json</code> records the total count — choose a smaller area or shorter period if you need
              the raw point list.
            </>
          )}
        </p>
      </div>
    </section>
  );
}
