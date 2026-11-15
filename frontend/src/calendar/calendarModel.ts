import type { CalendarMonth } from '../api/types';

export const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export type CellState = 'value' | 'zero' | 'no_data' | 'not_requested';

export interface CalendarCell {
  key: string; // YYYY-MM
  year: number;
  monthIndex: number; // 0 = janeiro
  state: CellState;
  detections: number;
  estimated: boolean;
  incomplete: boolean;
  label: string;
}

export interface YearRow {
  year: number;
  cells: CalendarCell[];
}

export interface MonthPosition {
  year: number;
  monthIndex: number;
}

export interface CalendarModel {
  years: YearRow[];
  sensorSwitch: MonthPosition | null;
  positiveExtent: [number, number] | null;
}

const countFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });

function daysInMonth(year: number, monthIndex: number): number {
  return new Date(Date.UTC(year, monthIndex + 1, 0)).getUTCDate();
}

function parseMonth(value: string): MonthPosition {
  const [year, month] = value.split('-').map(Number);
  return { year, monthIndex: month - 1 };
}

function monthKey(year: number, monthIndex: number): string {
  return `${year}-${String(monthIndex + 1).padStart(2, '0')}`;
}

function stateOf(month: CalendarMonth, position: MonthPosition): CellState {
  // Um mês inteiro sem dado do satélite não é um mês com zero focos.
  if (month.missing_days >= daysInMonth(position.year, position.monthIndex)) return 'no_data';
  return month.detections === 0 ? 'zero' : 'value';
}

function describe(month: CalendarMonth, position: MonthPosition, state: CellState): string {
  const name = `${MONTH_NAMES[position.monthIndex]} ${position.year}`;
  if (state === 'no_data') return `${name}: no satellite data`;

  const parts = [`${countFormat.format(month.detections)} detections`];
  if (month.source === 'estimated_modis') {
    const range =
      month.band_low !== null && month.band_high !== null
        ? ` (range ${countFormat.format(month.band_low)} to ${countFormat.format(month.band_high)})`
        : '';
    parts.push(`estimated from MODIS${range}`);
  } else {
    parts.push('observed by VIIRS');
  }
  if (month.missing_days > 0) parts.push(`${month.missing_days} days without satellite data`);
  if (month.incomplete) parts.push('incomplete month');
  if (month.provisional) parts.push('provisional (near real-time data)');
  return `${name}: ${parts.join(', ')}`;
}

function emptyCell(year: number, monthIndex: number): CalendarCell {
  return {
    key: monthKey(year, monthIndex),
    year,
    monthIndex,
    state: 'not_requested',
    detections: 0,
    estimated: false,
    incomplete: false,
    label: `${MONTH_NAMES[monthIndex]} ${year}: outside the selected period`,
  };
}

function toCell(month: CalendarMonth): CalendarCell {
  const position = parseMonth(month.month);
  const state = stateOf(month, position);
  return {
    key: month.month,
    ...position,
    state,
    detections: month.detections,
    estimated: month.source === 'estimated_modis',
    incomplete: month.incomplete,
    label: describe(month, position, state),
  };
}

function findSensorSwitch(months: CalendarMonth[]): MonthPosition | null {
  const hasEstimated = months.some((m) => m.source === 'estimated_modis');
  const firstObserved = months.find((m) => m.source === 'observed_viirs');
  return hasEstimated && firstObserved ? parseMonth(firstObserved.month) : null;
}

function findPositiveExtent(cells: CalendarCell[]): [number, number] | null {
  const positives = cells.filter((c) => c.state === 'value').map((c) => c.detections);
  return positives.length ? [Math.min(...positives), Math.max(...positives)] : null;
}

export function buildCalendar(months: CalendarMonth[]): CalendarModel {
  const cells = months.map(toCell);
  const byKey = new Map(cells.map((cell) => [cell.key, cell]));
  const firstYear = Math.min(...cells.map((c) => c.year));
  const lastYear = Math.max(...cells.map((c) => c.year));

  const years: YearRow[] = [];
  for (let year = firstYear; year <= lastYear; year++) {
    years.push({
      year,
      cells: MONTH_NAMES.map((_, monthIndex) => byKey.get(monthKey(year, monthIndex)) ?? emptyCell(year, monthIndex)),
    });
  }

  return { years, sensorSwitch: findSensorSwitch(months), positiveExtent: findPositiveExtent(cells) };
}
