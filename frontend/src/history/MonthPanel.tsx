import type { CalendarMonth } from '../api/types';
import { describeMonth } from '../calendar/monthDetail';
import { formatCount } from '../format';

interface MonthPanelProps {
  month: CalendarMonth | null;
  months: CalendarMonth[];
}

const SPARK_W = 248;
const SPARK_H = 64;

// Detalhe do mês escolhido, com o mesmo mês em todos os anos como contexto.
export function MonthPanel({ month, months }: MonthPanelProps) {
  if (!month) {
    return (
      <aside className="month-detail" aria-label="Month detail">
        <h3>Month detail</h3>
        <p className="month-detail__empty">Select a month in the calendar, with a click, a tap or the arrow keys and Enter.</p>
      </aside>
    );
  }
  const d = describeMonth(month);
  const mm = month.month.slice(5);
  const same = months.filter((m) => m.month.slice(5) === mm);
  const max = Math.max(1, ...same.map((m) => m.detections));
  const barW = SPARK_W / Math.max(1, same.length);

  return (
    <aside className="month-detail" aria-label="Month detail" aria-live="polite">
      <h3>{d.title}</h3>
      <div className="month-detail__value">{d.value}</div>
      <dl>
        <dt>Source</dt>
        <dd>{d.source}</dd>
        {d.range && (
          <>
            <dt>Range</dt>
            <dd>{d.range.replace('Uncertainty range ', '')}</dd>
          </>
        )}
        <dt>Audit</dt>
        <dd>{d.rawCount}</dd>
        {d.anomaly && (
          <>
            <dt>Anomaly</dt>
            <dd>{d.anomaly}</dd>
          </>
        )}
        {d.flags.length > 0 && (
          <>
            <dt>Notes</dt>
            <dd>{d.flags.join('. ')}</dd>
          </>
        )}
      </dl>
      <figure className="month-detail__spark" style={{ margin: 0 }}>
        <svg viewBox={`0 0 ${SPARK_W} ${SPARK_H + 14}`} role="img" aria-label={`${d.title.split(' ')[0]} in every year of the period, with ${d.title} highlighted`}>
          {same.map((m, i) => {
            const h = (m.detections / max) * SPARK_H;
            const isSel = m.month === month.month;
            return (
              <rect
                key={m.month}
                x={i * barW + 0.5}
                y={SPARK_H - h}
                width={Math.max(1, barW - 1.5)}
                height={Math.max(0.5, h)}
                fill={isSel ? '#8a5800' : m.source === 'estimated_modis' ? '#9aa3ab' : '#4b535c'}
              />
            );
          })}
          <text x={0} y={SPARK_H + 12}>
            {same[0]?.month.slice(0, 4)}
          </text>
          <text x={SPARK_W} y={SPARK_H + 12} textAnchor="end">
            {same[same.length - 1]?.month.slice(0, 4)}
          </text>
        </svg>
        <figcaption className="month-detail__empty" style={{ fontSize: 12 }}>
          {d.title.split(' ')[0]} in every year, up to {formatCount(max)} detections. Lighter bars are estimated.
        </figcaption>
      </figure>
    </aside>
  );
}
