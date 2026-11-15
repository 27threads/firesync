import type { PriorityCell, RecentHexagonProperties } from '../api/types';
import {
  DEFAULT_FILTERS,
  ZERO_COLOR,
  agoLabel,
  brasiliaLabel,
  countColor,
  filterCount,
  groupByTier,
  hexVisible,
  iconSize,
  priorityVisible,
  staleness,
  tierStartsOpen,
} from './heroMapModel';

const hex = (over: Partial<RecentHexagonProperties> = {}): RecentHexagonProperties => ({
  h3: 'a',
  detections: 10,
  n_low: 5,
  n_medium: 3,
  n_high: 2,
  ...over,
});
const cell = (over: Partial<PriorityCell> = {}): PriorityCell => ({
  h3: 'a',
  alert_level: 'normal',
  detections_7d: 10,
  typical_median: 5,
  share_followed_by_high: null,
  center: [-60, -3],
  ...over,
});

const luminance = (rgb: string) => {
  const m = rgb.match(/\d+/g)!.map(Number);
  return 0.2126 * m[0]! + 0.7152 * m[1]! + 0.0722 * m[2]!;
};

describe('escala de cor dos hot spots (cividis, logarítmica)', () => {
  test('zero tem cor própria, fora da rampa', () => {
    expect(countColor(0)).toBe(ZERO_COLOR);
    expect(countColor(1)).not.toBe(ZERO_COLOR);
  });
  test('a luminosidade cresce com a contagem e acima de 100 a cor não muda', () => {
    expect(luminance(countColor(10))).toBeGreaterThan(luminance(countColor(1)));
    expect(luminance(countColor(100))).toBeGreaterThan(luminance(countColor(10)));
    expect(countColor(5000)).toBe(countColor(100));
  });
});

describe('filtros do mapa', () => {
  test('sem filtro nenhum, o contador é zero e tudo aparece', () => {
    expect(filterCount('fire', DEFAULT_FILTERS)).toBe(0);
    expect(filterCount('risk', DEFAULT_FILTERS)).toBe(0);
    expect(hexVisible(hex(), 'fire', DEFAULT_FILTERS)).toBe(true);
  });
  test('o contador soma só os filtros que estreitam a vista', () => {
    expect(filterCount('fire', { ...DEFAULT_FILTERS, intensities: ['high'] })).toBe(1);
    expect(filterCount('risk', { ...DEFAULT_FILTERS, tiers: ['very_high', 'high'], quietOnly: true })).toBe(3);
  });
  test('Fire now filtra pela força do fogo e pelo nível', () => {
    const onlyHigh = { ...DEFAULT_FILTERS, intensities: ['high' as const] };
    expect(hexVisible(hex({ n_high: 0 }), 'fire', onlyHigh)).toBe(false);
    expect(hexVisible(hex({ n_high: 4 }), 'fire', onlyHigh)).toBe(true);
    expect(hexVisible(hex({ alert_level: 'critical' }), 'fire', { ...DEFAULT_FILTERS, levels: ['attention'] })).toBe(false);
  });
  test('Risk filtra pela faixa e por "No hot spots now"', () => {
    const tiers = { ...DEFAULT_FILTERS, tiers: ['very_high' as const] };
    expect(hexVisible(hex({ risk_tier: 'lower' }), 'risk', tiers)).toBe(false);
    expect(hexVisible(hex({ risk_tier: 'very_high' }), 'risk', tiers)).toBe(true);
    const quiet = { ...DEFAULT_FILTERS, quietOnly: true };
    expect(hexVisible(hex({ detections: 0, risk_tier: 'high' }), 'risk', quiet)).toBe(true);
    expect(hexVisible(hex({ detections: 3, risk_tier: 'high' }), 'risk', quiet)).toBe(false);
  });
  test('a lista de prioridades segue as mesmas regras', () => {
    expect(priorityVisible(cell({ risk_tier: 'lower' }), 'risk', { ...DEFAULT_FILTERS, tiers: ['high'] })).toBe(false);
    expect(priorityVisible(cell({ alert_level: 'critical' }), 'fire', { ...DEFAULT_FILTERS, levels: ['critical'] })).toBe(true);
  });
});

describe('Where to look first agrupado por risco', () => {
  const cells = [cell({ h3: 'm', risk_tier: 'medium' }), cell({ h3: 'v1', risk_tier: 'very_high' }), cell({ h3: 'v2', risk_tier: 'very_high' }), cell({ h3: 'x' })];
  test('agrupa da faixa mais alta para a menor, sem grupos vazios e sem áreas sem faixa', () => {
    const groups = groupByTier(cells);
    expect(groups.map((g) => g.tier)).toEqual(['very_high', 'medium']);
    expect(groups[0]!.cells.map((c) => c.h3)).toEqual(['v1', 'v2']);
  });
  test('muito alto e alto começam abertos; médio e menor, fechados', () => {
    expect([tierStartsOpen('very_high'), tierStartsOpen('high'), tierStartsOpen('medium'), tierStartsOpen('lower')]).toEqual([true, true, false, false]);
  });
});

describe('ícone, horário e frescor', () => {
  test('o ícone tem tamanho mínimo e máximo', () => {
    expect(iconSize(8)).toBe(14);
    expect(iconSize(100)).toBe(24);
  });
  test('o horário do risco sai em Brasília', () => {
    expect(brasiliaLabel('2026-11-15T14:54:13Z')).toBe('15 Nov, 11:54');
  });
  test('há quanto tempo e se o dado está atrasado', () => {
    const now = Date.parse('2026-11-15T15:00:00Z');
    expect(agoLabel('2026-11-15T14:25:00Z', now)).toBe('35 min ago');
    expect(agoLabel('2026-11-15T13:00:00Z', now)).toBe('2 h ago');
    expect(staleness('2026-11-15T13:00:00Z', now)).toBe('current');
    expect(staleness('2026-11-15T07:00:00Z', now)).toBe('delayed');
    expect(staleness('2026-11-14T10:00:00Z', now)).toBe('outdated');
  });
});
