import { useEffect, useState, type FormEvent } from 'react';
import type { AreaInput, CalendarRequest, GeoJsonPolygon, PointArea, RegionOption } from '../api/types';
import { AreaMap } from './AreaMap';
import {
  buildCalendarRequest,
  DEFAULT_RADIUS_KM,
  DEFAULT_START_MONTH,
  validatePeriod,
  validatePointInput,
  type PointValidationErrors,
} from './areaPeriodModel';

interface AreaPeriodControlsProps {
  regions: RegionOption[];
  lastMonth: string;
  activeArea: AreaInput | null;
  disabled?: boolean;
  onSubmitRequest: (request: CalendarRequest) => void;
}

export function AreaPeriodControls({
  regions,
  lastMonth,
  activeArea,
  disabled = false,
  onSubmitRequest,
}: AreaPeriodControlsProps) {
  const [selectedRegionId, setSelectedRegionId] = useState<string>('');
  const [focusBbox, setFocusBbox] = useState<[number, number, number, number] | null>(null);
  const [focusPoint, setFocusPoint] = useState<PointArea | null>(null);

  const [latInput, setLatInput] = useState<string>('');
  const [lonInput, setLonInput] = useState<string>('');
  const [radiusInput, setRadiusInput] = useState<string>(String(DEFAULT_RADIUS_KM));
  const [pointErrors, setPointErrors] = useState<PointValidationErrors>({});

  const [startMonth, setStartMonth] = useState<string>(DEFAULT_START_MONTH);
  const [endMonth, setEndMonth] = useState<string>(lastMonth);
  const [endEdited, setEndEdited] = useState<boolean>(false);
  const [periodError, setPeriodError] = useState<string | null>(null);

  useEffect(() => {
    if (!endEdited) {
      setEndMonth(lastMonth);
    }
  }, [lastMonth, endEdited]);

  const validateCurrentPeriod = (nextStart: string, nextEnd: string) => {
    const check = validatePeriod(nextStart, nextEnd, lastMonth);
    setPeriodError(check.ok ? null : check.error);
    return check;
  };

  const handleRegionChange = (rawId: string) => {
    setSelectedRegionId(rawId);
    if (!rawId) return;
    const regionId = Number(rawId);
    const matched = regions.find((r) => r.region_id === regionId);
    if (!matched) return;

    setFocusBbox(matched.bbox);
    setFocusPoint(null);
    setPointErrors({});

    const periodCheck = validateCurrentPeriod(startMonth, endMonth);
    if (!periodCheck.ok) return;

    const area: AreaInput = { type: 'region', region_id: matched.region_id };
    onSubmitRequest(buildCalendarRequest(area, periodCheck.value));
  };

  const handlePolygonSelect = (geometry: GeoJsonPolygon) => {
    setSelectedRegionId('');
    setFocusPoint(null);
    setPointErrors({});

    const periodCheck = validateCurrentPeriod(startMonth, endMonth);
    if (!periodCheck.ok) return;

    const area: AreaInput = { type: 'geojson', geometry };
    onSubmitRequest(buildCalendarRequest(area, periodCheck.value));
  };

  const handlePointSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const pointCheck = validatePointInput(latInput, lonInput, radiusInput);
    const periodCheck = validateCurrentPeriod(startMonth, endMonth);

    if (!pointCheck.ok) {
      setPointErrors(pointCheck.errors);
      return;
    }
    setPointErrors({});
    if (!periodCheck.ok) return;

    setSelectedRegionId('');
    setFocusBbox(null);
    setFocusPoint(pointCheck.value);
    onSubmitRequest(buildCalendarRequest(pointCheck.value, periodCheck.value));
  };

  const handlePeriodChange = (nextStart: string, nextEnd: string) => {
    const periodCheck = validateCurrentPeriod(nextStart, nextEnd);
    if (periodCheck.ok && activeArea) {
      onSubmitRequest(buildCalendarRequest(activeArea, periodCheck.value));
    }
  };

  return (
    <div className="area-controls">
      <div className="area-controls__top">
        <div className="control-field">
          <label htmlFor="region-select">Region (biome)</label>
          <select
            id="region-select"
            value={selectedRegionId}
            disabled={disabled}
            onChange={(e) => handleRegionChange(e.target.value)}
          >
            <option value="">Choose a region…</option>
            {regions.map((region) => (
              <option key={region.region_id} value={String(region.region_id)}>
                {region.name}
              </option>
            ))}
          </select>
        </div>

        <fieldset className="period-fieldset">
          <legend>Period (UTC months)</legend>
          <div className="period-fieldset__inputs">
            <div className="control-field">
              <label htmlFor="period-start">Start month</label>
              <input
                id="period-start"
                type="text"
                inputMode="numeric"
                maxLength={7}
                placeholder="YYYY-MM"
                value={startMonth}
                aria-invalid={periodError ? 'true' : undefined}
                aria-describedby={periodError ? 'period-error' : 'period-hint'}
                onChange={(e) => {
                  const next = e.target.value;
                  setStartMonth(next);
                  handlePeriodChange(next, endMonth);
                }}
              />
            </div>
            <div className="control-field">
              <label htmlFor="period-end">End month</label>
              <input
                id="period-end"
                type="text"
                inputMode="numeric"
                maxLength={7}
                placeholder="YYYY-MM"
                value={endMonth}
                aria-invalid={periodError ? 'true' : undefined}
                aria-describedby={periodError ? 'period-error' : 'period-hint'}
                onChange={(e) => {
                  const next = e.target.value;
                  setEndEdited(true);
                  setEndMonth(next);
                  handlePeriodChange(startMonth, next);
                }}
              />
            </div>
          </div>
          <p id="period-hint" className="control-hint">
            Available range: {DEFAULT_START_MONTH} to {lastMonth}.
          </p>
          {periodError && (
            <p id="period-error" className="field-error">
              {periodError}
            </p>
          )}
        </fieldset>
      </div>

      <AreaMap focusBbox={focusBbox} focusPoint={focusPoint} onSelectPolygon={handlePolygonSelect} />

      <form className="point-form" onSubmit={handlePointSubmit} noValidate>
        <fieldset className="point-fieldset">
          <legend>Or enter coordinates (keyboard alternative)</legend>
          <div className="point-fieldset__inputs">
            <div className="control-field">
              <label htmlFor="point-lat">Latitude</label>
              <input
                id="point-lat"
                type="text"
                inputMode="decimal"
                placeholder="e.g. -3.1"
                value={latInput}
                aria-invalid={pointErrors.lat ? 'true' : undefined}
                aria-describedby={pointErrors.lat ? 'point-lat-error' : undefined}
                onChange={(e) => setLatInput(e.target.value)}
              />
              {pointErrors.lat && (
                <p id="point-lat-error" className="field-error">
                  {pointErrors.lat}
                </p>
              )}
            </div>

            <div className="control-field">
              <label htmlFor="point-lon">Longitude</label>
              <input
                id="point-lon"
                type="text"
                inputMode="decimal"
                placeholder="e.g. -60.0"
                value={lonInput}
                aria-invalid={pointErrors.lon ? 'true' : undefined}
                aria-describedby={pointErrors.lon ? 'point-lon-error' : undefined}
                onChange={(e) => setLonInput(e.target.value)}
              />
              {pointErrors.lon && (
                <p id="point-lon-error" className="field-error">
                  {pointErrors.lon}
                </p>
              )}
            </div>

            <div className="control-field">
              <label htmlFor="point-radius">Radius (km)</label>
              <input
                id="point-radius"
                type="text"
                inputMode="decimal"
                value={radiusInput}
                aria-invalid={pointErrors.radius ? 'true' : undefined}
                aria-describedby={pointErrors.radius ? 'point-radius-error' : undefined}
                onChange={(e) => setRadiusInput(e.target.value)}
              />
              {pointErrors.radius && (
                <p id="point-radius-error" className="field-error">
                  {pointErrors.radius}
                </p>
              )}
            </div>

            <div className="point-form__submit">
              <button type="submit" className="map-btn map-btn--primary" disabled={disabled}>
                Show area
              </button>
            </div>
          </div>
        </fieldset>
      </form>
    </div>
  );
}
