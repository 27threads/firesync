import { useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { CalendarMonth } from '../api/types';
import { stripGeometry, type StripSpec } from '../calendar/calendarLayout';
import { buildCalendar, MONTH_NAMES, type CalendarCell } from '../calendar/calendarModel';
import { calendarHeight, CalendarSvg, gridBottomOf, gridWidth, HERO_GEOMETRY } from '../calendar/CalendarSvg';
import { Legend } from '../calendar/Legend';
import { MonthTip } from '../calendar/MonthTip';
import { Tooltip } from '../ui/Tooltip';
import { playHeroIntro, prefersReducedMotion } from './heroIntro';

interface HeroCalendarProps {
  months: CalendarMonth[];
  areaLabel: string;
  isDemo: boolean;
  onOpenExample: (monthKey: string | null) => void;
}

function monthLabel(key: string): string {
  const [y, m] = key.split('-').map(Number);
  return `${MONTH_NAMES[m - 1]} ${y}`;
}

export function HeroCalendar({ months, areaLabel, isDemo, onOpenExample }: HeroCalendarProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const overlayRef = useRef<SVGSVGElement>(null);
  const playedRef = useRef(false);
  const [hover, setHover] = useState<{ cell: CalendarCell; anchor: DOMRect } | null>(null);

  const model = useMemo(() => buildCalendar(months), [months]);
  const { grid, width } = HERO_GEOMETRY;
  const rows = model.years.length;
  const height = calendarHeight(grid, rows);
  const gw = gridWidth(grid);
  const midY = grid.top + (gridBottomOf(grid, rows) - grid.top) / 2;
  const strip: StripSpec = { left: grid.left, top: midY - 32, width: gw, height: 64 };

  const total = months.length;
  const nEstimated = months.filter((m) => m.source === 'estimated_modis').length;
  const switchBox = nEstimated > 0 && nEstimated < total ? stripGeometry(nEstimated, total, strip) : null;
  const first = months[0]?.month;
  const last = months[total - 1]?.month;
  const period = first && last ? `${monthLabel(first)} – ${monthLabel(last)}` : '';

  useLayoutEffect(() => {
    if (playedRef.current || !svgRef.current || !overlayRef.current || prefersReducedMotion()) return;
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
    // No celular o calendário fica abaixo da dobra: a abertura começa quando ele aparece.
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
  }, []); // A abertura toca uma vez só, com o primeiro conjunto de dados.

  return (
    <div className="hero-cal">
      <div className="hero-cal__head">
        <div>
          <p className="hero-cal__title">Monthly fire detections, {period}</p>
          <p className="hero-cal__area">{areaLabel}</p>
        </div>
        {isDemo ? (
          <span className="chip chip--demo" title="Illustrative values from the API contract example, not measurements">
            Demo data
          </span>
        ) : (
          <span className="chip chip--live">NASA FIRMS data</span>
        )}
      </div>

      <div style={{ position: 'relative' }}>
        <CalendarSvg
          ref={svgRef}
          months={months}
          theme="light"
          geometry={HERO_GEOMETRY}
          interactive={false}
          label={`Preview of the fire history, ${period}: one row per year, one column per month. Months before February 2012 are estimated from MODIS; later months are observed by VIIRS.`}
          onHover={(cell, anchor) => setHover(cell && anchor ? { cell, anchor } : null)}
          onSelect={(cell) => cell.month && onOpenExample(cell.key)}
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
              <line x1={switchBox.x} x2={switchBox.x} y1={strip.top - 40} y2={strip.top + strip.height + 10} stroke="#eef1f4" strokeWidth="1.5" />
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

      <div className="hero-cal__foot">
        <Legend extent={model.positiveExtent} theme="light" />
        <button type="button" className="hero-cal__explore" onClick={() => onOpenExample(null)}>
          Explore the example
        </button>
      </div>

      <Tooltip anchor={hover?.anchor ?? null} id="hero-tip">
        {hover && <MonthTip cell={hover.cell} />}
      </Tooltip>
    </div>
  );
}
