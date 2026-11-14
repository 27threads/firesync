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
