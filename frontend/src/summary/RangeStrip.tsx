import type { RecentWindow } from '../api/types';
import { formatWindowValue } from '../format';
import { rangeStripScale } from './summaryModel';

const WIDTH = 320;
const HEIGHT = 64;
const EDGE = 34;

// Texto perto da borda encosta nela em vez de sair do desenho.
function anchorAt(x: number): 'start' | 'middle' | 'end' {
  if (x < EDGE) return 'start';
  if (x > WIDTH - EDGE) return 'end';
  return 'middle';
}

interface RangeStripProps {
  window: RecentWindow;
  patternId: string;
}

// A janela atual desenhada sobre a faixa do normal (P25–P75), e não só um número.
export function RangeStrip({ window, patternId }: RangeStripProps) {
  const x = rangeStripScale(window, WIDTH);
  const low = x(window.typical_p25);
  const high = x(window.typical_p75);
  const median = x(window.typical_median);
  const now = x(window.detections);
  const typicalCenter = (low + high) / 2;

  const label =
    `${formatWindowValue(window.detections)} detections now; ` +
    `typical range ${formatWindowValue(window.typical_p25)} to ${formatWindowValue(window.typical_p75)}, ` +
    `median ${formatWindowValue(window.typical_median)}`;

  return (
    <svg className="range-strip" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={label}>
      <defs>
        <pattern id={patternId} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="5" className="range-strip__hatch" />
        </pattern>
      </defs>
      <line x1={0} x2={WIDTH} y1={32} y2={32} className="range-strip__axis" />
      <rect
        x={low}
        y={22}
        width={Math.max(high - low, 1)}
        height={20}
        fill={`url(#${patternId})`}
        className="range-strip__typical"
      />
      <line x1={median} x2={median} y1={22} y2={42} className="range-strip__median" />
      <text x={typicalCenter} y={14} textAnchor={anchorAt(typicalCenter)} className="range-strip__label">
        Typical range
      </text>
      <line x1={now} x2={now} y1={16} y2={44} className="range-strip__now" />
      <path d={`M${now},44 l-6,9 h12 z`} className="range-strip__now-mark" />
      <text x={now} y={HEIGHT - 1} textAnchor={anchorAt(now)} className="range-strip__label range-strip__label--now">
        {`Now ${formatWindowValue(window.detections)}`}
      </text>
    </svg>
  );
}
