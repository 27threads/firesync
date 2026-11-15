import type { RecentWindow } from '../api/types';
import { formatCount, formatWindowValue } from '../format';
import { compareToTypical, type TypicalStatus } from './summaryModel';

export interface Verdict {
  status: TypicalStatus;
  headline: string;
  sentence: string;
}

const HEADLINES: Record<TypicalStatus, string> = {
  above: 'More fire than usual',
  within: 'About as much fire as usual',
  below: 'Less fire than usual',
};

// Modo simples: a mesma régua do cartão dos 7 dias (faixa P25–P75), dita sem termo técnico.
export function buildVerdict(window: RecentWindow): Verdict {
  const status = compareToTypical(window);
  const spots = window.detections === 1 ? 'hot spot' : 'hot spots';
  // Arredonda para dentro: um número inteiro está na frase se e só se o veredito dele for "within".
  const low = Math.ceil(window.typical_p25);
  const high = Math.floor(window.typical_p75);
  const usual = low <= high ? `${formatCount(low)} to ${formatCount(high)}` : `about ${formatWindowValue(window.typical_median)}`;
  return {
    status,
    headline: HEADLINES[status],
    sentence: `In the last 7 days, satellites spotted ${formatCount(window.detections)} ${spots} here. A usual week at this time of year has ${usual}.`,
  };
}
