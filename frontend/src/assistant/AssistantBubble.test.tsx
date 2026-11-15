import { fireEvent, render, screen } from '@testing-library/react';
import { AssistantBubble, SUGGESTED_QUESTIONS } from './AssistantBubble';

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

const ACTION = { type: 'show_calendar', area: { type: 'region', region_id: 6 }, start: '2020-01', end: '2020-12' };

afterEach(() => vi.unstubAllGlobals());

test('a suggested question sends plain text and the action applies the calendar', async () => {
  const fetchMock = vi.fn(async () => json({ answer: 'September 2020 was the worst month.', actions: [ACTION], notes: [] }));
  vi.stubGlobal('fetch', fetchMock);
  const onShowCalendar = vi.fn();
  render(<AssistantBubble onShowCalendar={onShowCalendar} />);

  fireEvent.click(screen.getByRole('button', { name: 'Ask about fire data' }));
  fireEvent.click(screen.getByRole('button', { name: SUGGESTED_QUESTIONS[0] }));

  expect(await screen.findByText('September 2020 was the worst month.')).toBeInTheDocument();
  const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toMatch(/\/api\/v1\/ask$/);
  expect(JSON.parse(String(init.body))).toEqual({ messages: [{ role: 'user', content: SUGGESTED_QUESTIONS[0] }] });

  fireEvent.click(screen.getByRole('button', { name: 'Show on calendar' }));
  expect(onShowCalendar).toHaveBeenCalledWith(ACTION);
});

test('unavailable assistant tells the user to use the map', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => json({ error: { code: 'assistant_unavailable', message: 'Daily limit reached, use the map.' } }, 503)));
  render(<AssistantBubble onShowCalendar={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Ask about fire data' }));
  fireEvent.click(screen.getByRole('button', { name: SUGGESTED_QUESTIONS[3] }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Daily limit reached, use the map.');
});

test('escape closes the panel', () => {
  render(<AssistantBubble onShowCalendar={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: 'Ask about fire data' }));
  fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});
