import { render, screen, within } from '@testing-library/react';
import example from '../../../docs/api-exemplo.json';
import type { CalendarResponse } from '../api/types';
import { KeyIndicators } from './KeyIndicators';
import { RecentPanel } from './RecentPanel';
import { SeasonalPattern } from './SeasonalPattern';
import { YearRanking } from './YearRanking';

const data = example as unknown as CalendarResponse;

describe('KeyIndicators', () => {
  it('shows the total detections of the period, with its months and origin', () => {
    render(<KeyIndicators data={data} />);
    const panel = screen.getByRole('region', { name: /key indicators/i });
    expect(panel).toHaveTextContent('173,393');
    expect(panel).toHaveTextContent('Jan 2003–Nov 2026');
    expect(panel).toHaveTextContent(/estimated from MODIS/i);
  });

  it('compares the latest complete year with the reference average', () => {
    render(<KeyIndicators data={data} />);
    const panel = screen.getByRole('region', { name: /key indicators/i });
    expect(panel).toHaveTextContent('2025');
    expect(panel).toHaveTextContent('−41%');
    expect(panel).toHaveTextContent('4,406');
    expect(panel).toHaveTextContent('7,460');
    expect(panel).toHaveTextContent(/observed \(VIIRS\)/i);
  });

  it('shows the last 7 days against the typical value', () => {
    render(<KeyIndicators data={data} />);
    expect(screen.getByRole('region', { name: /key indicators/i })).toHaveTextContent('+54%');
  });
});

describe('RecentPanel', () => {
  it('has a "Last 7 days" region with the count, the typical value and the difference', () => {
    render(<RecentPanel recent={data.recent} updatedAt={data.meta.updated_at} />);
    const card = screen.getByRole('region', { name: /last 7 days/i });
    expect(card).toHaveTextContent('61');
    expect(card).toHaveTextContent('+54%');
    expect(card).toHaveTextContent('39.5');
    expect(card).toHaveTextContent('35.2–45.5');
    expect(card).toHaveTextContent(/above the typical range/i);
    expect(card).toHaveTextContent('8–14 Nov 2026');
  });

  it('says how the typical range was built', () => {
    render(<RecentPanel recent={data.recent} updatedAt={data.meta.updated_at} />);
    const card = screen.getByRole('region', { name: /last 7 days/i });
    expect(card).toHaveTextContent('434 windows');
    expect(card).toHaveTextContent('14 years');
  });

  it('counts high-intensity detections as a class, never as power', () => {
    render(<RecentPanel recent={data.recent} updatedAt={data.meta.updated_at} />);
    const card = screen.getByRole('region', { name: /last 7 days/i });
    expect(card).toHaveTextContent(/5 high-intensity detections \(8%\)/);
    expect(card).not.toHaveTextContent(/MW|FRP/);
  });

  it('draws the current window over the typical range, with words and not only shapes', () => {
    render(<RecentPanel recent={data.recent} updatedAt={data.meta.updated_at} />);
    const card = screen.getByRole('region', { name: /last 7 days/i });
    expect(within(card).getByRole('img', { name: /61 detections.*typical range 35\.2 to 45\.5/i })).toBeInTheDocument();
  });

  it('has a "Month to date" region with its own comparison', () => {
    render(<RecentPanel recent={data.recent} updatedAt={data.meta.updated_at} />);
    const card = screen.getByRole('region', { name: /month to date/i });
    expect(card).toHaveTextContent('146');
    expect(card).toHaveTextContent('+19%');
    expect(card).toHaveTextContent('1–14 Nov 2026');
  });

  it('shows once when the data was updated, in UTC', () => {
    render(<RecentPanel recent={data.recent} updatedAt={data.meta.updated_at} />);
    const updated = screen.getByText(/updated/i);
    expect(updated).toHaveTextContent('14 Nov 2026, 15:00 UTC');
    expect(within(updated).getByText('14 Nov 2026, 15:00 UTC').closest('time')).toHaveAttribute('datetime', '2026-11-14T15:00:00Z');
  });

  it('says "detections", never "fires", as the unit', () => {
    const { container } = render(<RecentPanel recent={data.recent} updatedAt={data.meta.updated_at} />);
    expect(container).not.toHaveTextContent(/\bfires\b/i);
  });
});

describe('SeasonalPattern', () => {
  it('lists the 12 months with median and lowest to highest year in a table', () => {
    render(<SeasonalPattern seasonality={data.seasonality} includesEstimatedYears />);
    const panel = screen.getByRole('region', { name: /seasonal pattern/i });
    const rows = within(panel).getAllByRole('row');
    expect(rows).toHaveLength(1 + 12);
    expect(rows[9]).toHaveTextContent('Sep');
    expect(rows[9]).toHaveTextContent('2,056');
    expect(rows[9]).toHaveTextContent('809–3,503');
  });

  it('names the peak month and how many years entered', () => {
    render(<SeasonalPattern seasonality={data.seasonality} includesEstimatedYears />);
    const panel = screen.getByRole('region', { name: /seasonal pattern/i });
    expect(panel).toHaveTextContent(/peak.*Sep/i);
    expect(panel).toHaveTextContent('23 complete years');
  });

  it('says when estimated years are part of the pattern', () => {
    render(<SeasonalPattern seasonality={data.seasonality} includesEstimatedYears />);
    expect(screen.getByRole('region', { name: /seasonal pattern/i })).toHaveTextContent(/estimated from MODIS/i);
  });

  it('has a chart with text labels for every month', () => {
    render(<SeasonalPattern seasonality={data.seasonality} includesEstimatedYears />);
    const chart = screen.getByRole('img', { name: /seasonal pattern/i });
    expect(within(chart).getByText('Sep')).toBeInTheDocument();
    expect(within(chart).getByText('Jan')).toBeInTheDocument();
  });
});

describe('YearRanking', () => {
  function rowOf(year: number) {
    return screen.getByRole('row', { name: new RegExp(`\\b${year}\\b`) });
  }

  it('is a table with one row per year in the order of the API', () => {
    render(<YearRanking years={data.years} />);
    const panel = screen.getByRole('region', { name: /years ranked/i });
    const rows = within(panel).getAllByRole('row');
    expect(rows).toHaveLength(1 + data.years.length);
    expect(rows[1]).toHaveTextContent('2024');
  });

  it('shows the uncertainty range and origin only on estimated years', () => {
    render(<YearRanking years={data.years} />);
    expect(rowOf(2010)).toHaveTextContent('11,105–12,253');
    expect(rowOf(2010)).toHaveTextContent(/estimated from MODIS/i);
    expect(rowOf(2024)).not.toHaveTextContent('–');
    expect(rowOf(2024)).toHaveTextContent(/observed \(VIIRS\)/i);
  });

  it('marks 2012 as mixed', () => {
    render(<YearRanking years={data.years} />);
    expect(rowOf(2012)).toHaveTextContent(/mixed/i);
  });

  it('leaves incomplete years without a position and says why', () => {
    render(<YearRanking years={data.years} />);
    expect(rowOf(2026)).toHaveTextContent(/not ranked/i);
    expect(rowOf(2026)).toHaveTextContent(/incomplete/i);
  });
});
