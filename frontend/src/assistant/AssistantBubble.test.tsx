import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AssistantBubble, SUGGESTED_QUESTIONS, describeSource } from './AssistantBubble';

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

const SOURCE = { endpoint: 'POST /api/v1/calendar', region: 'Pantanal', start: '2020-01', end: '2020-12', data_version: '2026-11-14T19:48:30Z' };
const ACTION = { type: 'show_calendar', area: { type: 'region', region_id: 6 }, start: '2020-01', end: '2020-12' };

afterEach(() => vi.unstubAllGlobals());

test('a suggested question sends plain text and the action applies the calendar', async () => {
  const fetchMock = vi.fn(async () =>
    json({ answer: 'September 2020 was the worst month.', actions: [ACTION], notes: [], sources: [SOURCE], verified: true }),
  );
  vi.stubGlobal('fetch', fetchMock);
  const onShowCalendar = vi.fn();
  render(<AssistantBubble onShowCalendar={onShowCalendar} />);

  fireEvent.click(screen.getByRole('button', { name: 'Ask about fire data' }));
  fireEvent.click(screen.getByRole('button', { name: SUGGESTED_QUESTIONS[0] }));

  expect(await screen.findByText('September 2020 was the worst month.')).toBeInTheDocument();
  const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toMatch(/\/api\/v1\/ask$/);
  expect(JSON.parse(String(init.body))).toEqual({ messages: [{ role: 'user', content: SUGGESTED_QUESTIONS[0] }] });

  expect(screen.getByRole('list', { name: 'Sources' })).toHaveTextContent(
    'NASA FIRMS via firesync calendar · Pantanal · 2020-01 to 2020-12 · data version 2026-11-14T19:48:30Z',
  );
  fireEvent.click(screen.getByRole('button', { name: 'Show on calendar' }));
  expect(onShowCalendar).toHaveBeenCalledWith(ACTION);
});

test('a long earlier answer goes back as history cut to the API limit', async () => {
  const fetchMock = vi.fn(async () => json({ answer: 'x'.repeat(5000), actions: [], notes: [], sources: [], verified: true }));
  vi.stubGlobal('fetch', fetchMock);
  render(<AssistantBubble onShowCalendar={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Ask about fire data' }));
  fireEvent.click(screen.getByRole('button', { name: SUGGESTED_QUESTIONS[4] }));
  await screen.findByText('x'.repeat(5000));
  fireEvent.change(screen.getByLabelText('Your question'), { target: { value: 'And 2023?' } });
  fireEvent.click(screen.getByRole('button', { name: 'Send' }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  const body = JSON.parse(String((fetchMock.mock.calls[1] as unknown as [string, RequestInit])[1].body));
  expect(body.messages.map((m: { content: string }) => m.content.length)).toEqual([SUGGESTED_QUESTIONS[4].length, 4000, 9]);
});

test('fire map sources name the time window', () => {
  expect(describeSource({ endpoint: 'GET /api/v1/detections/recent', hours: 72, data_version: 'v1' })).toBe(
    'NASA FIRMS via firesync fire map, last 72 h · data version v1',
  );
});

test('unavailable assistant tells the user to use the map', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => json({ error: { code: 'assistant_unavailable', message: 'Daily limit reached, use the map.' } }, 503)));
  render(<AssistantBubble onShowCalendar={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Ask about fire data' }));
  fireEvent.click(screen.getByRole('button', { name: SUGGESTED_QUESTIONS[3] }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Daily limit reached, use the map.');
});

test('escape closes the panel and focus returns to the bubble', () => {
  render(<AssistantBubble onShowCalendar={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Ask about fire data' }));
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Ask about fire data' })).toHaveFocus();
});

test('tab stays inside the open panel', () => {
  render(<AssistantBubble onShowCalendar={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Ask about fire data' }));
  const close = screen.getByRole('button', { name: 'Close assistant' });
  const input = screen.getByLabelText('Your question');
  fireEvent.change(input, { target: { value: 'hi' } });
  const send = screen.getByRole('button', { name: 'Send' });
  send.focus();
  fireEvent.keyDown(send, { key: 'Tab' });
  expect(close).toHaveFocus();
  fireEvent.keyDown(close, { key: 'Tab', shiftKey: true });
  expect(send).toHaveFocus();
});
