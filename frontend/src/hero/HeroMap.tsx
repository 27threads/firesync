import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { LayerGroup, Map as LeafletMap } from 'leaflet';
import { fetchRecentDetections, fetchRegions } from '../api/client';
import type { GeoJsonPolygon, PriorityCell, RecentDetectionsResponse, RegionOption } from '../api/types';
import { loadLeafletWithGeoman } from '../controls/leafletLoader';
import { BLUE_MARBLE_TILES, SURFACE_VIEW } from './globeTransition';
import {
  COUNT_GRADIENT,
  DEFAULT_FILTERS,
  HEX_FILL_OPACITY,
  hexQueryZoom,
  INTENSITIES,
  LEVELS,
  MIN_ICON_HEX_RADIUS,
  TIERS,
  TIER_COLOR,
  TIER_LABEL,
  type HeroFilters,
  type HeroMode,
  agoLabel,
  announceArea,
  brasiliaLabel,
  countColor,
  filterCount,
  groupByTier,
  hexSummary,
  hexVisible,
  iconSize,
  levelName,
  pointSummary,
  priorityVisible,
  staleness,
  tierStartsOpen,
  type MapSummary,
} from './heroMapModel';
import './heroMap.css';

interface Props {
  /** O mapa só reage a toque e roda quando a descida do globo terminou. */
  active: boolean;
  /** Voltar ao globo (zoom mínimo atingido ou botão do globo). */
  onReturn: () => void;
  /** Descer para o explorador. */
  onNext: () => void;
}

interface View {
  bbox: [number, number, number, number];
  zoom: number;
}

const PAGE = 10;
const cap = (text: string) => text[0]!.toUpperCase() + text.slice(1);
const fmt = (n: number) => new Intl.NumberFormat('en-US').format(n);
const escape = (text: string) => text.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
/** Popup text for a click on the map. Every value is escaped before it becomes HTML. */
const popupHtml = ({ title, lines }: MapSummary) =>
  `<div class="hm-pop"><strong>${escape(title)}</strong>${lines.map((line) => `<span>${escape(line)}</span>`).join('')}</div>`;

export default function HeroMap({ active, onReturn, onNext }: Props) {
  const mapNode = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LeafletMap | null>(null);
  const leafletRef = useRef<typeof import('leaflet') | null>(null);
  const hexLayer = useRef<LayerGroup | null>(null);
  const shapeLayer = useRef<LayerGroup | null>(null);
  const [ready, setReady] = useState(false);
  const [view, setView] = useState<View | null>(null);
  const [zoomTick, setZoomTick] = useState(0);

  const [mode, setMode] = useState<HeroMode>('fire');
  const [filters, setFilters] = useState<HeroFilters>(DEFAULT_FILTERS);
  const [filtersOpen, setFiltersOpen] = useState(() => window.innerWidth >= 900);
  const [legendOpen, setLegendOpen] = useState(() => window.innerHeight >= 760);
  const [panelOpen, setPanelOpen] = useState(false);
  const [shown, setShown] = useState(PAGE);
  const [groupOpen, setGroupOpen] = useState<Record<string, boolean>>({});
  const [groupShown, setGroupShown] = useState<Record<string, number>>({});

  const [data, setData] = useState<RecentDetectionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [reload, setReload] = useState(0);
  const [clock, setClock] = useState(() => Date.now());

  const [regions, setRegions] = useState<RegionOption[]>([]);
  const [regionId, setRegionId] = useState('');
  const [areaPanel, setAreaPanel] = useState<'none' | 'draw' | 'coords'>('none');
  const [drawing, setDrawing] = useState('');
  const [hasShape, setHasShape] = useState(false);
  const [coords, setCoords] = useState({ lat: '-3.1', lon: '-60.2', radius: '50' });
  // Name of the area just sent to the calendar below, for the "See its calendar" hint.
  const [announced, setAnnounced] = useState('');
  const rootRef = useRef<HTMLDivElement>(null);
  const footRef = useRef<HTMLElement>(null);

  // The footer grows to two or three lines (Risk tab, narrow screens): the controls above it follow its height.
  // On the phone the toolbar wraps and the legend opens and closes: the panels below and the buttons above them follow too.
  useEffect(() => {
    const foot = footRef.current;
    const root = rootRef.current;
    const toolbar = root?.querySelector<HTMLElement>('.hm-toolbar');
    const legend = root?.querySelector<HTMLElement>('.hm-legend');
    if (!foot || !root || !toolbar || !legend || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      root.style.setProperty('--hm-foot', `${foot.offsetHeight}px`);
      root.style.setProperty('--hm-top', `${toolbar.offsetTop + toolbar.offsetHeight}px`);
      root.style.setProperty('--hm-legend', `${legend.offsetHeight}px`);
    });
    [foot, toolbar, legend].forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  // Relógio do "Data updated X h ago".
  useEffect(() => {
    const timer = setInterval(() => setClock(Date.now()), 60_000);
    return () => clearInterval(timer);
  }, []);

  // Regiões da API (as mesmas do seletor do explorador).
  useEffect(() => {
    const controller = new AbortController();
    fetchRegions(controller.signal).then(setRegions).catch(() => undefined);
    return () => controller.abort();
  }, []);

  // Cria o mapa uma vez, no enquadramento em que a descida do globo termina.
  useEffect(() => {
    let cancelled = false;
    let map: LeafletMap | null = null;
    void loadLeafletWithGeoman().then((L) => {
      const node = mapNode.current;
      if (cancelled || !node) return;
      leafletRef.current = L;
      map = L.map(node, { zoomControl: false, scrollWheelZoom: false, fadeAnimation: false, zoomSnap: 0, minZoom: SURFACE_VIEW.zoom, preferCanvas: true }).setView(
        [SURFACE_VIEW.latitude, SURFACE_VIEW.longitude],
        SURFACE_VIEW.zoom,
        { animate: false },
      );
      L.tileLayer(BLUE_MARBLE_TILES, {
        attribution: 'Imagery: <a href="https://earthdata.nasa.gov/gibs" rel="noopener">NASA GIBS</a> · Blue Marble',
        maxNativeZoom: 8,
        maxZoom: 14,
      }).addTo(map);
      hexLayer.current = L.layerGroup().addTo(map);
      shapeLayer.current = L.layerGroup().addTo(map);
      const publish = () => {
        if (!map) return;
        const b = map.getBounds();
        setView({ bbox: [b.getWest(), b.getSouth(), b.getEast(), b.getNorth()], zoom: map.getZoom() });
      };
      let settle = 0;
      map.on('moveend', publish);
      map.on('zoomend', () => {
        window.clearTimeout(settle);
        settle = window.setTimeout(() => setZoomTick((t) => t + 1), 140);
      });
      map.on('pm:create', (event) => {
        const layer = (event as unknown as { layer: import('leaflet').Layer }).layer;
        shapeLayer.current?.clearLayers();
        shapeLayer.current?.addLayer(layer);
        setHasShape(true);
        setDrawing('');
        const geometry = (layer as unknown as { toGeoJSON: () => { geometry: GeoJsonPolygon } }).toGeoJSON().geometry;
        if (geometry.type === 'Polygon') {
          announceArea({ type: 'geojson', geometry });
          setAnnounced('Your drawn area');
        }
      });
      mapRef.current = map;
      publish();
      setReady(true);
    });
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
  }, []);

  // O mapa tem o tamanho certo só depois que a descida termina.
  useEffect(() => {
    if (active) mapRef.current?.invalidateSize({ animate: false });
  }, [active, ready]);

  // Roda do mouse: rolar para baixo aproxima (como na descida do globo) e, no enquadramento inicial,
  // rolar para cima deixa a página subir de volta ao planeta.
  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !active || !map) return;
    const el = map.getContainer();
    let target = map.getZoom();
    let anchor = map.getSize().divideBy(2);
    let raf = 0;
    const step = () => {
      raf = 0;
      const z = map.getZoom();
      const diff = target - z;
      if (Math.abs(diff) < 0.01) {
        map.setZoomAround(anchor, target, { animate: false });
        return;
      }
      map.setZoomAround(anchor, z + diff * 0.28, { animate: false });
      raf = requestAnimationFrame(step);
    };
    // The wheel over the map only zooms, never scrolls the page (review on 15/11: zooming out sent people back up).
    // The buttons "Back to the globe" and "See the fire calendar" are the ways out.
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const unit = e.deltaMode === 1 ? 33 : 120;
      if (!raf) target = map.getZoom();
      target = Math.max(SURFACE_VIEW.zoom, Math.min(map.getMaxZoom(), target + Math.max(-1, Math.min(1, e.deltaY / unit)) * 0.6));
      anchor = map.mouseEventToContainerPoint(e);
      if (!raf) raf = requestAnimationFrame(step);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => {
      if (raf) cancelAnimationFrame(raf);
      el.removeEventListener('wheel', onWheel);
    };
  }, [ready, active]);

  // Busca os dados da área visível. Os dados anteriores ficam na tela enquanto os novos chegam.
  useEffect(() => {
    if (!active || !view) return;
    const controller = new AbortController();
    setLoading(true);
    setError('');
    const timer = window.setTimeout(() => {
      // Always hexagons: the points of a close zoom were hard to read (review on 15/11); the click summary explains a cell.
      fetchRecentDetections({ bbox: view.bbox, zoom: hexQueryZoom(view.zoom), hours: 24, mode: 'hexagons' }, controller.signal)
        .then((response) => {
          if (!controller.signal.aborted) setData(response);
        })
        .catch((e: unknown) => {
          if (controller.signal.aborted) return;
          setError(e instanceof Error ? e.message : 'The recent hot spots are unavailable.');
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 400);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [view, active, reload]);

  const alerts = data?.alerts;
  const priorities = useMemo(
    () => (alerts?.priority ?? []).filter((cell) => priorityVisible(cell, mode, filters)),
    [alerts, mode, filters],
  );
  useEffect(() => {
    setShown(PAGE);
    setGroupShown({});
  }, [mode, filters, view]);

  // Desenha os hexágonos (ou os pontos, com o zoom muito perto) e os ícones de alerta.
  useEffect(() => {
    const L = leafletRef.current;
    const map = mapRef.current;
    const layer = hexLayer.current;
    if (!L || !map || !layer) return;
    layer.clearLayers();
    if (!data) return;
    const near = map.getZoom() >= 6;
    // The popup pans clear of the toolbar and the status on top of the map (on the phone they hid it); at most half the map.
    const root = rootRef.current;
    const topControls = root ? [...root.querySelectorAll<HTMLElement>('.hm-toolbar, .hm-right')].map((el) => el.offsetTop + el.offsetHeight) : [];
    const topPad = Math.min(Math.max(0, ...topControls) + 8, map.getSize().y / 2);
    const popup = (maxWidth: number) => ({ className: 'hm-popup', maxWidth, autoPanPaddingTopLeft: [12, topPad] as [number, number] });
    if (data.mode === 'points') {
      for (const f of data.features) {
        const [lng, lat] = f.geometry.coordinates;
        const k = f.properties.intensity;
        L.circleMarker([lat, lng], { radius: k === 'high' ? 9 : k === 'medium' ? 7 : 5, color: '#ffffff', weight: 2, fillColor: countColor(k === 'high' ? 100 : k === 'medium' ? 10 : 1), fillOpacity: 0.95 })
          .bindPopup(popupHtml(pointSummary(f.properties, lat, lng)), popup(280))
          .addTo(layer);
      }
      return;
    }
    const shares = Object.fromEntries((data.alerts?.risk?.tiers ?? []).map((t) => [t.tier, t.historical_share]));
    for (const f of data.features) {
      const p = f.properties;
      if (!hexVisible(p, mode, filters)) continue;
      const ring = f.geometry.coordinates[0] ?? [];
      if (ring.length < 3) continue;
      const risk = mode === 'risk' && p.risk_tier;
      const fill = risk ? TIER_COLOR[p.risk_tier!] : countColor(p.detections);
      const fire = p.detections > 0;
      const latlngs = ring.map(([lng, lat]) => [lat!, lng!] as [number, number]);
      const centreLat = ring.reduce((sum, c) => sum + (c[1] ?? 0), 0) / ring.length;
      const centreLng = ring.reduce((sum, c) => sum + (c[0] ?? 0), 0) / ring.length;
      // Far away the cells are tiny: an outline in their own colour makes them bigger and keeps the colour readable.
      // Close up a white outline separates neighbours on the dark satellite image.
      L.polygon(latlngs, {
        color: near ? '#ffffff' : fill,
        fillColor: fill,
        weight: risk && fire && near ? 2.5 : near ? 1.2 : 2.5,
        fillOpacity: HEX_FILL_OPACITY,
      })
        .bindPopup(popupHtml(hexSummary(p, centreLat, centreLng, data.hours, shares)), popup(300))
        .addTo(layer);
      // Ícone de alerta: só quando o hexágono já comporta o símbolo.
      const level = p.alert_level;
      if (mode === 'fire' && (level === 'critical' || level === 'attention')) {
        const lat = ring.reduce((sum, c) => sum + (c[1] ?? 0), 0) / ring.length;
        const lng = ring.reduce((sum, c) => sum + (c[0] ?? 0), 0) / ring.length;
        const centre = map.latLngToContainerPoint([lat, lng]);
        const vertex = map.latLngToContainerPoint(latlngs[0]!);
        const radius = Math.hypot(centre.x - vertex.x, centre.y - vertex.y);
        if (radius >= MIN_ICON_HEX_RADIUS) {
          const size = iconSize(radius);
          L.marker([lat, lng], {
            icon: L.divIcon({ className: `hm-map-icon hm-map-icon--${level}`, html: '<span>!</span>', iconSize: [size, size], iconAnchor: [size / 2, size / 2] }),
            interactive: false,
            keyboard: false,
          }).addTo(layer);
        }
      }
    }
  }, [data, mode, filters, zoomTick, ready]);

  const focusCell = useCallback((cell: PriorityCell) => {
    const map = mapRef.current;
    if (!map) return;
    map.setView([cell.center[1], cell.center[0]], Math.max(map.getZoom(), 8), { animate: false });
  }, []);

  const zoomBy = (direction: 1 | -1) => {
    const map = mapRef.current;
    if (!map) return;
    map.setZoom(Math.max(SURFACE_VIEW.zoom, map.getZoom() + direction), { animate: false });
  };

  const goToRegion = (id: string) => {
    setRegionId(id);
    const map = mapRef.current;
    if (!map) return;
    const region = regions.find((r) => String(r.region_id) === id);
    if (!region) {
      map.setView([SURFACE_VIEW.latitude, SURFACE_VIEW.longitude], SURFACE_VIEW.zoom, { animate: false });
      return;
    }
    const [west, south, east, north] = region.bbox;
    map.fitBounds([[south, west], [north, east]], { animate: false });
    announceArea({ type: 'region', region_id: region.region_id });
    setAnnounced(region.name);
  };

  const startDraw = (shape: 'Rectangle' | 'Polygon') => {
    const map = mapRef.current;
    if (!map) return;
    map.pm.disableDraw();
    if (drawing === shape) {
      setDrawing('');
      return;
    }
    map.pm.enableDraw(shape, { snappable: false, tooltips: false });
    setDrawing(shape);
  };

  const clearShape = () => {
    mapRef.current?.pm.disableDraw();
    shapeLayer.current?.clearLayers();
    setHasShape(false);
    setDrawing('');
    setAnnounced('');
  };

  const placeCircle = (event: { preventDefault: () => void }) => {
    event.preventDefault();
    const L = leafletRef.current;
    const map = mapRef.current;
    if (!L || !map) return;
    const lat = Number(coords.lat);
    const lon = Number(coords.lon);
    const km = Number(coords.radius);
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || lat < -90 || lat > 90 || lon < -180 || lon > 180 || !(km >= 1 && km <= 200)) return;
    shapeLayer.current?.clearLayers();
    const circle = L.circle([lat, lon], { radius: km * 1000, color: '#2f4fd6', weight: 2, fillOpacity: 0.12 });
    shapeLayer.current?.addLayer(circle);
    map.fitBounds(circle.getBounds(), { padding: [40, 40], maxZoom: 11, animate: false });
    setHasShape(true);
    setAreaPanel('none');
    announceArea({ type: 'point', lat, lon, radius_km: km });
    setAnnounced(`${km} km around ${lat}, ${lon}`);
  };

  const toggle = <T,>(list: T[], value: T) => (list.includes(value) ? list.filter((x) => x !== value) : [...list, value]);
  const count = filterCount(mode, filters);
  const risk = alerts?.risk;
  const fresh = data ? staleness(data.updated_at, clock) : null;

  const card = (cell: PriorityCell) => (
    <button key={cell.h3} type="button" className="hm-card" onClick={() => focusCell(cell)}>
      <strong>
        Area near {cell.center[1].toFixed(1)}, {cell.center[0].toFixed(1)}
      </strong>
      {mode === 'risk' ? (
        <span className="hm-line">
          Next 14 days{' '}
          {cell.risk_tier ? (
            <b className="hm-chip" style={{ background: TIER_COLOR[cell.risk_tier], color: cell.risk_tier === 'medium' || cell.risk_tier === 'lower' ? '#222' : '#fff' }}>
              {TIER_LABEL[cell.risk_tier]}
            </b>
          ) : (
            'unavailable'
          )}
        </span>
      ) : (
        <span className="hm-line">
          Compared with usual <b className={`hm-chip hm-chip--${cell.alert_level ?? 'normal'}`}>{levelName(cell.alert_level ?? 'normal')}</b>
        </span>
      )}
      <span className="hm-line">
        Right now{' '}
        {cell.detections_7d == null
          ? 'unavailable'
          : cell.detections_7d > 0
            ? `${fmt(cell.detections_7d)} hot spots in 7 days${cell.typical_median != null ? ` (usually ${fmt(cell.typical_median)})` : ''}`
            : 'No hot spots in the last 24 h'}
      </span>
      {cell.detections_7d != null && cell.typical_median != null && cell.detections_7d > cell.typical_median && (
        <span className="hm-tag">More than usual for the season</span>
      )}
    </button>
  );

  return (
    <div ref={rootRef} className="hm" data-active={active ? 'true' : 'false'} aria-hidden={!active} {...(active ? {} : { inert: '' as unknown as boolean })}>
      <div ref={mapNode} className="hm__map" role="application" aria-label="Fire map" />

      <nav className="hm-toolbar" aria-label="Map view and area">
        <div className="hm-tabs" role="tablist" aria-label="Map view">
          {(
            [
              ['fire', 'Fire now'],
              ['risk', 'Risk, next 14 days'],
            ] as const
          ).map(([value, label]) => (
            <button key={value} type="button" role="tab" aria-selected={mode === value} onClick={() => setMode(value)}>
              {label}
            </button>
          ))}
        </div>
        <span className="hm-area-label">Area</span>
        <label className="hm-select">
          <span className="visually-hidden">Region</span>
          <select value={regionId} onChange={(e) => goToRegion(e.target.value)}>
            <option value="">Region: All Brazil</option>
            {regions.map((r) => (
              <option key={r.region_id} value={String(r.region_id)}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" className="hm-tool" aria-pressed={areaPanel === 'draw' || drawing !== ''} onClick={() => setAreaPanel(areaPanel === 'draw' ? 'none' : 'draw')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 20h9" />
            <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
          </svg>
          Draw area
        </button>
        <button type="button" className="hm-tool" aria-pressed={areaPanel === 'coords'} onClick={() => setAreaPanel(areaPanel === 'coords' ? 'none' : 'coords')}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11Z" />
            <circle cx="12" cy="10" r="2.5" />
          </svg>
          Coordinates
        </button>
        {areaPanel === 'draw' && (
          <div className="hm-popover" role="group" aria-label="Draw an area on the map">
            <button type="button" className="hm-row" aria-pressed={drawing === 'Rectangle'} onClick={() => startDraw('Rectangle')}>
              Rectangle
            </button>
            <button type="button" className="hm-row" aria-pressed={drawing === 'Polygon'} onClick={() => startDraw('Polygon')}>
              Polygon
            </button>
            {hasShape && (
              <button type="button" className="hm-row" onClick={clearShape}>
                Clear area
              </button>
            )}
          </div>
        )}
        {areaPanel === 'coords' && (
          <form className="hm-popover hm-coords" onSubmit={placeCircle}>
            <label>
              Latitude
              <input type="number" step="any" min={-90} max={90} required value={coords.lat} onChange={(e) => setCoords({ ...coords, lat: e.target.value })} />
            </label>
            <label>
              Longitude
              <input type="number" step="any" min={-180} max={180} required value={coords.lon} onChange={(e) => setCoords({ ...coords, lon: e.target.value })} />
            </label>
            <label>
              Radius (km, 1 to 200)
              <input type="number" step="any" min={1} max={200} required value={coords.radius} onChange={(e) => setCoords({ ...coords, radius: e.target.value })} />
            </label>
            <button type="submit" className="hm-row hm-row--primary">
              Show this area
            </button>
          </form>
        )}
      </nav>

      <section className="hm-filters" aria-label="Filters">
        <button type="button" className="hm-filters__head" aria-expanded={filtersOpen} onClick={() => setFiltersOpen((v) => !v)}>
          <strong>Filters</strong>
          {count > 0 && <span className="hm-count">{count}</span>}
          <span aria-hidden="true" className={filtersOpen ? 'hm-caret hm-caret--open' : 'hm-caret'}>
            ▾
          </span>
        </button>
        {filtersOpen && mode === 'fire' && (
          <>
            <p className="hm-group">Fire strength</p>
            {[...INTENSITIES].map((v) => (
              <button key={v} type="button" className="hm-row" aria-pressed={filters.intensities.includes(v)} onClick={() => setFilters({ ...filters, intensities: toggle(filters.intensities, v) })}>
                <i className={`hm-dot hm-dot--${v}`} /> {cap(v)}
              </button>
            ))}
            <p className="hm-group">Compared with usual (icon on the map)</p>
            {LEVELS.map((v) => (
              <button key={v} type="button" className="hm-row" aria-pressed={filters.levels.includes(v)} onClick={() => setFilters({ ...filters, levels: toggle(filters.levels, v) })}>
                {v === 'normal' ? <i className="hm-ring" /> : <i className={`hm-icon hm-icon--${v}`}>!</i>} {v === 'normal' ? 'Usual (no icon)' : levelName(v)}
              </button>
            ))}
          </>
        )}
        {filtersOpen && mode === 'risk' && (
          <>
            <p className="hm-group">Risk tier</p>
            {TIERS.map((v) => (
              <button key={v} type="button" className="hm-row" aria-pressed={filters.tiers.includes(v)} onClick={() => setFilters({ ...filters, tiers: toggle(filters.tiers, v) })}>
                <i className="hm-swatch" style={{ background: TIER_COLOR[v] }} /> {TIER_LABEL[v]}
              </button>
            ))}
            <p className="hm-group">Cells</p>
            <button type="button" className="hm-row" aria-pressed={filters.quietOnly} onClick={() => setFilters({ ...filters, quietOnly: !filters.quietOnly })}>
              <i className="hm-ring hm-ring--quiet" /> No hot spots now
            </button>
          </>
        )}
      </section>

      <div className="hm-right">
        <section className="hm-status" role="status" aria-label="Data status">
          <strong>
            {mode === 'risk'
              ? risk
                ? `Risk calculated ${brasiliaLabel(risk.scored_at)} (Brasília)`
                : 'Risk not available for this view'
              : data
                ? `Data updated ${agoLabel(data.updated_at, clock)}`
                : loading
                  ? 'Loading recent hot spots…'
                  : 'Update time unavailable'}
          </strong>
          <span>{mode === 'risk' ? 'Looks 14 days ahead' : 'Hot spots seen in the last 24 hours'}</span>
          <span>{mode === 'risk' ? 'Based on how often fire followed in the past. Not a guarantee.' : 'Recent hot spots can still change'}</span>
          {error && (
            <span className="hm-alert">
              The API did not respond.{' '}
              <button type="button" className="hm-link" onClick={() => setReload((v) => v + 1)}>
                Retry
              </button>
            </span>
          )}
          {mode === 'fire' && fresh && fresh !== 'current' && <span className="hm-alert">{fresh === 'outdated' ? 'Data is outdated' : 'Data may be delayed'}</span>}
        </section>
        <button type="button" className="hm-indicators" aria-expanded={panelOpen} onClick={() => setPanelOpen((v) => !v)}>
          <span aria-hidden="true">▥</span> Indicators <span className="hm-count">{loading && !data ? '…' : priorities.length}</span>
        </button>
        {panelOpen && (
          <aside className="hm-panel" aria-label="Where to look first">
            <button type="button" className="hm-panel__close" onClick={() => setPanelOpen(false)} aria-label="Close indicators">
              ×
            </button>
            <h2>Where to look first</h2>
            {alerts && (
              <p className="hm-sub">
                {mode === 'risk'
                  ? `${fmt(priorities.filter((c) => c.risk_tier === 'very_high').length)} very high · ${fmt(priorities.filter((c) => c.risk_tier === 'high').length)} high areas in view`
                  : `${fmt(priorities.filter((c) => c.alert_level === 'critical').length)} critical · ${fmt(priorities.filter((c) => c.alert_level === 'attention').length)} attention areas in view`}
              </p>
            )}
            {!alerts && !loading && <p className="hm-sub">Risk levels are not available for this view. Zoom in.</p>}
            {mode === 'risk' ? (
              groupByTier(priorities).map(({ tier, cells }) => {
                const open = groupOpen[tier] ?? tierStartsOpen(tier);
                const limit = groupShown[tier] ?? PAGE;
                return (
                  <section key={tier} className="hm-groupblock">
                    <button type="button" className="hm-grouphead" aria-expanded={open} onClick={() => setGroupOpen((o) => ({ ...o, [tier]: !open }))}>
                      <i className="hm-swatch" style={{ background: TIER_COLOR[tier] }} />
                      <strong>{TIER_LABEL[tier]}</strong>
                      <span>{fmt(cells.length)} areas</span>
                      <span aria-hidden="true" className={open ? 'hm-caret hm-caret--open' : 'hm-caret'}>
                        ▾
                      </span>
                    </button>
                    {open && (
                      <>
                        {cells.slice(0, limit).map(card)}
                        <p className="hm-sub">
                          Showing {Math.min(limit, cells.length)} of {fmt(cells.length)} areas ({PAGE} at a time)
                        </p>
                        {cells.length > limit && (
                          <button type="button" className="hm-more" onClick={() => setGroupShown((g) => ({ ...g, [tier]: limit + PAGE }))}>
                            See {PAGE} more
                          </button>
                        )}
                      </>
                    )}
                  </section>
                );
              })
            ) : (
              <>
                {priorities.slice(0, shown).map(card)}
                {alerts && (
                  <p className="hm-sub">
                    Showing {Math.min(shown, priorities.length)} of {fmt(priorities.length)} areas ({PAGE} at a time)
                  </p>
                )}
                {priorities.length > shown && (
                  <button type="button" className="hm-more" onClick={() => setShown((n) => n + PAGE)}>
                    See {PAGE} more
                  </button>
                )}
              </>
            )}
          </aside>
        )}
      </div>

      <section className={`hm-legend${legendOpen ? ' hm-legend--open' : ''}`} aria-label="Legend">
        <button type="button" className="hm-legend__head" aria-expanded={legendOpen} onClick={() => setLegendOpen((v) => !v)}>
          <span>Legend</span>
          <span aria-hidden="true" className={legendOpen ? 'hm-caret hm-caret--open' : 'hm-caret'}>
            ▾
          </span>
        </button>
        {legendOpen &&
          (mode === 'fire' ? (
            <>
              <h3>Heat concentration · last 24 h</h3>
              <div className="hm-gradient" style={{ background: COUNT_GRADIENT }} />
              <div className="hm-gradient-labels">
                <span>1</span>
                <span>10</span>
                <span>100+</span>
              </div>
              <small>Hot spots per area: the more yellow, the more.</small>
              <p className="hm-sym-title">More than usual for the season</p>
              <p className="hm-sym">
                <i className="hm-icon hm-icon--critical" title="Strongly above the usual for this time of year">
                  !
                </i>{' '}
                Critical
                <i className="hm-icon hm-icon--attention" title="Above the usual for this time of year">
                  !
                </i>{' '}
                Attention
              </p>
              <small>No icon = usual. Icons show when you zoom in.</small>
            </>
          ) : (
            <>
              <h3>Fire risk, next 14 days</h3>
              {TIERS.map((t) => {
                const share = risk?.tiers.find((x) => x.tier === t)?.historical_share;
                return (
                  <p key={t} className="hm-sym">
                    <i className="hm-swatch" style={{ background: TIER_COLOR[t] }} /> {TIER_LABEL[t]}
                    {share != null && ` · fire followed in ${Math.round(share * 100)}% of past cases`}
                  </p>
                );
              })}
              <small>"More than usual" = above this time of year.</small>
            </>
          ))}
      </section>

      <div className="hm-zoom" role="toolbar" aria-label="Map navigation">
        <button type="button" onClick={() => zoomBy(1)} aria-label="Zoom in" title="Zoom in">
          +
        </button>
        <button type="button" onClick={() => zoomBy(-1)} aria-label="Zoom out" title="Zoom out">
          −
        </button>
        <button
          type="button"
          onClick={() => mapRef.current?.setView([SURFACE_VIEW.latitude, SURFACE_VIEW.longitude], SURFACE_VIEW.zoom, { animate: false })}
          aria-label="Center on Brazil"
          title="Center on Brazil"
        >
          ⌖
        </button>
      </div>

      {announced && (
        <button type="button" className="hm-announce" onClick={onNext}>
          Calendar below now shows <b>{announced}</b> · See it
        </button>
      )}

      <button type="button" className="hm-back" onClick={onReturn}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m6 15 6-6 6 6" />
        </svg>
        Back to the globe
      </button>

      <button type="button" className="hm-next" onClick={onNext}>
        See the fire calendar
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      <footer ref={footRef} className="hm-footnote">
        {mode === 'fire' ? (
          <span>Recent hot spots (NASA FIRMS, VIIRS) can still change. Usual does not mean safe.</span>
        ) : (
          <span>
            Tiers show how often significant fire followed in past data (Brazil, 2021–2024):{' '}
            {TIERS.map((t) => {
              const share = risk?.tiers.find((x) => x.tier === t)?.historical_share;
              return share != null ? `${TIER_LABEL[t]} ${Math.round(share * 100)}%` : null;
            })
              .filter(Boolean)
              .join(' · ')}
            . {risk && `Calculated ${brasiliaLabel(risk.scored_at)} (Brasília).`} <a href="#method">How reliable is this?</a>
          </span>
        )}
        <span>
          Data: NASA FIRMS · <a href="#credits">Data & credits</a>
        </span>
      </footer>
    </div>
  );
}
