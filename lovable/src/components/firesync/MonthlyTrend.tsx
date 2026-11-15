import { useState } from 'react';
import { line, scaleLinear, interpolateCividis } from 'd3';
import { number, monthNames, monthLabel, conversionBand, type Month, type CalendarData } from '@/lib/fire-data';
import { Button } from '@/components/ui/button';

export function MonthlyTrend({ data }: { data: CalendarData }) {
  const years = [...new Set(data.months.map(month => Number(month.month.slice(0, 4))))].sort((a, b) => a - b);
  const first = years.at(0) ?? 2003;
  const last = years.at(-1) ?? 2026;
  const [start, setStart] = useState(Math.max(first, last - 4));
  const [end, setEnd] = useState(last);
  const [selectedYear, setSelectedYear] = useState(last);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const range = years.filter(year => year >= Math.max(first, start) && year <= Math.min(last, end));
  const activeYear = range.includes(selectedYear) ? selectedYear : range.at(-1);
  const records = data.months.filter(month => range.includes(Number(month.month.slice(0, 4))));
  const detail = records.find(month => month.month === selectedMonth && Number(month.month.slice(0, 4)) === activeYear) ?? records.filter(month => Number(month.month.slice(0, 4)) === activeYear).at(-1);
  const x = scaleLinear().domain([1, 12]).range([55, 550]);
  const y = scaleLinear().domain([0, Math.max(1, ...records.map(month => month.detections ?? 0)) * 1.1]).nice().range([224, 28]);
  const path = line<Month>().defined(month => month.detections != null).x(month => x(Number(month.month.slice(5)))).y(month => y(month.detections ?? 0));
  const color = (year: number) => interpolateCividis(range.length === 1 ? 0.2 : range.indexOf(year) / (range.length - 1));

  return <section className="annual-trend" aria-label="Monthly comparison across years">
    <div className="trend-heading"><h3>Monthly patterns across years</h3><p>Monthly fire detections · Demo data</p></div>
    <div className="trend-range"><label>From<select aria-label="Trend start year" value={Math.max(first, start)} onChange={event => { const value = Number(event.target.value); setStart(value); if (value > end) setEnd(value); }}>{years.map(year => <option key={year}>{year}</option>)}</select></label><span>—</span><label>To<select aria-label="Trend end year" value={Math.min(last, end)} onChange={event => { const value = Number(event.target.value); setEnd(value); if (value < start) setStart(value); }}>{years.map(year => <option key={year}>{year}</option>)}</select></label></div>
    <div className="monthly-trend-scroll"><svg viewBox="0 0 590 264" className="annual-trend-svg" role="group" aria-label={`Monthly fire detections, January to December, years ${range.at(0)}–${range.at(-1)}`}>
      {y.ticks(4).map(tick => <g key={tick}><line className="trend-grid" x1="55" x2="550" y1={y(tick)} y2={y(tick)} /><text x="46" y={y(tick) + 4} textAnchor="end">{number(tick)}</text></g>)}
      {monthNames.map((name, index) => <text key={name} x={x(index + 1)} y="250" textAnchor="middle">{name}</text>)}
      {range.map(year => {
        const months = Array.from({ length: 12 }, (_, index) => data.months.find(month => month.month === `${year}-${String(index + 1).padStart(2, '0')}`) ?? { month: `${year}-${String(index + 1).padStart(2, '0')}`, detections: null, band_low: null, band_high: null, source: '', raw_count: null, missing_days: 0, incomplete: false, provisional: false, anomaly: null, anomaly_pct: null });
        return <g key={year} opacity={year === activeYear ? 1 : 0.45}><path fill="none" stroke={color(year)} strokeWidth={year === activeYear ? 3 : 1.5} d={path(months) ?? ''} />{year === activeYear && months.filter(month => month.detections != null).map(month => <g key={month.month} role="button" tabIndex={0} className="trend-point" aria-label={`${monthLabel(month.month)}: ${number(month.detections)} fire detections`} onClick={() => setSelectedMonth(month.month)} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelectedMonth(month.month); } }}><circle className="trend-hit" cx={x(Number(month.month.slice(5)))} cy={y(month.detections ?? 0)} r="12" /><circle cx={x(Number(month.month.slice(5)))} cy={y(month.detections ?? 0)} r={detail?.month === month.month ? 5 : 3} fill={month.incomplete ? 'var(--calendar-surface)' : color(year)} stroke={month.incomplete || month.provisional ? 'var(--mission-red)' : color(year)} strokeWidth="2" /><title>{`${monthLabel(month.month)} · ${number(month.detections)} detections`}</title></g>)}</g>;
      })}
    </svg></div>
    <div className="trend-year-legend" aria-label="Compare years">{range.map(year => <Button variant="calendarTab" key={year} aria-pressed={year === activeYear} onClick={() => { setSelectedYear(year); setSelectedMonth(null); }}><svg width="16" height="8" aria-hidden="true"><path d="M0 4H16" stroke={color(year)} strokeWidth="3" /></svg>{year}</Button>)}</div>
    {detail && <div className="trend-detail" role="status"><div><strong>{monthLabel(detail.month)}</strong><span>{detail.source === 'estimated_modis' ? 'Estimated MODIS' : 'Observed VIIRS'} · {[detail.incomplete && 'Incomplete', detail.provisional && 'Provisional'].filter(Boolean).join(' · ') || 'Complete'}</span></div><div><strong>{number(detail.detections)}</strong><span>fire detections</span></div>{conversionBand(detail) && <div><strong>{conversionBand(detail)}</strong><span>Conversion uncertainty</span></div>}</div>}
    <p className="trend-note">○ Incomplete · Red outline: provisional or incomplete. Gaps indicate unavailable months. Illustrative fixture, not measured results.</p>
  </section>;
}