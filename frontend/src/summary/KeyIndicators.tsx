import type { CalendarResponse } from '../api/types';
import { MONTH_NAMES } from '../calendar/calendarModel';
import { formatCount, formatSignedPct, formatWindowValue } from '../format';
import { sourceLabel } from './summaryModel';

function monthLabel(value: string): string {
  const [year, month] = value.split('-').map(Number);
  return `${MONTH_NAMES[month - 1]} ${year}`;
}

interface KeyIndicatorsProps {
  data: CalendarResponse;
}

export function KeyIndicators({ data }: KeyIndicatorsProps) {
  const { indicators, months, years, recent } = data;
  const period = `${monthLabel(months[0].month)}–${monthLabel(months[months.length - 1].month)}`;
  const estimated = months.filter((m) => m.source === 'estimated_modis');
  const latest = indicators.latest_complete_year;
  const latestYear = years.find((y) => y.year === latest.year);
  const latestBand =
    latestYear && latestYear.band_low !== null && latestYear.band_high !== null
      ? `, range ${formatCount(latestYear.band_low)}–${formatCount(latestYear.band_high)}`
      : '';
  const latestSource = latestYear ? sourceLabel(latestYear.source) : 'origin not reported';

  return (
    <section className="summary-block key-indicators" aria-labelledby="key-indicators-title">
      <h3 id="key-indicators-title">Key indicators</h3>
      <dl className="key-indicators__list">
        <div className="key-indicators__item">
          <dt>Last 7 days vs. typical</dt>
          <dd className="stat">{formatSignedPct(indicators.last_7_days_vs_typical_pct)}</dd>
          <dd className="stat-note">
            {formatCount(recent.last_7_days.detections)} detections; typical {formatWindowValue(recent.last_7_days.typical_median)}
          </dd>
        </div>
        <div className="key-indicators__item">
          <dt>{latest.year} vs. reference average</dt>
          <dd className="stat">{formatSignedPct(latest.anomaly_pct)}</dd>
          <dd className="stat-note">
            {/* TODO(confirm): anos de referência ainda em aberto no docs/api.md ("Em aberto", ponto 2). */}
            {`${formatCount(latest.detections)} detections, ${latestSource}${latestBand}; reference average ${formatCount(latest.reference_mean)}`}
          </dd>
        </div>
        <div className="key-indicators__item">
          <dt>Total detections, {period}</dt>
          <dd className="stat">{formatCount(indicators.total_detections)}</dd>
          {estimated.length > 0 && (
            <dd className="stat-note">
              {/* TODO(confirm): o contrato não traz faixa de incerteza para o total do intervalo. */}
              {`Includes months estimated from MODIS (to ${monthLabel(estimated[estimated.length - 1].month)}); the range of each one is in the calendar.`}
            </dd>
          )}
        </div>
      </dl>
    </section>
  );
}
