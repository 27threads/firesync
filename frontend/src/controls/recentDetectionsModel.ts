import type {
  IntensityClass,
  RecentHexagonFeature,
  RecentHexagonProperties,
  RecentPointProperties,
} from '../api/types';
import { makeColorScale } from '../calendar/colorScale';

export interface HexagonLayerStyle {
  fillColor: string;
  fillOpacity: number;
  color: string;
  weight: number;
}

export interface PointIntensityStyle {
  radius: number;
  weight: number;
  color: string;
  fillColor: string;
  fillOpacity: number;
  dashArray?: string;
  label: string;
}

/** Computes the positive [min, max] domain of hexagon detection counts for log-cividis scaling. */
export function computeHexagonDomain(features: RecentHexagonFeature[]): [number, number] {
  let min = Infinity;
  let max = -Infinity;
  for (const feature of features) {
    const d = feature.properties.detections;
    if (d > 0) {
      if (d < min) min = d;
      if (d > max) max = d;
    }
  }
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [1, 10];
  return [min, Math.max(min, max)];
}

/** Computes the Leaflet polygon style for an H3 hexagon using the calendar's log-cividis scale. */
export function styleForHexagon(detections: number, domain: [number, number]): HexagonLayerStyle {
  const scale = makeColorScale(domain);
  const fillColor = scale(Math.max(1, detections));
  const [min, max] = domain;
  const ratio =
    max > min ? (Math.log10(Math.max(1, detections)) - Math.log10(min)) / (Math.log10(max) - Math.log10(min)) : 0.5;
  const clamped = Math.max(0, Math.min(1, ratio));
  return {
    fillColor,
    fillOpacity: Number((0.55 + clamped * 0.3).toFixed(2)),
    color: '#0d0f11',
    weight: 1,
  };
}

/**
 * Returns Leaflet circleMarker styling for a point detection by intensity class (RD04, RD07).
 * Differentiates low, medium, and high by radius and border weight in addition to color.
 */
export function styleForIntensityPoint(intensity: IntensityClass): PointIntensityStyle {
  switch (intensity) {
    case 'high':
      return {
        radius: 8.5,
        weight: 3,
        color: '#fff7df',
        fillColor: '#f0a23a',
        fillOpacity: 0.92,
        label: 'High intensity',
      };
    case 'medium':
      return {
        radius: 6,
        weight: 2,
        color: '#0d0f11',
        fillColor: '#e0c25c',
        fillOpacity: 0.86,
        label: 'Medium intensity',
      };
    case 'low':
    default:
      return {
        radius: 4,
        weight: 1,
        color: '#c6cdd4',
        fillColor: '#8fa3b8',
        fillOpacity: 0.8,
        dashArray: '2 2',
        label: 'Low intensity',
      };
  }
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatAcquiredUtc(isoUtc: string): string {
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})/.exec(isoUtc.trim());
  if (m) return `${m[1]} ${m[2]} UTC`;
  return `${isoUtc} UTC`;
}

/** Formats an accessible English tooltip for an H3 hexagon without raw FRP in MW. */
export function formatHexagonTooltip(props: RecentHexagonProperties): string {
  const total = props.detections.toLocaleString('en-US');
  const high = props.n_high.toLocaleString('en-US');
  const medium = props.n_medium.toLocaleString('en-US');
  const low = props.n_low.toLocaleString('en-US');
  return [
    `<div class="map-detection-tooltip">`,
    `<strong>${total} hot spots</strong> <span class="muted">(H3 ${escapeHtml(props.h3)})</span>`,
    `<div>Intensity — High: ${high} · Medium: ${medium} · Low: ${low}</div>`,
    `</div>`,
  ].join('');
}

/** Formats an accessible English tooltip for an individual hot spot point in UTC without raw FRP in MW. */
export function formatPointTooltip(props: RecentPointProperties): string {
  const style = styleForIntensityPoint(props.intensity);
  const passLabel = props.daynight === 'N' ? 'Night pass' : 'Day pass';
  return [
    `<div class="map-detection-tooltip">`,
    `<strong>${escapeHtml(style.label)}</strong> · ${escapeHtml(formatAcquiredUtc(props.acquired_utc))}`,
    `<div>Satellite: ${escapeHtml(props.satellite)} · Confidence: ${escapeHtml(props.confidence)} · ${passLabel}</div>`,
    `</div>`,
  ].join('');
}
