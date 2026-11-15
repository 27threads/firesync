import type { RecentWindow } from '../api/types';
import { buildVerdict } from './verdictModel';

function week(detections: number, p25 = 35.2, p75 = 45.5, median = (p25 + p75) / 2): RecentWindow {
  return {
    start: '2026-11-08',
    end: '2026-11-14',
    detections,
    typical_median: median,
    typical_p25: p25,
    typical_p75: p75,
    difference: detections - 39.5,
    difference_pct: (detections - 39.5) / 39.5,
    n_years: 14,
    n_windows: 434,
    n_high: 0,
    high_share: 0,
  };
}

// Modo simples: a resposta em palavras que uma criança entende, com a mesma régua da faixa típica (P25–P75).
describe('buildVerdict', () => {
  it('says "more fire than usual" above the typical range', () => {
    const v = buildVerdict(week(61));
    expect(v.status).toBe('above');
    expect(v.headline).toBe('More fire than usual');
  });

  it('says "about as much fire as usual" inside the range, ends included', () => {
    expect(buildVerdict(week(40)).headline).toBe('About as much fire as usual');
    expect(buildVerdict(week(45.5)).status).toBe('within');
  });

  it('says "less fire than usual" below the typical range', () => {
    expect(buildVerdict(week(10)).headline).toBe('Less fire than usual');
  });

  it('explains with the count and the usual range, without technical words', () => {
    const v = buildVerdict(week(16842, 8887, 20614));
    expect(v.sentence).toBe('In the last 7 days, satellites spotted 16,842 hot spots here. A usual week at this time of year has 8,887 to 20,614.');
    expect(v.sentence).not.toMatch(/P25|P75|percentile|median|VIIRS|window/i);
  });

  // Contagens são inteiras: arredonda para dentro da faixa, para a frase nunca contradizer o veredito.
  it('shows the usual range as whole numbers inside the typical range', () => {
    expect(buildVerdict(week(40)).sentence).toMatch(/has 36 to 45\.$/);
    expect(buildVerdict(week(46)).status).toBe('above');
  });

  it('falls back to "about" the median when no whole number fits the range', () => {
    expect(buildVerdict(week(3, 3.2, 3.6, 3.5)).sentence).toMatch(/has about 3\.5\.$/);
  });

  it('uses the singular for one hot spot', () => {
    expect(buildVerdict(week(1)).sentence).toMatch(/spotted 1 hot spot here\./);
  });
});
