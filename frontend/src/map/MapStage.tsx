import { useCallback, useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';
import type * as LTypes from 'leaflet';
import { fetchRecentDetections } from '../api/client';
import type {
  GeoJsonPolygon,
  RecentDetectionsResponse,
  RecentHours,
} from '../api/types';
import { bboxToPolygon, closePolygonRing, DEFAULT_MAP_BBOX } from '../controls/areaPeriodModel';
import { BLUE_MARBLE_TILES, SURFACE_VIEW } from '../hero/globeTransition';
import { loadLeafletWithGeoman, type LeafletModule } from '../controls/leafletLoader';
import {
  computeHexagonDomain,
  formatHexagonTooltip,
  formatPointTooltip,
  styleForHexagon,
  styleForIntensityPoint,
} from '../controls/recentDetectionsModel';
import type { MapShape } from '../state/useExplorer';
import { EarlyWarning } from './EarlyWarning';
import { shapeView } from './shapeView';

export type BasemapId = 'black-marble' | 'blue-marble';
type DrawMode = 'rectangle' | 'polygon' | null;

interface DragBox {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface MapStageProps {
  shape: MapShape;
  onSelectPolygon: (geometry: GeoJsonPolygon) => void;
  /** Com o exemplo na tela, o mapa abre onde a descida do globo termina, em vez de enquadrar a área. */
  startOnArrival?: boolean;
}

// O mapa continua a descida da abertura: mesmo centro e mesmo zoom do fim do globo (SURFACE_VIEW).
export function arrivalView(startOnArrival: boolean): { center: [number, number]; zoom: number } | null {
  if (!startOnArrival) return null;
  return { center: [SURFACE_VIEW.latitude, SURFACE_VIEW.longitude], zoom: SURFACE_VIEW.zoom };
}

type DetectionsState = 'idle' | 'ready' | 'unavailable';

// Contorno da seleção: linha escura larga por baixo e âmbar por cima, legível em qualquer mapa base.
const HALO = { color: '#0d0f11', weight: 5, opacity: 0.85, fill: false, pmIgnore: true } as const;
const OUTLINE = { color: '#e9a23b', weight: 2.5, fillColor: '#e9a23b', fillOpacity: 0.08, pmIgnore: true } as const;

// Zoom em que uma célula H3 de resolução 4 (cerca de 1.770 km²) ocupa boa parte do mapa.
const FOCUS_ZOOM = 8;

function isCoarsePointer(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia('(pointer: coarse)').matches
    : false;
}

const GIBS = 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best';
const GIBS_ATTRIBUTION =
  'Imagery: <a href="https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs">NASA EOSDIS GIBS</a> · Coastlines: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

// Mapas base do NASA GIBS, sem chave de API. O Blue Marble é a mesma camada da descida do globo;
// o Black Marble é o próprio VIIRS de noite.
function applyBasemapLayers(L: LeafletModule, group: LTypes.LayerGroup, basemap: BasemapId): void {
  group.clearLayers();
  const base =
    basemap === 'black-marble'
      ? `${GIBS}/VIIRS_Black_Marble/default/2016-01-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.png`
      : BLUE_MARBLE_TILES;
  L.tileLayer(base, { maxZoom: 12, maxNativeZoom: 8, attribution: GIBS_ATTRIBUTION }).addTo(group);
  L.tileLayer(`${GIBS}/Coastlines_15m/default/GoogleMapsCompatible_Level13/{z}/{y}/{x}.png`, {
    maxZoom: 12,
    maxNativeZoom: 12,
    opacity: 0.55,
  }).addTo(group);
}

function renderShape(L: LeafletModule, group: LTypes.LayerGroup, shape: MapShape): LTypes.LatLngBounds | null {
  group.clearLayers();
  if (shape.kind === 'polygon') {
    const ring = shape.geometry.coordinates[0];
    if (!ring || ring.length < 3) return null;
    const latLngs: [number, number][] = ring.map(([lon, lat]) => [lat, lon]);
    L.polygon(latLngs, HALO).addTo(group);
    return L.polygon(latLngs, OUTLINE).addTo(group).getBounds();
  }
  if (shape.kind === 'point') {
    const { lat, lon, radius_km } = shape.point;
    L.circle([lat, lon], { ...HALO, radius: radius_km * 1000 }).addTo(group);
    const circle = L.circle([lat, lon], { ...OUTLINE, radius: radius_km * 1000 }).addTo(group);
    L.circleMarker([lat, lon], { radius: 3, color: '#e9a23b', fillColor: '#e9a23b', fillOpacity: 1, pmIgnore: true }).addTo(group);
    return circle.getBounds();
  }
  const [west, south, east, north] = shape.bbox;
  const corners: [[number, number], [number, number]] = [
    [south, west],
    [north, east],
  ];
  L.rectangle(corners, HALO).addTo(group);
  return L.rectangle(corners, OUTLINE).addTo(group).getBounds();
}

function renderRecentDetections(
  L: LeafletModule,
  group: LTypes.LayerGroup,
  data: RecentDetectionsResponse | null,
  visible: boolean,
): void {
  group.clearLayers();
  if (!visible || !data || data.features.length === 0) return;

  if (data.mode === 'hexagons') {
    const domain = computeHexagonDomain(data.features);
    const riskHorizonDays = data.alerts?.risk?.horizon_days;
    for (const feature of data.features) {
      const ring = feature.geometry.coordinates[0];
      if (!ring || ring.length < 3) continue;
      const latLngs: [number, number][] = ring.map(([lon, lat]) => [lat, lon]);
      const style = styleForHexagon(feature.properties.detections, domain);
      L.polygon(latLngs, {
        ...style,
        pmIgnore: true,
      })
        .bindTooltip(formatHexagonTooltip(feature.properties, riskHorizonDays))
        .addTo(group);
    }
    return;
  }

  for (const feature of data.features) {
    const [lon, lat] = feature.geometry.coordinates;
    const style = styleForIntensityPoint(feature.properties.intensity);
    L.circleMarker([lat, lon], {
      radius: style.radius,
      weight: style.weight,
      color: style.color,
      fillColor: style.fillColor,
      fillOpacity: style.fillOpacity,
      dashArray: style.dashArray,
      pmIgnore: true,
    })
      .bindTooltip(formatPointTooltip(feature.properties))
      .addTo(group);
  }
}

export function MapStage({ shape, onSelectPolygon, startOnArrival = false }: MapStageProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const startOnArrivalRef = useRef(startOnArrival);
  startOnArrivalRef.current = startOnArrival;
  const canvasHostRef = useRef<HTMLDivElement>(null);
  const leafletRef = useRef<LeafletModule | null>(null);
  const mapRef = useRef<LTypes.Map | null>(null);
  const baseGroupRef = useRef<LTypes.LayerGroup | null>(null);
  const detectionsGroupRef = useRef<LTypes.LayerGroup | null>(null);
  const selectionGroupRef = useRef<LTypes.LayerGroup | null>(null);
  const currentBboxRef = useRef<[number, number, number, number]>(DEFAULT_MAP_BBOX);
  const currentZoomRef = useRef<number>(4);
  const drawModeRef = useRef<DrawMode>(null);
  const basemapRef = useRef<BasemapId>('blue-marble');
  const showHotSpotsRef = useRef<boolean>(true);
  const hotSpotsHoursRef = useRef<RecentHours>(24);
  // Os pedidos de focos recentes nunca são cancelados: um contador descarta respostas antigas.
  // Cancelar (a cada movimento ou ao desmontar, que o StrictMode faz em dev) jogava fora
  // respostas já em trânsito.
  const detectionsSeqRef = useRef(0);
  const moveDebounceRef = useRef<number | null>(null);
  const onSelectPolygonRef = useRef(onSelectPolygon);
  const suppressClickOnceRef = useRef(false);
  const initPromiseRef = useRef<Promise<void> | null>(null);
  const dragStartRef = useRef<{ clientX: number; clientY: number } | null>(null);
  const shapeRef = useRef<MapShape>(shape);
  const pendingFocusRef = useRef<[number, number] | null>(null);

  const [basemap, setBasemap] = useState<BasemapId>('blue-marble');
  const [drawMode, setDrawMode] = useState<DrawMode>(null);
  const [polygonPoints, setPolygonPoints] = useState<[number, number][]>([]);
  const [dragBox, setDragBox] = useState<DragBox | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [showHotSpots, setShowHotSpots] = useState<boolean>(true);
  const [hotSpotsHours, setHotSpotsHours] = useState<RecentHours>(24);
  const [recentDetections, setRecentDetections] = useState<RecentDetectionsResponse | null>(null);
  const [detectionsState, setDetectionsState] = useState<DetectionsState>('idle');
  const [focusRequest, setFocusRequest] = useState(0);

  onSelectPolygonRef.current = onSelectPolygon;
  drawModeRef.current = drawMode;
  basemapRef.current = basemap;
  showHotSpotsRef.current = showHotSpots;
  hotSpotsHoursRef.current = hotSpotsHours;

  const requestRecentDetections = useCallback(
    async (bbox: [number, number, number, number], hours: RecentHours, zoom: number) => {
      const seq = ++detectionsSeqRef.current;
      const isStale = () => seq !== detectionsSeqRef.current;

      try {
        const result = await fetchRecentDetections({ bbox, hours, zoom: Math.round(zoom) });
        if (isStale()) return;
        setRecentDetections(result);
        setDetectionsState('ready');
      } catch {
        // Sem API, a camada fica vazia e a legenda explica. Nunca pontos inventados.
        if (isStale()) return;
        setRecentDetections(null);
        setDetectionsState('unavailable');
      }
    },
    [],
  );

  const syncDrawModeToMap = useCallback((mode: DrawMode) => {
    const map = mapRef.current;
    if (!map) return;
    map.pm.disableDraw();
    if (mode === 'rectangle') {
      map.dragging.disable();
      map.pm.enableDraw('Rectangle', { snappable: false });
    } else if (mode === 'polygon') {
      map.dragging.disable();
      map.pm.enableDraw('Polygon', { snappable: true });
    } else if (!isCoarsePointer()) {
      map.dragging.enable();
    }
  }, []);

  const ensureMap = useCallback(() => {
    if (mapRef.current || initPromiseRef.current) return initPromiseRef.current ?? Promise.resolve();
    const host = canvasHostRef.current;
    if (!host) return Promise.resolve();

    initPromiseRef.current = (async () => {
      try {
        const L = await loadLeafletWithGeoman();
        if (!canvasHostRef.current || mapRef.current) return;

        const coarse = isCoarsePointer();
        const map = L.map(canvasHostRef.current, {
          preferCanvas: true,
          scrollWheelZoom: false,
          dragging: !coarse,
          touchZoom: !coarse,
          pmIgnore: false,
        });

        const [west, south, east, north] = currentBboxRef.current;
        map.fitBounds(
          [
            [south, west],
            [north, east],
          ],
          { padding: [16, 16], animate: false },
        );

        const baseGroup = L.layerGroup().addTo(map);
        const detectionsGroup = L.layerGroup().addTo(map);
        const selectionGroup = L.layerGroup().addTo(map);
        applyBasemapLayers(L, baseGroup, basemapRef.current);
        const initialBounds = renderShape(L, selectionGroup, shapeRef.current);
        const arrival = arrivalView(startOnArrivalRef.current);
        if (arrival) map.setView(arrival.center, arrival.zoom, { animate: false });
        else if (initialBounds) map.fitBounds(initialBounds, { padding: [48, 48], maxZoom: 7, animate: false });
        currentZoomRef.current = Math.round(map.getZoom() || 4);

        const updateBoundsAndFetch = () => {
          const bounds = map.getBounds();
          const nextBbox: [number, number, number, number] = [
            Number(Math.max(-180, bounds.getWest()).toFixed(4)),
            Number(Math.max(-90, bounds.getSouth()).toFixed(4)),
            Number(Math.min(180, bounds.getEast()).toFixed(4)),
            Number(Math.min(90, bounds.getNorth()).toFixed(4)),
          ];
          currentBboxRef.current = nextBbox;
          currentZoomRef.current = Math.round(map.getZoom() || 4);

          if (!showHotSpotsRef.current) return;
          if (moveDebounceRef.current !== null) {
            window.clearTimeout(moveDebounceRef.current);
          }
          moveDebounceRef.current = window.setTimeout(() => {
            void requestRecentDetections(
              currentBboxRef.current,
              hotSpotsHoursRef.current,
              currentZoomRef.current,
            );
          }, 150);
        };

        map.on('moveend', updateBoundsAndFetch);
        map.on('zoomend', updateBoundsAndFetch);

        map.on('pm:create', (event) => {
          const createdLayer = event.layer as LTypes.Polygon;
          const geo = createdLayer.toGeoJSON();
          map.removeLayer(createdLayer);

          if (geo.geometry.type === 'Polygon') {
            const geometry: GeoJsonPolygon = {
              type: 'Polygon',
              coordinates: geo.geometry.coordinates.map(closePolygonRing),
            };
            setDrawMode(null);
            setPolygonPoints([]);
            map.pm.disableDraw();
            if (!isCoarsePointer()) map.dragging.enable();
            onSelectPolygonRef.current(geometry);
          }
        });

        map.on('pm:drawstart', (event) => {
          if (event.shape === 'Polygon') {
            setPolygonPoints([]);
            event.workingLayer.on('pm:vertexadded', (vertexEvent) => {
              const evt = vertexEvent as { latlng?: LTypes.LatLng };
              if (evt.latlng) {
                const { lng, lat } = evt.latlng;
                setPolygonPoints((prev) => [...prev, [Number(lng.toFixed(5)), Number(lat.toFixed(5))]]);
              }
            });
          }
        });

        leafletRef.current = L;
        mapRef.current = map;
        baseGroupRef.current = baseGroup;
        detectionsGroupRef.current = detectionsGroup;
        selectionGroupRef.current = selectionGroup;
        setMapReady(true);

        if (drawModeRef.current) {
          syncDrawModeToMap(drawModeRef.current);
        }
      } catch {
        // Fallback controls still permit drag/click polygon creation in environments without full canvas/DOM support.
      }
    })();

    return initPromiseRef.current;
  }, [requestRecentDetections, syncDrawModeToMap]);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          observer.disconnect();
          void ensureMap();
        }
      },
      { rootMargin: '120px' },
    );
    observer.observe(el);

    return () => {
      observer.disconnect();
    };
  }, [ensureMap]);

  useEffect(() => {
    const seqRef = detectionsSeqRef;
    return () => {
      seqRef.current += 1; // respostas que chegarem depois de desmontar são ignoradas
      if (moveDebounceRef.current !== null) {
        window.clearTimeout(moveDebounceRef.current);
      }
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!showHotSpots) {
      detectionsSeqRef.current += 1; // respostas que chegarem depois de desligar a camada são ignoradas
      if (detectionsGroupRef.current) {
        detectionsGroupRef.current.clearLayers();
      }
      return;
    }
    void requestRecentDetections(currentBboxRef.current, hotSpotsHours, currentZoomRef.current);
  }, [showHotSpots, hotSpotsHours, requestRecentDetections]);

  useEffect(() => {
    if (leafletRef.current && detectionsGroupRef.current) {
      renderRecentDetections(
        leafletRef.current,
        detectionsGroupRef.current,
        recentDetections,
        showHotSpots,
      );
    }
  }, [recentDetections, showHotSpots, mapReady]);

  useEffect(() => {
    if (leafletRef.current && baseGroupRef.current) {
      applyBasemapLayers(leafletRef.current, baseGroupRef.current, basemap);
    }
  }, [basemap]);

  useEffect(() => {
    const changed = shapeRef.current !== shape;
    shapeRef.current = shape;
    const L = leafletRef.current;
    const map = mapRef.current;
    const selectionGroup = selectionGroupRef.current;
    if (!L || !map || !selectionGroup) {
      // O mapa ainda não carregou (fica abaixo da abertura): os focos recentes da nova área
      // são pedidos já, pelo enquadramento da seleção. Quando o mapa carregar, ele parte daqui.
      if (!changed) return;
      const view = shapeView(shape);
      currentBboxRef.current = view.bbox;
      currentZoomRef.current = view.zoom;
      if (showHotSpotsRef.current) void requestRecentDetections(view.bbox, hotSpotsHoursRef.current, view.zoom);
      return;
    }
    const bounds = renderShape(L, selectionGroup, shape);
    // Quando o mapa acaba de carregar no enquadramento da chegada, a área do exemplo só é desenhada.
    if (bounds && (changed || !startOnArrivalRef.current)) map.fitBounds(bounds, { padding: [48, 48], maxZoom: 7, animate: false });
  }, [shape, mapReady, requestRecentDetections]);

  // Depois do efeito acima: se o clique na lista carregou o mapa, o enquadramento da área não desfaz o foco.
  useEffect(() => {
    const map = mapRef.current;
    const latLng = pendingFocusRef.current;
    if (!map || !latLng) return;
    pendingFocusRef.current = null;
    map.setView(latLng, Math.max(map.getZoom(), FOCUS_ZOOM), { animate: false });
  }, [focusRequest, mapReady]);

  const clientToLngLat = useCallback((clientX: number, clientY: number): [number, number] => {
    const viewport = viewportRef.current;
    const L = leafletRef.current;
    const map = mapRef.current;
    if (viewport && L && map) {
      const rect = viewport.getBoundingClientRect();
      const point = L.point(clientX - rect.left, clientY - rect.top);
      const ll = map.containerPointToLatLng(point);
      return [Number(ll.lng.toFixed(5)), Number(ll.lat.toFixed(5))];
    }

    const rect = viewport?.getBoundingClientRect();
    const width = rect && rect.width > 0 ? rect.width : 600;
    const height = rect && rect.height > 0 ? rect.height : 380;
    const left = rect?.left ?? 0;
    const top = rect?.top ?? 0;
    const [west, south, east, north] = currentBboxRef.current;
    const rx = Math.min(1, Math.max(0, (clientX - left) / width));
    const ry = Math.min(1, Math.max(0, (clientY - top) / height));
    const lon = Number((west + rx * (east - west)).toFixed(5));
    const lat = Number((north - ry * (north - south)).toFixed(5));
    return [lon, lat];
  }, []);

  const commitDrawnGeometry = useCallback((geometry: GeoJsonPolygon) => {
    setDrawMode(null);
    setPolygonPoints([]);
    syncDrawModeToMap(null);
    onSelectPolygonRef.current(geometry);
  }, [syncDrawModeToMap]);

  const finishRectangleDrag = useCallback(
    (startX: number, startY: number, endX: number, endY: number) => {
      const p1 = clientToLngLat(startX, startY);
      const p2 = clientToLngLat(endX, endY);
      const geometry = bboxToPolygon(p1[0], p1[1], p2[0], p2[1]);
      commitDrawnGeometry(geometry);
    },
    [clientToLngLat, commitDrawnGeometry],
  );

  const handleMouseDownCapture = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (drawModeRef.current !== 'rectangle') return;
      const start = { clientX: event.clientX, clientY: event.clientY };
      dragStartRef.current = start;

      const computeBox = (cx: number, cy: number): DragBox | null => {
        const rect = viewportRef.current?.getBoundingClientRect();
        if (!rect) return null;
        return {
          left: Math.min(start.clientX, cx) - rect.left,
          top: Math.min(start.clientY, cy) - rect.top,
          width: Math.abs(cx - start.clientX),
          height: Math.abs(cy - start.clientY),
        };
      };

      const onWindowMouseMove = (moveEvent: MouseEvent) => {
        if (Math.hypot(moveEvent.clientX - start.clientX, moveEvent.clientY - start.clientY) >= 5) {
          setDragBox(computeBox(moveEvent.clientX, moveEvent.clientY));
        }
      };

      const onWindowMouseUp = (upEvent: MouseEvent) => {
        window.removeEventListener('mousemove', onWindowMouseMove);
        window.removeEventListener('mouseup', onWindowMouseUp);
        setDragBox(null);
        dragStartRef.current = null;

        if (Math.hypot(upEvent.clientX - start.clientX, upEvent.clientY - start.clientY) >= 5) {
          suppressClickOnceRef.current = true;
          window.setTimeout(() => {
            suppressClickOnceRef.current = false;
          }, 0);
          finishRectangleDrag(start.clientX, start.clientY, upEvent.clientX, upEvent.clientY);
        }
      };

      window.addEventListener('mousemove', onWindowMouseMove);
      window.addEventListener('mouseup', onWindowMouseUp);
    },
    [finishRectangleDrag],
  );

  const handleViewportClickCapture = useCallback((event: ReactMouseEvent<HTMLDivElement>) => {
    if (suppressClickOnceRef.current) {
      suppressClickOnceRef.current = false;
      event.stopPropagation();
      event.preventDefault();
    }
  }, []);

  const handleViewportClick = useCallback(
    (event: ReactMouseEvent<HTMLDivElement>) => {
      if (drawModeRef.current !== 'polygon') return;
      // When Leaflet-Geoman is active, pm:drawstart/vertexadded tracks points; fallback covers pre-load clicks.
      if (!mapRef.current) {
        const point = clientToLngLat(event.clientX, event.clientY);
        setPolygonPoints((prev) => [...prev, point]);
      }
    },
    [clientToLngLat],
  );

  const finishPolygon = useCallback(() => {
    const map = mapRef.current as (LTypes.Map & {
      pm?: { Draw?: { Polygon?: { _finishShape?: () => void } } };
    }) | null;

    if (map?.pm?.Draw?.Polygon?._finishShape) {
      map.pm.Draw.Polygon._finishShape();
      if (drawModeRef.current === null) return;
    }

    if (polygonPoints.length >= 3) {
      const geometry: GeoJsonPolygon = {
        type: 'Polygon',
        coordinates: [closePolygonRing(polygonPoints)],
      };
      commitDrawnGeometry(geometry);
    }
  }, [commitDrawnGeometry, polygonPoints]);

  const toggleMode = (mode: Exclude<DrawMode, null>) => {
    void ensureMap();
    const nextMode = drawMode === mode ? null : mode;
    // Ao entrar no modo de desenho, o mapa precisa estar na tela para receber o arrasto.
    if (nextMode) viewportRef.current?.scrollIntoView({ block: 'nearest', behavior: 'instant' as ScrollBehavior });
    setDrawMode(nextMode);
    setPolygonPoints([]);
    syncDrawModeToMap(nextMode);
  };

  // Item da lista "Where to look first": traz o mapa para a tela e centra na célula de resolução 4.
  const focusCell = (latLng: [number, number]) => {
    viewportRef.current?.scrollIntoView({ block: 'nearest', behavior: 'instant' as ScrollBehavior });
    pendingFocusRef.current = latLng;
    void ensureMap();
    setFocusRequest((n) => n + 1);
  };

  const switchBasemap = (next: BasemapId) => {
    void ensureMap();
    setBasemap(next);
  };

  const statusText =
    drawMode === 'rectangle'
      ? 'Drag across the map to draw a rectangle.'
      : drawMode === 'polygon'
        ? `Click to add points (${polygonPoints.length} so far), then finish the polygon.`
        : null;

  const windowLabel = hotSpotsHours === 168 ? 'last 7 days' : `last ${hotSpotsHours} h`;

  return (
    <div className="map-stage">
      <div className="map-stage__bar" role="toolbar" aria-label="Map drawing and layer controls">
        <div className="map-stage__group">
          <button
            type="button"
            className="map-btn"
            aria-pressed={drawMode === 'rectangle'}
            onClick={() => toggleMode('rectangle')}
          >
            Draw rectangle
          </button>
          <button
            type="button"
            className="map-btn"
            aria-pressed={drawMode === 'polygon'}
            onClick={() => toggleMode('polygon')}
          >
            Draw polygon
          </button>
          {drawMode === 'polygon' && polygonPoints.length >= 3 && (
            <button type="button" className="map-btn map-btn--primary" onClick={finishPolygon}>
              Finish polygon
            </button>
          )}
        </div>
        <div className="map-stage__group" role="group" aria-label="Recent hot spots layer">
          <button
            type="button"
            className="map-btn"
            aria-pressed={showHotSpots}
            onClick={() => setShowHotSpots((prev) => !prev)}
          >
            Recent hot spots
          </button>
          <select
            aria-label="Recent hot spots window"
            className="map-select"
            value={String(hotSpotsHours)}
            disabled={!showHotSpots}
            onChange={(e) => setHotSpotsHours(Number(e.target.value) as RecentHours)}
          >
            <option value="24">24 h</option>
            <option value="72">72 h</option>
            <option value="168">7 days</option>
          </select>
        </div>
        <div className="map-stage__group" role="group" aria-label="Base map layer">
          <button type="button" className="map-btn" aria-pressed={basemap === 'black-marble'} onClick={() => switchBasemap('black-marble')}>
            Black Marble (NASA GIBS)
          </button>
          <button type="button" className="map-btn" aria-pressed={basemap === 'blue-marble'} onClick={() => switchBasemap('blue-marble')}>
            Blue Marble (NASA GIBS)
          </button>
        </div>
      </div>

      <div
        ref={viewportRef}
        role="region"
        aria-label="Area selection map"
        className={`map-stage__viewport${drawMode ? ' map-stage__viewport--drawing' : ''}`}
        onMouseDownCapture={handleMouseDownCapture}
        onClickCapture={handleViewportClickCapture}
        onClick={handleViewportClick}
        onDoubleClick={() => {
          if (drawMode === 'polygon' && !mapRef.current && polygonPoints.length >= 3) {
            finishPolygon();
          }
        }}
      >
        <div ref={canvasHostRef} className="map-stage__canvas" />
        {statusText && (
          <p className="map-stage__hint" aria-live="polite">
            {statusText}
          </p>
        )}
        {dragBox && (
          <div
            className="map-stage__drag"
            style={{ left: `${dragBox.left}px`, top: `${dragBox.top}px`, width: `${dragBox.width}px`, height: `${dragBox.height}px` }}
            aria-hidden="true"
          />
        )}
        {!mapReady && (
          <div className="map-stage__placeholder">
            <span>Loading map…</span>
          </div>
        )}
      </div>

      <div className="map-stage__legend" aria-label="Recent hot spots legend" aria-live="polite">
        {!showHotSpots ? (
          <span>Recent hot spots layer is off.</span>
        ) : detectionsState === 'unavailable' ? (
          <span>Recent hot spots are unavailable: the API did not respond. No points are drawn.</span>
        ) : (
          <>
            <span className="map-stage__legend-count">
              {recentDetections !== null
                ? `${recentDetections.total_detections.toLocaleString('en-US')} VIIRS detections in view, ${windowLabel}`
                : `Recent VIIRS detections, ${windowLabel}`}
            </span>
            {recentDetections?.mode === 'hexagons' ? (
              <span>
                <span className="map-swatch map-swatch--hex" style={{ background: 'linear-gradient(90deg, #00224e, #7c7b78, #fee838)' }} aria-hidden="true" />
                Detections per hexagon (log scale)
              </span>
            ) : (
              <>
                <span>
                  <span className="map-swatch map-swatch--low" aria-hidden="true" />
                  Low
                </span>
                <span>
                  <span className="map-swatch map-swatch--medium" aria-hidden="true" />
                  Medium
                </span>
                <span>
                  <span className="map-swatch map-swatch--high" aria-hidden="true" />
                  High intensity
                </span>
              </>
            )}
          </>
        )}
      </div>

      {showHotSpots && detectionsState === 'ready' && (
        <EarlyWarning alerts={recentDetections?.alerts} onFocusCell={focusCell} />
      )}
    </div>
  );
}
