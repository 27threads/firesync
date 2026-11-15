import { useEffect, useId, useState, type FormEvent } from 'react';
import type { AreaInput, RegionOption } from '../api/types';
import type { ApiStatus, Period, Selection } from '../state/useExplorer';
import { DEFAULT_RADIUS_KM, DEFAULT_START_MONTH, validatePeriod, validatePointInput, type PointValidationErrors } from './areaPeriodModel';

interface SelectionPanelProps {
  regions: RegionOption[];
  apiStatus: ApiStatus;
  selection: Selection;
  period: Period;
  lastMonth: string;
  onSelectArea: (area: AreaInput) => void;
  onSetPeriod: (period: Period) => void;
  onShowExample: () => void;
}

function isNarrow(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia('(max-width: 760px)').matches
    : false;
}

export function SelectionPanel({
  regions,
  apiStatus,
  selection,
  period,
  lastMonth,
  onSelectArea,
  onSetPeriod,
  onShowExample,
}: SelectionPanelProps) {
  const uid = useId();
  const [open, setOpen] = useState(true);
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [radius, setRadius] = useState(String(DEFAULT_RADIUS_KM));
  const [pointErrors, setPointErrors] = useState<PointValidationErrors>({});
  const [start, setStart] = useState(period.start);
  const [end, setEnd] = useState(period.end);
  const [periodError, setPeriodError] = useState<string | null>(null);

  useEffect(() => {
    setStart(period.start);
    setEnd(period.end);
  }, [period.start, period.end]);

  // No celular, o painel recolhe depois de uma escolha para devolver espaço ao mapa e ao resumo.
  const collapseOnNarrow = () => {
    if (isNarrow()) setOpen(false);
  };

  const regionValue = selection.area?.type === 'region' ? String(selection.area.region_id) : '';

  function submitPoint(event: FormEvent) {
    event.preventDefault();
    const result = validatePointInput(lat, lon, radius);
    if (!result.ok) {
      setPointErrors(result.errors);
      return;
    }
    setPointErrors({});
    onSelectArea(result.value);
    collapseOnNarrow();
  }

  function submitPeriod(event: FormEvent) {
    event.preventDefault();
    const result = validatePeriod(start, end, lastMonth);
    if (!result.ok) {
      setPeriodError(result.error);
      return;
    }
    setPeriodError(null);
    onSetPeriod(result.value);
  }

  return (
    <section className="controls" data-open={open} aria-label="Area and period">
      <button
        type="button"
        className="controls__toggle"
        aria-expanded={open}
        aria-controls={`${uid}-body`}
        onClick={() => setOpen((v) => !v)}
      >
        <span>Area and period</span>
        <span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      <div className="controls__body" id={`${uid}-body`}>
        <div className="controls__group">
          <button
            type="button"
            className="controls__example"
            onClick={() => {
              onShowExample();
              collapseOnNarrow();
            }}
          >
            Explore the example
          </button>
          <p className="controls__hint">Or choose a region, enter coordinates, or draw on the map.</p>
        </div>

        <div className="field">
          <label htmlFor={`${uid}-region`}>Region</label>
          <select
            id={`${uid}-region`}
            value={regionValue}
            disabled={regions.length === 0}
            onChange={(e) => {
              if (!e.target.value) return;
              onSelectArea({ type: 'region', region_id: Number(e.target.value) });
              collapseOnNarrow();
            }}
          >
            <option value="">
              {regions.length > 0 ? 'Choose a region' : apiStatus === 'checking' ? 'Loading regions…' : 'Regions need the API'}
            </option>
            {regions.map((r) => (
              <option key={r.region_id} value={r.region_id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>

        <form className="controls__group" onSubmit={submitPoint} noValidate>
          <span className="controls__legend">Point and radius</span>
          <div className="controls__row">
            <div className="field">
              <label htmlFor={`${uid}-lat`}>Latitude</label>
              <input id={`${uid}-lat`} inputMode="decimal" placeholder="-3.10" value={lat} onChange={(e) => setLat(e.target.value)} aria-invalid={!!pointErrors.lat} />
            </div>
            <div className="field">
              <label htmlFor={`${uid}-lon`}>Longitude</label>
              <input id={`${uid}-lon`} inputMode="decimal" placeholder="-60.00" value={lon} onChange={(e) => setLon(e.target.value)} aria-invalid={!!pointErrors.lon} />
            </div>
          </div>
          <div className="field">
            <label htmlFor={`${uid}-radius`}>Radius (km, 1 to 200)</label>
            <input id={`${uid}-radius`} inputMode="decimal" value={radius} onChange={(e) => setRadius(e.target.value)} aria-invalid={!!pointErrors.radius} />
          </div>
          {Object.values(pointErrors).map((msg) => (
            <span key={msg} className="field__error">
              {msg}
            </span>
          ))}
          <button type="submit" className="ctl-btn ctl-btn--primary">
            Show this area
          </button>
        </form>

        <form className="controls__group" onSubmit={submitPeriod} noValidate>
          <span className="controls__legend">Period (UTC)</span>
          <div className="controls__row">
            <div className="field">
              <label htmlFor={`${uid}-start`}>From</label>
              <input id={`${uid}-start`} type="month" min={DEFAULT_START_MONTH} max={lastMonth} value={start} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor={`${uid}-end`}>To</label>
              <input id={`${uid}-end`} type="month" min={DEFAULT_START_MONTH} max={lastMonth} value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
          </div>
          {periodError && <span className="field__error">{periodError}</span>}
          <button type="submit" className="ctl-btn">
            Apply period
          </button>
        </form>
      </div>
    </section>
  );
}
