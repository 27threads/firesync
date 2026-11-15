/** Shared geographic framing for the globe surface and the Leaflet handoff. */
export const SURFACE_VIEW = { latitude: -14, longitude: -52, zoom: 4, radius: 1.6, fov: 34 };
export const MAP_ARRIVAL_HOLD = 0.8;
export const MAP_WHEEL_SETTLE_MS = 900;
export const journeyTransitionDistance = (sectionHeight: number, viewportHeight: number) => Math.max(1, sectionHeight - viewportHeight * (1 + MAP_ARRIVAL_HOLD));
export const BLUE_MARBLE_TILES = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg';
/** Cancel map inertia and restore the exact globe destination while the map is hidden. */
export function restoreSurfaceView(map: { stop: () => unknown; setView: (center: [number, number], zoom: number, options: { animate: boolean }) => unknown }) {
  map.stop();
  map.setView([SURFACE_VIEW.latitude, SURFACE_VIEW.longitude], SURFACE_VIEW.zoom, { animate: false });
}
export const tilePosition = (latitude: number, longitude: number, zoom: number) => ({
  x: (longitude + 180) / 360 * 2 ** zoom,
  y: (1 - mercatorLatitude(latitude) / Math.PI) / 2 * 2 ** zoom,
});
export const smoothPhase = (value: number, start: number, end: number) => {
  const t = Math.max(0, Math.min(1, (value - start) / (end - start)));
  return t * t * (3 - 2 * t);
};
/** Freeze idle rotation during descent; the existing geographic morph aligns the map. */
export const advanceGlobeRotation = (angle: number, delta: number, progress: number, running: boolean) => running && progress < 0.02 ? angle + delta * 0.015 : angle;
export const mercatorLatitude = (latitude: number) => Math.log(Math.tan(Math.PI / 4 + latitude * Math.PI / 360));
export const surfaceCameraDistance = (height: number) => {
  const pixelsPerUnit = 256 * 2 ** SURFACE_VIEW.zoom / (2 * Math.PI * SURFACE_VIEW.radius);
  return height / (2 * Math.tan(SURFACE_VIEW.fov * Math.PI / 360) * pixelsPerUnit);
};