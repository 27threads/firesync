import { fireEvent, render, screen, within } from '@testing-library/react';
import example from '../../../docs/api-exemplo.json';
import type { CalendarMonth } from '../api/types';
import { FireCalendar } from './FireCalendar';

const months = example.months as CalendarMonth[];

describe('FireCalendar with the API example', () => {
  it('is a grid named "Fire calendar" with a header row and one row per year (2003 to 2026)', () => {
    render(<FireCalendar months={months} />);
    const grid = screen.getByRole('grid', { name: /fire calendar/i });
    expect(within(grid).getAllByRole('row')).toHaveLength(1 + 24);
  });

  it('names every month cell with its year, month and count', () => {
    render(<FireCalendar months={months} />);
    expect(screen.getByRole('gridcell', { name: /^Sep 2010: .* detections, estimated from MODIS \(range/ })).toBeInTheDocument();
  });

  it('marks the current month as incomplete', () => {
    render(<FireCalendar months={months} />);
    expect(screen.getByRole('gridcell', { name: /^Nov 2026:/ })).toHaveAttribute('aria-label', expect.stringMatching(/incomplete/));
  });

  it('shows a tooltip with the uncertainty range when an estimated month is hovered', () => {
    render(<FireCalendar months={months} />);
    fireEvent.mouseEnter(screen.getByRole('gridcell', { name: /^Sep 2010:/ }));
    expect(screen.getByRole('tooltip')).toHaveTextContent(/range/i);
  });

  it('shows the same tooltip when a month gets keyboard focus', () => {
    render(<FireCalendar months={months} />);
    fireEvent.focus(screen.getByRole('gridcell', { name: /^Aug 2015:/ }));
    expect(screen.getByRole('tooltip')).toHaveTextContent(/Aug 2015/);
  });

  it('moves focus between months with the arrow keys', () => {
    render(<FireCalendar months={months} />);
    const sep2010 = screen.getByRole('gridcell', { name: /^Sep 2010:/ });
    sep2010.focus();
    fireEvent.keyDown(sep2010, { key: 'ArrowRight' });
    expect(document.activeElement).toBe(screen.getByRole('gridcell', { name: /^Oct 2010:/ }));
    fireEvent.keyDown(document.activeElement!, { key: 'ArrowDown' });
    expect(document.activeElement).toBe(screen.getByRole('gridcell', { name: /^Oct 2011:/ }));
  });

  it('marks the sensor switch in February 2012', () => {
    render(<FireCalendar months={months} />);
    expect(screen.getByText(/VIIRS from Feb 2012/i)).toBeInTheDocument();
  });

  it('explains every visual state in the legend, not only by color', () => {
    render(<FireCalendar months={months} />);
    const legend = screen.getByRole('list', { name: /legend/i });
    for (const state of [/zero detections/i, /no satellite data/i, /estimated from MODIS/i, /incomplete month/i]) {
      expect(within(legend).getByText(state)).toBeInTheDocument();
    }
  });
});

describe('FireCalendar with states that the example does not have', () => {
  const base: CalendarMonth = {
    month: '2020-01', detections: 0, band_low: null, band_high: null, source: 'observed_viirs', raw_count: 0,
    missing_days: 0, incomplete: false, provisional: false, anomaly: null, anomaly_pct: null,
  };

  it('draws zero and no data differently, never with the same fill', () => {
    render(<FireCalendar months={[base, { ...base, month: '2020-02', missing_days: 29 }]} />);
    const zero = screen.getByRole('gridcell', { name: /^Jan 2020: 0 detections/ });
    const noData = screen.getByRole('gridcell', { name: /^Feb 2020: no satellite data/ });
    expect(zero.getAttribute('data-state')).toBe('zero');
    expect(noData.getAttribute('data-state')).toBe('no_data');
  });
});
