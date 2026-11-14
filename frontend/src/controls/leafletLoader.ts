import type * as LeafletNs from 'leaflet';

export type LeafletModule = typeof LeafletNs;

let loaderPromise: Promise<LeafletModule> | null = null;

/** Dynamically loads Leaflet, its CSS, and Leaflet-Geoman on demand (never on initial paint). */
export function loadLeafletWithGeoman(): Promise<LeafletModule> {
  if (!loaderPromise) {
    loaderPromise = (async () => {
      await import('leaflet/dist/leaflet.css');
      await import('@geoman-io/leaflet-geoman-free/dist/leaflet-geoman.css');
      const mod = await import('leaflet');
      const L = ((mod as { default?: LeafletModule }).default ?? mod) as LeafletModule;
      // Leaflet-Geoman attaches to global L when imported as a plugin.
      (globalThis as { L?: LeafletModule }).L = L;
      await import('@geoman-io/leaflet-geoman-free');
      return L;
    })();
  }
  return loaderPromise;
}
