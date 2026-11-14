import example from '../../docs/api-exemplo.json';
import type { CalendarResponse } from './api/types';
import { FireCalendar } from './calendar/FireCalendar';
import { KeyIndicators } from './summary/KeyIndicators';
import { RecentPanel } from './summary/RecentPanel';
import { SeasonalPattern } from './summary/SeasonalPattern';
import { YearRanking } from './summary/YearRanking';

// Até a API existir (D7), a ferramenta mostra o JSON de exemplo do contrato, com aviso na tela.
const data = example as unknown as CalendarResponse;
const includesEstimatedYears = data.years.some((y) => y.complete && y.source !== 'observed_viirs');

// Ordem da tela (docs/ux-telas.md): primeiro o agora, depois a história, por último o detalhe.
export function App() {
  return (
    <section className="tool-panel" aria-labelledby="tool-title">
      <h2 id="tool-title">Explore an area</h2>
      <p>Choose an area and a period to see its monthly fire calendar since 2003.</p>
      <p className="example-notice" role="note">
        Showing example data for an area in the Amazon while area selection is being built.
      </p>
      <KeyIndicators data={data} />
      <RecentPanel recent={data.recent} updatedAt={data.meta.updated_at} />
      <FireCalendar months={data.months} />
      <div className="history-grid">
        <SeasonalPattern seasonality={data.seasonality} includesEstimatedYears={includesEstimatedYears} />
        <YearRanking years={data.years} />
      </div>
    </section>
  );
}
