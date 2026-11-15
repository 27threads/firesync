import { describe, expect, it } from 'vitest';
import type { PriorityCell, RecentAlerts, RiskLegend } from '../api/types';
import {
  PRIORITY_LIMIT,
  alertBadge,
  centerToLatLng,
  priorityView,
  riskLegendView,
  riskTierLabel,
} from './alertsModel';

function cell(overrides: Partial<PriorityCell> = {}): PriorityCell {
  return {
    h3: '84a8101ffffffff',
    alert_level: 'critical',
    detections_7d: 46,
    typical_median: 7,
    share_followed_by_high: 0.266,
    center: [-60.2, -3.1],
    ...overrides,
  };
}

const risk: RiskLegend = {
  scored_at: '2026-11-14T06:12:00Z',
  data_ref: '2026-11-13',
  model_version: 'gbm-1',
  horizon_days: 14,
  rules_version: '1.0',
  tiers: [
    { tier: 'very_high', min_prob: 0.6, historical_share: 0.82 },
    { tier: 'high', min_prob: 0.4, historical_share: 0.46 },
    { tier: 'medium', min_prob: 0.2, historical_share: 0.27 },
    { tier: 'lower', min_prob: 0, historical_share: 0.03 },
  ],
};

function alerts(overrides: Partial<RecentAlerts> = {}): RecentAlerts {
  return { data_through: '2026-11-14', alert_rules_version: '1.1', priority: [cell()], ...overrides };
}

describe('centerToLatLng', () => {
  it('turns the API [lon, lat] into the Leaflet [lat, lon]', () => {
    expect(centerToLatLng([-60.2, -3.1])).toEqual([-3.1, -60.2]);
  });
});

describe('alertBadge', () => {
  it('shows "Unusual for the season" only for attention and critical', () => {
    expect(alertBadge('critical')).toBe('Unusual for the season');
    expect(alertBadge('attention')).toBe('Unusual for the season');
    expect(alertBadge('normal')).toBeNull();
    expect(alertBadge(null)).toBeNull();
    expect(alertBadge(undefined)).toBeNull();
  });
});

describe('riskTierLabel', () => {
  it('names the four tiers in English', () => {
    expect(riskTierLabel('very_high')).toBe('Very high');
    expect(riskTierLabel('high')).toBe('High');
    expect(riskTierLabel('medium')).toBe('Medium');
    expect(riskTierLabel('lower')).toBe('Lower');
  });
});

describe('priorityView', () => {
  it('renders nothing without the alerts block (API before PR #86)', () => {
    expect(priorityView(undefined, false)).toBeNull();
  });

  it('keeps the order the API sends, never reordering', () => {
    const priority = [
      cell({ h3: 'a', alert_level: 'attention', detections_7d: 3 }),
      cell({ h3: 'b', alert_level: 'critical', detections_7d: 90 }),
      cell({ h3: 'c', alert_level: null, detections_7d: null, risk_tier: 'very_high' }),
    ];
    const view = priorityView(alerts({ priority }), false)!;
    expect(view.items.map((item) => item.h3)).toEqual(['a', 'b', 'c']);
  });

  it(`limits the list to ${PRIORITY_LIMIT} items until "Show all"`, () => {
    const priority = Array.from({ length: 13 }, (_, i) => cell({ h3: `cell-${i}` }));
    const short = priorityView(alerts({ priority }), false)!;
    expect(short.items).toHaveLength(10);
    expect(short.hidden).toBe(3);
    const all = priorityView(alerts({ priority }), true)!;
    expect(all.items).toHaveLength(13);
    expect(all.hidden).toBe(0);
  });

  it('says "No fire now" for an early-warning cell with null detections_7d, never 0', () => {
    const view = priorityView(alerts({ priority: [cell({ detections_7d: null, typical_median: null, alert_level: null })] }), false)!;
    expect(view.items[0].fireNow).toBe('No fire now');
    expect(view.items[0].fireNow).not.toMatch(/\b0\b/);
  });

  it('describes the last 7 days against the typical count when there is fire now', () => {
    const view = priorityView(alerts(), false)!;
    expect(view.items[0].fireNow).toBe('46 detections in 7 days (typical 7)');
    const noMedian = priorityView(alerts({ priority: [cell({ detections_7d: 1, typical_median: null })] }), false)!;
    expect(noMedian.items[0].fireNow).toBe('1 detection in 7 days');
  });

  it('gives each item its Leaflet position, its badge and its risk tier only when the API sends risk', () => {
    const withoutRisk = priorityView(alerts(), false)!;
    expect(withoutRisk.items[0]).toMatchObject({ latLng: [-3.1, -60.2], badge: 'Unusual for the season', risk: null });

    const withRisk = priorityView(
      alerts({ risk, priority: [cell({ alert_level: 'normal', risk_tier: 'high', risk_prob: 0.45 })] }),
      false,
    )!;
    expect(withRisk.items[0]).toMatchObject({ badge: null, risk: 'High' });
  });

  it('ignores a risk tier on the item when the legend (alerts.risk) is missing', () => {
    const view = priorityView(alerts({ priority: [cell({ risk_tier: 'very_high' })] }), false)!;
    expect(view.items[0].risk).toBeNull();
  });
});

describe('riskLegendView', () => {
  it('renders nothing without alerts or without alerts.risk: never a zeroed risk', () => {
    expect(riskLegendView(undefined)).toBeNull();
    expect(riskLegendView(alerts())).toBeNull();
  });

  it('builds the legend from the response numbers, in UTC', () => {
    const view = riskLegendView(alerts({ risk }))!;
    expect(view.title).toBe('Fire risk, next 14 days');
    expect(view.scoredAt).toBe('Scored on 14 Nov 2026, 06:12 UTC');
    expect(view.tiers).toEqual([
      'Very high: relevant fire (10+ detections) followed in 82% of past cases',
      'High: relevant fire (10+ detections) followed in 46% of past cases',
      'Medium: relevant fire (10+ detections) followed in 27% of past cases',
      'Lower: relevant fire (10+ detections) followed in 3% of past cases',
    ]);
    expect(view.caveat).toBe('A frequency from the past, not a forecast.');
  });

  it('follows the horizon and shares the API sends, not fixed numbers', () => {
    const other: RiskLegend = { ...risk, horizon_days: 7, tiers: [{ tier: 'very_high', min_prob: 0.5, historical_share: 0.7 }] };
    const view = riskLegendView(alerts({ risk: other }))!;
    expect(view.title).toBe('Fire risk, next 7 days');
    expect(view.tiers).toEqual(['Very high: relevant fire (10+ detections) followed in 70% of past cases']);
  });

  it('does not invent a share the API did not send', () => {
    const view = riskLegendView(alerts({ risk: { ...risk, tiers: [{ tier: 'lower', min_prob: 0, historical_share: null }] } }))!;
    expect(view.tiers).toEqual(['Lower: past share not available']);
  });

  it('lists the limits the screen must state', () => {
    const view = riskLegendView(alerts({ risk }))!;
    expect(view.limits.join(' ')).toMatch(/not burned area/);
    expect(view.limits.join(' ')).toMatch(/weather forecast/);
    expect(view.limits.join(' ')).toMatch(/Pantanal/);
    expect(view.limits.join(' ')).toMatch(/outside the fire season/);
  });
});
