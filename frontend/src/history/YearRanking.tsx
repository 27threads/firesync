import { scaleLinear } from 'd3-scale';
import { useId } from 'react';
import type { YearTotal } from '../api/types';
import { formatCount } from '../format';
import { buildRanking } from '../summary/summaryModel';

const W = 520;
const ROW = 17;
const LEFT = 64;
const RIGHT = 70;

interface YearRankingProps {
  years: YearTotal[];
  highlightYear: number | null;
}

// A ordem e o rank vêm da API. Anos incompletos ficam fora do ranking, listados à parte.
export function YearRanking({ years, highlightYear }: YearRankingProps) {
  const uid = useId().replace(/:/g, '');
  const rows = buildRanking(years);
  const ranked = rows.filter((r) => r.rankLabel !== null);
  const unranked = rows.filter((r) => r.rankLabel === null);
  const max = Math.max(1, ...ranked.map((r) => r.bandHigh ?? r.detections));
  const x = scaleLinear().domain([0, max]).range([0, W - LEFT - RIGHT]);
  const H = ranked.length * ROW + 8;
  const top5 = ranked
    .slice(0, 5)
    .map((r) => `${r.year} ${formatCount(r.detections)}`)
    .join('; ');

  return (
    <section aria-labelledby="ranking-title">
      <div className="section-head">
        <div>
          <h3 id="ranking-title">Years ranked by detections</h3>
          <p>Complete years only. Hatched bars are estimated from MODIS, with their uncertainty range as a line.</p>
        </div>
      </div>
      <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Years ranked by detections, highest first: ${top5}.`}>
        <defs>
          <pattern id={`rk-${uid}`} width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="4" height="4" fill="#9aa3ab" />
            <line x1="0.5" y1="0" x2="0.5" y2="4" stroke="#fbfbfa" strokeWidth="1.1" />
          </pattern>
        </defs>
        {ranked.map((r, i) => {
          const yy = i * ROW + 4;
          const barH = ROW - 5;
          const isHi = r.year === highlightYear;
          return (
            <g key={r.year} className={`chart__row${isHi ? ' chart__row--highlight' : ''}`}>
              <title>{r.label}</title>
              <text x={0} y={yy + barH - 1} className={i === 0 || isHi ? 'chart__strong' : undefined}>
                {r.rankLabel}
              </text>
              <text x={LEFT - 8} y={yy + barH - 1} textAnchor="end" className={i === 0 || isHi ? 'chart__strong' : undefined}>
                {r.year}
              </text>
              <rect
                className={`chart__bar${i === 0 ? ' chart__bar--top' : ''}`}
                x={LEFT}
                y={yy}
                width={x(r.detections)}
                height={barH}
                fill={r.hatched && !isHi ? `url(#rk-${uid})` : undefined}
              />
              {r.bandLow !== null && r.bandHigh !== null && (
                <line className="chart__band" x1={LEFT + x(r.bandLow)} x2={LEFT + x(r.bandHigh)} y1={yy + barH / 2} y2={yy + barH / 2} />
              )}
              <text x={LEFT + x(r.bandHigh ?? r.detections) + 6} y={yy + barH - 1}>
                {formatCount(r.detections)}
              </text>
            </g>
          );
        })}
      </svg>
      {unranked.length > 0 && (
        <p className="ranking-incomplete">
          Not ranked (incomplete):{' '}
          {unranked.map((r) => `${r.year}, ${formatCount(r.detections)} detections so far`).join('; ')}.
        </p>
      )}
    </section>
  );
}
