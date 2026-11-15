import type { Recent, RecentWindow } from '../api/types';
import { formatDayRange, formatShare, formatSignedPct, formatUpdatedAt, formatWindowValue } from '../format';
import { RangeStrip } from './RangeStrip';
import { compareToTypical, type TypicalStatus } from './summaryModel';

const STATUS_TEXT: Record<TypicalStatus, string> = {
  above: 'Above the typical range',
  within: 'Within the typical range',
  below: 'Below the typical range',
};

interface RecentCardProps {
  id: string;
  title: string;
  window: RecentWindow;
}

function RecentCard({ id, title, window }: RecentCardProps) {
  const status = compareToTypical(window);
  const titleId = `${id}-title`;
  const high =
    window.high_share === null
      ? 'No detections'
      : `${window.n_high} high-intensity detections (${formatShare(window.high_share)})`;

  return (
    <section className="recent-card" aria-labelledby={titleId}>
      <h3 id={titleId}>{title}</h3>
      <p className="recent-card__dates">
        <time dateTime={window.start}>{formatDayRange(window.start, window.end)}</time>
      </p>
      <p className="recent-card__headline">
        <span className="stat">{formatSignedPct(window.difference_pct)}</span> vs. typical
      </p>
      <p className={`status status--${status}`}>{STATUS_TEXT[status]}</p>
      <RangeStrip window={window} patternId={`${id}-hatch`} />
      <dl className="recent-card__facts">
        <div>
          <dt>Detections</dt>
          <dd>{formatWindowValue(window.detections)}</dd>
        </div>
        <div>
          <dt>Typical (median)</dt>
          <dd>{formatWindowValue(window.typical_median)}</dd>
        </div>
        <div>
          <dt>Typical range (P25 to P75)</dt>
          <dd>{`${formatWindowValue(window.typical_p25)}–${formatWindowValue(window.typical_p75)}`}</dd>
        </div>
        <div>
          <dt>High intensity</dt>
          <dd>{high}</dd>
        </div>
      </dl>
      <p className="stat-note">
        {`Typical: ${window.n_windows} windows of the same length within ±15 days of these dates, in ${window.n_years} years of VIIRS data. It shows how much fire varies between years, not measurement uncertainty.`}
      </p>
    </section>
  );
}

interface RecentPanelProps {
  recent: Recent;
  updatedAt: string;
}

export function RecentPanel({ recent, updatedAt }: RecentPanelProps) {
  return (
    <div className="recent">
      <p className="recent__updated">
        Updated <time dateTime={updatedAt}>{formatUpdatedAt(updatedAt)}</time>. Recent days are VIIRS near
        real-time data, provisional until the standard product replaces them.
      </p>
      <div className="recent__cards">
        <RecentCard id="last-7-days" title="Last 7 days vs. typical" window={recent.last_7_days} />
        <RecentCard id="month-to-date" title="Month to date vs. typical" window={recent.month_to_date} />
      </div>
    </div>
  );
}
