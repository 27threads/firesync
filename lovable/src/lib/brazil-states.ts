import { inView, type Priority, type Viewport } from './recent-data';

export const BRAZIL_STATES = [
  'Acre', 'Alagoas', 'Amapá', 'Amazonas', 'Bahia', 'Ceará', 'Distrito Federal',
  'Espírito Santo', 'Goiás', 'Maranhão', 'Mato Grosso', 'Mato Grosso do Sul',
  'Minas Gerais', 'Pará', 'Paraíba', 'Paraná', 'Pernambuco', 'Piauí',
  'Rio de Janeiro', 'Rio Grande do Norte', 'Rio Grande do Sul', 'Rondônia',
  'Roraima', 'Santa Catarina', 'São Paulo', 'Sergipe', 'Tocantins',
] as const;
export type BrazilState = typeof BRAZIL_STATES[number];
// TODO(confirm): supply state bounding boxes derived from official IBGE boundaries.
// The IBGE boundary service could not be reached; do not substitute guessed coordinates.
export const STATE_BOUNDS: Partial<Record<BrazilState, Viewport['bbox']>> = {};
export function priorityInState(cells: Priority[], state: BrazilState | '') {
  if (!state) return cells;
  const bounds = STATE_BOUNDS[state];
  return bounds ? cells.filter(cell => inView(cell.center, bounds)) : [];
}