import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { CalendarRequest, CalendarResponse } from '../api/types';
import { stripGeometry, type StripSpec } from '../calendar/calendarLayout';
import { buildCalendar, MONTH_NAMES, type CalendarCell } from '../calendar/calendarModel';
import { calendarHeight, CalendarSvg, FULL_GEOMETRY, FULL_NARROW_GEOMETRY, gridBottomOf, gridWidth } from '../calendar/CalendarSvg';
import { Legend } from '../calendar/Legend';
import { describeMonth } from '../calendar/monthDetail';
import { MonthTip } from '../calendar/MonthTip';
import { ExportBar } from '../export/ExportBar';
import { playHeroIntro, prefersReducedMotion } from '../hero/heroIntro';
import type { ResultState } from '../state/explorerModel';
import { Tooltip } from '../ui/Tooltip';
import { NARROW_QUERY, useMediaQuery } from '../ui/useMediaQuery';
import { MonthPanel } from './MonthPanel';
import { SeasonalChart } from './SeasonalChart';
import { YearRanking } from './YearRanking';

function monthLabel(key: string): string {
  const [y, m] = key.split('-').map(Number);
  return `${MONTH_NAMES[m - 1]} ${y}`;
}

interface HistoryPanelProps {
  shown: { data: CalendarResponse; isDemo: boolean } | null;
  result: ResultState;
  selectedKey: string | null;
  onSelectKey: (key: string | null) => void;
  highlightMonthIndex: number | null;
  highlightYear: number | null;
  areaLabel: string;
  periodLabel: string;
  request: CalendarRequest | null;
}

function CalendarTable({ data }: { data: CalendarResponse }) {
  return (
    <div className="cal-table-wrap">
      <table className="cal-table">
        <caption className="visually-hidden">Monthly detections, one row per month</caption>
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col">Detections</th>
            <th scope="col">Source</th>
            <th scope="col">Uncertainty range</th>
            <th scope="col">Days without data</th>
            <th scope="col">Notes</th>
          </tr>
        </thead>
        <tbody>
          {data.months.map((m) => {
            const d = describeMonth(m);
            return (
              <tr key={m.month}>
                <th scope="row">{d.title}</th>
                <td className="n">{d.value.replace(' detections', '')}</td>
                <td>{m.source === 'estimated_modis' ? 'Estimated (MODIS)' : 'Observed (VIIRS)'}</td>
                <td>{d.range ? d.range.replace('Uncertainty range ', '') : '—'}</td>
                <td className="n">{m.missing_days}</td>
                <td>{[m.incomplete && 'Incomplete', m.provisional && 'Provisional'].filter(Boolean).join(', ')}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EmptyHistory({ result }: { result: ResultState }) {
  if (result.kind === 'no_coverage') {
    return (
      <div className="empty-state">
        <h3>No record for this area</h3>
        <p>The area is outside the current coverage, so there is no calendar to show. This is not a record of zero detections.</p>
      </div>
    );
  }
  if (result.kind === 'error' || result.kind === 'rate_limited') {
    return (
      <div className="empty-state">
        <h3>The record could not be loaded</h3>
        <p>{result.message}</p>
      </div>
    );
  }
  return (
    <div className="empty-state">
      <h3>Loading the record…</h3>
      <p>Monthly detections for this area will appear here.</p>
    </div>
  );
}

export function HistoryPanel({
  shown,
  result,
  selectedKey,
  onSelectKey,
  highlightMonthIndex,
  highlightYear,
  areaLabel,
  periodLabel,
  request,
}: HistoryPanelProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const overlayRef = useRef<SVGSVGElement>(null);
  const playedRef = useRef(false);
  const [asTable, setAsTable] = useState(false);
  const [hover, setHover] = useState<{ cell: CalendarCell; anchor: DOMRect } | null>(null);
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const narrow = useMediaQuery(NARROW_QUERY);
  const data = shown?.data ?? null;
  const model = useMemo(() => (data ? buildCalendar(data.months) : null), [data]);
  const selectedMonth = data && selectedKey ? data.months.find((m) => m.month === selectedKey) ?? null : null;
  const includesEstimatedYears = data ? data.years.some((y) => y.complete && y.source !== 'observed_viirs') : false;

  const geometry = narrow ? FULL_NARROW_GEOMETRY : FULL_GEOMETRY;
  const { grid, width } = geometry;
  const rows = model?.years.length ?? 0;
  const height = calendarHeight(geometry, rows);
  const gw = gridWidth(grid);
  const midY = grid.top + (gridBottomOf(grid, rows) - grid.top) / 2;
  const strip: StripSpec = { left: grid.left, top: midY - 32, width: gw, height: 64 };

  const months = data?.months ?? [];
  const total = months.length;
  const nEstimated = months.filter((m) => m.source === 'estimated_modis').length;
  const switchBox = nEstimated > 0 && nEstimated < total ? stripGeometry(nEstimated, total, strip) : null;
  const first = months[0]?.month;
  const last = months[total - 1]?.month;

  useLayoutEffect(() => {
    if (playedRef.current || !data || !svgRef.current || !overlayRef.current || prefersReducedMotion()) return;
    playedRef.current = true;
    const svg = svgRef.current;
    const overlay = overlayRef.current;
    let stop: () => void = () => undefined;
    const play = () => {
      try {
        stop = playHeroIntro(svg, overlay, strip);
      } catch {
        // Sem animação, o calendário já está no estado final.
      }
    };
    let observer: IntersectionObserver | null = null;
    const rect = svg.getBoundingClientRect();
    if (rect.top < window.innerHeight * 0.8 || typeof IntersectionObserver === 'undefined') {
      play();
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          if (entries.some((e) => e.isIntersecting)) {
            observer?.disconnect();
            play();
          }
        },
        { threshold: 0.35 },
      );
      observer.observe(svg);
    }
    return () => {
      observer?.disconnect();
      stop();
      playedRef.current = false; // No StrictMode (dev) o efeito roda duas vezes; a segunda toca de novo.
    };
  }, [Boolean(data)]);

  return (
    <div className="ws-history" id="history">
      <section aria-labelledby="history-title">
        <div className="section-head">
          <div>
            <h2 id="history-title">A longer view of fire activity</h2>
            <p>
              Monthly detections on the VIIRS scale, {periodLabel}. One row per year, January to December.
              {shown?.isDemo ? ' Demo data.' : ''}
            </p>
          </div>
          {data && (
            <div className="section-head__actions">
              <button type="button" className="btn btn--quiet" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)}>
                View as table
              </button>
            </div>
          )}
        </div>

        {!data || !model ? (
          <EmptyHistory result={result} />
        ) : (
          <div className={result.kind === 'loading' ? 'is-loading' : undefined}>
            <div className="calendar-block">
              <div>
                <div className="calendar-scroll" style={{ position: 'relative' }}>
                  <CalendarSvg
                    ref={svgRef}
                    months={data.months}
                    geometry={geometry}
                    interactive
                    label={`Fire calendar, monthly detections, ${periodLabel}`}
                    selectedKey={selectedKey}
                    focusKey={focusKey}
                    highlightMonthIndex={highlightMonthIndex}
                    highlightYear={highlightYear}
                    onFocusKeyChange={setFocusKey}
                    onSelect={(cell) => onSelectKey(cell.month ? cell.key : null)}
                    onHover={(cell, anchor) => setHover(cell && anchor ? { cell, anchor } : null)}
                  />
                  <svg
                    ref={overlayRef}
                    className="hero-cal__svg"
                    viewBox={`0 0 ${width} ${height}`}
                    style={{ position: 'absolute', inset: 0, opacity: 0, pointerEvents: 'none' }}
                    aria-hidden="true"
                  >
                    {switchBox && (
                      <>
                        <text className="cal-strip-label" x={strip.left} y={strip.top - 30}>
                          MODIS Aqua
                        </text>
                        <text className="cal-strip-sub" x={strip.left} y={strip.top - 14}>
                          estimated
                        </text>
                        <text className="cal-strip-label" x={switchBox.x + 10} y={strip.top - 30}>
                          VIIRS
                        </text>
                        <text className="cal-strip-sub" x={switchBox.x + 10} y={strip.top - 14}>
                          observed
                        </text>
                        <line x1={switchBox.x} x2={switchBox.x} y1={strip.top - 40} y2={strip.top + strip.height + 10} stroke="var(--ink)" strokeWidth="1.5" />
                        <text className="cal-strip-sub" x={switchBox.x} y={strip.top + strip.height + 26} textAnchor="middle">
                          Feb 2012
                        </text>
                      </>
                    )}
                    <text className="cal-strip-sub" x={strip.left} y={strip.top + strip.height + 26}>
                      {first ? monthLabel(first) : ''}
                    </text>
                    <text className="cal-strip-sub" x={strip.left + strip.width} y={strip.top + strip.height + 26} textAnchor="end">
                      {last ? monthLabel(last) : ''}
                    </text>
                    <text className="cal-strip-sub" x={strip.left} y={strip.top + strip.height + 48}>
                      {total} months in one record
                    </text>
                  </svg>
                </div>
                <Legend extent={model.positiveExtent} className="calendar-legend" />
              </div>
              <MonthPanel month={selectedMonth} months={data.months} />
            </div>
            {asTable && <CalendarTable data={data} />}

            <div className="context-grid">
              <SeasonalChart seasonality={data.seasonality} includesEstimatedYears={includesEstimatedYears} highlightMonthIndex={highlightMonthIndex} />
              <YearRanking years={data.years} highlightYear={highlightYear} />
            </div>

            <ExportBar data={data} isDemo={shown?.isDemo ?? false} request={request} areaLabel={areaLabel} periodLabel={periodLabel} />
          </div>
        )}
      </section>
      <Tooltip anchor={hover?.anchor ?? null} id="calendar-tip">
        {hover && <MonthTip cell={hover.cell} />}
      </Tooltip>
    </div>
  );
}
