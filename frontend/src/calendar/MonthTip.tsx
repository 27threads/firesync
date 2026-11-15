import type { CalendarCell } from './calendarModel';
import { describeMonth } from './monthDetail';

// Conteúdo do tooltip: mês, detecções, origem, faixa (só nos estimados) e dias sem dado.
export function MonthTip({ cell }: { cell: CalendarCell }) {
  if (!cell.month) {
    return <div className="tip__muted">{cell.label}</div>;
  }
  const d = describeMonth(cell.month);
  return (
    <>
      <div className="tip__title">{d.title}</div>
      <div className="tip__value">{d.value}</div>
      <div>{d.source}</div>
      {d.range && <div>{d.range}</div>}
      {d.flags.map((f) => (
        <div key={f} className="tip__muted">
          {f}
        </div>
      ))}
    </>
  );
}
