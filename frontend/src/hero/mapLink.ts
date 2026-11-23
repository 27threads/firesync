// Nome do lugar e link para uma área do mapa. Funções puras: a tela só desenha e copia.
import type { Place } from '../api/types';
import { place as coordinates, type HeroMode } from './heroMapModel';

/** "Altamira, PA": what people in the field call the area. Without a known place, its coordinates. */
export function placeName(place: Place | null | undefined, lat: number, lon: number): string {
  if (place?.municipality) return place.state ? `${place.municipality}, ${place.state}` : place.municipality;
  return `Area near ${coordinates(lat, lon)}`;
}

/** Indigenous lands first, then conservation units: the agencies in charge of each are different. */
export function protectedAreas(place: Place | null | undefined): string[] {
  if (!place) return [];
  return [...place.indigenous_lands.map((name) => `Indigenous land: ${name}`), ...place.conservation_units.map((name) => `Conservation unit: ${name}`)];
}

export interface AreaLink {
  lat: number;
  lon: number;
  mode: HeroMode;
}

/** Link that opens the map on this area and view: `?at=lat,lon&view=risk`. */
export function areaLink(pageUrl: string, center: [number, number], mode: HeroMode): string {
  const url = new URL(pageUrl);
  const [lon, lat] = center;
  return `${url.origin}${url.pathname}?at=${lat.toFixed(3)},${lon.toFixed(3)}&view=${mode}`;
}

export function parseAreaLink(search: string): AreaLink | null {
  const params = new URLSearchParams(search);
  const parts = (params.get('at') ?? '').split(',');
  if (parts.length !== 2 || parts.some((part) => part.trim() === '')) return null;
  const [lat, lon] = parts.map(Number) as [number, number];
  if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return null;
  return { lat, lon, mode: params.get('view') === 'risk' ? 'risk' : 'fire' };
}
