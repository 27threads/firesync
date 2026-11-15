import { useId } from 'react';
import { interpolateCividis } from 'd3-scale-chromatic';
import { formatCount } from '../format';
import type { CalendarTheme } from './CalendarSvg';

interface LegendProps {
  extent: [number, number] | null;
  theme: CalendarTheme;
  className?: string;
}

const RAMP = Array.from({ length: 11 }, (_, i) => interpolateCividis(i / 10)).join(', ');

function geometricMid([min, max]: [number, number]): number {
  return Math.sqrt(min * max);
}

export function Legend({ extent, theme, className = '' }: LegendProps) {
  const uid = useId().replace(/:/g, '');
  const dark = theme === 'dark';
  const stroke = dark ? '#eef1f4' : '#15181b';
  return (
    <div className={`legend theme-${theme} ${className}`} aria-label="Calendar legend" role="group">
      {extent && (
        <div className="legend__ramp">
          <span>Detections per month (log scale)</span>
          <span className="legend__ramp-bar" style={{ background: `linear-gradient(90deg, ${RAMP})` }} aria-hidden="true" />
          <span className="legend__ticks">
            <span>{formatCount(extent[0])}</span>
            <span>{formatCount(geometricMid(extent))}</span>
            <span>{formatCount(extent[1])}</span>
          </span>
        </div>
      )}
      <span className="legend__item">
        <svg className="legend__swatch" viewBox="0 0 16 12" aria-hidden="true">
          <rect width="16" height="12" fill={dark ? '#22282e' : '#fff'} stroke={dark ? '#939ca6' : '#4b535c'} />
          <line x1="5" x2="11" y1="6" y2="6" stroke={dark ? '#939ca6' : '#4b535c'} />
        </svg>
        Zero
      </span>
      <span className="legend__item">
        <svg className="legend__swatch" viewBox="0 0 16 12" aria-hidden="true">
          <defs>
            <pattern id={`lg-nd-${uid}`} width="6" height="6" patternUnits="userSpaceOnUse">
              <rect width="6" height="6" fill={dark ? '#1d2227' : '#eceeef'} />
              <path d="M0 0L6 6M6 0L0 6" stroke={dark ? '#5b646e' : '#9aa1a8'} strokeWidth="0.8" />
            </pattern>
          </defs>
          <rect width="16" height="12" fill={`url(#lg-nd-${uid})`} />
        </svg>
        No satellite data
      </span>
      <span className="legend__item">
        <svg className="legend__swatch" viewBox="0 0 16 12" aria-hidden="true">
          <defs>
            <pattern id={`lg-h-${uid}`} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line className="cal-hatch-a" x1="0.5" y1="0" x2="0.5" y2="5" />
              <line className="cal-hatch-b" x1="1.6" y1="0" x2="1.6" y2="5" />
            </pattern>
          </defs>
          <rect width="16" height="12" fill={interpolateCividis(0.45)} />
          <rect width="16" height="12" fill={`url(#lg-h-${uid})`} />
        </svg>
        Estimated from MODIS
      </span>
      <span className="legend__item">
        <svg className="legend__swatch" viewBox="0 0 16 12" aria-hidden="true">
          <rect width="16" height="12" fill={interpolateCividis(0.6)} />
          <rect x="1.25" y="1.25" width="13.5" height="9.5" fill="none" stroke={stroke} strokeWidth="1.5" strokeDasharray="3 2" />
        </svg>
        Incomplete
      </span>
      <span className="legend__item">
        <svg className="legend__swatch" viewBox="0 0 16 12" aria-hidden="true">
          <rect width="16" height="12" fill={interpolateCividis(0.6)} />
          <circle cx="11.5" cy="4.5" r="2.4" fill={stroke} stroke={dark ? '#0d0f11' : '#fbfbfa'} strokeWidth="1.2" />
        </svg>
        Provisional
      </span>
    </div>
  );
}
