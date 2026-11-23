// Divisas dos estados no mapa do hero (IBGE, arquivo gerado por `data-pipeline/lugares.py --estados`).
// Ajudam a ler o card ("Almeirim, PA") no próprio mapa. Funções puras: a tela só desenha.
import type { GeoJsonPolygon } from '../api/types';

export const STATES_URL = `${import.meta.env.BASE_URL}brazil-states.geojson`;

export interface StateFeature {
  type: 'Feature';
  properties: { state: string; label: [number, number] }; // label = [lon, lat], dentro do estado
  geometry: GeoJsonPolygon | { type: 'MultiPolygon'; coordinates: number[][][][] };
}

export interface StatesCollection {
  type: 'FeatureCollection';
  features: StateFeature[];
}

/** Thin white line above the hexagons, without fill: the risk colours stay readable underneath. */
export const STATE_BORDER_STYLE = { color: '#ffffff', weight: 1.2, opacity: 0.7, fill: false } as const;

/** In the whole-Brazil view the 27 abbreviations crowd the map; they appear once the map is closer. */
export const STATE_LABEL_MIN_ZOOM = 5;
export const stateLabelsVisible = (zoom: number): boolean => zoom >= STATE_LABEL_MIN_ZOOM;

export function stateLabels(states: StatesCollection): { state: string; latlng: [number, number] }[] {
  return states.features.map(({ properties: { state, label } }) => ({ state, latlng: [label[1], label[0]] }));
}
