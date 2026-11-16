import { scaleLinear } from 'd3-scale';
import { useEffect, useId, useState } from 'react';
import type { CalendarMonth, SeasonalityMonth } from '../api/types';
import { MONTH_NAMES } from '../calendar/calendarModel';
import { formatCount } from '../format';
import { NARROW_QUERY, useMediaQuery } from '../ui/useMediaQuery';

/** Detections of each month of `year`, January to December; null where the record has no such month or no satellite data. */
export function yearLine(months: CalendarMonth[], year: number): (number | null)[] {
  const line: (number | null)[] = Array(12).fill(null);
  for (const m of months) {
    const [y, mm] = m.month.split('-').map(Number);
    // Same rule as describeMonth: a month missing every day has no data, which is not a zero.
    const noData = m.missing_days >= new Date(Date.UTC(y, mm, 0)).getUTCDate();
    if (y === year && !noData) line[mm - 1] = m.detections;
  }
  return line;
}

/** The years of the record, oldest first. */
export const yearsOf = (months: CalendarMonth[]): number[] => [...new Set(months.map((m) => Number(m.month.slice(0, 4))))];

/** Top of the scale: the chosen years and the typical month, so a record year elsewhere does not flatten them. */
export const linesMax = (lines: (number | null)[][], median: number[]): number =>
  Math.max(0, ...median, ...lines.flat().map((v) => v ?? 0));

const M = { top: 22, right: 54, bottom: 26 };
// Room for the Y axis numbers, as in the seasonal chart.
const CHAR_W = 6.2;
const AXIS_GAP = 10;

interface YearLinesChartProps {
  months: CalendarMonth[];
  seasonality: SeasonalityMonth[];
  /** The year chosen in the guided example; without one, the latest year of the record. */
  highlightYear: number | null;
}

/** "Is this year normal?": one line per chosen year over the range (lowest to highest month) of the complete years. */
export function YearLinesChart({ months, seasonality, highlightYear }: YearLinesChartProps) {
  const narrow = useMediaQuery(NARROW_QUERY);
  const uid = useId();
  const years = yearsOf(months);
  const latest = years[years.length - 1] ?? 0;
  const [to, setTo] = useState(highlightYear ?? latest);
  const [from, setFrom] = useState(Math.max(years[0] ?? 0, (highlightYear ?? latest) - 1));
  useEffect(() => {
    if (highlightYear === null) return;
    setTo(highlightYear);
    setFrom((f) => Math.min(f, highlightYear));
  }, [highlightYear]);

  if (!years.length || seasonality.length !== 12) return null;
  const W = narrow ? 340 : 760;
  const H = narrow ? 230 : 270;
  const chosen = years.filter((y) => y >= from && y <= to);
  const lines = chosen.map((y) => ({ year: y, values: yearLine(months, y) }));
  const current = lines[lines.length - 1]?.values ?? Array(12).fill(null);
  const nYears = seasonality[0]?.n_years ?? 0;

  const median = seasonality.map((s) => s.median);
  const y = scaleLinear()
    .domain([0, linesMax(lines.map((l) => l.values), median) || 1])
    .nice()
    .range([H - M.bottom, M.top]);
  const ticks = y.ticks(4);
  const left = Math.ceil(AXIS_GAP + CHAR_W * Math.max(...ticks.map((t) => formatCount(t).length)));
  const x = (i: number) => left + ((W - left - M.right) / 11) * i;
  const clipId = `${uid}-plot`.replace(/:/g, '');

  const path = (values: (number | null)[]) =>
    values.reduce<string>((d, v, i) => (v === null ? d : `${d}${d && values[i - 1] !== null ? 'L' : 'M'}${x(i)},${y(v)}`), '');
  const band =
    seasonality.map((s, i) => `${i ? 'L' : 'M'}${x(i)},${y(s.max)}`).join('') +
    [...seasonality].reverse().map((s, j) => `L${x(11 - j)},${y(s.min)}`).join('') +
    'Z';
  const lastIndex = current.reduce<number>((at, v, i) => (v === null ? at : i), -1);
  const lastValue = lastIndex >= 0 ? current[lastIndex] : null;
  // A month still running (or with missing days) is not comparable yet: its label says so.
  const lastMonth = months.find((m) => m.month === `${to}-${String(lastIndex + 1).padStart(2, '0')}`);
  const soFar = lastMonth?.incomplete || lastMonth?.provisional ? ' so far' : '';
  // The band of the record years can go past the top of a quiet range: it is cut there, and the key says so.
  const bandCut = Math.max(...seasonality.map((s) => s.max)) > y.domain()[1];

  return (
    <section className="year-lines" aria-labelledby="year-lines-title">
      <div className="section-head">
        <div>
          <h3 id="year-lines-title">{from === to ? `Is ${to} a normal fire year?` : `${from} to ${to} against the record`}</h3>
          <p>
            Each line is one year, January to December. The grey band goes from the lowest to the highest month in {nYears} complete
            years: inside it is usual for the season. Pick the years to compare; the scale follows them.
          </p>
        </div>
      </div>
      <div className="year-lines__range">
        <label htmlFor={`${uid}-from`}>From</label>
        <select id={`${uid}-from`} value={from} onChange={(e) => setFrom(Number(e.target.value))}>
          {years
            .filter((yr) => yr <= to)
            .map((yr) => (
              <option key={yr} value={yr}>
                {yr}
              </option>
            ))}
        </select>
        <span aria-hidden="true">—</span>
        <label htmlFor={`${uid}-to`}>To</label>
        <select id={`${uid}-to`} value={to} onChange={(e) => setTo(Number(e.target.value))}>
          {years
            .filter((yr) => yr >= from)
            .map((yr) => (
              <option key={yr} value={yr}>
                {yr}
              </option>
            ))}
        </select>
      </div>
      <ul className="year-lines__key" aria-hidden="true">
        <li>
          <span className="year-lines__swatch year-lines__swatch--year" /> {to}
        </li>
        {chosen.length > 1 && (
          <li>
            <span className={`year-lines__swatch year-lines__swatch--${chosen.length === 2 ? 'prev' : 'other'}`} />{' '}
            {chosen.length === 2 ? from : `${from} to ${to - 1}`}
          </li>
        )}
        <li>
          <span className="year-lines__swatch year-lines__swatch--median" /> Typical month (median)
        </li>
        <li>
          <span className="year-lines__swatch year-lines__swatch--band" /> Lowest to highest{bandCut ? ' (cut at the top)' : ''}
        </li>
      </ul>
      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Monthly detections from ${from} to ${to}${lastValue !== null ? `; ${formatCount(lastValue)} in ${MONTH_NAMES[lastIndex]} ${to}${soFar}` : ''}; against the lowest to highest month of ${nYears} complete years.`}
      >
        <defs>
          <clipPath id={clipId}>
            <rect x={left} y={M.top} width={W - left - M.right} height={H - M.top - M.bottom} />
          </clipPath>
        </defs>
        {ticks.map((t) => (
          <g key={t}>
            <line className="chart__grid" x1={left} x2={W - M.right} y1={y(t)} y2={y(t)} />
            <text x={left - 6} y={y(t) + 4} textAnchor="end">
              {formatCount(t)}
            </text>
          </g>
        ))}
        <path className="year-lines__band" d={band} clipPath={`url(#${clipId})`} />
        <path className="year-lines__median" d={path(median)} />
        {lines.slice(0, -1).map((l) => (
          <path key={l.year} className={chosen.length === 2 ? 'year-lines__prev' : 'year-lines__other'} d={path(l.values)} />
        ))}
        <path className="year-lines__year" d={path(current)} />
        {current.map((v, i) => v !== null && <circle key={i} className="year-lines__dot" cx={x(i)} cy={y(v)} r={i === lastIndex ? 4 : 2.5} />)}
        {lastValue !== null && (
          <text className="chart__strong" x={x(lastIndex)} y={y(lastValue) - 10} textAnchor="middle">
            {formatCount(lastValue)}
            {soFar}
          </text>
        )}
        {MONTH_NAMES.map((name, i) => (
          <text key={name} x={x(i)} y={H - 8} textAnchor="middle">
            {narrow ? name.slice(0, 1) : name}
          </text>
        ))}
      </svg>
    </section>
  );
}
