import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import example from '../../docs/api-exemplo.json';
import { App } from './App';

type Handler = (url: string, init?: RequestInit) => Response | Promise<Response>;

const REGIONS = [{ region_id: 1, name: 'Amazônia', source: 'IBGE', bbox: [-74, -16.3, -43.9, 5.3] }];
const HEALTH = { status: 'ok', data_version: '2026-11-14T19:48:30Z', last_month: '2026-11', updated_at: example.meta.updated_at, h3_resolution: 6 };

function json(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

function mockApi(calendar: Handler) {
  const calls: { url: string; body: unknown }[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url, body: init?.body ? JSON.parse(String(init.body)) : null });
      if (url.endsWith('/api/v1/health')) return json(HEALTH);
      if (url.endsWith('/api/v1/regions')) return json(REGIONS);
      if (url.includes('/api/v1/detections/recent')) return json({ type: 'FeatureCollection', mode: 'points', hours: 24, updated_at: HEALTH.updated_at, total_detections: 0, features: [] });
      if (url.endsWith('/api/v1/calendar')) return calendar(url, init);
      return new Response('not found', { status: 404 });
    }),
  );
  return calls;
}

function offline() {
  vi.stubGlobal('fetch', vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))));
}

beforeEach(() => {
  // Como o Playwright, o teste não deixa a primeira região carregar sozinha.
  Object.defineProperty(navigator, 'webdriver', { value: true, configurable: true });
  document.body.innerHTML = '';
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('App', () => {
  it('opens on clearly labelled demo data when the API is offline, with the full calendar', async () => {
    offline();
    render(<App />);
    const grid = await screen.findByRole('grid', { name: /fire calendar/i });
    expect(within(grid).getAllByRole('row')).toHaveLength(1 + 24);
    expect(screen.getAllByText('Demo data').length).toBeGreaterThan(0);
    expect(screen.getByRole('region', { name: /last 7 days/i })).toHaveTextContent('+54%');
    expect(screen.getByRole('button', { name: /audit package/i })).toBeDisabled();
  });

  it('answers in plain words first: more, about the same or less fire than usual', async () => {
    offline();
    render(<App />);
    // Exemplo do contrato: 61 detecções contra a faixa típica de 35,2 a 45,5.
    const verdict = await screen.findByRole('region', { name: /fire right now/i });
    expect(within(verdict).getByRole('heading', { name: 'More fire than usual' })).toBeInTheDocument();
    expect(verdict).toHaveTextContent('satellites spotted 61 hot spots');
  });

  it('keeps coordinates and period under More options, closed at first, and the region choice in sight', async () => {
    offline();
    render(<App />);
    const more = (await screen.findByLabelText(/latitude/i)).closest('details');
    expect(more).not.toBeNull();
    expect(more).not.toHaveAttribute('open');
    expect(within(more!).getByText(/more options/i)).toBeInTheDocument();
    expect(within(more!).getByLabelText(/^from$/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /region/i }).closest('details')).toBeNull();
  });

  it('includes the MODIS-to-VIIRS strip overlay inside the main calendar without duplicating the calendar grid', async () => {
    offline();
    render(<App />);
    const grids = await screen.findAllByRole('grid', { name: /fire calendar/i });
    expect(grids).toHaveLength(1);
    const history = document.getElementById('history')!;
    expect(history).toHaveTextContent('MODIS Aqua');
    expect(history).toHaveTextContent('287 months in one record');
  });

  it('shows the API message and no calendar when the area is outside coverage', async () => {
    const none = {
      meta: example.meta,
      area: example.area,
      coverage: { status: 'none', covered_fraction: 0, message: 'No data for this area yet. Current coverage: Brazil.' },
    };
    mockApi(() => json(none));
    render(<App />);
    fireEvent.change(screen.getByLabelText(/latitude/i), { target: { value: '48.8' } });
    fireEvent.change(screen.getByLabelText(/longitude/i), { target: { value: '2.3' } });
    fireEvent.click(screen.getByRole('button', { name: /show this area/i }));
    expect(await screen.findByText(/no record for this area/i)).toBeInTheDocument();
    expect(screen.queryByRole('grid', { name: /fire calendar/i })).toBeNull();
    expect(screen.getAllByText(/current coverage: brazil/i).length).toBeGreaterThan(0);
  });

  it('sends the point request from the contract and shows the returned calendar', async () => {
    const calls = mockApi(() => json(example));
    render(<App />);
    fireEvent.change(screen.getByLabelText(/latitude/i), { target: { value: '-3.1' } });
    fireEvent.change(screen.getByLabelText(/longitude/i), { target: { value: '-60.0' } });
    fireEvent.change(screen.getByLabelText(/radius/i), { target: { value: '25' } });
    fireEvent.click(screen.getByRole('button', { name: /show this area/i }));
    await waitFor(() => expect(calls.some((c) => c.url.endsWith('/api/v1/calendar'))).toBe(true));
    const body = calls.find((c) => c.url.endsWith('/api/v1/calendar'))!.body as { area: unknown; start: string; end: string };
    expect(body.area).toEqual({ type: 'point', lat: -3.1, lon: -60, radius_km: 25 });
    expect(body.start).toBe('2003-01');
    expect(await screen.findByRole('button', { name: /audit package/i })).toBeEnabled();
  });

  it('never aborts a recent-detections request, not even when the map unmounts (StrictMode remounts in dev)', async () => {
    const signals: (AbortSignal | null | undefined)[] = [];
    mockApi(() => json(example));
    const base = globalThis.fetch as unknown as (url: string, init?: RequestInit) => Promise<Response>;
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string, init?: RequestInit) => {
        if (url.includes('/detections/recent')) signals.push(init?.signal);
        return base(url, init);
      }),
    );
    const { unmount } = render(<App />);
    const select = await screen.findByRole('combobox', { name: /region/i });
    await waitFor(() => expect(select).toBeEnabled());
    fireEvent.change(select, { target: { value: '1' } });
    unmount();
    expect(signals.some((s) => s?.aborted)).toBe(false);
  });

  it('keeps the region selector available after a choice, so the area can be changed again', async () => {
    mockApi(() => json(example));
    render(<App />);
    const select = await screen.findByRole('combobox', { name: /region/i });
    await waitFor(() => expect(select).toBeEnabled());
    fireEvent.change(select, { target: { value: '1' } });
    await screen.findByRole('grid', { name: /fire calendar/i });
    expect(screen.getByRole('combobox', { name: /region/i })).toHaveTextContent('Amazônia');
    expect(screen.getByRole('button', { name: /download audit package/i })).toBeEnabled();
  });

  it('turns a 429 into a friendly alert with the wait time', async () => {
    mockApi(() => json({ error: { code: 'rate_limited', message: 'Too many requests. Try again in 30 seconds.' } }, 429, { 'Retry-After': '30' }));
    render(<App />);
    const select = await screen.findByRole('combobox', { name: /region/i });
    await waitFor(() => expect(select).toBeEnabled());
    fireEvent.change(select, { target: { value: '1' } });
    expect(await screen.findByRole('alert')).toHaveTextContent(/try again in 30 seconds/i);
  });

  it('keeps a drawn selection but says the figures are demo data when the API goes down', async () => {
    mockApi(() => new Response('<html>Bad gateway</html>', { status: 502 }));
    render(<App />);
    fireEvent.change(screen.getByLabelText(/latitude/i), { target: { value: '-10' } });
    fireEvent.change(screen.getByLabelText(/longitude/i), { target: { value: '-55' } });
    fireEvent.click(screen.getByRole('button', { name: /show this area/i }));
    expect(await screen.findByText(/figures below belong to the demo example/i)).toBeInTheDocument();
    expect(screen.getByText('Demo data, not this area')).toBeInTheDocument();
  });

  it('shows the month detail with its uncertainty range when a calendar cell is selected', async () => {
    offline();
    render(<App />);
    const cell = await screen.findByRole('gridcell', { name: /^Sep 2010/ });
    fireEvent.click(cell);
    const detail = screen.getByRole('complementary', { name: /month detail/i });
    expect(detail).toHaveTextContent('Sep 2010');
    expect(detail).toHaveTextContent(/P5–P95/);
    expect(detail).toHaveTextContent(/Estimated from MODIS Aqua/);
  });
});
