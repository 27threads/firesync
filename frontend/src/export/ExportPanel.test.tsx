import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import example from '../../../docs/api-exemplo.json';
import { ApiClientError } from '../api/client';
import type { CalendarRequest, CalendarResponse } from '../api/types';
import { ExportPanel } from './ExportPanel';

const sampleData = example as unknown as CalendarResponse;
const sampleRequest: CalendarRequest = {
  area: { type: 'region', region_id: 1 },
  start: '2003-01',
  end: '2026-11',
};

describe('ExportPanel (Tela 5: Exportar, RF13, RD05)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders accessible buttons for audit package ZIP, CSV and PNG and lists audit package contents', () => {
    render(<ExportPanel data={sampleData} request={sampleRequest} isDemo={false} disabled={false} />);

    expect(screen.getByRole('region', { name: /export|download/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /download|export/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /monthly series csv/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /annual ranking csv/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /seasonality csv/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /calendar image \(png\)/i })).toBeInTheDocument();

    // Lists the 5 files of the audit package and the 500,000 detections note
    expect(screen.getAllByText('result.csv').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('counts.csv').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('factors.csv').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('metadata.json').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('detections.csv').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/500,000/).length).toBeGreaterThanOrEqual(1);
  });

  it('disables all export buttons when disabled is true (e.g. coverage.status === "none")', () => {
    render(<ExportPanel data={sampleData} request={sampleRequest} isDemo={false} disabled={true} />);

    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThanOrEqual(3);
    for (const button of buttons) {
      expect(button).toBeDisabled();
    }
  });

  it('triggers POST /api/v1/export, shows Exporting… while in flight, and downloads the returned ZIP', async () => {
    let resolveExport!: (res: Response) => void;
    const fetchMock = vi.fn().mockImplementation(
      () =>
        new Promise<Response>((resolve) => {
          resolveExport = resolve;
        }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const onTriggerDownload = vi.fn();
    render(
      <ExportPanel
        data={sampleData}
        request={sampleRequest}
        isDemo={false}
        disabled={false}
        onTriggerDownload={onTriggerDownload}
      />,
    );

    const auditBtn = screen.getByRole('button', { name: /download.*audit package|export.*audit package/i });
    fireEvent.click(auditBtn);

    expect(auditBtn).toBeDisabled();
    expect(auditBtn).toHaveTextContent(/exporting/i);

    resolveExport(
      new Response(new Uint8Array([0x50, 0x4b]), {
        status: 200,
        headers: {
          'Content-Type': 'application/zip',
          'Content-Disposition': 'attachment; filename="firesync-2026-11-14.zip"',
        },
      }),
    );

    await waitFor(() => {
      expect(onTriggerDownload).toHaveBeenCalledWith(expect.any(Blob), 'firesync-2026-11-14.zip');
    });
    expect(auditBtn).not.toBeDisabled();
  });

  it('shows role="alert" with Retry-After when POST /api/v1/export returns 429', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({ error: { code: 'rate_limited', message: 'Too many export requests.' } }),
          {
            status: 429,
            headers: { 'Content-Type': 'application/json', 'Retry-After': '30' },
          },
        ),
      ),
    );

    render(<ExportPanel data={sampleData} request={sampleRequest} isDemo={false} disabled={false} />);
    const auditBtn = screen.getByRole('button', { name: /download.*audit package|export.*audit package/i });
    fireEvent.click(auditBtn);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/30 seconds/i);
  });

  it('shows role="alert" when POST /api/v1/export returns a contract error', async () => {
    const errorPayload = {
      error: { code: 'area_too_large', message: 'The selected area is too large. Draw a smaller area.' },
    };
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(errorPayload), {
          status: 413,
          headers: { 'Content-Type': 'application/json' },
        }),
      ),
    );

    render(<ExportPanel data={sampleData} request={sampleRequest} isDemo={false} disabled={false} />);
    fireEvent.click(screen.getByRole('button', { name: /download.*audit package|export.*audit package/i }));

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/selected area is too large/i);
    expect(ApiClientError).toBeDefined();
  });

  it('downloads local CSV of monthly series (result.csv) when clicking the CSV button', () => {
    const onTriggerDownload = vi.fn();
    render(
      <ExportPanel
        data={sampleData}
        request={sampleRequest}
        isDemo={true}
        disabled={false}
        onTriggerDownload={onTriggerDownload}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /monthly series csv/i }));
    expect(onTriggerDownload).toHaveBeenCalledWith(expect.any(Blob), 'result.csv');
  });

  it('downloads calendar PNG from the rendered fire-calendar SVG', async () => {
    const onTriggerDownload = vi.fn();
    render(
      <div>
        <figure className="fire-calendar">
          <svg viewBox="0 0 500 550" role="grid" aria-label="Fire calendar">
            <rect x="0" y="0" width="36" height="20" className="fire-calendar__cell" />
          </svg>
        </figure>
        <ExportPanel
          data={sampleData}
          request={sampleRequest}
          isDemo={false}
          disabled={false}
          onTriggerDownload={onTriggerDownload}
        />
      </div>,
    );

    fireEvent.click(screen.getByRole('button', { name: /calendar image \(png\)/i }));
    await waitFor(() => {
      expect(onTriggerDownload).toHaveBeenCalledWith(expect.any(Blob), 'firesync-calendar-2003-01-2026-11.png');
    });
  });
});
