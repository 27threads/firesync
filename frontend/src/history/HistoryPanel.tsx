import { useMemo, useState } from 'react';
import type { CalendarRequest, CalendarResponse } from '../api/types';
import { buildCalendar, type CalendarCell } from '../calendar/calendarModel';
import { CalendarSvg, FULL_GEOMETRY } from '../calendar/CalendarSvg';
import { Legend } from '../calendar/Legend';
import { describeMonth } from '../calendar/monthDetail';
import { MonthTip } from '../calendar/MonthTip';
import { ExportBar } from '../export/ExportBar';
import type { ResultState } from '../state/explorerModel';
import { Tooltip } from '../ui/Tooltip';
import { MonthPanel } from './MonthPanel';
import { SeasonalChart } from './SeasonalChart';
import { YearRanking } from './YearRanking';

interface HistoryPanelProps {
  shown: { data: CalendarResponse; isDemo: boolean } | null;
  result: ResultState;
  selectedKey: string | null;
  onSelectKey: (key: string | null) => void;
  highlightMonthIndex: number | null;
  highlightYear: number | null;
  areaLabel: string;
  periodLabel: string;
  request: CalendarRequest | null;
}

function CalendarTable({ data }: { data: CalendarResponse }) {
  return (
    <div className="cal-table-wrap">
      <table className="cal-table">
        <caption className="visually-hidden">Monthly detections, one row per month</caption>
        <thead>
          <tr>
            <th scope="col">Month</th>
            <th scope="col">Detections</th>
            <th scope="col">Source</th>
            <th scope="col">Uncertainty range</th>
            <th scope="col">Days without data</th>
            <th scope="col">Notes</th>
          </tr>
        </thead>
        <tbody>
          {data.months.map((m) => {
            const d = describeMonth(m);
            return (
              <tr key={m.month}>
                <th scope="row">{d.title}</th>
                <td className="n">{d.value.replace(' detections', '')}</td>
                <td>{m.source === 'estimated_modis' ? 'Estimated (MODIS)' : 'Observed (VIIRS)'}</td>
                <td>{d.range ? d.range.replace('Uncertainty range ', '') : '—'}</td>
                <td className="n">{m.missing_days}</td>
                <td>{[m.incomplete && 'Incomplete', m.provisional && 'Provisional'].filter(Boolean).join(', ')}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function EmptyHistory({ result }: { result: ResultState }) {
  if (result.kind === 'no_coverage') {
    return (
      <div className="empty-state">
        <h3>No record for this area</h3>
        <p>The area is outside the current coverage, so there is no calendar to show. This is not a record of zero detections.</p>
      </div>
    );
  }
  if (result.kind === 'error' || result.kind === 'rate_limited') {
    return (
      <div className="empty-state">
        <h3>The record could not be loaded</h3>
        <p>{result.message}</p>
      </div>
    );
  }
  return (
    <div className="empty-state">
      <h3>Loading the record…</h3>
      <p>Monthly detections for this area will appear here.</p>
    </div>
  );
}

export function HistoryPanel({
  shown,
  result,
  selectedKey,
  onSelectKey,
  highlightMonthIndex,
  highlightYear,
  areaLabel,
  periodLabel,
  request,
}: HistoryPanelProps) {
  const [asTable, setAsTable] = useState(false);
  const [hover, setHover] = useState<{ cell: CalendarCell; anchor: DOMRect } | null>(null);
  const [focusKey, setFocusKey] = useState<string | null>(null);
  const data = shown?.data ?? null;
  const model = useMemo(() => (data ? buildCalendar(data.months) : null), [data]);
  const selectedMonth = data && selectedKey ? data.months.find((m) => m.month === selectedKey) ?? null : null;
  const includesEstimatedYears = data ? data.years.some((y) => y.complete && y.source !== 'observed_viirs') : false;

  return (
    <div className="ws-history" id="history">
      <section aria-labelledby="history-title">
        <div className="section-head">
          <div>
            <h2 id="history-title">A longer view of fire activity</h2>
            <p>
              Monthly detections on the VIIRS scale, {periodLabel}. One row per year, January to December.
              {shown?.isDemo ? ' Demo data.' : ''}
            </p>
          </div>
          {data && (
            <div className="section-head__actions">
              <button type="button" className="btn btn--quiet" aria-pressed={asTable} onClick={() => setAsTable((v) => !v)}>
                View as table
              </button>
            </div>
          )}
        </div>

        {!data || !model ? (
          <EmptyHistory result={result} />
        ) : (
          <div className={result.kind === 'loading' ? 'is-loading' : undefined}>
            <div className="calendar-block">
              <div>
                <div className="calendar-scroll">
                  <CalendarSvg
                    months={data.months}
                    theme="light"
                    geometry={FULL_GEOMETRY}
                    interactive
                    label={`Fire calendar, monthly detections, ${periodLabel}`}
                    selectedKey={selectedKey}
                    focusKey={focusKey}
                    highlightMonthIndex={highlightMonthIndex}
                    highlightYear={highlightYear}
                    onFocusKeyChange={setFocusKey}
                    onSelect={(cell) => onSelectKey(cell.month ? cell.key : null)}
                    onHover={(cell, anchor) => setHover(cell && anchor ? { cell, anchor } : null)}
                  />
                </div>
                <Legend extent={model.positiveExtent} theme="light" className="calendar-legend" />
              </div>
              <MonthPanel month={selectedMonth} months={data.months} />
            </div>
            {asTable && <CalendarTable data={data} />}

            <div className="context-grid">
              <SeasonalChart seasonality={data.seasonality} includesEstimatedYears={includesEstimatedYears} highlightMonthIndex={highlightMonthIndex} />
              <YearRanking years={data.years} highlightYear={highlightYear} />
            </div>

            <ExportBar data={data} isDemo={shown?.isDemo ?? false} request={request} areaLabel={areaLabel} periodLabel={periodLabel} />
          </div>
        )}
      </section>
      <Tooltip anchor={hover?.anchor ?? null} id="calendar-tip">
        {hover && <MonthTip cell={hover.cell} />}
      </Tooltip>
    </div>
  );
}
