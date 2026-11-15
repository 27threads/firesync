import { fireEvent, render, screen, within } from '@testing-library/react';
import type { PriorityCell, RecentAlerts } from '../api/types';
import { EarlyWarning } from './EarlyWarning';

function cell(i: number, overrides: Partial<PriorityCell> = {}): PriorityCell {
  return {
    h3: `84a81${i}fffffff`,
    alert_level: 'critical',
    detections_7d: 40 + i,
    typical_median: 7,
    share_followed_by_high: 0.266,
    center: [-60 - i, -3 - i],
    ...overrides,
  };
}

const risk = {
  scored_at: '2026-11-14T06:12:00Z',
  data_ref: '2026-11-13',
  model_version: 'gbm-1',
  horizon_days: 14,
  rules_version: '1.0',
  tiers: [
    { tier: 'very_high' as const, min_prob: 0.6, historical_share: 0.82 },
    { tier: 'lower' as const, min_prob: 0, historical_share: 0.03 },
  ],
};

describe('EarlyWarning', () => {
  it('renders nothing without the alerts block: the map stays as before', () => {
    const { container } = render(<EarlyWarning alerts={undefined} onFocusCell={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('lists where to look first, ten at a time, and takes the map to the cell in [lat, lon]', () => {
    const onFocusCell = vi.fn();
    const alerts: RecentAlerts = {
      data_through: '2026-11-14',
      alert_rules_version: '1.1',
      priority: Array.from({ length: 12 }, (_, i) => cell(i)),
    };
    render(<EarlyWarning alerts={alerts} onFocusCell={onFocusCell} />);

    const list = screen.getByRole('list', { name: /where to look first/i });
    expect(within(list).getAllByRole('button')).toHaveLength(10);
    fireEvent.click(within(list).getAllByRole('button')[1]);
    expect(onFocusCell).toHaveBeenCalledWith([-4, -61]);

    const showAll = screen.getByRole('button', { name: /show all/i });
    expect(showAll).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(showAll);
    expect(within(list).getAllByRole('button')).toHaveLength(12);
    expect(screen.getByRole('button', { name: /show fewer/i })).toHaveAttribute('aria-expanded', 'true');

    expect(screen.getAllByText('Unusual for the season')).toHaveLength(12);
    expect(screen.queryByText(/fire risk/i)).toBeNull(); // sem alerts.risk, nada de risco
  });

  it('shows the risk legend and an early-warning cell with no fire now', () => {
    const alerts: RecentAlerts = {
      data_through: '2026-11-14',
      alert_rules_version: '1.1',
      priority: [cell(0, { alert_level: null, detections_7d: null, typical_median: null, risk_tier: 'very_high', risk_prob: 0.7 })],
      risk,
    };
    render(<EarlyWarning alerts={alerts} onFocusCell={vi.fn()} />);

    const item = screen.getByRole('button', { name: /very high/i });
    expect(item).toHaveTextContent('No fire now');
    expect(item).not.toHaveTextContent('Unusual');

    const legend = screen.getByRole('group', { name: /fire risk, next 14 days/i });
    expect(legend).toHaveTextContent('Scored on 14 Nov 2026, 06:12 UTC');
    expect(legend).toHaveTextContent('Very high: relevant fire (10+ detections) followed in 82% of past cases');
    expect(legend).toHaveTextContent('A frequency from the past, not a forecast.');
    expect(legend).toHaveTextContent(/not burned area/);
  });

  it('says so when the API flags no cell in view', () => {
    render(<EarlyWarning alerts={{ data_through: '2026-11-14', alert_rules_version: '1.1', priority: [] }} onFocusCell={vi.fn()} />);
    expect(screen.getByText(/no cell to look at first in view/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /show all/i })).toBeNull();
  });
});
