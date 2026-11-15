import { useEffect, useRef } from 'react';
import L from 'leaflet';
import { VectorTile } from '@mapbox/vector-tile';
import { PbfReader } from 'pbf';

export default function HistoryMap({ year, onStatus }: { year: number; onStatus: (status: string) => void }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const callback = useRef(onStatus); callback.current = onStatus;
  useEffect(() => {
    if (!container.current) return;
    const map = L.map(container.current, { zoomControl: false, scrollWheelZoom: false, attributionControl: true }).setView([-12, -54], 4);
    mapRef.current = map;
    L.tileLayer('https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg', { attribution: 'NASA GIBS · Blue Marble', maxNativeZoom: 8, maxZoom: 8 }).addTo(map);
    L.control.zoom({ position: 'topright' }).addTo(map);
    const observer = new ResizeObserver(() => map.invalidateSize()); observer.observe(container.current);
    return () => { observer.disconnect(); map.remove(); mapRef.current = null; };
  }, []);
  useEffect(() => {
    const map = mapRef.current; if (!map) return;
    let cancelled = false;
    const abort = new AbortController();
    callback.current('Loading NASA observations…');
    const source = year < 2012 ? 'MODIS_Combined_Thermal_Anomalies_All' : 'VIIRS_SNPP_Thermal_Anomalies_375m_All';
    const matrix = year < 2012 ? 'GoogleMapsCompatible_Level7' : 'GoogleMapsCompatible_Level8';
    const date = `${year}-09-15`;
    const color = getComputedStyle(document.documentElement).getPropertyValue('--mission-red').trim();
    let loaded = false;
    class ThermalTiles extends L.GridLayer {
      override createTile(coords: L.Coords, done: L.DoneCallback) {
        const canvas = document.createElement('canvas'); canvas.width = 256; canvas.height = 256;
        const url = `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${source}/default/${date}/${matrix}/${coords.z}/${coords.y}/${coords.x}.mvt`;
        fetch(url, { signal: abort.signal }).then(async response => {
          if (!response.ok) throw new Error('NASA tiles unavailable');
          const tile = new VectorTile(new PbfReader(new Uint8Array(await response.arrayBuffer())));
          const context = canvas.getContext('2d'); if (!context || cancelled) return;
          context.fillStyle = color;
          for (const layer of Object.values(tile.layers)) {
            for (let index = 0; index < layer.length; index++) {
              const feature = layer.feature(index);
              if (feature.type !== 1) continue;
              for (const ring of feature.loadGeometry()) for (const point of ring) {
                context.beginPath(); context.arc(point.x / layer.extent * 256, point.y / layer.extent * 256, 2.4, 0, Math.PI * 2); context.fill();
              }
            }
          }
          loaded = true; callback.current('NASA observations · Daily snapshot');
          done(undefined, canvas);
        }).catch(() => { if (!cancelled) { if (!loaded) callback.current('NASA layer unavailable · Basemap only'); done(undefined, canvas); } });
        return canvas;
      }
    }
    const layer = new ThermalTiles({ maxNativeZoom: 7, maxZoom: 8, attribution: 'Thermal anomalies: NASA FIRMS / GIBS', keepBuffer: 1 }).addTo(map);
    return () => { cancelled = true; abort.abort(); map.removeLayer(layer); };
  }, [year]);
  return <div ref={container} className="history-map" aria-label={`Interactive NASA thermal anomaly map for September 15, ${year}`} />;
}