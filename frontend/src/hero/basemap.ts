// Imagem de fundo do mapa do hero. Duas opções do NASA GIBS: a vista limpa (Blue Marble, a mesma em que o globo pousa),
// que é a padrão, e a imagem real do último dia completo (VIIRS cor verdadeira), com a fumaça e as nuvens daquele dia.
import { BLUE_MARBLE_TILES } from './globeTransition';

export type BasemapId = 'clear' | 'latest';

const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best';

/** Day before in UTC: GIBS fills today's image as the satellite passes, so today is still partly empty. */
export function latestImageDate(now: Date): string {
  return new Date(now.getTime() - 86_400_000).toISOString().slice(0, 10);
}

export const viirsTrueColorTiles = (date: string): string =>
  `${GIBS}/VIIRS_NOAA20_CorrectedReflectance_TrueColor/default/${date}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`;

export function latestImageLabel(date: string): string {
  const day = new Date(`${date}T00:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  return `Satellite image of ${day} (NASA VIIRS, NOAA-20)`;
}

export const BASEMAPS = {
  clear: { url: BLUE_MARBLE_TILES, maxNativeZoom: 8, attribution: 'Blue Marble' },
  latest: { url: viirsTrueColorTiles('{date}'), maxNativeZoom: 9, attribution: 'VIIRS NOAA-20 true color' },
} as const;

/** The map opens on the clear view, the image the globe lands on; "Latest image" shows the real last full day. */
export const DEFAULT_BASEMAP: BasemapId = 'clear';
