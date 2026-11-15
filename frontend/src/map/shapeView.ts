import type { MapShape } from '../state/useExplorer';

export interface ShapeView {
  bbox: [number, number, number, number]; // oeste, sul, leste, norte
  zoom: number;
}

const KM_PER_DEGREE = 111.32;

// Enquadramento de uma seleção sem depender do Leaflet: serve para pedir os focos recentes
// da área escolhida mesmo antes de o mapa carregar.
export function shapeView(shape: MapShape): ShapeView {
  let bbox: [number, number, number, number];
  if (shape.kind === 'bbox') {
    bbox = shape.bbox;
  } else if (shape.kind === 'point') {
    const { lat, lon, radius_km } = shape.point;
    const dLat = radius_km / KM_PER_DEGREE;
    const dLon = radius_km / (KM_PER_DEGREE * Math.max(0.01, Math.cos((lat * Math.PI) / 180)));
    bbox = [lon - dLon, lat - dLat, lon + dLon, lat + dLat];
  } else {
    const ring = shape.geometry.coordinates[0] ?? [];
    const lons = ring.map(([lon]) => lon);
    const lats = ring.map(([, lat]) => lat);
    bbox = [Math.min(...lons), Math.min(...lats), Math.max(...lons), Math.max(...lats)];
  }
  const span = Math.max(bbox[2] - bbox[0], bbox[3] - bbox[1], 0.01);
  const zoom = Math.max(2, Math.min(12, Math.round(Math.log2(360 / span))));
  return { bbox, zoom };
}
