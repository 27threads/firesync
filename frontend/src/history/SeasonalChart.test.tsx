import { render } from '@testing-library/react';
import type { SeasonalityMonth } from '../api/types';
import { SeasonalChart } from './SeasonalChart';

function months(max: number): SeasonalityMonth[] {
  return Array.from({ length: 12 }, (_, i) => ({
    month_of_year: i + 1,
    median: max / 2,
    mean: max / 2,
    min: 0,
    max: i === 8 ? max : max / 4,
    n_years: 20,
  }));
}

// Where the plot starts: the left end of the grid lines, right after the Y axis numbers.
function plotLeft(max: number): number {
  const { container, unmount } = render(
    <SeasonalChart seasonality={months(max)} includesEstimatedYears={false} highlightMonthIndex={null} />,
  );
  const x = Number(container.querySelector('.chart__grid')!.getAttribute('x1'));
  unmount();
  return x;
}

test('the Y axis gets room for long numbers like 500,000 (they were cut on the phone)', () => {
  expect(plotLeft(520_750)).toBeGreaterThanOrEqual(52);
});

test('short Y axis numbers keep a narrow margin', () => {
  expect(plotLeft(900)).toBeLessThan(plotLeft(520_750));
});
