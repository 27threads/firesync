import type { RecentWindow } from '../api/types';
import { formatCount, formatWindowValue } from '../format';
import { rangeStripScale } from './summaryModel';

const WIDTH = 360;
const HEIGHT = 54;
const TRACK_Y = 20;

// O valor atual desenhado sobre a faixa típica (P25–P75 das janelas de referência).
export function RangeStrip({ window, compact = false }: { window: RecentWindow; compact?: boolean }) {
  const x = rangeStripScale(window, WIDTH - 16);
  const off = 8;
  const value = off + x(window.detections);
  const p25 = off + x(window.typical_p25);
  const p75 = off + x(window.typical_p75);
  const median = off + x(window.typical_median);
  const h = compact ? 8 : 12;
  return (
    <svg
      className="range-strip"
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={`Current ${formatCount(window.detections)} detections; typical range ${formatWindowValue(window.typical_p25)} to ${formatWindowValue(window.typical_p75)}, median ${formatWindowValue(window.typical_median)}.`}
    >
      <rect className="range-strip__track" x={off} y={TRACK_Y} width={WIDTH - 16} height={h} />
      <rect className="range-strip__band" x={p25} y={TRACK_Y} width={Math.max(1, p75 - p25)} height={h} />
      <line className="range-strip__median" x1={median} x2={median} y1={TRACK_Y - 3} y2={TRACK_Y + h + 3} />
      <line className="range-strip__value-line" x1={value} x2={value} y1={TRACK_Y - 8} y2={TRACK_Y + h + 4} />
      <path className="range-strip__value" d={`M${value - 5} ${TRACK_Y - 14} H${value + 5} L${value} ${TRACK_Y - 7} Z`} />
      <text x={(p25 + p75) / 2} y={TRACK_Y + h + 16} textAnchor="middle">
        typical {formatWindowValue(window.typical_p25)}–{formatWindowValue(window.typical_p75)}
      </text>
      <text x={off} y={TRACK_Y + h + 16}>
        0
      </text>
    </svg>
  );
}
