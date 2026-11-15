import circle from "@turf/circle";
import { scaleSequentialLog, interpolateCividis } from "d3";
import type { Feature, Geometry } from "geojson";
import fixture from "@/data/demo-recent.json";
export type Level = "critical" | "attention" | "normal";
export type Intensity = "high" | "medium" | "low";
export type RiskTier = "very_high" | "high" | "medium" | "lower";
export const TIERS: RiskTier[] = ["very_high", "high", "medium", "lower"];
export const TIER_LABEL: Record<RiskTier, string> = { very_high: "Very high", high: "High", medium: "Medium", lower: "Lower" };
export const TIER_COLOR: Record<RiskTier, string> = { very_high: "#c62828", high: "#ef6c1a", medium: "#f5bf2a", lower: "#cdd2d8" };
// Escala logarítmica cividis, acessível a daltonismo (RD03 e RD04): poucos hot spots em azul-escuro,
// muitos em amarelo. O zero tem cor própria, fora da rampa (a escala logarítmica não representa o zero).
export const COUNT_DOMAIN: [number, number] = [1, 100];
export const ZERO_COLOR = "#d9dde3";
const countScale = scaleSequentialLog(interpolateCividis).domain(COUNT_DOMAIN).clamp(true);
export const countColor = (n: number) => (n > 0 ? countScale(n) : ZERO_COLOR);
export const COUNT_GRADIENT = `linear-gradient(to right, ${[1, 2, 4, 8, 16, 32, 64, 100].map(countColor).join(", ")})`;
export const RING_COLOR = { critical: "#d62728", attention: "#f2b134" } as const;
export type Viewport = { bbox: [number, number, number, number]; zoom: number };
export type DetectionProperties = {
  h3?: string;
  detections?: number;
  n_low?: number;
  n_medium?: number;
  n_high?: number;
  alert_cell?: string;
  alert_level?: Level;
  risk_prob?: number | null;
  risk_tier?: RiskTier | null;
  frp?: number;
  saturated?: boolean;
};
export type DetectionFeature = Feature<Geometry, DetectionProperties>;
export type Priority = {
  h3: string;
  alert_level: Level;
  detections_7d: number;
  typical_median: number;
  share_followed_by_high?: number;
  center: [number, number];
  risk_prob?: number | null;
  risk_tier?: RiskTier | null;
};
export type RiskLegend = {
  scored_at: string;
  data_ref: string;
  model_version: string;
  horizon_days: number;
  rules_version: string;
  tiers: { tier: RiskTier; min_prob: number; historical_share: number | null }[];
};
export type RecentData = {
  type: "FeatureCollection";
  mode: string;
  hours: number;
  updated_at: string;
  total_detections: number;
  features: DetectionFeature[];
  alerts?:
    | {
        data_through: string;
        alert_rules_version: string;
        unit: string;
        horizon_days: number;
        overall_share?: number;
        priority: Priority[];
        risk?: RiskLegend;
      }
    | undefined;
};
export const demoRecent = fixture as unknown as RecentData;
export const RECENT_WINDOWS = [24, 72, 168] as const;
export const RISK_HORIZON = 14;
export const intensityClass = (frp: number, saturated = false): Intensity =>
  saturated || frp >= 25 ? "high" : frp >= 5 ? "medium" : "low";
export const freshness = (updated: string, now = Date.now()) => {
  const hours = Math.max(0, (now - Date.parse(updated)) / 3600000);
  return {
    hours,
    relative: hours < 1 ? `${Math.floor(hours * 60)} min ago` : `${Math.floor(hours)} h ago`,
    state: hours > 24 ? "outdated" : hours > 6 ? "delayed" : "current",
  };
};
export function inView(center: [number, number], bbox: Viewport["bbox"]) {
  return (
    center[0] >= bbox[0] && center[0] <= bbox[2] && center[1] >= bbox[1] && center[1] <= bbox[3]
  );
}
export function priorityInView(data: RecentData, view: Viewport) {
  const rank = { critical: 0, attention: 1, normal: 2 };
  const tier = (p: Priority) => (p.risk_tier ? TIERS.indexOf(p.risk_tier) : TIERS.length);
  return (data.alerts?.priority ?? [])
    .filter((p) => inView(p.center, view.bbox))
    .sort((a, b) => tier(a) - tier(b) || rank[a.alert_level] - rank[b.alert_level] || b.detections_7d - a.detections_7d);
}
export function riskFrequency(cell: Priority, data: RecentData, drawn = false) {
  if (
    drawn ||
    cell.share_followed_by_high == null ||
    data.alerts?.overall_share == null ||
    data.alerts.horizon_days !== RISK_HORIZON
  )
    return null;
  return {
    share: cell.share_followed_by_high,
    average: data.alerts.overall_share,
    horizon: RISK_HORIZON,
  };
}
export function highShare(features: DetectionFeature[]) {
  let count = 0,
    high = 0;
  for (const f of features) {
    if (f.geometry.type === "Point") {
      if (f.properties.frp == null && !f.properties.saturated) return null;
      count++;
      high += intensityClass(f.properties.frp ?? 0, f.properties.saturated) === "high" ? 1 : 0;
    } else {
      if (f.properties.detections == null || f.properties.n_high == null) return null;
      count += f.properties.detections;
      high += f.properties.n_high;
    }
  }
  return count ? high / count : null;
}
export function demoInView(view: Viewport): RecentData {
  const visible = inView([-60.2, -3.1], view.bbox);
  // The supplied national total includes observations whose geometry was not supplied.
  // Only the literal example cell is suitable for viewport counts.
  return {
    ...demoRecent,
    total_detections: visible ? 46 : 0,
    features: visible ? demoRecent.features : [],
    alerts: demoRecent.alerts
      ? { ...demoRecent.alerts, priority: visible ? demoRecent.alerts.priority : [] }
      : undefined,
  };
}

export function demoForWindow(view: Viewport, hours: number): RecentData | null {
  return hours === 24 ? demoInView(view) : null;
}

export function recentTotals(data: RecentData) {
  return {
    detections: data.total_detections,
    critical: data.alerts ? data.alerts.priority.filter(cell => cell.alert_level === 'critical').length : null,
    attention: data.alerts ? data.alerts.priority.filter(cell => cell.alert_level === 'attention').length : null,
  };
}

export function coordinateArea(latitude: number, longitude: number, radius: number) {
  if (
    radius < 1 ||
    radius > 200 ||
    !Number.isFinite(radius) ||
    latitude < -90 ||
    latitude > 90 ||
    longitude < -180 ||
    longitude > 180
  )
    throw new Error("Coordinates or radius are outside the allowed range.");
  return circle([longitude, latitude], radius, { steps: 64, units: "kilometers" }).geometry;
}
