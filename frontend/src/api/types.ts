// Tipos da resposta de POST /calendar, iguais ao docs/api.md. Só o que o front usa.

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
  median: number;
  mean: number;
  min: number;
  max: number;
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
  latest_complete_year: { year: number; detections: number; reference_mean: number; anomaly_pct: number | null };
  last_7_days_vs_typical_pct: number | null;
}

export interface Meta {
  data_version: string;
  last_month: string;
  updated_at: string;
}

export interface CalendarResponse {
  meta: Meta;
  months: CalendarMonth[];
  years: YearTotal[];
  seasonality: SeasonalityMonth[];
  recent: Recent;
  indicators: Indicators;
}
