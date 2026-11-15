import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import '@geoman-io/leaflet-geoman-free';
import countryBoundariesUrl from '@/assets/geography/country-boundaries.geojson?url';
import type { Feature, FeatureCollection, Geometry } from 'geojson';
import { BLUE_MARBLE_TILES, MAP_WHEEL_SETTLE_MS, restoreSurfaceView, SURFACE_VIEW } from '@/lib/globe-transition';
import { LocateFixed, MapPin, Minus, Pentagon, Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { intensityClass, type DetectionFeature, type Level, type Intensity, type RecentData, type Viewport } from '@/lib/recent-data';

export type AreaSelection = { type: 'geojson'; geometry: unknown; name?: string } | { type: 'circle'; latitude: number; longitude: number; radius_km: number } | { type: 'region'; region_id: number };
export default function AreaMap({ onSelect, selection, immersive = false, active = true, resetForHandoff = false, onReady, initialCountry, recent, onViewport, onCell, focus, layer = 'risk', levels = ['critical','attention','normal'], intensities = ['high','medium','low'], basemap = 'blue', drawMode, operational = false, stateBounds }: { onSelect: (area: AreaSelection | null) => void; selection: AreaSelection | null; immersive?: boolean; active?: boolean; resetForHandoff?: boolean; onReady?: () => void; initialCountry?: string; recent?: RecentData | null; onViewport?: (view: Viewport) => void; onCell?: (cell: DetectionFeature) => void; focus?: { center: [number,number]; nonce: number } | undefined; layer?: string; levels?: Level[]; intensities?: Intensity[]; basemap?: string; drawMode?: string; operational?: boolean; stateBounds?: Viewport['bbox'] }) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const callback = useRef(onSelect); callback.current = onSelect;
  const readyCallback = useRef(onReady); readyCallback.current = onReady;
  const drawn = useRef<L.Layer[]>([]);
  const imageryRef = useRef<L.TileLayer | null>(null);
  const viewportCallback = useRef(onViewport); viewportCallback.current = onViewport;
  const cellCallback = useRef(onCell); cellCallback.current = onCell;
  const currentSelection = useRef(selection); currentSelection.current = selection;
  const initialHighlight = useRef(false);
  const [countries, setCountries] = useState<Feature<Geometry>[]>([]);
  const [countryError, setCountryError] = useState(false);
  const [drawing, setDrawing] = useState(false);
  const chooseCountry = (feature: Feature<Geometry>) => {
    mapRef.current?.pm.disableDraw();
    callback.current({ type: 'geojson', geometry: feature.geometry, name: String(feature.properties?.['name'] ?? 'Selected country') });
  };
  useEffect(() => {
    if (!container.current) return;
    const map = L.map(container.current, { zoomControl: false, scrollWheelZoom: immersive ? false : true, preferCanvas: true }).setView([SURFACE_VIEW.latitude, SURFACE_VIEW.longitude], immersive ? SURFACE_VIEW.zoom : 5);
    mapRef.current = map;
    const imagery = L.tileLayer(BLUE_MARBLE_TILES, { attribution: 'Imagery: <a href="https://earthdata.nasa.gov/gibs">NASA GIBS · Blue Marble</a>', maxNativeZoom: 8, maxZoom: 14 });
    imagery.once('load', () => readyCallback.current?.());
    imagery.addTo(map);
    imageryRef.current = imagery;
    const reportView = () => { const b = map.getBounds(); viewportCallback.current?.({ bbox: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()], zoom: map.getZoom() }); };
    map.on('moveend', reportView); reportView();
    if (!immersive) {
      L.control.zoom({ position: 'bottomright' }).addTo(map);
      map.pm.addControls({ position: 'topleft', drawMarker: false, drawCircleMarker: false, drawPolyline: false, drawCircle: false, drawText: false, editMode: false, dragMode: false, cutPolygon: false, removalMode: true, rotateMode: false });
    }
    map.on('pm:drawstart', () => setDrawing(true));
    map.on('pm:drawend', () => setDrawing(false));
    const tokens = getComputedStyle(document.documentElement);
    map.pm.setPathOptions({ color: tokens.getPropertyValue('--map-selection').trim(), fillColor: tokens.getPropertyValue('--map-selection').trim(), fillOpacity: 0.12, weight: 2 });
    map.on('pm:create', event => {
      if (!(event.layer instanceof L.Polygon) && !(event.layer instanceof L.Circle)) return;
      drawn.current.forEach(layer => map.removeLayer(layer)); drawn.current = [event.layer];
      map.pm.disableDraw();
      if (event.layer instanceof L.Circle) { const c=event.layer.getLatLng(); callback.current({ type:'circle',latitude:c.lat,longitude:c.lng,radius_km:event.layer.getRadius()/1000 }); }
      else callback.current({ type: 'geojson', geometry: event.layer.toGeoJSON().geometry });
    });
    map.on('pm:remove', () => { drawn.current = drawn.current.filter(layer => map.hasLayer(layer)); if (!drawn.current.length) callback.current(null); });
    const controller = new AbortController();
    if (immersive && !operational) void fetch(countryBoundariesUrl, { signal: controller.signal }).then(response => { if (!response.ok) throw new Error('Boundaries unavailable'); return response.json() as Promise<FeatureCollection>; }).then(data => {
      setCountries(data.features.slice().sort((a, b) => String(a.properties?.['name']).localeCompare(String(b.properties?.['name']))));
      L.geoJSON(data, { style: { color: tokens.getPropertyValue('--map-selection').trim(), weight: 0.7, fillOpacity: 0.015 }, onEachFeature: (feature, layer) => {
        layer.bindTooltip(String(feature.properties?.['name'] ?? ''), { sticky: true });
        layer.on('click', () => { if (!map.pm.globalDrawModeEnabled()) chooseCountry(feature); });
      } }).addTo(map);
      const initial = data.features.find(feature => feature.properties?.['name'] === initialCountry);
      if (initial && !currentSelection.current) {
        initialHighlight.current = true;
        chooseCountry(initial);
      }
    }).catch(error => { if (error.name !== 'AbortError') setCountryError(true); });
    return () => { controller.abort(); map.remove(); mapRef.current = null; drawn.current = []; };
  }, []);
  useEffect(() => {
    const map=mapRef.current; if(!map || !recent) return;
    const tokens=getComputedStyle(document.documentElement);
    const token=(name:string)=>tokens.getPropertyValue(name).trim();
    const visible=recent.features.filter(f => (!f.properties.alert_level || levels.includes(f.properties.alert_level)) && (f.geometry.type !== 'Point' || intensities.includes(intensityClass(f.properties.frp ?? 0, f.properties.saturated))));
    const marks=L.geoJSON({type:'FeatureCollection',features:visible} as FeatureCollection, {
      style: f => { const p=f?.properties; const severity=recent.alerts ? p?.alert_level ?? 'normal' : 'normal'; const ink=token(layer === 'risk' ? `--risk-${severity}` : layer==='intensity' ? '--intensity-high' : '--map-selection'); return {color:ink,fillColor:ink,weight:severity==='critical'?4:severity==='attention'?3:1,fillOpacity:layer==='count'?0.55:severity==='normal'?0.08:0.32,dashArray:severity==='attention'?'5 3':undefined}; },
      pointToLayer: (f,c) => { const k=intensityClass(f.properties.frp ?? 0,f.properties.saturated); return L.circleMarker(c,{radius:k==='high'?8:k==='medium'?5:3,color:token(`--intensity-${k}`),weight:k==='high'?3:1,fillOpacity:0.7}); },
      onEachFeature: (f,l) => { const p=f.properties; const text=layer==='count'?`${p.detections ?? '—'}`:p.alert_level==='critical'?'! Critical':p.alert_level==='attention'?'△ Attention':null; if(text && recent.alerts) l.bindTooltip(text,{permanent:true,direction:'center',className:'risk-map-label'}); l.on('click',()=>cellCallback.current?.(f as DetectionFeature)); }
    }).addTo(map);
    return ()=>{map.removeLayer(marks);};
  },[recent,layer,levels,intensities]);
  useEffect(()=>{if(focus) mapRef.current?.setView([focus.center[1],focus.center[0]],8,{animate:false});},[focus]);
  useEffect(() => {
    if (!stateBounds) return;
    const [west, south, east, north] = stateBounds;
    mapRef.current?.fitBounds([[south, west], [north, east]], { animate: false, padding: [30, 80] });
  }, [stateBounds]);
  useEffect(()=>{const map=mapRef.current;if(!map || !drawMode) return; map.pm.disableDraw(); if(drawMode!=='none') map.pm.enableDraw(drawMode as 'Polygon',{snappable:false,tooltips:false});},[drawMode]);
  useEffect(()=>{const imagery=imageryRef.current;if(!imagery)return;imagery.setOpacity(basemap==='plain'?0:1);if(basemap==='night') imagery.setUrl('https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_CityLights_2012/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg');else imagery.setUrl(BLUE_MARBLE_TILES);},[basemap]);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !immersive) return;
    map.scrollWheelZoom.disable();
    if (!active) { map.pm.disableDraw(); return; }
    map.invalidateSize({ animate: false });
    // Let the arrival gesture finish before wheel movement starts zooming the map.
    const timer = window.setTimeout(() => map.scrollWheelZoom.enable(), MAP_WHEEL_SETTLE_MS);
    return () => { window.clearTimeout(timer); map.scrollWheelZoom.disable(); };
  }, [active, immersive]);
  useEffect(() => {
    const map = mapRef.current;
    if (map && immersive && resetForHandoff) restoreSurfaceView(map);
  }, [immersive, resetForHandoff]);
  useEffect(() => {
    const map = mapRef.current; if (!map) return;
    if (!selection) { drawn.current.forEach(layer => map.removeLayer(layer)); drawn.current = []; map.setView([SURFACE_VIEW.latitude, SURFACE_VIEW.longitude], immersive ? SURFACE_VIEW.zoom : 5); return; }
    if (selection.type === 'geojson') {
      if (!selection.name) return;
      drawn.current.forEach(layer => map.removeLayer(layer));
      const feature: Feature<Geometry> = { type: 'Feature', properties: {}, geometry: selection.geometry as Geometry };
      const layer = L.geoJSON(feature, { style: { color: getComputedStyle(document.documentElement).getPropertyValue('--map-selection').trim(), weight: 2, fillOpacity: 0.12 } }).addTo(map);
      drawn.current = [layer];
      if (initialHighlight.current) { initialHighlight.current = false; return; }
      if (immersive && !active) return;
      map.fitBounds(layer.getBounds(), { paddingTopLeft: [60, 80], paddingBottomRight: [60, immersive ? 140 : 60], maxZoom: 6 });
      return;
    }
    if (selection.type !== 'circle') return;
    drawn.current.forEach(layer => map.removeLayer(layer));
    const color = getComputedStyle(document.documentElement).getPropertyValue('--map-selection').trim();
    const circle = L.circle([selection.latitude, selection.longitude], { radius: selection.radius_km * 1000, color, fillOpacity: 0.12, weight: 2 }).addTo(map);
    drawn.current = [circle];
    if (!immersive || active) map.fitBounds(circle.getBounds(), { padding: [30, 30], maxZoom: 11 });
  }, [selection]);
  const tools = [
    { label: drawing ? 'Cancel drawing' : 'Draw an area', icon: drawing ? X : Pentagon, pressed: drawing, disabled: false, run: () => {
      const map = mapRef.current;
      if (!map) return;
      if (drawing) map.pm.disableDraw();
      else map.pm.enableDraw('Polygon', { snappable: false, tooltips: false });
    } },
    { label: 'Clear selection', icon: X, disabled: !selection || drawing, run: () => callback.current(null) },
  ];
  return <div className={immersive ? 'mission-map' : 'area-map-wrap'}>
    <div ref={container} className="area-map" aria-label="Interactive area selection map" />
    {immersive && <TooltipProvider delayDuration={200}>
      {!operational && <div className="mission-country">
        <MapPin size={17} aria-hidden="true" />
        <select id="mission-country" aria-label="Select country" value={selection?.type === 'geojson' ? selection.name ?? '' : ''} disabled={!countries.length} onChange={event => { const country = countries.find(feature => feature.properties?.['name'] === event.target.value); if (country) chooseCountry(country); else callback.current(null); }}>
          <option value="">{countryError ? 'Boundaries unavailable' : countries.length ? selection ? 'Custom area' : 'Select a country' : 'Loading countries…'}</option>
          {countries.map(feature => <option key={String(feature.properties?.['name'])}>{String(feature.properties?.['name'])}</option>)}
        </select>
        <div className="mission-selection-tools">{tools.map(tool => <Tooltip key={tool.label}><TooltipTrigger asChild><Button variant="ghost" size="icon" aria-label={tool.label} aria-pressed={tool.pressed} disabled={tool.disabled} onClick={tool.run}><tool.icon size={17} /></Button></TooltipTrigger><TooltipContent className="mission-tooltip">{tool.label}</TooltipContent></Tooltip>)}</div>
      </div>}
      <div className="mission-navigation" role="toolbar" aria-label="Map navigation">
        {[{ label: 'Zoom in', icon: Plus, run: () => mapRef.current?.zoomIn(1, { animate: false }) }, { label: 'Zoom out', icon: Minus, run: () => mapRef.current?.zoomOut(1, { animate: false }) }, { label: 'Center on Brazil', icon: LocateFixed, run: () => { const map = mapRef.current; if (map) restoreSurfaceView(map); } }].map(tool => <Tooltip key={tool.label}><TooltipTrigger asChild><Button variant="ghost" size="icon" aria-label={tool.label} onClick={tool.run}><tool.icon size={17} /></Button></TooltipTrigger><TooltipContent side="left" className="mission-tooltip">{tool.label}</TooltipContent></Tooltip>)}
      </div>
    </TooltipProvider>}
  </div>;
}