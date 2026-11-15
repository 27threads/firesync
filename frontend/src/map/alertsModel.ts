import type { AlertLevel, RecentAlerts, RiskTier } from '../api/types';
import { formatCount, formatShare, formatUpdatedAt } from '../format';

// Aviso antecipado (RFC 0003). Tudo aqui sai da resposta da API: sem `alerts` ou sem `alerts.risk`,
// a parte correspondente não aparece. Nunca risco zerado nem número escrito no código.

// No pico da temporada a lista fica longa (docs/ux-telas.md, decisão 4): a tela mostra 10 e oferece "Show all".
export const PRIORITY_LIMIT = 10;

const TIER_LABELS: Record<RiskTier, string> = {
  very_high: 'Very high',
  high: 'High',
  medium: 'Medium',
  lower: 'Lower',
};

// Os limites que a tela precisa dizer junto com o risco (docs/ux-telas.md e docs/requisitos.md, RD08).
const RISK_LIMITS = [
  'Counts satellite fire detections, not burned area.',
  'Uses no weather forecast.',
  'Few data for the Pantanal.',
  'Lower coverage outside the fire season.',
];

export interface PriorityItem {
  h3: string;
  latLng: [number, number];
  badge: string | null;
  fireNow: string;
  risk: string | null;
}

export interface PriorityView {
  dataThrough: string;
  items: PriorityItem[];
  total: number;
  hidden: number;
}

export interface RiskLegendView {
  title: string;
  scoredAt: string;
  tiers: string[];
  caveat: string;
  limits: string[];
}

/** The API sends `center` as [lon, lat] (GeoJSON); Leaflet wants [lat, lon]. The only place that converts it. */
export function centerToLatLng([lon, lat]: [number, number]): [number, number] {
  return [lat, lon];
}

/** The v1 alert level is a badge, shown only when the week is unusual for the season. */
export function alertBadge(level: AlertLevel | null | undefined): string | null {
  return level === 'attention' || level === 'critical' ? 'Unusual for the season' : null;
}

export function riskTierLabel(tier: RiskTier): string {
  return TIER_LABELS[tier];
}

function describeFireNow(detections: number | null, typical: number | null): string {
  // Sem contagem recente, a célula entrou pelo risco: aviso antecipado, sem fogo agora (nunca "0").
  if (detections === null) return 'No fire now';
  const count = `${formatCount(detections)} ${detections === 1 ? 'detection' : 'detections'} in 7 days`;
  return typical === null ? count : `${count} (typical ${formatCount(typical)})`;
}

/** "Where to look first": the API order, cut to PRIORITY_LIMIT unless the user asked for all. */
export function priorityView(alerts: RecentAlerts | undefined, showAll: boolean): PriorityView | null {
  if (!alerts) return null;
  const hasRisk = alerts.risk !== undefined;
  const shown = showAll ? alerts.priority : alerts.priority.slice(0, PRIORITY_LIMIT);
  return {
    dataThrough: alerts.data_through,
    total: alerts.priority.length,
    hidden: alerts.priority.length - shown.length,
    items: shown.map((cell) => ({
      h3: cell.h3,
      latLng: centerToLatLng(cell.center),
      badge: alertBadge(cell.alert_level),
      fireNow: describeFireNow(cell.detections_7d, cell.typical_median),
      risk: hasRisk && cell.risk_tier ? riskTierLabel(cell.risk_tier) : null,
    })),
  };
}

/** Legend of the 14-day risk, only when the API sends `alerts.risk`. */
export function riskLegendView(alerts: RecentAlerts | undefined): RiskLegendView | null {
  const risk = alerts?.risk;
  if (!risk) return null;
  return {
    title: `Fire risk, next ${risk.horizon_days} days`,
    scoredAt: `Scored on ${formatUpdatedAt(risk.scored_at)}`,
    tiers: risk.tiers.map(({ tier, historical_share }) =>
      historical_share === null
        ? `${riskTierLabel(tier)}: past share not available`
        : `${riskTierLabel(tier)}: relevant fire (10+ detections) followed in ${formatShare(historical_share)} of past cases`,
    ),
    caveat: 'A frequency from the past, not a forecast.',
    limits: RISK_LIMITS,
  };
}
