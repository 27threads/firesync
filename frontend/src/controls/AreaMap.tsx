import { useCallback, useEffect, useRef, useState, type MouseEvent as ReactMouseEvent } from 'react';
import type * as LTypes from 'leaflet';
import type { GeoJsonPolygon, PointArea } from '../api/types';
import { bboxToPolygon, closePolygonRing, DEFAULT_MAP_BBOX } from './areaPeriodModel';
import { loadLeafletWithGeoman, type LeafletModule } from './leafletLoader';

export type BasemapId = 'carto-dark' | 'nasa-gibs';
type DrawMode = 'rectangle' | 'polygon' | null;

interface DragBox {
  left: number;
  top: number;
  width: number;
  height: number;
}

interface AreaMapProps {
  focusBbox: [number, number, number, number] | null;
  focusPoint: PointArea | null;
  onSelectPolygon: (geometry: GeoJsonPolygon) => void;
}

function isCoarsePointer(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia('(pointer: coarse)').matches
    : false;
}

function applyBasemapLayers(L: LeafletModule, group: LTypes.LayerGroup, basemap: BasemapId): void {
  group.clearLayers();
  if (basemap === 'nasa-gibs') {
    L.tileLayer(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_NextGeneration/default/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpg',
      {
        maxZoom: 19,
        maxNativeZoom: 8,
        attribution: 'Imagery: <a href="https://earthdata.nasa.gov/eosdis/science-system-description/eosdis-components/gibs">NASA EOSDIS GIBS</a>',
      },
    ).addTo(group);
    // Keep Reference_Features_15m only; Reference_Labels_15m produces black blocks in Leaflet.
    L.tileLayer(
      'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/Reference_Features_15m/default/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png',
      {
        maxZoom: 19,
        maxNativeZoom: 9,
        opacity: 0.75,
      },
    ).addTo(group);
    return;
  }

  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    subdomains: 'abcd',
    maxZoom: 19,
    attribution:
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
  }).addTo(group);
}

function renderPolygonSelection(L: LeafletModule, group: LTypes.LayerGroup, geometry: GeoJsonPolygon): void {
  group.clearLayers();
  const ring = geometry.coordinates[0];
  if (!ring || ring.length < 3) return;
  const latLngs: [number, number][] = ring.map(([lon, lat]) => [lat, lon]);
  L.polygon(latLngs, {
    color: '#f2a93b',
    weight: 2,
    fillColor: '#f2a93b',
    fillOpacity: 0.16,
    pmIgnore: true,
  }).addTo(group);
}

export function AreaMap({ focusBbox, focusPoint, onSelectPolygon }: AreaMapProps) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const canvasHostRef = useRef<HTMLDivElement>(null);
  const leafletRef = useRef<LeafletModule | null>(null);
  const mapRef = useRef<LTypes.Map | null>(null);
  const baseGroupRef = useRef<LTypes.LayerGroup | null>(null);
  const selectionGroupRef = useRef<LTypes.LayerGroup | null>(null);
  const currentBboxRef = useRef<[number, number, number, number]>(DEFAULT_MAP_BBOX);
  const drawModeRef = useRef<DrawMode>(null);
  const basemapRef = useRef<BasemapId>('carto-dark');
  const onSelectPolygonRef = useRef(onSelectPolygon);
  const suppressClickOnceRef = useRef(false);
  const initPromiseRef = useRef<Promise<void> | null>(null);
  const dragStartRef = useRef<{ clientX: number; clientY: number } | null>(null);
  const lastDrawnPolygonRef = useRef<GeoJsonPolygon | null>(null);

  const [basemap, setBasemap] = useState<BasemapId>('carto-dark');
  const [drawMode, setDrawMode] = useState<DrawMode>(null);
  const [polygonPoints, setPolygonPoints] = useState<[number, number][]>([]);
  const [dragBox, setDragBox] = useState<DragBox | null>(null);
  const [mapReady, setMapReady] = useState(false);

  onSelectPolygonRef.current = onSelectPolygon;
  drawModeRef.current = drawMode;
  basemapRef.current = basemap;

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
        const selectionGroup = L.layerGroup().addTo(map);
        applyBasemapLayers(L, baseGroup, basemapRef.current);

        map.on('pm:create', (event) => {
          const createdLayer = event.layer as LTypes.Polygon;
          const geo = createdLayer.toGeoJSON();
          map.removeLayer(createdLayer);

          if (geo.geometry.type === 'Polygon') {
            const geometry: GeoJsonPolygon = {
              type: 'Polygon',
              coordinates: geo.geometry.coordinates.map(closePolygonRing),
            };
            lastDrawnPolygonRef.current = geometry;
            renderPolygonSelection(L, selectionGroup, geometry);
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
        selectionGroupRef.current = selectionGroup;
        if (lastDrawnPolygonRef.current) {
          renderPolygonSelection(L, selectionGroup, lastDrawnPolygonRef.current);
        }
        setMapReady(true);

        if (drawModeRef.current) {
          syncDrawModeToMap(drawModeRef.current);
        }
      } catch {
        // Fallback controls still permit drag/click polygon creation in environments without full canvas/DOM support.
      }
    })();

    return initPromiseRef.current;
  }, [syncDrawModeToMap]);

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
    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (leafletRef.current && baseGroupRef.current) {
      applyBasemapLayers(leafletRef.current, baseGroupRef.current, basemap);
    }
  }, [basemap]);

  useEffect(() => {
    if (!focusBbox) return;
    lastDrawnPolygonRef.current = null;
    currentBboxRef.current = focusBbox;
    const L = leafletRef.current;
    const map = mapRef.current;
    const selectionGroup = selectionGroupRef.current;
    if (!L || !map || !selectionGroup) return;

    const [west, south, east, north] = focusBbox;
    map.fitBounds(
      [
        [south, west],
        [north, east],
      ],
      { padding: [20, 20], animate: false },
    );
    selectionGroup.clearLayers();
    L.rectangle(
      [
        [south, west],
        [north, east],
      ],
      {
        color: '#f2a93b',
        weight: 2,
        fillColor: '#f2a93b',
        fillOpacity: 0.1,
        pmIgnore: true,
      },
    ).addTo(selectionGroup);
  }, [focusBbox, mapReady]);

  useEffect(() => {
    if (!focusPoint) return;
    lastDrawnPolygonRef.current = null;
    const L = leafletRef.current;
    const map = mapRef.current;
    const selectionGroup = selectionGroupRef.current;
    if (!L || !map || !selectionGroup) return;

    selectionGroup.clearLayers();
    const circle = L.circle([focusPoint.lat, focusPoint.lon], {
      radius: focusPoint.radius_km * 1000,
      color: '#f2a93b',
      weight: 2,
      fillColor: '#f2a93b',
      fillOpacity: 0.16,
      pmIgnore: true,
    }).addTo(selectionGroup);
    L.circleMarker([focusPoint.lat, focusPoint.lon], {
      radius: 4,
      color: '#f2a93b',
      fillColor: '#f2a93b',
      fillOpacity: 1,
      pmIgnore: true,
    }).addTo(selectionGroup);
    map.fitBounds(circle.getBounds(), { padding: [32, 32], maxZoom: 12, animate: false });
  }, [focusPoint, mapReady]);

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
    lastDrawnPolygonRef.current = geometry;
    const L = leafletRef.current;
    const selectionGroup = selectionGroupRef.current;
    if (L && selectionGroup) {
      renderPolygonSelection(L, selectionGroup, geometry);
    }
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
    setDrawMode(nextMode);
    setPolygonPoints([]);
    syncDrawModeToMap(nextMode);
  };

  const switchBasemap = (next: BasemapId) => {
    void ensureMap();
    setBasemap(next);
  };

  const statusText =
    drawMode === 'rectangle'
      ? 'Drag across the map or click two opposite corners to draw a rectangle.'
      : drawMode === 'polygon'
        ? `Click points on the map to outline an area (${polygonPoints.length} points), then finish the polygon.`
        : 'Draw an area on the map, pick a region above, or enter coordinates below.';

  return (
    <div className="area-map">
      <div className="area-map__toolbar" role="toolbar" aria-label="Map drawing and layer controls">
        <div className="area-map__actions">
          <button
            type="button"
            className={`map-btn${drawMode === 'rectangle' ? ' map-btn--active' : ''}`}
            aria-pressed={drawMode === 'rectangle'}
            onClick={() => toggleMode('rectangle')}
          >
            Draw rectangle
          </button>
          <button
            type="button"
            className={`map-btn${drawMode === 'polygon' ? ' map-btn--active' : ''}`}
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
        <div className="area-map__layers" role="group" aria-label="Base map layer">
          <button
            type="button"
            className={`map-btn${basemap === 'carto-dark' ? ' map-btn--active' : ''}`}
            aria-pressed={basemap === 'carto-dark'}
            onClick={() => switchBasemap('carto-dark')}
          >
            Dark map (CARTO)
          </button>
          <button
            type="button"
            className={`map-btn${basemap === 'nasa-gibs' ? ' map-btn--active' : ''}`}
            aria-pressed={basemap === 'nasa-gibs'}
            onClick={() => switchBasemap('nasa-gibs')}
          >
            NASA GIBS satellite
          </button>
        </div>
      </div>

      <p className="area-map__hint" aria-live="polite">
        {statusText}
      </p>

      <div
        ref={viewportRef}
        role="region"
        aria-label="Area selection map"
        className={`area-map__viewport${drawMode ? ' area-map__viewport--drawing' : ''}`}
        onMouseDownCapture={handleMouseDownCapture}
        onClickCapture={handleViewportClickCapture}
        onClick={handleViewportClick}
        onDoubleClick={() => {
          if (drawMode === 'polygon' && !mapRef.current && polygonPoints.length >= 3) {
            finishPolygon();
          }
        }}
      >
        <div ref={canvasHostRef} className="area-map__canvas" />
        {dragBox && (
          <div
            className="area-map__drag-preview"
            style={{
              left: `${dragBox.left}px`,
              top: `${dragBox.top}px`,
              width: `${dragBox.width}px`,
              height: `${dragBox.height}px`,
            }}
            aria-hidden="true"
          />
        )}
        {!mapReady && (
          <div className="area-map__placeholder">
            <span>Interactive map canvas</span>
          </div>
        )}
      </div>
    </div>
  );
}
