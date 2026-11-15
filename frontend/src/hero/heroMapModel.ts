// Regras do mapa em tela cheia do hero (Fire now e Risk, next 14 days). Funções puras: a tela só desenha.
import type { AlertLevel, AreaInput, IntensityClass, PriorityCell, RecentHexagonProperties, RecentPointProperties, RiskTier } from '../api/types';
import { makeColorScale } from '../calendar/colorScale';

export type HeroMode = 'fire' | 'risk';

export const TIERS: RiskTier[] = ['very_high', 'high', 'medium', 'lower'];
export const TIER_LABEL: Record<RiskTier, string> = { very_high: 'Very high', high: 'High', medium: 'Medium', lower: 'Lower' };
export const TIER_COLOR: Record<RiskTier, string> = { very_high: '#c62828', high: '#ef6c1a', medium: '#f5bf2a', lower: '#cdd2d8' };

export const LEVELS: AlertLevel[] = ['critical', 'attention', 'normal'];
export const INTENSITIES: IntensityClass[] = ['high', 'medium', 'low'];

/** Opacidade da cor dos hexágonos: deixa o relevo e a vegetação do mapa aparecerem por baixo. */
// Over the dark Blue Marble the 0.55 of the first version hid the weak cells (review on 15/11).
export const HEX_FILL_OPACITY = 0.8;

// Escala logarítmica cividis (acessível a daltonismo, RD03 e RD04). O zero tem cor própria, fora da rampa.
export const COUNT_DOMAIN: [number, number] = [1, 100];
export const ZERO_COLOR = '#d9dde3';
const countScale = makeColorScale(COUNT_DOMAIN);
export const countColor = (detections: number): string => (detections > 0 ? countScale(detections) : ZERO_COLOR);
export const COUNT_GRADIENT = `linear-gradient(to right, ${[1, 2, 4, 8, 16, 32, 64, 100].map(countColor).join(', ')})`;

export interface HeroFilters {
  intensities: IntensityClass[];
  levels: AlertLevel[];
  tiers: RiskTier[];
  quietOnly: boolean;
}

export const DEFAULT_FILTERS: HeroFilters = {
  intensities: [...INTENSITIES],
  levels: [...LEVELS],
  tiers: [...TIERS],
  quietOnly: false,
};

/** Quantos filtros estão estreitando a vista (o contador do painel de filtros). */
export function filterCount(mode: HeroMode, f: HeroFilters): number {
  if (mode === 'fire') {
    return (f.intensities.length < INTENSITIES.length ? f.intensities.length : 0) + (f.levels.length < LEVELS.length ? f.levels.length : 0);
  }
  return (f.tiers.length < TIERS.length ? f.tiers.length : 0) + (f.quietOnly ? 1 : 0);
}

/** Um hexágono aparece no mapa conforme a aba e os filtros. */
export function hexVisible(p: RecentHexagonProperties, mode: HeroMode, f: HeroFilters): boolean {
  if (mode === 'risk') {
    return (!p.risk_tier || f.tiers.includes(p.risk_tier)) && (!f.quietOnly || !(p.detections > 0));
  }
  const noClasses = p.n_low == null && p.n_medium == null && p.n_high == null;
  const hasStrength =
    (p.n_low > 0 && f.intensities.includes('low')) || (p.n_medium > 0 && f.intensities.includes('medium')) || (p.n_high > 0 && f.intensities.includes('high'));
  return (noClasses || hasStrength) && (!p.alert_level || f.levels.includes(p.alert_level));
}

/** O mesmo filtro para a lista "Where to look first". */
export function priorityVisible(cell: PriorityCell, mode: HeroMode, f: HeroFilters): boolean {
  if (mode === 'risk') {
    return (!cell.risk_tier || f.tiers.includes(cell.risk_tier)) && (!f.quietOnly || !((cell.detections_7d ?? 0) > 0));
  }
  return !cell.alert_level || f.levels.includes(cell.alert_level);
}

export interface TierGroup {
  tier: RiskTier;
  cells: PriorityCell[];
}

/** Agrupa a lista por faixa de risco, da mais alta para a menor, e só devolve grupos com áreas. */
export function groupByTier(cells: PriorityCell[]): TierGroup[] {
  return TIERS.map((tier) => ({ tier, cells: cells.filter((c) => c.risk_tier === tier) })).filter((g) => g.cells.length > 0);
}

/** Muito alto e alto começam abertos; médio e menor, fechados. */
export const tierStartsOpen = (tier: RiskTier): boolean => tier === 'very_high' || tier === 'high';

/** "Ícone só quando o hexágono já comporta o símbolo": o raio do hexágono na tela, em pixels. */
export const MIN_ICON_HEX_RADIUS = 8;
export function iconSize(hexRadiusPx: number): number {
  return Math.round(Math.max(14, Math.min(24, hexRadiusPx * 0.9)));
}

const BRASILIA = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'America/Sao_Paulo' });
/** "15 Nov, 11:54" no horário de Brasília. */
export function brasiliaLabel(iso: string): string {
  return BRASILIA.format(new Date(iso));
}

/** "35 min ago" ou "2 h ago", a partir de updated_at. */
export function agoLabel(updatedIso: string, now: number = Date.now()): string {
  const hours = Math.max(0, (now - Date.parse(updatedIso)) / 3_600_000);
  return hours < 1 ? `${Math.floor(hours * 60)} min ago` : `${Math.floor(hours)} h ago`;
}

export type Staleness = 'current' | 'delayed' | 'outdated';
export function staleness(updatedIso: string, now: number = Date.now()): Staleness {
  const hours = (now - Date.parse(updatedIso)) / 3_600_000;
  return hours > 24 ? 'outdated' : hours > 6 ? 'delayed' : 'current';
}

export const levelName = (level: AlertLevel): string => (level === 'normal' ? 'Usual' : level === 'critical' ? 'Critical' : 'Attention');

/** "3.10°S, 52.40°W": hemispheres in words, so nobody has to read a minus sign. */
export function place(lat: number, lon: number): string {
  return `${Math.abs(lat).toFixed(2)}°${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lon).toFixed(2)}°${lon >= 0 ? 'E' : 'W'}`;
}

export interface MapSummary {
  title: string;
  lines: string[];
}

const LEVEL_SENTENCE: Record<AlertLevel, string> = {
  normal: 'About as much fire as usual for this time of year',
  attention: 'More fire than usual for this time of year',
  critical: 'Much more fire than usual for this time of year',
};

/** What a click on a hexagon tells, in plain words. `shares` = how often fire followed each risk tier in the past. */
export function hexSummary(
  p: RecentHexagonProperties,
  lat: number,
  lon: number,
  hours: number,
  shares: Partial<Record<RiskTier, number>> = {},
): MapSummary {
  const lines = [p.detections > 0 ? `${p.detections} hot spots in the last ${hours} h` : `No hot spots in the last ${hours} h`];
  if (p.detections > 0) lines.push(`Fire strength: ${p.n_high} strong · ${p.n_medium} medium · ${p.n_low} weak`);
  if (p.alert_level) lines.push(LEVEL_SENTENCE[p.alert_level]);
  if (p.risk_tier) {
    const share = shares[p.risk_tier];
    lines.push(
      `Next 14 days: ${TIER_LABEL[p.risk_tier].toLowerCase()} risk` +
        (share != null ? ` (fire followed in ${Math.round(share * 100)}% of similar past cases)` : ''),
    );
  }
  lines.push('Zoom in to see each fire point.');
  return { title: `Area near ${place(lat, lon)}`, lines };
}

const SATELLITE_NAME: Record<string, string> = { N20: 'NOAA-20', N21: 'NOAA-21', SNPP: 'Suomi NPP' };
const CONFIDENCE_WORD: Record<string, string> = { high: 'high', nominal: 'medium', low: 'low' };

/** What a click on one detection tells: where, when, which satellite and how strong. */
export function pointSummary(p: RecentPointProperties, lat: number, lon: number): MapSummary {
  return {
    title: 'Fire detected by satellite',
    lines: [
      `Where: ${place(lat, lon)}`,
      `When: ${brasiliaLabel(p.acquired_utc)} (Brasília time)`,
      `Seen by: ${SATELLITE_NAME[p.satellite] ?? p.satellite} (VIIRS sensor), during the ${p.daynight === 'D' ? 'day' : 'night'}`,
      `Fire strength: ${p.intensity === 'high' ? 'strong' : p.intensity === 'medium' ? 'medium' : 'weak'}`,
      `Detection confidence: ${CONFIDENCE_WORD[p.confidence] ?? p.confidence}`,
    ],
  };
}

/**
 * The hero map and the explorer are separate React roots: an area chosen on the hero map reaches the explorer
 * (calendar, summary) through this window event, so Region, Draw area and Coordinates do what they promise.
 */
export const HERO_AREA_EVENT = 'firesync:hero-area';
export const announceArea = (area: AreaInput) => window.dispatchEvent(new CustomEvent<AreaInput>(HERO_AREA_EVENT, { detail: area }));
