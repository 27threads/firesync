import { forwardRef, useId, useMemo, type KeyboardEvent, type PointerEvent } from 'react';
import type { CalendarMonth } from '../api/types';
import { gridGeometry, type GridSpec } from './calendarLayout';
import { buildCalendar, MONTH_NAMES, type CalendarCell } from './calendarModel';
import { makeColorScale } from './colorScale';


// Largura total = margem dos anos + 12 colunas + coluna de notas à direita.
export interface CalendarGeometry {
  width: number;
  grid: GridSpec;
}

export const HERO_GEOMETRY: CalendarGeometry = {
  width: 652,
  grid: { left: 38, top: 22, cellWidth: 38.5, cellHeight: 16, gap: 2 },
};

export const FULL_GEOMETRY: CalendarGeometry = {
  width: 960,
  grid: { left: 46, top: 24, cellWidth: 60, cellHeight: 20, gap: 2 },
};

interface CalendarSvgProps {
  months: CalendarMonth[];
  geometry: CalendarGeometry;
  label: string;
  interactive: boolean; // true: grade navegável por teclado (role="grid")
  selectedKey?: string | null;
  highlightMonthIndex?: number | null;
  highlightYear?: number | null;
  focusKey?: string | null;
  onSelect?: (cell: CalendarCell) => void;
  onHover?: (cell: CalendarCell | null, anchor: DOMRect | null) => void;
  onFocusKeyChange?: (key: string) => void;
}

export function gridWidth(spec: GridSpec): number {
  return 12 * spec.cellWidth + 11 * spec.gap;
}

export function gridBottomOf(spec: GridSpec, rows: number): number {
  return rowY(spec, rows) - spec.gap;
}

export function calendarHeight(spec: GridSpec, rows: number): number {
  return gridBottomOf(spec, rows) + 14;
}

function rowY(spec: GridSpec, row: number): number {
  return spec.top + row * (spec.cellHeight + spec.gap);
}

function colX(spec: GridSpec, col: number): number {
  return spec.left + col * (spec.cellWidth + spec.gap);
}

export const CalendarSvg = forwardRef<SVGSVGElement, CalendarSvgProps>(function CalendarSvg(
  {
    months,
    geometry,
    label,
    interactive,
    selectedKey = null,
    highlightMonthIndex = null,
    highlightYear = null,
    focusKey = null,
    onSelect,
    onHover,
    onFocusKeyChange,
  },
  ref,
) {
  const uid = useId().replace(/:/g, '');
  const model = useMemo(() => buildCalendar(months), [months]);
  const color = useMemo(() => (model.positiveExtent ? makeColorScale(model.positiveExtent) : null), [model]);
  const { grid } = geometry;
  const firstYear = model.years[0]?.year ?? 2003;
  const rows = model.years.length;
  const gw = gridWidth(grid);
  const gridBottom = gridBottomOf(grid, rows);
  const height = calendarHeight(grid, rows);
  const noteX = grid.left + gw + 14;

  const allCells = model.years.flatMap((row) => row.cells);
  const firstRealKey = allCells.find((c) => c.month)?.key ?? null;
  const activeKey = focusKey ?? selectedKey ?? firstRealKey;

  // Linha em degrau entre o último mês estimado e o primeiro observado.
  const sw = model.sensorSwitch;
  let switchPath: string | null = null;
  let switchRow = 0;
  if (sw) {
    switchRow = sw.year - firstYear;
    const half = grid.gap / 2;
    const yTop = rowY(grid, switchRow) - half;
    const yBottom = rowY(grid, switchRow + 1) - half;
    const xCol = colX(grid, sw.monthIndex) - half;
    switchPath =
      sw.monthIndex === 0
        ? `M${grid.left - 4} ${yTop} H${grid.left + gw + 4}`
        : `M${grid.left - 4} ${yBottom} H${xCol} V${yTop} H${grid.left + gw + 4}`;
  }
  const hasEstimated = months.some((m) => m.source === 'estimated_modis');
  const hasObserved = months.some((m) => m.source === 'observed_viirs');

  const hatchId = `hatch-${uid}`;
  const noDataId = `nodata-${uid}`;

  function keyAt(row: number, col: number): string | null {
    const r = model.years[row];
    return r ? r.cells[col]?.key ?? null : null;
  }

  function handleKeyDown(event: KeyboardEvent<SVGGElement>, cell: CalendarCell) {
    const row = cell.year - firstYear;
    const col = cell.monthIndex;
    const moves: Record<string, [number, number]> = {
      ArrowRight: [row, Math.min(11, col + 1)],
      ArrowLeft: [row, Math.max(0, col - 1)],
      ArrowDown: [Math.min(rows - 1, row + 1), col],
      ArrowUp: [Math.max(0, row - 1), col],
      Home: [row, 0],
      End: [row, 11],
    };
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onSelect?.(cell);
      return;
    }
    const target = moves[event.key];
    if (!target) return;
    event.preventDefault();
    const next = keyAt(target[0], target[1]);
    if (next) {
      onFocusKeyChange?.(next);
      const svg = (event.currentTarget.ownerSVGElement ?? null) as SVGSVGElement | null;
      const el = svg?.querySelector<SVGGElement>(`[data-key="${next}"]`);
      el?.focus();
    }
  }

  function hover(event: PointerEvent<SVGGElement> | null, cell: CalendarCell | null) {
    if (!onHover) return;
    if (!event || !cell) {
      onHover(null, null);
      return;
    }
    onHover(cell, (event.currentTarget as SVGGElement).getBoundingClientRect());
  }

  let stripIndex = 0;

  return (
    <svg
      ref={ref}
      className="calendar-svg-root"
      viewBox={`0 0 ${geometry.width} ${height}`}
      role={interactive ? 'grid' : 'img'}
      aria-label={label}
      aria-rowcount={interactive ? rows + 1 : undefined}
      data-first-year={firstYear}
      data-rows={rows}
    >
      <defs>
        <pattern id={hatchId} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line className="cal-hatch-a" x1="0.5" y1="0" x2="0.5" y2="5" />
          <line className="cal-hatch-b" x1="1.6" y1="0" x2="1.6" y2="5" />
        </pattern>
        <pattern id={noDataId} width="6" height="6" patternUnits="userSpaceOnUse">
          <rect width="6" height="6" fill="#eceeef" />
          <path d="M0 0L6 6M6 0L0 6" stroke="#9aa1a8" strokeWidth="0.8" />
        </pattern>
      </defs>

      <g className="cal-decor" data-decor="axis" role={interactive ? 'row' : undefined}>
        {interactive && (
          <text className="cal-axis" x={grid.left - 8} y={grid.top - 8} textAnchor="end" role="columnheader">
            Year
          </text>
        )}
        {MONTH_NAMES.map((name, i) => (
          <text
            key={name}
            className="cal-axis"
            x={colX(grid, i) + grid.cellWidth / 2}
            y={grid.top - 8}
            textAnchor="middle"
            role={interactive ? 'columnheader' : undefined}
          >
            {name}
          </text>
        ))}
      </g>

      {model.years.map((row, r) => (
        <g key={row.year} role={interactive ? 'row' : undefined}>
          <text
            className="cal-axis cal-decor"
            data-decor="axis"
            x={grid.left - 8}
            y={rowY(grid, r) + grid.cellHeight / 2 + 4}
            textAnchor="end"
            role={interactive ? 'rowheader' : undefined}
          >
            {row.year}
          </text>
          {row.cells.map((cell) => {
            const box = gridGeometry(cell, firstYear, grid);
            const w = grid.cellWidth;
            const h = grid.cellHeight;
            const isReal = cell.month !== null;
            const index = isReal ? stripIndex++ : -1;
            let fill: string | undefined;
            let className = 'cal-cell';
            if (cell.state === 'value') fill = color ? color(cell.detections) : undefined;
            else if (cell.state === 'zero') className += ' cal-zero';
            else if (cell.state === 'no_data') fill = `url(#${noDataId})`;
            else className += ' cal-outside';

            const content = (
              <svg
                x={box.x}
                y={box.y}
                width={w}
                height={h}
                viewBox={`0 0 ${w} ${h}`}
                preserveAspectRatio="none"
                overflow="visible"
                className="cal-cellbox"
                data-strip-i={index >= 0 ? index : undefined}
              >
                <rect className={className} width={w} height={h} fill={fill} />
                {cell.state === 'zero' && <line className="cal-zero-mark" x1={w / 2 - 4} x2={w / 2 + 4} y1={h / 2} y2={h / 2} />}
                {cell.estimated && cell.state !== 'no_data' && <rect width={w} height={h} fill={`url(#${hatchId})`} />}
                {cell.incomplete && <rect className="cal-incomplete" x={1.25} y={1.25} width={w - 2.5} height={h - 2.5} />}
                {cell.provisional && <circle className="cal-provisional" cx={w - 4.5} cy={4.5} r={2.4} />}
                <rect className="cal-hover" x={0.75} y={0.75} width={w - 1.5} height={h - 1.5} />
                <rect className="cal-focus" x={1.25} y={1.25} width={w - 2.5} height={h - 2.5} />
              </svg>
            );

            if (!interactive) {
              return (
                <g
                  key={cell.key}
                  data-key={cell.key}
                  onPointerEnter={(e) => hover(e, cell)}
                  onPointerLeave={() => hover(null, null)}
                  onClick={() => onSelect?.(cell)}
                  style={{ cursor: isReal ? 'pointer' : 'default' }}
                >
                  {content}
                </g>
              );
            }

            return (
              <g
                key={cell.key}
                className="cal-gridcell"
                role="gridcell"
                data-key={cell.key}
                aria-label={cell.label}
                aria-selected={cell.key === selectedKey}
                tabIndex={cell.key === activeKey ? 0 : -1}
                onPointerEnter={(e) => hover(e, cell)}
                onPointerLeave={() => hover(null, null)}
                onFocus={(e) => {
                  onFocusKeyChange?.(cell.key);
                  onHover?.(cell, (e.currentTarget as SVGGElement).getBoundingClientRect());
                }}
                onBlur={() => onHover?.(null, null)}
                onClick={() => onSelect?.(cell)}
                onKeyDown={(e) => handleKeyDown(e, cell)}
              >
                {content}
              </g>
            );
          })}
        </g>
      ))}

      {highlightMonthIndex !== null && (
        <rect
          className="cal-highlight"
          x={colX(grid, highlightMonthIndex) - 2}
          y={grid.top - 2}
          width={grid.cellWidth + 4}
          height={gridBottom - grid.top + 4}
        />
      )}
      {highlightYear !== null && highlightYear >= firstYear && highlightYear < firstYear + rows && (
        <rect
          className="cal-highlight"
          x={grid.left - 2}
          y={rowY(grid, highlightYear - firstYear) - 2}
          width={gw + 4}
          height={grid.cellHeight + 4}
        />
      )}
      {selectedKey &&
        (() => {
          const cell = allCells.find((c) => c.key === selectedKey);
          if (!cell) return null;
          const box = gridGeometry(cell, firstYear, grid);
          return <rect className="cal-selected" x={box.x - 1.5} y={box.y - 1.5} width={box.width + 3} height={box.height + 3} />;
        })()}

      <g className="cal-decor" data-decor="notes" aria-hidden="true">
        {switchPath && <path className="cal-switch" d={switchPath} data-decor="switch" />}
        {hasEstimated && sw && (
          <>
            <path className="cal-bracket" d={`M${noteX} ${grid.top} H${noteX + 6} V${rowY(grid, switchRow) + grid.cellHeight - 2} H${noteX}`} />
            <text className="cal-note cal-note--strong" x={noteX + 12} y={grid.top + 10}>
              Estimated
            </text>
            <text className="cal-note" x={noteX + 12} y={grid.top + 24}>
              from MODIS Aqua,
            </text>
            <text className="cal-note" x={noteX + 12} y={grid.top + 38}>
              with uncertainty
            </text>
            <text className="cal-note" x={noteX + 12} y={grid.top + 52}>
              range
            </text>
          </>
        )}
        {hasObserved && (
          <>
            <path
              className="cal-bracket"
              d={`M${noteX} ${sw && hasEstimated ? rowY(grid, switchRow) + 2 : grid.top} H${noteX + 6} V${gridBottom} H${noteX}`}
            />
            <text className="cal-note cal-note--strong" x={noteX + 12} y={(sw && hasEstimated ? rowY(grid, switchRow) : grid.top) + 22}>
              {sw && hasEstimated ? `${MONTH_NAMES[sw.monthIndex]} ${sw.year}` : 'Observed'}
            </text>
            <text className="cal-note" x={noteX + 12} y={(sw && hasEstimated ? rowY(grid, switchRow) : grid.top) + 36}>
              {sw && hasEstimated ? 'VIIRS observations' : 'by VIIRS'}
            </text>
            {sw && hasEstimated && (
              <text className="cal-note" x={noteX + 12} y={rowY(grid, switchRow) + 50}>
                begin
              </text>
            )}
          </>
        )}
      </g>
    </svg>
  );
});
