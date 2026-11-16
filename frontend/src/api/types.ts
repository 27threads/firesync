// Tipos da resposta de POST /calendar, iguais ao docs/api.md. Só o que o front usa.

export interface GeoJsonPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface RegionArea {
  type: 'region';
  region_id: number;
}

export interface GeoJsonArea {
  type: 'geojson';
  geometry: GeoJsonPolygon;
}

export interface PointArea {
  type: 'point';
  lat: number;
  lon: number;
  radius_km: number;
}

export type AreaInput = RegionArea | GeoJsonArea | PointArea;

export interface PeriodInput {
  start?: string;
  end?: string;
}

export interface CalendarRequest {
  area: AreaInput;
  start?: string;
  end?: string;
}

export interface RegionOption {
  region_id: number;
  name: string;
  source: string;
  bbox: [number, number, number, number];
}

export interface HealthResponse {
  status: string;
  data_version: string;
  last_month: string;
  updated_at: string;
  h3_resolution: number;
}

export type CoverageStatus = 'full' | 'partial' | 'none';

export interface Coverage {
  status: CoverageStatus;
  covered_fraction: number;
  message: string | null;
}

export interface BiomeShare {
  region_id: number;
  name: string;
  fraction: number;
}

export interface ResponseArea {
  type: 'region' | 'geojson' | 'point';
  n_cells: number;
  area_km2: number;
  biomes: BiomeShare[];
}

export interface NoCoverageResponse {
  meta: Meta;
  area: ResponseArea;
  coverage: Coverage & { status: 'none' };
}

export type MonthSource = 'estimated_modis' | 'observed_viirs';

export interface CalendarMonth {
  month: string; // YYYY-MM
  detections: number;
  band_low: number | null;
  band_high: number | null;
  source: MonthSource;
  raw_count: number;
  missing_days: number;
  incomplete: boolean;
  provisional: boolean;
  anomaly: number | null;
  anomaly_pct: number | null;
}

export type YearSource = MonthSource | 'mixed';

export interface YearTotal {
  year: number;
  detections: number;
  band_low: number | null;
  band_high: number | null;
  source: YearSource;
  complete: boolean;
  rank: number | null;
}

export interface SeasonalityMonth {
  month_of_year: number; // 1–12
  median: number | null; // null when the period has no complete year (n_years 0)
  mean: number | null; // null when the period has no complete year (n_years 0)
  min: number | null; // null when the period has no complete year (n_years 0)
  max: number | null; // null when the period has no complete year (n_years 0)
  n_years: number;
}

export interface RecentWindow {
  start: string; // YYYY-MM-DD
  end: string;
  detections: number;
  typical_median: number;
  typical_p25: number;
  typical_p75: number;
  difference: number;
  difference_pct: number | null;
  n_years: number;
  n_windows: number;
  n_high: number;
  high_share: number | null;
}

export interface Recent {
  data_through: string;
  last_7_days: RecentWindow;
  month_to_date: RecentWindow;
}

export interface Indicators {
  total_detections: number;
  latest_complete_year: { year: number; detections: number; reference_median: number | null; anomaly_pct: number | null } | null;
  last_7_days_vs_typical_pct: number | null;
}

export interface Meta {
  data_version: string;
  last_month: string;
  updated_at: string;
}

export interface CalendarResponse {
  meta: Meta;
  area?: ResponseArea;
  coverage?: Coverage;
  months: CalendarMonth[];
  years: YearTotal[];
  seasonality: SeasonalityMonth[];
  recent: Recent;
  indicators: Indicators;
}

export type CalendarApiResult = CalendarResponse | NoCoverageResponse;

export type IntensityClass = 'low' | 'medium' | 'high';
export type DetectionConfidence = 'low' | 'nominal' | 'high';
export type RecentHours = 24 | 72 | 168;
export type RecentDetectionsMode = 'auto' | 'hexagons' | 'points';

export interface RecentDetectionsParams {
  bbox: [number, number, number, number];
  hours?: RecentHours;
  zoom: number;
  mode?: RecentDetectionsMode;
}

// Aviso antecipado (RFC 0003, PRs #86 e #97 da API). Tudo opcional: a API no ar pode ainda não mandar.
export type AlertLevel = 'normal' | 'attention' | 'critical';
export type RiskTier = 'very_high' | 'high' | 'medium' | 'lower';

export interface RecentHexagonProperties {
  h3: string;
  detections: number;
  n_low: number;
  n_medium: number;
  n_high: number;
  alert_cell?: string;
  alert_level?: AlertLevel | null;
  risk_prob?: number | null;
  risk_tier?: RiskTier | null;
}

export interface RiskTierLegend {
  tier: RiskTier;
  min_prob: number;
  historical_share: number | null;
}

export interface RiskLegend {
  scored_at: string;
  data_ref: string;
  model_version: string;
  horizon_days: number;
  rules_version: string;
  tiers: RiskTierLegend[];
}

export interface PriorityCell {
  h3: string;
  alert_level: AlertLevel | null;
  detections_7d: number | null;
  typical_median: number | null;
  share_followed_by_high: number | null;
  center: [number, number]; // [lon, lat], como o GeoJSON
  risk_prob?: number | null;
  risk_tier?: RiskTier | null;
}

export interface RecentAlerts {
  data_through: string;
  alert_rules_version: string;
  unit?: string | null;
  horizon_days?: number | null;
  overall_share?: number | null;
  priority: PriorityCell[];
  risk?: RiskLegend;
}

export interface RecentHexagonFeature {
  type: 'Feature';
  geometry: GeoJsonPolygon;
  properties: RecentHexagonProperties;
}

export interface GeoJsonPoint {
  type: 'Point';
  coordinates: [number, number];
}

export interface RecentPointProperties {
  satellite: string;
  acquired_utc: string;
  confidence: DetectionConfidence;
  intensity: IntensityClass;
  daynight: 'D' | 'N';
}

export interface RecentPointFeature {
  type: 'Feature';
  geometry: GeoJsonPoint;
  properties: RecentPointProperties;
}

export interface RecentDetectionsHexagonsResponse {
  type: 'FeatureCollection';
  mode: 'hexagons';
  h3_resolution: number;
  hours: RecentHours;
  updated_at: string;
  total_detections: number;
  features: RecentHexagonFeature[];
  alerts?: RecentAlerts;
}

export interface RecentDetectionsPointsResponse {
  type: 'FeatureCollection';
  mode: 'points';
  hours: RecentHours;
  updated_at: string;
  total_detections: number;
  features: RecentPointFeature[];
  alerts?: RecentAlerts;
}

export type RecentDetectionsResponse =
  | RecentDetectionsHexagonsResponse
  | RecentDetectionsPointsResponse;

/** Assistant chat (RFC 0004): plain text turns only; the server rejects anything else. */
export interface AssistantMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AssistantAction {
  type: 'show_calendar' | 'download_export';
  /** Region and period, e.g. "Pantanal · 2024-01 to 2024-12": one answer can carry buttons for several. */
  label?: string;
  area: RegionArea;
  start?: string;
  end?: string;
}

/** Where the answer's figures came from: the API route and request each tool ran, with the data version. */
export interface AssistantSource {
  endpoint: string;
  region?: string;
  start?: string;
  end?: string;
  hours?: number;
  data_version: string;
}

export interface AssistantResponse {
  answer: string;
  actions: AssistantAction[];
  notes: string[];
  sources: AssistantSource[];
  verified: boolean;
}
