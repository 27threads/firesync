import { render, screen } from '@testing-library/react';
import type { CalendarMonth, SeasonalityMonth } from '../api/types';
import { SeasonalChart } from './SeasonalChart';
import { YearLinesChart } from './yearLines';

// What the API sends for a period without a complete year (checked on 15/11 with Pantanal, 2026-01 to 2026-11).
const noCompleteYear: SeasonalityMonth[] = Array.from({ length: 12 }, (_, i) => ({
  month_of_year: i + 1,
  median: null,
  mean: null,
  min: null,
  max: null,
  n_years: 0,
}));

const months: CalendarMonth[] = [
  {
    month: '2026-01',
    detections: 1108,
    band_low: null,
    band_high: null,
    source: 'observed_viirs',
    raw_count: 1108,
    missing_days: 0,
    incomplete: false,
    provisional: false,
    anomaly: null,
    anomaly_pct: null,
  },
];

test('the seasonal pattern says there is no complete year instead of drawing zeros', () => {
  const { container } = render(<SeasonalChart seasonality={noCompleteYear} includesEstimatedYears={false} highlightMonthIndex={null} />);
  expect(screen.getByText(/no complete year in this period/i)).toBeInTheDocument();
  expect(container.querySelector('svg.chart')).toBeNull();
});

test('the year lines say there is no complete year instead of a band at zero', () => {
  const { container } = render(<YearLinesChart months={months} seasonality={noCompleteYear} highlightYear={null} />);
  expect(screen.getByText(/no complete year in this period/i)).toBeInTheDocument();
  expect(container.querySelector('svg.chart')).toBeNull();
});
