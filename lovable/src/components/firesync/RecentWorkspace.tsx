import { cellToBoundary, isValidCell } from "h3-js";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  Globe2,
  Copy,
  Crosshair,
  Download,
  Info,
  LoaderCircle,
  SlidersHorizontal,
  ChevronDown,
  Layers,
  X,
} from "lucide-react";
import AreaMap, { type AreaSelection } from "./AreaMap";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Calendar } from "./Calendar";
import { demoData, number, type CalendarData } from "@/lib/fire-data";
import {
  coordinateArea,
  demoForWindow,
  freshness,
  highShare,
  priorityInView,
  riskFrequency,
  type DetectionFeature,
  type Intensity,
  type Level,
  type Priority,
  type RecentData,
  type Viewport,
} from "@/lib/recent-data";
import { fetchAreaHistory, fetchRecent, RecentApiError } from "@/lib/recent-api";
import { BRAZIL_STATES, STATE_BOUNDS, priorityInState, type BrazilState } from '@/lib/brazil-states';
const levelsAll: Level[] = ["critical", "attention", "normal"];
const intensityAll: Intensity[] = ["high", "medium", "low"];
const share = (v: number) =>
  new Intl.NumberFormat("en-US", { style: "percent", maximumFractionDigits: 1 }).format(v);
function RiskSentence({ cell, data }: { cell: Priority; data: RecentData }) {
  const risk = riskFrequency(cell, data);
  return (
    <>
      {risk && (
        <p>
          In past weeks rated {cell.alert_level}, unusually high detections followed in the next 14
          days {share(risk.share)} of the time ({share(risk.average)} on average). Based on past
          frequency in 2013–2024, not a prediction for this place.
        </p>
      )}
      <p className="risk-caution">
        Normal does not mean safe: about half of the high-detection periods followed a week rated
        Normal.
      </p>
    </>
  );
}
export default function RecentWorkspace({
  active,
  resetForHandoff,
  onReady,
  onReturn,
  selection,
  onSelect,
  onRecentSummary,
}: {
  active: boolean;
  resetForHandoff: boolean;
  onReady: () => void;
  onReturn: () => void;
  selection: AreaSelection | null;
  onSelect: (s: AreaSelection | null) => void;
  onRecentSummary?: (data: RecentData, demo: boolean) => void;
}) {
  const [view, setView] = useState<Viewport>({ bbox: [-80, -40, -30, 15], zoom: 4 });
  const [hours, setHours] = useState(24);
  const [layer, setLayer] = useState("risk");
  const [levels, setLevels] = useState<Level[]>(levelsAll);
  const [intensities, setIntensities] = useState<Intensity[]>(intensityAll);
  const [basemap, setBasemap] = useState("blue");
  const [state, setState] = useState<BrazilState | ''>('');
  const [drawMode, setDrawMode] = useState("none");
  const [data, setData] = useState<RecentData | null>(null);
  const [demo, setDemo] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [reload, setReload] = useState(0);
  const [selected, setSelected] = useState<DetectionFeature | null>(null);
  const [focus, setFocus] = useState<{ center: [number, number]; nonce: number }>();
  const [all, setAll] = useState(false);
  const [priorityOpen, setPriorityOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<CalendarData | null>(null);
  const [historyError, setHistoryError] = useState("");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyDemo, setHistoryDemo] = useState(false);
  const historyRequest = useRef<AbortController | null>(null);
  const [coordsOpen, setCoordsOpen] = useState(false);
  const [lat, setLat] = useState("-3.1");
  const [lon, setLon] = useState("-60.2");
  const [radius, setRadius] = useState("50");
  const [copyStatus, setCopyStatus] = useState("");
  const [clock, setClock] = useState(Date.now());
  const summaryCallback = useRef(onRecentSummary);
  summaryCallback.current = onRecentSummary;
  useEffect(() => {
    const t = setInterval(() => setClock(Date.now()), 60000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();
    setData(null);
    setSelected(null);
    setLoading(true);
    setError("");
    const timer = setTimeout(async () => {
      const timeout = setTimeout(() => controller.abort("timeout"), 10000);
      try {
        const result = await fetchRecent(view, hours, controller.signal);
        if (!controller.signal.aborted) {
          setData(result);
          setDemo(false);
          if (hours === 24) summaryCallback.current?.(result, false);
        }
      } catch (e) {
        if (controller.signal.aborted && controller.signal.reason !== "timeout") return;
        setError(e instanceof RecentApiError ? e.message : "API unavailable.");
        const fallback = demoForWindow(view, hours);
        setData(fallback);
        setDemo(true);
        if (fallback) summaryCallback.current?.(fallback, true);
      } finally {
        clearTimeout(timeout);
        if (!controller.signal.aborted || controller.signal.reason === "timeout") setLoading(false);
      }
    }, 400);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [view, hours, active, reload]);
  useEffect(() => () => historyRequest.current?.abort(), []);
  const priorities = useMemo(
    () => (data ? priorityInState(priorityInView(data, view), state).filter((p) => levels.includes(p.alert_level)) : []),
    [data, view, levels, state],
  );
  const updated = data ? freshness(data.updated_at, clock) : null;
  const high = data ? highShare(data.features) : null;
  const cell =
    selected &&
    data?.alerts?.priority.find(
      (p) => p.h3 === selected.properties.alert_cell || p.h3 === selected.properties.h3,
    );
  const selectedCoords =
    cell?.center ??
    (selected?.geometry.type === "Point"
      ? (selected.geometry.coordinates.slice(0, 2) as [number, number])
      : undefined);
  const choose = (p: Priority) => {
    setPriorityOpen(false);
    const feature = data?.features.find(
      (f) => f.properties.h3 === p.h3 || f.properties.alert_cell === p.h3,
    );
    if (feature) setSelected(feature);
    else if (isValidCell(p.h3)) {
      const ring = cellToBoundary(p.h3, true);
      const first = ring[0];
      if (first)
        setSelected({
          type: "Feature",
          geometry: { type: "Polygon", coordinates: [[...ring, first]] },
          properties: { h3: p.h3, alert_cell: p.h3, alert_level: p.alert_level },
        });
    }
  };
  const zoom = (p: Priority) => {
    choose(p);
    setFocus({ center: p.center, nonce: Date.now() });
  };
  async function openHistory(area: AreaSelection) {
    historyRequest.current?.abort();
    const controller = new AbortController();
    historyRequest.current = controller;
    setHistoryOpen(true);
    setHistory(null);
    setHistoryDemo(false);
    setHistoryError("");
    onSelect(area);
    setHistoryLoading(true);
    const queryArea =
      area.type === "circle"
        ? {
            type: "geojson" as const,
            geometry: coordinateArea(area.latitude, area.longitude, area.radius_km),
          }
        : area;
    if (queryArea.type !== "geojson") {
      setHistoryError("Region history request fields are not supplied.");
      setHistoryLoading(false);
      return;
    }
    const timer = setTimeout(() => controller.abort("timeout"), 15000);
    try {
      const response = await fetchAreaHistory(queryArea.geometry, controller.signal);
      if (controller.signal.aborted) return;
      const candidate = response.calendar ?? response;
      if (
        !Array.isArray(candidate.months) ||
        !Array.isArray(candidate.years) ||
        !Array.isArray(candidate.seasonality)
      )
        throw Error("The history response does not include the documented monthly record.");
      setHistory(candidate as CalendarData);
      setHistoryError(
        typeof response.message === "string"
          ? response.message
          : typeof response.coverage?.message === "string"
            ? response.coverage.message
            : "",
      );
    } catch (e) {
      if (controller.signal.aborted && controller.signal.reason !== "timeout") return;
      setHistoryError(e instanceof Error ? e.message : "Area history unavailable.");
    } finally {
      clearTimeout(timer);
      if (!controller.signal.aborted || controller.signal.reason === "timeout")
        setHistoryLoading(false);
    }
  }
  const areaChosen = (area: AreaSelection | null) => {
    onSelect(area);
    if (area) {
      setDrawMode("none");
      void openHistory(area);
    }
  };
  const badge = demo ? <span className="demo-badge">Demo data</span> : null;
  return (
    <div className="recent-workspace">
      <AreaMap
        immersive
        operational
        active={active}
        resetForHandoff={resetForHandoff}
        onReady={onReady}
        selection={selection}
        onSelect={areaChosen}
        recent={data}
        onViewport={setView}
        onCell={(feature) => {
          setPriorityOpen(false);
          setSelected(feature);
        }}
        focus={focus}
        layer={layer}
        levels={levels}
        intensities={intensities}
        basemap={basemap}
        drawMode={drawMode}
        {...(state && STATE_BOUNDS[state] ? { stateBounds: STATE_BOUNDS[state] } : {})}
      />
      <header className="recent-topbar">
        <strong>
          firesync<span>.</span>
        </strong>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="recent-status"
              aria-label="Data status and information"
              title="Data status and information"
            >
              {loading ? <LoaderCircle size={15} className="spin" /> : <Info size={15} />}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="recent-popover" align="start">
            <strong>
              {demo ? "Demo data · API unavailable" : "Recent detections · near real time"}
            </strong>
            <p>
              {data
                ? `${number(data.total_detections)} detections · ${high == null ? "High intensity unavailable" : `${share(high)} high intensity`}`
                : demo && hours !== 24 ? "No demo data for this window" : "Recent detections unavailable"}
            </p>
            {data?.alerts && <p>Data through {data.alerts.data_through} · UTC</p>}
            {error && (
              <p role="status">
                {error}
                <Button variant="ghost" size="sm" onClick={() => setReload((v) => v + 1)}>
                  Retry
                </Button>
              </p>
            )}
            <p>
              {data
                ? `${new Date(data.updated_at).toUTCString()} · UTC`
                : "No update time available."}
            </p>
            <p>Recent detections are near real time and may be revised.</p>
            {updated?.state !== "current" && updated && (
              <p>{updated.state === "outdated" ? "Data is outdated" : "Data may be delayed"}</p>
            )}
            <p>Sensor attribution must be confirmed against the API metadata.</p>
          </PopoverContent>
        </Popover>
        {badge}
        <Button
          variant="ghost"
          size="icon"
          onClick={onReturn}
          aria-label="Back to globe"
          title="Back to globe"
        >
          <Globe2 size={18} />
        </Button>
      </header>
      <div className="recent-indicators" aria-busy={loading}>
        <Button
          variant="ghost"
          className="recent-metric"
          aria-label="Priority areas"
          aria-expanded={priorityOpen}
          onClick={() => {
            setSelected(null);
            setPriorityOpen((value) => !value);
          }}
        >
          <span className="recent-level-dot" />
          <strong>
            {loading
              ? "—"
              : data?.alerts
                ? number(priorities.filter((p) => p.alert_level === "critical").length)
                : "—"}
          </strong>
          <span>Critical</span>
          <ChevronDown size={13} />
        </Button>
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" className="recent-metric" aria-label="Detection summary">
              <strong>{loading ? "—" : data ? number(data.total_detections) : "—"}</strong>
              <span>Detections</span>
              <ChevronDown size={13} />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="recent-popover" align="start">
            {badge}
            <h2>
              Recent detections · {hours / 24} {hours === 24 ? "day" : "days"}
            </h2>
            <p>
              {data
                ? `${number(data.total_detections)} detections in this map view.`
                : "Detections unavailable for this view."}
            </p>
            <p>High intensity: {high == null ? "unavailable" : share(high)} of detections.</p>
            <p>
              {demo
                ? "Supplied example cell only, not production observations."
                : "Satellite detections are not a count of individual fires."}
            </p>
            <p>Updated {updated?.relative ?? "time unavailable"}.</p>
          </PopoverContent>
        </Popover>
      </div>
      <div className="recent-controls">
        <div className="recent-window" role="group" aria-label="Recent activity window">
          {[
            { value: 24, label: "24 h" },
            { value: 72, label: "3 d" },
            { value: 168, label: "7 d" },
          ].map((window) => (
            <Button
              key={window.value}
              variant="ghost"
              aria-pressed={hours === window.value}
              onClick={() => setHours(window.value)}
            >
              {window.label}
            </Button>
          ))}
        </div>
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="ghost" size="icon" aria-label="Map layers" title="Map layers">
              <Layers size={18} />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="recent-popover recent-filter-panel" side="top">
            <label>
              Map layer
              <select value={layer} onChange={(e) => setLayer(e.target.value)}>
                <option value="risk">Risk level</option>
                <option value="count">Detection count</option>
                <option value="intensity">Intensity</option>
              </select>
            </label>
            <p>Risk horizon: next 14 days. Based on past frequency, not a prediction.</p>
            <p>Normal does not mean safe.</p>
            <Link to="/method">Method & uncertainty</Link>
          </PopoverContent>
        </Popover>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              size="icon"
              aria-label="Map filters and area tools"
              title="Map filters and area tools"
            >
              <SlidersHorizontal size={18} />
            </Button>
          </PopoverTrigger>
          <PopoverContent className="recent-popover recent-filter-panel" side="top" align="end">
            <label>
              State
              <select aria-label="State" value={state} onChange={event => setState(event.target.value as BrazilState | '')}>
                <option value="">All Brazil</option>
                {BRAZIL_STATES.map(name => <option key={name}>{name}</option>)}
              </select>
            </label>
            {state && !STATE_BOUNDS[state] && <p role="status">Official state bounds pending confirmation. Map position is unchanged.</p>}
            <fieldset>
              <legend>Level filter</legend>
              {levelsAll.map((v) => (
                <Button
                  key={v}
                  variant="outline"
                  aria-pressed={levels.includes(v)}
                  onClick={() =>
                    setLevels((old) => (old.includes(v) ? old.filter((x) => x !== v) : [...old, v]))
                  }
                >
                  {v}
                </Button>
              ))}
            </fieldset>
            <fieldset>
              <legend>Intensity filter</legend>
              {intensityAll.map((v) => (
                <Button
                  key={v}
                  variant="outline"
                  aria-pressed={intensities.includes(v)}
                  onClick={() =>
                    setIntensities((old) =>
                      old.includes(v) ? old.filter((x) => x !== v) : [...old, v],
                    )
                  }
                >
                  {v}
                </Button>
              ))}
            </fieldset>
            <label>
              Base map
              <select value={basemap} onChange={(e) => setBasemap(e.target.value)}>
                <option value="blue">Blue marble</option>
                <option value="night">Satellite-night</option>
                <option value="plain">Plain</option>
              </select>
            </label>
            <label>
              Draw area
              <select value={drawMode} onChange={(e) => setDrawMode(e.target.value)}>
                <option value="none">None</option>
                <option value="Polygon">Polygon</option>
                <option value="Rectangle">Rectangle</option>
                <option value="Circle">Circle</option>
              </select>
            </label>
            <Button variant="outline" onClick={() => setCoordsOpen(true)}>
              <Crosshair />
              Enter coordinates
            </Button>
            {selection && (
              <Button variant="ghost" onClick={() => onSelect(null)}>
                <X />
                Clear area
              </Button>
            )}
          </PopoverContent>
        </Popover>
      </div>
      {priorityOpen && (
        <aside className="recent-priority" aria-label="Priority areas panel">
          <Button
            variant="ghost"
            size="icon"
            className="recent-panel-close"
            aria-label="Close priority areas"
            onClick={() => setPriorityOpen(false)}
          >
            <X size={18} />
          </Button>
          <h2>Priority areas {badge}</h2>
          {state && <p>{STATE_BOUNDS[state] ? 'Approximate: by state bounding box.' : 'State priority areas unavailable until official bounds are confirmed.'}</p>}
          {loading ? (
            <p>
              <LoaderCircle className="spin" size={16} /> Loading recent detections…
            </p>
          ) : error ? (
            <div className="recent-notice" role="status">
              <p>
                {error.startsWith("Too many")
                  ? error
                  : demo
                    ? "Demo data · API unavailable."
                    : error}
              </p>
              <Button variant="outline" size="sm" onClick={() => setReload((v) => v + 1)}>
                Retry
              </Button>
            </div>
          ) : null}
          {updated && updated.state !== "current" && (
            <p className="recent-delay">
              {updated.state === "outdated" ? "Data is outdated" : "Data may be delayed"}
            </p>
          )}
          {!loading && !data && (
            <p>{demo ? 'No demo data for this window' : 'Recent detections unavailable.'} Choose 24 hours or retry the API.</p>
          )}
          {data && !data.alerts && <p>Risk levels are not available for this view. Zoom in.</p>}
          {data && !data.total_detections && (
            <p>
              No detections in the last{" "}
              {hours === 24 ? "24 hours" : hours === 72 ? "3 days" : "7 days"} in this view.
            </p>
          )}
          {priorities.slice(0, all ? undefined : 20).map((p, i) => (
            <article key={p.h3} className="priority-cell">
              {badge}
              <Button variant="ghost" className="priority-select" onClick={() => choose(p)}>
                <span>{i + 1}</span>
                <span className={`risk-badge risk-${p.alert_level}`}>
                  {p.alert_level === "critical" ? "! " : p.alert_level === "attention" ? "△ " : ""}
                  {p.alert_level}
                </span>
              </Button>
              <strong>
                {demo ? `${number(data?.features.find(feature => feature.properties.h3 === p.h3)?.properties.detections)} detections in the last 24 hours` : `${number(p.detections_7d)} detections in 7 days`}
                {!demo && <small>(typical: {number(p.typical_median)})</small>}
              </strong>

              <div className="priority-location">
                <span>
                  {p.center[1].toFixed(2)}, {p.center[0].toFixed(2)}
                </span>
                <Button variant="outline" size="sm" onClick={() => zoom(p)}>
                  Zoom to
                </Button>
              </div>
            </article>
          ))}
          {priorities.length > 20 && (
            <Button variant="ghost" onClick={() => setAll(!all)}>
              {all ? "Show top 20" : "Show all"}
            </Button>
          )}
          {demo && (
            <p className="recent-demo-note">
              The supplied mock includes one cell. Its national total of 3,833 has no complete
              geometry and is not used as a viewport count.
            </p>
          )}
        </aside>
      )}
      {selected && (
        <aside className="recent-cell-detail">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Close cell details"
            onClick={() => setSelected(null)}
          >
            <X size={18} />
          </Button>
          {badge}
          <h2>Cell detail</h2>
          {cell && data && (
            <>
              <span className={`risk-badge risk-${cell.alert_level}`}>{cell.alert_level}</span>
              <p>
                {demo ? `${number(selected.properties.detections)} detections in the last 24 hours.` : `${number(cell.detections_7d)} detections in the last 7 days; typical for this time of year: ${number(cell.typical_median)}. Usual range unavailable in this response.`}
              </p>
              <RiskSentence cell={cell} data={data} />
            </>
          )}
          <div className="intensity-summary">
            {(["low", "medium", "high"] as const).map((k) => (
              <span key={k} className={`intensity-${k}`}>
                {k}: {number(selected.properties[`n_${k}`])}
              </span>
            ))}
          </div>
          <p>
            Intensity helps prioritize where to look. It does not replace field information, wind or
            the advance of the fire front.
          </p>
          {selectedCoords && (
            <div className="cell-coordinate-actions">
              <span>
                {selectedCoords[1].toFixed(3)}, {selectedCoords[0].toFixed(3)}
              </span>
              <Button
                variant="outline"
                size="icon"
                title="Copy coordinates"
                aria-label="Copy coordinates"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(
                      `${selectedCoords[1]}, ${selectedCoords[0]}`,
                    );
                    setCopyStatus("Coordinates copied.");
                  } catch {
                    setCopyStatus("Copy unavailable. Select the displayed coordinates.");
                  }
                }}
              >
                <Copy size={16} />
              </Button>
              <a
                href={`https://www.google.com/maps?q=${selectedCoords[1]},${selectedCoords[0]}`}
                target="_blank"
                rel="noreferrer"
              >
                Open in maps
              </a>
              <span role="status">{copyStatus}</span>
            </div>
          )}
          <Button
            onClick={() => void openHistory({ type: "geojson", geometry: selected.geometry })}
          >
            Open full history
          </Button>
        </aside>
      )}
      <details className="recent-legend">
        <summary>Legend</summary>
        <p>Risk, next 14 days, from past frequency</p>
        <p>
          <span className="risk-badge risk-critical">! Critical</span>{" "}
          <span className="risk-badge risk-attention">△ Attention</span>{" "}
          <span className="risk-badge risk-normal">Normal</span>
        </p>
        <p>Level = last 7 days compared with the same season in past years.</p>
        <p>Intensity: Low · Medium · High</p>
        <p>Normal does not mean safe.</p>
      </details>
      <div className="recent-map-credit">
        Data: NASA FIRMS · <Link to="/data">Data & credits</Link>
      </div>
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="recent-history-dialog">
          <DialogTitle>
            Area history {historyDemo && <span className="demo-badge">Demo data</span>}
          </DialogTitle>
          <DialogDescription>
            {historyDemo
              ? "Separate example area — not the selected cell or drawn area."
              : "Monthly record for the selected geometry."}
          </DialogDescription>
          {historyLoading && (
            <p>
              <LoaderCircle className="spin" />
              Loading area history…
            </p>
          )}
          {historyError && <p role="status">{historyError}</p>}
          {!history && !historyLoading && (
            <Button
              variant="outline"
              onClick={() => {
                setHistory(demoData);
                setHistoryDemo(true);
                setHistoryError("");
              }}
            >
              Demo — example area
            </Button>
          )}
          {history && <Calendar data={history} demo={historyDemo} />}
          <Button
            variant="outline"
            onClick={() =>
              setHistoryError(
                "The export request envelope has not been supplied. The audit ZIP cannot be requested safely yet.",
              )
            }
          >
            <Download />
            Download data
          </Button>
        </DialogContent>
      </Dialog>
      <Dialog open={coordsOpen} onOpenChange={setCoordsOpen}>
        <DialogContent className="recent-coordinate-dialog">
          <DialogTitle>Enter coordinates</DialogTitle>
          <DialogDescription>Radius: 1–200 km. Coordinates in decimal degrees.</DialogDescription>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setCoordsOpen(false);
              void openHistory({
                type: "circle",
                latitude: Number(lat),
                longitude: Number(lon),
                radius_km: Number(radius),
              });
            }}
          >
            <label>
              Latitude
              <input
                type="number"
                min={-90}
                max={90}
                step="any"
                required
                value={lat}
                onChange={(e) => setLat(e.target.value)}
              />
            </label>
            <label>
              Longitude
              <input
                type="number"
                min={-180}
                max={180}
                step="any"
                required
                value={lon}
                onChange={(e) => setLon(e.target.value)}
              />
            </label>
            <label>
              Radius (km)
              <input
                type="number"
                min={1}
                max={200}
                step="any"
                required
                value={radius}
                onChange={(e) => setRadius(e.target.value)}
              />
            </label>
            <Button type="submit">Open area history</Button>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
