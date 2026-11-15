import { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import '@geoman-io/leaflet-geoman-free';
import countryBoundariesUrl from '@/assets/geography/country-boundaries.geojson?url';
import type { Feature, FeatureCollection, Geometry } from 'geojson';
import { BLUE_MARBLE_TILES, MAP_WHEEL_SETTLE_MS, restoreSurfaceView, SURFACE_VIEW } from '@/lib/globe-transition';
import { LocateFixed, MapPin, Minus, Pentagon, Plus, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { intensityClass, countColor, TIER_COLOR, TIER_LABEL, type RiskTier, type DetectionFeature, type Level, type Intensity, type RecentData, type Viewport } from '@/lib/recent-data';

export type AreaSelection = { type: 'geojson'; geometry: unknown; name?: string } | { type: 'circle'; latitude: number; longitude: number; radius_km: number } | { type: 'region'; region_id: number };
// Camada de cor translúcida: deixa o relevo e a vegetação do mapa aparecerem por baixo.
const HEX_FILL_OPACITY = 0.55;
export default function AreaMap({ onSelect, selection, immersive = false, active = true, resetForHandoff = false, onReady, initialCountry, recent, onViewport, onCell, focus, layer = 'risk', levels = ['critical','attention','normal'], intensities = ['high','medium','low'], basemap = 'blue', drawMode, operational = false, stateBounds, tiers = ['very_high','high','medium','lower'], quietOnly = false, onMinZoomOut }: { onMinZoomOut?: () => void; tiers?: RiskTier[]; quietOnly?: boolean; onSelect: (area: AreaSelection | null) => void; selection: AreaSelection | null; immersive?: boolean; active?: boolean; resetForHandoff?: boolean; onReady?: () => void; initialCountry?: string; recent?: RecentData | null; onViewport?: (view: Viewport) => void; onCell?: (cell: DetectionFeature) => void; focus?: { center: [number,number]; nonce: number } | undefined; layer?: string; levels?: Level[]; intensities?: Intensity[]; basemap?: string; drawMode?: string; operational?: boolean; stateBounds?: Viewport['bbox'] }) {
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
    const map = L.map(container.current, { zoomControl: false, scrollWheelZoom: immersive ? false : true, preferCanvas: true, ...(immersive ? { minZoom: SURFACE_VIEW.zoom, zoomSnap: 0, zoomDelta: 1 } : {}) }).setView([SURFACE_VIEW.latitude, SURFACE_VIEW.longitude], immersive ? SURFACE_VIEW.zoom : 5);
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
    const isCell=(f:DetectionFeature)=>f.geometry.type!=='Point';
    const visible=recent.features.filter(f => {
      const p=f.properties;
      if (f.geometry.type==='Point') return intensities.includes(intensityClass(p.frp ?? 0, p.saturated));
      if (layer==='risk') return (!p.risk_tier || tiers.includes(p.risk_tier)) && (!quietOnly || !(p.detections && p.detections>0));
      const any=((p.n_low??0)>0&&intensities.includes('low'))||((p.n_medium??0)>0&&intensities.includes('medium'))||((p.n_high??0)>0&&intensities.includes('high'))||(p.n_low==null&&p.n_medium==null&&p.n_high==null);
      return any && (!p.alert_level || levels.includes(p.alert_level));
    });
    const styleOf=(f?:{properties?:DetectionFeature['properties']}|undefined) => {
        const p=f?.properties; const severity=recent.alerts ? p?.alert_level ?? 'normal' : 'normal';
        const near=map.getZoom()>=6; if (layer==='risk' && p?.risk_tier) { const ink=TIER_COLOR[p.risk_tier as RiskTier]; const fire=(p.detections??0)>0; return {color:fire&&near?'#ffffff':ink,fillColor:ink,weight:fire&&near?2.5:near?1:0.4,fillOpacity:HEX_FILL_OPACITY}; }
        if (layer==='intensity') { return {color:near?'#ffffff':countColor(p?.detections??0),fillColor:countColor(p?.detections??0),weight:near?1:0.4,fillOpacity:HEX_FILL_OPACITY}; }
        const ink=token(layer === 'risk' ? `--risk-${severity}` : '--map-selection'); return {color:ink,fillColor:ink,weight:severity==='critical'?4:severity==='attention'?3:1,fillOpacity:severity==='normal'?0.08:0.32,dashArray:severity==='attention'?'5 3':undefined};
    };
    const marks=L.geoJSON({type:'FeatureCollection',features:visible} as FeatureCollection, {
      style: f => styleOf(f as never),
      pointToLayer: (f,c) => { const k=intensityClass(f.properties.frp ?? 0,f.properties.saturated); return L.circleMarker(c,{radius:k==='high'?8:k==='medium'?5:3,color:token(`--intensity-${k}`),weight:k==='high'?3:1,fillOpacity:0.7}); },
      onEachFeature: (f,l) => { const p=f.properties; const text=layer==='risk'&&p.risk_tier? (p.risk_tier==='very_high'||p.risk_tier==='high'?TIER_LABEL[p.risk_tier as RiskTier]:null) : layer==='intensity'&&p.alert_level==='critical'?'! Critical':layer==='intensity'&&p.alert_level==='attention'?'△ Attention':null; if(text && recent.alerts) l.bindTooltip(text,{sticky:true,direction:'top',className:'risk-map-label'}); l.on('click',()=>cellCallback.current?.(f as DetectionFeature)); }
    }).addTo(map);
    void isCell;
    const rings=L.layerGroup().addTo(map);
    const drawRings=()=>{
      rings.clearLayers();
      if (layer!=='intensity') return;
      for (const f of visible) {
        if (f.geometry.type!=='Polygon') continue;
        const ring=(f.geometry.coordinates[0]??[]) as number[][];
        if (ring.length<3) continue;
        const lng=ring.reduce((a,c)=>a+(c[0]??0),0)/ring.length, lat=ring.reduce((a,c)=>a+(c[1]??0),0)/ring.length;
        // Ícone só quando o hexágono já tem tamanho para abrigá-lo: sem poluir o zoom nacional.
        const c0=map.latLngToContainerPoint([lat,lng]), v0=map.latLngToContainerPoint([ring[0]![1]!,ring[0]![0]!]);
        const hexR=Math.hypot(c0.x-v0.x,c0.y-v0.y);
        const lv=f.properties.alert_level;
        if (recent.alerts && (lv==='critical'||lv==='attention') && hexR>=8) {
          const size=Math.round(Math.max(14,Math.min(24,hexR*0.9)));
          L.marker([lat,lng],{icon:L.divIcon({className:`fs-map-icon fs-map-icon-${lv}`,html:'<span>!</span>',iconSize:[size,size],iconAnchor:[size/2,size/2]}),interactive:false,keyboard:false}).addTo(rings);
        }
      }
    };
    drawRings();
    const restyle=()=>marks.setStyle(styleOf);
    let settle = 0;
    const settled = () => { window.clearTimeout(settle); settle = window.setTimeout(() => { drawRings(); restyle(); }, 140); };
    map.on('zoomend', settled);
    return ()=>{window.clearTimeout(settle);map.off('zoomend',settled);map.removeLayer(marks);map.removeLayer(rings);};
  },[recent,layer,levels,intensities,tiers,quietOnly]);
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
    // Mesma direção da abertura: rolar para baixo aproxima, para cima afasta. No enquadramento inicial,
    // rolar para cima deixa a página subir de volta ao globo (não bloqueia o scroll da página).
    const el = map.getContainer();
    let target = map.getZoom();
    let anchor = map.getSize().divideBy(2);
    let raf = 0;
    const step = () => {
      raf = 0;
      const z = map.getZoom();
      const diff = target - z;
      if (Math.abs(diff) < 0.01) { map.setZoomAround(anchor, target, { animate: false }); return; }
      map.setZoomAround(anchor, z + diff * 0.28, { animate: false });
      raf = requestAnimationFrame(step);
    };
    const onWheel = (e: WheelEvent) => {
      const down = e.deltaY > 0;
      if (!down && map.getZoom() <= SURFACE_VIEW.zoom + 0.001) return;
      e.preventDefault();
      const unit = e.deltaMode === 1 ? 33 : 120;
      if (!raf) target = map.getZoom();
      target = Math.max(SURFACE_VIEW.zoom, Math.min(map.getMaxZoom(), target + Math.max(-1, Math.min(1, e.deltaY / unit)) * 0.6));
      anchor = map.mouseEventToContainerPoint(e);
      if (!raf) raf = requestAnimationFrame(step);
    };
    const timer = window.setTimeout(() => el.addEventListener('wheel', onWheel, { passive: false }), MAP_WHEEL_SETTLE_MS);
    return () => { window.clearTimeout(timer); if (raf) cancelAnimationFrame(raf); el.removeEventListener('wheel', onWheel); };
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
        {[{ label: 'Zoom in', icon: Plus, run: () => mapRef.current?.zoomIn(1, { animate: false }) }, { label: 'Zoom out', icon: Minus, run: () => { const map = mapRef.current; if (!map) return; if (immersive && map.getZoom() <= SURFACE_VIEW.zoom) onMinZoomOut?.(); else map.zoomOut(1, { animate: false }); } }, { label: 'Center on Brazil', icon: LocateFixed, run: () => { const map = mapRef.current; if (map) restoreSurfaceView(map); } }].map(tool => <Tooltip key={tool.label}><TooltipTrigger asChild><Button variant="ghost" size="icon" aria-label={tool.label} onClick={tool.run}><tool.icon size={17} /></Button></TooltipTrigger><TooltipContent side="left" className="mission-tooltip">{tool.label}</TooltipContent></Tooltip>)}
      </div>
    </TooltipProvider>}
  </div>;
}