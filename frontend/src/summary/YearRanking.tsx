import { useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import type { YearTotal } from '../api/types';
import { formatCount } from '../format';
import { buildRanking, sourceLabel, type RankingRow } from './summaryModel';

const BAR_Y = 3;
const BAR_H = 10;

interface YearBarProps {
  row: RankingRow;
  toPct: (value: number) => number;
}

// Largura em % do próprio SVG: a barra acompanha a coluna em qualquer tela sem distorcer a hachura.
function YearBar({ row, toPct }: YearBarProps) {
  const classes = ['year-bar__fill'];
  if (row.hatched) classes.push('year-bar__fill--estimated');
  if (row.incomplete) classes.push('year-bar__fill--incomplete');
  const mid = BAR_Y + BAR_H / 2;

  return (
    <svg className="year-bar" role="img" aria-label={row.label}>
      <rect x="0" y={BAR_Y} width={`${toPct(row.detections)}%`} height={BAR_H} className={classes.join(' ')} />
      {row.hatched && (
        <rect
          x="0"
          y={BAR_Y}
          width={`${toPct(row.detections)}%`}
          height={BAR_H}
          fill="url(#year-ranking-hatch)"
        />
      )}
      {row.bandLow !== null && row.bandHigh !== null && (
        <g className="year-bar__band">
          <line x1={`${toPct(row.bandLow)}%`} x2={`${toPct(row.bandHigh)}%`} y1={mid} y2={mid} />
          <line x1={`${toPct(row.bandLow)}%`} x2={`${toPct(row.bandLow)}%`} y1={1} y2={BAR_H + 5} />
          <line x1={`${toPct(row.bandHigh)}%`} x2={`${toPct(row.bandHigh)}%`} y1={1} y2={BAR_H + 5} />
        </g>
      )}
    </svg>
  );
}

interface YearRankingProps {
  years: YearTotal[];
}

export function YearRanking({ years }: YearRankingProps) {
  const rows = useMemo(() => buildRanking(years), [years]);
  const top = Math.max(...rows.map((r) => r.bandHigh ?? r.detections));
  const toPct = scaleLinear().domain([0, top]).range([0, 100]);

  return (
    <section className="summary-block year-ranking" aria-labelledby="year-ranking-title">
      <h3 id="year-ranking-title">Years ranked by detections</h3>
      <p>
        Only complete years get a position. Estimated years show the range of the MODIS to VIIRS conversion (hatched bar,
        line with end marks). Incomplete years have a dashed outline.
      </p>
      <svg width="0" height="0" aria-hidden="true" className="visually-hidden">
        <defs>
          <pattern id="year-ranking-hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="4" className="year-bar__hatch" />
          </pattern>
        </defs>
      </svg>
      <div className="year-ranking__scroll">
        <table className="year-ranking__table">
          <thead>
            <tr>
              <th scope="col">Rank</th>
              <th scope="col">Year</th>
              <th scope="col">Detections</th>
              <th scope="col">Origin</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.year} className={row.incomplete ? 'year-ranking__row--incomplete' : undefined}>
                <td className="year-ranking__rank">{row.rankLabel ?? 'Not ranked'}</td>
                <th scope="row">{row.year}</th>
                <td className="year-ranking__value">
                  <span className="year-ranking__number">{formatCount(row.detections)}</span>
                  {row.rangeText && <span className="year-ranking__range">{` range ${row.rangeText}`}</span>}
                  <YearBar row={row} toPct={toPct} />
                </td>
                <td className="year-ranking__source">
                  {sourceLabel(row.source)}
                  {row.incomplete && <span className="year-ranking__flag">Incomplete year</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
