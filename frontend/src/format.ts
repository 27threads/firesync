import { MONTH_NAMES } from './calendar/calendarModel';

// Formatação dos números e datas da tela. Datas sempre em UTC (regra do CLAUDE.md).

const countFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
const windowFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 });

export function formatCount(value: number): string {
  return countFormat.format(value);
}

// Mediana e quartis de janelas curtas: arredondar para inteiro muda a diferença que a tela mostra.
export function formatWindowValue(value: number): string {
  return windowFormat.format(value);
}

export function formatSignedPct(value: number | null): string {
  if (value === null) return 'n/a';
  const rounded = Math.round(value * 100);
  if (rounded === 0) return '0%';
  return `${rounded > 0 ? '+' : '−'}${Math.abs(rounded)}%`;
}

export function formatShare(value: number): string {
  return `${Math.round(value * 100)}%`;
}

const pad = (n: number) => String(n).padStart(2, '0');

export function formatUpdatedAt(iso: string): string {
  const d = new Date(iso);
  return `${d.getUTCDate()} ${MONTH_NAMES[d.getUTCMonth()]} ${d.getUTCFullYear()}, ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}

function parseDay(value: string): { year: number; month: string; day: number } {
  const [year, month, day] = value.split('-').map(Number);
  return { year, month: MONTH_NAMES[month - 1], day };
}

export function formatDayRange(start: string, end: string): string {
  const a = parseDay(start);
  const b = parseDay(end);
  if (a.year !== b.year) return `${a.day} ${a.month} ${a.year} – ${b.day} ${b.month} ${b.year}`;
  if (a.month !== b.month) return `${a.day} ${a.month} – ${b.day} ${b.month} ${b.year}`;
  return `${a.day}–${b.day} ${b.month} ${b.year}`;
}
