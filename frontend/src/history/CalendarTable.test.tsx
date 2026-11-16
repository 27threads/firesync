import { fireEvent, render, screen } from '@testing-library/react';
import type { CalendarMonth, CalendarResponse } from '../api/types';
import { CalendarTable } from './HistoryPanel';

const month = (key: string, detections: number): CalendarMonth => ({
  month: key,
  detections,
  band_low: null,
  band_high: null,
  source: 'observed_viirs',
  raw_count: detections,
  missing_days: 0,
  incomplete: false,
  provisional: false,
  anomaly: null,
  anomaly_pct: null,
});

const data = { months: [month('2019-07', 900), month('2019-08', 12028)] } as CalendarResponse;

test('a click on a month in the table opens it in the month detail, like a click on the calendar', () => {
  const onSelect = vi.fn();
  render(<CalendarTable data={data} selectedKey={null} onSelectKey={onSelect} />);
  fireEvent.click(screen.getByRole('button', { name: 'Aug 2019' }));
  expect(onSelect).toHaveBeenCalledWith('2019-08');
});

test('the chosen month is marked in the table', () => {
  render(<CalendarTable data={data} selectedKey="2019-08" onSelectKey={() => undefined} />);
  expect(screen.getByRole('button', { name: 'Aug 2019' })).toHaveAttribute('aria-pressed', 'true');
  expect(screen.getByRole('button', { name: 'Jul 2019' })).toHaveAttribute('aria-pressed', 'false');
});
