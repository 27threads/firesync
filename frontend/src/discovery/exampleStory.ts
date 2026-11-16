import type { CalendarResponse } from '../api/types';
import { MONTH_NAMES } from '../calendar/calendarModel';
import { formatCount, formatDayRange, formatWindowValue } from '../format';
import { compareToTypical, completeSeasonality } from '../summary/summaryModel';

// Perguntas e respostas da descoberta guiada. Todo texto sai dos campos da resposta:
// nada de nome de evento, ano famoso ou número escrito à mão.

export interface StoryStep {
  id: 'recent' | 'season' | 'ranking';
  question: string;
  answer: string;
  monthIndex?: number;
  year?: number;
}

const STATUS_PHRASES = {
  above: 'Above the typical range',
  within: 'Within the typical range',
  below: 'Below the typical range',
} as const;

function recentStep(data: CalendarResponse): StoryStep {
  const w = data.recent.last_7_days;
  const status = compareToTypical(w);
  return {
    id: 'recent',
    question: 'Are the last 7 days unusual for this time of year?',
    answer:
      `${STATUS_PHRASES[status]}: ${formatCount(w.detections)} detections from ${formatDayRange(w.start, w.end)}, ` +
      `against a typical ${formatWindowValue(w.typical_p25)}–${formatWindowValue(w.typical_p75)} ` +
      `for the same dates (P25–P75 of ${formatCount(w.n_windows)} windows across ${w.n_years} years).`,
  };
}

function seasonStep(data: CalendarResponse): StoryStep | null {
  const season = completeSeasonality(data.seasonality);
  if (!season) return null;
  const peak = season.reduce((best, m) => (m.median > best.median ? m : best));
  const name = MONTH_NAMES[peak.month_of_year - 1];
  return {
    id: 'season',
    question: 'When does fire activity usually peak here?',
    answer:
      `${name} has the highest median: ${formatCount(peak.median)} detections, ` +
      `between ${formatCount(peak.min)} and ${formatCount(peak.max)} across ${peak.n_years} complete years.`,
    monthIndex: peak.month_of_year - 1,
  };
}

function rankingStep(data: CalendarResponse): StoryStep | null {
  const top = data.years.find((y) => y.complete && y.rank === 1);
  if (!top) return null;
  const origin =
    top.source === 'observed_viirs'
      ? 'observed by VIIRS'
      : top.source === 'mixed'
        ? 'part estimated from MODIS, part observed by VIIRS'
        : 'estimated from MODIS';
  const band =
    top.band_low !== null && top.band_high !== null
      ? `, range ${formatCount(top.band_low)}–${formatCount(top.band_high)}`
      : '';
  return {
    id: 'ranking',
    question: 'Which year had the most detections?',
    answer: `${top.year} ranks first among complete years: ${formatCount(top.detections)} detections, ${origin}${band}.`,
    year: top.year,
  };
}

export function buildExampleStory(data: CalendarResponse): StoryStep[] {
  const steps = [recentStep(data), seasonStep(data), rankingStep(data)];
  return steps.filter((s): s is StoryStep => s !== null);
}
