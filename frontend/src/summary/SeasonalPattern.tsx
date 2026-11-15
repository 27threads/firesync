import { useMemo } from 'react';
import { scaleBand, scaleLinear } from 'd3-scale';
import type { SeasonalityMonth } from '../api/types';
import { formatCount } from '../format';
import { buildSeasonality } from './summaryModel';

const WIDTH = 360;
const HEIGHT = 200;
const MARGIN = { top: 12, right: 2, bottom: 22, left: 38 };
const CAP = 4;

interface SeasonalPatternProps {
  seasonality: SeasonalityMonth[];
  includesEstimatedYears: boolean;
}

export function SeasonalPattern({ seasonality, includesEstimatedYears }: SeasonalPatternProps) {
  const model = useMemo(() => buildSeasonality(seasonality), [seasonality]);
  const x = scaleBand<string>()
    .domain(model.months.map((m) => m.name))
    .range([MARGIN.left, WIDTH - MARGIN.right])
    .padding(0.3);
  const y = scaleLinear()
    .domain([0, model.maxValue])
    .nice()
    .range([HEIGHT - MARGIN.bottom, MARGIN.top]);
  const years = model.nYears === null ? 'the complete years' : `${model.nYears} complete years`;

  return (
    <section className="summary-block seasonal" aria-labelledby="seasonal-title">
      <h3 id="seasonal-title">Seasonal pattern</h3>
      <p>
        {`Peak month: ${model.peak.name}, median ${formatCount(model.peak.median)} detections. Median and lowest to highest year for each month, across ${years}.`}
        {includesEstimatedYears && ' Years before 2012 are estimated from MODIS; 2012 mixes both sensors.'}
      </p>
      <figure className="seasonal__figure">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label={`Seasonal pattern chart: median detections by month, peak in ${model.peak.name}`}
        >
          {y.ticks(4).map((tick) => (
            <g key={tick}>
              <line x1={MARGIN.left} x2={WIDTH - MARGIN.right} y1={y(tick)} y2={y(tick)} className="chart__grid" />
              <text x={MARGIN.left - 6} y={y(tick)} dy="0.32em" textAnchor="end" className="chart__axis">
                {formatCount(tick)}
              </text>
            </g>
          ))}
          {model.months.map((m) => {
            const left = x(m.name)!;
            const center = left + x.bandwidth() / 2;
            const peak = m === model.peak;
            return (
              <g key={m.name}>
                <rect
                  x={left}
                  y={y(m.median)}
                  width={x.bandwidth()}
                  height={y(0) - y(m.median)}
                  className={peak ? 'seasonal__bar seasonal__bar--peak' : 'seasonal__bar'}
                />
                <line x1={center} x2={center} y1={y(m.min)} y2={y(m.max)} className="seasonal__spread" />
                <line x1={center - CAP} x2={center + CAP} y1={y(m.max)} y2={y(m.max)} className="seasonal__spread" />
                <line x1={center - CAP} x2={center + CAP} y1={y(m.min)} y2={y(m.min)} className="seasonal__spread" />
                <text x={center} y={HEIGHT - 6} textAnchor="middle" className="chart__axis">
                  {m.name}
                </text>
              </g>
            );
          })}
        </svg>
        <figcaption className="chart__legend">
          <span>
            <span className="chart__key chart__key--bar" aria-hidden="true" /> Bar: median year
          </span>
          <span>
            <span className="chart__key chart__key--spread" aria-hidden="true" /> Line: lowest to highest year
          </span>
        </figcaption>
      </figure>
      <table className="visually-hidden">
        <caption>Detections by month of the year</caption>
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col">Median</th>
            <th scope="col">Lowest to highest year</th>
          </tr>
        </thead>
        <tbody>
          {model.months.map((m) => (
            <tr key={m.name}>
              <th scope="row">{m.name}</th>
              <td>{formatCount(m.median)}</td>
              <td>{`${formatCount(m.min)}–${formatCount(m.max)}`}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
