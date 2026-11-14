import { useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { interpolateCividis } from 'd3-scale-chromatic';
import type { CalendarMonth } from '../api/types';
import { buildCalendar, MONTH_NAMES, type CalendarCell, type MonthPosition } from './calendarModel';
import { makeColorScale } from './colorScale';

const CELL_W = 36;
const CELL_H = 20;
const GAP = 2;
const LABEL_W = 44;
const HEADER_H = 22;
const RAMP_STOPS = 10;

const countFormat = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });

const cellX = (monthIndex: number) => LABEL_W + monthIndex * (CELL_W + GAP);
const rowY = (rowIndex: number) => HEADER_H + rowIndex * (CELL_H + GAP);

// Linha entre o último mês estimado (MODIS) e o primeiro observado (VIIRS), para ninguém ler a troca como aumento.
function sensorSwitchPath({ monthIndex }: MonthPosition, rowIndex: number): string {
  const top = rowY(rowIndex) - GAP / 2;
  const bottom = rowY(rowIndex + 1) - GAP / 2;
  const right = cellX(12) - GAP / 2;
  const left = cellX(0) - GAP / 2;
  const split = cellX(monthIndex) - GAP / 2;
  if (monthIndex === 0) return `M${left},${top} H${right}`;
  return `M${right},${top} H${split} V${bottom} H${left}`;
}

interface FireCalendarProps {
  months: CalendarMonth[];
}

export function FireCalendar({ months }: FireCalendarProps) {
  const calendar = useMemo(() => buildCalendar(months), [months]);
  const color = useMemo(
    () => (calendar.positiveExtent ? makeColorScale(calendar.positiveExtent) : null),
    [calendar.positiveExtent],
  );
  const [active, setActive] = useState<string>(() => lastRequestedKey(calendar.years.flatMap((r) => r.cells)));
  const [tooltip, setTooltip] = useState<CalendarCell | null>(null);
  const cellRefs = useRef(new Map<string, SVGRectElement>());

  const width = cellX(12);
  const height = rowY(calendar.years.length);
  const switchRow = calendar.sensorSwitch
    ? calendar.years.findIndex((row) => row.year === calendar.sensorSwitch!.year)
    : -1;

  function moveFocus(cell: CalendarCell, event: KeyboardEvent<SVGRectElement>) {
    const steps: Record<string, [number, number]> = {
      ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0],
    };
    const step = steps[event.key];
    if (!step) return;
    event.preventDefault();
    const rowIndex = calendar.years.findIndex((row) => row.year === cell.year);
    const target = calendar.years[rowIndex + step[0]]?.cells[cell.monthIndex + step[1]];
    if (target) {
      setActive(target.key);
      cellRefs.current.get(target.key)?.focus();
    }
  }

  function fillOf(cell: CalendarCell): string {
    if (cell.state === 'value' && color) return color(cell.detections);
    if (cell.state === 'no_data') return 'url(#fc-no-data)';
    return 'transparent';
  }

  return (
    <figure className="fire-calendar">
      <figcaption className="fire-calendar__caption">
        Monthly fire detections on the VIIRS scale. Above the line, months are estimated from MODIS Aqua; below it,
        observed by VIIRS from {calendar.sensorSwitch ? `${MONTH_NAMES[calendar.sensorSwitch.monthIndex]} ${calendar.sensorSwitch.year}` : 'the start'}.
      </figcaption>

      <div className="fire-calendar__plot">
        <svg viewBox={`0 0 ${width} ${height}`} role="grid" aria-label="Fire calendar: monthly fire detections by year">
          <defs>
            <pattern id="fc-hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="4" className="fire-calendar__hatch" />
            </pattern>
            <pattern id="fc-no-data" width="6" height="6" patternUnits="userSpaceOnUse">
              <path d="M0,0 L6,6 M6,0 L0,6" className="fire-calendar__no-data-mark" />
            </pattern>
          </defs>

          <g role="row">
            <text role="columnheader" x={LABEL_W - 6} y={HEADER_H - 8} className="fire-calendar__axis" textAnchor="end">
              Year
            </text>
            {MONTH_NAMES.map((name, monthIndex) => (
              <text
                key={name}
                role="columnheader"
                x={cellX(monthIndex) + CELL_W / 2}
                y={HEADER_H - 8}
                textAnchor="middle"
                className="fire-calendar__axis"
              >
                {name}
              </text>
            ))}
          </g>

          {calendar.years.map((row, rowIndex) => (
            <g role="row" key={row.year}>
              <text role="rowheader" x={LABEL_W - 6} y={rowY(rowIndex) + CELL_H / 2 + 4} textAnchor="end" className="fire-calendar__axis">
                {row.year}
              </text>
              {row.cells.map((cell) => (
                <g key={cell.key}>
                  <rect
                    ref={(node) => {
                      if (node) cellRefs.current.set(cell.key, node);
                      else cellRefs.current.delete(cell.key);
                    }}
                    role="gridcell"
                    aria-label={cell.label}
                    data-state={cell.state}
                    tabIndex={cell.key === active ? 0 : -1}
                    x={cellX(cell.monthIndex)}
                    y={rowY(rowIndex)}
                    width={CELL_W}
                    height={CELL_H}
                    rx={2}
                    fill={fillOf(cell)}
                    className={`fire-calendar__cell fire-calendar__cell--${cell.state}${cell.incomplete ? ' fire-calendar__cell--incomplete' : ''}`}
                    onMouseEnter={() => setTooltip(cell)}
                    onMouseLeave={() => setTooltip(null)}
                    onFocus={() => {
                      setActive(cell.key);
                      setTooltip(cell);
                    }}
                    onBlur={() => setTooltip(null)}
                    onKeyDown={(event) => moveFocus(cell, event)}
                  />
                  {cell.estimated && cell.state !== 'no_data' && (
                    <rect
                      x={cellX(cell.monthIndex)}
                      y={rowY(rowIndex)}
                      width={CELL_W}
                      height={CELL_H}
                      rx={2}
                      fill="url(#fc-hatch)"
                      pointerEvents="none"
                      aria-hidden="true"
                    />
                  )}
                </g>
              ))}
            </g>
          ))}

          {calendar.sensorSwitch && switchRow >= 0 && (
            <path d={sensorSwitchPath(calendar.sensorSwitch, switchRow)} className="fire-calendar__switch" aria-hidden="true" />
          )}
        </svg>

        {tooltip && (
          <div
            role="tooltip"
            className="fire-calendar__tooltip"
            style={{
              left: `${((cellX(tooltip.monthIndex) + CELL_W / 2) / width) * 100}%`,
              top: `${(rowY(calendar.years.findIndex((r) => r.year === tooltip.year)) / height) * 100}%`,
            }}
          >
            {tooltip.label}
          </div>
        )}
      </div>

      <ul className="fire-calendar__legend" aria-label="Legend">
        {calendar.positiveExtent && (
          <li className="fire-calendar__ramp">
            <span>{countFormat.format(calendar.positiveExtent[0])}</span>
            <span
              className="fire-calendar__ramp-bar"
              style={{ background: `linear-gradient(to right, ${rampStops()})` }}
              aria-hidden="true"
            />
            <span>{countFormat.format(calendar.positiveExtent[1])} detections per month (log scale)</span>
          </li>
        )}
        <li><span className="fire-calendar__swatch fire-calendar__swatch--zero" aria-hidden="true" />Zero detections</li>
        <li><span className="fire-calendar__swatch fire-calendar__swatch--no-data" aria-hidden="true" />No satellite data</li>
        <li><span className="fire-calendar__swatch fire-calendar__swatch--estimated" aria-hidden="true" />Estimated from MODIS (with uncertainty range)</li>
        <li><span className="fire-calendar__swatch fire-calendar__swatch--incomplete" aria-hidden="true" />Incomplete month</li>
      </ul>
    </figure>
  );
}

function rampStops(): string {
  return Array.from({ length: RAMP_STOPS + 1 }, (_, i) => interpolateCividis(i / RAMP_STOPS)).join(', ');
}

function lastRequestedKey(cells: CalendarCell[]): string {
  const requested = cells.filter((c) => c.state !== 'not_requested');
  return requested.length ? requested[requested.length - 1].key : cells[0]?.key ?? '';
}
