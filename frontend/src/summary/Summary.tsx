import { useEffect, useState, type ReactNode } from 'react';
import type { CalendarResponse, RecentWindow } from '../api/types';
import { MONTH_NAMES } from '../calendar/calendarModel';
import type { StoryStep } from '../discovery/exampleStory';
import { formatCount, formatDayRange, formatShare, formatSignedPct, formatUpdatedAt, formatWindowValue } from '../format';
import type { ResultState } from '../state/explorerModel';
import { RangeStrip } from './RangeStrip';
import { compareToTypical } from './summaryModel';

interface SummaryProps {
  shown: { data: CalendarResponse; isDemo: boolean } | null;
  result: ResultState;
  stale: boolean;
  selectionIsExample: boolean;
  periodIgnoredInDemo: boolean;
  story: StoryStep[] | null;
  storyIndex: number;
  onStoryIndex: (i: number) => void;
  onRetry: () => void;
}

const VERDICT = {
  above: 'Above the typical range',
  within: 'Within the typical range',
  below: 'Below the typical range',
} as const;

function dayLabel(iso: string): string {
  const [y, m, d] = iso.split('-').map(Number);
  return `${d} ${MONTH_NAMES[m - 1]} ${y}`;
}

function WindowCard({ title, window, secondary = false }: { title: string; window: RecentWindow; secondary?: boolean }) {
  return (
    <section className={`window-card${secondary ? ' window-card--secondary' : ''}`} aria-label={title}>
      <p className="window-card__label">
        {title} · {formatDayRange(window.start, window.end)}
      </p>
      <div className="window-card__figures">
        <span>
          <span className="window-card__value">{formatCount(window.detections)}</span>{' '}
          <span className="window-card__unit">detections</span>
        </span>
        <span className="window-card__diff">
          {window.difference_pct === null ? 'No typical median to compare' : `${formatSignedPct(window.difference_pct)} vs. typical`}
        </span>
      </div>
      <RangeStrip window={window} compact={secondary} />
      <p className="window-card__note">
        Typical for these dates: {formatWindowValue(window.typical_p25)}–{formatWindowValue(window.typical_p75)}, median{' '}
        {formatWindowValue(window.typical_median)} (P25–P75 of {formatCount(window.n_windows)} windows within ±15 days, {window.n_years} years).
        {!secondary && window.high_share !== null && (
          <>
            {' '}
            {formatCount(window.n_high)} high-intensity detections ({formatShare(window.high_share)}).
          </>
        )}
      </p>
    </section>
  );
}

function RetryButton({ onRetry, waitSeconds }: { onRetry: () => void; waitSeconds: number | null }) {
  const [remaining, setRemaining] = useState(waitSeconds ?? 0);
  useEffect(() => {
    if (!waitSeconds) return;
    setRemaining(waitSeconds);
    const timer = window.setInterval(() => setRemaining((s) => Math.max(0, s - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [waitSeconds]);
  return (
    <div className="notice__actions">
      <button type="button" className="btn btn--quiet" onClick={onRetry} disabled={remaining > 0}>
        {remaining > 0 ? `Try again in ${remaining} s` : 'Try again'}
      </button>
    </div>
  );
}

function Story({ steps, index, onIndex, isDemo }: { steps: StoryStep[]; index: number; onIndex: (i: number) => void; isDemo: boolean }) {
  const step = steps[index] ?? steps[0];
  return (
    <section className="story" aria-label="Explore the example">
      <div className="story__head">
        <h4 className="story__title">Explore the example</h4>
        <div className="story__steps">
          {steps.map((s, i) => (
            <button
              key={s.id}
              type="button"
              className="story__dot"
              aria-current={i === index ? 'step' : undefined}
              aria-label={`Question ${i + 1}: ${s.question}`}
              onClick={() => onIndex(i)}
            >
              {i + 1}
            </button>
          ))}
        </div>
      </div>
      <p className="story__q">{step.question}</p>
      <p className="story__a" aria-live="polite">
        {step.answer}
      </p>
      {isDemo && <p className="story__a">These answers describe the demo data, not a real place.</p>}
    </section>
  );
}

export function Summary({
  shown,
  result,
  stale,
  selectionIsExample,
  periodIgnoredInDemo,
  story,
  storyIndex,
  onStoryIndex,
  onRetry,
}: SummaryProps) {
  let notice: ReactNode = null;
  if (result.kind === 'error') {
    notice = (
      <div className="notice notice--alert" role="alert">
        {result.message}
        <RetryButton onRetry={onRetry} waitSeconds={null} />
      </div>
    );
  } else if (result.kind === 'rate_limited') {
    notice = (
      <div className="notice notice--alert" role="alert">
        {result.message}
        <RetryButton onRetry={onRetry} waitSeconds={result.retryAfter} />
      </div>
    );
  } else if (result.kind === 'no_coverage') {
    notice = (
      <p className="notice" role="status">
        {result.message} Outside coverage there is no record to compare, which is not the same as zero detections.
      </p>
    );
  } else if (result.kind === 'api_unavailable') {
    notice = (
      <div className="notice notice--demo" role="status">
        The API is unavailable, so the figures below are demo data for the example area, not for your selection.
        <RetryButton onRetry={onRetry} waitSeconds={null} />
      </div>
    );
  } else if (shown?.isDemo && result.kind !== 'loading') {
    notice = (
      <p className="notice notice--demo" role="note">
        Demo data: illustrative values from the API contract example, shown so the tool can be explored without the API.
        {periodIgnoredInDemo && ' The demo always shows its full period; changing the period needs the API.'}
      </p>
    );
  } else if (stale) {
    notice = (
      <p className="notice notice--alert" role="alert">
        Data may be out of date (more than 6 hours old).
      </p>
    );
  }

  const hasData = shown !== null && (result.kind === 'ready' || result.kind === 'demo' || result.kind === 'api_unavailable' || result.kind === 'loading');
  const data = shown?.data;
  const last = data?.months[data.months.length - 1];
  const status = data ? compareToTypical(data.recent.last_7_days) : null;

  return (
    <aside className={`summary${result.kind === 'loading' ? ' is-loading' : ''}`} aria-labelledby="summary-question" aria-busy={result.kind === 'loading'}>
      <div className="summary__head">
        <h3 id="summary-question" className="summary__question">
          Is recent fire activity typical here?
        </h3>
        {shown?.isDemo && hasData && <span className="chip chip--demo">Demo data</span>}
      </div>

      {result.kind === 'loading' && (
        <p className="visually-hidden" role="status">
          Loading the record for this area…
        </p>
      )}
      {notice}

      {hasData && data && status && (
        <>
          <p className="summary__verdict">
            <strong>{VERDICT[status]}</strong> for these dates, with data through {dayLabel(data.recent.data_through)}.
          </p>
          <WindowCard title="Last 7 days" window={data.recent.last_7_days} />
          <WindowCard title="Month to date" window={data.recent.month_to_date} secondary />
          <div className="summary__meta">
            <p>Updated {formatUpdatedAt(data.meta.updated_at)}</p>
            {last?.provisional && <p>Recent days come from near real-time data and are provisional.</p>}
            {last?.incomplete && <p>The current month is still incomplete.</p>}
            {data.coverage?.status === 'partial' && (
              <p>
                Partial coverage: {formatShare(data.coverage.covered_fraction)} of this area is covered; figures use only that part.
                {data.coverage.message ? ` ${data.coverage.message}` : ''}
              </p>
            )}
            {data.area && (
              <p>
                {formatCount(data.area.area_km2)} km² · {data.area.biomes.map((b) => `${b.name} ${formatShare(b.fraction)}`).join(', ')}
              </p>
            )}
          </div>
          {selectionIsExample && story && (
            <Story steps={story} index={storyIndex} onIndex={onStoryIndex} isDemo={shown?.isDemo ?? false} />
          )}
          <a className="summary__link" href="#history">
            View the long-term history
          </a>
        </>
      )}
    </aside>
  );
}
