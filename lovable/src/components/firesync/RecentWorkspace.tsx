import { cellToBoundary, isValidCell } from "h3-js";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";
import {
  Globe2,
  Copy,
  Crosshair,
  Download,
  LoaderCircle,
  ChevronDown,
  Clock,
  CalendarDays,
  BarChart3,
  MapPin,
  Pencil,
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
  type RiskTier,
  TIERS,
  TIER_LABEL,
  TIER_COLOR,
  COUNT_GRADIENT,
  type Level,
  type Priority,
  type RecentData,
  type Viewport,
} from "@/lib/recent-data";
import { fetchAreaHistory, fetchRecent, RecentApiError } from "@/lib/recent-api";
import { BRAZIL_STATES, STATE_BOUNDS, priorityInState, type BrazilState } from '@/lib/brazil-states';
const brasilia = (iso: string) =>
  new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "America/Sao_Paulo" }).format(new Date(iso));
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
  onNext,
}: {
  active: boolean;
  resetForHandoff: boolean;
  onReady: () => void;
  onReturn: () => void;
  selection: AreaSelection | null;
  onSelect: (s: AreaSelection | null) => void;
  onRecentSummary?: (data: RecentData, demo: boolean) => void;
  onNext?: () => void;
}) {
  const [view, setView] = useState<Viewport>({ bbox: [-80, -40, -30, 15], zoom: 4 });
  const [hours, setHours] = useState(24);
  const [mode, setMode] = useState<"fire" | "risk">("fire");
  const layer = mode === "fire" ? "intensity" : "risk";
  const [levels, setLevels] = useState<Level[]>(levelsAll);
  const [intensities, setIntensities] = useState<Intensity[]>(intensityAll);
  const [tiers, setTiers] = useState<RiskTier[]>(TIERS);
  const [quietOnly, setQuietOnly] = useState(false);
  const [legendOpen, setLegendOpen] = useState(() => typeof window === "undefined" || window.innerHeight >= 760);
  const [filtersOpen, setFiltersOpen] = useState(() => typeof window === "undefined" || window.innerWidth >= 900);
  const [shown, setShown] = useState(10);
  const [groupOpen, setGroupOpen] = useState<Record<string, boolean>>({});
  const [groupShown, setGroupShown] = useState<Record<string, number>>({});
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
    () => (data ? priorityInState(priorityInView(data, view), state).filter((p) => (mode === "risk" ? (!p.risk_tier || tiers.includes(p.risk_tier)) && (!quietOnly || !(p.detections_7d > 0)) : levels.includes(p.alert_level))) : []),
    [data, view, levels, state, mode, tiers, quietOnly],
  );
  const filterCount =
    mode === "fire"
      ? (intensities.length < 3 ? intensities.length : 0) + (levels.length < 3 ? levels.length : 0)
      : (tiers.length < 4 ? tiers.length : 0) + (quietOnly ? 1 : 0);
  useEffect(() => {
    setShown(10);
    setGroupShown({});
  }, [mode, view, tiers, levels, quietOnly]);
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
  const renderCard = (p: Priority) => (
              <button key={p.h3} className="fs-card" onClick={() => zoom(p)}>
                <strong>
                  Area near {p.center[1].toFixed(1)}, {p.center[0].toFixed(1)}
                </strong>
                {mode === "risk" ? (
                  <span className="fs-line">
                    Next 14 days{" "}
                    {p.risk_tier ? (
                      <b className="fs-chip" style={{ background: TIER_COLOR[p.risk_tier], color: p.risk_tier === "medium" || p.risk_tier === "lower" ? "#222" : "#fff" }}>
                        {TIER_LABEL[p.risk_tier]}
                      </b>
                    ) : (
                      "unavailable"
                    )}
                  </span>
                ) : (
                  <span className="fs-line">
                    Compared with usual{" "}
                    <b className={`fs-chip fs-chip-${p.alert_level}`}>{p.alert_level === "normal" ? "Usual" : p.alert_level[0]!.toUpperCase() + p.alert_level.slice(1)}</b>
                  </span>
                )}
                <span className="fs-line">
                  Right now{" "}
                  {p.detections_7d > 0 ? `${number(p.detections_7d)} hot spots in 7 days (usually ${number(p.typical_median)})` : "No hot spots in the last 24 h"}
                </span>
                {p.detections_7d > p.typical_median && <span className="fs-tag">More than usual for the season</span>}
              </button>
  );
    const badge = demo ? <span className="demo-badge">Demo data</span> : null;
  return (
    <div className="recent-workspace">
      <AreaMap
        immersive
        operational
        active={active}
        resetForHandoff={resetForHandoff}
        onReady={onReady}
        onMinZoomOut={onReturn}
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
        tiers={tiers}
        quietOnly={quietOnly}
        {...(state && STATE_BOUNDS[state] ? { stateBounds: STATE_BOUNDS[state] } : {})}
      />
      <header className="fs-brand">
        <strong>
          firesync<span>.</span>
        </strong>
        {badge}
        <Button variant="ghost" size="icon" onClick={onReturn} aria-label="Back to globe" title="Back to globe">
          <Globe2 size={16} />
        </Button>
      </header>
      <nav className="fs-toolbar" aria-label="Map view and area">
        <div className="fs-tabs" role="tablist" aria-label="Map view">
          {([
            ["fire", "Fire now"],
            ["risk", "Risk, next 14 days"],
          ] as const).map(([value, label]) => (
            <button key={value} role="tab" aria-selected={mode === value} onClick={() => setMode(value)}>
              {label}
            </button>
          ))}
        </div>
        <span className="fs-area-label">Area</span>
        <Popover>
          <PopoverTrigger asChild>
            <button className="fs-tool">State: {state || "All Brazil"}</button>
          </PopoverTrigger>
          <PopoverContent className="recent-popover recent-filter-panel" align="center">
            <label>
              State
              <select aria-label="State" value={state} onChange={(event) => setState(event.target.value as BrazilState | "")}>
                <option value="">All Brazil</option>
                {BRAZIL_STATES.map((name) => (
                  <option key={name}>{name}</option>
                ))}
              </select>
            </label>
            {state && !STATE_BOUNDS[state] && <p role="status">Official state bounds pending confirmation. Map position is unchanged.</p>}
          </PopoverContent>
        </Popover>
        <Popover>
          <PopoverTrigger asChild>
            <button className="fs-tool" aria-pressed={drawMode !== "none"}>
              <Pencil size={14} /> Draw area
            </button>
          </PopoverTrigger>
          <PopoverContent className="recent-popover recent-filter-panel" align="center">
            <fieldset>
              <legend>Draw an area on the map</legend>
              {["Polygon", "Rectangle", "Circle"].map((shape) => (
                <Button key={shape} variant="outline" aria-pressed={drawMode === shape} onClick={() => setDrawMode(drawMode === shape ? "none" : shape)}>
                  {shape}
                </Button>
              ))}
            </fieldset>
            {selection && (
              <Button variant="ghost" onClick={() => onSelect(null)}>
                <X /> Clear area
              </Button>
            )}
          </PopoverContent>
        </Popover>
        <button className="fs-tool" onClick={() => setCoordsOpen(true)}>
          <MapPin size={14} /> Coordinates
        </button>
      </nav>
      <section className="fs-filters" aria-label="Filters">
        <button className="fs-filters-head" aria-expanded={filtersOpen} onClick={() => setFiltersOpen((v) => !v)}>
          <strong>Filters</strong>
          {filterCount > 0 && <span className="fs-count">{filterCount}</span>}
          <ChevronDown size={14} className={filtersOpen ? "open" : ""} />
        </button>
        {filtersOpen && mode === "fire" && (
          <>
            <p className="fs-group">Fire strength</p>
            {intensityAll
              .slice()
              .reverse()
              .map((v) => (
                <button key={v} className="fs-row" aria-pressed={intensities.includes(v)} onClick={() => setIntensities((old) => (old.includes(v) ? old.filter((x) => x !== v) : [...old, v]))}>
                  <i className={`fs-dot fs-dot-${v}`} /> {v[0]!.toUpperCase() + v.slice(1)}
                </button>
              ))}
            <p className="fs-group">Compared with usual (icon on the map)</p>
            {levelsAll.map((v) => (
              <button key={v} className="fs-row" aria-pressed={levels.includes(v)} onClick={() => setLevels((old) => (old.includes(v) ? old.filter((x) => x !== v) : [...old, v]))}>
                {v === "normal" ? <i className="fs-ring fs-ring-normal" /> : <i className={`fs-icon fs-icon-${v}`}>!</i>} {v === "normal" ? "Usual (no icon)" : v[0]!.toUpperCase() + v.slice(1)}
              </button>
            ))}
          </>
        )}
        {filtersOpen && mode === "risk" && (
          <>
            <p className="fs-group">Risk tier</p>
            {TIERS.map((v) => (
              <button key={v} className="fs-row" aria-pressed={tiers.includes(v)} onClick={() => setTiers((old) => (old.includes(v) ? old.filter((x) => x !== v) : [...old, v]))}>
                <i className="fs-swatch" style={{ background: TIER_COLOR[v] }} /> {TIER_LABEL[v]}
              </button>
            ))}
            <p className="fs-group">Cells</p>
            <button className="fs-row" aria-pressed={quietOnly} onClick={() => setQuietOnly((v) => !v)}>
              <i className="fs-ring fs-ring-quiet" /> No hot spots now
            </button>
          </>
        )}
      </section>
      <div className="fs-right">
      <section className="fs-status" role="status" aria-label="Data status">
        <strong>
          {mode === "risk"
            ? data?.alerts?.risk
              ? `Risk calculated ${brasilia(data.alerts.risk.scored_at)} (Brasília)`
              : "Risk not available for this view"
            : updated
              ? `Data updated ${updated.relative}`
              : "Update time unavailable"}
        </strong>
        <span>
          {mode === "risk" ? <CalendarDays size={13} /> : <Clock size={13} />}
          {mode === "risk" ? "Looks 14 days ahead" : "Hot spots seen in the last 24 hours"}
        </span>
        <span>{mode === "risk" ? "Based on how often fire followed in the past. Not a guarantee." : "Recent hot spots can still change"}</span>
        {error && (
          <span>
            {error}{" "}
            <button className="fs-link" onClick={() => setReload((v) => v + 1)}>
              Retry
            </button>
          </span>
        )}
        {updated && updated.state !== "current" && mode === "fire" && <span className="recent-delay">{updated.state === "outdated" ? "Data is outdated" : "Data may be delayed"}</span>}
      </section>
      <button
        className="fs-indicators"
        aria-expanded={priorityOpen}
        onClick={() => {
          setSelected(null);
          setPriorityOpen((v) => !v);
        }}
      >
        <BarChart3 size={15} /> Indicators
        <span className="fs-count">{loading ? "…" : priorities.length}</span>
      </button>
      {priorityOpen && (
        <aside className="fs-panel" aria-label="Where to look first">
          <Button variant="ghost" size="icon" className="recent-panel-close" aria-label="Close indicators" onClick={() => setPriorityOpen(false)}>
            <X size={18} />
          </Button>
          <h2>
            Where to look first {badge}
          </h2>
          {data?.alerts && (
            <p className="fs-sub">
              {mode === "risk"
                ? `${number(priorities.filter((p) => p.risk_tier === "very_high").length)} very high · ${number(priorities.filter((p) => p.risk_tier === "high").length)} high areas in view`
                : `${number(priorities.filter((p) => p.alert_level === "critical").length)} critical · ${number(priorities.filter((p) => p.alert_level === "attention").length)} attention areas in view`}
            </p>
          )}
          {state && <p className="fs-sub">{STATE_BOUNDS[state] ? "Approximate: by state bounding box." : "State areas unavailable until official bounds are confirmed."}</p>}
          {loading && (
            <p>
              <LoaderCircle className="spin" size={16} /> Loading…
            </p>
          )}
          {!loading && error && (
            <div className="recent-notice" role="status">
              <p>{demo ? "Demo data · API unavailable." : error}</p>
              <Button variant="outline" size="sm" onClick={() => setReload((v) => v + 1)}>
                Retry
              </Button>
            </div>
          )}
          {data && !data.alerts && <p>Risk levels are not available for this view. Zoom in.</p>}
          {mode === "risk" ? (
            TIERS.map((t) => {
              const group = priorities.filter((p) => p.risk_tier === t);
              if (!group.length) return null;
              const open = groupOpen[t] ?? (t === "very_high" || t === "high");
              const limit = groupShown[t] ?? 10;
              return (
                <section key={t} className="fs-group-block">
                  <button className="fs-group-head" aria-expanded={open} onClick={() => setGroupOpen((o) => ({ ...o, [t]: !open }))}>
                    <i className="fs-swatch" style={{ background: TIER_COLOR[t] }} />
                    <strong>{TIER_LABEL[t]}</strong>
                    <span>{number(group.length)} areas</span>
                    <ChevronDown size={14} className={open ? "open" : ""} />
                  </button>
                  {open && (
                    <>
                      {group.slice(0, limit).map(renderCard)}
                      <p className="fs-sub">
                        Showing {Math.min(limit, group.length)} of {number(group.length)} areas (10 at a time)
                      </p>
                      {group.length > limit && (
                        <Button variant="outline" className="fs-more" onClick={() => setGroupShown((g) => ({ ...g, [t]: limit + 10 }))}>
                          See 10 more
                        </Button>
                      )}
                    </>
                  )}
                </section>
              );
            })
          ) : (
            <>
              {priorities.slice(0, shown).map(renderCard)}
              {!loading && data?.alerts && (
                <p className="fs-sub">
                  Showing {Math.min(shown, priorities.length)} of {number(priorities.length)} areas (10 at a time)
                </p>
              )}
              {priorities.length > shown && (
                <Button variant="outline" className="fs-more" onClick={() => setShown((n) => n + 10)}>
                  See 10 more
                </Button>
              )}
            </>
          )}
        </aside>
      )}
      </div>
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
      <section className={`fs-legend ${legendOpen ? "is-open" : ""}`} aria-label="Legend">
        <button className="fs-legend-head" aria-expanded={legendOpen} onClick={() => setLegendOpen((v) => !v)}>
          <span>Legend</span>
          <ChevronDown size={14} className={legendOpen ? "open" : ""} />
        </button>
        {legendOpen && (
          <>
        {mode === "fire" ? (
          <>
            <h3>
              <Clock size={13} /> Heat concentration · last 24 h
            </h3>
            <div className="fs-gradient" style={{ background: COUNT_GRADIENT }} />
            <div className="fs-gradient-labels">
              <span>1</span>
              <span>10</span>
              <span>100+</span>
            </div>
            <small>Hot spots per area: the more yellow, the more.</small>
            <p className="fs-sym-title">More than usual for the season</p>
            <p className="fs-sym">
              <i className="fs-icon fs-icon-critical" title="Strongly above the usual for this time of year">!</i> Critical
              <i className="fs-icon fs-icon-attention" title="Above the usual for this time of year">!</i> Attention
            </p>
            <small>No icon = usual. Icons show when you zoom in.</small>
          </>
        ) : (
          <>
            <h3>Fire risk, next 14 days</h3>
            {TIERS.map((t) => {
              const sh = data?.alerts?.risk?.tiers.find((x) => x.tier === t)?.historical_share;
              return (
                <p key={t}>
                  <i className="fs-swatch" style={{ background: TIER_COLOR[t] }} /> {TIER_LABEL[t]}
                  {sh != null && ` · fire followed in ${Math.round(sh * 100)}% of past cases`}
                </p>
              );
            })}
            <small>"More than usual" = above this time of year.</small>
          </>
        )}
          </>
        )}
      </section>
      {onNext && (
        <button className="fs-next" onClick={onNext} aria-label="Scroll down to read more about firesync" title="Read more about firesync">
          <ChevronDown size={20} />
        </button>
      )}
      <footer className="fs-footnote">
        {mode === "fire" ? (
          <span>Recent hot spots (NASA FIRMS, VIIRS) can still change. Usual does not mean safe.{demo && " Demo data."}</span>
        ) : (
          <span>
            Tiers show how often significant fire followed in past data (Brazil, 2021–2024):{" "}
            {TIERS.map((t) => {
              const sh = data?.alerts?.risk?.tiers.find((x) => x.tier === t)?.historical_share;
              return sh != null ? `${TIER_LABEL[t]} ${Math.round(sh * 100)}%` : null;
            })
              .filter(Boolean)
              .join(" · ")}
            . {data?.alerts?.risk && `Calculated ${brasilia(data.alerts.risk.scored_at)} (Brasília).`}
            {demo && " Demo data."}{" "}
            <Link to="/method">How reliable is this?</Link>
          </span>
        )}
        <span>
          Data: NASA FIRMS · <Link to="/data">Data & credits</Link>
        </span>
      </footer>
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
