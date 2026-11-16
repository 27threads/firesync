import { scaleLinear } from 'd3-scale';
import type { SeasonalityMonth } from '../api/types';
import { formatCount } from '../format';
import { buildSeasonality } from '../summary/summaryModel';
import { NARROW_QUERY, useMediaQuery } from '../ui/useMediaQuery';

const M = { top: 16, right: 8, bottom: 26 };
// Room for the Y axis numbers: about 6.2 units per character at the chart's font size, plus the gap to the plot.
const CHAR_W = 6.2;
const AXIS_GAP = 10;

interface SeasonalChartProps {
  seasonality: SeasonalityMonth[];
  includesEstimatedYears: boolean;
  highlightMonthIndex: number | null;
}

export function SeasonalChart({ seasonality, includesEstimatedYears, highlightMonthIndex }: SeasonalChartProps) {
  // No celular o SVG tem quase a largura da tela, e o texto fica no tamanho do CSS.
  const narrow = useMediaQuery(NARROW_QUERY);
  const W = narrow ? 340 : 600;
  const H = narrow ? 220 : 250;
  const model = buildSeasonality(seasonality);
  const y = scaleLinear().domain([0, model.maxValue || 1]).nice().range([H - M.bottom, M.top]);
  const ticks = y.ticks(4);
  const left = Math.ceil(AXIS_GAP + CHAR_W * Math.max(...ticks.map((t) => formatCount(t).length)));
  const band = (W - left - M.right) / 12;
  const peakIndex = model.months.indexOf(model.peak);
  const hi = highlightMonthIndex ?? peakIndex;

  return (
    <section aria-labelledby="season-title">
      <div className="section-head">
        <div>
          <h3 id="season-title">Seasonal pattern</h3>
          <p>
            Median detections per month{model.nYears ? ` across ${model.nYears} complete years` : ''}, with the lowest and highest
            year. {includesEstimatedYears ? 'Includes years estimated from MODIS.' : ''}
          </p>
        </div>
      </div>
      <svg
        className="chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Seasonal pattern. ${model.peak.name} has the highest median, ${formatCount(model.peak.median)} detections.`}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line className="chart__grid" x1={left} x2={W - M.right} y1={y(t)} y2={y(t)} />
            <text x={left - 6} y={y(t) + 4} textAnchor="end">
              {formatCount(t)}
            </text>
          </g>
        ))}
        {model.months.map((m, i) => {
          const cx = left + band * i + band / 2;
          return (
            <g key={m.name} className={i === hi ? 'chart__peak' : undefined}>
              <title>{`${m.name}: median ${formatCount(m.median)}, lowest ${formatCount(m.min)}, highest ${formatCount(m.max)}`}</title>
              <line className="chart__range" x1={cx} x2={cx} y1={y(m.min)} y2={y(m.max)} />
              <rect className="chart__median" x={cx - band * 0.32} y={y(m.median) - 1.5} width={band * 0.64} height={3} />
              <text x={cx} y={H - 8} textAnchor="middle" className={i === hi ? 'chart__strong' : undefined}>
                {m.name}
              </text>
              {i === hi && (
                <text x={cx} y={y(m.max) - 6} textAnchor="middle" className="chart__strong">
                  {formatCount(m.median)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </section>
  );
}
