// Geometria da abertura com o globo (portada do protótipo em lovable/). Funções puras: a cena só desenha.

/** Enquadramento final da descida: o Brasil no centro, no zoom 4 dos tiles do NASA GIBS. */
export const SURFACE_VIEW = { latitude: -14, longitude: -52, zoom: 4, radius: 1.6, fov: 34 };

/** Abaixo desta largura (celular e tablet em pé) o texto fica em cima e o globo embaixo. */
export const STACKED_OPENING_MAX_WIDTH = 959;

export type OpeningLayout = 'stacked' | 'side';

export const openingLayout = (width: number): OpeningLayout => (width <= STACKED_OPENING_MAX_WIDTH ? 'stacked' : 'side');

export const BLUE_MARBLE_TILES =
  'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg';

export const mercatorLatitude = (latitude: number) => Math.log(Math.tan(Math.PI / 4 + (latitude * Math.PI) / 360));

export const tilePosition = (latitude: number, longitude: number, zoom: number) => ({
  x: ((longitude + 180) / 360) * 2 ** zoom,
  y: ((1 - mercatorLatitude(latitude) / Math.PI) / 2) * 2 ** zoom,
});

export function smoothPhase(value: number, start: number, end: number): number {
  const t = Math.max(0, Math.min(1, (value - start) / (end - start)));
  return t * t * (3 - 2 * t);
}

/** Quanto da abertura já passou: 0 com o topo da seção no topo da janela, 1 quando a parte fixa termina. */
export function journeyProgress(sectionTop: number, sectionHeight: number, viewportHeight: number): number {
  const distance = Math.max(1, sectionHeight - viewportHeight);
  return Math.max(0, Math.min(1, -sectionTop / distance));
}

export function chapterAt(progress: number): number {
  if (progress < 0.25) return 0;
  return progress < 0.6 ? 1 : 2;
}

/** O globo gira parado; na descida a rotação congela e a superfície se alinha ao mapa. */
export const advanceGlobeRotation = (angle: number, delta: number, progress: number, running: boolean) =>
  running && progress < 0.02 ? angle + delta * 0.015 : angle;

export function surfaceCameraDistance(height: number): number {
  const pixelsPerUnit = (256 * 2 ** SURFACE_VIEW.zoom) / (2 * Math.PI * SURFACE_VIEW.radius);
  return height / (2 * Math.tan((SURFACE_VIEW.fov * Math.PI) / 360) * pixelsPerUnit);
}

// Lambert diffuse in Three.js lights a texture at albedo x intensity / pi.
export const litDiffuseGain = ({ ambient, sun }: { ambient: number; sun: number }) => (ambient + sun) / Math.PI;

export const SPACECRAFT_LIGHT = { ambient: 0.8, sun: 2.3 };
