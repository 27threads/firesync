import { describe, expect, it } from 'vitest';
import type { RecentHexagonFeature, RecentPointProperties } from '../api/types';
import {
  computeHexagonDomain,
  formatHexagonTooltip,
  formatPointTooltip,
  styleForHexagon,
  styleForIntensityPoint,
} from './recentDetectionsModel';

describe('recentDetectionsModel', () => {
  it('computes positive extent domain for hexagons and colors polygons with log cividis scale', () => {
    const features: RecentHexagonFeature[] = [
      {
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [[[-60, -3], [-60, -2], [-59, -2], [-60, -3]]] },
        properties: { h3: '85a8100ffffffff', detections: 5, n_low: 3, n_medium: 2, n_high: 0 },
      },
      {
        type: 'Feature',
        geometry: { type: 'Polygon', coordinates: [[[-59, -3], [-59, -2], [-58, -2], [-59, -3]]] },
        properties: { h3: '85a8101ffffffff', detections: 500, n_low: 200, n_medium: 200, n_high: 100 },
      },
    ];

    const domain = computeHexagonDomain(features);
    expect(domain).toEqual([5, 500]);

    const lowStyle = styleForHexagon(5, domain);
    const highStyle = styleForHexagon(500, domain);
    expect(lowStyle.fillColor).not.toBe(highStyle.fillColor);
    expect(highStyle.fillOpacity).toBeGreaterThan(lowStyle.fillOpacity);
  });

  it('differentiates low, medium, and high intensity points by radius and stroke weight in addition to color (RD04)', () => {
    const low = styleForIntensityPoint('low');
    const medium = styleForIntensityPoint('medium');
    const high = styleForIntensityPoint('high');

    // RD04: never rely on color alone — radius and stroke weight must progress from low < medium < high
    expect(low.radius).toBeLessThan(medium.radius);
    expect(medium.radius).toBeLessThan(high.radius);
    expect(low.weight).toBeLessThan(medium.weight);
    expect(medium.weight).toBeLessThan(high.weight);
    expect(new Set([low.fillColor, medium.fillColor, high.fillColor]).size).toBe(3);
  });

  it('formats hexagon and point tooltips in English with UTC timestamps and intensity classes (never FRP in MW)', () => {
    const hexHtml = formatHexagonTooltip({
      h3: '85a8100ffffffff',
      detections: 37,
      n_low: 21,
      n_medium: 12,
      n_high: 4,
    });
    expect(hexHtml).toMatch(/37 hot spots/i);
    expect(hexHtml).toMatch(/high:\s*4/i);
    expect(hexHtml).toMatch(/medium:\s*12/i);
    expect(hexHtml).toMatch(/low:\s*21/i);
    expect(hexHtml).not.toMatch(/\bFRP\b|\bMW\b/i);

    const pointProps: RecentPointProperties = {
      satellite: 'N20',
      acquired_utc: '2026-11-14T05:42:00Z',
      confidence: 'nominal',
      intensity: 'high',
      daynight: 'N',
    };
    const pointHtml = formatPointTooltip(pointProps);
    expect(pointHtml).toMatch(/High intensity/i);
    expect(pointHtml).toMatch(/2026-11-14 05:42 UTC/);
    expect(pointHtml).toMatch(/N20/);
    expect(pointHtml).toMatch(/nominal/i);
    expect(pointHtml).toMatch(/Night/i);
    expect(pointHtml).not.toMatch(/\bFRP\b|\bMW\b/i);
  });
});
