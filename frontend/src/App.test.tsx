import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import example from '../../docs/api-exemplo.json';
import { App } from './App';

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

function mockApi(
  options: {
    calendarStatus?: number;
    calendarBody?: unknown;
    calendarHeaders?: Record<string, string>;
  } = {},
) {
  const { calendarStatus = 200, calendarBody = example, calendarHeaders = {} } = options;
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith('/api/v1/health')) {
      return jsonResponse({
        status: 'ok',
        data_version: '2026-11-14T19:48:30Z',
        last_month: '2026-11',
        updated_at: example.meta.updated_at,
        h3_resolution: 6,
      });
    }
    if (url.endsWith('/api/v1/regions')) {
      return jsonResponse([
        { region_id: 1, name: 'Amazônia', source: 'IBGE, Biomas do Brasil 1:250.000', bbox: [-74.0, -16.3, -43.9, 5.3] },
      ]);
    }
    if (url.endsWith('/api/v1/calendar')) {
      return jsonResponse(calendarBody, calendarStatus, calendarHeaders);
    }
    throw new Error(`Unexpected URL: ${url}`);
  });
}

describe('App (interactive tool shell)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows the tool as a labelled region with its heading', async () => {
    vi.stubGlobal('fetch', mockApi());
    render(<App />);
    expect(screen.getByRole('region', { name: /explore an area/i })).toBeInTheDocument();
    await screen.findByRole('option', { name: 'Amazônia' });
  });

  it('tells the user what to do first and falls back to example data when the API fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('network down')));
    render(<App />);
    expect(screen.getByText(/choose an area/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText(/showing example data/i)).toBeInTheDocument();
    });
  });

  it('puts now before history: indicators and the last 7 days come before the calendar', async () => {
    vi.stubGlobal('fetch', mockApi());
    render(<App />);
    await screen.findByRole('option', { name: 'Amazônia' });
    const order = [
      screen.getByRole('region', { name: /key indicators/i }),
      screen.getByRole('region', { name: /last 7 days/i }),
      screen.getByRole('grid', { name: /fire calendar/i }),
      screen.getByRole('region', { name: /seasonal pattern/i }),
      screen.getByRole('region', { name: /years ranked/i }),
    ];
    for (let i = 1; i < order.length; i++) {
      expect(order[i - 1].compareDocumentPosition(order[i]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    }
  });

  it('replaces example data when the user chooses a region from GET /regions', async () => {
    const customResponse = {
      ...example,
      indicators: { ...example.indicators, total_detections: 98765 },
    };
    const fetchMock = mockApi({ calendarBody: customResponse });
    vi.stubGlobal('fetch', fetchMock);

    render(<App />);
    const select = await screen.findByRole('combobox', { name: /region/i });
    await screen.findByRole('option', { name: 'Amazônia' });

    fireEvent.change(select, { target: { value: '1' } });

    await waitFor(() => {
      expect(screen.getByText('98,765')).toBeInTheDocument();
    });
    expect(screen.queryByText(/showing example data/i)).toBeNull();
  });

  it('shows the coverage message and hides the calendar when coverage.status is "none"', async () => {
    const noCoverage = {
      meta: example.meta,
      area: { type: 'point', n_cells: 0, area_km2: 0, biomes: [] },
      coverage: { status: 'none', covered_fraction: 0, message: 'No data for this area yet. Current coverage: Brazil.' },
    };
    vi.stubGlobal('fetch', mockApi({ calendarBody: noCoverage }));

    render(<App />);
    await screen.findByRole('option', { name: 'Amazônia' });
    fireEvent.change(screen.getByLabelText(/latitude/i), { target: { value: '48.8' } });
    fireEvent.change(screen.getByLabelText(/longitude/i), { target: { value: '2.3' } });
    fireEvent.click(screen.getByRole('button', { name: /show|search/i }));

    await waitFor(() => {
      expect(screen.getByText(/Current coverage: Brazil/)).toBeInTheDocument();
    });
    expect(screen.queryByRole('grid', { name: /fire calendar/i })).toBeNull();
  });

  it('shows a rate-limit alert with Retry-After seconds on HTTP 429', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi({
        calendarStatus: 429,
        calendarHeaders: { 'Retry-After': '30' },
        calendarBody: { error: { code: 'rate_limited', message: 'Too many requests.' } },
      }),
    );

    render(<App />);
    await screen.findByRole('option', { name: 'Amazônia' });
    fireEvent.change(screen.getByRole('combobox', { name: /region/i }), { target: { value: '1' } });

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/try again in 30 seconds/i);
  });

  it('shows contract errors like area_too_large in role="alert"', async () => {
    vi.stubGlobal(
      'fetch',
      mockApi({
        calendarStatus: 413,
        calendarBody: { error: { code: 'area_too_large', message: 'The selected area is too large. Draw a smaller area.' } },
      }),
    );

    render(<App />);
    await screen.findByRole('option', { name: 'Amazônia' });
    fireEvent.change(screen.getByRole('combobox', { name: /region/i }), { target: { value: '1' } });

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/selected area is too large/i);
  });

  it('warns in role="alert" when API data updated_at is older than 6 hours', async () => {
    const staleResponse = {
      ...example,
      meta: { ...example.meta, updated_at: '2026-11-13T00:00:00Z' },
    };
    vi.spyOn(Date, 'now').mockReturnValue(Date.parse('2026-11-14T15:00:00Z'));
    vi.stubGlobal('fetch', mockApi({ calendarBody: staleResponse }));

    render(<App />);
    await screen.findByRole('option', { name: 'Amazônia' });
    fireEvent.change(screen.getByRole('combobox', { name: /region/i }), { target: { value: '1' } });

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent(/may be out of date/i);
  });
});
