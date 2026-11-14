import example from '../../docs/api-exemplo.json';
import type { CalendarMonth } from './api/types';
import { FireCalendar } from './calendar/FireCalendar';

// Até a API existir (D7), a ferramenta mostra o JSON de exemplo do contrato, com aviso na tela.
const exampleMonths = example.months as CalendarMonth[];

export function App() {
  return (
    <section className="tool-panel" aria-labelledby="tool-title">
      <h2 id="tool-title">Explore an area</h2>
      <p>Choose an area and a period to see its monthly fire calendar since 2003.</p>
      <p className="example-notice" role="note">
        Showing example data for an area in the Amazon while area selection is being built.
      </p>
      <FireCalendar months={exampleMonths} />
    </section>
  );
}
